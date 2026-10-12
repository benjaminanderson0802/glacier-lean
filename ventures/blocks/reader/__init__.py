"""Local-first document extraction with explicit cross-engine agreement."""

from . import reader as _implementation
_available_engines = _implementation._available_engines


def read_document(path, schema=None):
    # Keep engine selection replaceable for independent, deterministic checks.
    _implementation._available_engines = _available_engines
    return _implementation.read_document(path, schema)

__all__ = ["read_document"]
