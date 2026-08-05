"""OpenCode HTTP client — ONLY module allowed to talk to OpenCode."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_OC_BASE = "http://127.0.0.1:4096"
PROBE_TIMEOUT_S = 2.0
CHAT_TIMEOUT_S = 180.0


@dataclass
class OcProbeResult:
    ok: bool
    endpoint: str
    version: str | None = None
    error: str | None = None
    mode: str = "optional"  # platform works without OC

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "endpoint": _mask_endpoint(self.endpoint),
            "mode": self.mode,
            "required": False,
        }
        if self.version is not None:
            out["version"] = self.version
        if self.error is not None and not self.ok:
            out["error"] = self.error
        return out


def _mask_endpoint(url: str) -> str:
    try:
        p = urlparse(url)
        host = p.hostname or "127.0.0.1"
        port = p.port
        if port:
            return f"{host}:{port}"
        return host
    except Exception:
        return "127.0.0.1:4096"


def oc_base_url() -> str:
    return os.environ.get("FSA_OPENCODE_BASE_URL", DEFAULT_OC_BASE).rstrip("/")


class OcClient:
    """Thin HTTP wrapper for OpenCode serve (optional runtime)."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = PROBE_TIMEOUT_S,
        chat_timeout: float = CHAT_TIMEOUT_S,
    ) -> None:
        self.base_url = (base_url or oc_base_url()).rstrip("/")
        self.timeout = timeout
        self.chat_timeout = chat_timeout

    def probe(self) -> OcProbeResult:
        """Prefer /global/health; fall back to /. Never raises."""
        last_err = "unreachable"
        for path in ("/global/health", "/api/health", "/"):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(f"{self.base_url}{path}")
                if resp.status_code >= 500:
                    last_err = f"http_{resp.status_code}"
                    continue
                version = None
                try:
                    body = resp.json()
                    if isinstance(body, dict):
                        version = body.get("version")
                        data = body.get("data")
                        if isinstance(data, dict) and not version:
                            version = data.get("version")
                        if body.get("healthy") is False:
                            return OcProbeResult(
                                ok=False,
                                endpoint=self.base_url,
                                version=version,
                                error="unhealthy",
                            )
                except Exception:
                    version = resp.headers.get("x-opencode-version")
                return OcProbeResult(ok=True, endpoint=self.base_url, version=version)
            except Exception as exc:  # noqa: BLE001
                last_err = type(exc).__name__
                continue
        return OcProbeResult(ok=False, endpoint=self.base_url, error=last_err)

    def create_session(self, title: str = "财务中台会话") -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/session",
                json={"title": title},
            )
            resp.raise_for_status()
            return resp.json()

    def send_message(self, session_id: str, text: str) -> dict[str, Any]:
        """POST /session/{id}/message with text part; may return error payload."""
        body = {"parts": [{"type": "text", "text": text}]}
        with httpx.Client(timeout=self.chat_timeout) as client:
            resp = client.post(
                f"{self.base_url}/session/{session_id}/message",
                json=body,
            )
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text, "status_code": resp.status_code}
            if not isinstance(data, dict):
                data = {"data": data, "status_code": resp.status_code}
            if resp.status_code >= 400:
                data["_http_status"] = resp.status_code
            return data


def extract_assistant_text(oc_response: dict[str, Any]) -> str:
    """Best-effort extract human text from OC message response."""
    if not isinstance(oc_response, dict):
        return str(oc_response)

    if oc_response.get("_http_status") and oc_response.get("_http_status", 0) >= 400:
        msg = oc_response.get("message") or oc_response.get("error") or oc_response.get("raw")
        return f"[OpenCode HTTP 错误] {msg or oc_response.get('_http_status')}"

    info = oc_response.get("info") or {}
    err = info.get("error") if isinstance(info, dict) else None
    if isinstance(err, dict):
        data = err.get("data") or {}
        msg = data.get("message") or err.get("name") or "OpenCode 调用失败"
        return f"[OpenCode 错误] {msg}"

    # nested data.info / data.parts
    data = oc_response.get("data")
    if isinstance(data, dict):
        nested = extract_assistant_text(data)
        if nested and not nested.startswith("[OpenCode 已响应"):
            return nested

    parts = oc_response.get("parts")
    if isinstance(parts, list):
        chunks: list[str] = []
        for p in parts:
            if not isinstance(p, dict):
                continue
            if p.get("type") == "text" and p.get("text"):
                chunks.append(str(p["text"]))
            elif p.get("text"):
                chunks.append(str(p["text"]))
        if chunks:
            return "\n".join(chunks)

    if oc_response.get("raw"):
        return str(oc_response["raw"])[:2000]
    return "[OpenCode 已响应，但未能解析文本]"


def extract_session_id(oc_create_response: dict[str, Any]) -> str | None:
    if not isinstance(oc_create_response, dict):
        return None
    for key in ("id", "sessionID", "session_id"):
        if oc_create_response.get(key):
            return str(oc_create_response[key])
    data = oc_create_response.get("data")
    if isinstance(data, dict):
        for key in ("id", "sessionID", "session_id"):
            if data.get(key):
                return str(data[key])
    return None


def enable_guide() -> dict[str, Any]:
    """Copyable commands for user-confirmed OC setup (no auto-install)."""
    base = oc_base_url()
    host = "127.0.0.1"
    port = 4096
    try:
        p = urlparse(base)
        host = p.hostname or host
        port = p.port or port
    except Exception:
        pass
    return {
        "title": "启用 OpenCode（可选）",
        "summary": (
            "中台可不依赖 OpenCode 独立使用（登录、工作台、本机说明、技能目录只读）。"
            "智能对话需要本机 opencode serve。中台不会在未确认时自动安装或改系统。"
        ),
        "confirm_text": (
            "我将按官方方式在本机检测/更新/启动 OpenCode。"
            "中台只提供可复制命令，不会静默执行 brew install，也不会写入 API Key。"
        ),
        "commands": [
            {
                "label": "检测是否已安装",
                "cmd": "which opencode && opencode --version",
            },
            {
                "label": "更新到最新（已安装时）",
                "cmd": "opencode upgrade",
            },
            {
                "label": "官方安装（未安装时，请按 opencode.ai 文档执行）",
                "cmd": "curl -fsSL https://opencode.ai/install | bash",
            },
            {
                "label": "启动本机 serve（仅回环）",
                "cmd": f"opencode serve --port {port} --hostname {host}",
            },
            {
                "label": "探测健康（另开终端）",
                "cmd": f"curl -sS {base}/global/health || curl -sS {base}/",
            },
        ],
        "after_start": "启动成功后回到中台点「我已启动」，将重新探测。",
        "troubleshooting": [
            "确认端口未被占用：lsof -nP -iTCP:4096 -sTCP:LISTEN",
            "模型 API Key 在 OpenCode 侧配置（/connect 或 opencode.json），勿提交 git",
            "浏览器永远不要直连 OpenCode，只访问中台",
            "serve 日志中的 provider/auth 错误请在 OC 文档排查",
        ],
        "probe_base": base,
        "probe_endpoint_masked": _mask_endpoint(base),
    }
