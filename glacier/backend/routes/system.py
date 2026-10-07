"""System discovery and effective setup settings."""
from fastapi import APIRouter

import system_check

router = APIRouter()


@router.get("/api/system/check")
def check_system():
    return system_check.check_system()


@router.get("/api/system/settings")
def system_settings():
    return system_check.effective_settings(include_ask_route=True)
