#!/usr/bin/env bash
# ARMOR-UPDATER - build.sh
# Creates/uses its own project-local .venv first, unlike every other
# A.R.M.O.R. repository's build.sh. Installs the core + dev extras only,
# never the optional "gui" extra (PySide6) here - the CLI and the
# safety-critical update core stay stdlib-only, on purpose, so a headless
# deployment target never needs a Qt runtime just to run this. Use
# `pip install -e ".[gui]"` by hand for the desktop shell on a machine
# that actually has a display. GPL-3.0-or-later.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# The venv is put first on the PATH instead of being activated: the python first on the PATH may be a stripped one (for example the one of ESP-IDF) whose venv has no activate script.
if [ ! -x .venv/bin/python ] && [ ! -x .venv/Scripts/python.exe ]; then
    (python3 -m venv .venv 2>/dev/null || python -m venv .venv)
fi
if [ -x .venv/bin/python ]; then VENV_BIN="$PWD/.venv/bin"; else VENV_BIN="$PWD/.venv/Scripts"; fi
if [ ! -x "$VENV_BIN/python" ] && [ ! -x "$VENV_BIN/python.exe" ]; then echo "ERROR: the venv has no python; delete the .venv folder and run this again." >&2; exit 1; fi
export VIRTUAL_ENV="$PWD/.venv"
export PATH="$VENV_BIN:$PATH"

python -m pip install -e ".[dev]"

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/../ARMOR-COMMON/scripts" && pwd)/armor-project.sh" build "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
