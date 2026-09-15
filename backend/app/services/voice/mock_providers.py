import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from app.services.voice.base import STTCapability, STTProvider, TTSProvider, Transcript

logger = logging.getLogger("app.services.voice.mock_providers")


class MockSTTProvider(STTProvider):
    """Hermetic Mock STT Provider for testing voice sessions without external API calls.
    Can be configured with deterministic canned responses or partial/final streaming.
    """

    def __init__(
        self,
        capability: STTCapability = STTCapability.REALTIME_STREAMING,
        canned_transcript: str = "Hello, what is your refund policy?",
        should_fail: bool = False,
    ):
        self._capability = capability
        self.canned_transcript = canned_transcript
        self.should_fail = should_fail
        self.transcribed_chunks_count = 0

    @property
    def capability(self) -> STTCapability:
        return self._capability

    async def transcribe_utterance(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        audio_format: str = "webm",
    ) -> Transcript:
        if self.should_fail:
            raise RuntimeError("Mock STT forced failure")

        self.transcribed_chunks_count += 1
        return Transcript(
            text=self.canned_transcript,
            is_final=True,
            confidence=0.98,
            language=language or "en",
            duration_seconds=round(len(audio_bytes) / 16000, 2),
            metadata={"mock": True, "audio_bytes_len": len(audio_bytes)},
        )

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language: Optional[str] = None,
    ) -> AsyncIterator[Transcript]:
        if self.should_fail:
            raise RuntimeError("Mock STT stream forced failure")

        words = self.canned_transcript.split()
        if len(words) > 1:
            # Yield 1 partial transcript
            partial = " ".join(words[: len(words) // 2])
            yield Transcript(
                text=partial,
                is_final=False,
                confidence=0.85,
                language=language or "en",
            )
            await asyncio.sleep(0.01)

        # Final transcript
        yield Transcript(
            text=self.canned_transcript,
            is_final=True,
            confidence=0.98,
            language=language or "en",
        )


class MockTTSProvider(TTSProvider):
    """Hermetic Mock TTS Provider for testing voice sessions without external API calls."""

    AVAILABLE_VOICES = [
        {"id": "mock_aria", "name": "Mock Aria", "gender": "female", "description": "Crisp and clear"},
        {"id": "mock_roger", "name": "Mock Roger", "gender": "male", "description": "Natural baritone"},
    ]

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.synthesized_calls: List[str] = []

    def get_available_voices(self) -> List[Dict[str, Any]]:
        return self.AVAILABLE_VOICES

    async def synthesize(
        self,
        text: str,
        voice_config: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        if self.should_fail:
            raise RuntimeError("Mock TTS forced failure")

        self.synthesized_calls.append(text)
        # Produce synthetic valid dummy MP3 frame (MPEG-1 Audio Layer 3 header + padding)
        header = b"\xFF\xFB\x90\x64"
        payload = text.encode("utf-8")[:128]
        return header + payload.ljust(128, b"\x00")

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        voice_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        async for chunk in text_stream:
            segment = chunk.strip()
            if segment:
                yield await self.synthesize(segment, voice_config=voice_config)
