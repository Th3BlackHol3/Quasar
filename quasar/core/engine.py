"""End-to-end assessment workflow."""
from __future__ import annotations

import json
import logging
import os
import platform
import re
import time
from pathlib import Path
from typing import Any

from .dependencies import DependencyManager
from .normalization import extract_alive_urls, extract_scoped_hostnames, sorted_unique_hostnames
from .process_runner import ProcessResult, run_process
from .reporting import create_assessment_dir, utc_now, write_json, write_lines, write_text
from .targets import load_targets_with_originals
from ..modules import httpx as httpx_adapter, puredns as puredns_adapter
from ..modules.registry import BY_KEY, TOOL_SPECS

LOG = logging.getLogger("quasar")


def _read_artifact_texts(directory: Path) -> list[tuple[str, str]]:
    """Read likely text artifacts produced by tools (excluding our final outputs and logs)."""
    if not directory.exists():
        return []
    suffixes = {".txt", ".json", ".jsonl", ".xml", ".csv", ".html", ".htm", ".log", ".yaml", ".yml"}
    results: list[tuple[str, str]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        try:
            # Limit individual artifacts to keep accidental huge reports from consuming memory.
            if path.stat().st_size > 20_000_000:
                continue
            results.append((str(path), path.read_text(encoding="utf-8", errors="replace")))
        except OSError as exc:
            LOG.warning("Unable to read tool artifact %s: %s", path, exc)
    return results


def _setup_text(setup: dict[str, Any]) -> str:
    managers = setup.get("available_package_managers_and_runtimes", [])
    lines = [
        "Quasar - Dependency Setup Report",
        f"Application version: {setup.get('application_version', 'unknown')}",
        f"Timestamp (UTC): {setup.get('timestamp_utc')}",
        f"Operating system: {setup.get('platform_system', setup.get('platform'))} {setup.get('platform_release', '')}".rstrip(),
        f"Platform identifier: {setup.get('platform')} | Architecture: {setup.get('architecture', platform.machine())}",
        f"Python: {setup.get('python')} | Executable: {setup.get('python_executable', 'n/a')}",
        f"Quasar user data directory: {setup.get('quasar_data_directory', 'n/a')}",
        f"Detected runtimes/package managers: {', '.join(managers) if managers else 'none detected'}",
        f"Automatic installation enabled: {setup.get('auto_install_enabled')}",
        "",
        "Tool status:",
    ]
    for tool in setup.get("tools", []):
        lines.append(f"- {tool.get('tool')}: {tool.get('status')} | path={tool.get('path') or 'n/a'}")
        if tool.get("error"):
            lines.append(f"    Error: {tool['error']}")
        for candidate in tool.get("candidate_diagnostics", []):
            lines.append(f"    Candidate: {candidate.get('path')} | verified={candidate.get('verified')} | {candidate.get('detail')}")
        installation = tool.get("installation")
        if installation and installation.get("method"):
            lines.append(f"    Installer: {installation.get('method')} ({installation.get('status')})")
        if tool.get("platform_note"):
            lines.append(f"    Platform note: {tool['platform_note']}")
    lines.append("")
    lines.append("Extra prerequisites:")
    for item in setup.get("extra_prerequisites", []):
        lines.append(f"- {item.get('name')}: {item.get('status')} | {item.get('note', '')}")
    lines.append("")
    lines.append("Note: 'available' confirms a CLI/version/help probe, not successful end-to-end enumeration.")
    return "\n".join(lines) + "\n"


def _tool_by_key(setup: dict[str, Any], key: str) -> dict[str, Any] | None:
    spec = BY_KEY[key]
    for row in setup.get("tools", []):
        if row.get("tool") == spec.display_name:
            return row
    return None


def _verified_path(setup: dict[str, Any], key: str) -> str | None:
    row = _tool_by_key(setup, key)
    if not row or row.get("status") not in {"available", "installed_and_verified"}:
        return None
    return row.get("path")


def _write_tool_result_files(raw_dir: Path, normalized_dir: Path, display_name: str,
                             stdout: str = "", stderr: str = "", hostnames: set[str] | None = None) -> None:
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "", display_name)
    write_text(raw_dir / f"{safe_name}_raw.txt", stdout)
    write_text(raw_dir / f"{safe_name}_stderr.log", stderr)
    write_lines(normalized_dir / f"{safe_name}_subdomains.txt", sorted_unique_hostnames(hostnames or set()))


def _result_summary(tool: str, status: str, duration: float = 0, returncode: int | None = None,
                    count: int = 0, error: str | None = None, command: list[str] | None = None) -> dict[str, Any]:
    return {
        "tool": tool,
        "status": status,
        "duration_seconds": round(duration, 2),
        "returncode": returncode,
        "candidate_count": count,
        "error": error,
        "command": command,
    }


def _run_one_enumerator(key: str, target: str, tool_row: dict[str, Any] | None,
                        target_dir: Path, config: dict[str, Any], include_apex: bool) -> tuple[dict[str, Any], set[str]]:
    spec = BY_KEY[key]
    raw_dir = target_dir / "raw"
    normalized_dir = target_dir / "tool_subdomains"
    artifact_dir = target_dir / "artifacts" / key
    for folder in (raw_dir, normalized_dir, artifact_dir):
        folder.mkdir(parents=True, exist_ok=True)
    if not tool_row or tool_row.get("status") not in {"available", "installed_and_verified"} or not tool_row.get("path"):
        err = (tool_row or {}).get("error") or "Tool is not installed or failed verification; see setup_report.txt."
        _write_tool_result_files(raw_dir, normalized_dir, spec.display_name, stderr=err)
        return _result_summary(spec.display_name, "skipped_missing", error=err), set()

    executable = tool_row["path"]
    if key == "puredns":
        return _run_puredns(target, target_dir, config, include_apex, executable)
    if spec.adapter is None:
        err = "No enumeration adapter is configured for this tool."
        _write_tool_result_files(raw_dir, normalized_dir, spec.display_name, stderr=err)
        return _result_summary(spec.display_name, "failed", error=err), set()

    try:
        command = spec.adapter(executable, target, raw_dir, artifact_dir, config)
    except Exception as exc:  # adapter failures should not stop other tools
        _write_tool_result_files(raw_dir, normalized_dir, spec.display_name, stderr=f"Adapter error: {exc}")
        return _result_summary(spec.display_name, "failed", error=f"Adapter error: {exc}"), set()

    print(f"[+] {target}: running {spec.display_name} ...", flush=True)
    result = run_process(command, timeout=int(config.get("tool_timeout", 600)), cwd=target_dir)
    # Preserve raw stdout and stderr exactly as captured; native artifacts remain under artifacts/<tool>.
    artifact_texts = _read_artifact_texts(artifact_dir)
    candidate_text = result.stdout + "\n" + "\n".join(value for _, value in artifact_texts)
    candidates = extract_scoped_hostnames(candidate_text, target, include_apex=include_apex)
    _write_tool_result_files(raw_dir, normalized_dir, spec.display_name, result.stdout, result.stderr, candidates)

    # Archive a small execution metadata record next to any native outputs.
    write_json(artifact_dir / "execution.json", {
        "tool": spec.display_name,
        "command": command,
        "returncode": result.returncode,
        "duration_seconds": round(result.duration_seconds, 2),
        "timed_out": result.timed_out,
        "error": result.error,
    })
    if result.error:
        status = "failed"
        error = result.error
    elif result.timed_out:
        status = "partial" if candidates else "timed_out"
        error = result.error
    elif result.returncode == 0:
        status = "success"
        error = None
    elif candidates:
        status = "partial"
        error = f"Process exited with code {result.returncode}; usable candidates were retained."
    else:
        status = "failed"
        error = f"Process exited with code {result.returncode}. Check raw stderr and setup prerequisites."
    print(f"    {status}: {len(candidates)} scoped candidate(s)", flush=True)
    return _result_summary(spec.display_name, status, result.duration_seconds, result.returncode,
                           len(candidates), error, command), candidates


def _run_puredns(target: str, target_dir: Path, config: dict[str, Any], include_apex: bool,
                 executable: str) -> tuple[dict[str, Any], set[str]]:
    spec = BY_KEY["puredns"]
    raw_dir, normalized_dir = target_dir / "raw", target_dir / "tool_subdomains"
    artifact_dir = target_dir / "artifacts" / "puredns"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    other_candidate_files = sorted(normalized_dir.glob("*_subdomains.txt"))
    candidates = set()
    for path in other_candidate_files:
        if path.name == "PureDNS_subdomains.txt":
            continue
        try:
            candidates.update(extract_scoped_hostnames(path.read_text(encoding="utf-8", errors="replace"), target, include_apex))
        except OSError:
            continue
    candidate_input = artifact_dir / "candidates_to_resolve.txt"
    write_lines(candidate_input, sorted_unique_hostnames(candidates))
    resolved_output = artifact_dir / "PureDNS_resolved.txt"
    if not candidates:
        _write_tool_result_files(raw_dir, normalized_dir, spec.display_name,
                                 stderr="Skipped because preceding tools produced no scoped candidates.")
        return _result_summary(spec.display_name, "skipped_no_candidates", count=0), set()

    command = puredns_adapter.build_resolve_command(executable, candidate_input, resolved_output, config)
    print(f"[+] {target}: running PureDNS candidate resolution ...", flush=True)
    result = run_process(command, timeout=int(config.get("tool_timeout", 600)), cwd=target_dir)
    artifact_text = ""
    if resolved_output.exists():
        artifact_text = resolved_output.read_text(encoding="utf-8", errors="replace")
    resolved = extract_scoped_hostnames((result.stdout or "") + "\n" + artifact_text, target, include_apex)
    _write_tool_result_files(raw_dir, normalized_dir, spec.display_name, result.stdout, result.stderr, resolved)
    write_json(artifact_dir / "execution.json", {
        "tool": spec.display_name, "command": command, "returncode": result.returncode,
        "duration_seconds": round(result.duration_seconds, 2), "timed_out": result.timed_out, "error": result.error,
        "candidate_input_count": len(candidates), "resolved_count": len(resolved),
    })
    if result.error:
        status, error = "failed", result.error
    elif result.returncode == 0:
        status, error = "success", None
    elif resolved:
        status, error = "partial", f"Process exited with code {result.returncode}; usable candidates retained."
    else:
        status, error = "failed", f"Process exited with code {result.returncode}. Confirm MassDNS/resolver configuration."
    print(f"    {status}: {len(resolved)} resolved candidate(s)", flush=True)
    return _result_summary(spec.display_name, status, result.duration_seconds, result.returncode,
                           len(resolved), error, command), resolved


def _run_httpx(target: str, target_dir: Path, setup: dict[str, Any], config: dict[str, Any],
               include_apex: bool, final_hosts: list[str]) -> tuple[dict[str, Any], list[str]]:
    spec = BY_KEY["httpx"]
    raw_dir, normalized_dir = target_dir / "raw", target_dir / "tool_subdomains"
    artifact_dir = target_dir / "artifacts" / "httpx"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    alive_file = target_dir / "Alive_Subdomains.txt"
    details_file = target_dir / "Alive_Subdomains_Details.txt"
    input_file = artifact_dir / "httpx_input.txt"
    write_lines(input_file, final_hosts)
    executable = _verified_path(setup, "httpx")
    if not executable:
        err = "ProjectDiscovery HTTPX was not found or failed fingerprint verification; Python httpx is not a substitute."
        _write_tool_result_files(raw_dir, normalized_dir, spec.display_name, stderr=err)
        write_lines(alive_file, [])
        write_lines(details_file, [])
        return _result_summary(spec.display_name, "skipped_missing", error=err), []
    if not final_hosts:
        _write_tool_result_files(raw_dir, normalized_dir, spec.display_name,
                                 stderr="Skipped because Final_Subdomains.txt is empty.")
        write_lines(alive_file, [])
        write_lines(details_file, [])
        return _result_summary(spec.display_name, "skipped_no_candidates"), []
    httpx_output_file = artifact_dir / "httpx_results.txt"
    command = httpx_adapter.build_command(executable, input_file, config, httpx_output_file)
    print(f"[+] {target}: checking HTTP/HTTPS with ProjectDiscovery HTTPX ...", flush=True)
    result = run_process(command, timeout=int(config.get("httpx_run_timeout", config.get("tool_timeout", 600))), cwd=target_dir)
    file_output = ""
    if httpx_output_file.is_file():
        try:
            file_output = httpx_output_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            LOG.warning("Unable to read HTTPX output file %s: %s", httpx_output_file, exc)
    combined_output = "\n".join(part for part in (result.stdout, file_output) if part.strip())
    alive_urls = extract_alive_urls(combined_output, target, include_apex=include_apex)
    # Only plain responsive URLs in the required file; optional details can be enabled separately.
    write_lines(alive_file, alive_urls)
    if config.get("httpx_details", False):
        write_text(details_file, combined_output)
    else:
        write_lines(details_file, [])
    alive_hosts: set[str] = set()
    for url in alive_urls:
        alive_hosts.update(extract_scoped_hostnames(url, target, include_apex=include_apex))
    raw_httpx = combined_output or result.stdout
    _write_tool_result_files(raw_dir, normalized_dir, spec.display_name, raw_httpx, result.stderr, alive_hosts)
    write_json(artifact_dir / "execution.json", {
        "tool": spec.display_name, "command": command, "returncode": result.returncode,
        "duration_seconds": round(result.duration_seconds, 2), "timed_out": result.timed_out,
        "error": result.error, "responsive_url_count": len(alive_urls),
        "stdout_bytes": len(result.stdout.encode("utf-8")),
        "output_file": str(httpx_output_file), "output_file_bytes": len(file_output.encode("utf-8")),
    })
    if result.error:
        status = "timed_out" if result.timed_out else "failed"
        detail = result.error
        if result.stderr.strip():
            detail += f"; stderr: {result.stderr.strip()[-800:]}"
        error = detail
    elif result.returncode == 0:
        status, error = "success", None
    elif alive_urls:
        status, error = "partial", f"Process exited with code {result.returncode}; responsive URLs retained."
    else:
        diagnostic = (result.stderr or result.stdout).strip()
        if diagnostic:
            diagnostic = diagnostic[-1000:]
            error = f"ProjectDiscovery HTTPX exited with code {result.returncode} and returned no responsive URLs. Diagnostic: {diagnostic}"
        else:
            error = f"ProjectDiscovery HTTPX exited with code {result.returncode} and returned no responsive URLs; see raw stderr and artifacts/httpx/execution.json."
        status = "failed"
    print(f"    {status}: {len(alive_urls)} responsive URL(s)", flush=True)
    return _result_summary(spec.display_name, status, result.duration_seconds, result.returncode,
                           len(alive_urls), error, command), alive_urls


def run_assessment(args: Any, config: dict[str, Any]) -> int:
    targets, rejected, original_inputs = load_targets_with_originals(args.domain, args.list)
    setup_manager = DependencyManager()
    setup = setup_manager.ensure_all(auto_install=(not args.no_install) and bool(config.get("auto_install", True)),
                                     strict=bool(args.strict_dependencies or config.get("strict_dependencies", False)))
    assessment_id, assessment_dir = create_assessment_dir(args.output_dir)
    write_text(assessment_dir / "setup_report.txt", _setup_text(setup))
    write_json(assessment_dir / "setup_report.json", setup)
    for rejected_row in rejected:
        print(f"[!] Skipping invalid target {rejected_row['input']!r}: {rejected_row['reason']}", flush=True)
    if setup.get("strict_mode_blocked"):
        print("[!] Strict dependency mode enabled; one or more requested tools are unavailable. See setup_report.txt.", flush=True)
        return 2

    report: dict[str, Any] = {
        "assessment_id": assessment_id,
        "started_at_utc": utc_now(),
        "platform": platform.platform(),
        "targets": [],
        "rejected_target_inputs": rejected,
        "setup_report": "setup_report.json",
        "authorized_use_notice": "Run only for domains you own or are explicitly authorized to assess.",
    }
    print(f"[*] Assessment {assessment_id}: {len(targets)} target(s)", flush=True)
    combined_hosts: set[str] = set()
    combined_alive: set[str] = set()
    include_apex = bool(args.include_apex or config.get("include_apex", False))

    source_keys = ["subfinder", "sublist3r", "bbot", "amass", "assetfinder", "findomain", "knockpy",
                   "theharvester", "dnsrecon", "dnsenum"]
    for target in targets:
        target_dir = assessment_dir / target
        target_dir.mkdir(parents=True, exist_ok=False)
        (target_dir / "raw").mkdir()
        (target_dir / "tool_subdomains").mkdir()
        target_report: dict[str, Any] = {"target": target, "normalized_target": target,
                                         "original_input": original_inputs.get(target, target),
                                         "started_at_utc": utc_now(), "tools": [], "final_subdomain_count": 0,
                                         "alive_url_count": 0}
        all_hosts: set[str] = set()
        for key in source_keys:
            spec = BY_KEY[key]
            row = _tool_by_key(setup, key)
            tool_result, hosts = _run_one_enumerator(key, target, row, target_dir, config, include_apex)
            target_report["tools"].append(tool_result)
            all_hosts.update(hosts)

        puredns_spec = BY_KEY["puredns"]
        puredns_result, puredns_hosts = _run_one_enumerator(
            "puredns", target, _tool_by_key(setup, "puredns"), target_dir, config, include_apex)
        target_report["tools"].append(puredns_result)
        # Keep passive/discovery candidates even if they do not resolve now. PureDNS adds confirmed candidates;
        # it does not remove DNS names that may be temporarily unavailable or CNAME-related findings.
        all_hosts.update(puredns_hosts)
        final_hosts = sorted_unique_hostnames(all_hosts)
        write_lines(target_dir / "Final_Subdomains.txt", final_hosts)
        target_report["final_subdomain_count"] = len(final_hosts)
        target_report["final_subdomains_file"] = str((target_dir / "Final_Subdomains.txt").relative_to(assessment_dir))
        if not final_hosts:
            print(f"[!] {target}: no qualifying subdomains were discovered.", flush=True)

        httpx_result, alive_urls = _run_httpx(target, target_dir, setup, config, include_apex, final_hosts)
        target_report["tools"].append(httpx_result)
        target_report["alive_url_count"] = len(alive_urls)
        target_report["alive_file"] = str((target_dir / "Alive_Subdomains.txt").relative_to(assessment_dir))
        target_report["finished_at_utc"] = utc_now()
        write_json(target_dir / "run_report.json", target_report)
        report["targets"].append(target_report)
        combined_hosts.update(final_hosts)
        combined_alive.update(alive_urls)

    if len(targets) > 1:
        combined_dir = assessment_dir / "combined"
        combined_dir.mkdir()
        write_lines(combined_dir / "Final_Subdomains.txt", sorted_unique_hostnames(combined_hosts))
        write_lines(combined_dir / "Alive_Subdomains.txt", sorted_unique_hostnames(combined_alive))
        report["combined_files"] = {
            "final_subdomains": "combined/Final_Subdomains.txt",
            "alive_subdomains": "combined/Alive_Subdomains.txt",
        }

    report["finished_at_utc"] = utc_now()
    report["summary"] = {
        "target_count": len(targets),
        "unique_subdomain_count_across_targets": len(combined_hosts),
        "responsive_url_count_across_targets": len(combined_alive),
        "unavailable_tools": setup.get("unavailable_tools", []),
    }
    write_json(assessment_dir / "run_report.json", report)
    print("\n=== Assessment summary ===", flush=True)
    print(f"Targets processed: {len(targets)}", flush=True)
    print(f"Unique subdomains (aggregate): {len(combined_hosts)}", flush=True)
    print(f"Responsive HTTP/HTTPS URLs (aggregate): {len(combined_alive)}", flush=True)
    print(f"Results directory: {assessment_dir.resolve()}", flush=True)
    print(f"Setup report: {(assessment_dir / 'setup_report.txt').resolve()}", flush=True)
    print(f"Run report: {(assessment_dir / 'run_report.json').resolve()}", flush=True)
    if setup.get("unavailable_tools"):
        print("Unavailable tools: " + ", ".join(setup["unavailable_tools"]), flush=True)
    return 0


def check_tools_only(args: Any, config: dict[str, Any] | None = None) -> int:
    manager = DependencyManager()
    options = config or {}
    setup = manager.ensure_all(auto_install=(not args.no_install) and bool(options.get("auto_install", True)),
                               strict=bool(args.strict_dependencies or options.get("strict_dependencies", False)))
    assessment_id, assessment_dir = create_assessment_dir(args.output_dir)
    write_text(assessment_dir / "setup_report.txt", _setup_text(setup))
    write_json(assessment_dir / "setup_report.json", setup)
    print(_setup_text(setup))
    print(f"Setup report saved: {(assessment_dir / 'setup_report.txt').resolve()}")
    return 2 if setup.get("strict_mode_blocked") else 0
