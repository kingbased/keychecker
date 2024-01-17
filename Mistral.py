import aiohttp
import APIKey


async def check_mistral(key: APIKey):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://api.mistral.ai/v1/models', headers={'Authorization': f'Bearer {key.api_key}'}) as response:
            if response.status != 200:
                return
            key.subbed = await check_sub_status(key, session)
            return True


async def check_sub_status(key: APIKey, session):
    data = {
        'model': 'mistral-tiny',
        'messages': [{'role': 'user', 'content': ''}],
        'max_tokens': 1
    }
    async with session.post(f'https://api.mistral.ai/v1/chat/completions', headers={'Authorization': f'Bearer {key.api_key}'}, json=data) as response:
        if response.status == 401 or response.status == 429:
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