"""
Ollama / Local LLM Provider (OpenAI-compatible).

Allows connecting to locally running models (e.g., Llama 3, Mistral, Gemma 2, Phi-3, Qwen)
via Ollama's OpenAI-compatible API endpoint (default: http://localhost:11434/v1).
"""
import httpx
from openai import OpenAI
from app.core.config import settings
from app.services.rag.providers.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        self.base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.model = getattr(settings, "OLLAMA_MODEL", "llama3")
        try:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key="ollama",  # Ollama doesn't require a real API key
                timeout=30.0,
            )
        except Exception:
            self.client = None

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.client:
            raise ValueError(f"Failed to initialize Ollama client at {self.base_url}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
