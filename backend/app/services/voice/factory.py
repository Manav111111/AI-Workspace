import logging
from typing import Optional
from app.core.config import settings
from app.services.voice.base import STTProvider, TTSProvider
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider
from app.services.voice.stt_openai import OpenAIWhisperSTT
from app.services.voice.tts_openai import OpenAITTS

logger = logging.getLogger("app.services.voice.factory")


class VoiceProviderFactory:
    """Factory resolving configured STT and TTS provider implementations.
    Strictly decouples the voice runtime from concrete vendor instances.
    """

    @classmethod
    def get_stt_provider(cls, provider_name: Optional[str] = None) -> STTProvider:
        name = (provider_name or settings.VOICE_STT_PROVIDER).lower().strip()
        if name == "openai" or name == "whisper":
            return OpenAIWhisperSTT(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
            )
        elif name == "mock":
            return MockSTTProvider()
        else:
            logger.warning(f"Unknown STT provider '{name}', falling back to MockSTTProvider")
            return MockSTTProvider()

    @classmethod
    def get_tts_provider(cls, provider_name: Optional[str] = None) -> TTSProvider:
        name = (provider_name or settings.VOICE_TTS_PROVIDER).lower().strip()
        if name == "openai":
            return OpenAITTS(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
            )
        elif name == "mock":
            return MockTTSProvider()
        else:
            logger.warning(f"Unknown TTS provider '{name}', falling back to MockTTSProvider")
            return MockTTSProvider()
