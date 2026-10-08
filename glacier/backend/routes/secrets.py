"""HTTP endpoints for managing secret names and values."""
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import secrets_store
import vault
import audit_log


router = APIRouter()
_VALID_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


class SecretValue(BaseModel):
    value: str


@router.get("/api/secrets")
def list_secrets():
    return secrets_store.names()


@router.put("/api/secrets/{name}")
def save_secret(name: str, body: SecretValue):
    if not _VALID_NAME.fullmatch(name):
        raise HTTPException(400, "Use letters, numbers, dots, underscores, or dashes in a secret name")
    try:
        secrets_store.set(name, body.value)
    except Exception:
        raise HTTPException(500, "Could not save this secret in the operating-system keychain")
    audit_log.record("secret.set", what={"name": name})
    return {"saved": True}


@router.delete("/api/secrets/{name}")
def remove_secret(name: str):
    if not _VALID_NAME.fullmatch(name):
        raise HTTPException(400, "That secret name is not allowed")
    try:
        secrets_store.delete(name)
    except Exception:
        raise HTTPException(500, "Could not remove this secret from the operating-system keychain")
    if vault.VAULT:
        vault.record_event("owner", "delete", {"kind": "secret", "name": name})
    audit_log.record("secret.deleted", what={"name": name})
    return {"deleted": True}
