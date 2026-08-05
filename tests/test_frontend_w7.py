"""W7 structural checks on shipped frontend (tokens, no alert, EP stack)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "frontend"


def test_element_plus_in_package_json() -> None:
    pkg = (FE / "package.json").read_text(encoding="utf-8")
    assert "element-plus" in pkg
    assert "@element-plus/icons-vue" in pkg


def test_design_tokens_light_and_neon() -> None:
    css = (FE / "src" / "styles.css").read_text(encoding="utf-8")
    assert "[data-theme=\"light\"]" in css or ":root" in css
    assert "[data-theme=\"neon\"]" in css
    assert "--space-4" in css
    assert "--font-md" in css
    assert "--accent" in css
    assert "prefers-reduced-motion" in css


def test_no_alert_or_confirm_in_src() -> None:
    hits = []
    for path in (FE / "src").rglob("*"):
        if path.suffix not in {".vue", ".js", ".ts"}:
            continue
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            if "alert(" in line or "confirm(" in line:
                hits.append(f"{path.relative_to(ROOT)}:{i}:{line.strip()}")
    assert hits == [], "alert/confirm forbidden on main UI:\n" + "\n".join(hits)


def test_shell_and_state_components_exist() -> None:
    assert (FE / "src" / "components" / "StateBlock.vue").is_file()
    app = (FE / "src" / "App.vue").read_text(encoding="utf-8")
    assert "nav-link" in app or "RouterLink" in app
    assert "工作台" in app or "home" in app
    assert "visibleNav" in app or "adminOnly" in app
    assert "登出" in app
    for name in ("LoginView.vue", "HomeView.vue", "ChatView.vue", "SkillsView.vue"):
        assert (FE / "src" / "views" / name).is_file()


def test_human_chinese_error_paths_in_views() -> None:
    chat = (FE / "src" / "views" / "ChatView.vue").read_text(encoding="utf-8")
    assert "OpenCode 未就绪" in chat or "oc_unavailable" in chat
    skills = (FE / "src" / "views" / "SkillsView.vue").read_text(encoding="utf-8")
    assert "授权" in skills
    login = (FE / "src" / "views" / "LoginView.vue").read_text(encoding="utf-8")
    assert "登录" in login


def test_chat_list_loading_before_empty_and_retry() -> None:
    """Shipped ChatView: listLoading gates empty; errors offer 重试."""
    chat = (FE / "src" / "views" / "ChatView.vue").read_text(encoding="utf-8")
    assert "listLoading" in chat
    assert 'kind="loading"' in chat
    assert "reloadChats" in chat
    # empty only after loading finished
    assert "v-if=\"listLoading\"" in chat or "v-if='listLoading'" in chat
    assert "重试" in chat
    assert "重试发送" in chat
