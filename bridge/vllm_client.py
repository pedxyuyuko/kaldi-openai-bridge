"""VLLM client for async HTTP communication with vLLM server."""

import logging
from collections.abc import AsyncIterator

import httpx

from bridge.config import BridgeConfig
from bridge.sse_parser import extract_transcription_text, is_stream_done, parse_sse_line

logger = logging.getLogger(__name__)


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
        data = {"stream": "true"}

        headers: dict[str, str] = {}
        if self._config.api_key is not None:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        log_headers = {
            k: (v[:16] + "..." if len(v) > 16 else v) for k, v in headers.items()
        }
        logger.debug("POST %s", url)
        logger.debug("headers: %s", log_headers)

        async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
            async with client.stream("POST", url, files=files, data=data) as response:
                response.raise_for_status()
                logger.debug("response status: %d", response.status_code)

                in_asr = False
                async for line in response.aiter_lines():
                    logger.debug("sse line: %s", line)

                    sse_data = parse_sse_line(line)
                    if sse_data is None:
                        continue

                    if is_stream_done(sse_data):
                        break

                    text = extract_transcription_text(sse_data)
                    if not text:
                        continue

                    if "<asr_text>" in text:
                        in_asr = True
                        continue

                    if not in_asr:
                        continue

                    if text.startswith("<") and text.endswith(">"):
                        continue

                    yield text
