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

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -e ".[dev]"

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/../ARMOR-COMMON/scripts" && pwd)/armor-project.sh" build "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
