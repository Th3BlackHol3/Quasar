from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    # theHarvester's -f option writes native reports; keep those separate from captured stdout.
    return [executable, "-d", target, "-b", "all", "-f", str(artifact_dir / "theHarvester")]
