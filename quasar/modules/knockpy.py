from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    """Run official KnockPy passive recon using parseable, non-interactive output."""
    return [executable, "-d", target, "--recon", "--json"]
