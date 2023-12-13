import requests
import APIKey


def check_makersuite(key: APIKey):
    response = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key.api_key}")
    if response.status_code != 200:
        return
    return True


def pretty_print_makersuite_keys(keys):
    print('-' * 90)
    print(f'Validated {len(keys)} MakerSuite keys:')
    for key in keys:
        print(f'{key.api_key}')
    print(f'\n--- Total Valid MakerSuite Keys: {len(keys)} ---\n')
