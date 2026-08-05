#!/usr/bin/env bash
# 代码门禁（轻量）。判绿：sh tests/run_verify.sh; echo EXIT:$?
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail=0
echo "== run_verify =="

if git ls-files 2>/dev/null | grep -E '(^|/)\.env$|opencode\.json$|config\.local' ; then
  echo "FAIL: secret-like tracked files"; fail=1
else
  echo "OK secrets"
fi

PY=python3
[[ -x backend/.venv/bin/python ]] && PY=backend/.venv/bin/python
[[ -x .venv/bin/python ]] && PY=.venv/bin/python
if [[ -f backend/app/main.py ]]; then
  "$PY" -m compileall -q backend/app && echo "OK compileall" || fail=1
fi
if command -v ruff >/dev/null 2>&1 && [[ -f pyproject.toml ]]; then
  ruff check backend || fail=1
else
  echo "SKIP ruff"
fi
if [[ "$fail" -ne 0 ]]; then echo FAILED; exit 1; fi
echo PASSED
exit 0
