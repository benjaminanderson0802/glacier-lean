"""A local folder start. The trigger poller supplies the file for each new run."""

import os
from pathlib import Path


def validate_folder(folder: str, home: str) -> Path:
    if not isinstance(folder, str) or not folder.strip():
        raise ValueError("Choose a folder to watch")
    path = Path(folder).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise ValueError("Choose an existing folder")
    data = Path(home).resolve()
    if path == data or data in path.parents:
        raise ValueError("Choose a folder outside Glacier's data folder")
    return path


def run(ctx: dict) -> dict:
    path = str((ctx.get("trigger") or {}).get("file") or "")
    if not path:
        raise ValueError("This step starts when a new file appears")
    return {"state": "done", "output": path, "exit_code": 0}


NODE = {
    "catalog": {
        "type": "file_trigger", "label": "When a file appears",
        "description": "Start when a new file appears in a folder on this computer.",
        "worker": True,
        "fields": [
            {"key": "folder", "label": "Folder", "placeholder": "/path/to/folder", "default": ""},
            {"key": "pattern", "label": "File name pattern", "placeholder": "*.pdf", "default": "*"},
        ],
        "branches": None,
    },
    "run": run,
}
