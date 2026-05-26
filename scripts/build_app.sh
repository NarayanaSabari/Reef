#!/usr/bin/env bash
# Build dist/Reef.app via py2app.
#
# KNOWN ISSUE (2026-05-26): this CURRENTLY FAILS with
#     error: install_requires is no longer supported
# because py2app explicitly rejects projects that declare install_requires
# (which pyproject.toml's [project] dependencies become). See setup.py header
# for the path forward (likely: switch to `briefcase` for bundling).
#
# Meanwhile, the menubar app runs perfectly via:
#     uv run reef-app
# which gives you the real macOS menubar experience without the .app bundle.

set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"

uv sync --group dev
rm -rf build dist

ALIAS_FLAG=""
if [ "${1-}" = "--alias" ]; then ALIAS_FLAG="-A"; fi

uv run python setup.py py2app $ALIAS_FLAG

echo
echo "Built: dist/Reef.app"
echo "Run:   open dist/Reef.app"
echo "Note:  Coral CLI must be installed separately (brew install withcoral/tap/coral)."
