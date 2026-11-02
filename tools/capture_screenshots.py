#!/usr/bin/env python3
# =============================================================================
# tools/capture_screenshots.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Retakes the screenshots of the README: the real window of the updater, drawn off screen (no window opens on the desktop) over a made-up workspace.

    py -3 tools/capture_screenshots.py              # writes images/screenshots/<file> for every screen listed in docs/screenshots.json
    py -3 tools/capture_screenshots.py --out DIR    # writes them in DIR instead, to look at them first

The workspace is a throw-away folder with a few project manifests, the settings go to a throw-away home folder (nothing of the machine is read or written) and the
check of GitHub is skipped (the window is shown as it is when offline). It needs PySide6 (the optional desktop shell) and Pillow (to shrink a picture over 400 KB).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from typing import Any
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAX_BYTES = 400 * 1024
TARGET_BYTES = 380 * 1024
SIZE = (1920, 1080)
# the manifests that make the made-up workspace: public project names with their own manifest
PROJECTS = ["ARMOR-COMMON", "ARMOR-DOCS", "ARMOR-NETWORK", "ARMOR-NODE-RADAR", "ARMOR-NODE-SOLAR", "ARMOR-SERVER", "ARMOR-SIMULATOR", "ARMOR-STUDIO", "ARMOR-UPDATER", "ARMOR-VISION"]
SELECTED = "ARMOR-STUDIO"


def shrink(source: Path, target: Path) -> int:
    """Saves source as target; when it is too heavy, reduces its palette until it fits. Returns the final size."""
    from PIL import Image
    image = Image.open(source).convert("RGB")
    image.save(target, optimize=True)
    for colours in (256, 192, 128, 96, 64):
        if target.stat().st_size <= TARGET_BYTES:
            break
        image.quantize(colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(target, optimize=True)
    return target.stat().st_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=REPO / "images" / "screenshots")
    args = parser.parse_args(argv)
    screens = [item["file"] for item in json.loads((REPO / "docs" / "screenshots.json").read_text(encoding="utf-8"))["screens"]]
    args.out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="armor-updater-shots-"))
    try:
        home = work / "home"
        home.mkdir()
        os.environ.update({"QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software", "QT_QPA_FONTDIR": r"C:\Windows\Fonts", "USERPROFILE": str(home), "HOME": str(home)})
        sys.path.insert(0, str(REPO / "src"))
        workspace = work / "workspace"
        for name in PROJECTS:
            source = REPO.parent / name / "armor.project.json"
            if source.is_file():
                (workspace / name).mkdir(parents=True)
                shutil.copyfile(source, workspace / name / "armor.project.json")
        from PySide6.QtCore import Property, QTimer, QUrl, Slot
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow
        from armor_updater import qt_gui

        app = QGuiApplication(sys.argv)  # noqa: F841 - it has to stay alive while the window is drawn
        engine = QQmlApplicationEngine()

        class DemoBridge(qt_gui.UpdaterBridge):
            @Property(str, notify=qt_gui.UpdaterBridge.summaryChanged)
            def workspaceRoot(self) -> str:   # only what the window shows: not the folder of this machine
                return "~/armor"

            @Slot(bool)
            def refresh(self, offline: bool) -> None:   # never ask GitHub: the window is shown as it is offline
                super().refresh(True)

        qt_gui.i18n.resolve_initial_lang = lambda: "en"   # the language of the picture, not the one saved on this machine
        bridge = DemoBridge(workspace)
        engine.rootContext().setContextProperty("backend", bridge)
        engine.load(QUrl.fromLocalFile(str(REPO / "src" / "armor_updater" / "qml" / "Main.qml")))
        if not engine.rootObjects():
            print("the window did not load")
            return 1
        window: Any = engine.rootObjects()[0]
        window.setProperty("visibility", 2)   # windowed: the size below is the one of the picture
        window.resize(*SIZE)
        steps = {"projects.png": "", "project-selected.png": SELECTED}
        queue = [name for name in screens if name in steps]
        failed: list[str] = []

        def settle(milliseconds: int = 1200) -> None:
            from PySide6.QtCore import QEventLoop
            loop = QEventLoop()
            QTimer.singleShot(milliseconds, loop.quit)
            loop.exec()

        settle()
        for name in queue:
            bridge.selectProject(steps[name])
            settle()
            raw = work / name
            QQuickWindow.grabWindow(window).save(str(raw))
            size = shrink(raw, args.out / name)
            print(f"{name}: {size} bytes")
            if size > MAX_BYTES:
                failed.append(name)
        window.deleteLater()
        del engine
        return 1 if failed or set(screens) - set(queue) else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
