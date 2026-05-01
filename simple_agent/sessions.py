from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_messages(session_file: Path | None) -> list[dict[str, Any]]:
    if session_file is None or not session_file.exists():
        return []
    messages: list[dict[str, Any]] = []
    with session_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            messages.append(json.loads(line))
    return messages


def append_messages(session_file: Path | None, messages: list[dict[str, Any]]) -> None:
    if session_file is None:
        return
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with session_file.open("a", encoding="utf-8") as handle:
        for message in messages:
            handle.write(json.dumps(message, ensure_ascii=False) + "\n")
