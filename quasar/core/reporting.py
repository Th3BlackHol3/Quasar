"""Report serialization and durable text writes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_lines(path: str | Path, lines: list[str]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(lines)
    destination.write_text((body + "\n") if body else "", encoding="utf-8")


def write_text(path: str | Path, value: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(value, encoding="utf-8", errors="replace")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_assessment_dir(root: str | Path) -> tuple[str, Path]:
    # External tools run with cwd set to the target folder. Keep every artifact
    # path absolute so relative CLI output paths are not accidentally resolved
    # relative to that nested working directory.
    base = Path(root).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    candidate = base / stamp
    suffix = 1
    while candidate.exists():
        candidate = base / f"{stamp}_{suffix:02d}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate.name, candidate
