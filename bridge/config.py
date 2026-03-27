"""Configuration module for kaldi-openai-bridge."""

import argparse
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class BridgeConfig(BaseModel):
    """Configuration model for the bridge service."""

    vllm_url: str = Field(description="vLLM server URL")
    api_key: str | None = Field(default=None, description="vLLM API key (--api-key)")
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8000, description="Server port")
    max_session_duration_s: int = Field(
        default=60, description="Max session duration in seconds"
    )
    max_concurrent_sessions: int = Field(
        default=10, description="Max concurrent sessions"
    )
    vllm_timeout_s: float = Field(
        default=30, description="vLLM request timeout in seconds"
    )
    log_level: str = Field(default="info", description="Logging level")


def load_config(path: str) -> BridgeConfig:
    """Load configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        BridgeConfig instance with loaded values.
    """
    config_path = Path(path)
    with config_path.open() as f:
        data = yaml.safe_load(f)
    return BridgeConfig(**data)


def parse_args() -> BridgeConfig:
    """Parse CLI arguments and load configuration.

    Returns:
        BridgeConfig instance from CLI-specified config file.
    """
    parser = argparse.ArgumentParser(description="kaldi-openai-bridge")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration YAML file (default: config.yaml)",
    )
    args = parser.parse_args()
    return load_config(args.config)
