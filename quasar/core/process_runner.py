"""Safe subprocess execution (never uses a shell)."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class ProcessResult:
    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    error: str | None = None


def prepare_command(command: Sequence[str], *, system_name: str | None = None,
                    python_executable: str | None = None) -> list[str]:
    """Normalize a command for the host platform without invoking a shell.

    Windows cannot consistently execute a .py path directly via CreateProcess, so
    Python script launchers are explicitly prefixed with the current interpreter.
    This helper is kept separate to make platform-specific behavior unit-testable.
    """
    cmd = [str(arg) for arg in command]
    host = system_name or platform.system()
    if host == "Windows" and cmd and Path(cmd[0]).suffix.lower() in {".py", ".pyw"}:
        cmd.insert(0, python_executable or sys.executable)
    return cmd


def run_process(command: Sequence[str], timeout: int = 300, cwd: str | Path | None = None) -> ProcessResult:
    """Run a command with captured output, bounded timeout, and shell=False."""
    cmd = prepare_command(command, system_name="Windows" if os.name == "nt" else platform.system())
    start = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
        )
        return ProcessResult(cmd, completed.returncode, completed.stdout, completed.stderr,
                             time.monotonic() - start)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ProcessResult(cmd, None, stdout, stderr, time.monotonic() - start,
                             timed_out=True, error=f"Timed out after {timeout} seconds")
    except FileNotFoundError as exc:
        return ProcessResult(cmd, None, "", "", time.monotonic() - start, error=str(exc))
    except OSError as exc:
        return ProcessResult(cmd, None, "", "", time.monotonic() - start, error=f"OS error: {exc}")
