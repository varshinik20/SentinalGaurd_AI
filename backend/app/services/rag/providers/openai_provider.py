"""
OpenAI LLM Provider.
"""
from openai import OpenAI
from app.core.config import settings
from app.services.rag.providers.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=getattr(settings, "OPENAI_BASE_URL", None),
            )
        else:
            self.client = None

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.client:
            raise ValueError("OpenAI API key is not configured. Please use offline mode or provide an API key.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0
        )
        return response.choices[0].message.content or ""
