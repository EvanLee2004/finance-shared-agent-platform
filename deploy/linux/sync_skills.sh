#!/usr/bin/env bash
set -euo pipefail
SKILLS_DIR="${SKILLS_DIR:-/opt/finance-shared/skills-repo}"
BRANCH="${SKILLS_BRANCH:-main}"
if [[ ! -d "$SKILLS_DIR/.git" ]]; then
  echo "clone first"
  exit 1
fi
cd "$SKILLS_DIR"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"
echo "skills at $(git rev-parse --short HEAD)"
