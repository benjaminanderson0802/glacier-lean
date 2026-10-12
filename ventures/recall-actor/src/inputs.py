"""Validation and normalization for one-item and batch Actor inputs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

FIELDS = ("barcode", "brand", "model", "product_name", "year")


def normalize_input(actor_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(actor_input, Mapping):
        raise ValueError("Input must be a JSON object")
    if "queries" in actor_input:
        queries = actor_input["queries"]
        if not isinstance(queries, list) or not 1 <= len(queries) <= 100:
            raise ValueError("queries must contain between 1 and 100 items")
    else:
        queries = [{field: actor_input[field] for field in FIELDS if field in actor_input}]
    normalized = []
    for index, item in enumerate(queries, 1):
        if not isinstance(item, Mapping):
            raise ValueError(f"Query {index} must be an object")
        query: dict[str, Any] = {}
        for field in FIELDS:
            value = item.get(field)
            if value is None or value == "":
                continue
            if field == "year":
                if isinstance(value, bool) or not isinstance(value, int) or not 1900 <= value <= 2100:
                    raise ValueError(f"Query {index} year must be between 1900 and 2100")
                query[field] = value
            elif not isinstance(value, str):
                raise ValueError(f"Query {index} {field} must be text")
            else:
                value = value.strip()
                if value:
                    if len(value) > (32 if field == "barcode" else 200):
                        raise ValueError(f"Query {index} {field} is too long")
                    query[field] = value
        if not query:
            raise ValueError(f"Query {index} needs at least one item identifier")
        normalized.append(query)
    return normalized
