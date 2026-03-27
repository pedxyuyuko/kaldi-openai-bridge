"""Application factory for kaldi-openai-bridge."""

from fastapi import FastAPI

from bridge.config import BridgeConfig
from bridge.server import create_ws_router
from bridge.session import SessionManager
from bridge.vllm_client import VLLMClient


def create_app(config: BridgeConfig) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Bridge configuration.

    Returns:
        Configured FastAPI app with WebSocket router registered.
    """
    app = FastAPI()

    session_mgr = SessionManager(config)
    vllm = VLLMClient(config)
    router = create_ws_router(config, session_mgr, vllm)
    app.include_router(router)

    return app
