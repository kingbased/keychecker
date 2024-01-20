import APIKey


async def check_ai21(key: APIKey, session):
    url = "https://api.ai21.com/studio/v1/j2-light/complete"

    payload = {
        "prompt": "a",
        "maxTokens": 1,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {key.api_key}"
    }

    async with session.post(url, json=payload, headers=headers) as response:
        if response.status not in [200, 402]:
            return

        if response.status == 402:  # unsure if this error code also applies to empty keys
            key.trial_elapsed = True

        return True


def pretty_print_ai21_keys(keys):
    print('-' * 90)
    dead = 0
    print(f'Validated {len(keys)} AI21 keys:')
    for key in keys:
        if key.trial_elapsed:
            dead += 1
        print(f'{key.api_key}' + (' | trial elapsed' if key.trial_elapsed else ""))
    print(f'\n--- Total Valid AI21 Keys: {len(keys)} ({dead} trial elapsed, {len(keys) - dead} still valid) ---\n')
