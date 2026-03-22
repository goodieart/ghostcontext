from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from chromadb.api.models.Collection import Collection
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, OpenAIError

from ghostcontext.schemas.openai_chat import ChatCompletionRequest
from ghostcontext.services.logging_fs import append_exchange_to_daily_log
from ghostcontext.services.memory import (
    format_memory_documents,
    get_last_user_message_text,
    inject_memory_into_messages,
)
from ghostcontext.services.upstream import chat_completion_to_json_dict

logger = logging.getLogger(__name__)

router = APIRouter(tags=["openai"])

_ALLOWED_CHAT_KEYS = frozenset({
    "model",
    "messages",
    "temperature",
    "top_p",
    "max_tokens",
    "stop",
    "presence_penalty",
    "frequency_penalty",
    "user",
    "tools",
    "tool_choice",
    "response_format",
    "seed",
    "logit_bias",
    "logprobs",
    "top_logprobs",
    "parallel_tool_calls",
    "modalities",
    "reasoning_effort",
    "verbosity",
})


def _openai_error_response(
    *,
    status_code: int,
    message: str,
    error_type: str,
    code: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "code": code,
            }
        },
    )


def _resolve_model(request_model: str | None, default_upstream_model: str | None) -> str:
    if request_model and request_model.strip():
        return request_model.strip()
    if default_upstream_model and default_upstream_model.strip():
        return default_upstream_model.strip()
    return "local-model"


@router.get("/v1/models")
async def list_models(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": settings.proxy_model_id,
                "object": "model",
                "created": created,
                "owned_by": "ghostcontext",
            }
        ],
    }


@router.post("/v1/chat/completions", response_model=None)
async def create_chat_completion(
    request: Request,
    body: ChatCompletionRequest,
) -> dict[str, Any] | JSONResponse:
    if body.stream:
        return _openai_error_response(
            status_code=501,
            message=(
                "Streaming is not implemented in this MVP. "
                "Set stream=false in the request (most clients allow this in settings)."
            ),
            error_type="not_implemented_error",
            code="stream_not_supported",
        )

    if not body.messages:
        return _openai_error_response(
            status_code=400,
            message="You must provide a non-empty messages array.",
            error_type="invalid_request_error",
            code="empty_messages",
        )

    settings = request.app.state.settings
    collection: Collection = request.app.state.collection
    llm_client: AsyncOpenAI = request.app.state.llm_client

    last_user_text = get_last_user_message_text(body.messages)
    memory_text = ""
    if last_user_text:

        def _query_chroma() -> dict[str, Any]:
            return collection.query(
                query_texts=[last_user_text],
                n_results=settings.n_results,
                include=["documents", "metadatas", "distances"],
            )

        try:
            raw = await asyncio.to_thread(_query_chroma)
        except Exception:
            logger.exception("ChromaDB query failed; continuing without retrieved memory")
            raw = {}

        documents = (raw.get("documents") or [[]])[0] or []
        metadatas = (raw.get("metadatas") or [[]])[0] or []
        memory_text = format_memory_documents(documents, metadatas)

    messages_payload = [
        message.model_dump(exclude_none=True, mode="json") for message in body.messages
    ]
    forwarded_messages = inject_memory_into_messages(messages_payload, memory_text)

    raw_kwargs = body.model_dump(exclude_none=True, mode="json")
    kwargs = {key: value for key, value in raw_kwargs.items() if key in _ALLOWED_CHAT_KEYS}
    kwargs["messages"] = forwarded_messages
    kwargs["stream"] = False
    kwargs["model"] = _resolve_model(body.model, settings.default_upstream_model)
    if kwargs.get("n", 1) != 1:
        kwargs.pop("n", None)

    try:
        response = await llm_client.chat.completions.create(**kwargs)
    except OpenAIError as exc:
        logger.warning("Upstream OpenAI-compatible error: %s", exc)
        status_code = int(getattr(exc, "status_code", None) or 502)
        message = str(getattr(exc, "message", None) or exc)
        return _openai_error_response(
            status_code=status_code,
            message=message,
            error_type="upstream_error",
            code="upstream_request_failed",
        )
    except Exception as exc:
        logger.exception("Upstream request failed")
        return _openai_error_response(
            status_code=502,
            message=str(exc),
            error_type="upstream_error",
            code="upstream_request_failed",
        )

    assistant_text = ""
    if response.choices:
        content = response.choices[0].message.content
        if isinstance(content, str):
            assistant_text = content

    if last_user_text:

        def _persist() -> None:
            created_at = datetime.now(timezone.utc).isoformat()
            document = f"Q: {last_user_text}\nA: {assistant_text}"
            collection.add(
                documents=[document],
                ids=[str(uuid4())],
                metadatas=[
                    {
                        "created_at": created_at,
                        "source": "ghostcontext",
                    }
                ],
            )
            append_exchange_to_daily_log(
                log_dir=settings.log_dir,
                user_text=last_user_text,
                assistant_text=assistant_text,
            )

        try:
            await asyncio.to_thread(_persist)
        except Exception:
            logger.exception("Persisting exchange to Chroma or disk failed")

    return chat_completion_to_json_dict(response)
