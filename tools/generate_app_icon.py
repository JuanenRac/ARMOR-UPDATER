# =============================================================================
# ARMOR-UPDATER - Generate the Windows application icon from the official
# A.R.M.O.R. SVG identity asset: generate_app_icon.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Render the public A.R.M.O.R. SVG into the icon consumed by Windows.

The source of truth is images/ARMOR_ICON.svg - the same emblem
tools/make_brand.py (in ARMOR-DOCS) generates for this repository's README,
so the desktop window and the README show the same icon. This small tool is
kept in the repository so a future branding change can regenerate the ICO
rather than hand-editing a binary asset.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "images" / "ARMOR_ICON.svg"
OUTPUT = ROOT / "images" / "ARMOR_ICON.ico"
ICON_SIZE = 256


def main() -> int:
    renderer = QSvgRenderer(str(SOURCE))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG icon source: {SOURCE}")

    image = QImage(ICON_SIZE, ICON_SIZE, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(OUTPUT), "ICO"):
        raise RuntimeError(f"Qt could not write ICO output: {OUTPUT}")
    print(f"APP_ICON=GENERATED source={SOURCE.name} output={OUTPUT.name} size={ICON_SIZE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
