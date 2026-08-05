#!/usr/bin/env bash
set -euo pipefail
VERSION="${1:?usage: $0 <version>}"
PREFIX="${OPENCODE_PREFIX:-/opt/opencode}"
mkdir -p "$PREFIX/versions"
echo "TODO: install opencode $VERSION into $PREFIX/versions/$VERSION and switch current symlink"
