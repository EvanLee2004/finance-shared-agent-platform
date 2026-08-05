"""Skills repository adapter — local clone and optional git pull (no push)."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_GITEE = "https://gitee.com/Lee157/finance-shared-skills.git"


def skills_root() -> Path | None:
    """Resolve skills tree: FSA_SKILLS_ROOT, then env default paths."""
    raw = os.environ.get("FSA_SKILLS_ROOT", "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
        return p if p.is_dir() else None
    # Optional well-known local clone (dev machine)
    candidates = [
        Path.home()
        / "Documents/甲骨易实习/项目/长期项目/财务Skill运行平台/程序/finance-shared-skills",
        Path(__file__).resolve().parents[3] / "skills-workspace" / "finance-shared-skills",
    ]
    for c in candidates:
        if c.is_dir() and (c / "catalog.yaml").is_file():
            return c
    return None


def parse_catalog_yaml(text: str) -> list[dict[str, str]]:
    """Minimal parser for catalog.yaml shape used by finance-shared-skills.

    Expects:
      skills:
        - id: foo
          version: "0.1.0"
          summary: "..."
          path: skills/foo
    """
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_skills = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if re.match(r"^skills\s*:\s*$", line):
            in_skills = True
            continue
        if not in_skills:
            continue
        m_id = re.match(r"^\s*-\s*id\s*:\s*(.+)$", line)
        if m_id:
            if current and current.get("id"):
                items.append(current)
            current = {"id": m_id.group(1).strip().strip("\"'")}
            continue
        if current is None:
            continue
        m_kv = re.match(r"^\s+(version|summary|path|title)\s*:\s*(.+)$", line)
        if m_kv:
            key, val = m_kv.group(1), m_kv.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            current[key] = val
    if current and current.get("id"):
        items.append(current)
    return items


def load_catalog(root: Path) -> dict[str, Any]:
    catalog_path = root / "catalog.yaml"
    if not catalog_path.is_file():
        return {"ok": False, "error": "catalog_missing", "items": [], "root": str(root)}
    text = catalog_path.read_text(encoding="utf-8")
    items = parse_catalog_yaml(text)
    # enrich content_hash from path if present
    out_items: list[dict[str, str]] = []
    for it in items:
        rel = it.get("path") or f"skills/{it['id']}"
        skill_dir = root / rel
        h = ""
        if skill_dir.is_dir():
            h = _dir_fingerprint(skill_dir)
        out_items.append(
            {
                "skill_key": it["id"],
                "version": it.get("version") or "0.0.0",
                "summary": it.get("summary") or "",
                "title": it.get("title") or it["id"],
                "rel_path": rel,
                "content_hash": h,
            }
        )
    return {
        "ok": True,
        "error": None,
        "items": out_items,
        "root": str(root),
        "count": len(out_items),
    }


def _dir_fingerprint(path: Path) -> str:
    """Stable short hash of file relative paths + sizes (not full content)."""
    h = hashlib.sha256()
    files = sorted(p for p in path.rglob("*") if p.is_file())
    for f in files[:200]:
        rel = f.relative_to(path).as_posix()
        try:
            st = f.stat()
            h.update(rel.encode())
            h.update(str(st.st_size).encode())
        except OSError:
            continue
    return h.hexdigest()[:16]


def git_tip(root: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return out.strip() or None
    except Exception:
        return None


def git_pull(root: Path) -> dict[str, Any]:
    """Optional pull — never push. Returns {ok, tip, error}."""
    try:
        subprocess.check_call(
            ["git", "-C", str(root), "pull", "--ff-only"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return {"ok": True, "tip": git_tip(root), "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "tip": git_tip(root), "error": type(exc).__name__}
