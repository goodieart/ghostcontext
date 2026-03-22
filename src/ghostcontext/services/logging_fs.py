from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def append_exchange_to_daily_log(
    *,
    log_dir: Path,
    user_text: str,
    assistant_text: str,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = log_dir / f"{day}.md"
    stamp = datetime.now(timezone.utc).isoformat()
    block = (
        f"\n## Exchange — {stamp} (UTC)\n\n"
        f"### Запрос\n\n{user_text.strip()}\n\n"
        f"### Ответ\n\n{assistant_text.strip()}\n\n"
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(block)
