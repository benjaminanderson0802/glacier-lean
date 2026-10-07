"""Store secret values in the operating-system keyring and names in GLACIER_HOME."""
import json
import builtins
import os
import re
import tempfile

import keyring


SERVICE = "Glacier"
PLACEHOLDER = re.compile(r"\{secret:([^{}]+)\}")


def _home() -> str:
    return os.path.abspath(os.environ.get("GLACIER_HOME", "data"))


def _names_path() -> str:
    return os.path.join(_home(), "secret_names.json")


def names() -> list[str]:
    """Return the names index; this file never contains secret values."""
    try:
        with open(_names_path(), encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        return []
    if not isinstance(value, list) or any(not isinstance(name, str) for name in value):
        raise RuntimeError("The saved secret names list is damaged")
    return sorted(builtins.set(value))


def _write_names(values: list[str]) -> None:
    home = _home()
    os.makedirs(home, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".secret_names-", dir=home, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(sorted(builtins.set(values)), handle, indent=2)
            handle.write("\n")
        os.replace(temp_path, _names_path())
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def set(name: str, value: str) -> None:
    """Save a value in the system keyring and record only its name locally."""
    keyring.set_password(SERVICE, name, value)
    _write_names([*names(), name])


def delete(name: str) -> None:
    """Delete a keyring value and remove its name from the local index."""
    if name in names():
        try:
            keyring.delete_password(SERVICE, name)
        except keyring.errors.PasswordDeleteError:
            pass
        _write_names([saved for saved in names() if saved != name])


def _value(name: str) -> str:
    value = keyring.get_password(SERVICE, name)
    if value is None:
        raise ValueError(f"Unknown secret: {name}")
    return value


def resolve(text: str) -> str:
    """Replace {secret:NAME} placeholders for execution-time use."""
    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in names():
            raise ValueError(f"Unknown secret: {name}")
        return _value(name)

    return PLACEHOLDER.sub(replace, text)


def redact(text: str) -> str:
    """Replace known keyring values with their names in output text."""
    result = text
    # Replace longer values first so a shorter secret cannot expose part of a longer one.
    values = [
        (value, name)
        for name in names()
        if (value := keyring.get_password(SERVICE, name)) and len(value) >= 4
    ]
    for value, name in sorted(values, key=lambda item: len(item[0]), reverse=True):
        result = result.replace(value, f"[secret {name}]")
    return result
