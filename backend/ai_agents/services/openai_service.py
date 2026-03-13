"""
OpenAI Service — used for:
  - Whisper: speech-to-text (interview simulator)
  - TTS: text-to-speech (interview simulator)
  - GPT-4o: optional text generation / fallback
"""

import logging
from typing import Dict, List, Optional
from decouple import config

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI API service for voice and optional text tasks."""

    def __init__(self):
        self.api_key = config('OPENAI_API_KEY', default='')
        self.model = config('OPENAI_MODEL', default='gpt-4o-mini')
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai package not installed. Run: pip install openai")

    # ── Voice ──────────────────────────────────────────────────────────────────

    def transcribe(self, audio_file, language: str = 'en') -> str:
        """
        Transcribe audio to text using Whisper.
        audio_file: a Django UploadedFile, open file-like object, or bytes.
        Returns the transcribed text string.
        """
        if not self.client:
            raise Exception("OpenAI client not available. Check OPENAI_API_KEY and openai package.")
        try:
            # OpenAI SDK requires bytes, io.IOBase, PathLike, or a tuple.
            # Django's UploadedFile is not accepted directly — convert to tuple.
            if hasattr(audio_file, 'read'):
                audio_file.seek(0)
                file_bytes = audio_file.read()
                filename = getattr(audio_file, 'name', 'recording.webm')
                content_type = getattr(audio_file, 'content_type', 'audio/webm')
                file_data = (filename, file_bytes, content_type)
            else:
                file_data = audio_file

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=file_data,
                language=language,
            )
            return transcript.text
        except Exception as e:
            logger.error("Whisper transcription error: %s", e)
            raise Exception(f"Whisper error: {e}")

    def text_to_speech(self, text: str, voice: str = 'alloy') -> bytes:
        """
        Convert text to speech using OpenAI TTS.
        voice options: alloy, echo, fable, onyx, nova, shimmer
        Returns raw MP3 bytes.
        """
        if not self.client:
            raise Exception("OpenAI client not available. Check OPENAI_API_KEY and openai package.")
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
            )
            return response.content
        except Exception as e:
            logger.error("TTS error: %s", e)
            raise Exception(f"TTS error: {e}")

    # ── Text Generation (GPT-4o fallback) ─────────────────────────────────────

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using GPT-4o."""
        if not self.client:
            raise Exception("OpenAI client not available. Check OPENAI_API_KEY and openai package.")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("OpenAI generate error: %s", e)
            raise Exception(f"OpenAI API error: {e}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Chat completion using GPT-4o."""
        if not self.client:
            raise Exception("OpenAI client not available. Check OPENAI_API_KEY and openai package.")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or 2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("OpenAI chat error: %s", e)
            raise Exception(f"OpenAI API error: {e}")

    def check_connection(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False

    def get_model_info(self) -> Dict:
        return {"name": self.model, "provider": "OpenAI"}


# Global instance
openai_service = OpenAIService()
