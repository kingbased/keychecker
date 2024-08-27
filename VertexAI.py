import asyncio
import APIKey
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

location = 'us-east5'
model = 'claude-3-opus@20240229'


async def check_vertexai(key: APIKey, session):
    try:
        with open(key.api_key, 'r') as file:
            data = json.load(file)
        if data.get('type') != 'service_account':
            return

        project_id = data.get('project_id')
        if not project_id:
            return
        key.project_id = project_id

        credentials = service_account.Credentials.from_service_account_file(
            key.api_key,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        credentials.refresh(Request())

        key.has_opus = await test_model_response(key, credentials.token, session)
        return True

    except Exception:
        return


async def test_model_response(key: APIKey, access_token, session):
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{key.project_id}/locations/{location}/publishers/anthropic/models/{model}:rawPredict"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    data = {
        "anthropic_version": "vertex-2023-10-16",
        "messages": [
            {'role': 'user', 'content': ''}
        ],
        "max_tokens": 0,
    }

    for i in range(5):
        try:
            async with session.post(url, headers=headers, json=data) as response:
                resp = await response.json()
                if response.status == 429:
                    print(f"Rate limited on vertexai model response, retrying in 5 seconds (attempt {i} of 5)")
                    await asyncio.sleep(5)
                    continue
                # returned on non enabled models afaik, couldn't test on the anthropic models though since they're all enabled on my service account
                elif response.status == 400 and resp.get('error', {}).get('status') == 'FAILED_PRECONDITION':
                    return False
                elif response.status == 400 and resp.get('error', {}).get('type') == 'invalid_request_error':
                    return True
                else:
                    return False
        except Exception as e:
            print(f"Error testing model response: {str(e)}")
            return False


def pretty_print_vertexai_keys(keys):
    print('-' * 90)
    print(f'Validated {len(keys)} Google Vertex AI keys:')

    keys_with_opus = [key for key in keys if key.has_opus]
    keys_without_opus = [key for key in keys if not key.has_opus]

    print(f'\nValid keys with Opus enabled: {len(keys_with_opus)}')
    for key in keys_with_opus:
        print(f'{key.api_key} | {key.project_id} | has opus')

    print(f'\nValid keys without Opus enabled: {len(keys_without_opus)}')
    for key in keys_without_opus:
        print(f'{key.api_key} | {key.project_id}')

    print(f'\n--- Total Valid Google Vertex AI Keys: {len(keys)} ({len(keys_with_opus)} with Opus enabled) ---\n')
