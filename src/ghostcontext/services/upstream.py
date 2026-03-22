from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion


def build_async_openai_client(*, base_url: str, api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


def chat_completion_to_json_dict(response: ChatCompletion) -> dict[str, Any]:
    return response.model_dump(mode="json")
