import APIKey
import json
import vertexai
from google.cloud import aiplatform
from google.oauth2 import service_account
import google.api_core.exceptions
from vertexai.language_models import TextGenerationModel


location = 'us-central1'  # location doesn't matter unlike azure/aws


def check_vertexai(key: APIKey):
    try:
        credentials = service_account.Credentials.from_service_account_file(key.api_key)
        with open(key.api_key, 'r') as file:
            data = json.load(file)
        if data.get('type') != 'service_account':
            return

        project_id = data.get('project_id')
        if not project_id:
            return
        key.project_id = project_id

        aiplatform.init(credentials=credentials, location=location, project=key.project_id)
        test_model_response(key, credentials)

    except google.api_core.exceptions.InvalidArgument:
        key.api_key = f'"{key.api_key}"'
        return True  # if we get to the stage where google yells at us for a bad parameter, 99% sure the key works.
    except Exception as e:
        return


def test_model_response(key: APIKey, credentials):
    vertexai.init(project=key.project_id, location=location, credentials=credentials)
    model = TextGenerationModel.from_pretrained("text-bison@002")
    model.predict("bweh", **{"temperature": 0.1, "max_output_tokens": 0})


def pretty_print_vertexai_keys(keys):
    print('-' * 90)
    print(f'Validated {len(keys)} Google Vertex AI keys:')
    for key in keys:
        print(f'{key.api_key} | {key.project_id}')
    print(f'\n--- Total Valid Google Vertex AI Keys: {len(keys)} ---\n')
