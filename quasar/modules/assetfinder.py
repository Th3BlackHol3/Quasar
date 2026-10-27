from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    return [executable, "--subs-only", target]
