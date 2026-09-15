import pytest
import asyncio
from app.services.voice.base import STTCapability, Transcript
from app.services.voice.factory import VoiceProviderFactory
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider
from app.services.voice.segmentation import SentenceSegmenter


@pytest.mark.asyncio
async def test_mock_stt_provider_utterance():
    provider = MockSTTProvider(canned_transcript="How do I return an item?")
    assert provider.capability == STTCapability.REALTIME_STREAMING

    res = await provider.transcribe_utterance(b"dummy_audio_bytes", language="en")
    assert isinstance(res, Transcript)
    assert res.text == "How do I return an item?"
    assert res.is_final is True
    assert res.confidence == 0.98


@pytest.mark.asyncio
async def test_mock_stt_provider_stream():
    provider = MockSTTProvider(canned_transcript="Can you check my order status?")
    
    async def dummy_stream():
        yield b"chunk_1"
        yield b"chunk_2"

    transcripts = []
    async for t in provider.transcribe_stream(dummy_stream()):
        transcripts.append(t)

    assert len(transcripts) >= 2
    assert transcripts[0].is_final is False
    assert transcripts[-1].is_final is True
    assert transcripts[-1].text == "Can you check my order status?"


@pytest.mark.asyncio
async def test_mock_tts_provider_synthesize():
    tts = MockTTSProvider()
    voices = tts.get_available_voices()
    assert len(voices) >= 2
    assert any(v["id"] == "mock_aria" for v in voices)

    audio = await tts.synthesize("Hello, I am your AI employee.")
    assert len(audio) > 0
    assert audio.startswith(b"\xFF\xFB\x90\x64")
    assert "Hello, I am your AI employee." in tts.synthesized_calls


@pytest.mark.asyncio
async def test_mock_tts_provider_stream():
    tts = MockTTSProvider()

    async def text_chunks():
        yield "First sentence."
        yield "Second sentence."

    audio_chunks = []
    async for chunk in tts.synthesize_stream(text_chunks()):
        audio_chunks.append(chunk)

    assert len(audio_chunks) == 2


@pytest.mark.asyncio
async def test_sentence_segmenter_natural_phrasing():
    segmenter = SentenceSegmenter(min_chunk_chars=30)
    
    # Comma should NOT split if sentence boundary has not been reached
    segments = segmenter.push("Yes, we do have that, ")
    assert len(segments) == 0

    # Punctuation '.' triggers split
    segments = segmenter.push("and our return policy allows 30 days. Next, you can ")
    assert len(segments) == 1
    assert "return policy allows 30 days." in segments[0]

    # Flush catches remainder
    final_segments = segmenter.flush()
    assert len(final_segments) == 1
    assert "Next, you can" in final_segments[0]


def test_voice_factory_resolution():
    stt = VoiceProviderFactory.get_stt_provider("mock")
    assert isinstance(stt, MockSTTProvider)

    tts = VoiceProviderFactory.get_tts_provider("mock")
    assert isinstance(tts, MockTTSProvider)
