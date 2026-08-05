#!/usr/bin/env bash
# 财务共享中台 · 一键门禁（scaffold → 随 Phase 加严）
# 判绿：sh tests/run_verify.sh; echo EXIT:$?
# 禁止：... | tail / | head 当成功依据
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "== finance-shared-agent-platform run_verify =="
echo "ROOT=$ROOT"

fail=0

# 1) 关键开工文件存在
for f in AGENTS.md Agent.md docs/softeng/10_代码架构与整洁度_中台.md; do
  if [[ ! -f "$f" ]]; then
    echo "MISSING: $f"
    fail=1
  else
    echo "OK file: $f"
  fi
done

# 2) 禁止把密钥样例提交进跟踪文件（粗检）
if git ls-files 2>/dev/null | grep -E '\.env$|opencode\.json$|config\.local' ; then
  echo "FAIL: secret-like tracked files"
  fail=1
else
  echo "OK: no obvious secret files tracked"
fi

# 3) Python 语法（有 venv 则用之）
PY=python3
if [[ -x backend/.venv/bin/python ]]; then PY=backend/.venv/bin/python; fi
if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; fi
if [[ -f backend/app/main.py ]]; then
  "$PY" -m compileall -q backend/app && echo "OK compileall backend/app" || fail=1
fi

# 4) ruff（若已安装）
if command -v ruff >/dev/null 2>&1 && [[ -f pyproject.toml ]]; then
  ruff check backend || fail=1
  echo "OK ruff (or see errors above)"
else
  echo "SKIP ruff (not installed or no pyproject)"
fi

# 5) pytest（有测试再跑）
if [[ -d backend/tests ]] || [[ -d tests && -n "$(find tests -name 'test_*.py' 2>/dev/null | head -1)" ]]; then
  if "$PY" -c "import pytest" 2>/dev/null; then
    "$PY" -m pytest -q backend/tests tests --ignore=tests/run_verify.sh 2>/dev/null || \
    "$PY" -m pytest -q 2>/dev/null || fail=1
  else
    echo "SKIP pytest (not installed)"
  fi
else
  echo "SKIP pytest (no tests yet)"
fi

if [[ "$fail" -ne 0 ]]; then
  echo "run_verify FAILED"
  exit 1
fi
echo "run_verify PASSED"
exit 0
