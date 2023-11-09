import requests
import APIKey


def check_palm(key: APIKey):
    response = requests.get(f"https://generativelanguage.googleapis.com/v1beta2/models?key={key.api_key}")
    if response.status_code != 200:
        return
    return True


def pretty_print_palm_keys(keys):
    print('-' * 90)
    print(f'Validated {len(keys)} PaLM keys:')
    for key in keys:
        print(f'{key.api_key}')
    print(f'\n--- Total Valid PaLM Keys: {len(keys)} ---\n')
