from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    artifact = artifact_dir / "Findomain_output.txt"
    return [executable, "-t", target, "-u", str(artifact)]
