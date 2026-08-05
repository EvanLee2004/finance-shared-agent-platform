"""Pytest fixtures — isolated temp DATA_ROOT per test."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("FSA_DATA_ROOT", str(root))
    # Avoid accidental bootstrap unless tests set these
    monkeypatch.delenv("FSA_BOOTSTRAP_ADMIN_USER", raising=False)
    monkeypatch.delenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    # Force OC probe to a closed port so health tests see ok=false by default
    monkeypatch.setenv("FSA_OPENCODE_BASE_URL", "http://127.0.0.1:1")
    return root


@pytest.fixture()
def client(data_root: Path) -> Generator[TestClient, None, None]:
    # Import after env is set so lifespan uses FSA_DATA_ROOT
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_client(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-123")
    from app.main import app

    with TestClient(app) as c:
        yield c
