"""
Base LLM Provider interface.
"""
from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        Send a prompt to the LLM and return the generated text.
        """
        pass
