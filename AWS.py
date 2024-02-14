import json
import boto3
import APIKey
import botocore.exceptions


# us-gov-west-1 is also a supported bedrock region but needs an additional security token
aws_regions = [
    "us-east-1",
    "us-west-2",
    "ap-southeast-1",
    "ap-northeast-1",
    "eu-central-1",
]


def check_aws(key: APIKey):
    line = key.api_key.split(":")
    access_key = line[0]
    secret = line[1]

    try:
        try:
            session = boto3.Session(aws_access_key_id=access_key,aws_secret_access_key=secret)
            sts_client = session.client("sts")
            iam_client = session.client("iam")
            bedrock_runtime_client = session.client("bedrock-runtime")

            region = get_region(session)
            if region is not None and len(region) > 0:
                key.region = region[0]
                key.alt_regions = region[1:]
                # key.bedrock_enabled = True
                key.useless = False
            else:
                key.useless_reasons.append('Failed Region Fetch')

            response = sts_client.get_caller_identity()
            if response and 'Arn' in response:
                arn_parts = response['Arn'].split('/')
                if len(arn_parts) > 1:
                    username = arn_parts[1]
                else:
                    username = 'default'
            else:
                username = 'default'
            if username is not None:
                key.username = username
        except botocore.exceptions.ClientError:
            return

        policies = None
        try:
            policies = iam_client.list_attached_user_policies(UserName=username)['AttachedPolicies']
        except botocore.exceptions.ClientError:
            key.useless_reasons.append('Failed Policy Fetch')

        can_invoke = test_invoke_perms(bedrock_runtime_client)
        if can_invoke is not None:
            key.bedrock_enabled = True
            key.useless = False
        else:
            key.useless_reasons.append('Failed Model Invoke Check')

        if policies is not None:
            for policy in policies:
                if "AdministratorAccess" in policy["PolicyName"]:
                    key.admin_priv = True
                    key.useless = False
                    break

                policy_ver = iam_client.get_policy(PolicyArn=policy['PolicyArn'])['Policy']['DefaultVersionId']
                policy_doc = iam_client.get_policy_version(PolicyArn=policy['PolicyArn'], VersionId=policy_ver)['PolicyVersion']['Document']

                for statement in policy_doc['Statement']:
                    if statement['Effect'] == 'Allow':
                        if statement['Action'] == '*':
                            key.admin_priv = True
                            key.useless = False
                        elif 'iam:CreateUser' in statement['Action']:
                            key.useless = False
                        continue

                # Admin keys will never expose this policy even if they are quarantined.
                if "AWSCompromisedKeyQuarantine" in policy["PolicyName"]:
                    key.useless = True
                    key.useless_reasons.append('Quarantined Key')
                    break
        if not key.useless:
            check_logging(session, key)
        elif key.useless and policies is not None:
            key.useless_reasons.append('Key policies lack Admin or User Creation perms')
        return True

    except botocore.exceptions.ClientError as e:
        print(e)
        print("Please report this on github if you see this because I missed something if this shows up.")
        return


def get_region(session):
    regions = []
    for region in aws_regions:
        try:
            bedrock_client = session.client("bedrock", region_name=region)
            response = bedrock_client.list_foundation_models()
            cloudies = ['anthropic.claude-v1', 'anthropic.claude-v2']
            models = [model['modelId'] for model in response.get('modelSummaries', [])]
            if all(model_id in models for model_id in cloudies):
                regions.append(region)
        except botocore.exceptions.ClientError:
            return
    return regions


def test_invoke_perms(bedrock_runtime_client):
    data = {
        "prompt": "\n\nHuman:\n\nAssistant:",
        "max_tokens_to_sample": -1,
    }
    try:
        bedrock_runtime_client.invoke_model(body=json.dumps(data), modelId="anthropic.claude-instant-v1")
    except bedrock_runtime_client.exceptions.ValidationException:
        return True
    except bedrock_runtime_client.exceptions.AccessDeniedException:
        return


def check_logging(session, key: APIKey):
    try:
        bedrock_client = session.client("bedrock", region_name=key.region)
        logging_config = bedrock_client.get_model_invocation_logging_configuration()

        if 'loggingConfig' in logging_config and 'textDataDeliveryEnabled' in logging_config['loggingConfig']:
            key.logged = logging_config['loggingConfig']['textDataDeliveryEnabled']
        else:
            key.logged = False

    except botocore.exceptions.ClientError:
        return


def pretty_print_aws_keys(keys):
    print('-' * 90)
    admin_count = 0
    ready_to_go_keys = []
    needs_setup_keys = []
    useless_keys = []

    for key in keys:
        if key.useless:
            useless_keys.append(key)
        else:
            if key.admin_priv:
                admin_count += 1
            if key.bedrock_enabled:
                ready_to_go_keys.append(key)
            else:
                needs_setup_keys.append(key)

    if ready_to_go_keys:
        print(f"Validated {len(ready_to_go_keys)} AWS keys that are working and already have Bedrock setup.")
        for key in ready_to_go_keys:
            print(f'{key.api_key}' + (f' | {key.username}' if key.username != "" else "") +
                  (' | admin key' if key.admin_priv else "") + (f' | {key.region}' if key.region != "" else "") +
                  (f' | alt regions - {key.alt_regions}' if key.alt_regions else "") +
                  (' | LOGGED KEY' if key.logged is True else ""))

    if needs_setup_keys:
        print(f"\nValidated {len(needs_setup_keys)} AWS keys that failed to invoke Claude and need further permissions setup. Keys without a region displayed do not have the models setup and need to do so")
        for key in needs_setup_keys:
            print(f'{key.api_key}' + (f' | {key.username}' if key.username != "" else "") +
                  (' | admin key' if key.admin_priv else "") + (f' | {key.region}' if key.region != "" else ""))

    if useless_keys:
        print(f"\nValidated {len(useless_keys)} AWS keys that are deemed useless and most likely s3 slop (can't be used to setup Bedrock/Claude)")
        for key in useless_keys:
            print(f'{key.api_key}' + (f' | {key.username}' if key.username != "" else "")
                  + (f' | REASON - {key.useless_reasons}' if len(key.useless_reasons) > 1 else ''))
    print(f'\n--- Total Valid RPable AWS Keys: {len(keys) - len(useless_keys)} ({admin_count} with admin priv) ---\n')
