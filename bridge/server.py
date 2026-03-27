from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bridge.config import BridgeConfig
from bridge.session import SessionManager
from bridge.vllm_client import VLLMClient

logger = logging.getLogger(__name__)


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


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


def create_ws_router(
    config: BridgeConfig, session_mgr: SessionManager, vllm: VLLMClient
) -> APIRouter:
    router = APIRouter()

    async def handle_speech(ws: WebSocket, token: str | None = None) -> None:
        if config.token is not None and token != config.token:
            await ws.close(code=1008)
            return

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

                        duration_s = session.audio.duration_s()
                        wav_size = len(wav_bytes)
                        t0 = time.monotonic()

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

                        elapsed = time.monotonic() - t0
                        full_text = "".join(accumulated)
                        logger.info(
                            "session %s: duration=%.1fs wav=%s elapsed=%.3fs",
                            session_id,
                            duration_s,
                            _format_bytes(wav_size),
                            elapsed,
                        )
                        await ws.send_text(_make_response(full_text, final=True))

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
            await ws.close()

    @router.websocket("/{token}/client/ws/speech")
    async def speech_ws_with_token(ws: WebSocket, token: str) -> None:
        await handle_speech(ws, token)

    @router.websocket("/{token}/client/ws/status")
    async def status_ws(ws: WebSocket, token: str) -> None:
        await ws.accept()

        if config.token is not None and token != config.token:
            await ws.close(code=1008)
            return

        await ws.send_text(
            json.dumps(
                {
                    "status": 0,
                    "num_workers_available": session_mgr.available_slots(),
                }
            )
        )
        await ws.close()

    return router
