# =============================================================================
# ARMOR-UPDATER - The lock, the journal, the backups and the rollback
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from armor_updater import install, promotion
from armor_updater.detect import discover_workspace
from armor_updater.install import install_order, install_or_update
from armor_updater.promotion import (
    Promotion,
    PromotionJournal,
    WorkspaceBusy,
    WorkspaceLock,
    list_backups,
    new_backup_path,
    prune_backups,
    recover_interrupted_promotion,
    rollback,
)
from armor_updater.registry import ProjectEntry


def entry(name: str = "ARMOR-EXAMPLE", parent: str | None = None) -> ProjectEntry:
    return ProjectEntry(name, "python", "1.0.0", parent=parent)


# ---- the lock ----------------------------------------------------------------------------------------------------------------------

def test_a_second_updater_is_refused_while_the_first_works(tmp_path: Path):
    with WorkspaceLock(tmp_path):
        with pytest.raises(WorkspaceBusy):
            WorkspaceLock(tmp_path).acquire()
    WorkspaceLock(tmp_path).acquire()   # released with the first: free again


def test_a_lock_of_a_process_that_is_gone_or_too_old_is_taken_over(tmp_path: Path):
    lock = promotion.state_directory(tmp_path) / promotion.LOCK_FILE
    lock.parent.mkdir(parents=True)
    lock.write_text(json.dumps({"pid": 2**30, "at": time.time()}), encoding="utf-8")   # no such process
    with WorkspaceLock(tmp_path):
        pass
    lock.write_text(json.dumps({"pid": os.getpid(), "at": time.time() - 10 * 3600}), encoding="utf-8")   # alive but far too old
    with WorkspaceLock(tmp_path):
        pass
    lock.write_text("not json", encoding="utf-8")
    with WorkspaceLock(tmp_path):
        pass


def test_install_or_update_says_so_when_another_updater_is_working(tmp_path: Path):
    with WorkspaceLock(tmp_path):
        (result,) = install_or_update(entry(), tmp_path)
    assert not result.ok and "another updater" in result.message


# ---- the journal ---------------------------------------------------------------------------------------------------------------

def test_a_crash_between_the_two_renames_is_healed(tmp_path: Path):
    path = tmp_path / "ARMOR-EXAMPLE"
    staging = tmp_path / ".ARMOR-EXAMPLE.update-x"
    backup = promotion.backups_directory(tmp_path, "ARMOR-EXAMPLE") / "20260101-000000-abc"
    backup.mkdir(parents=True)
    (backup / "marker.txt").write_text("the previous install", encoding="utf-8")
    staging.mkdir()
    journal = PromotionJournal(tmp_path)
    journal.begin(Promotion("ARMOR-EXAMPLE", str(path), str(staging), str(backup)))
    journal.advance("backed_up")   # the first rename happened, the second never did: the project has no folder

    actions = recover_interrupted_promotion(tmp_path)

    assert (path / "marker.txt").read_text(encoding="utf-8") == "the previous install"
    assert not staging.exists() and journal.read() is None
    assert actions and "undone" in actions[0]


def test_a_promotion_that_did_finish_is_only_closed(tmp_path: Path):
    path = tmp_path / "ARMOR-EXAMPLE"
    path.mkdir()
    backup = promotion.backups_directory(tmp_path, "ARMOR-EXAMPLE") / "20260101-000000-abc"
    backup.mkdir(parents=True)
    journal = PromotionJournal(tmp_path)
    journal.begin(Promotion("ARMOR-EXAMPLE", str(path), str(tmp_path / ".gone"), str(backup)))
    journal.advance("backed_up")
    assert recover_interrupted_promotion(tmp_path) == []   # the new folder is there: nothing to undo
    assert path.is_dir() and backup.is_dir() and journal.read() is None


def test_a_damaged_journal_is_removed_not_trusted(tmp_path: Path):
    journal = PromotionJournal(tmp_path)
    journal.path.parent.mkdir(parents=True)
    journal.path.write_text("{ not a record", encoding="utf-8")
    assert recover_interrupted_promotion(tmp_path) == ["a damaged promotion record was removed"]
    assert not journal.path.exists()
    assert recover_interrupted_promotion(tmp_path) == []


# ---- the backups -----------------------------------------------------------------------------------------------------------------

def _backup(root: Path, name: str, stamp: str, text: str) -> Path:
    folder = promotion.backups_directory(root, name) / stamp
    folder.mkdir(parents=True)
    (folder / "marker.txt").write_text(text, encoding="utf-8")
    return folder


def test_only_the_newest_backups_are_kept(tmp_path: Path):
    for number in range(1, 6):
        _backup(tmp_path, "ARMOR-EXAMPLE", f"2026010{number}-000000-abc", str(number))
    removed = prune_backups(tmp_path, "ARMOR-EXAMPLE", 2)
    assert [b.name for b in list_backups(tmp_path, "ARMOR-EXAMPLE")] == ["20260105-000000-abc", "20260104-000000-abc"]
    assert len(removed) == 3


def test_two_backups_in_the_same_second_get_different_names(tmp_path: Path):
    first = new_backup_path(tmp_path, "ARMOR-EXAMPLE", "abcdef123456")
    first.mkdir(parents=True)
    second = new_backup_path(tmp_path, "ARMOR-EXAMPLE", "abcdef123456")
    assert first != second


def test_rollback_puts_the_newest_backup_back_and_can_be_undone(tmp_path: Path):
    path = tmp_path / "ARMOR-EXAMPLE"
    path.mkdir()
    (path / "marker.txt").write_text("current", encoding="utf-8")
    _backup(tmp_path, "ARMOR-EXAMPLE", "20260101-000000-abc", "older")
    _backup(tmp_path, "ARMOR-EXAMPLE", "20260102-000000-abc", "previous")

    assert "back in" in rollback(tmp_path, "ARMOR-EXAMPLE")
    assert (path / "marker.txt").read_text(encoding="utf-8") == "previous"
    rollback(tmp_path, "ARMOR-EXAMPLE")   # the checkout that was replaced is itself the newest backup
    assert (path / "marker.txt").read_text(encoding="utf-8") == "current"


def test_rollback_without_a_backup_says_so(tmp_path: Path):
    with pytest.raises(RuntimeError, match="no backup"):
        rollback(tmp_path, "ARMOR-EXAMPLE")


def test_the_state_folder_and_the_staging_folders_are_not_projects(tmp_path: Path):
    for name in (".armor-updater", ".ARMOR-EXAMPLE.update-abc", "ARMOR-EXAMPLE.backup-1a2b3c4d"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "armor.project.json").write_text("{}", encoding="utf-8")
    found = discover_workspace(tmp_path)
    assert found.projects == () and found.errors == (), found.errors


# ---- the order of a batch --------------------------------------------------------------------------------------------------------

def test_armor_common_comes_first_then_parents_before_children():
    names = [e.name for e in install_order([entry("ARMOR-NODE-ALARM"), entry("ARMOR-CHILD", parent="ARMOR-ZETA"), entry("ARMOR-ZETA"), entry("ARMOR-COMMON")])]
    assert names[0] == "ARMOR-COMMON"
    assert names.index("ARMOR-ZETA") < names.index("ARMOR-CHILD")
    assert sorted(names) == sorted(["ARMOR-NODE-ALARM", "ARMOR-CHILD", "ARMOR-ZETA", "ARMOR-COMMON"])


def test_a_loop_of_parents_does_not_hang():
    names = [e.name for e in install_order([entry("A", parent="B"), entry("B", parent="A")])]
    assert sorted(names) == ["A", "B"]


# ---- install_or_update never raises, and does not build without ARMOR-COMMON ----------------------------------------------------

def test_install_or_update_turns_an_exception_into_a_failed_result_and_evidence(tmp_path: Path, monkeypatch):
    (tmp_path / "ARMOR-COMMON").mkdir()

    def boom(*_args, **_kwargs):
        raise PermissionError("[WinError 5] the folder is in use")

    monkeypatch.setattr(install, "clone_or_pull", boom)
    (result,) = install_or_update(entry(), tmp_path)
    assert not result.ok and "PermissionError" in result.message
    lines = (tmp_path / ".armor-updater" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[-1])["ok"] is False
    assert not (tmp_path / ".armor-updater" / "lock").exists(), "the lock is released whatever happens"


def test_a_project_is_not_built_without_armor_common_next_to_it(tmp_path: Path):
    (result,) = install_or_update(entry(), tmp_path)
    assert not result.ok and "ARMOR-COMMON is not installed" in result.message
    assert not (tmp_path / "ARMOR-EXAMPLE").exists()


# ---- an update to the commit that is installed does nothing; a virtual environment is made again where it lives ----------------

def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _manifest(path: Path, version: str) -> None:
    (path / "armor.project.json").write_text(json.dumps({
        "schema_version": "1.0", "ecosystem": "A.R.M.O.R.", "name": "ARMOR-EXAMPLE", "version": version, "role": "service", "stack": "python", "technologies": ["Python"],
        "deployment_target": "The central server", "maturity": "functional", "family": "Test", "parent": None, "native_version": version, "build": "x", "notes": "Test manifest.",
    }), encoding="utf-8")


def _remote_with_project(tmp_path: Path, build_test: str, build: str | None = None) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    _git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    _git("clone", str(remote), str(seed), cwd=tmp_path)
    _git("config", "user.email", "t@example.invalid", cwd=seed)
    _git("config", "user.name", "T", cwd=seed)
    _manifest(seed, "1.0.0")
    name = "build-test.bat" if os.name == "nt" else "build-test.sh"
    (seed / name).write_text(build_test, encoding="utf-8")
    if build is not None:
        (seed / ("build.bat" if os.name == "nt" else "build.sh")).write_text(build, encoding="utf-8")
    _git("add", "-A", cwd=seed)
    _git("commit", "-m", "v1", cwd=seed)
    _git("push", "origin", "HEAD", cwd=seed)
    return remote, seed


def _script(body_posix: str, body_windows: str) -> str:
    return body_windows if os.name == "nt" else body_posix


def test_an_update_to_the_installed_commit_changes_nothing(tmp_path: Path, monkeypatch):
    remote, _seed = _remote_with_project(tmp_path, _script("exit 0\n", "@echo off\r\nexit /b 0\r\n"))
    monkeypatch.setattr(install, "github_repo_url", lambda _e: str(remote))
    local = tmp_path / "ARMOR-EXAMPLE"
    _git("clone", str(remote), str(local), cwd=tmp_path)
    result = install.clone_or_pull(entry(), tmp_path)
    assert result.ok and "already up to date" in result.message
    assert list_backups(tmp_path, "ARMOR-EXAMPLE") == [], "no backup is made for nothing"


def test_a_new_project_is_built_before_it_takes_its_place_and_a_failed_build_installs_nothing(tmp_path: Path, monkeypatch):
    remote, _seed = _remote_with_project(tmp_path, _script("exit 3\n", "@echo off\r\nexit /b 3\r\n"))
    monkeypatch.setattr(install, "github_repo_url", lambda _e: str(remote))
    result = install.clone_or_pull(entry(), tmp_path)
    assert not result.ok and "was not installed" in result.message
    assert not (tmp_path / "ARMOR-EXAMPLE").exists(), "a project whose build fails is not left half installed"
    assert not list(tmp_path.glob(".ARMOR-EXAMPLE.*")), "and leaves no staging folder"


def test_a_new_project_with_a_good_build_is_installed(tmp_path: Path, monkeypatch):
    remote, _seed = _remote_with_project(tmp_path, _script("echo built > built.txt\n", "@echo off\r\necho built> built.txt\r\n"))
    monkeypatch.setattr(install, "github_repo_url", lambda _e: str(remote))
    result = install.clone_or_pull(entry(), tmp_path)
    assert result.ok and "after a verified build" in result.message, result.message
    assert (tmp_path / "ARMOR-EXAMPLE" / "built.txt").exists()


def test_the_virtual_environment_of_the_staging_clone_is_removed_and_made_again_in_the_final_place(tmp_path: Path, monkeypatch):
    posix_test = "mkdir -p .venv/bin\necho staged > .venv/bin/where.txt\n"
    windows_test = "@echo off\r\nmkdir .venv\\bin\r\necho staged> .venv\\bin\\where.txt\r\n"
    posix_build = 'mkdir -p .venv/bin\npwd > .venv/bin/where.txt\n'
    windows_build = "@echo off\r\nmkdir .venv\\bin 2>nul\r\ncd > .venv\\bin\\where.txt\r\n"
    remote, _seed = _remote_with_project(tmp_path, _script(posix_test, windows_test), _script(posix_build, windows_build))
    monkeypatch.setattr(install, "github_repo_url", lambda _e: str(remote))
    result = install.clone_or_pull(entry(), tmp_path)
    assert result.ok, result.message
    assert "made the environment again" in result.message
    marker = tmp_path / "ARMOR-EXAMPLE" / ".venv" / "bin" / "where.txt"
    assert marker.exists(), "the environment exists in the final place"
    assert "update" not in marker.read_text(encoding="utf-8") and ".clone-" not in marker.read_text(encoding="utf-8"), "and was made there, not carried from the staging folder"


def test_the_nested_build_folders_are_not_carried_over(tmp_path: Path, monkeypatch):
    remote, seed = _remote_with_project(tmp_path, _script("exit 0\n", "@echo off\r\nexit /b 0\r\n"))
    (seed / ".gitignore").write_text("app/build/\n.gradle/\ndata/\n", encoding="utf-8")
    _git("add", "-A", cwd=seed)
    _git("commit", "-m", "ignore", cwd=seed)
    _git("push", "origin", "HEAD", cwd=seed)
    monkeypatch.setattr(install, "github_repo_url", lambda _e: str(remote))
    local = tmp_path / "ARMOR-EXAMPLE"
    _git("clone", str(remote), str(local), cwd=tmp_path)
    (local / "app" / "build").mkdir(parents=True)
    (local / "app" / "build" / "old.class").write_text("stale", encoding="utf-8")
    (local / ".gradle").mkdir()
    (local / ".gradle" / "cache").write_text("big", encoding="utf-8")
    (local / "data").mkdir()
    (local / "data" / "users.json").write_text("kept", encoding="utf-8")
    _manifest(seed, "1.1.0")
    _git("add", "-A", cwd=seed)
    _git("commit", "-m", "v2", cwd=seed)
    _git("push", "origin", "HEAD", cwd=seed)

    result = install.clone_or_pull(entry(), tmp_path)

    assert result.ok, result.message
    assert (local / "data" / "users.json").read_text(encoding="utf-8") == "kept"
    assert not (local / "app" / "build").exists() and not (local / ".gradle").exists()
