#!/usr/bin/env python3
"""CLI entry point for Quasar."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from quasar import __version__ as APP_VERSION
from quasar.banner import show_banner
from quasar.core.engine import check_tools_only, run_assessment
from quasar.core.targets import TargetValidationError



def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.is_file():
        raise ValueError(f"Configuration file does not exist: {config_path}")
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read JSON configuration {config_path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError("Configuration root must be a JSON object.")
    return loaded


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="Quasar",
        description="Quasar: cross-platform authorized subdomain enumeration and HTTP/HTTPS availability checking.",
        epilog="Use only for domains you own or are explicitly authorized to assess."
    )
    parser.add_argument("--domain", help="Single domain, e.g. example.com")
    parser.add_argument("--list", dest="list", help="Text file containing one domain per line")
    parser.add_argument("--output-dir", default="results", help="Parent directory for timestamped assessment results (default: results)")
    parser.add_argument("--config", help="Optional JSON configuration file")
    parser.add_argument("--no-install", action="store_true", help="Check dependencies but do not attempt automatic installation")
    parser.add_argument("--strict-dependencies", action="store_true", help="Abort enumeration if any of the 12 requested tools is unavailable")
    parser.add_argument("--check-tools", action="store_true", help="Only check/install dependencies and write a setup report")
    parser.add_argument("--include-apex", action="store_true", help="Include the target apex domain in final subdomain/live results")
    parser.add_argument("--tool-timeout", type=int, default=None, help="Per-tool timeout in seconds (default: 600)")
    parser.add_argument("--source-timeout", type=int, default=None, help="Subfinder source timeout in seconds (default: 30)")
    parser.add_argument("--source-max-minutes", type=int, default=None, help="Subfinder maximum runtime in minutes (default: 5)")
    parser.add_argument("--httpx-timeout", type=int, default=None, help="HTTPX timeout in seconds per probe (default: 8)")
    parser.add_argument("--httpx-threads", type=int, default=None, help="HTTPX concurrency (default: 10)")
    parser.add_argument("--httpx-retries", type=int, default=None, help="HTTPX retries (default: 1)")
    parser.add_argument("--resolvers", help="Optional PureDNS resolver list file")
    parser.add_argument("--trusted-resolvers", help="Optional PureDNS trusted resolver list file")
    parser.add_argument("--version", action="version", version=f"Quasar {APP_VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    show_banner()
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = load_config(args.config)
    except ValueError as exc:
        print(f"[!] Configuration error: {exc}", file=sys.stderr)
        return 2

    cli_values = {
        "tool_timeout": (args.tool_timeout, 600),
        "source_timeout": (args.source_timeout, 30),
        "source_max_minutes": (args.source_max_minutes, 5),
        "httpx_timeout": (args.httpx_timeout, 8),
        "httpx_threads": (args.httpx_threads, 10),
        "httpx_retries": (args.httpx_retries, 1),
    }
    for key, (cli_value, default_value) in cli_values.items():
        if cli_value is not None:
            config[key] = cli_value
        else:
            config.setdefault(key, default_value)
    if args.resolvers:
        config["resolvers_file"] = args.resolvers
    if args.trusted_resolvers:
        config["trusted_resolvers_file"] = args.trusted_resolvers

    try:
        numeric_config = {key: int(config[key]) for key in cli_values}
    except (TypeError, ValueError, KeyError) as exc:
        print(f"[!] Timeout/concurrency configuration must contain valid integers: {exc}", file=sys.stderr)
        return 2
    if (numeric_config["tool_timeout"] < 1 or numeric_config["source_timeout"] < 1
            or numeric_config["source_max_minutes"] < 1 or numeric_config["httpx_timeout"] < 1
            or numeric_config["httpx_threads"] < 1 or numeric_config["httpx_retries"] < 0):
        print("[!] Timeouts/threads must be positive and retries must be non-negative.", file=sys.stderr)
        return 2
    if args.check_tools:
        return check_tools_only(args, config)

    if bool(args.domain) == bool(args.list):
        if args.domain or args.list:
            print("[!] Specify exactly one of --domain or --list.", file=sys.stderr)
            return 2
        if not sys.stdin.isatty():
            print("[!] Provide --domain or --list (or run --check-tools).", file=sys.stderr)
            return 2
        value = input("Enter a domain or path to a domain-list file: ").strip()
        if not value:
            print("[!] No target entered.", file=sys.stderr)
            return 2
        if Path(value).is_file():
            args.list = value
        else:
            args.domain = value
    try:
        return run_assessment(args, config)
    except TargetValidationError as exc:
        print(f"[!] Target error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user. Any completed raw outputs are preserved.", file=sys.stderr)
        return 130
    except Exception as exc:
        logging.exception("Unexpected error")
        print(f"[!] Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
