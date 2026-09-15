import base64
import json
import logging
from typing import Dict
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.services.voice.factory import VoiceProviderFactory
from app.services.voice.runtime import VoiceRuntimeManager, VoiceSessionSecurityException

logger = logging.getLogger("app.api.v1.voice")
router = APIRouter(prefix="/voice", tags=["Voice AI"])

# Global tracker for concurrent voice sessions
ACTIVE_VOICE_SESSIONS: Dict[str, int] = {}


@router.get("/voices")
async def get_available_voices():
    """Returns available synthesized voices for the currently configured TTS provider."""
    tts_provider = VoiceProviderFactory.get_tts_provider()
    return {
        "provider": settings.VOICE_TTS_PROVIDER,
        "voices": tts_provider.get_available_voices(),
    }


@router.websocket("/stream")
async def voice_stream_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """Bidirectional streaming WebSocket endpoint for Real-Time Voice AI conversations.
    Protocol:
    1. Client connects.
    2. Client MUST send handshake frame: {"type": "auth", "token": "sess_pub_..."}.
    3. Server verifies session and locks company_id/ai_employee_id context.
    4. Client sends audio chunks: {"type": "audio", "data": "<base64>", "format": "webm"}.
    5. Server returns transcripts, assistant text, and streamed audio chunks.
    6. User interruption triggers {"type": "interrupted"} wiping audio buffers.
    """
    await websocket.accept()

    manager = VoiceRuntimeManager(websocket=websocket, session=db)
    client_host = websocket.client.host if websocket.client else "unknown"

    try:
        # Step 1: Wait for initial authentication handshake
        handshake_data = await websocket.receive_text()
        try:
            payload = json.loads(handshake_data)
        except json.JSONDecodeError:
            logger.warning(f"Voice WS: Received malformed JSON from {client_host}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid handshake format")
            return

        if payload.get("type") != "auth" or not payload.get("token"):
            logger.warning(f"Voice WS: First frame from {client_host} was not auth")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
            return

        token = str(payload["token"]).strip()
        try:
            pub_session = await manager.authenticate_handshake(token)
        except Exception as auth_err:
            logger.warning(f"Voice WS: Authentication failed for {client_host}: {auth_err}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(auth_err))
            return

        # Check concurrent session limit for tenant
        tenant_key = str(pub_session.company_id)
        current_active = ACTIVE_VOICE_SESSIONS.get(tenant_key, 0)
        if current_active >= settings.VOICE_MAX_CONCURRENT_SESSIONS_PER_TENANT:
            logger.warning(f"Voice WS: Tenant {tenant_key} reached concurrent session quota.")
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Tenant concurrent voice session quota reached.",
            )
            return

        ACTIVE_VOICE_SESSIONS[tenant_key] = current_active + 1

        # Send authentication confirmation to client
        await websocket.send_text(json.dumps({
            "type": "auth_ok",
            "employee": {
                "name": manager.ai_employee.name,
                "role": manager.ai_employee.role,
                "language": manager.ai_employee.language,
            },
        }))

        # Step 2: Main bidirectional event loop
        while True:
            raw_msg = await websocket.receive_text()
            try:
                event = json.loads(raw_msg)
            except json.JSONDecodeError:
                continue

            event_type = event.get("type")

            # Check for re-authentication attempt (strictly disallowed)
            if event_type == "auth":
                logger.warning(f"Voice WS: Disallowed second auth attempt from {client_host}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Session already authenticated.",
                }))
                continue

            # Check for user barge-in / speech started
            if event_type == "user_speaking":
                await manager.handle_barge_in()
                continue

            # Process incoming audio utterance
            if event_type == "audio_utterance":
                b64_data = event.get("data") or ""
                audio_fmt = event.get("format") or "webm"
                try:
                    audio_bytes = base64.b64decode(b64_data)
                except Exception:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid audio encoding",
                    }))
                    continue

                # Audio chunk size check
                if len(audio_bytes) > settings.VOICE_MAX_AUDIO_CHUNK_SIZE_BYTES:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Audio chunk exceeds maximum allowed size",
                    }))
                    continue

                # Handle barge-in if AI is currently talking
                await manager.handle_barge_in()

                # Process utterance via ConversationEngine
                await manager.process_user_utterance(
                    audio_data=audio_bytes,
                    audio_format=audio_fmt,
                    pending_action_id=event.get("pending_action_id"),
                    confirm_action=bool(event.get("confirm_action", False)),
                )

            # Process direct text message in voice mode (conversation continuity)
            elif event_type == "text_message":
                msg_text = event.get("text", "").strip()
                await manager.handle_barge_in()
                await manager.process_user_utterance(
                    audio_data=b"",
                    user_text=msg_text,
                    pending_action_id=event.get("pending_action_id"),
                    confirm_action=bool(event.get("confirm_action", False)),
                )

            # Explicit action confirmation frame from voice UI card
            elif event_type == "confirm_action":
                action_id = event.get("pending_action_id")
                verdict = bool(event.get("confirm", False))
                await manager.process_user_utterance(
                    audio_data=b"",
                    pending_action_id=action_id,
                    confirm_action=verdict,
                )

    except WebSocketDisconnect:
        logger.info(f"Voice WS: Client disconnected normally ({client_host})")
    except Exception as e:
        logger.error(f"Voice WS: Unexpected error: {e}")
    finally:
        if manager.is_authenticated and manager.public_session:
            tenant_key = str(manager.public_session.company_id)
            if tenant_key in ACTIVE_VOICE_SESSIONS:
                ACTIVE_VOICE_SESSIONS[tenant_key] = max(0, ACTIVE_VOICE_SESSIONS[tenant_key] - 1)
        await manager.close_session()
