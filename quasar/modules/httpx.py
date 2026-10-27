from pathlib import Path


def build_command(executable: str, input_file: Path, config: dict, output_file: Path | None = None) -> list[str]:
    """Build a ProjectDiscovery HTTPX command, never the Python httpx client CLI."""
    command = [
        executable, "-l", str(input_file), "-silent", "-no-fallback",
        "-threads", str(config.get("httpx_threads", 10)),
        "-timeout", str(config.get("httpx_timeout", 8)),
        "-retries", str(config.get("httpx_retries", 1)),
        "-disable-update-check",
    ]
    if output_file is not None:
        command.extend(["-o", str(output_file)])
    return command
