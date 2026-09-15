import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from app.core.exceptions import AppException
from app.services.voice.base import TTSProvider

logger = logging.getLogger("app.services.voice.tts_openai")


class OpenAITTS(TTSProvider):
    """OpenAI Text-to-Speech implementation.
    Supports streaming audio chunks (mp3) with provider-agnostic voice configuration.
    """

    AVAILABLE_VOICES = [
        {"id": "alloy", "name": "Alloy", "gender": "neutral", "description": "Balanced and versatile"},
        {"id": "echo", "name": "Echo", "gender": "male", "description": "Warm and conversational"},
        {"id": "fable", "name": "Fable", "gender": "female", "description": "Expressive and dynamic"},
        {"id": "onyx", "name": "Onyx", "gender": "male", "description": "Authoritative and calm"},
        {"id": "nova", "name": "Nova", "gender": "female", "description": "Friendly and energetic"},
        {"id": "shimmer", "name": "Shimmer", "gender": "female", "description": "Clear and resonant"},
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "tts-1",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.timeout = timeout_seconds

    def get_available_voices(self) -> List[Dict[str, Any]]:
        return self.AVAILABLE_VOICES

    async def synthesize(
        self,
        text: str,
        voice_config: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        if not text or not text.strip():
            return b""

        if not self.api_key:
            logger.warning("OpenAI API key not configured for TTS. Returning synthetic audio bytes.")
            return b"\xFF\xF3\x40\xC4" + (b"\x00" * 32)  # Minimal dummy frame

        v_cfg = voice_config or {}
        voice_id = v_cfg.get("voice_id") or "alloy"
        speed = float(v_cfg.get("speed", 1.0))
        speed = max(0.5, min(speed, 2.0))

        url = f"{self.base_url}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text.strip(),
            "voice": voice_id,
            "response_format": "mp3",
            "speed": speed,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.error(f"OpenAI TTS error {resp.status_code}: {resp.text}")
                    raise AppException(f"TTS synthesis failed: {resp.status_code}", status_code=502)
                return resp.content
        except Exception as e:
            logger.error(f"Error during OpenAI TTS synthesis: {e}")
            raise AppException(f"TTS error: {str(e)}", status_code=502)

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        voice_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        async for text_segment in text_stream:
            segment = text_segment.strip()
            if segment:
                audio_bytes = await self.synthesize(segment, voice_config=voice_config)
                if audio_bytes:
                    yield audio_bytes
