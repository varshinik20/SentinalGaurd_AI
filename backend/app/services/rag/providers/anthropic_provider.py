"""
Anthropic Claude LLM Provider.
"""
from anthropic import Anthropic
from app.core.config import settings
from app.services.rag.providers.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.client:
            raise ValueError("Anthropic API key is not configured. Please use offline mode or provide an API key.")

        system = system_prompt or ""
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            temperature=0.0,
            system=system,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        # Parse content block
        return response.content[0].text if response.content else ""
