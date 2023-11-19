import json
import boto3
import APIKey
import botocore.exceptions


aws_regions = [
    "us-east-2",
    "us-east-1",
    "us-west-1",
    "us-west-2",
    "af-south-1",
    "ap-east-1",
    "ap-south-2",
    "ap-southeast-3",
    "ap-southeast-4",
    "ap-south-1",
    "ap-northeast-3",
    "ap-northeast-2",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-northeast-1",
    "ca-central-1",
    "eu-central-1",
    "eu-west-1",
    "eu-west-2",
    "eu-south-1",
    "eu-west-3",
    "eu-south-2",
    "eu-north-1",
    "eu-central-2",
    "il-central-1",
    "me-south-1",
    "me-central-1",
    "sa-east-1"
]


def check_aws(key: APIKey):
    line = key.api_key.split(":")
    access_key = line[0]
    secret = line[1]

    try:
        session = boto3.Session(aws_access_key_id=access_key,aws_secret_access_key=secret)
        sts_client = session.client("sts")
        iam_client = session.client("iam")
        bedrock_runtime_client = session.client("bedrock-runtime")

        region = get_region(session)
        if region is not None:
            key.region = region
            # key.bedrock_enabled = True
            key.useless = False

        username = sts_client.get_caller_identity()['Arn'].split('/')[1]
        policies = iam_client.list_attached_user_policies(UserName=username)['AttachedPolicies']

        if username is not None:
            key.username = username

        can_invoke = check_default_bedrock_status(bedrock_runtime_client)
        if can_invoke is not None:
            key.bedrock_enabled = True
            key.useless = False

        if policies is None and region is None and can_invoke is None:
            return

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

        if key.useless:
            return
        return True

    except botocore.exceptions.ClientError as e:
        print({e})
        return


def get_region(session):
    for region in aws_regions:
        try:
            bedrock_client = session.client("bedrock", region_name=region)
            response = bedrock_client.list_foundation_models()
            cloudies = ['anthropic.claude-v1', 'anthropic.claude-v2']
            models = [model['modelId'] for model in response.get('modelSummaries', [])]
            if all(model_id in models for model_id in cloudies):
                return region
        except botocore.exceptions.ClientError as e:
            print(e)
            return


def check_default_bedrock_status(bedrock_runtime_client):
    data = {
        "prompt": "\n\nHuman:\n\nAssistant:",
        "max_tokens_to_sample": -1,
    }
    try:
        bedrock_runtime_client.invoke_model(body=json.dumps(data), modelId="anthropic.claude-instant-v1")
        return True
    except bedrock_runtime_client.exceptions.AccessDeniedException as e:
        print({e})
        return


def pretty_print_aws_keys(keys):
    print('-' * 90)
    admin_count = 0
    ready_to_go_keys = []
    needs_setup_keys = []

    for key in keys:
        if key.admin_priv:
            admin_count += 1
        if key.bedrock_enabled:
            ready_to_go_keys.append(key)
        else:
            needs_setup_keys.append(key)

    print(f"Validated {len(ready_to_go_keys)} AWS keys that are working and already have Bedrock setup.")
    for key in ready_to_go_keys:
        print(f'{key.api_key}' + (f' | {key.username}' if key.username != "" else "") +
              (' | admin key' if key.admin_priv else "") + (f' | {key.region}' if key.region != "" else ""))

    print(f"\nValidated {len(needs_setup_keys)} AWS keys that failed to invoke Claude and need further permissions setup. Keys without a region displayed do not have the models setup and need to do so")
    for key in needs_setup_keys:
        print(f'{key.api_key}' + (f' | {key.username}' if key.username != "" else "") +
              (' | admin key' if key.admin_priv else "") + (f' | {key.region}' if key.region != "" else ""))

    print(f'\n--- Total Valid AWS Keys: {len(keys)} ({admin_count} with admin priv) ---\n')