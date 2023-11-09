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


class Provider(Enum):
    OPENAI = 1,
    ANTHROPIC = 2
    AI21 = 3
    PALM = 4
