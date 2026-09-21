#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_ROOT="${1:-${CODEX_HOME:-$HOME/.codex}/skills/dynamic-comic-video}"

command -v python3 >/dev/null || { echo "Python 3.10+ is required." >&2; exit 1; }
command -v npm >/dev/null || { echo "Node.js/npm is required for MP4 rendering." >&2; exit 1; }

mkdir -p "$INSTALL_ROOT"
if [ "$(cd "$REPO_ROOT" && pwd)" != "$(cd "$INSTALL_ROOT" && pwd)" ]; then
  find "$REPO_ROOT" -mindepth 1 -maxdepth 1 \
    ! -name .git ! -name .venv ! -name node_modules ! -name projects \
    ! -name renderer ! -name manga-renderer -exec cp -R {} "$INSTALL_ROOT" \;
fi
python3 -m venv "$INSTALL_ROOT/.venv"
"$INSTALL_ROOT/.venv/bin/python" -m pip install -r "$REPO_ROOT/requirements.txt"
(cd "$INSTALL_ROOT/assets/remotion" && npm ci)

echo "Ready. Skill: $INSTALL_ROOT"
echo "Python: $INSTALL_ROOT/.venv/bin/python"
echo "Renderer: $INSTALL_ROOT/assets/remotion"
echo "Keep project stories, images, audio and MP4 files outside this shared skill folder."
