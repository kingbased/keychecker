from enum import Enum


class APIKey:
    def __init__(self, provider, api_key):
        self.provider = provider
        self.api_key = api_key

        if provider == Provider.OPENAI:
            self.model = ""
            self.trial = False
            self.has_quota = False
            self.default_org = ""
            self.organizations = []
            self.rpm = 0

        elif provider == Provider.ANTHROPIC:
            self.pozzed = False
            self.rate_limited = False

        elif provider == Provider.AI21:
            self.trial_elapsed = False

        elif provider == Provider.AWS:
            self.username = ""
            self.useless = True
            self.admin_priv = False
            self.bedrock_enabled = False
            self.region = ""
            self.useless_reasons = []
            self.logged = False

        elif provider == Provider.AZURE:
            self.endpoint = ""
            self.best_deployment = ""
            self.model = ""
            self.deployments = []
            self.unfiltered = False

        elif provider == Provider.VERTEXAI:
            self.project_id = ""

        elif provider == Provider.MISTRAL:
            self.subbed = False


class Provider(Enum):
    OPENAI = 1,
    ANTHROPIC = 2
    AI21 = 3
    MAKERSUITE = 4
    AWS = 5
    AZURE = 6
    VERTEXAI = 7
    MISTRAL = 8
