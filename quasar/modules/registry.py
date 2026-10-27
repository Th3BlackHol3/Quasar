"""Tool registry with tool-specific command adapters and official install recipes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import amass, assetfinder, bbot, dnsenum, dnsrecon, findomain, knockpy, puredns, subfinder, sublist3r, theharvester

Builder = Callable[[str, str, Path, Path, dict], list[str]]


@dataclass(frozen=True)
class ToolSpec:
    key: str
    display_name: str
    executables: tuple[str, ...]
    version_args: tuple[str, ...]
    adapter: Builder | None = None
    installer_kind: str | None = None
    installer_command: tuple[str, ...] = ()
    installer_note: str = ""
    needs_massdns: bool = False


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec("subfinder", "Subfinder", ("subfinder",), ("-version",), subfinder.build_command,
             "go", ("github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",),
             "Official ProjectDiscovery Go module."),
    ToolSpec("sublist3r", "Sublist3r", ("sublist3r", "sublist3r.py", "Sublist3r.py"), ("-h",), sublist3r.build_command,
             "git-python-script", ("https://github.com/aboul3la/Sublist3r.git",),
             "Legacy upstream script; install into a user-local virtual environment."),
    ToolSpec("bbot", "BBOT", ("bbot",), ("--version",), bbot.build_command,
             "pipx", ("bbot",), "Official BBOT Python package."),
    ToolSpec("amass", "Amass", ("amass",), ("version",), amass.build_command,
             "go-cgo0", ("github.com/owasp-amass/amass/v5/cmd/amass@main",),
             "Official OWASP Amass v5 Go module."),
    ToolSpec("assetfinder", "Assetfinder", ("assetfinder",), ("-h",), assetfinder.build_command,
             "go", ("github.com/tomnomnom/assetfinder@latest",), "Official tomnomnom Go module."),
    ToolSpec("findomain", "Findomain", ("findomain",), ("--version",), findomain.build_command,
             "cargo", ("findomain",), "Official Findomain crate; requires a working Rust/Cargo toolchain."),
    ToolSpec("knockpy", "Knockpy", ("knockpy",), ("-h",), knockpy.build_command,
             "pipx-git", ("git+https://github.com/guelfoweb/knockpy.git",),
             "Install from the official guelfoweb/KnockPy repository; avoid the ambiguous PyPI package name."),
    ToolSpec("theharvester", "theHarvester", ("theHarvester", "theharvester"), ("-h",), theharvester.build_command,
             "pipx", ("theHarvester",), "Official theHarvester package; API sources vary by configuration."),
    ToolSpec("puredns", "PureDNS", ("puredns",), ("--help",), None,
             "go", ("github.com/d3mondev/puredns/v2@latest",), "Official d3mondev Go module.", needs_massdns=True),
    ToolSpec("dnsrecon", "DNSRecon", ("dnsrecon",), ("-h",), dnsrecon.build_command,
             "pipx-git", ("git+https://github.com/darkoperator/dnsrecon.git",), "Official DNSRecon repository."),
    ToolSpec("dnsenum", "DNSEnum", ("dnsenum",), ("-h",), dnsenum.build_command,
             "apt-root", ("dnsenum",), "May install via the system apt package only when already running as root; no sudo is invoked."),
    ToolSpec("httpx", "HTTPX (ProjectDiscovery)", ("httpx", "projectdiscovery-httpx"), ("-version",), None,
             "go", ("github.com/projectdiscovery/httpx/cmd/httpx@latest",),
             "Official ProjectDiscovery Go module; reject the unrelated Python HTTPX CLI."),
)

BY_KEY = {spec.key: spec for spec in TOOL_SPECS}
