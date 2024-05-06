import APIKey

gemini_models = ["gemini-1.0-pro", "gemini-1.5-pro", "gemini-1.0-ultra"]


async def check_makersuite(key: APIKey, session):
    async with session.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key.api_key}") as response:
        if response.status != 200:
            return
        response_json = await response.json()
        model_names = [model['name'].replace('models/', '').replace('-latest', '') for model in response_json['models']]
        for model in gemini_models:
            if model in model_names:
                key.models.append(model)
        return True


def pretty_print_makersuite_keys(keys):
    model_counts = {model: [] for model in gemini_models}
    total = 0
    for key in keys:
        for model in key.models:
            model_counts[model].append(key.api_key)
        total += 1

    print('-' * 90)
    print(f'Validated {len(keys)} MakerSuite keys:')
    for model, keys in model_counts.items():
        print(f'\n{len(keys)} keys with model {model}:')
        for key in keys:
            print(f'{key}')
    print(f'\n--- Total Valid MakerSuite Keys: {total} ---\n')
