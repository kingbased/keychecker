import APIKey


async def check_makersuite(key: APIKey, session):
    async with session.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key.api_key}") as response:
        if response.status != 200:
            return
        return True


def pretty_print_makersuite_keys(keys):
    print('-' * 90)
    print(f'Validated {len(keys)} MakerSuite keys:')
    for key in keys:
        print(f'{key.api_key}')
    print(f'\n--- Total Valid MakerSuite Keys: {len(keys)} ---\n')
