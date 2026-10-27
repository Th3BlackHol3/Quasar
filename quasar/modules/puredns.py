from pathlib import Path


def build_resolve_command(executable: str, candidates_file: Path, output_file: Path, config: dict) -> list[str]:
    command = [executable, "resolve", str(candidates_file), "--write", str(output_file), "-q"]
    resolvers = config.get("resolvers_file")
    if resolvers:
        command.extend(["-r", str(resolvers)])
    trusted = config.get("trusted_resolvers_file")
    if trusted:
        command.extend(["--resolvers-trusted", str(trusted)])
    return command
