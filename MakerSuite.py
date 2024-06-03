import APIKey

gemini_models = ["gemini-1.5-pro", "gemini-1.0-ultra"]


async def check_makersuite(key: APIKey, session):
    async with session.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key.api_key}") as response:
        if response.status != 200:
            return
        check_billing = await test_makersuite_billing(key, session)
        if not check_billing:
            return
        response_json = await response.json()
        model_names = [model['name'].replace('models/', '').replace('-latest', '') for model in response_json['models']]
        for model in gemini_models:
            if model in model_names:
                key.models.append(model)
        return True


# rpm limit of 2 on nonbilling keys is hit or miss for me, and rpm isn't returned in headers like oai/anthro so have to check it like this unfortunately.
# google will also start terminating generation requests on high key batches (40+), so the checker will output errors but recover and check fine still
async def test_makersuite_billing(key: APIKey, session):
    data = {
        "contents": {
            "role": "user",
            "parts": [
                {
                    "text": "test\n" * 32000
                }
            ]
        }
    }

    async with session.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={key.api_key}", json=data) as response:
        if response.status != 429:
            key.enabled_billing = True
        return True


def pretty_print_makersuite_keys(keys):
    model_counts = {model: [] for model in gemini_models}
    total = 0
    billing_count = 0

    for key in keys:
        for model in key.models:
            model_counts[model].append(key)
        total += 1
        if key.enabled_billing:
            billing_count += 1

    print('-' * 90)
    print(f'Validated {len(keys)} MakerSuite keys:')
    for model, keys in model_counts.items():
        print(f'\n{len(keys)} keys with model {model}:')
        sorted_keys = sorted(keys, key=lambda x: not x.enabled_billing)
        for key in sorted_keys:
            print(f'{key.api_key}' + (' | billing enabled' if key.enabled_billing else ''))
    print(f'\n--- Total Valid MakerSuite Keys: {total} ({billing_count} with billing enabled) ---\n')
