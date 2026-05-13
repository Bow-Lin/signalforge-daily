from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI


DEFAULT_BASE_URL = "https://apis.iflow.cn/v1"
DEFAULT_MODEL = "qwen3-max"


@dataclass(frozen=True)
class IFlowConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.2
    max_tokens: int = 16384


def load_iflow_config(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> IFlowConfig:
    key = api_key or os.getenv("IFLOW_API_KEY")
    if not key:
        raise ValueError(
            "IFLOW_API_KEY not set; provide --iflow-key or set IFLOW_API_KEY"
        )
    return IFlowConfig(
        api_key=key,
        base_url=base_url or DEFAULT_BASE_URL,
        model=model or DEFAULT_MODEL,
    )


def create_iflow_client(config: IFlowConfig) -> OpenAI:
    return OpenAI(base_url=config.base_url, api_key=config.api_key)
