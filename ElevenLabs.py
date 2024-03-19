import APIKey


async def check_elevenlabs(key: APIKey, session):
    async with session.get('https://api.elevenlabs.io/v1/user/subscription', headers={'xi-api-key': key.api_key}) as response:
        if response.status != 200:
            return
        response = await response.json()
        try:
            key.characters_left = int(response['character_limit']) - int(response['character_count'])
            next_invoice = response['next_invoice']
            tier_pricing = [33000, 9900, 2200, 500]
            key.usage = "${:.2f}".format(int(next_invoice['amount_due_cents']) / 100) if next_invoice and int(next_invoice['amount_due_cents']) not in tier_pricing else ''
            key.tier = response['tier']
            key.unlimited = response['can_extend_character_limit'] and response['allowed_to_extend_character_limit']
            if response['can_use_professional_voice_cloning']:
                key.pro_voice_limit = int(response['professional_voice_limit'])
        except (KeyError, ValueError):
            return
        return True


def pretty_print_elevenlabs_keys(keys):
    keys_by_tier = {}
    for key in keys:
        if key.tier not in keys_by_tier:
            keys_by_tier[key.tier] = []
        keys_by_tier[key.tier].append(key)

    tier_order = ['growing_business', 'pro', 'creator', 'starter', 'free']

    print('-' * 90)
    print(f'Validated {len(keys)} ElevenLabs keys:')
    for tier in tier_order:
        if tier in keys_by_tier:
            keys_in_tier = sorted(keys_by_tier[tier], key=lambda x: x.characters_left, reverse=True)
            print(f'\n{len(keys_in_tier)} keys found in {tier} tier:')
            for key in keys_in_tier:
                print(f'{key.api_key} | {key.characters_left} characters remaining' + (' | !!!unlimited quota!!!' if key.unlimited else '')
                      + (f' | plan limit exceeded - next invoice {key.usage}' if key.usage else '')
                      + (f' | pro voice cloning limit of {key.pro_voice_limit}' if key.pro_voice_limit else ''))
    print(f'\n--- Total Valid ElevenLabs Keys: {len(keys)} ---\n')
