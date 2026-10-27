from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    artifact = artifact_dir / "Amass_output.txt"
    return [executable, "enum", "-passive", "-d", target, "-o", str(artifact)]
