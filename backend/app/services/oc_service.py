"""OpenCode use-cases for routes — sole entry that may construct OcClient.

Routes/api must not import OcClient or build OC URLs; call this module (or chat_service).
"""

from __future__ import annotations

from typing import Any

from app.adapters.oc_client import OcClient
from app.adapters.oc_client import enable_guide as _enable_guide


def probe() -> dict[str, Any]:
    return OcClient().probe().as_dict()


def list_models() -> dict[str, Any]:
    return OcClient().list_models()


def enable_guide() -> dict[str, Any]:
    return _enable_guide()


def client() -> OcClient:
    """For services that need a live client instance (chat bind/send)."""
    return OcClient()
