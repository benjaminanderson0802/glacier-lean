"""Conservative product-to-recall matching."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


def normalize_text(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def normalize_code(value: Any) -> str:
    return "".join(re.findall(r"\d", str(value or "")))


def _tokens(value: Any) -> set[str]:
    return set(normalize_text(value).split())


_GENERIC_PRODUCT_SUFFIXES = {"seat", "sleeper", "toy"}


def _query_product_tokens(query: Mapping[str, Any]) -> list[str]:
    value = query.get("model") or query.get("product_name")
    tokens = normalize_text(value).split()
    while len(tokens) > 2 and tokens[-1] in _GENERIC_PRODUCT_SUFFIXES:
        tokens.pop()
    return tokens


def _contains_phrase(fields: Sequence[Any], phrase_tokens: Sequence[str]) -> bool:
    if not phrase_tokens:
        return False
    for field in fields:
        tokens = normalize_text(field).split()
        if any(tokens[start : start + len(phrase_tokens)] == list(phrase_tokens) for start in range(len(tokens))):
            return True
    return False


def classify_matches(query: Mapping[str, Any], recalls: Sequence[Mapping[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    barcode = normalize_code(query.get("barcode"))
    if barcode:
        exact = [dict(recall) for recall in recalls if barcode in {normalize_code(v) for v in recall.get("barcode_values", [])}]
        if exact:
            return "match", exact
        if not (query.get("brand") and query.get("model")):
            # A source returned a potentially relevant row but omitted its barcode;
            # that cannot support a clean negative result.
            return ("uncertain", []) if recalls else ("no_match", [])

    brand = _tokens(query.get("brand"))
    model = normalize_text(query.get("model")).replace(" ", "")
    product_tokens = _query_product_tokens(query)
    if brand and (model or query.get("product_name")):
        exact_model: list[dict[str, Any]] = []
        possible: list[dict[str, Any]] = []
        for recall in recalls:
            recall_brand = _tokens(recall.get("brand"))
            model_fields = [recall.get("model"), recall.get("title"), recall.get("description")]
            model_tokens = [normalize_text(value).split() for value in model_fields]
            brand_match = brand.issubset(recall_brand) or brand.issubset(_tokens(" ".join(str(v or "") for v in (recall.get("brand"), recall.get("title")))))
            if brand_match:
                model_match = False
                if model:
                    for tokens in model_tokens:
                        for start in range(len(tokens)):
                            compact = ""
                            for token in tokens[start:]:
                                compact += token
                                if compact == model:
                                    model_match = True
                                    break
                                if len(compact) >= len(model):
                                    break
                            if model_match:
                                break
                        if model_match:
                            break
                else:
                    model_match = _contains_phrase(model_fields, product_tokens)
                if model_match:
                    exact_model.append(dict(recall))
                else:
                    possible.append(dict(recall))
        if exact_model:
            return "match", exact_model
        if possible:
            return "uncertain", []
        return "no_match", []

    # A name-only search is deliberately not promoted to a positive identification.
    if query.get("product_name") or query.get("brand") or query.get("model"):
        return "uncertain", []
    return "uncertain", []
