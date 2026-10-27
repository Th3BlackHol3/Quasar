# Quasar v1.2.1 — Dependency and Compatibility Report

This report describes Quasar's cross-platform packaging and the assumptions made by its third-party command adapters. Tool versions and CLI syntax can change; the machine-specific `setup_report.json` produced at runtime is the authority for the system where Quasar is executed.

## Platform support

| Area | Linux | macOS | Windows |
|---|---|---|---|
| Quasar Python core | Supported; Python 3.10+ | Supported; Python 3.10+ | Supported; Python 3.10+ |
| Local virtual environment setup | `setup.sh` / `bootstrap.py` | `setup.sh` / `bootstrap.py` | `setup.ps1`, `setup.bat`, or `bootstrap.py` |
| Run wrapper | `run.sh` | `run.sh` | `run.ps1` or `run.bat` |
| Go-based tools | If upstream binary/module supports OS/architecture and Go is installed | Same | Same; Windows `.exe`/PATH behavior is supported by the manager |
| Cargo-based Findomain | If supported by Rust toolchain/upstream | If supported | If supported by Rust toolchain/upstream |
| pipx-managed tools | Subject to upstream Python/platform constraints | Same | Same; current pipx recommends Python 3.11+ |
| DNSEnum | Automatic install is limited to apt-based Linux when already root; other cases need manual setup | Manual/not configured | Manual/not configured; may require compatible Perl environment |
| PureDNS | Requires MassDNS and resolvers for normal resolution | Same | Requires a compatible MassDNS binary and resolvers; confirm upstream support |

**Important distinction:** Quasar itself is cross-platform. The upstream tools are independent projects, and some do not provide full support for every operating system or architecture. Quasar reports unavailable or unsupported tools rather than claiming they are installed. Missing sources can reduce enumeration coverage; a run is not comprehensive merely because the workflow completes.

## Validation performed in this release

- Quasar version and help smoke checks: passed.
- HTTPX output file/stdout fallback and relative-results-path regression checks: passed.
- Python compilation: passed.
- Standard-library unit tests: **27 passed** including HTTPX/KnockPy regression coverage, bootstrap path checks, and a simulated Windows Python-launcher test.
- Single-target and multi-target workflow tests with mocked external command output: passed.
- Installer code uses per-user paths and doesn't invoke `sudo` or silent administrator elevation.
- Bootstrap creates a local `.venv`, compiles the app, and checks the CLI without requiring installation of optional reconnaissance tools.

**Not validated here:** Live installs or live enumeration against each third-party executable on native Linux, macOS, and Windows. This environment is Linux; native PowerShell/Windows and macOS execution were not available. External tools, service API configuration, DNS resolver behavior, and platform-specific upstream dependencies therefore still require validation on the intended machine. Do not interpret mocked tests as a live integration test.

## Adapter matrix

| Tool | Adapter behavior | Installer recipe | Important dependency/limitation |
|---|---|---|---|
| Subfinder | `subfinder -d DOMAIN -silent ...` | `go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` | Go must be installed. Many passive data sources require API keys. [Upstream](https://github.com/projectdiscovery/subfinder) |
| Sublist3r | `sublist3r -d DOMAIN -o ARTIFACT` | Clone the upstream repository; install into isolated user venv and create an OS-appropriate launcher | Legacy project; newer Python/dependency incompatibilities are possible. Windows launcher runs as a Python script and avoids `.cmd` execution. [Upstream](https://github.com/aboul3la/Sublist3r) |
| BBOT | `bbot -t DOMAIN -p subdomain-enum -rf passive -n NAME -o OUTPUT_DIR` | `pipx install bbot`; if missing, Quasar can bootstrap pipx into a private venv on Python 3.11+ | OS/Python constraints and API configuration vary. [Upstream](https://github.com/blacklanternsecurity/bbot) |
| Amass | `amass enum -passive -d DOMAIN -o ARTIFACT` | `CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@main` | Requires Go; confirm module path against upstream if changed. [Upstream](https://github.com/owasp-amass/amass) |
| Assetfinder | `assetfinder --subs-only DOMAIN` | `go install -v github.com/tomnomnom/assetfinder@latest` | Passive data source coverage varies. [Upstream](https://github.com/tomnomnom/assetfinder) |
| Findomain | `findomain -t DOMAIN -u ARTIFACT` | `cargo install findomain` | Requires Rust/Cargo. Upstream publishes different platform artifacts; prefer its OS-specific instructions when cargo build is unsuitable. [Installation](https://github.com/Findomain/Findomain/blob/master/docs/INSTALLATION.md) |
| KnockPy | `knockpy -d DOMAIN --recon --json` | `pipx install --force git+https://github.com/guelfoweb/knockpy.git` | Quasar verifies the security CLI flags and uses the official Git repository to avoid the unrelated same-named PyPI package. [Upstream](https://github.com/guelfoweb/KnockPy) |
| theHarvester | `theHarvester -d DOMAIN -b all -f ARTIFACT_PREFIX` | `pipx install theHarvester`; may bootstrap pipx | Available data sources and API requirements vary by release. [Upstream](https://github.com/laramies/theHarvester) |
| PureDNS | `puredns resolve CANDIDATES --write RESOLVED -q` | `go install -v github.com/d3mondev/puredns/v2@latest` | Needs MassDNS and resolvers for normal DNS resolution. It adds valid candidates but does not delete unresolved discovery evidence. [Upstream](https://github.com/d3mondev/puredns) |
| DNSRecon | `dnsrecon -d DOMAIN -t std --xml ARTIFACT` | `pipx install git+https://github.com/darkoperator/dnsrecon.git`; may bootstrap pipx | Runtime and OS compatibility follow the upstream Python package. [Upstream](https://github.com/darkoperator/dnsrecon) |
| DNSEnum | `dnsenum --noreverse --nocolor --subfile ARTIFACT DOMAIN` | `apt-get install -y dnsenum` only when already root on an apt-based machine | No automatic native Windows/macOS recipe is configured. May perform active DNS queries. [Kali package docs](https://www.kali.org/tools/dnsenum/) |
| HTTPX (ProjectDiscovery) | `httpx -l INPUT -silent -no-fallback -threads N -timeout N -retries N -disable-update-check -o OUTPUT` | `go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest` | Quasar fingerprints current upstream version banners, rejects Python HTTPX client CLIs, and reads an explicit output file. [Upstream](https://github.com/projectdiscovery/httpx) |

## Runtime behavior

1. Quasar searches `PATH` and common Go, Cargo, pipx, and Quasar user-local binary directories, including Windows application-data paths.
2. It probes tool version/help output; ProjectDiscovery HTTPX requires a recognizable Go CLI version response.
3. Missing supported tools can trigger an installation attempt when enabled. Go/Rust runtimes are not installed by Quasar; administrator elevation is never silently requested.
4. A package install return code alone is not enough: Quasar probes again after the installer exits.
5. Missing or failed tools are recorded and skipped unless `--strict-dependencies` is set.
6. Hostname extraction accepts only the target itself or names ending with `.<target>`, preventing suffix lookalikes from contaminating a target's output.
7. Automated workflow tests use mocks and make no public DNS or HTTP requests.


## Entry point and terminal branding

The primary application entry point is `quasar.py`. Linux/macOS and Windows launchers and bootstrap smoke checks reference this filename. The requested ASCII brand banner is printed on user-facing CLI and setup startup; internal smoke checks suppress duplicate banners. The banner uses a safe encoding fallback for consoles that cannot display the block glyphs.
