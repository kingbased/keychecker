import json
import requests

import APIKey

oai_api_url = "https://api.openai.com/v1"
oai_t1_rpm_limits = {"gpt-3.5-turbo": 3500, "gpt-4": 500, "gpt-4-32k": 20}
oai_tiers = {3: 'Tier1', 5: 'Tier2', 7: 'Tier3', 10: 'Tier4', 20: 'Tier5'}

def get_oai_model(key: APIKey):
    response = requests.get(f'{oai_api_url}/models', headers={'Authorization': f'Bearer {key.api_key}'})
    top_model = "gpt-3.5-turbo"
    if response.status_code != 200:
        return
    else:
        data = json.loads(response.text)
        models = data["data"]
        for model in models:
            if model["id"] == "gpt-4-32k":
                top_model = model["id"]
                break
            elif model["id"] == "gpt-4":
                top_model = model["id"]
    key.model = top_model
    return True


def get_oai_key_attribs(key: APIKey):
    chat_object = {"model": f'{key.model}', "messages": [{"role": "user", "content": ""}], "max_tokens": 0}
    response = requests.post(f'{oai_api_url}/chat/completions',
                             headers={'Authorization': f'Bearer {key.api_key}', 'accept': 'application/json'},
                             json=chat_object)
    if response.status_code in [400, 429]:
        data = json.loads(response.text)
        message = data["error"]["type"]
        if message is None:
            return
        match message:
            case "access_terminated":
                return
            case "billing_not_active":
                return
            case "insufficient_quota":
                key.has_quota = False
            case "invalid_request_error":
                key.has_quota = True
                key.rpm = int(response.headers.get("x-ratelimit-limit-requests"))
                if key.rpm < oai_t1_rpm_limits[key.model]:  # oddly seen some gpt4 trial keys
                    key.trial = True
                key.tier = get_oai_key_tier(key)
    else:
        return
    return True


# this will weed out fake t4/t5 keys reporting a 10k rpm limit, those keys would have requested to have their rpm increased
def get_oai_key_tier(key: APIKey):
    if key.trial:
        return 'Free'
    tts_object = {"model": "tts-1-hd", "input": "", "voice": "alloy"}
    response = requests.post(f'{oai_api_url}/audio/speech',
                             headers={'Authorization': f'Bearer {key.api_key}', 'accept': 'application/json'},
                             json=tts_object)
    if response.status_code in [400, 429]:
        try:
            return oai_tiers[int(response.headers.get("x-ratelimit-limit-requests"))]
        except KeyError:
            return
    else:
        return


def get_oai_org(key: APIKey):
    response = requests.get(f'{oai_api_url}/organizations', headers={'Authorization': f'Bearer {key.api_key}'})
    if response.status_code != 200:
        return

    data = json.loads(response.text)
    orgs = data["data"]

    for org in orgs:
        if not org["personal"]:
            if org["is_default"]:
                key.default_org = org["name"]
            key.organizations.append(org["name"])
    return True


def check_manual_increase(key: APIKey):
    if key.model == 'gpt-3.5-turbo' and key.rpm > 3500:
        return True
    elif key.tier == 'Tier1' and key.model != 'gpt-3.5-turbo' and key.rpm > 500:
        return True
    elif key.tier in ['Tier2', 'Tier3'] and key.rpm > 5000:
        return True
    elif key.tier in ['Tier3', 'Tier4'] and key.rpm > 10000:
        return True
    return False


def pretty_print_oai_keys(keys):
    print('-' * 90)
    org_count = 0
    quota_count = 0
    no_quota_count = 0
    t5_count = 0

    key_groups = {
        "gpt-3.5-turbo": {
            "has_quota": [],
            "no_quota": []
        },
        "gpt-4": {
            "has_quota": [],
            "no_quota": []
        },
        "gpt-4-32k": {
            "has_quota": [],
            "no_quota": []
        }
    }

    for key in keys:
        if key.organizations:
            org_count += 1
        if key.tier == 'Tier5':
            t5_count += 1
        if key.has_quota:
            key_groups[key.model]['has_quota'].append(key)
            quota_count += 1
        else:
            key_groups[key.model]['no_quota'].append(key)
            no_quota_count += 1

    print(f'Validated {len(key_groups["gpt-3.5-turbo"]["has_quota"])} Turbo keys with quota:')
    for key in key_groups["gpt-3.5-turbo"]["has_quota"]:
        print(f"{key.api_key}"
              + (f" | default org - {key.default_org}" if key.default_org else "")
              + (f" | other orgs - {key.organizations}" if len(key.organizations) > 1 else "")
              + f" | {key.rpm} RPM" + (f" - {key.tier}" if key.tier else "")
              + (" (RPM increased via request)" if check_manual_increase(key) else "")
              + (f" | TRIAL KEY" if key.trial else ""))

    print(f'\nValidated {len(key_groups["gpt-3.5-turbo"]["no_quota"])} Turbo keys with no quota:')
    for key in key_groups["gpt-3.5-turbo"]["no_quota"]:
        print(f"{key.api_key}"
              + (f" | default org - {key.default_org}" if key.default_org else "")
              + (f" | other orgs - {key.organizations}" if len(key.organizations) > 1 else ""))

    print(f'\nValidated {len(key_groups["gpt-4"]["has_quota"])} gpt-4 keys with quota:')
    for key in key_groups["gpt-4"]["has_quota"]:
        print(f"{key.api_key}"
              + (f" | default org - {key.default_org}" if key.default_org else "")
              + (f" | other orgs - {key.organizations}" if len(key.organizations) > 1 else "")
              + f" | {key.rpm} RPM" + (f" - {key.tier}" if key.tier else "")
              + (" (RPM increased via request)" if check_manual_increase(key) else "")
              + (f" | TRIAL KEY" if key.trial else ""))

    print(f'\nValidated {len(key_groups["gpt-4"]["no_quota"])} gpt-4 keys with no quota:')
    for key in key_groups["gpt-4"]["no_quota"]:
        print(f"{key.api_key}"
              + (f" | default org - {key.default_org}" if key.default_org else "")
              + (f" | other orgs - {key.organizations}" if len(key.organizations) > 1 else ""))

    print(f'\nValidated {len(key_groups["gpt-4-32k"]["has_quota"])} gpt-4-32k keys with quota:')
    for key in key_groups["gpt-4-32k"]["has_quota"]:
        print(f"{key.api_key}"
              + (f" | default org - {key.default_org}" if key.default_org else "")
              + (f" | other orgs - {key.organizations}" if len(key.organizations) > 1 else "")
              + f" | {key.rpm} RPM" + (f" - {key.tier}" if key.tier else "")
              + (" (RPM increased via request)" if check_manual_increase(key) else "")
              + (f" | TRIAL KEY" if key.trial else ""))

    print(f'\nValidated {len(key_groups["gpt-4-32k"]["no_quota"])} gpt-4-32k keys with no quota:')
    for key in key_groups["gpt-4-32k"]["no_quota"]:
        print(f"{key.api_key}"
              + (f" | default org - {key.default_org}" if key.default_org else "")
              + (f" | other orgs - {key.organizations}" if len(key.organizations) > 1 else ""))

    print(f'\n--- Total Valid OpenAI Keys: {len(keys)} ({quota_count} in quota, {no_quota_count} no quota, {org_count} orgs, {t5_count} Tier5) ---\n')
