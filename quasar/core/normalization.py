"""Scope-aware hostname and live URL normalization."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .targets import normalize_domain, TargetValidationError


def in_scope(hostname: str, target: str) -> bool:
    """True only when hostname equals target or is a label-boundary subdomain of it."""
    host = hostname.rstrip(".").lower()
    scope = target.rstrip(".").lower()
    return host == scope or host.endswith("." + scope)


def extract_scoped_hostnames(text: str, target: str, include_apex: bool = False) -> set[str]:
    """Extract only hostnames within target scope from noisy CLI output."""
    target = normalize_domain(target)
    # Match DNS-looking strings ending on the exact target suffix, including URLs and JSON.
    suffix = re.escape(target)
    pattern = re.compile(
        rf"(?i)(?<![a-z0-9_-])(?:\*\.)?(?:[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?\.)*{suffix}\.?"
        rf"(?![a-z0-9_-])"
    )
    found: set[str] = set()
    for match in pattern.finditer(text):
        candidate = match.group(0).strip().rstrip(".")
        if candidate.startswith("*."):
            candidate = candidate[2:]
        try:
            candidate = normalize_domain(candidate)
        except TargetValidationError:
            continue
        if not in_scope(candidate, target):
            continue
        if candidate == target and not include_apex:
            continue
        found.add(candidate)
    return found


def sorted_unique_hostnames(hostnames: set[str] | list[str] | tuple[str, ...]) -> list[str]:
    return sorted(set(hostnames), key=lambda value: (value.casefold(), value))


def extract_alive_urls(text: str, target: str, include_apex: bool = False) -> list[str]:
    """Parse ProjectDiscovery httpx output into plain responsive URLs in target scope."""
    urls: set[str] = set()
    for line in text.splitlines():
        match = re.search(r"https?://[^\s\[\]\"']+", line, flags=re.IGNORECASE)
        if not match:
            continue
        url = match.group(0).rstrip(".,;)")
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                continue
            host = normalize_domain(parsed.hostname)
        except (ValueError, TargetValidationError):
            continue
        if not in_scope(host, target):
            continue
        if host == target and not include_apex:
            continue
        # Keep the endpoint URL only, not httpx's optional status/title decoration.
        urls.add(url)
    return sorted(urls, key=lambda value: (value.casefold(), value))
