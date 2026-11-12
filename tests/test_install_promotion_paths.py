# =============================================================================
# ARMOR-UPDATER - the paths of the promotion and of the rebuild of the environment that go wrong
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A checkout is put in place of the installed one with two renames, journalled. What a person must be able to rely on is what happens when a rename fails: the previous
installation is not lost, the verified candidate is kept for inspection, and the message says which of the two it is. Every case here makes one rename fail on purpose."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from armor_updater import install
from armor_updater.registry import ProjectEntry


def entry() -> ProjectEntry:
    return ProjectEntry("ARMOR-EXAMPLE", "python", "1.0.0")


def folders(tmp_path: Path) -> tuple[Path, Path, Path]:
    workspace = tmp_path / "workspace"
    path = workspace / "ARMOR-EXAMPLE"
    staging = workspace / ".staging" / "ARMOR-EXAMPLE"
    path.mkdir(parents=True)
    staging.mkdir(parents=True)
    (path / "old.txt").write_text("old", encoding="utf-8")
    (staging / "new.txt").write_text("new", encoding="utf-8")
    return workspace, path, staging


def failing_rename(monkeypatch, fail_when) -> list[tuple[Path, Path]]:
    """Path.rename that raises for the calls `fail_when(source, target)` picks and does the real thing for the others."""
    real = Path.rename
    calls: list[tuple[Path, Path]] = []

    def rename(self: Path, target):
        calls.append((self, Path(target)))
        if fail_when(self, Path(target)):
            raise OSError("in use")
        return real(self, target)

    monkeypatch.setattr(Path, "rename", rename)
    return calls


def test_a_promotion_puts_the_candidate_in_place_and_keeps_the_old_one_as_a_backup(tmp_path: Path):
    workspace, path, staging = folders(tmp_path)

    done = install._promote(entry(), workspace, path, staging, "abc", None)

    assert isinstance(done, tuple)
    backup = done[0]
    assert backup is not None and (backup / "old.txt").read_text(encoding="utf-8") == "old"
    assert (path / "new.txt").read_text(encoding="utf-8") == "new"
    assert not staging.exists()


def test_a_new_project_has_no_backup(tmp_path: Path):
    workspace, path, staging = folders(tmp_path)
    for child in path.iterdir():
        child.unlink()
    path.rmdir()

    done = install._promote(entry(), workspace, path, staging, "abc", None)

    assert done == (None,)
    assert (path / "new.txt").is_file()


def test_when_the_installed_checkout_cannot_be_moved_aside_it_is_left_as_it_was(tmp_path: Path, monkeypatch):
    workspace, path, staging = folders(tmp_path)
    failing_rename(monkeypatch, lambda source, target: source == path)

    done = install._promote(entry(), workspace, path, staging, "abc", None)

    assert isinstance(done, install.InstallResult) and not done.ok
    assert "could not move the installed checkout aside" in done.message
    assert "was left as it was" in done.message
    assert (path / "old.txt").read_text(encoding="utf-8") == "old", "the installation is exactly what it was"


def test_when_the_candidate_cannot_be_put_in_place_the_old_checkout_comes_back(tmp_path: Path, monkeypatch):
    workspace, path, staging = folders(tmp_path)
    failing_rename(monkeypatch, lambda source, target: source == staging)

    done = install._promote(entry(), workspace, path, staging, "abc", None)

    assert isinstance(done, install.InstallResult) and not done.ok
    assert "the previous installation is back" in done.message
    assert (path / "old.txt").read_text(encoding="utf-8") == "old"
    assert (staging / "new.txt").is_file(), "the verified candidate stays for inspection"


def test_when_even_the_restore_fails_the_message_says_where_the_previous_installation_is(tmp_path: Path, monkeypatch):
    workspace, path, staging = folders(tmp_path)
    failing_rename(monkeypatch, lambda source, target: source == staging or target == path)

    done = install._promote(entry(), workspace, path, staging, "abc", None)

    assert isinstance(done, install.InstallResult) and not done.ok
    assert "the restore also failed" in done.message
    backups = list(workspace.rglob("old.txt"))
    assert len(backups) == 1 and backups[0].parent != path, "the old installation is in the backup folder the message names"
    assert str(backups[0].parent) in done.message


def test_the_environment_is_not_made_again_when_the_project_has_no_build_script(tmp_path: Path):
    project = tmp_path / "ARMOR-EXAMPLE"
    project.mkdir()

    done = install._rebuild_environment(project, None)

    assert done.ok
    assert "run its own set-up once" in done.message


@pytest.mark.parametrize("code,ok", [(0, True), (3, False)])
def test_the_build_script_makes_the_environment_and_its_failure_is_reported(tmp_path: Path, monkeypatch, code: int, ok: bool):
    project = tmp_path / "ARMOR-EXAMPLE"
    project.mkdir()
    script = project / ("build.bat" if install.os.name == "nt" else "build.sh")
    script.write_text("exit 0\n", encoding="utf-8")
    seen = {}

    def fake_run(command, cwd=None, capture_output=False, **_kwargs):
        seen["command"], seen["cwd"], seen["capture"] = command, cwd, capture_output
        return subprocess.CompletedProcess(command, code, stdout="made" if code == 0 else "", stderr="")

    monkeypatch.setattr(install, "_run", fake_run)
    steps: list[tuple[str, str]] = []

    done = install._rebuild_environment(project, lambda stage, message, *rest: steps.append((stage, message)))

    assert done.ok is ok
    assert seen["cwd"] == project and seen["capture"] is True, "a window that shows progress also gets the output"
    assert str(script) in seen["command"]
    assert steps and steps[0][0] == "build"
    if not ok:
        assert "exited with code 3" in done.message


def test_without_a_progress_window_the_output_is_not_captured(tmp_path: Path, monkeypatch):
    project = tmp_path / "ARMOR-EXAMPLE"
    project.mkdir()
    (project / ("build.bat" if install.os.name == "nt" else "build.sh")).write_text("exit 0\n", encoding="utf-8")
    seen = {}

    def fake_run(command, cwd=None, capture_output=False, **_kwargs):
        seen["capture"] = capture_output
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(install, "_run", fake_run)

    assert install._rebuild_environment(project, None).ok
    assert seen["capture"] is False
