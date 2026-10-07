"""Markdown editor compatibility checks for the local memory vault."""

from fastapi import APIRouter

import vault_compat

router = APIRouter()


@router.get("/api/memory/compat")
def compatibility():
    return vault_compat.check_vault()
