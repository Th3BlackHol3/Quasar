from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    artifact = artifact_dir / "Sublist3r_output.txt"
    return [executable, "-d", target, "-o", str(artifact)]
