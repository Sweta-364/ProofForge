from pathlib import Path

import yaml

WORKFLOW_REL = ".github/workflows/ci.yml"


def workflow_text(starter_dir):
    return (Path(starter_dir) / WORKFLOW_REL).read_text(encoding="utf-8")


def workflow_config(starter_dir):
    return yaml.safe_load(workflow_text(starter_dir))


def triggers(config):
    """The 'on' key - yaml.safe_load parses a bare 'on' as boolean True."""
    raw = config.get("on", config.get(True))
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return list(raw.keys())
    return []
