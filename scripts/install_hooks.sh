#!/usr/bin/env sh
# One-shot: install git pre-commit hook for vendor SHA256SUMS validation.
set -eu
ROOT="$(git rev-parse --show-toplevel)"
SRC="${ROOT}/scripts/githooks/pre-commit"
DST="${ROOT}/.git/hooks/pre-commit"
cp "${SRC}" "${DST}"
chmod +x "${DST}"
echo "Installed ${DST}"
