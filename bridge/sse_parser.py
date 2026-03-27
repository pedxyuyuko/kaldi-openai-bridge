"""SSE (Server-Sent Events) parser for vLLM streaming responses."""

import json
from typing import Any


def parse_sse_line(line: str) -> dict[str, Any] | None:
    """Parse an SSE 'data: ...' line into a dict, or None for [DONE]."""
    stripped = line.strip()
    if not stripped.startswith("data:"):
        return None

    payload = stripped[5:].strip()
    if payload == "[DONE]":
        return None

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def extract_transcription_text(sse_data: dict[str, Any]) -> str | None:
    """Extract transcription text from sse_data choices[0].delta.content."""
    try:
        return sse_data["choices"][0]["delta"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def is_stream_done(sse_data: dict[str, Any]) -> bool:
    """Return True if finish_reason is 'stop'."""
    try:
        return sse_data["choices"][0]["finish_reason"] == "stop"
    except (KeyError, IndexError, TypeError):
        return False
