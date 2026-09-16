"""
Google Gemini LLM Provider.
"""
import google.generativeai as genai
from app.core.config import settings
from app.services.rag.providers.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.model:
            raise ValueError("Google Gemini API key is not configured. Please use offline mode or provide an API key.")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser Question:\n{prompt}"

        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.0)
        )
        return response.text or ""
