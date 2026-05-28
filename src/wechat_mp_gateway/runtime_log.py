from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from .config import get_settings

_LOCK = Lock()


def append_log(level: str, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    log_dir = settings.runtime_path
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "message": message,
        "extra": extra or {},
    }
    path = log_dir / "gateway.jsonl"
    with _LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_logs(limit: int = 100) -> list[dict[str, Any]]:
    path = Path(get_settings().runtime_dir) / "gateway.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-max(1, limit):]
