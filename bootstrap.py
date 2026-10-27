#!/usr/bin/env python3
"""Prepare Quasar's local virtual environment on Windows, macOS, or Linux.

The core application has no third-party Python runtime dependencies. This script
therefore stays offline-friendly unless --with-tools is selected or requirements.txt
contains packages. It never installs OS packages or requests administrator elevation.
"""
from __future__ import annotations

import argparse
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from quasar.banner import show_banner

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"


def venv_python(venv_dir: Path = VENV_DIR, system: str | None = None) -> Path:
    system = system or platform.system()
    if system == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(command: Sequence[str], *, cwd: Path = ROOT, suppress_banner: bool = False) -> int:
    parts = [str(x) for x in command]
    rendered = subprocess.list2cmdline(parts) if os.name == "nt" else shlex.join(parts)
    print("[quasar-setup] $ " + rendered, flush=True)
    try:
        environment = os.environ.copy()
        if suppress_banner:
            environment["QUASAR_SUPPRESS_BANNER"] = "1"
        result = subprocess.run(
            [str(item) for item in command], cwd=str(cwd), check=False,
            stdin=subprocess.DEVNULL, shell=False, env=environment,
        )
        return int(result.returncode)
    except OSError as exc:
        print(f"[ERROR] Could not start command: {exc}", file=sys.stderr)
        return 127


def _requirements_have_packages(path: Path) -> bool:
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        candidate = line.strip()
        if candidate and not candidate.startswith("#"):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    show_banner()
    parser = argparse.ArgumentParser(
        description="Set up Quasar's Python environment on Windows, macOS, or Linux."
    )
    parser.add_argument("--with-tools", action="store_true",
                        help="also attempt installation of configured external security tools (requires network access).")
    parser.add_argument("--check-tools", action="store_true",
                        help="check external tools without installing them after preparing the environment.")
    parser.add_argument("--upgrade-pip", action="store_true",
                        help="upgrade pip inside .venv; requires network access (not needed for Quasar core).")
    args = parser.parse_args(argv)

    if sys.version_info < (3, 10):
        print(f"[ERROR] Quasar requires Python 3.10 or newer. Current: {sys.version.split()[0]}", file=sys.stderr)
        return 2

    print(f"Quasar 1.2.1 setup | OS: {platform.system()} {platform.release()} | Architecture: {platform.machine()}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"Project directory: {ROOT}")
    python = venv_python()

    if not python.exists():
        code = _run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if code != 0 or not python.exists():
            print("[ERROR] Could not create .venv. Ensure Python's venv component is available, then consult README.md.", file=sys.stderr)
            return code or 1
    else:
        print(f"[OK] Existing virtual environment found: {VENV_DIR}")

    if args.upgrade_pip:
        code = _run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        if code != 0:
            print("[ERROR] pip upgrade failed. Quasar's standard-library core may still work; review the output above.", file=sys.stderr)
            return code

    requirements = ROOT / "requirements.txt"
    if _requirements_have_packages(requirements):
        code = _run([str(python), "-m", "pip", "install", "-r", str(requirements)])
        if code != 0:
            print("[ERROR] Python requirements installation failed.", file=sys.stderr)
            return code

    code = _run([str(python), "-m", "compileall", "-q", str(ROOT / "quasar.py"), str(ROOT / "quasar")])
    if code != 0:
        print("[ERROR] Python compilation check failed.", file=sys.stderr)
        return code

    version_code = _run([str(python), str(ROOT / "quasar.py"), "--version"], suppress_banner=True)
    if version_code != 0:
        print("[ERROR] Quasar CLI smoke check failed.", file=sys.stderr)
        return version_code

    if args.with_tools or args.check_tools:
        command = [str(python), str(ROOT / "quasar.py"), "--check-tools"]
        if args.check_tools and not args.with_tools:
            command.append("--no-install")
        code = _run(command, suppress_banner=True)
        if code not in (0, 2):
            print("[WARN] Tool check returned an error. See the diagnostic output and setup report.", file=sys.stderr)
        elif code == 2:
            print("[WARN] One or more tools are unavailable. Quasar core is set up; see setup_report.txt for OS-specific actions.")

    print("\n[OK] Quasar's Python environment is ready.")
    print("No third-party tool was claimed as installed unless Quasar's dependency check verified it.")
    print("Next: use run.sh/run.ps1/run.bat, or invoke .venv's Python with quasar.py.")
    print("Examples: --help | --check-tools --no-install | --domain example.com | --list domains.txt")
    if platform.system() != "Windows":
        print(f"Run command: {ROOT / 'run.sh'} --help")
    else:
        print(f"Run command: {ROOT / 'run.bat'} --help")
    if sys.version_info < (3, 11):
        print("[NOTE] Python 3.11+ is recommended for smoother installation of the latest pipx-managed tools.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
