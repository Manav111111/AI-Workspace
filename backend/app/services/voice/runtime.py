import asyncio
import base64
import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_employee import AIEmployee
from app.models.public_session import PublicChatSession
from app.models.public_usage import PublicUsageEvent
from app.models.voice_session import VoiceSession, VoiceSessionStatus
from app.services.conversation_engine import ConversationEngine
from app.services.public_runtime.security import PublicSecurityService
from app.services.voice.base import STTCapability, STTProvider, TTSProvider, Transcript
from app.services.voice.factory import VoiceProviderFactory
from app.services.voice.segmentation import SentenceSegmenter

logger = logging.getLogger("app.services.voice.runtime")


class VoiceSessionSecurityException(Exception):
    """Raised when authentication or multi-tenant boundaries fail in voice."""
    pass


class VoiceRuntimeManager:
    """Manages an active real-time bidirectional WebSocket voice session.
    Reuses the existing unified ConversationEngine, RAG retriever, tool executor,
    and server-side PendingToolAction confirmation flows.
    """

    def __init__(
        self,
        websocket: WebSocket,
        session: AsyncSession,
        stt_provider: Optional[STTProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
    ):
        self.websocket = websocket
        self.session = session
        self.stt_provider = stt_provider or VoiceProviderFactory.get_stt_provider()
        self.tts_provider = tts_provider or VoiceProviderFactory.get_tts_provider()

        # Authenticated Session Context
        self.public_session: Optional[PublicChatSession] = None
        self.ai_employee: Optional[AIEmployee] = None
        self.voice_session_record: Optional[VoiceSession] = None

        # State tracking
        self.is_authenticated = False
        self.is_ai_speaking = False
        self.active_tts_task: Optional[asyncio.Task] = None
        self.active_generation_id: Optional[str] = None
        self.audio_buffer = bytearray()
        self.sequence_counter = 0

        # Telemetry metrics
        self.input_audio_seconds = 0.0
        self.output_audio_seconds = 0.0
        self.stt_requests = 0
        self.tts_requests = 0
        self.llm_input_tokens = 0
        self.llm_output_tokens = 0
        self.interruptions_count = 0
        self.first_transcript_time_ms = 0.0
        self.first_audio_time_ms = 0.0
        self.session_start_time = time.perf_counter()

    async def send_avatar_event(self, event_type: str, payload: Optional[Dict[str, Any]] = None, **kwargs):
        """Dispatches an AvatarEvent adhering to the standardized Avatar Event Protocol.
        Guarantees:
        - Monotonically increasing sequence number per session.
        - High-resolution timestamp.
        - Uniform envelope containing session_id and generation_id.
        """
        self.sequence_counter += 1
        data = {
            "protocol_version": 2,
            "type": event_type,
            "sequence": self.sequence_counter,
            "timestamp": time.time(),
            "session_id": str(self.public_session.id) if self.public_session else None,
            "generation_id": self.active_generation_id,
        }
        if payload:
            data.update(payload)
        data.update(kwargs)
        await self.websocket.send_text(json.dumps(data))

    async def authenticate_handshake(self, auth_token: str) -> PublicChatSession:
        """Validates bearer session token from the initial handshake frame.
        Guarantees:
        - Single authentication rule (rejects re-auth attempts).
        - Resolves active public session.
        - Enforces server-side tenant isolation (company_id & ai_employee_id cannot be spoofed).
        - Tokens are never logged raw.
        """
        if self.is_authenticated:
            logger.warning("Rejecting duplicate authentication handshake on active socket.")
            raise VoiceSessionSecurityException("Session is already authenticated.")

        if not auth_token or not isinstance(auth_token, str):
            raise VoiceSessionSecurityException("Invalid or missing session token.")

        # Log masked token
        masked_tok = f"{auth_token[:8]}...{auth_token[-4:]}" if len(auth_token) > 12 else "***"
        logger.info(f"Authenticating voice WebSocket with token [{masked_tok}]")

        pub_session = await PublicSecurityService.resolve_active_session(self.session, auth_token)

        # Load employee and verify active status
        from app.services.public_runtime.runtime import PublicRuntimeService
        runtime = PublicRuntimeService(self.session)
        emp = await runtime.get_published_employee(pub_session.ai_employee.public_id)

        # Create VoiceSession telemetry record
        voice_rec = VoiceSession(
            company_id=pub_session.company_id,
            ai_employee_id=emp.id,
            conversation_id=pub_session.conversation_id,
            public_session_id=pub_session.id,
            status=VoiceSessionStatus.ACTIVE,
        )
        self.session.add(voice_rec)
        await self.session.commit()

        self.public_session = pub_session
        self.ai_employee = emp
        self.voice_session_record = voice_rec
        self.is_authenticated = True

        logger.info(
            f"Voice session authenticated successfully | company={emp.company_id} "
            f"| employee={emp.id} | conversation={pub_session.conversation_id}"
        )
        return pub_session

    async def handle_barge_in(self):
        """Cancels ongoing AI speech playback and generation when the user interrupts."""
        if not self.is_ai_speaking:
            return

        logger.info("Barge-in detected: cancelling active AI speech generation.")
        self.is_ai_speaking = False
        self.interruptions_count += 1

        if self.active_tts_task and not self.active_tts_task.done():
            self.active_tts_task.cancel()

        # Send interrupt command to wipe browser audio buffer
        await self.send_avatar_event("interrupted")

    async def process_user_utterance(
        self,
        audio_data: bytes,
        audio_format: str = "webm",
        user_text: Optional[str] = None,
        pending_action_id: Optional[str] = None,
        confirm_action: bool = False,
    ):
        """Transcribes audio, dispatches to unified ConversationEngine, and streams synthesized audio."""
        if not self.is_authenticated or not self.public_session or not self.ai_employee:
            raise VoiceSessionSecurityException("Cannot process audio without an authenticated session.")

        generation_id = str(uuid.uuid4())
        self.active_generation_id = generation_id
        utterance_start = time.perf_counter()

        # 1. Speech-to-Text (STT) or direct text
        final_text = (user_text or "").strip()
        if not final_text and audio_data:
            await self.send_avatar_event("status", state="transcribing")
            self.stt_requests += 1
            est_audio_seconds = max(0.5, round(len(audio_data) / 32000, 2))
            self.input_audio_seconds += est_audio_seconds

            stt_start = time.perf_counter()
            transcript_res: Transcript = await self.stt_provider.transcribe_utterance(
                audio_bytes=audio_data,
                language=self.ai_employee.language or "en",
                audio_format=audio_format,
            )
            final_text = transcript_res.text.strip()
            self.first_transcript_time_ms = round((time.perf_counter() - stt_start) * 1000, 2)

            # Send final transcript to client
            await self.send_avatar_event(
                "transcript",
                text=final_text,
                is_final=True,
            )

        if not final_text and not pending_action_id:
            await self.send_avatar_event("status", state="idle")
            return

        # 2. Unified ConversationEngine Execution (Reusing identical RAG, Agent, Tools, and Confirmation)
        await self.send_avatar_event("status", state="thinking")

        parsed_action_id = uuid.UUID(pending_action_id) if pending_action_id else None
        engine = ConversationEngine(self.session)

        engine_response = await engine.respond(
            company_id=self.public_session.company_id,
            conversation_id=self.public_session.conversation_id,
            user_query=final_text,
            user_id=None,
            pending_action_id=parsed_action_id,
            confirm_action=confirm_action,
        )

        reply_text = engine_response.assistant_message.content
        citations = [
            {
                "document_name": c.get("document_name", "Document"),
                "page_number": c.get("page_number"),
                "header_path": c.get("header_path"),
                "score": round(float(c.get("score", 0.0)), 3),
            }
            for c in engine_response.citations
        ]
        tool_activity = [
            tc.get("name") or tc.get("tool_name")
            for tc in engine_response.tool_calls
            if tc.get("name") or tc.get("tool_name")
        ]

        # Check for write tool pending confirmation
        pending_conf = None
        if engine_response.pending_confirmation:
            pc = engine_response.pending_confirmation
            pending_conf = {
                "pending_action_id": str(pc.get("pending_action_id")),
                "tool_name": str(pc.get("tool_name")),
                "arguments": pc.get("arguments", {}),
                "message": pc.get("message"),
            }

        # Send structured text, citation payload, and presentation metadata
        presentation_meta = getattr(engine_response, "presentation", None)
        await self.send_avatar_event(
            "assistant_message",
            text=reply_text,
            citations=citations,
            tool_activity=tool_activity,
            pending_confirmation=pending_conf,
            presentation=presentation_meta,
        )

        # Dispatch explicit presentation events if present
        if presentation_meta:
            if presentation_meta.get("emotion"):
                await self.send_avatar_event(
                    "emotion",
                    emotion=presentation_meta["emotion"],
                    intensity=presentation_meta.get("intensity", 0.5),
                    duration_ms=presentation_meta.get("duration_ms", 2000),
                )
            if presentation_meta.get("gesture") and presentation_meta.get("gesture") != "none":
                await self.send_avatar_event(
                    "gesture",
                    gesture=presentation_meta["gesture"],
                    duration_ms=presentation_meta.get("duration_ms", 2000),
                )
            if presentation_meta.get("gaze"):
                await self.send_avatar_event(
                    "gaze",
                    gaze=presentation_meta["gaze"],
                    duration_ms=presentation_meta.get("duration_ms", 2000),
                )

        # 3. Stream Synthesized Audio (TTS)
        self.is_ai_speaking = True
        await self.send_avatar_event("status", state="speaking")
        await self.send_avatar_event("speech_start")

        voice_config = (self.ai_employee.voice_config or {}).copy()
        segmenter = SentenceSegmenter(min_chunk_chars=settings.VOICE_TTS_BUFFER_MIN_CHARS)
        sentences = segmenter.push(reply_text) + segmenter.flush()

        first_chunk = True
        tts_start = time.perf_counter()

        try:
            for sentence in sentences:
                if not self.is_ai_speaking:
                    logger.info("Speech generation aborted due to barge-in.")
                    break

                self.tts_requests += 1
                audio_bytes = await self.tts_provider.synthesize(sentence, voice_config=voice_config)
                if audio_bytes and self.is_ai_speaking:
                    if first_chunk:
                        self.first_audio_time_ms = round((time.perf_counter() - tts_start) * 1000, 2)
                        first_chunk = False

                    self.output_audio_seconds += max(0.5, len(audio_bytes) / 16000)
                    # Stream binary audio chunk as base64 with metadata & sequence
                    await self.send_avatar_event(
                        "audio_chunk",
                        audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
                        format="mp3",
                        text=sentence,
                    )
                    # Brief yield for event loop
                    await asyncio.sleep(0.01)

            if self.is_ai_speaking:
                await self.send_avatar_event("speech_end")

        except asyncio.CancelledError:
            logger.info("TTS task was cancelled.")
        finally:
            self.is_ai_speaking = False
            await self.send_avatar_event("status", state="idle")

        total_turn_ms = round((time.perf_counter() - utterance_start) * 1000, 2)

        # Record usage telemetry in database
        usage_event = PublicUsageEvent(
            company_id=self.public_session.company_id,
            ai_employee_id=self.public_session.ai_employee_id,
            session_id=self.public_session.id,
            event_type="VOICE_TURN",
            message_count=1,
            tool_call_count=len(tool_activity),
            input_tokens=engine_response.metrics.get("prompt_tokens", 0) or 0,
            output_tokens=engine_response.metrics.get("completion_tokens", 0) or 0,
            latency_ms=total_turn_ms,
        )
        self.session.add(usage_event)
        await self.session.commit()

    async def close_session(self):
        """Finalizes voice session metrics on disconnect."""
        if self.voice_session_record:
            total_duration_ms = round((time.perf_counter() - self.session_start_time) * 1000, 2)
            self.voice_session_record.status = VoiceSessionStatus.COMPLETED
            self.voice_session_record.ended_at = datetime.datetime.now(datetime.timezone.utc)
            self.voice_session_record.input_audio_seconds = self.input_audio_seconds
            self.voice_session_record.output_audio_seconds = self.output_audio_seconds
            self.voice_session_record.stt_requests = self.stt_requests
            self.voice_session_record.tts_requests = self.tts_requests
            self.voice_session_record.time_to_first_transcript_ms = self.first_transcript_time_ms
            self.voice_session_record.time_to_first_audio_ms = self.first_audio_time_ms
            self.voice_session_record.total_latency_ms = total_duration_ms
            self.voice_session_record.interruptions_count = self.interruptions_count
            self.session.add(self.voice_session_record)
            try:
                await self.session.commit()
            except Exception as e:
                logger.error(f"Error persisting VoiceSession summary on close: {e}")
