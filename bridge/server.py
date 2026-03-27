from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bridge.session import SessionManager
from bridge.vllm_client import VLLMClient

logger = logging.getLogger(__name__)


def _make_response(transcript: str, final: bool) -> str:
    return json.dumps(
        {
            "status": 0,
            "result": {
                "hypotheses": [{"transcript": transcript}],
                "final": final,
            },
        }
    )


def create_ws_router(session_mgr: SessionManager, vllm: VLLMClient) -> APIRouter:
    router = APIRouter()

    @router.websocket("/client/ws/speech")
    async def speech_ws(ws: WebSocket) -> None:  # noqa: C901
        _ = ws.query_params.get("lm")

        if not session_mgr.check_limits():
            await ws.accept()
            await ws.send_text(json.dumps({"status": 9}))
            await ws.close()
            return

        session_id: str | None = None
        try:
            session_id = session_mgr.create_session()
            await ws.accept()
            logger.info("session %s connected", session_id)

            while True:
                msg = await ws.receive()

                if "bytes" in msg and msg["bytes"] is not None:
                    session = session_mgr.get_session(session_id)
                    if session is not None:
                        session.feed(msg["bytes"])

                elif "text" in msg and msg["text"] is not None:
                    text = msg["text"].strip()
                    if text == "EOS":
                        session = session_mgr.get_session(session_id)
                        if session is None:
                            break

                        wav_bytes = session.audio.to_wav()
                        if len(wav_bytes) <= 44:
                            await ws.send_text(_make_response("", final=True))
                            break

                        accumulated: list[str] = []
                        try:
                            async for chunk in vllm.transcribe_stream(wav_bytes):
                                accumulated.append(chunk)
                                await ws.send_text(_make_response(chunk, final=False))
                        except Exception:
                            logger.exception(
                                "session %s: vLLM transcription failed", session_id
                            )
                            await ws.send_text(json.dumps({"status": 9}))
                            break

                        full_text = "".join(accumulated)
                        await ws.send_text(_make_response(full_text, final=True))
                        break
        except WebSocketDisconnect:
            logger.info("session %s disconnected", session_id)
        except Exception:
            logger.exception("session %s: unexpected error", session_id)
            if session_id is not None:
                try:
                    await ws.send_text(json.dumps({"status": 9}))
                except Exception:
                    pass
        finally:
            if session_id is not None:
                session_mgr.remove_session(session_id)
                logger.info("session %s cleaned up", session_id)

    return router
