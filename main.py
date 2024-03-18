from Anthropic import check_anthropic, pretty_print_anthropic_keys
from IO import IO
from OpenAI import get_oai_model, get_oai_key_attribs, get_oai_org, pretty_print_oai_keys, clone_key
from AI21 import check_ai21, pretty_print_ai21_keys
from MakerSuite import check_makersuite, pretty_print_makersuite_keys
from AWS import check_aws, pretty_print_aws_keys
from Azure import check_azure, pretty_print_azure_keys
from VertexAI import check_vertexai, pretty_print_vertexai_keys
from Mistral import check_mistral, pretty_print_mistral_keys
from OpenRouter import check_openrouter, pretty_print_openrouter_keys

from APIKey import APIKey, Provider
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from datetime import datetime
import re
import argparse
import os.path
import asyncio
import aiohttp

api_keys = set()


def parse_args():
    parser = argparse.ArgumentParser(description='slop checker')
    parser.add_argument('-nooutput', '--nooutput', action='store_true', help='stop writing slop to a file')
    parser.add_argument('-proxyoutput', '--proxyoutput', action='store_true', help='proxy format output for easy copying')
    parser.add_argument('-file', '--file', action='store', dest='file', help='read slop from a provided filename')
    parser.add_argument('-verbose', '--verbose', action='store_true', help='watch as your slop is checked real time')
    return parser.parse_args()


args = parse_args()
inputted_keys = set()

if args.file:
    inputted_keys = IO.read_keys_from_file(args.file)
    if inputted_keys is None:
        sys.exit(1)
else:
    print('Enter API keys (OpenAI/Anthropic/AI21/MakerSuite/AWS/Azure/Mistral) one per line. Press Enter on a blank line to start validation')
    print('Expected format for AWS keys is accesskey:secret, for Azure keys it\'s resourcegroup:apikey. For Vertex AI keys the absolute path to the secrets key file is expected in quotes. "/path/to/secrets.json"')
    while True:
        current_line = input()
        if not current_line:
            print("Starting validation...")
            break
        inputted_keys.add(current_line.strip().split()[0].split(",")[0])


# hold on let me land
cloned_keys = None
async def validate_openai(key: APIKey, sem):
    retries = 10
    async with sem, aiohttp.ClientSession() as session:
        IO.conditional_print(f"Checking OpenAI key: {key.api_key}", args.verbose)
        if await get_oai_model(key, session, retries) is None:
            IO.conditional_print(f"Invalid OpenAI key: {key.api_key}", args.verbose)
            return
        if await get_oai_key_attribs(key, session, retries) is None:
            return
        if await get_oai_org(key, session, retries) is None:
            return
        IO.conditional_print(f"OpenAI key '{key.api_key}' is valid", args.verbose)
        api_keys.add(key)
        global cloned_keys
        cloned_keys = await clone_key(key, session, retries)
        if cloned_keys:
            IO.conditional_print(f"Cloned OpenAI key '{key.api_key}'", args.verbose)
            api_keys.update(cloned_keys)


async def validate_anthropic(key: APIKey, retry_count, sem):
    async with sem, aiohttp.ClientSession() as session:
        IO.conditional_print(f"Checking Anthropic key: {key.api_key}", args.verbose)
        key_status = await check_anthropic(key, session)
        if key_status is None:
            IO.conditional_print(f"Invalid Anthropic key: {key.api_key}", args.verbose)
            return
        elif key_status is False:
            i = 0
            while await check_anthropic(key, session) is False and i < retry_count:
                i += 1
                await asyncio.sleep(1)
                print(f"Stuck determining pozzed status of rate limited Anthropic key '{key.api_key[-8:]}' - attempt {i} of {retry_count}")
                key.rate_limited = True
            else:
                if i < retry_count:
                    key.rate_limited = False
        IO.conditional_print(f"Anthropic key '{key.api_key}' is valid", args.verbose)
        api_keys.add(key)


async def validate_ai21_and_mistral(key: APIKey, sem):
    async with sem, aiohttp.ClientSession() as session:
        IO.conditional_print(f"Checking AI21 key: {key.api_key}", args.verbose)
        if await check_ai21(key, session) is None:
            IO.conditional_print(f"Invalid AI21 key: {key.api_key}, checking provider Mistral", args.verbose)
            key.provider = Provider.MISTRAL
            if await check_mistral(key, session) is None:
                IO.conditional_print(f"Invalid Mistral key: {key.api_key}", args.verbose)
                return
        IO.conditional_print(f"{'AI21' if key.provider == Provider.AI21 else 'Mistral'} key '{key.api_key}' is valid", args.verbose)
        api_keys.add(key)


async def validate_makersuite(key: APIKey, sem):
    async with sem, aiohttp.ClientSession() as session:
        IO.conditional_print(f"Checking MakerSuite key: {key.api_key}", args.verbose)
        if await check_makersuite(key, session) is None:
            IO.conditional_print(f"Invalid MakerSuite key: {key.api_key}", args.verbose)
            return
        IO.conditional_print(f"MakerSuite key '{key.api_key}' is valid", args.verbose)
        api_keys.add(key)


async def validate_openrouter(key: APIKey, sem):
    async with sem, aiohttp.ClientSession() as session:
        IO.conditional_print(f"Checking OpenRouter: {key.api_key}", args.verbose)
        if await check_openrouter(key, session) is None:
            IO.conditional_print(f"Invalid OpenRouter key: {key.api_key}", args.verbose)
            return
        IO.conditional_print(f"OpenRouter key '{key.api_key}' is valid", args.verbose)
        api_keys.add(key)


def validate_aws(key: APIKey):
    IO.conditional_print(f"Checking AWS key: {key.api_key}", args.verbose)
    if check_aws(key) is None:
        IO.conditional_print(f"Invalid AWS key: {key.api_key}", args.verbose)
        return
    IO.conditional_print(f"AWS key '{key.api_key}' is valid", args.verbose)
    api_keys.add(key)


def validate_azure(key: APIKey):
    IO.conditional_print(f"Checking Azure key: {key.api_key}", args.verbose)
    if check_azure(key) is None:
        IO.conditional_print(f"Invalid Azure key: {key.api_key}", args.verbose)
        return
    IO.conditional_print(f"Azure key '{key.api_key}' is valid", args.verbose)
    api_keys.add(key)


def validate_vertexai(key: APIKey):
    IO.conditional_print(f"Checking Vertex AI keyfile: {key.api_key}", args.verbose)
    if check_vertexai(key) is None:
        IO.conditional_print(f"Invalid Vertex AI keyfile: {key.api_key}", args.verbose)
        return
    IO.conditional_print(f"Vertex AI keyfile '{key.api_key}' is valid", args.verbose)
    api_keys.add(key)


oai_regex = re.compile('(sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20})')
anthropic_regex = re.compile(r'sk-ant-api03-[A-Za-z0-9\-_]{93}AA')
anthropic_secondary_regex = re.compile(r'sk-ant-[A-Za-z0-9\-_]{86}')
ai21_and_mistral_regex = re.compile('[A-Za-z0-9]{32}')
makersuite_regex = re.compile(r'AIzaSy[A-Za-z0-9\-_]{33}')
aws_regex = re.compile(r'^(AKIA[0-9A-Z]{16}):([A-Za-z0-9+/]{40})$')
azure_regex = re.compile(r'^(.+):([a-z0-9]{32})$')
openrouter_regex = re.compile(r'sk-or-v1-[a-z0-9]{64}')
# vertex_regex = re.compile(r'^(.+):(ya29.[A-Za-z0-9\-_]{469})$') regex for the oauth tokens, useless since they expire hourly
executor = ThreadPoolExecutor(max_workers=100)
concurrent_connections = asyncio.Semaphore(1500)


async def validate_keys():
    tasks = []
    futures = []
    for key in inputted_keys:
        if '"' in key[:1]:
            key = key.strip('"')
            if not os.path.isfile(key):
                continue
            key_obj = APIKey(Provider.VERTEXAI, key)
            futures.append(executor.submit(validate_vertexai, key_obj))
        elif "sk-ant-" in key[:7]:
            match = anthropic_regex.match(key) if "ant-api03" in key else anthropic_secondary_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.ANTHROPIC, key)
            tasks.append(validate_anthropic(key_obj, 20, concurrent_connections))
        elif "AIzaSy" in key[:6]:
            match = makersuite_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.MAKERSUITE, key)
            tasks.append(validate_makersuite(key_obj, concurrent_connections))
        elif "sk-or-v1-" in key:
            match = openrouter_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.OPENROUTER, key)
            tasks.append(validate_openrouter(key_obj, concurrent_connections))
        elif "sk-" in key:
            match = oai_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.OPENAI, key)
            tasks.append(validate_openai(key_obj, concurrent_connections))
        elif ":" and "AKIA" in key:
            match = aws_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.AWS, key)
            futures.append(executor.submit(validate_aws, key_obj))
        elif ":" in key and "AKIA" not in key:
            match = azure_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.AZURE, key)
            futures.append(executor.submit(validate_azure, key_obj))
        else:
            match = ai21_and_mistral_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.AI21, key)
            tasks.append(validate_ai21_and_mistral(key_obj, concurrent_connections))
    results = await asyncio.gather(*tasks)
    for result in results:
        if result is not None:
            api_keys.add(result)

    for _ in as_completed(futures):
        pass
    futures.clear()


def get_invalid_keys(valid_oai_keys, valid_anthropic_keys, valid_ai21_keys, valid_makersuite_keys, valid_aws_keys, valid_azure_keys, valid_vertexai_keys, valid_mistral_keys, valid_openrouter_keys):
    valid_oai_keys_set = set([key.api_key for key in valid_oai_keys])
    valid_anthropic_keys_set = set([key.api_key for key in valid_anthropic_keys])
    valid_ai21_keys_set = set([key.api_key for key in valid_ai21_keys])
    valid_makersuite_keys_set = set([key.api_key for key in valid_makersuite_keys])
    valid_aws_keys_set = set([key.api_key for key in valid_aws_keys])
    valid_azure_keys_set = set([key.api_key for key in valid_azure_keys])
    valid_vertexai_keys_set = set([key.api_key for key in valid_vertexai_keys])
    valid_mistral_keys_set = set([key.api_key for key in valid_mistral_keys])
    valid_openrouter_keys_set = set([key.api_key for key in valid_openrouter_keys])

    invalid_keys = inputted_keys - valid_oai_keys_set - valid_anthropic_keys_set - valid_ai21_keys_set - valid_makersuite_keys_set - valid_aws_keys_set - valid_azure_keys_set - valid_vertexai_keys_set - valid_mistral_keys_set - valid_openrouter_keys_set
    invalid_keys_len = len(invalid_keys) + len(cloned_keys) if cloned_keys else len(invalid_keys)
    if invalid_keys_len < 1:
        return
    print('\nInvalid Keys:')
    for key in invalid_keys:
        print(key)


def output_keys():
    should_write = not args.nooutput and not args.proxyoutput
    asyncio.run(validate_keys())
    valid_oai_keys = []
    valid_anthropic_keys = []
    valid_ai21_keys = []
    valid_makersuite_keys = []
    valid_aws_keys = []
    valid_azure_keys = []
    valid_vertexai_keys = []
    valid_mistral_keys = []
    valid_openrouter_keys = []

    for key in api_keys:
        if key.provider == Provider.OPENAI:
            valid_oai_keys.append(key)
        elif key.provider == Provider.ANTHROPIC:
            valid_anthropic_keys.append(key)
        elif key.provider == Provider.AI21:
            valid_ai21_keys.append(key)
        elif key.provider == Provider.MAKERSUITE:
            valid_makersuite_keys.append(key)
        elif key.provider == Provider.AWS:
            valid_aws_keys.append(key)
        elif key.provider == Provider.AZURE:
            valid_azure_keys.append(key)
        elif key.provider == Provider.VERTEXAI:
            valid_vertexai_keys.append(key)
        elif key.provider == Provider.MISTRAL:
            valid_mistral_keys.append(key)
        elif key.provider == Provider.OPENROUTER:
            valid_openrouter_keys.append(key)
    if should_write:
        output_filename = "key_snapshots.txt"
        sys.stdout = IO(output_filename)

    if not args.proxyoutput:
        invalid_keys = len(inputted_keys) - len(api_keys) + len(cloned_keys) if cloned_keys else len(inputted_keys) - len(api_keys)
        print("#" * 90)
        print(f"Key snapshot from {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#" * 90)
        print(f'\n--- Checked {len(inputted_keys)} keys | {invalid_keys} were invalid ---')
        get_invalid_keys(valid_oai_keys, valid_anthropic_keys, valid_ai21_keys, valid_makersuite_keys, valid_aws_keys, valid_azure_keys, valid_vertexai_keys, valid_mistral_keys, valid_openrouter_keys)
        print()
        if valid_oai_keys:
            pretty_print_oai_keys(valid_oai_keys, cloned_keys)
        if valid_anthropic_keys:
            pretty_print_anthropic_keys(valid_anthropic_keys)
        if valid_ai21_keys:
            pretty_print_ai21_keys(valid_ai21_keys)
        if valid_makersuite_keys:
            pretty_print_makersuite_keys(valid_makersuite_keys)
        if valid_aws_keys:
            pretty_print_aws_keys(valid_aws_keys)
        if valid_azure_keys:
            pretty_print_azure_keys(valid_azure_keys)
        if valid_vertexai_keys:
            pretty_print_vertexai_keys(valid_vertexai_keys)
        if valid_mistral_keys:
            pretty_print_mistral_keys(valid_mistral_keys)
        if valid_openrouter_keys:
            pretty_print_openrouter_keys(valid_openrouter_keys)
    else:
        # ai21, openrouter and vertex keys aren't supported in proxies so no point outputting them, filtered azure keys should be excluded.
        print("OPENAI_KEY=" + ','.join(key.api_key for key in valid_oai_keys))
        print("ANTHROPIC_KEY=" + ','.join(key.api_key for key in valid_anthropic_keys))
        print("AWS_CREDENTIALS=" + ','.join(f"{key.api_key}:{region}" for key in valid_aws_keys if not key.useless and key.bedrock_enabled for region in [key.region] + key.alt_regions))
        print("GOOGLE_AI_KEY=" + ','.join(key.api_key for key in valid_makersuite_keys))
        print("AZURE_CREDENTIALS=" + ','.join(f"{key.api_key.split(':')[0]}:{key.best_deployment}:{key.api_key.split(':')[1]}" for key in valid_azure_keys if key.unfiltered))
        print("MISTRAL_AI_KEY=" + ','.join(key.api_key for key in valid_mistral_keys))
    if should_write:
        sys.stdout.file.close()
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    start_time = datetime.now()
    output_keys()
    elapsed_time = datetime.now() - start_time
    minutes, seconds = divmod(elapsed_time.total_seconds(), 60)
    print(f"Finished checking {len(inputted_keys)} keys in {f'{int(minutes)}m ' if minutes else ''}{seconds:.2f}s")
