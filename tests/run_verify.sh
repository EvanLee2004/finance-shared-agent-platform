#!/usr/bin/env bash
# 代码门禁。判绿：sh tests/run_verify.sh; echo EXIT:$?
# 禁止用 | head / | tail 作为判绿依据。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail=0
echo "== run_verify =="

# --- secrets ---
if git ls-files 2>/dev/null | grep -E '(^|/)\.env$|opencode\.json$|config\.local' ; then
  echo "FAIL: secret-like tracked files"
  fail=1
else
  echo "OK secrets"
fi

# --- python ---
PY=python3
if [[ -x backend/.venv/bin/python ]]; then
  PY=backend/.venv/bin/python
elif [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
fi

if [[ -d backend/app ]]; then
  if ! "$PY" -m compileall -q backend/app; then
    echo "FAIL compileall"
    fail=1
  else
    echo "OK compileall"
  fi
fi

if command -v ruff >/dev/null 2>&1 && [[ -f pyproject.toml ]]; then
  if ! ruff check backend; then
    echo "FAIL ruff"
    fail=1
  else
    echo "OK ruff"
  fi
else
  echo "SKIP ruff"
fi

# --- pytest (required for Phase0) ---
export PYTHONPATH="${ROOT}/backend${PYTHONPATH:+:$PYTHONPATH}"
if ! "$PY" -c "import pytest" 2>/dev/null; then
  echo "Installing pytest + backend deps into temp note: prefer venv"
  "$PY" -m pip install -q -r backend/requirements.txt pytest 2>/dev/null || true
fi

if ! "$PY" -m pytest -q tests; then
  echo "FAIL pytest"
  fail=1
else
  echo "OK pytest"
fi

# --- optional frontend build ---
if [[ -f frontend/package.json ]] && command -v npm >/dev/null 2>&1; then
  if [[ ! -d frontend/node_modules ]]; then
    (cd frontend && npm install --no-fund --no-audit) || fail=1
  fi
  if (cd frontend && npm run build); then
    echo "OK frontend build"
  else
    echo "FAIL frontend build"
    fail=1
  fi
else
  echo "SKIP frontend build"
fi

if [[ "$fail" -ne 0 ]]; then
  echo FAILED
  exit 1
fi
echo PASSED
exit 0
