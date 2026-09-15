from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import enum
from typing import Any, AsyncIterator, Dict, List, Optional


class STTCapability(str, enum.Enum):
    """Supported transcription modalities."""
    REALTIME_STREAMING = "REALTIME_STREAMING"
    UTTERANCE_BATCH = "UTTERANCE_BATCH"


@dataclass
class Transcript:
    """Normalized speech-to-text transcript."""
    text: str
    is_final: bool = True
    confidence: float = 1.0
    language: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioChunk:
    """Normalized audio buffer."""
    data: bytes
    format: str = "webm"  # "webm", "pcm", "mp3", "wav"
    sample_rate: int = 16000
    duration_seconds: float = 0.0


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text providers.
    Supports both real-time streaming audio transcription and utterance-based batch transcription.
    Avtaar components strictly depend on this interface, never vendor SDKs.
    """

    @property
    @abstractmethod
    def capability(self) -> STTCapability:
        """Returns provider streaming vs batch capability."""
        pass

    @abstractmethod
    async def transcribe_utterance(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        audio_format: str = "webm",
    ) -> Transcript:
        """Transcribes a discrete audio segment / utterance."""
        pass

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        language: Optional[str] = None,
    ) -> AsyncIterator[Transcript]:
        """Transcribes an audio chunk stream yielding partial and final transcripts.
        Default implementation buffers stream and falls back to transcribe_utterance.
        """
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
        if buffer:
            res = await self.transcribe_utterance(bytes(buffer), language=language)
            yield res


class TTSProvider(ABC):
    """Abstract interface for Text-to-Speech synthesis providers.
    Decoupled from vendor-specific models (OpenAI, ElevenLabs, Deepgram, Edge-TTS).
    """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_config: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Synthesizes complete text into an audio byte buffer (e.g. mp3 or pcm)."""
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        voice_config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[bytes]:
        """Synthesizes incoming text chunks into streamed audio buffers."""
        pass

    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Returns available voice IDs, names, and supported genders/languages for this provider."""
        pass
