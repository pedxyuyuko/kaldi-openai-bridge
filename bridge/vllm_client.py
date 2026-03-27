"""VLLM client for async HTTP communication with vLLM server."""

from collections.abc import AsyncIterator

import httpx

from bridge.config import BridgeConfig
from bridge.sse_parser import extract_transcription_text, is_stream_done, parse_sse_line


class VLLMClient:
    def __init__(self, config: BridgeConfig) -> None:
        self._config: BridgeConfig = config
        self._base_url: str = config.vllm_url.rstrip("/")
        self._timeout: httpx.Timeout = httpx.Timeout(config.vllm_timeout_s)

    async def transcribe_stream(self, wav_bytes: bytes) -> AsyncIterator[str]:
        """Yields transcription text chunks from vLLM streaming API.

        Raises httpx.HTTPStatusError on HTTP errors, httpx.ConnectError on connection
        failures, httpx.TimeoutException on timeout.
        """
        url = f"{self._base_url}/v1/audio/transcriptions"

        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {
            "model": self._config.vllm_model,
            "stream": "true",
        }
        if self._config.language is not None:
            data["language"] = self._config.language

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", url, files=files, data=data) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    sse_data = parse_sse_line(line)
                    if sse_data is None:
                        continue

                    if is_stream_done(sse_data):
                        break

                    text = extract_transcription_text(sse_data)
                    if text:
                        yield text
