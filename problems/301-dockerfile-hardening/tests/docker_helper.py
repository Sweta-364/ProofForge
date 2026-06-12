from pathlib import Path


def dockerfile_lines(starter_dir):
    """Significant (non-comment, non-empty) Dockerfile lines, continuation-joined."""
    raw = (Path(starter_dir) / "Dockerfile").read_text(encoding="utf-8")
    joined = raw.replace("\\\n", " ")
    lines = []
    for line in joined.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines
