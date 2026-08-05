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
