from pathlib import Path


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    # The standard record enumeration mode avoids explicit brute-force modes.
    return [executable, "-d", target, "-t", "std", "--xml", str(artifact_dir / "DNSRecon.xml")]
