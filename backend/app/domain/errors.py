"""Stable API error codes."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AuthFailed(AppError):
    def __init__(self, message: str = "用户名或密码错误") -> None:
        super().__init__("auth_failed", message, 401)


class AuthRequired(AppError):
    def __init__(self, message: str = "未登录或会话已失效") -> None:
        super().__init__("auth_required", message, 401)


class ValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("validation_error", message, 422)


class NotFound(AppError):
    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__("not_found", message, 404)


class OcUnavailable(AppError):
    """Send path needs OpenCode; platform still usable without it."""

    def __init__(
        self,
        message: str = "OpenCode 未就绪。请在工作台启用 OpenCode 后再发送消息。",
    ) -> None:
        super().__init__("oc_unavailable", message, 503)


class Forbidden(AppError):
    def __init__(self, message: str = "无权限") -> None:
        super().__init__("forbidden", message, 403)
