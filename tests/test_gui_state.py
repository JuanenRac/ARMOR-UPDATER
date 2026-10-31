"""What the two desktop windows do with the results the worker threads hand them: the state they keep and the steps they mark. The Qt bridge is built without starting its refresh, so no
network and no thread is involved; the Qt part is skipped where PySide6 is not installed."""
import os
from pathlib import Path

import pytest

from armor_updater.install import InstallResult

ROOT = Path(__file__).resolve().parents[1]


def _qt_bridge():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QObject

    from armor_updater import qt_gui
    bridge = qt_gui.UpdaterBridge.__new__(qt_gui.UpdaterBridge)
    QObject.__init__(bridge)
    bridge._workspace_root = ROOT
    bridge._locals, bridge._remotes, bridge._activity = [], {}, []
    bridge._busy, bridge._status, bridge._notice, bridge._selected = False, "", "", ""
    bridge._deploy = "all"
    bridge._lang = "en"
    bridge._operation_steps = [{"id": "preflight", "state": "active", "detail": ""}, {"id": "complete", "state": "pending", "detail": ""}]
    bridge._operation_progress, bridge._active_phase, bridge._operation_visible = 0, "", False
    bridge._batch_current, bridge._batch_total, bridge._batch_project = 1, 1, ""
    return bridge


def test_qt_remote_result_keeps_projects_and_shows_the_first_two_errors():
    bridge = _qt_bridge()
    bridge._on_remote_result([], {"a": object()}, ("first", "second", "third"))
    assert bridge._locals == [] and list(bridge._remotes) == ["a"]
    assert bridge._busy is False and bridge._status == "first; second"


def test_qt_finish_operation_marks_the_steps():
    bridge = _qt_bridge()
    bridge._finish_operation(True, [InstallResult(True, "done")])
    assert bridge._active_phase == "complete" and bridge._operation_progress == 100
    assert [step["state"] for step in bridge._operation_steps] == ["done", "done"]
    bridge = _qt_bridge()
    bridge._finish_operation(False, [InstallResult(False, "the build failed")])
    assert bridge._operation_steps[0]["state"] == "failed" and bridge._active_phase == "preflight"
    assert "build failed" in bridge._operation_steps[0]["detail"]


def test_tk_window_keeps_its_filter_table_empty_before_the_first_refresh():
    tk = pytest.importorskip("tkinter")
    from armor_updater import gui
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display for Tk")
    root.withdraw()
    try:
        window = gui.UpdaterGUI(root, ROOT)
        assert window._filter_by_label is not None
        assert isinstance(window.locals_, list) and isinstance(window.remotes, dict)
    finally:
        root.destroy()
