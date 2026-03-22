from __future__ import annotations

from typing import Any

from ghostcontext.schemas.openai_chat import ChatMessage


def message_content_as_text(content: str | list[dict[str, Any]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    parts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            parts.append(part["text"])
    return "\n".join(parts).strip()


def get_last_user_message_text(messages: list[ChatMessage]) -> str | None:
    for message in reversed(messages):
        if message.role.lower() != "user":
            continue
        text = message_content_as_text(message.content)
        if text:
            return text
    return None


def format_memory_documents(
    documents: list[str] | None,
    metadatas: list[dict[str, Any]] | None,
) -> str:
    if not documents:
        return ""
    lines: list[str] = []
    for index, doc in enumerate(documents):
        if not doc.strip():
            continue
        meta = (metadatas or [{}])[index] if index < len(metadatas or []) else {}
        stamp = meta.get("created_at") or meta.get("created") or ""
        prefix = f"[{stamp}] " if stamp else ""
        lines.append(f"{prefix}{doc.strip()}")
    return "\n\n---\n\n".join(lines)


def inject_memory_into_messages(
    messages: list[dict[str, Any]],
    memory_block: str,
) -> list[dict[str, Any]]:
    if not memory_block.strip():
        return messages
    block = (
        "Relevant past conversations (use only if relevant; prefer the current thread "
        "when information conflicts):\n"
        f"{memory_block.strip()}"
    )
    merged: list[dict[str, Any]] = [dict(m) for m in messages]
    if not merged:
        return [{"role": "system", "content": block}]
    first = merged[0]
    if first.get("role") == "system":
        existing = first.get("content")
        if isinstance(existing, str) and existing.strip():
            first["content"] = f"{existing.strip()}\n\n{block}"
        elif existing is None or existing == "":
            first["content"] = block
        else:
            merged.insert(0, {"role": "system", "content": block})
        return merged
    merged.insert(0, {"role": "system", "content": block})
    return merged
