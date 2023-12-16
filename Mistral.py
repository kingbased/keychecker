import APIKey
import requests


def check_mistral(key: APIKey):
    response = requests.get(f'https://api.mistral.ai/v1/models', headers={'Authorization': f'Bearer {key.api_key}'})
    if response.status_code != 200:
        return
    key.subbed = check_sub_status(key)
    return True


def check_sub_status(key: APIKey):
    data = {
        'model': 'mistral-tiny',
        'messages': [{'role': 'user', 'content': ''}],
        'max_tokens': 0
    }
    response = requests.post(f'https://api.mistral.ai/v1/chat/completions', headers={'Authorization': f'Bearer {key.api_key}'}, json=data)
    if response.status_code == 401 or response.status_code == 429:
        return False
    return True


def pretty_print_mistral_keys(keys):
    print('-' * 90)
    subbed = 0
    print(f'Validated {len(keys)} Mistral keys:')
    for key in keys:
        if key.subbed:
            subbed += 1
        print(f'{key.api_key}' + (' | has sub active' if key.subbed else ''))
    print(f'\n--- Total Valid Mistral Keys: {len(keys)} ({subbed} with an active subscription) ---\n')