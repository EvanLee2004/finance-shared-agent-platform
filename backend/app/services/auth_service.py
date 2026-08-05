"""AuthService: password hashing, sessions, login/logout/change-password."""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.db.migrate import utc_now
from app.domain import enums
from app.domain.errors import AuthFailed, AuthRequired, ValidationError
from app.domain.ids import new_id
from app.services.audit_service import write_audit

# Argon2id defaults (argon2-cffi PasswordHasher uses Argon2id by default)
# Documented params for ops: time_cost=2, memory_cost=65536, parallelism=1
_PH = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)

COOKIE_NAME = "fsa_sid"
SESSION_HOURS = 24
TOKEN_BYTES = 32


@dataclass
class UserRecord:
    id: str
    username: str
    display_name: str
    role: str
    status: str
    must_change_password: int
    password_hash: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "status": self.status,
            "must_change_password": bool(self.must_change_password),
        }


@dataclass
class SessionRecord:
    id: str
    user_id: str
    token_hash: str
    expires_at: str
    revoked_at: str | None


def hash_password(password: str) -> str:
    return _PH.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _PH.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _row_user(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        role=row["role"],
        status=row["status"],
        must_change_password=int(row["must_change_password"]),
        password_hash=row["password_hash"],
    )


def get_user_by_username(conn: sqlite3.Connection, username: str) -> UserRecord | None:
    norm = username.strip().lower()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND deleted_at IS NULL",
        (norm,),
    ).fetchone()
    return _row_user(row) if row else None


def get_user_by_id(conn: sqlite3.Connection, user_id: str) -> UserRecord | None:
    row = conn.execute(
        "SELECT * FROM users WHERE id = ? AND deleted_at IS NULL",
        (user_id,),
    ).fetchone()
    return _row_user(row) if row else None


def count_admins(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c FROM users
        WHERE role = ? AND status = ? AND deleted_at IS NULL
        """,
        (enums.ROLE_ADMIN, enums.STATUS_ACTIVE),
    ).fetchone()
    return int(row["c"] if isinstance(row, sqlite3.Row) else row[0])


def bootstrap_admin_if_needed(conn: sqlite3.Connection) -> str | None:
    """Create bootstrap admin only when no admin exists.

    Env: FSA_BOOTSTRAP_ADMIN_USER / FSA_BOOTSTRAP_ADMIN_PASSWORD
    Returns new user id or None if skipped.
    """
    if count_admins(conn) > 0:
        return None
    username = os.environ.get("FSA_BOOTSTRAP_ADMIN_USER", "").strip()
    password = os.environ.get("FSA_BOOTSTRAP_ADMIN_PASSWORD", "")
    if not username or not password:
        return None
    return create_user(
        conn,
        username=username,
        password=password,
        display_name=username,
        role=enums.ROLE_ADMIN,
    )


def create_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    password: str,
    display_name: str,
    role: str = enums.ROLE_USER,
) -> str:
    user_id = new_id()
    now = utc_now()
    norm = username.strip().lower()
    if not norm or not password:
        raise ValidationError("username and password required")
    conn.execute(
        """
        INSERT INTO users(
          id, username, display_name, password_hash, role, status,
          must_change_password, last_login_at, created_at, updated_at, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, NULL)
        """,
        (
            user_id,
            norm,
            display_name or norm,
            hash_password(password),
            role,
            enums.STATUS_ACTIVE,
            now,
            now,
        ),
    )
    return user_id


def login(
    conn: sqlite3.Connection,
    *,
    username: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[UserRecord, str]:
    """Verify credentials and create session.

    Returns (user, raw_token). Cookie stores raw_token; DB stores SHA-256.
    """
    user = get_user_by_username(conn, username)
    if user is None or user.status != enums.STATUS_ACTIVE:
        write_audit(
            conn,
            action=enums.AUDIT_LOGIN_FAILED,
            resource_type="user",
            summary="login failed",
            ip=ip,
            detail={"username": username.strip().lower()},
        )
        conn.commit()
        raise AuthFailed()
    if not verify_password(user.password_hash, password):
        write_audit(
            conn,
            action=enums.AUDIT_LOGIN_FAILED,
            resource_type="user",
            resource_id=user.id,
            actor_user_id=user.id,
            summary="login failed",
            ip=ip,
        )
        conn.commit()
        raise AuthFailed()

    raw_token = generate_session_token()
    token_hash = hash_token(raw_token)
    session_id = new_id()
    now = utc_now()
    expires = (
        datetime.now(UTC) + timedelta(hours=SESSION_HOURS)
    ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    conn.execute(
        """
        INSERT INTO auth_sessions(
          id, user_id, token_hash, created_at, expires_at, last_seen_at,
          revoked_at, revoke_reason, ip, user_agent
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
        """,
        (session_id, user.id, token_hash, now, expires, now, ip, user_agent),
    )
    conn.execute(
        "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
        (now, now, user.id),
    )
    write_audit(
        conn,
        action=enums.AUDIT_LOGIN,
        resource_type="session",
        resource_id=session_id,
        actor_user_id=user.id,
        summary=f"login ok: {user.username}",
        ip=ip,
    )
    conn.commit()
    return user, raw_token


def resolve_session(
    conn: sqlite3.Connection, raw_token: str | None
) -> tuple[UserRecord, SessionRecord]:
    if not raw_token:
        raise AuthRequired()
    th = hash_token(raw_token)
    row = conn.execute(
        """
        SELECT s.id AS sid, s.user_id, s.token_hash, s.expires_at, s.revoked_at,
               u.id, u.username, u.display_name, u.role, u.status,
               u.must_change_password, u.password_hash
        FROM auth_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND u.deleted_at IS NULL
        """,
        (th,),
    ).fetchone()
    if row is None:
        raise AuthRequired()
    if row["revoked_at"] is not None:
        raise AuthRequired()
    # expires_at ISO compare works for Z timestamps
    now = utc_now()
    if row["expires_at"] < now:
        raise AuthRequired()
    if row["status"] != enums.STATUS_ACTIVE:
        raise AuthRequired()

    user = UserRecord(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        role=row["role"],
        status=row["status"],
        must_change_password=int(row["must_change_password"]),
        password_hash=row["password_hash"],
    )
    session = SessionRecord(
        id=row["sid"],
        user_id=row["user_id"],
        token_hash=row["token_hash"],
        expires_at=row["expires_at"],
        revoked_at=row["revoked_at"],
    )
    conn.execute(
        "UPDATE auth_sessions SET last_seen_at = ? WHERE id = ?",
        (now, session.id),
    )
    conn.commit()
    return user, session


def logout(
    conn: sqlite3.Connection,
    *,
    raw_token: str | None,
    ip: str | None = None,
) -> None:
    if not raw_token:
        return
    th = hash_token(raw_token)
    row = conn.execute(
        "SELECT id, user_id, revoked_at FROM auth_sessions WHERE token_hash = ?",
        (th,),
    ).fetchone()
    if row is None or row["revoked_at"] is not None:
        return
    now = utc_now()
    conn.execute(
        """
        UPDATE auth_sessions
        SET revoked_at = ?, revoke_reason = ?
        WHERE id = ?
        """,
        (now, enums.REVOKE_LOGOUT, row["id"]),
    )
    write_audit(
        conn,
        action=enums.AUDIT_LOGOUT,
        resource_type="session",
        resource_id=row["id"],
        actor_user_id=row["user_id"],
        summary="logout",
        ip=ip,
    )
    conn.commit()


def revoke_all_user_sessions(
    conn: sqlite3.Connection,
    user_id: str,
    reason: str,
) -> int:
    now = utc_now()
    cur = conn.execute(
        """
        UPDATE auth_sessions
        SET revoked_at = ?, revoke_reason = ?
        WHERE user_id = ? AND revoked_at IS NULL
        """,
        (now, reason, user_id),
    )
    return int(cur.rowcount)


def change_password(
    conn: sqlite3.Connection,
    *,
    user: UserRecord,
    old_password: str,
    new_password: str,
    ip: str | None = None,
) -> None:
    if not new_password or len(new_password) < 8:
        raise ValidationError("new_password must be at least 8 characters")
    if not verify_password(user.password_hash, old_password):
        raise AuthFailed("原密码错误")
    now = utc_now()
    conn.execute(
        """
        UPDATE users
        SET password_hash = ?, must_change_password = 0, updated_at = ?
        WHERE id = ?
        """,
        (hash_password(new_password), now, user.id),
    )
    revoke_all_user_sessions(conn, user.id, enums.REVOKE_PASSWORD_CHANGE)
    write_audit(
        conn,
        action=enums.AUDIT_PASSWORD_CHANGE,
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        summary="password changed; all sessions revoked",
        ip=ip,
    )
    conn.commit()
