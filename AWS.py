import boto3
import APIKey
import botocore.exceptions


def check_aws(key: APIKey):
    line = key.api_key.split(":")
    access_key = line[0]
    secret = line[1]

    try:
        session = boto3.Session(aws_access_key_id=access_key,aws_secret_access_key=secret)
        sts_client = session.client("sts")
        iam_client = session.client("iam")
        username = sts_client.get_caller_identity()['Arn'].split('/')[1]
        policies = iam_client.list_attached_user_policies(UserName=username)['AttachedPolicies']

        if username is not None:
            key.username = username
        print(f"Username: {username}")
        if policies is None:
            return

        for policy in policies:
            print(f"Key has policy: {policy}")
            if "AdministratorAccess" in policy["PolicyName"]:
                key.admin_priv = True
                key.useless = False
                break

            # should be a catch-all? idk haven't found a non slop key yet
            policy_ver = iam_client.get_policy(PolicyArn=policy['PolicyArn'])['Policy']['DefaultVersionId']
            policy_doc = iam_client.get_policy_version(PolicyArn=policy['PolicyArn'], VersionId=policy_ver)
            for statement in policy_doc['Statement']:
                if statement['Effect'] == 'Allow' and 'iam:CreateUser' in statement['Action']:
                    key.useless = False
                    continue

        if key.useless:
            return
        return True

    except botocore.exceptions.ClientError as e:
        print(f"error occurred: {e}")
        return


def pretty_print_aws_keys(keys):
    print('-' * 90)
    admin_count = 0
    print(f'Validated {len(keys)} working AWS keys:')
    for key in keys:
        if key.admin_priv:
            admin_count += 1
        print(f'{key.api_key}' + (' | admin' if key.admin_priv else ""))
    print(f'\n--- Total Valid AWS Keys: {len(keys)} ({admin_count} with admin priv) ---\n')
