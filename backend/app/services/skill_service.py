"""Skills sync, grants, runnable filtering (published ∩ grant; admin sees all)."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.adapters import skills_repo
from app.db.migrate import utc_now
from app.domain import enums
from app.domain.errors import Forbidden, NotFound, ValidationError
from app.domain.ids import new_id
from app.services.audit_service import write_audit


def _system_owner_id(conn: sqlite3.Connection) -> str:
    """Use first admin as owner for published git skills, or create placeholder."""
    row = conn.execute(
        """
        SELECT id FROM users
        WHERE role = ? AND status = ? AND deleted_at IS NULL
        ORDER BY created_at ASC LIMIT 1
        """,
        (enums.ROLE_ADMIN, enums.STATUS_ACTIVE),
    ).fetchone()
    if row:
        return str(row["id"])
    # Fallback: any user
    row2 = conn.execute(
        "SELECT id FROM users WHERE deleted_at IS NULL ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    if not row2:
        raise ValidationError("库中无用户，无法同步 skills 归属")
    return str(row2["id"])


def sync_from_local(
    conn: sqlite3.Connection,
    *,
    actor_user_id: str,
    actor_role: str,
    pull: bool = False,
) -> dict[str, Any]:
    """Load catalog.yaml into skills table as published. Admin only if pull/sync write."""
    if actor_role != enums.ROLE_ADMIN:
        raise Forbidden("仅管理员可同步 Skills")
    root = skills_repo.skills_root()
    if root is None:
        return {
            "ok": False,
            "error": "skills_root_missing",
            "message": "未配置 FSA_SKILLS_ROOT 且未找到本地 finance-shared-skills",
            "upserted": 0,
        }
    pull_info = None
    if pull:
        pull_info = skills_repo.git_pull(root)
    cat = skills_repo.load_catalog(root)
    if not cat.get("ok"):
        return {
            "ok": False,
            "error": cat.get("error") or "catalog_invalid",
            "message": "catalog.yaml 无效或缺失",
            "upserted": 0,
            "root": cat.get("root"),
            "pull": pull_info,
        }
    owner = _system_owner_id(conn)
    now = utc_now()
    upserted = 0
    for it in cat["items"]:
        skill_key = it["skill_key"]
        existing = conn.execute(
            "SELECT id FROM skills WHERE skill_key = ? AND deleted_at IS NULL",
            (skill_key,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE skills SET
                  title = ?, summary = ?, current_version = ?, content_hash = ?,
                  visibility = 'published', storage_kind = 'published_git',
                  rel_path = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    it["title"],
                    it["summary"],
                    it["version"],
                    it["content_hash"],
                    it["rel_path"],
                    now,
                    existing["id"],
                ),
            )
        else:
            sid = new_id()
            conn.execute(
                """
                INSERT INTO skills(
                  id, skill_key, owner_user_id, visibility, title, summary,
                  risk_level, current_version, content_hash, storage_kind, rel_path,
                  catalog_extra_json, created_at, updated_at, deleted_at
                ) VALUES (?, ?, ?, 'published', ?, ?, 'low', ?, ?, 'published_git', ?, NULL, ?, ?, NULL)
                """,
                (
                    sid,
                    skill_key,
                    owner,
                    it["title"],
                    it["summary"],
                    it["version"],
                    it["content_hash"],
                    it["rel_path"],
                    now,
                    now,
                ),
            )
        upserted += 1
    tip = skills_repo.git_tip(root)
    write_audit(
        conn,
        action=enums.AUDIT_SKILLS_SYNC,
        resource_type="skills_repo",
        actor_user_id=actor_user_id,
        summary=f"sync catalog upserted={upserted} root={root}",
        detail={
            "upserted": upserted,
            "root": str(root),
            "tip": tip,
            "pull": pull_info,
        },
    )
    conn.commit()
    return {
        "ok": True,
        "error": None,
        "upserted": upserted,
        "root": str(root),
        "tip": tip,
        "pull": pull_info,
        "count": cat.get("count"),
    }


def list_skills(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    role: str,
    scope: str = "runnable",
) -> list[dict[str, Any]]:
    """scope=runnable: published ∩ (grant or admin). scope=all: admin all / user own+granted published."""
    scope = (scope or "runnable").strip().lower()
    if scope not in ("runnable", "all", "mine"):
        raise ValidationError("scope 须为 runnable|all|mine")

    rows = conn.execute(
        """
        SELECT * FROM skills
        WHERE deleted_at IS NULL
        ORDER BY skill_key ASC
        """
    ).fetchall()

    grant_skill_ids = _grant_skill_ids_for_user(conn, user_id=user_id, role=role)
    out: list[dict[str, Any]] = []
    for r in rows:
        vis = r["visibility"]
        sid = r["id"]
        is_admin = role == enums.ROLE_ADMIN
        granted = sid in grant_skill_ids
        owned = r["owner_user_id"] == user_id
        runnable = vis == enums.VIS_PUBLISHED and (is_admin or granted)
        if scope == "runnable" and not runnable:
            continue
        if scope == "mine" and not owned and not granted:
            continue
        if scope == "all" and not is_admin and not owned and not granted and vis != "published":
            # non-admin all: still only see published (for discovery) + own
            if vis != "published":
                continue
        item = _skill_public(r)
        item["runnable"] = runnable
        item["granted"] = granted or is_admin
        out.append(item)
    return out


def _grant_skill_ids_for_user(
    conn: sqlite3.Connection, *, user_id: str, role: str
) -> set[str]:
    rows = conn.execute(
        """
        SELECT skill_id FROM skill_grants
        WHERE (principal_type = 'user' AND principal_id = ?)
           OR (principal_type = 'role' AND principal_id = ?)
        """,
        (user_id, role),
    ).fetchall()
    return {str(r["skill_id"]) for r in rows}


def _skill_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "skill_key": row["skill_key"],
        "title": row["title"],
        "summary": row["summary"],
        "visibility": row["visibility"],
        "current_version": row["current_version"],
        "content_hash": row["content_hash"],
        "rel_path": row["rel_path"],
        "owner_user_id": row["owner_user_id"],
        "updated_at": row["updated_at"],
    }


def get_skill(
    conn: sqlite3.Connection, *, user_id: str, role: str, skill_id: str
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM skills WHERE id = ? AND deleted_at IS NULL",
        (skill_id,),
    ).fetchone()
    if row is None:
        raise NotFound("技能不存在")
    is_admin = role == enums.ROLE_ADMIN
    grants = _grant_skill_ids_for_user(conn, user_id=user_id, role=role)
    owned = row["owner_user_id"] == user_id
    published = row["visibility"] == "published"
    if not is_admin and not owned and not (published and skill_id in grants) and not published:
        raise NotFound("技能不存在")
    # published visible to all for discovery; private only owner/admin
    if row["visibility"] == "private" and not is_admin and not owned:
        raise NotFound("技能不存在")
    item = _skill_public(row)
    item["runnable"] = published and (is_admin or skill_id in grants)
    item["granted"] = is_admin or skill_id in grants
    return item


def grant_run(
    conn: sqlite3.Connection,
    *,
    actor_user_id: str,
    actor_role: str,
    skill_id: str,
    principal_type: str,
    principal_id: str,
) -> dict[str, Any]:
    if actor_role != enums.ROLE_ADMIN:
        raise Forbidden("仅管理员可授权")
    if principal_type not in (enums.PRINCIPAL_USER, enums.PRINCIPAL_ROLE):
        raise ValidationError("principal_type 须为 user|role")
    if not principal_id.strip():
        raise ValidationError("principal_id 必填")
    skill = conn.execute(
        "SELECT id, skill_key, visibility FROM skills WHERE id = ? AND deleted_at IS NULL",
        (skill_id,),
    ).fetchone()
    if skill is None:
        raise NotFound("技能不存在")
    now = utc_now()
    existing = conn.execute(
        """
        SELECT id FROM skill_grants
        WHERE skill_id = ? AND principal_type = ? AND principal_id = ? AND perm = 'run'
        """,
        (skill_id, principal_type, principal_id),
    ).fetchone()
    if existing:
        gid = str(existing["id"])
    else:
        gid = new_id()
        conn.execute(
            """
            INSERT INTO skill_grants(
              id, skill_id, principal_type, principal_id, perm, created_by, created_at
            ) VALUES (?, ?, ?, ?, 'run', ?, ?)
            """,
            (gid, skill_id, principal_type, principal_id, actor_user_id, now),
        )
    write_audit(
        conn,
        action=enums.AUDIT_SKILLS_GRANT,
        resource_type="skill_grant",
        resource_id=gid,
        actor_user_id=actor_user_id,
        summary=f"grant run skill={skill['skill_key']} to {principal_type}:{principal_id}",
        detail={
            "skill_id": skill_id,
            "principal_type": principal_type,
            "principal_id": principal_id,
        },
    )
    conn.commit()
    return {
        "id": gid,
        "skill_id": skill_id,
        "principal_type": principal_type,
        "principal_id": principal_id,
        "perm": "run",
    }


def list_audit(
    conn: sqlite3.Connection,
    *,
    actor_role: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if actor_role != enums.ROLE_ADMIN:
        raise Forbidden("仅管理员可查看审计")
    limit = max(1, min(int(limit), 200))
    rows = conn.execute(
        """
        SELECT id, ts, actor_user_id, action, resource_type, resource_id,
               chat_id, summary, detail_json
        FROM audit_events
        ORDER BY ts DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "ts": r["ts"],
            "actor_user_id": r["actor_user_id"],
            "action": r["action"],
            "resource_type": r["resource_type"],
            "resource_id": r["resource_id"],
            "chat_id": r["chat_id"],
            "summary": r["summary"],
            "detail_json": r["detail_json"],
        }
        for r in rows
    ]


def repo_status() -> dict[str, Any]:
    root = skills_repo.skills_root()
    if root is None:
        return {"ok": False, "root": None, "tip": None, "error": "skills_root_missing"}
    tip = skills_repo.git_tip(root)
    cat_ok = (root / "catalog.yaml").is_file()
    return {
        "ok": cat_ok,
        "root": str(root),
        "tip": tip,
        "error": None if cat_ok else "catalog_missing",
    }
