from pathlib import Path
import re


def build_command(executable: str, target: str, raw_dir: Path, artifact_dir: Path, config: dict) -> list[str]:
    scan_name = "subenum_" + re.sub(r"[^a-zA-Z0-9_-]", "_", target)
    command = [executable, "-t", target, "-p", "subdomain-enum", "-rf", "passive",
               "-n", scan_name, "-o", str(artifact_dir)]
    # BBOT writes scan artifacts to the provided output directory.
    return command
