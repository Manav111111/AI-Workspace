import json
import time
import uuid
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.public_session import PublicChatSession
from app.schemas.avatar import (
    AvatarEmotion,
    AvatarEventEnvelope,
    AvatarGaze,
    AvatarGesture,
    PresentationMetadata,
    map_conversation_context_to_presentation,
)
from app.services.public_runtime.security import hash_token
from app.services.voice.mock_providers import MockSTTProvider, MockTTSProvider
from app.services.voice.runtime import VoiceRuntimeManager
import datetime


def test_presentation_metadata_validation_and_clamping():
    """Verifies that PresentationMetadata strictly clamps numeric values,
    normalizes enums, and discards dangerous script/eval injections.
    """
    # 1. Valid metadata
    valid = PresentationMetadata(
        emotion=AvatarEmotion.CONFIDENT,
        intensity=0.8,
        duration_ms=3000,
        gesture=AvatarGesture.EXPLAIN,
        gaze=AvatarGaze.SPEAKING,
    )
    assert valid.emotion == AvatarEmotion.CONFIDENT
    assert valid.intensity == 0.8
    assert valid.duration_ms == 3000
    assert valid.gesture == AvatarGesture.EXPLAIN
    assert valid.gaze == AvatarGaze.SPEAKING

    # 2. Clamping intensity and duration
    clamped = PresentationMetadata.model_validate({
        "emotion": "happy",
        "intensity": 5.5,  # Out of range -> should clamp to 1.0
        "duration_ms": 50000,  # Out of range -> should clamp to 10000
    })
    assert clamped.emotion == AvatarEmotion.HAPPY
    assert clamped.intensity == 1.0
    assert clamped.duration_ms == 10000

    low_clamped = PresentationMetadata.model_validate({
        "emotion": "friendly",
        "intensity": -1.0,  # Out of range -> should clamp to 0.0
        "duration_ms": 10,  # Out of range -> should clamp to 100
    })
    assert low_clamped.intensity == 0.0
    assert low_clamped.duration_ms == 100

    # 3. Discarding malicious injections
    malicious = PresentationMetadata.model_validate({
        "emotion": "friendly",
        "javascript": "alert('hacked')",
        "url": "http://malicious.site/payload.js",
        "execute": "rm -rf /",
        "script": "<script>evil()</script>",
    })
    data = malicious.model_dump()
    assert "javascript" not in data
    assert "url" not in data
    assert "execute" not in data
    assert "script" not in data
    assert data["emotion"] == "friendly"

    # 4. Unknown emotion falls back safely to neutral
    unknown_emotion = PresentationMetadata.model_validate({
        "emotion": "hyperactive_alien",
    })
    assert unknown_emotion.emotion == AvatarEmotion.NEUTRAL


def test_map_conversation_context_to_presentation():
    """Verifies deterministic context mapping translates conversational states
    safely without calling any external LLM or database.
    """
    # Pending confirmation -> curious
    p1 = map_conversation_context_to_presentation(
        reply_text="Should I proceed with placing this order?",
        pending_confirmation={"tool_name": "place_order"},
    )
    assert p1.emotion == AvatarEmotion.CURIOUS

    # Tool activity -> confident
    p2 = map_conversation_context_to_presentation(
        reply_text="I retrieved 3 active subscriptions.",
        tool_activity=["search_catalog"],
    )
    assert p2.emotion == AvatarEmotion.CONFIDENT
    assert p2.gesture == AvatarGesture.EXPLAIN

    # Apologetic text -> apologetic
    p3 = map_conversation_context_to_presentation(
        reply_text="I am sorry, but unfortunately I cannot find that record.",
    )
    assert p3.emotion == AvatarEmotion.APOLOGETIC
    assert p3.gaze == AvatarGaze.GLANCE_AWAY

    # Friendly greeting
    p4 = map_conversation_context_to_presentation(
        reply_text="Hello and welcome! How can I assist you today?",
    )
    assert p4.emotion == AvatarEmotion.FRIENDLY
    assert p4.gesture == AvatarGesture.WELCOME


def test_avatar_event_envelope_protocol_v2():
    """Verifies AvatarEventEnvelope validates protocol version 2 and remains backward compatible."""
    # V2 envelope
    env = AvatarEventEnvelope(
        protocol_version=2,
        type="emotion",
        sequence=15,
        timestamp=time.time(),
        session_id="sess_123",
        generation_id="gen_456",
        payload={"emotion": "friendly", "intensity": 0.7},
    )
    assert env.protocol_version == 2
    assert env.type == "emotion"
    assert env.sequence == 15
    assert env.generation_id == "gen_456"

    # Backward compatibility with unversioned / v1 envelopes (defaulting protocol_version)
    env_v1 = AvatarEventEnvelope.model_validate({
        "type": "status",
        "sequence": 1,
        "timestamp": time.time(),
        "state": "speaking",
    })
    assert env_v1.protocol_version == 2
    assert env_v1.type == "status"
    assert env_v1.sequence == 1


@pytest.mark.asyncio
async def test_voice_runtime_emits_protocol_v2_and_turn_taking(db_session: AsyncSession):
    """Verifies VoiceRuntimeManager emits protocol_version=2, speech_start,
    speech_end, and presentation events with strict generation IDs.
    """
    company = Company(name="Phase 7 Co", slug=f"p7-{uuid.uuid4().hex[:6]}")
    db_session.add(company)
    await db_session.flush()

    emp = AIEmployee(
        company_id=company.id,
        name="Avatar Priya P7",
        role="Product Specialist",
        public_id=f"pub_p7_{uuid.uuid4().hex[:8]}",
        is_published=True,
        status=AIEmployeeStatus.ACTIVE,
        allowed_domains=["*"],
        avatar_config={"model_id": "default_female", "expression_preset": "friendly"},
        voice_config={"voice_id": "mock_aria", "speed": 1.0},
    )
    db_session.add(emp)
    await db_session.flush()

    conv = Conversation(company_id=company.id, ai_employee_id=emp.id, title="P7 Session")
    db_session.add(conv)
    await db_session.flush()

    raw_token = f"sess_p7_{uuid.uuid4().hex}"
    pub_session = PublicChatSession(
        company_id=company.id,
        ai_employee_id=emp.id,
        conversation_id=conv.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24),
    )
    db_session.add(pub_session)
    await db_session.commit()

    sent_frames = []
    mock_ws = AsyncMock()
    mock_ws.client.host = "127.0.0.1"

    async def capture_send_text(text: str):
        sent_frames.append(json.loads(text))

    mock_ws.send_text.side_effect = capture_send_text

    stt = MockSTTProvider(canned_transcript="Can you help me check my order?")
    tts = MockTTSProvider()

    manager = VoiceRuntimeManager(
        websocket=mock_ws,
        session=db_session,
        stt_provider=stt,
        tts_provider=tts,
    )

    await manager.authenticate_handshake(raw_token)
    await manager.process_user_utterance(audio_data=b"\x00" * 3200, audio_format="webm")

    event_types = [f["type"] for f in sent_frames]

    # Protocol v2 verification: every frame contains protocol_version=2 and matching generation_id
    gen_id = manager.active_generation_id
    assert gen_id is not None
    for f in sent_frames:
        assert f.get("protocol_version") == 2
        assert "sequence" in f
        assert "timestamp" in f
        assert f.get("session_id") == str(pub_session.id)
        if f["type"] not in ["auth_ok"]:
            assert f.get("generation_id") == gen_id

    # Turn-taking verification: speech_start and speech_end must wrap audio streaming
    assert "speech_start" in event_types
    assert "speech_end" in event_types
    assert "assistant_message" in event_types
    assert "status" in event_types

    # Monotonic ordering
    sequences = [f["sequence"] for f in sent_frames]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)
