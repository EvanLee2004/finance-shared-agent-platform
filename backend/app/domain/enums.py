"""Domain enums (string values match schema CHECK constraints)."""

from __future__ import annotations

ROLE_USER = "user"
ROLE_ADMIN = "admin"

STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"

REVOKE_LOGOUT = "logout"
REVOKE_PASSWORD_CHANGE = "password_change"
REVOKE_ADMIN_KICK = "admin_kick"
REVOKE_EXPIRED = "expired"
REVOKE_REPLACED = "replaced"

AUDIT_LOGIN = "auth.login"
AUDIT_LOGOUT = "auth.logout"
AUDIT_PASSWORD_CHANGE = "auth.password_change"
AUDIT_LOGIN_FAILED = "auth.login_failed"
AUDIT_CHAT_CREATE = "chat.create"
AUDIT_CHAT_MESSAGE = "chat.message"
AUDIT_SKILLS_SYNC = "skills.sync"
AUDIT_SKILLS_GRANT = "skills.grant"

# Skill visibility (schema CHECK)
VIS_PRIVATE = "private"
VIS_PENDING = "pending"
VIS_PUBLISHED = "published"
VIS_DISABLED = "disabled"

PRINCIPAL_USER = "user"
PRINCIPAL_ROLE = "role"
PERM_RUN = "run"
