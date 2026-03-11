"""
Claude AI Service (replaces Ollama for LLM inference)
Drop-in replacement with the same interface as the old OllamaService.
"""

import logging
from typing import Dict, Generator, List, Optional, Union
from decouple import config

import anthropic

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Claude API service with the same interface as the old OllamaService.
    All agents and tools continue to work without any changes.
    """

    def __init__(self):
        self.api_key = config('ANTHROPIC_API_KEY', default='')
        self.model = config('CLAUDE_MODEL', default='claude-haiku-4-5-20251001')
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """Generate text using Claude API."""
        if not self.client:
            raise Exception("ANTHROPIC_API_KEY is not set in .env")

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or 2048,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        try:
            if stream:
                return self._stream_response(kwargs)

            response = self.client.messages.create(**kwargs)
            return response.content[0].text

        except Exception as e:
            logger.error("Claude generate error: %s", e)
            raise Exception(f"Claude API error: {e}")

    def _stream_response(self, kwargs) -> Generator[str, None, None]:
        """Yield text chunks from a streaming Claude response."""
        try:
            with self.client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error("Claude stream error: %s", e)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Chat completion using Claude API.
        Accepts messages in OpenAI/Ollama format: [{"role": "...", "content": "..."}]
        System messages are extracted and passed as the system parameter.
        """
        if not self.client:
            raise Exception("ANTHROPIC_API_KEY is not set in .env")

        # Extract system message if present (Claude uses a separate system param)
        system = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        if not user_messages:
            user_messages = [{"role": "user", "content": "Hello"}]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or 2048,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system:
            kwargs["system"] = system

        try:
            response = self.client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            logger.error("Claude chat error: %s", e)
            raise Exception(f"Claude API error: {e}")

    def check_connection(self) -> bool:
        """Return True if Claude API is reachable and key is valid."""
        if not self.client:
            return False
        try:
            self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}]
            )
            return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Return available Claude models."""
        return [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6",
            "claude-opus-4-6",
        ]

    def get_model_info(self) -> Dict:
        """Return info about the currently configured model."""
        return {"name": self.model, "provider": "Anthropic Claude"}


# Global instance — same name so all imports continue to work
ollama_service = OllamaService()
