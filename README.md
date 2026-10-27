# Quasar — Cross-Platform Subdomain Enumeration Framework

<p align="center">
  <img src="https://github.com/Th3BlackHol3/Quasar/blob/main/Quasar%20by%20Th3BlackHol3.gif">
</p>

**Quasar** is a Python-based command-line framework that orchestrates subdomain discovery tools, consolidates and validates their results, removes duplicates, and checks discovered hostnames for responsive HTTP/HTTPS services. It is designed for authorized penetration testing, bug bounty reconnaissance, and attack-surface management.

**Developed by:** [Th3BlackHol3](https://github.com/Th3BlackHol3)  
**Version:** `1.2.1`  
**Platforms:** Linux · macOS · Windows  
**Python:** 3.10+ (Python 3.11+ recommended for smoother installation of current `pipx`-managed tools)

> **Authorized use only:** Use Quasar only against domains you own or have explicit permission to assess. Enumeration can generate DNS and HTTP/HTTPS traffic and may contact third-party services. You are responsible for authorization, applicable laws, program rules, rate limits, and the configuration of every integrated tool.

## Table of Contents

- [Banner](#banner)
- [Features](#features)
- [Integrated tools](#integrated-tools)
- [Requirements and limitations](#requirements-and-limitations)
- [Installation](#installation)
  - [Linux](#linux)
  - [macOS](#macos)
  - [Windows PowerShell](#windows-powershell)
  - [Windows Command Prompt](#windows-command-prompt)
  - [Manual setup](#manual-setup)
- [Usage](#usage)
- [Command-line options](#command-line-options)
- [Configuration](#configuration)
- [Output structure](#output-structure)
- [Dependency installation behavior](#dependency-installation-behavior)
- [Troubleshooting](#troubleshooting)
- [Testing](#testing)
- [Security and responsible use](#security-and-responsible-use)
- [Credits and upstream projects](#credits-and-upstream-projects)
- [License](#license)

## Banner

Quasar displays this branding in the terminal when the CLI or setup bootstrap starts:

```text
_░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓██████▓▒░░▒▓███████▓▒░
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░░▒▓██████▓▒░░▒▓████████▓▒░▒▓███████▓▒░
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░
 ░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░
   ░▒▓█▓▒░
    ░▒▓██▓▒░ Quasar v1.2.1 | Developed by Th3BlackHol3

https://github.com/Th3BlackHol3
https://twitter.com/Th3BlackHol3_
https://www.linkedin.com/in/th3blackhol3/
https://www.facebook.com/Th3BlackHol3
```

## Features

- Accepts a single domain or a text file containing multiple domains.
- Provides setup and launch scripts for Linux, macOS, Windows PowerShell, and Windows Command Prompt.
- Creates a project-local Python virtual environment; Quasar's core uses only the Python standard library.
- Detects external tools, probes their CLI identity, and attempts supported installation recipes when enabled.
- Reports missing runtimes, failed installations, unavailable tools, and platform limitations instead of claiming an unverified installation succeeded.
- Runs tools independently so one tool's failure does not automatically stop the rest of the workflow.
- Captures tool stdout, stderr, native artifacts, normalized candidate files, and structured reports.
- Normalizes hostname candidates, filters them to the requested domain scope, sorts them, and removes duplicates.
- Writes `Final_Subdomains.txt` and checks responsive services with ProjectDiscovery HTTPX to create `Alive_Subdomains.txt`.
- Creates per-target results and aggregate files for multi-target assessments.
- Uses argument-list subprocess execution rather than shell command strings and does not silently escalate privileges.
- Includes automated tests using fixtures and mocked subprocess results.

## Integrated tools

Quasar contains adapters for the following twelve tools:

| Tool | Purpose in Quasar | Important notes |
|---|---|---|
| [Subfinder](https://github.com/projectdiscovery/subfinder) | Passive subdomain discovery | Results depend on configured sources and any required API keys. |
| [Sublist3r](https://github.com/aboul3la/Sublist3r) | Subdomain discovery | Legacy upstream project; installation can be difficult with newer Python dependencies. |
| [BBOT](https://github.com/blacklanternsecurity/bbot) | Subdomain-enumeration profile | Uses BBOT's passive reconnaissance profile. |
| [Amass](https://github.com/owasp-amass/amass) | Passive attack-surface enumeration | Requires a compatible Go installation for automatic setup. |
| [Assetfinder](https://github.com/tomnomnom/assetfinder) | Subdomain discovery | Installed through the upstream Go module when Go is available. |
| [Findomain](https://github.com/Findomain/Findomain) | Subdomain discovery | Automatic installation requires Rust/Cargo. |
| [KnockPy](https://github.com/guelfoweb/KnockPy) | Domain and subdomain reconnaissance | Installed from the official Git repository to avoid the unrelated same-named PyPI package. |
| [theHarvester](https://github.com/laramies/theHarvester) | Public-source reconnaissance | Some data sources need API keys or provider-specific setup. |
| [PureDNS](https://github.com/d3mondev/puredns) | Resolves/validates candidates from other tools | It is used as a candidate-resolution step, not as an independent passive discovery source. Normal use requires MassDNS and resolver configuration. |
| [DNSRecon](https://github.com/darkoperator/dnsrecon) | DNS record reconnaissance | Behavior and output depend on the installed upstream version. |
| [DNSEnum](https://www.kali.org/tools/dnsenum/) | DNS enumeration | Automatic installation is limited; manual setup may be needed, particularly on macOS and Windows. |
| [HTTPX (ProjectDiscovery)](https://github.com/projectdiscovery/httpx) | HTTP/HTTPS service probing | Must be the Go-based ProjectDiscovery CLI, not the unrelated Python `httpx` client. |

Quasar is an orchestration framework, not a guarantee that all tools can be installed or run on every OS/architecture. An `available` status means the executable passed a basic identity/version/help probe; it does not guarantee that a live scan will succeed.

## Requirements and limitations

### Required for Quasar

- Python 3.10 or newer.
- Permission to create files in the project directory and the OS-specific Quasar user-data directory.
- Git and network access if you clone the repository or install external tools from source.

Quasar core has no mandatory third-party Python runtime dependencies. `requirements.txt` is intentionally empty unless a future version introduces application-level packages.

### Optional prerequisites for external tools

Depending on which integrations you use, you may also need:

- **Go:** https://go.dev/dl/
- **Rust/Cargo:** https://www.rust-lang.org/tools/install
- **Git:** https://git-scm.com/downloads
- **pipx:** https://pipx.pypa.io/latest/how-to/install-pipx.html
- **MassDNS and DNS resolver lists:** required for normal PureDNS resolution workflows.
- **API keys/provider configuration:** required by some passive sources used by Subfinder, theHarvester, and other upstream tools.

Quasar does not automatically install the Go or Rust language runtimes, does not call `sudo`, and does not silently request administrator access. Some integrations have no safe automatic installation recipe on certain platforms; consult `COMPATIBILITY.md` and the generated setup report.

## Installation

### 1. Get the source code

After publishing the repository under the name `Quasar`, clone it with:

```bash
git clone https://github.com/Th3BlackHol3/Quasar.git
cd Quasar
```

If you choose a different GitHub repository name, replace the clone URL and directory name accordingly. You can also use GitHub's **Code → Download ZIP** option, then extract the archive and open a terminal in the extracted project directory.

### Linux

From the project directory:

```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh --help
```

To set up Quasar and also attempt installation of supported external tools:

```bash
./setup.sh --with-tools
```

To prepare Quasar and check tool availability without attempting to install external tools:

```bash
./setup.sh --check-tools
```

### macOS

Open Terminal in the project directory:

```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh --help
```

Optional external tool installation attempts:

```bash
./setup.sh --with-tools
```

### Windows PowerShell

Open PowerShell in the project directory:

```powershell
.\setup.ps1
.\run.ps1 --help
```

To also attempt installation of supported external tools:

```powershell
.\setup.ps1 -WithTools
```

To check external tool availability without installation attempts:

```powershell
.\setup.ps1 -CheckTools
```

If Windows blocks local PowerShell scripts due to the current execution policy, you can run the setup for that process without permanently changing the machine policy:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Use the same approach for `run.ps1` if needed. Review scripts before running them, and follow your organization's endpoint policy.

### Windows Command Prompt

Open Command Prompt in the project directory and run:

```bat
setup.bat
run.bat --help
```

To also attempt supported external tool installations:

```bat
setup.bat --with-tools
```

To check tool availability without attempting installation:

```bat
setup.bat --check-tools
```

### Manual setup

You can run the bootstrap directly on any supported OS with Python 3.10+:

```bash
python bootstrap.py
```

The bootstrap creates `.venv`, compiles the application, and smoke-tests the CLI. It does not install OS-level runtimes. The equivalent direct invocation after setup is:

**Linux/macOS:**

```bash
.venv/bin/python quasar.py --help
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe .\quasar.py --help
```

## Usage

Run these commands from the project directory, or use absolute paths where appropriate.

### Enumerate one domain

Linux/macOS:

```bash
./run.sh --domain example.com
```

Windows PowerShell:

```powershell
.\run.ps1 --domain example.com
```

Windows Command Prompt:

```bat
run.bat --domain example.com
```

### Enumerate multiple domains

Create a file named `domains.txt` with one authorized domain per line. Blank lines and lines beginning with `#` are ignored:

```text
# Only include domains you are authorized to assess
example.com
example.org
```

Run it on Linux/macOS:

```bash
./run.sh --list domains.txt
```

Or on Windows PowerShell:

```powershell
.\run.ps1 --list domains.txt
```

Or Windows Command Prompt:

```bat
run.bat --list domains.txt
```

Quasar validates and normalizes targets and removes duplicate input domains. It filters discoveries to the exact DNS scope of each specified target; for example, `notexample.com` is not treated as a subdomain of `example.com`.

### Check tools without installing them

```bash
./run.sh --check-tools --no-install
```

A setup report is created under the output directory. To choose an output parent:

```bash
./run.sh --check-tools --no-install --output-dir results/setup-check
```

### Useful command examples

```bash
# Print help
./run.sh --help

# Print application version
./run.sh --version

# Run without attempting to install missing tools
./run.sh --domain example.com --no-install

# Stop before enumeration if any of the twelve integrations is unavailable
./run.sh --domain example.com --strict-dependencies

# Include the target apex in the final hostname/live results
./run.sh --domain example.com --include-apex

# Tune timeouts and HTTPX concurrency
./run.sh --domain example.com --tool-timeout 900 --httpx-timeout 10 --httpx-threads 15 --httpx-retries 2

# Use a custom PureDNS resolver list
./run.sh --domain example.com --resolvers /path/to/resolvers.txt --trusted-resolvers /path/to/trusted-resolvers.txt

# Use a JSON configuration file and save results under a custom parent directory
./run.sh --domain example.com --config config/config.example.json --output-dir ./assessment-results
```

Equivalent commands use `run.ps1` or `run.bat` on Windows. Use `--help` for the current list of flags.

**Note about automatic installation:** `config/config.example.json` sets `auto_install` to `true`. A normal assessment therefore attempts configured installation recipes for missing tools unless `--no-install` is supplied. The setup script by itself prepares Quasar; `--with-tools` additionally invokes the tool-check/install workflow. Review the setup report, and install any required OS-level runtime such as Go or Rust/Cargo before retrying the affected tool.

## Command-line options

| Option | Description |
|---|---|
| `--domain DOMAIN` | Assess one domain. |
| `--list FILE` | Read domains from a text file, one per line. |
| `--output-dir DIR` | Parent directory for a new timestamped run directory. Defaults to `results`. |
| `--config FILE` | Load optional JSON configuration. |
| `--no-install` | Detect and report dependencies but do not attempt automatic installation. |
| `--strict-dependencies` | Stop before enumeration when any of the twelve integrations is unavailable. |
| `--check-tools` | Check/install dependencies and write a setup report without starting enumeration. |
| `--include-apex` | Include the target apex domain in final hostnames and live checks. |
| `--tool-timeout SECONDS` | Per-tool timeout. Default: `600`. |
| `--source-timeout SECONDS` | Subfinder source timeout. Default: `30`. |
| `--source-max-minutes MINUTES` | Subfinder maximum runtime. Default: `5`. |
| `--httpx-timeout SECONDS` | HTTPX timeout per probe. Default: `8`. |
| `--httpx-threads COUNT` | HTTPX concurrency. Default: `10`. |
| `--httpx-retries COUNT` | HTTPX retries. Default: `1`. |
| `--resolvers FILE` | Optional PureDNS resolver list. |
| `--trusted-resolvers FILE` | Optional PureDNS trusted-resolver list. |
| `--version` | Print the Quasar version. |
| `-h`, `--help` | Show help. |

For interactive terminal use, Quasar prompts for a domain or a domain-list path when no target argument is provided. In non-interactive sessions, specify `--domain`, `--list`, or `--check-tools` explicitly.

## Configuration

The sample configuration is at [`config/config.example.json`](config/config.example.json):

```json
{
  "auto_install": true,
  "tool_timeout": 600,
  "source_timeout": 30,
  "source_max_minutes": 5,
  "httpx_timeout": 8,
  "httpx_threads": 10,
  "httpx_retries": 1,
  "include_apex": false,
  "strict_dependencies": false,
  "httpx_details": false,
  "resolvers_file": null,
  "trusted_resolvers_file": null
}
```

Use it with:

```bash
./run.sh --domain example.com --config config/config.example.json
```

| Setting | Meaning |
|---|---|
| `auto_install` | Allow configured tool installation attempts during dependency checks. Default: `true`. |
| `tool_timeout` | Maximum runtime for an individual enumeration tool, in seconds. |
| `source_timeout` | Subfinder source timeout, in seconds. |
| `source_max_minutes` | Subfinder maximum run time, in minutes. |
| `httpx_timeout` | Timeout for each HTTPX probe, in seconds. |
| `httpx_threads` | HTTPX concurrency setting. Use conservative values appropriate for the assessment. |
| `httpx_retries` | HTTPX retry count. |
| `include_apex` | Include the apex domain in final candidate and live results. |
| `strict_dependencies` | Stop if one or more integrations are unavailable. |
| `httpx_details` | Preserve HTTPX output details in `Alive_Subdomains_Details.txt` when enabled. |
| `resolvers_file` | Optional path to a PureDNS resolver file. |
| `trusted_resolvers_file` | Optional path to a PureDNS trusted-resolver file. |

CLI flags take precedence over corresponding settings when a flag is provided. Keep API keys out of source code and version control; configure credentials using each upstream tool's supported configuration or environment variables.

## Output structure

Each run creates a unique UTC-timestamped directory under the selected output parent:

```text
results/
└── run_YYYYMMDDTHHMMSSZ/
    ├── setup_report.txt
    ├── setup_report.json
    ├── run_report.json
    ├── example.com/
    │   ├── raw/
    │   ├── tool_subdomains/
    │   ├── artifacts/
    │   │   ├── httpx/
    │   │   └── puredns/
    │   ├── Final_Subdomains.txt
    │   ├── Alive_Subdomains.txt
    │   ├── Alive_Subdomains_Details.txt
    │   └── run_report.json
    └── combined/                 # created for multi-target runs
        ├── Final_Subdomains.txt
        └── Alive_Subdomains.txt
```

### Important output files

- **`Final_Subdomains.txt`** — sorted, unique, normalized hostname candidates inside the target's DNS scope. The apex is excluded by default.
- **`Alive_Subdomains.txt`** — one responsive HTTP/HTTPS endpoint URL per line, as detected by ProjectDiscovery HTTPX.
- **`Alive_Subdomains_Details.txt`** — contains HTTPX details when `httpx_details` is enabled; otherwise it is empty.
- **`setup_report.txt` / `setup_report.json`** — tool availability, detected executable paths, installation attempts, errors, runtimes, and platform notes.
- **`run_report.json`** — per-tool status, exit code, duration, candidate counts, output paths, and aggregate summary.
- **`raw/`** — stdout capture and stderr log files for each tool.
- **`tool_subdomains/`** — normalized per-tool hostname candidates.
- **`artifacts/`** — native tool output and adapter-specific files, including the HTTPX input/output file and PureDNS candidate/resolution files.
- **`combined/`** — aggregate final and live lists for multi-target runs.

An empty final file is valid when no qualifying hostnames are discovered. An HTTP/HTTPS probe failure does **not** prove that a DNS name does not exist, and a responsive URL is **not** proof of a vulnerability.

## Dependency installation behavior

Quasar checks executable paths, probes tool identity/help/version output, attempts configured recipes when enabled, and verifies the executable again after installation. It records results rather than silently claiming a tool is ready.

- **Go-based tools:** Subfinder, Amass, Assetfinder, PureDNS, and ProjectDiscovery HTTPX. Install Go yourself from [go.dev/dl](https://go.dev/dl/); Quasar does not install the Go runtime.
- **Cargo-based tool:** Findomain. Install Rust/Cargo from [rust-lang.org](https://www.rust-lang.org/tools/install).
- **pipx-managed tools:** BBOT, KnockPy, theHarvester, and DNSRecon, subject to upstream platform/Python constraints. Depending on your Python version, Quasar may bootstrap pipx in an isolated user environment.
- **Sublist3r:** Cloned from its upstream repository and installed into an isolated virtual environment. The project is legacy and may not work with all modern Python versions.
- **DNSEnum:** Automatic installation is limited to apt-based Linux when Quasar is already running as root. Quasar does not call `sudo`. Other environments may require manual installation or skipping this optional integration.
- **PureDNS:** Needs MassDNS and a configured resolver list for the usual resolution workflow.

Quasar core and the upstream tools are separate pieces of software. Installers may need network access, and tool-specific API keys or configuration may be required. Review installation output before retrying a failed setup.

### ProjectDiscovery HTTPX vs Python HTTPX

Quasar needs the Go-based [ProjectDiscovery HTTPX](https://github.com/projectdiscovery/httpx) CLI. The Python package also uses the name `httpx`, but it is not a substitute. Quasar fingerprints candidate executables and writes ProjectDiscovery HTTPX output to an explicit file as well as capturing stdout. If HTTPX is reported missing or unverified, review `setup_report.json` for candidate paths and probe diagnostics.

### KnockPy package-name conflict

Quasar installs [the official KnockPy repository](https://github.com/guelfoweb/KnockPy) through its Git source instead of blindly trusting a PyPI package with the same name. Its CLI is checked for security-reconnaissance flags. If it still fails, review stderr and the identity check in the setup report.

## Troubleshooting

### Python or virtual environment problems

- Install Python 3.10+ and confirm `python --version` or `python3 --version` works.
- On Linux, some distributions package `venv` separately. Install the appropriate OS package if `python -m venv` fails.
- Python 3.11+ is recommended for easier setup with current pipx releases.
- Run setup from the extracted project directory and make sure your user can write to it.

### An external tool is missing after installation

1. Run `./run.sh --check-tools --no-install` (or the relevant Windows launcher).
2. Open the newest `setup_report.txt` and `setup_report.json`.
3. Check whether the expected runtime (Go, Cargo, Git, or pipx) is installed and on `PATH`.
4. Open a new terminal if you have just changed `PATH`.
5. Follow the upstream tool's official installation documentation and rerun the check.

### HTTPX is detected incorrectly or produces no live results

- Confirm it is ProjectDiscovery HTTPX, not the Python HTTPX client CLI.
- Check the resolved executable path and fingerprint diagnostics in `setup_report.json`.
- Review `raw/HTTPX_stderr.log`, `artifacts/httpx/execution.json`, and `artifacts/httpx/httpx_results.txt` in the target output folder.
- A hostname may resolve but not expose an HTTP/HTTPS service, or a probe may fail because of TLS, connectivity, timeout, or server behavior. A failed probe does not establish that the hostname is nonexistent.

### KnockPy is missing or uses the wrong package

- Verify the installed program's help output includes KnockPy security-reconnaissance options such as `--recon`.
- Confirm Quasar installed from `guelfoweb/KnockPy`, not an unrelated package with the same name.
- Review `raw/KnockPy_stderr.log` and the KnockPy row in `setup_report.json`.
- Consult [`TROUBLESHOOTING_HTTPX_KNOCKPY.md`](TROUBLESHOOTING_HTTPX_KNOCKPY.md) for focused repair commands.

### PureDNS fails

- Verify that `massdns` is installed and accessible.
- Configure a usable resolver file and, if needed, a trusted resolver file.
- Review `artifacts/puredns/` and the PureDNS stderr log.

### Results are limited

- Some passive sources require provider API keys.
- A source may return no data because of rate limits, network restrictions, source availability, or lack of configured credentials.
- Quasar continues when individual tools fail unless strict dependency mode blocks the assessment. Check the run report for `failed`, `partial`, or `skipped` statuses.

More details: [`COMPATIBILITY.md`](COMPATIBILITY.md) and [`TROUBLESHOOTING_HTTPX_KNOCKPY.md`](TROUBLESHOOTING_HTTPX_KNOCKPY.md).

## Testing

Quasar's automated tests use controlled fixtures and mocked subprocess results. They do not enumerate public targets or require the external security tools to be installed.

**Linux/macOS:**

```bash
.venv/bin/python -m unittest discover -s tests -v
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Useful smoke checks:

```bash
./run.sh --help
./run.sh --version
./run.sh --check-tools --no-install --output-dir results/setup-check
```

Check [`TEST_REPORT.md`](TEST_REPORT.md) for the latest recorded test run. Passing unit tests verify application logic and mocked workflows; they do not certify live compatibility with every upstream binary, OS, architecture, API provider, or resolver setup. Native Windows/macOS and full live-tool tests should be performed on the target systems before production use.

## Security and responsible use

- Only assess systems for which you have explicit authorization.
- Respect bug bounty and vulnerability-disclosure program rules, including scope, rate limits, and restrictions on active techniques.
- Use conservative concurrency and timeouts; avoid enabling high-volume techniques unless explicitly approved.
- Do not treat a discovered subdomain or a responsive web service as proof of a security vulnerability.
- Protect result directories: raw reconnaissance data may contain sensitive infrastructure information. The local `results/` directory is ignored by Git, but review files carefully before publishing or sharing artifacts.
- Inspect installation commands and upstream project instructions before running them on sensitive systems.
- Keep API keys and other secrets out of commits, logs, and shared reports.

## Credits and upstream projects

Quasar integrates or orchestrates independently maintained tools. See [Integrated tools](#integrated-tools) for upstream repository links and documentation. Each project has its own license, dependencies, release schedule, and platform support; please consult those upstream projects directly.

## License

Copyright (c) 2027 Th3BlackHol3

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
