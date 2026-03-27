# kaldi-openai-bridge

A lightweight bridge server that connects Kaldi GStreamer-based speech recognition clients (like [Kõnele](https://github.com/Kaljurand/Kõnele) on Android) to OpenAI-compatible audio transcription APIs (like [vLLM](https://github.com/vllm-project/vllm)).

It accepts audio streams over WebSocket using the Kaldi server protocol, accumulates PCM audio, and forwards the complete WAV to a vLLM server for transcription.

## Quick Start

```bash
# Clone and install
git clone https://github.com/kaldi-openai-bridge/kaldi-openai-bridge.git
cd kaldi-openai-bridge
pip install -e .

# Copy and edit config
cp config.example.yaml config.yaml
# Edit config.yaml with your vLLM server URL

# Run
python -m bridge --config config.yaml
```

## Requirements

- Python 3.10+
- A running [vLLM](https://github.com/vllm-project/vllm) server with an audio model (e.g., Qwen2-Audio-7B-Instruct)

## Configuration

Copy `config.example.yaml` to `config.yaml` and adjust:

```yaml
# vLLM server URL (OpenAI-compatible endpoint)
vllm_url: "http://localhost:8000/v1"

# vLLM API key (--api-key). Omit or set to null if no auth.
# api_key: null

# WebSocket auth token. Set to null to disable auth.
# token: null

# Bridge server bind address
host: "0.0.0.0"

# Bridge server port
port: 8888

# Maximum duration per streaming session (seconds)
max_session_duration_s: 300

# Maximum concurrent WebSocket sessions
max_concurrent_sessions: 10

# Timeout for vLLM API requests (seconds)
vllm_timeout_s: 120

# Logging level (debug, info, warning, error, critical)
log_level: "info"
```

### Config Fields

| Field | Default | Description |
|-------|---------|-------------|
| `vllm_url` | `http://localhost:8000/v1` | vLLM server base URL |
| `api_key` | `null` | vLLM API key (Bearer token) |
| `token` | `null` | WebSocket auth token (query param) |
| `host` | `0.0.0.0` | Server bind address |
| `port` | `8888` | Server bind port |
| `max_session_duration_s` | `300` | Max session duration in seconds |
| `max_concurrent_sessions` | `10` | Max simultaneous connections |
| `vllm_timeout_s` | `120` | vLLM request timeout |
| `log_level` | `info` | Logging verbosity |

## Kõnele Configuration

Install [Kõnele](https://github.com/Kaljurand/Kõnele) from F-Droid or Google Play.

Configure a custom recognition service with:

- **WebSocket URL**: `ws://<your-host>:<port>/client/ws/speech`

If token auth is enabled:

- **WebSocket URL**: `ws://<your-host>:<port>/<your-token>/client/ws/speech`

For example, if the bridge runs on `192.168.1.100:8888`:

```
ws://192.168.1.100:8888/client/ws/speech
```

In Kõnele settings:
1. Go to **Settings > Speech recognition > Recognition service**
2. Add a custom service URL with the WebSocket address above
3. The bridge will handle the Kaldi protocol and return transcriptions

## Architecture

```
┌─────────────────┐         WebSocket          ┌──────────────────┐
│                 │  Kaldi protocol (PCM)      │                  │
│  Kõnele (Android)│ ─────────────────────────> │  kaldi-openai-   │
│  or any Kaldi   │                             │  bridge          │
│  GStreamer client│ <───────────────────────── │                  │
│                 │  Kaldi responses (JSON)     │                  │
└─────────────────┘                             └────────┬─────────┘
                                                         │
                                                         │ HTTP POST
                                                         │ multipart/form-data
                                                         │ (WAV file)
                                                         ▼
                                                ┌──────────────────┐
                                                │                  │
                                                │  vLLM Server     │
                                                │  (OpenAI-compat) │
                                                │                  │
                                                └──────────────────┘
```

### How It Works

1. **Audio Collection**: Kõnele streams raw PCM audio (16kHz, 16-bit, mono) over WebSocket
2. **Session Management**: Each connection gets an isolated audio buffer
3. **EOS Trigger**: When Kõnele sends "EOS", the bridge stops accepting audio
4. **vLLM Request**: Complete audio is converted to WAV and sent to vLLM `/v1/audio/transcriptions`
5. **Streaming Response**: Transcription chunks are streamed back as Kaldi protocol responses

### Modules

| Module | Purpose |
|--------|---------|
| `server.py` | WebSocket endpoint and Kaldi protocol handling |
| `session.py` | Session and audio buffer management |
| `vllm_client.py` | HTTP client for vLLM streaming API |
| `audio.py` | PCM to WAV conversion |
| `sse_parser.py` | Server-Sent Events parser for vLLM responses |
| `config.py` | YAML config loading and validation |

## Development

```bash
# Install in dev mode
pip install -e .

# Run with debug logging
python -m bridge --config config.yaml
# (set log_level: "debug" in config.yaml)
```

## License

MIT
