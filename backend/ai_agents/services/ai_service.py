"""
Claude AI Service — primary LLM provider for all text-based AI tasks.
"""

import logging
from typing import Dict, Generator, List, Optional, Union
from decouple import config

import anthropic

logger = logging.getLogger(__name__)


class AIService:
    """Claude API service used by all agents for text generation."""

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
        """Chat completion using Claude API. Accepts OpenAI-style message format."""
        if not self.client:
            raise Exception("ANTHROPIC_API_KEY is not set in .env")

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

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """Streaming chat — yields text tokens as Claude generates them."""
        if not self.client:
            raise Exception("ANTHROPIC_API_KEY is not set in .env")

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
            with self.client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error("Claude chat stream error: %s", e)
            raise Exception(f"Claude API error: {e}")

    def check_connection(self) -> bool:
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
        return [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6",
            "claude-opus-4-6",
        ]

    def get_model_info(self) -> Dict:
        return {"name": self.model, "provider": "Anthropic Claude"}


# Global instance
ai_service = AIService()
