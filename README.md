# keychecker
a bulk key checker for various AI services

NOTE: OAI recently seems to be hard blocking requests when checking some number of keys in short succession, this has persisted despite using different IP's so it's not an IP ban. I have tested other keycheckers (kkc, OAI_API_Checker) and they also fail, or in the case of kkc, outright crash after 5 minutes. This keychecker should still work for OAI but expect it to take its time if you're running it on a decently sized load and have been throttled (possibly more than 10 minutes). If this isn't just a temporary issue on OAI's end and is in fact permenant, I will investigate further and work on a fix.

Currently supports and validates keys for the services below, and checks for the listed attributes a key might have:

- OpenAI - (Best model, key in quota, RPM (catches increase requests), tier, list of organizations if applicable, trial key status)
- Anthropic - (Pozzed check)
- AI21 - (Trial check)
- Google MakerSuite (Gemini)
- AWS - (Admin status, auto-fetch the region, logging status, username, bedrock status)
- Azure - (Auto-fetch all deployments, auto-fetch best deployment/model, filter status)
- Google Cloud Vertex AI - (Requires a key file since oauth tokens expire hourly. Good luck scraping for those.)
- MistralAI - (Subscription status)
# Usage:
`pip install -r requirements.txt`

`python main.py`

# Optional Arguments:

`-proxyoutput`

Outputs keys in a format that can be easily copy pasted into khanon's proxy instead of pretty print


`-nooutput`

Stops outputting and saving keys to the snapshot file (proxyoutput will also do this)

`-file`

Reads keys from a file instead of stdin, place either the absolute or relative path to the file in quotes after the flag.
