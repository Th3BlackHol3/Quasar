from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    return [executable, "-d", target, "-silent", "-timeout", str(config.get("source_timeout", 30)),
            "-max-time", str(config.get("source_max_minutes", 5))]
