#!/usr/bin/env bash
# ARMOR-UPDATER - build-test.sh
# Same .venv setup as build.sh, but non-mutating: no version bump.
# GPL-3.0-or-later.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install -e ".[dev]"

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")/../ARMOR-COMMON/scripts" && pwd)/armor-project.sh" build-test "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
