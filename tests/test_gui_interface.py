"""The two desktop windows driven the way a person does: switching the language through all eight, the buttons that depend on the selection, and a project list that is
drawn from real results. Qt runs offscreen and Tk is skipped where there is no display; nothing reaches the network and the saved language is never written."""
import os
from pathlib import Path

import pytest

from armor_updater import i18n

ROOT = Path(__file__).resolve().parents[1]
CODES = [code for code, _label in i18n.LANGUAGES]


def test_the_window_languages_are_the_eight_of_the_ecosystem():
    assert set(CODES) == {"en", "es", "de", "fr", "it", "ja", "zh", "pt"}


def _bridge(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QObject

    from armor_updater import qt_gui
    monkeypatch.setattr(i18n, "save_lang_preference", lambda _lang: None)
    bridge = qt_gui.UpdaterBridge.__new__(qt_gui.UpdaterBridge)
    QObject.__init__(bridge)
    bridge._workspace_root = ROOT
    bridge._locals, bridge._remotes, bridge._activity = [], {}, []
    bridge._busy, bridge._status, bridge._notice, bridge._selected = False, "", "", ""
    bridge._deploy = "all"
    bridge._lang = "en"
    bridge._operation_steps, bridge._operation_progress, bridge._active_phase, bridge._operation_visible = [], 0, "", False
    bridge._batch_current, bridge._batch_total, bridge._batch_project = 1, 1, ""
    return bridge


def test_qt_every_language_can_be_chosen_and_changes_the_texts(monkeypatch):
    bridge = _bridge(monkeypatch)
    seen = {}
    for code in CODES:
        bridge.setLanguage(code)
        assert bridge.language == code
        seen[code] = bridge.text("ui_subtitle")
        assert seen[code] and seen[code] != "ui_subtitle", f"{code} has no text for the subtitle"
    assert len(set(seen.values())) >= 6, "the languages are not all showing the same words"


def test_qt_an_unknown_language_is_ignored(monkeypatch):
    bridge = _bridge(monkeypatch)
    bridge.setLanguage("xx")
    assert bridge.language == "en"


def test_qt_nothing_can_be_installed_or_updated_without_a_selection(monkeypatch):
    bridge = _bridge(monkeypatch)
    assert (bridge.canInstall, bridge.canUpdate, bridge.canRestore) == (False, False, False)
    assert bridge.projects == [] and bridge.discoveredCount == 0


def test_qt_a_deploy_filter_outside_the_known_ones_is_refused(monkeypatch):
    bridge = _bridge(monkeypatch)
    bridge.setDeploy("nonsense")
    assert bridge._deploy == "all"


def test_tk_every_language_relabels_the_window_in_place():
    tk = pytest.importorskip("tkinter")
    from armor_updater import gui
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display for Tk")
    root.withdraw()
    try:
        window = gui.UpdaterGUI(root, ROOT)
        subtitles = {}
        for code in CODES:
            window._apply_language(code, rerender=False)
            assert window.lang == code
            subtitles[code] = window.subtitle_lbl.cget("text")
            assert subtitles[code] == window.t("ui_subtitle")
        assert len(set(subtitles.values())) >= 6
    finally:
        root.destroy()
