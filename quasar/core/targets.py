"""Domain input validation and normalization."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


class TargetValidationError(ValueError):
    """Raised when a target is not a valid DNS domain name."""


def normalize_domain(value: str) -> str:
    """Normalize a domain to ASCII IDNA lower-case form; reject URLs and host:port inputs."""
    if not isinstance(value, str):
        raise TargetValidationError("Domain must be text.")
    raw = value.strip().rstrip(".")
    if not raw:
        raise TargetValidationError("Domain cannot be empty.")
    if any(ch in raw for ch in "/\\@?#") or ":" in raw or raw.startswith("*."):
        raise TargetValidationError("Provide a domain name only (no URL, path, port, or wildcard).")
    try:
        ascii_domain = raw.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise TargetValidationError("Domain contains an invalid internationalized label.") from exc
    if len(ascii_domain) > 253 or "." not in ascii_domain:
        raise TargetValidationError("A fully qualified domain name with at least one dot is required.")
    labels = ascii_domain.split(".")
    if any(not label or len(label) > 63 or not _LABEL_RE.fullmatch(label) for label in labels):
        raise TargetValidationError("Domain contains an invalid DNS label.")
    return ascii_domain


def load_targets_with_originals(domain: str | None = None, list_path: str | Path | None = None) -> tuple[list[str], list[dict[str, str]], dict[str, str]]:
    """Load, normalize, and deduplicate targets, preserving the first original input for each target."""
    if bool(domain) == bool(list_path):
        raise TargetValidationError("Specify exactly one of --domain or --list.")
    entries: list[str] = []
    if domain:
        entries.append(domain)
    else:
        path = Path(list_path)  # type: ignore[arg-type]
        if not path.is_file():
            raise TargetValidationError(f"Target list does not exist or is not a file: {path}")
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    entries.append(stripped)
        except OSError as exc:
            raise TargetValidationError(f"Unable to read target list {path}: {exc}") from exc

    accepted: list[str] = []
    rejected: list[dict[str, str]] = []
    originals: dict[str, str] = {}
    seen: set[str] = set()
    for original in entries:
        try:
            normalized = normalize_domain(original)
        except TargetValidationError as exc:
            rejected.append({"input": original, "reason": str(exc)})
            continue
        if normalized not in seen:
            accepted.append(normalized)
            originals[normalized] = original
            seen.add(normalized)
    if not accepted:
        detail = "; ".join(f"{r['input']!r}: {r['reason']}" for r in rejected) or "no targets found"
        raise TargetValidationError(f"No valid targets supplied ({detail}).")
    return accepted, rejected, originals


def load_targets(domain: str | None = None, list_path: str | Path | None = None) -> tuple[list[str], list[dict[str, str]]]:
    """Compatibility helper returning targets and invalid rows."""
    targets, rejected, _ = load_targets_with_originals(domain=domain, list_path=list_path)
    return targets, rejected
