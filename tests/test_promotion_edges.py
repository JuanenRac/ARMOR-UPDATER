# =============================================================================
# ARMOR-UPDATER - Characterization of the edges of the lock, the journal and the rollback
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from armor_updater import promotion
from armor_updater.promotion import (
    Promotion,
    PromotionJournal,
    WorkspaceBusy,
    WorkspaceLock,
    list_backups,
    new_backup_path,
    recover_interrupted_promotion,
    rollback,
)


def test_a_process_id_that_is_not_positive_is_never_alive():
    assert promotion._process_is_alive(0) is False
    assert promotion._process_is_alive(-5) is False


def test_the_running_process_is_alive():
    assert promotion._process_is_alive(os.getpid()) is True


def test_a_lock_of_a_process_that_is_gone_is_taken_over(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(promotion, "_process_is_alive", lambda pid: False)
    first = WorkspaceLock(tmp_path)
    first.acquire()
    second = WorkspaceLock(tmp_path)
    second.acquire()   # the first holder "died": the lock is taken over
    assert json.loads(second.path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    second.release()
    assert not second.path.exists()


def test_a_lock_older_than_the_limit_is_taken_over(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(promotion, "_process_is_alive", lambda pid: True)
    clock = {"now": 1000.0}
    first = WorkspaceLock(tmp_path, stale_after=60, now=lambda: clock["now"])
    first.acquire()
    clock["now"] = 1030.0
    with pytest.raises(WorkspaceBusy):
        WorkspaceLock(tmp_path, stale_after=60, now=lambda: clock["now"]).acquire()
    clock["now"] = 1100.0
    WorkspaceLock(tmp_path, stale_after=60, now=lambda: clock["now"]).acquire()


def test_a_damaged_lock_file_is_replaced(tmp_path: Path):
    lock = WorkspaceLock(tmp_path)
    lock.path.parent.mkdir(parents=True, exist_ok=True)
    lock.path.write_text("not json", encoding="utf-8")
    lock.acquire()
    assert json.loads(lock.path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    lock.release()


def test_releasing_a_lock_that_was_never_taken_changes_nothing(tmp_path: Path):
    lock = WorkspaceLock(tmp_path)
    lock.release()
    assert not lock.path.exists()


def test_completing_a_journal_that_does_not_exist_is_quiet(tmp_path: Path):
    PromotionJournal(tmp_path).complete()


def test_advancing_without_a_record_writes_nothing(tmp_path: Path):
    journal = PromotionJournal(tmp_path)
    journal.advance("promoted")
    assert not journal.path.exists()
    assert journal.read() is None


def test_a_record_without_a_phase_reads_as_begun(tmp_path: Path):
    journal = PromotionJournal(tmp_path)
    journal.path.parent.mkdir(parents=True, exist_ok=True)
    journal.path.write_text(json.dumps({"project": "P", "path": "a", "staging": "b", "backup": "c"}), encoding="utf-8")
    assert journal.read() == Promotion("P", "a", "b", "c", "begun")


def test_a_backed_up_promotion_with_neither_folder_nor_backup_says_so(tmp_path: Path):
    staging = tmp_path / "staging"
    staging.mkdir()
    journal = PromotionJournal(tmp_path)
    journal.begin(Promotion("P", str(tmp_path / "P"), str(staging), str(tmp_path / "gone"), "backed_up"))
    actions = recover_interrupted_promotion(tmp_path)
    assert len(actions) == 1 and "no backup" in actions[0]
    assert not staging.exists()
    assert journal.read() is None


def test_a_backed_up_promotion_that_cannot_be_undone_keeps_the_record(tmp_path: Path, monkeypatch):
    backup = tmp_path / "backup"
    backup.mkdir()
    journal = PromotionJournal(tmp_path)
    journal.begin(Promotion("P", str(tmp_path / "P"), str(tmp_path / "staging"), str(backup), "backed_up"))

    def refuse(self, target):  # noqa: ANN001
        raise OSError("locked")

    monkeypatch.setattr(Path, "rename", refuse)
    actions = recover_interrupted_promotion(tmp_path)
    assert len(actions) == 1 and "could not be undone" in actions[0]
    assert journal.read() is not None   # the next run tries again


def test_rolling_back_with_no_backup_raises(tmp_path: Path):
    with pytest.raises(RuntimeError):
        rollback(tmp_path, "P")


def test_rolling_back_without_a_current_checkout_just_restores(tmp_path: Path):
    backup = new_backup_path(tmp_path, "P", "update")
    backup.mkdir(parents=True)
    (backup / "marker.txt").write_text("old", encoding="utf-8")
    message = rollback(tmp_path, "P")
    assert (tmp_path / "P" / "marker.txt").read_text(encoding="utf-8") == "old"
    assert backup.name in message
    assert list_backups(tmp_path, "P") == []


def test_a_failed_rollback_puts_the_current_checkout_back(tmp_path: Path, monkeypatch):
    backup = new_backup_path(tmp_path, "P", "update")
    backup.mkdir(parents=True)
    current = tmp_path / "P"
    current.mkdir()
    (current / "marker.txt").write_text("current", encoding="utf-8")
    real_rename = Path.rename

    def selective(self, target):  # noqa: ANN001
        if self == backup:
            raise OSError("cannot move the backup")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", selective)
    with pytest.raises(OSError):
        rollback(tmp_path, "P")
    assert (current / "marker.txt").read_text(encoding="utf-8") == "current"
