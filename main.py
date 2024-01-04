from time import sleep
from Anthropic import check_anthropic, pretty_print_anthropic_keys
from IO import IO
from OpenAI import get_oai_model, get_oai_key_attribs, get_oai_org, pretty_print_oai_keys
from AI21 import check_ai21, pretty_print_ai21_keys
from MakerSuite import check_makersuite, pretty_print_makersuite_keys
from AWS import check_aws, pretty_print_aws_keys
from Azure import check_azure, pretty_print_azure_keys
from VertexAI import check_vertexai, pretty_print_vertexai_keys
from Mistral import check_mistral, pretty_print_mistral_keys

from APIKey import APIKey, Provider
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from datetime import datetime
import re
import argparse
import os.path

api_keys = set()


def parse_args():
    parser = argparse.ArgumentParser(description='slop checker')
    parser.add_argument('-nooutput', '--nooutput', action='store_true', help='stop writing slop to a file')
    parser.add_argument('-proxyoutput', '--proxyoutput', action='store_true', help='proxy format output for easy copying')
    parser.add_argument('-file', '--file', action='store', dest='file', help='read slop from a provided filename')
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


def validate_openai(key: APIKey):
    if get_oai_model(key) is None:
        return
    if get_oai_key_attribs(key) is None:
        return
    if get_oai_org(key) is None:
        return
    api_keys.add(key)


def validate_anthropic(key: APIKey, retry_count):
    key_status = check_anthropic(key)
    if key_status is None:
        return
    elif key_status is False:
        i = 0
        while check_anthropic(key) is False and i < retry_count:
            i += 1
            sleep(1)
            print(f"Stuck determining pozzed status of rate limited Anthropic key '{key.api_key[-8:]}' - attempt {i} of {retry_count}")
            key.rate_limited = True
        else:
            if i < retry_count:
                key.rate_limited = False
    api_keys.add(key)


def validate_ai21_and_mistral(key: APIKey):
    if check_ai21(key) is None:
        key.provider = Provider.MISTRAL
        if check_mistral(key) is None:
            return
    api_keys.add(key)


def validate_makersuite(key: APIKey):
    if check_makersuite(key) is None:
        return
    api_keys.add(key)


def validate_aws(key: APIKey):
    if check_aws(key) is None:
        return
    api_keys.add(key)


def validate_azure(key: APIKey):
    if check_azure(key) is None:
        return
    api_keys.add(key)


def validate_vertexai(key: APIKey):
    if check_vertexai(key) is None:
        return
    api_keys.add(key)


oai_regex = re.compile('(sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20})')
anthropic_regex = re.compile(r'sk-ant-api03-[A-Za-z0-9\-_]{93}AA')
ai21_and_mistral_regex = re.compile('[A-Za-z0-9]{32}')
makersuite_regex = re.compile(r'AIzaSy[A-Za-z0-9\-_]{33}')
aws_regex = re.compile(r'^(AKIA[0-9A-Z]{16}):([A-Za-z0-9+/]{40})$')
azure_regex = re.compile(r'^(.+):([a-z0-9]{32})$')
# vertex_regex = re.compile(r'^(.+):(ya29.[A-Za-z0-9\-_]{469})$') regex for the oauth tokens, useless since they expire hourly

executor = ThreadPoolExecutor(max_workers=100)


def validate_keys():
    futures = []
    for key in inputted_keys:
        if '"' in key[:1]:
            key = key.strip('"')
            if not os.path.isfile(key):
                continue
            key_obj = APIKey(Provider.VERTEXAI, key)
            futures.append(executor.submit(validate_vertexai, key_obj))
        elif "ant-api03" in key:
            match = anthropic_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.ANTHROPIC, key)
            futures.append(executor.submit(validate_anthropic, key_obj, 20))
        elif "AIzaSy" in key[:6]:
            match = makersuite_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.MAKERSUITE, key)
            futures.append(executor.submit(validate_makersuite, key_obj))
        elif "sk-" in key:
            match = oai_regex.match(key)
            if not match:
                continue
            key_obj = APIKey(Provider.OPENAI, key)
            futures.append(executor.submit(validate_openai, key_obj))
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
            futures.append(executor.submit(validate_ai21_and_mistral, key_obj))
    for _ in as_completed(futures):
        pass

    futures.clear()


def get_invalid_keys(valid_oai_keys, valid_anthropic_keys, valid_ai21_keys, valid_makersuite_keys, valid_aws_keys, valid_azure_keys, valid_vertexai_keys, valid_mistral_keys):
    valid_oai_keys_set = set([key.api_key for key in valid_oai_keys])
    valid_anthropic_keys_set = set([key.api_key for key in valid_anthropic_keys])
    valid_ai21_keys_set = set([key.api_key for key in valid_ai21_keys])
    valid_makersuite_keys_set = set([key.api_key for key in valid_makersuite_keys])
    valid_aws_keys_set = set([key.api_key for key in valid_aws_keys])
    valid_azure_keys_set = set([key.api_key for key in valid_azure_keys])
    valid_vertexai_keys_set = set([key.api_key for key in valid_vertexai_keys])
    valid_mistral_keys_set = set([key.api_key for key in valid_mistral_keys])

    invalid_keys = inputted_keys - valid_oai_keys_set - valid_anthropic_keys_set - valid_ai21_keys_set - valid_makersuite_keys_set - valid_aws_keys_set - valid_azure_keys_set - valid_vertexai_keys_set - valid_mistral_keys_set
    if len(invalid_keys) < 1:
        return
    print('\nInvalid Keys:')
    for key in invalid_keys:
        print(key)


def output_keys():
    should_write = not args.nooutput and not args.proxyoutput
    validate_keys()
    valid_oai_keys = []
    valid_anthropic_keys = []
    valid_ai21_keys = []
    valid_makersuite_keys = []
    valid_aws_keys = []
    valid_azure_keys = []
    valid_vertexai_keys = []
    valid_mistral_keys = []

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
    if should_write:
        output_filename = "key_snapshots.txt"
        sys.stdout = IO(output_filename)

    if not args.proxyoutput:
        print("#" * 90)
        print(f"Key snapshot from {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#" * 90)
        print(f'\n--- Checked {len(inputted_keys)} keys | {len(inputted_keys) - len(api_keys)} were invalid ---')
        get_invalid_keys(valid_oai_keys, valid_anthropic_keys, valid_ai21_keys, valid_makersuite_keys, valid_aws_keys, valid_azure_keys, valid_vertexai_keys, valid_mistral_keys)
        print()
        if valid_oai_keys:
            pretty_print_oai_keys(valid_oai_keys)
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
    else:
        # ai21 and vertex keys aren't supported in proxies so no point outputting them, filtered azure keys should be excluded.
        print("OPENAI_KEY=" + ','.join(key.api_key for key in valid_oai_keys))
        print("ANTHROPIC_KEY=" + ','.join(key.api_key for key in valid_anthropic_keys))
        print("AWS_CREDENTIALS=" + ','.join(f"{key.api_key}:{key.region}" for key in valid_aws_keys if not key.useless))
        print("GOOGLE_AI_KEY=" + ','.join(key.api_key for key in valid_makersuite_keys))
        print("AZURE_CREDENTIALS=" + ','.join(f"{key.api_key.split(':')[0]}:{key.best_deployment}:{key.api_key.split(':')[1]}" for key in valid_azure_keys if key.unfiltered))
        print("MISTRAL_AI_KEY=" + ','.join(key.api_key for key in valid_mistral_keys))
    if should_write:
        sys.stdout.file.close()


if __name__ == "__main__":
    output_keys()
