# =============================================================================
# ARMOR-UPDATER - Keeping child processes from opening console windows: console_flags.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""On Windows the graphical updater runs under pythonw.exe, which has no console. Every console program it starts (git above all) then opens a console
window of its own, and a screen that refreshes many projects fills the desktop with them. Every child process of the updater passes NO_WINDOW."""
from __future__ import annotations

import os
import subprocess
import sys

NO_WINDOW: int = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def headless() -> bool:
    """True when this process has no console of its own (pythonw.exe, the silent launcher): children must never create one either."""
    return os.name == "nt" and (sys.stdout is None or os.path.basename(sys.executable).lower() == "pythonw.exe")
