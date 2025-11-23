import httpx
from openai import AzureOpenAI


class LLMClient:
    def __init__(self, api_key, endpoint, api_version="********"):
        insecure_client = httpx.Client(verify=False)
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
            http_client=insecure_client,
        )

    def ask(self, prompt, model="********"):
        response = self.client.responses.create(
            model=model,
            input=prompt
        )
        return response.output_text
