"""Cross-platform dependency discovery and safe, per-user tool installation.

Quasar itself uses only the Python standard library. External reconnaissance tools
are optional and have different platform/runtime requirements. This manager never
uses shell command strings, silently elevates privileges, or marks an installation
successful until the tool is probed again.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .process_runner import run_process
from .. import __version__
from ..modules.registry import TOOL_SPECS, ToolSpec


def _executable_file(path: Path) -> bool:
    return path.is_file() and (os.name == "nt" or os.access(path, os.X_OK))


def quasar_data_dir() -> Path:
    """Return an OS-appropriate per-user data directory without creating it."""
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return root / "Quasar"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Quasar"
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).expanduser()
    if not root.is_absolute():
        root = Path.home() / ".local" / "share"
    return root / "quasar"


def _user_bin_dirs() -> list[Path]:
    data_bin = quasar_data_dir() / "bin"
    candidates = [data_bin, Path.home() / ".local" / "bin", Path.home() / "go" / "bin", Path.home() / ".cargo" / "bin"]
    # Preserve and discover the previous release's private paths so upgrading does
    # not make an already-installed Sublist3r launcher or tool binary disappear.
    legacy = Path.home() / "AppData" / "Local" / "SubdomainAutomation" / "bin"
    candidates.append(legacy)
    gobin = os.environ.get("GOBIN")
    if gobin:
        candidates.insert(0, Path(gobin).expanduser())
    return candidates


class DependencyManager:
    def __init__(self) -> None:
        self.extra_bin_dirs: list[Path] = []
        self._pipx_command_cache: list[str] | None = None
        self._pipx_error_cache: str | None = None
        self._refresh_paths()

    def _refresh_paths(self) -> None:
        candidates = _user_bin_dirs()
        go = shutil.which("go")
        if go:
            res = run_process([go, "env", "GOPATH"], timeout=8)
            if res.returncode == 0 and res.stdout.strip():
                candidates.extend(Path(p) / "bin" for p in res.stdout.strip().split(os.pathsep) if p)
        for path in candidates:
            try:
                if path.exists() and path.is_dir() and path not in self.extra_bin_dirs:
                    self.extra_bin_dirs.append(path)
            except OSError:
                continue
        path_value = os.environ.get("PATH", "")
        new_parts = [str(p) for p in self.extra_bin_dirs]
        # Keep PATH stable across repeated refresh calls and avoid duplicate entries.
        existing = [part for part in path_value.split(os.pathsep) if part]
        for part in reversed(new_parts):
            if part not in existing:
                existing.insert(0, part)
        os.environ["PATH"] = os.pathsep.join(existing)

    def _candidate_paths(self, names: tuple[str, ...]) -> list[Path]:
        result: list[Path] = []
        path_entries = [Path(entry or ".") for entry in os.environ.get("PATH", "").split(os.pathsep)]
        path_entries = self.extra_bin_dirs + path_entries
        extensions = [""]
        if os.name == "nt":
            extensions = os.environ.get("PATHEXT", ".COM;.EXE").split(";")
            # Avoid .bat/.cmd wrappers: Windows may invoke a command interpreter for them
            # even when subprocess was requested with shell=False.
            extensions = [ext if ext.startswith(".") else "." + ext for ext in extensions]
        for name in names:
            possible_names = [name] if Path(name).suffix else [name + ext for ext in extensions]
            for directory in path_entries:
                for possible_name in possible_names:
                    candidate = directory / possible_name
                    if os.name == "nt" and candidate.suffix.lower() in {".bat", ".cmd"}:
                        continue
                    if _executable_file(candidate) and candidate not in result:
                        result.append(candidate)
        for name in names:
            found = shutil.which(name)
            found_path = Path(found) if found else None
            if found_path and os.name == "nt" and found_path.suffix.lower() in {".bat", ".cmd"}:
                continue
            if found_path and found_path not in result:
                result.append(found_path)
        return result

    def _probe(self, executable: Path, spec: ToolSpec) -> tuple[bool, str]:
        attempts: list[tuple[str, ...]] = [spec.version_args, ("--version",), ("-h",), ("--help",)]
        seen: set[tuple[str, ...]] = set()
        combined_output = ""
        for args in attempts:
            if args in seen:
                continue
            seen.add(args)
            result = run_process([str(executable), *args], timeout=10)
            output = (result.stdout + "\n" + result.stderr).strip()
            if output:
                combined_output = output[:3000]
            if spec.key == "httpx":
                # Upstream versions have used both "httpx v1.2.3" and
                # "Current httpx version v1.2.3" banners. Require a ProjectDiscovery
                # fingerprint and explicitly reject Python-client CLIs.
                python_cli = re.search(r"(?i)(encode/httpx|python.{0,30}httpx|httpx.{0,30}python client|usage:\s*httpx\s+\[options\].*url)", output)
                pd_banner = re.search(r"(?i)\bhttpx\s+(?:version\s+)?v?\d+\.\d+\.\d+\b", output)
                pd_help = re.search(r"(?i)multi-purpose HTTP toolkit|projectdiscovery", output)
                if not python_cli and (pd_banner or pd_help):
                    return True, output.splitlines()[0][:300]
                continue
            if spec.key == "knockpy":
                # Do not mistake an unrelated distribution with the same package name
                # for the security tool. KnockPy v9's CLI does not expose --version;
                # its -h/--help output is the reliable compatibility probe.
                knockpy_cli = re.search(r"(?i)knockpy", output)
                security_flags = re.search(r"(?i)--recon|--bruteforce|subdomain\s+(?:scan|enumeration)|knock subdomain", output)
                if knockpy_cli and security_flags and (result.returncode == 0 or "usage" in output.lower()):
                    return True, output.splitlines()[0][:300]
                continue
            if result.returncode == 0 or re.search(r"(?i)(usage:|usage\s|version|flags:|options:|commands:)", output):
                return True, output.splitlines()[0][:300] if output else "command responded"
        return False, combined_output.splitlines()[0][:300] if combined_output else "No recognizable version/help response."

    def find_and_verify(self, spec: ToolSpec) -> dict[str, Any]:
        checked: list[dict[str, str]] = []
        for executable in self._candidate_paths(spec.executables):
            ok, detail = self._probe(executable, spec)
            checked.append({"path": str(executable), "verified": str(ok).lower(), "detail": detail})
            if ok:
                return {"tool": spec.display_name, "status": "available", "path": str(executable),
                        "version_or_probe": detail, "candidate_diagnostics": checked}
        if checked:
            explanation = "Executables were found but none passed this tool's identity/CLI check."
        else:
            explanation = "No candidate executable was found in PATH or known user install locations."
        return {"tool": spec.display_name, "status": "missing", "path": None,
                "version_or_probe": explanation, "candidate_diagnostics": checked}

    def _pipx_prefix(self) -> tuple[list[str] | None, str | None]:
        """Find pipx or bootstrap it inside Quasar's private virtual environment.

        A self-managed virtual environment avoids system-Python modification and
        works on Windows, macOS, and Linux. Current pipx releases require Python 3.11+.
        """
        pipx = shutil.which("pipx")
        if pipx:
            self._pipx_command_cache = [pipx]
            return self._pipx_command_cache, None
        probe = run_process([sys.executable, "-m", "pipx", "--version"], timeout=8)
        if probe.returncode == 0:
            self._pipx_command_cache = [sys.executable, "-m", "pipx"]
            return self._pipx_command_cache, None
        if self._pipx_command_cache:
            return self._pipx_command_cache, self._pipx_error_cache
        if self._pipx_error_cache:
            return None, self._pipx_error_cache
        if sys.version_info < (3, 11):
            self._pipx_error_cache = "pipx is missing. Quasar can bootstrap current pipx only with Python 3.11+; install pipx with your OS package manager or use Python 3.11+."
            return None, self._pipx_error_cache

        app_data = quasar_data_dir()
        venv = app_data / "venvs" / "pipx"
        python_exe = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        try:
            app_data.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._pipx_error_cache = f"Cannot create Quasar user data directory {app_data}: {exc}"
            return None, self._pipx_error_cache
        if not python_exe.exists():
            created = run_process([sys.executable, "-m", "venv", str(venv)], timeout=180)
            if created.returncode != 0 or not python_exe.exists():
                detail = created.error or created.stderr or created.stdout or "Virtual environment creation failed."
                self._pipx_error_cache = f"Could not create isolated pipx environment: {detail[-1800:]}"
                return None, self._pipx_error_cache
        installed = run_process([str(python_exe), "-m", "pip", "install", "pipx"], timeout=900)
        if installed.returncode != 0 or installed.timed_out or installed.error:
            detail = installed.error or installed.stderr or installed.stdout or "pipx installation failed."
            self._pipx_error_cache = f"Could not bootstrap pipx in Quasar's isolated environment: {detail[-1800:]}"
            return None, self._pipx_error_cache
        verification = run_process([str(python_exe), "-m", "pipx", "--version"], timeout=15)
        if verification.returncode != 0:
            self._pipx_error_cache = "pipx bootstrap completed but its version check failed. Review network/Python installation and retry."
            return None, self._pipx_error_cache
        self._pipx_command_cache = [str(python_exe), "-m", "pipx"]
        self._refresh_paths()
        return self._pipx_command_cache, None

    def _run_installer(self, spec: ToolSpec) -> dict[str, Any]:
        if not spec.installer_kind:
            return {"status": "manual_required", "method": None,
                    "error": spec.installer_note or "No safe automatic installer is configured."}
        if spec.installer_kind == "git-python-script":
            return self._install_sublist3r(spec)
        if spec.installer_kind in {"go", "go-cgo0"}:
            go = shutil.which("go")
            if not go:
                return {"status": "manual_required", "method": "go install",
                        "error": "Go is not installed. Install Go from https://go.dev/dl/ (Windows/macOS/Linux), open a new terminal, and rerun Quasar."}
            command = [go, "install", "-v", *spec.installer_command]
            method = "go install -v " + " ".join(spec.installer_command)
        elif spec.installer_kind == "cargo":
            cargo = shutil.which("cargo")
            if not cargo:
                return {"status": "manual_required", "method": "cargo install",
                        "error": "Rust/Cargo is not installed. Follow https://www.rust-lang.org/tools/install for this OS, then rerun Quasar."}
            command = [cargo, "install", *spec.installer_command]
            method = "cargo install " + " ".join(spec.installer_command)
        elif spec.installer_kind == "apt-root":
            apt = shutil.which("apt-get")
            is_root = hasattr(os, "geteuid") and os.geteuid() == 0
            if not apt or not is_root:
                system = platform.system()
                if system == "Darwin":
                    error = "No safe automatic macOS recipe is configured for DNSEnum. Install Perl and its upstream dependencies using reviewed instructions, or skip DNSEnum."
                elif system == "Windows":
                    error = "DNSEnum does not have a configured native Windows installer. Install it manually with a compatible Perl runtime/dependencies, or skip this module."
                else:
                    error = "Automatic DNSEnum installation is limited to apt-based systems when Quasar is already running as root. No privilege escalation is performed; install it manually with your distribution package manager."
                return {"status": "manual_required", "method": "platform-specific DNSEnum installation", "error": error}
            command = [apt, "install", "-y", *spec.installer_command]
            method = "apt-get install -y " + " ".join(spec.installer_command)
        elif spec.installer_kind in {"pipx", "pipx-git"}:
            command_prefix, pipx_error = self._pipx_prefix()
            if not command_prefix:
                return {"status": "manual_required", "method": "pipx install", "error": pipx_error or "pipx is unavailable; install it using the official pipx instructions."}
            package = spec.installer_command[0]
            # Force is intentional for VCS installs: it replaces an unverified
            # same-named distribution (notably the unrelated PyPI package called
            # "knockpy") with the official upstream app. Verified installs never
            # enter this installer path.
            command = [*command_prefix, "install"]
            if spec.installer_kind == "pipx-git":
                command.append("--force")
            command.append(package)
            method = "pipx install " + ("--force " if spec.installer_kind == "pipx-git" else "") + package
        else:
            return {"status": "manual_required", "method": None, "error": "Unknown installer recipe."}

        original_cgo = os.environ.get("CGO_ENABLED")
        if spec.installer_kind == "go-cgo0":
            os.environ["CGO_ENABLED"] = "0"
        try:
            result = run_process(command, timeout=1200)
        finally:
            if spec.installer_kind == "go-cgo0":
                if original_cgo is None:
                    os.environ.pop("CGO_ENABLED", None)
                else:
                    os.environ["CGO_ENABLED"] = original_cgo
        self._refresh_paths()
        details = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
        installer_result = {
            "status": "installer_failed" if result.returncode != 0 or result.timed_out or result.error else "installer_completed",
            "method": method,
            "returncode": result.returncode,
            "duration_seconds": round(result.duration_seconds, 2),
            "error": result.error or (details[-2500:] if result.returncode != 0 else None),
        }
        return installer_result

    def _install_sublist3r(self, spec: ToolSpec) -> dict[str, Any]:
        """Install legacy Sublist3r in an isolated user-local virtual environment."""
        git = shutil.which("git")
        if not git:
            return {"status": "manual_required", "method": "git clone + Python venv",
                    "error": "Git is not installed. Install Git from https://git-scm.com/downloads for this OS, then rerun Quasar."}
        start = time.monotonic()
        base = quasar_data_dir()
        repo = base / "tools" / "Sublist3r"
        venv = base / "venvs" / "sublist3r"
        script = repo / "sublist3r.py"
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return {"status": "installer_failed", "method": "Quasar user-local application data", "error": str(exc)}
        if not repo.exists():
            clone = run_process([git, "clone", "--depth", "1", "--", spec.installer_command[0], str(repo)], timeout=300)
            if clone.returncode != 0 or clone.error or not script.is_file():
                detail = clone.error or (clone.stderr or clone.stdout or "Git clone failed.")[-2000:]
                return {"status": "installer_failed", "method": "git clone official Sublist3r repository", "error": detail}
        elif not script.is_file():
            return {"status": "manual_required", "method": "git clone + Python venv",
                    "error": f"Existing Sublist3r directory is incomplete: {repo}. Review it manually; Quasar did not overwrite it."}

        venv_python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not venv_python.exists():
            venv_result = run_process([sys.executable, "-m", "venv", str(venv)], timeout=180)
            if venv_result.returncode != 0 or not venv_python.exists():
                detail = venv_result.error or (venv_result.stderr or venv_result.stdout or "Unable to create virtual environment.")[-2000:]
                return {"status": "installer_failed", "method": "python -m venv", "error": detail}
        requirements = repo / "requirements.txt"
        if requirements.is_file():
            install = run_process([str(venv_python), "-m", "pip", "install", "-r", str(requirements)], timeout=1200)
            if install.returncode != 0 or install.error or install.timed_out:
                detail = install.error or (install.stderr or install.stdout or "Dependency installation failed.")[-2500:]
                return {"status": "installer_failed", "method": "Sublist3r isolated venv pip install", "error": detail}

        launcher_dir = quasar_data_dir() / "bin"
        launcher_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            # A Python launcher avoids relying on .cmd/.bat subprocess quirks on Windows.
            launcher = launcher_dir / "sublist3r.py"
            launcher.write_text(
                "import subprocess, sys\n"
                f"PYTHON = {str(venv_python)!r}\n"
                f"SCRIPT = {str(script)!r}\n"
                "raise SystemExit(subprocess.call([PYTHON, SCRIPT, *sys.argv[1:]]))\n",
                encoding="utf-8",
            )
        else:
            import shlex
            launcher = Path.home() / ".local" / "bin" / "sublist3r"
            launcher.parent.mkdir(parents=True, exist_ok=True)
            launcher.write_text(f"#!/bin/sh\nexec {shlex.quote(str(venv_python))} {shlex.quote(str(script))} \"$@\"\n", encoding="utf-8")
            launcher.chmod(0o755)
        self._refresh_paths()
        return {"status": "installer_completed", "method": "official Sublist3r repository + isolated Python venv",
                "duration_seconds": round(time.monotonic() - start, 2), "launcher": str(launcher), "error": None}

    @staticmethod
    def _available_package_managers() -> list[str]:
        candidates = ("go", "cargo", "pipx", "git", "brew", "port", "apt-get", "apt", "dnf", "yum",
                      "pacman", "zypper", "winget", "choco", "scoop", "perl", "massdns")
        return [name for name in candidates if shutil.which(name)]

    def ensure_all(self, auto_install: bool = True, strict: bool = False) -> dict[str, Any]:
        report: dict[str, Any] = {
            "application": "Quasar",
            "application_version": __version__,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "platform": sys.platform,
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "quasar_data_directory": str(quasar_data_dir()),
            "available_package_managers_and_runtimes": self._available_package_managers(),
            "auto_install_enabled": auto_install,
            "tools": [],
            "extra_prerequisites": [],
            "strict_mode": strict,
        }
        for spec in TOOL_SPECS:
            initial = self.find_and_verify(spec)
            row: dict[str, Any] = {**initial, "installation": None}
            if initial["status"] == "missing" and auto_install:
                row["installation"] = self._run_installer(spec)
                final = self.find_and_verify(spec)
                row["post_install"] = final
                if final["status"] == "available":
                    row.update({"status": "installed_and_verified", "path": final["path"],
                                "version_or_probe": final["version_or_probe"]})
                else:
                    installation_status = row["installation"].get("status")
                    row["status"] = installation_status if installation_status in {"manual_required", "installer_failed"} else "install_failed"
                    row["error"] = row["installation"].get("error") or "Installer completed but the tool was not available after verification."
            row["platform_note"] = self._platform_note(spec)
            report["tools"].append(row)

        massdns_path = shutil.which("massdns")
        report["extra_prerequisites"].append({
            "name": "MassDNS (PureDNS runtime dependency)",
            "status": "available" if massdns_path else "missing",
            "path": massdns_path,
            "note": "PureDNS resolution normally requires MassDNS and a configured resolver list. Follow the official MassDNS/PureDNS documentation for this OS."
        })
        missing = [tool for tool in report["tools"] if tool["status"] not in {"available", "installed_and_verified"}]
        report["all_tools_verified"] = not missing
        report["unavailable_tools"] = [tool["tool"] for tool in missing]
        report["strict_mode_blocked"] = bool(strict and missing)
        return report

    @staticmethod
    def _platform_note(spec: ToolSpec) -> str:
        system = platform.system()
        if spec.key == "puredns":
            return "Requires Go plus MassDNS and configured resolvers for normal DNS resolution."
        if spec.key == "sublist3r":
            return "Legacy upstream Python project; isolated installation can fail with modern Python/dependency versions."
        if spec.installer_kind == "apt-root":
            if system == "Linux":
                return "Automatic package install is limited to apt-based Linux when already running as root; otherwise install manually."
            if system == "Darwin":
                return "No automatic macOS installer configured; this tool's native Perl/runtime dependencies may require manual setup."
            if system == "Windows":
                return "No automatic native Windows installer configured; use an appropriate Perl environment or skip this optional module."
        if spec.installer_kind in {"go", "go-cgo0"}:
            return "Requires Go; see https://go.dev/dl/ if it is not installed."
        if spec.installer_kind == "cargo":
            return "Requires Rust/Cargo; see https://www.rust-lang.org/tools/install if missing."
        if spec.installer_kind in {"pipx", "pipx-git"}:
            return "Can be installed in an isolated pipx environment; upstream packages may have their own OS/Python constraints."
        return "The Quasar wrapper supports this platform, subject to the upstream tool's own requirements."
