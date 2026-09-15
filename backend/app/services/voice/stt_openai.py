import asyncio
import io
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.exceptions import AppException
from app.services.voice.base import STTCapability, STTProvider, Transcript

logger = logging.getLogger("app.services.voice.stt_openai")


class OpenAIWhisperSTT(STTProvider):
    """OpenAI Whisper Speech-to-Text implementation (Utterance Batch).
    Supports OpenAI API and OpenAI-compatible Whisper endpoints (LocalAI, Faster-Whisper server, etc.).
    Supports multilingual input including English, Hindi, and Hinglish.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "whisper-1",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.timeout = timeout_seconds

    @property
    def capability(self) -> STTCapability:
        return STTCapability.UTTERANCE_BATCH

    async def transcribe_utterance(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        audio_format: str = "webm",
    ) -> Transcript:
        if not audio_bytes:
            return Transcript(text="", is_final=True, confidence=0.0)

        if not self.api_key:
            logger.warning("OpenAI API key not configured for Whisper STT. Falling back to empty transcript.")
            return Transcript(text="[Audio received: transcription unavailable without API key]", is_final=True)

        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        file_extension = "webm" if "webm" in audio_format else ("wav" if "wav" in audio_format else "mp3")
        filename = f"audio.{file_extension}"

        files = {
            "file": (filename, audio_bytes, f"audio/{file_extension}"),
        }
        data: Dict[str, Any] = {
            "model": self.model,
            "response_format": "verbose_json",
        }
        if language and language != "auto":
            data["language"] = language

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, data=data, files=files)
                if resp.status_code != 200:
                    logger.error(f"OpenAI Whisper error {resp.status_code}: {resp.text}")
                    raise AppException(f"Whisper transcription failed: {resp.status_code}", status_code=502)

                result = resp.json()
                transcribed_text = (result.get("text") or "").strip()
                detected_lang = result.get("language")
                duration = float(result.get("duration", 0.0))

                return Transcript(
                    text=transcribed_text,
                    is_final=True,
                    confidence=1.0,
                    language=detected_lang or language,
                    duration_seconds=duration,
                    metadata={"provider": "openai_whisper", "model": self.model},
                )
        except httpx.TimeoutException:
            logger.error("Whisper transcription request timed out.")
            raise AppException("Transcription service timed out", status_code=504)
        except Exception as e:
            logger.error(f"Error during Whisper transcription: {e}")
            raise AppException(f"Transcription error: {str(e)}", status_code=502)
