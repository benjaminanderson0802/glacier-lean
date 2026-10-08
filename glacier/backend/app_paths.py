"""Paths for state stored under GLACIER_HOME (or the local data folder)."""

import os
from pathlib import Path


def app_data_home() -> Path:
    return Path(os.environ.get("GLACIER_HOME", "data")).resolve()


def state_file(name: str) -> Path:
    return app_data_home() / name
