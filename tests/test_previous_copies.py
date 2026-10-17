# =============================================================================
# ARMOR-UPDATER - tests/test_previous_copies.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Restoring and cleaning the previous copies (what the window's buttons call), their size in `status`, and the window itself."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from armor_updater import i18n, main
from armor_updater.install import backup_summary, clean_previous_copies, restore_previous_copy
from armor_updater.promotion import WorkspaceLock, list_backups, new_backup_path
from armor_updater.result_text import localized_message


def make_project(workspace: Path, name: str = "ARMOR-EXAMPLE", marker: str = "current") -> Path:
    path = workspace / name
    path.mkdir(exist_ok=True)
    (path / "marker.txt").write_text(marker, encoding="utf-8")
    return path


def make_backup(workspace: Path, name: str, marker: str, size: int = 10) -> Path:
    backup = new_backup_path(workspace, name, marker)
    backup.mkdir(parents=True)
    (backup / "marker.txt").write_text(marker, encoding="utf-8")
    (backup / "padding.bin").write_bytes(b"x" * size)
    return backup


def test_the_summary_counts_the_copies_and_their_bytes(tmp_path: Path):
    assert backup_summary(tmp_path) == (0, 0)
    make_backup(tmp_path, "A", "one", 100)
    make_backup(tmp_path, "A", "two", 200)
    make_backup(tmp_path, "B", "three", 50)
    count, size = backup_summary(tmp_path, "A")
    assert count == 2 and size >= 300
    assert backup_summary(tmp_path)[0] == 3
    assert backup_summary(tmp_path, "C") == (0, 0)


def test_restore_puts_the_newest_copy_back_and_keeps_the_replaced_checkout_as_a_copy(tmp_path: Path):
    project = make_project(tmp_path, marker="installed now")
    make_backup(tmp_path, "ARMOR-EXAMPLE", "previous")
    result = restore_previous_copy(tmp_path, "ARMOR-EXAMPLE")
    assert result.ok and result.code == "restored", result.message
    assert (project / "marker.txt").read_text(encoding="utf-8") == "previous"
    kept = list_backups(tmp_path, "ARMOR-EXAMPLE")
    assert len(kept) == 1 and (kept[0] / "marker.txt").read_text(encoding="utf-8") == "installed now"
    # and it can be undone
    assert restore_previous_copy(tmp_path, "ARMOR-EXAMPLE").ok
    assert (project / "marker.txt").read_text(encoding="utf-8") == "installed now"


def test_restore_without_a_copy_says_so_and_touches_nothing(tmp_path: Path):
    project = make_project(tmp_path)
    result = restore_previous_copy(tmp_path, "ARMOR-EXAMPLE")
    assert not result.ok and result.code == "no_backup"
    assert (project / "marker.txt").read_text(encoding="utf-8") == "current"


def test_restore_and_clean_wait_for_the_other_updater(tmp_path: Path):
    make_project(tmp_path)
    make_backup(tmp_path, "ARMOR-EXAMPLE", "previous")
    with WorkspaceLock(tmp_path):
        assert restore_previous_copy(tmp_path, "ARMOR-EXAMPLE").code == "busy"
        assert clean_previous_copies(tmp_path, "ARMOR-EXAMPLE").code == "busy"
    assert len(list_backups(tmp_path, "ARMOR-EXAMPLE")) == 1


def test_clean_deletes_the_copies_and_says_how_much_disk_came_back(tmp_path: Path):
    make_backup(tmp_path, "ARMOR-EXAMPLE", "one", 1024 * 1024)
    make_backup(tmp_path, "ARMOR-EXAMPLE", "two", 1024 * 1024)
    result = clean_previous_copies(tmp_path, "ARMOR-EXAMPLE")
    assert result.ok and result.code == "cleaned" and result.params["count"] == "2"
    assert float(result.params["size"]) >= 2.0
    assert list_backups(tmp_path, "ARMOR-EXAMPLE") == []
    assert clean_previous_copies(tmp_path, "ARMOR-EXAMPLE", keep=1).params["count"] == "0"


def test_clean_can_keep_the_newest(tmp_path: Path):
    make_backup(tmp_path, "ARMOR-EXAMPLE", "one")
    make_backup(tmp_path, "ARMOR-EXAMPLE", "two")
    assert clean_previous_copies(tmp_path, "ARMOR-EXAMPLE", keep=1).params["count"] == "1"
    assert len(list_backups(tmp_path, "ARMOR-EXAMPLE")) == 1


def test_every_outcome_is_said_in_every_language(tmp_path: Path):
    make_project(tmp_path)
    make_backup(tmp_path, "ARMOR-EXAMPLE", "previous")
    outcomes = [
        restore_previous_copy(tmp_path, "ARMOR-EXAMPLE"),   # restored
        restore_previous_copy(tmp_path, "ARMOR-NOTHING"),   # no copy
        clean_previous_copies(tmp_path, "ARMOR-EXAMPLE"),   # cleaned
    ]
    for result in outcomes:
        texts = set()
        for code, _label in i18n.LANGUAGES:
            text = localized_message(code, result)
            assert result.params["project"] in text and "{" not in text
            texts.add(text)
        assert len(texts) == len(i18n.LANGUAGES)


def test_the_button_strings_exist_in_the_eight_languages():
    for key in ("restore_button", "clean_copies_button", "msg_confirm_restore", "msg_confirm_clean", "backups_summary", "signature_mode_warn", "signature_mode_require"):
        values = {code: i18n.t(code, key, name="X", count=1, size="1.0") for code, _ in i18n.LANGUAGES}
        assert all(value and value != key for value in values.values()), key
        assert len(set(values.values())) == len(i18n.LANGUAGES), key


def test_status_shows_the_copies_and_the_signature_policy(tmp_path: Path, capsys):
    make_backup(tmp_path, "ARMOR-EXAMPLE", "one", 1024)
    args = main.build_parser().parse_args(["status", "--offline", "--workspace", str(tmp_path)])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "Previous copies kept: 1" in out
    assert "Signature policy: warn" in out


def test_status_json_carries_the_copies_and_the_policy(tmp_path: Path, capsys):
    make_backup(tmp_path, "ARMOR-EXAMPLE", "one", 1024)
    args = main.build_parser().parse_args(["status", "--offline", "--json", "--workspace", str(tmp_path)])
    assert args.func(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["backups"]["count"] == 1 and payload["backups"]["bytes"] >= 1024
    assert payload["signature_policy"] == "warn"


# ---- the Qt window --------------------------------------------------------------------------------------------------------------------------------

def test_the_qt_bridge_offers_the_restore_only_when_there_is_a_copy(tmp_path: Path, monkeypatch):
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from armor_updater import github_client, qt_gui

    monkeypatch.setattr(qt_gui, "discover_remote_projects", lambda: github_client.RemoteDiscovery((), ()))
    manifest = {
        "schema_version": "1.0", "ecosystem": "A.R.M.O.R.", "name": "ARMOR-EXAMPLE", "version": "1.0.0", "role": "service", "stack": "python", "technologies": ["Python"],
        "deployment_target": "The central server", "maturity": "functional", "family": "Test", "parent": None, "native_version": "1.0.0", "build": "x", "notes": "n",
    }
    project = make_project(tmp_path)
    (project / "armor.project.json").write_text(json.dumps(manifest), encoding="utf-8")
    bridge = qt_gui.UpdaterBridge(tmp_path, None)
    bridge.selectProject("ARMOR-EXAMPLE")
    assert bridge.canRestore is False and bridge.backupsSummary == ""
    make_backup(tmp_path, "ARMOR-EXAMPLE", "previous")
    assert bridge.canRestore is True
    assert "1" in bridge.backupsSummary
    # what the confirmation dialog ends up calling: the restore, then the bridge saying the result in the language of the window
    bridge._lang = "en"
    bridge._busy = False   # the first scan of the workspace answers through the event loop, which this test does not run
    bridge._on_copies_result(restore_previous_copy(tmp_path, "ARMOR-EXAMPLE"))
    assert any("ARMOR-EXAMPLE" in line and "previous copy" in line for line in bridge.fullActivity)
    assert backup_summary(tmp_path, "ARMOR-EXAMPLE")[0] == 1   # the checkout that was replaced is the copy now
