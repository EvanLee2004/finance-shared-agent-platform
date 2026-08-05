"""OpenCode HTTP client — ONLY module allowed to talk to OpenCode."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_OC_BASE = "http://127.0.0.1:4096"
PROBE_TIMEOUT_S = 1.5


@dataclass
class OcProbeResult:
    ok: bool
    endpoint: str
    version: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "endpoint": _mask_endpoint(self.endpoint),
        }
        if self.version is not None:
            out["version"] = self.version
        if self.error is not None and not self.ok:
            out["error"] = self.error
        return out


def _mask_endpoint(url: str) -> str:
    """Hide full path details in health responses."""
    # e.g. http://127.0.0.1:4096 -> 127.0.0.1:***
    try:
        from urllib.parse import urlparse

        p = urlparse(url)
        host = p.hostname or "127.0.0.1"
        return f"{host}:***"
    except Exception:
        return "127.0.0.1:***"


def oc_base_url() -> str:
    return os.environ.get("FSA_OPENCODE_BASE_URL", DEFAULT_OC_BASE).rstrip("/")


class OcClient:
    """Thin HTTP wrapper for OpenCode serve."""

    def __init__(self, base_url: str | None = None, timeout: float = PROBE_TIMEOUT_S) -> None:
        self.base_url = (base_url or oc_base_url()).rstrip("/")
        self.timeout = timeout

    def probe(self) -> OcProbeResult:
        """Check if OpenCode is reachable. Never raises for network failures."""
        url = f"{self.base_url}/"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
            # Any HTTP response means process is up enough for health
            version = resp.headers.get("x-opencode-version") or None
            if resp.status_code < 500:
                return OcProbeResult(
                    ok=True,
                    endpoint=self.base_url,
                    version=version,
                )
            return OcProbeResult(
                ok=False,
                endpoint=self.base_url,
                error=f"http_{resp.status_code}",
            )
        except Exception as exc:  # noqa: BLE001 — probe must never break health
            return OcProbeResult(
                ok=False,
                endpoint=self.base_url,
                error=type(exc).__name__,
            )
