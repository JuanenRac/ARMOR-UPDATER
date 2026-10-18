# =============================================================================
# ARMOR-UPDATER - tests/test_main_commands.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The command line beyond `status --json`: the offline table, install and update guards (GitHub is never asked: discovery is replaced), rollback, the list of backups and what the
entry point does with its arguments."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from armor_updater import main as main_module
from armor_updater.detect import LocalDiscovery, LocalStatus
from armor_updater.github_client import MissingTokenError, RemoteDiscovery, RemoteStatus
from armor_updater.install import InstallResult
from armor_updater.main import build_parser
from armor_updater.promotion import new_backup_path
from armor_updater.registry import ProjectEntry
from armor_updater.version_parse import Version


@pytest.fixture(autouse=True)
def never_the_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("GitHub was asked in a test")
    monkeypatch.setattr(main_module, "discover_remote_projects", refuse)
    monkeypatch.setattr(main_module, "fetch_all", refuse, raising=False)


def entry(name="ARMOR-ONE", **changes) -> ProjectEntry:
    return ProjectEntry(name=name, stack="python", native_version="0.1.0", maturity="functional", role="library", **changes)


def local(tmp_path: Path, name="ARMOR-ONE", installed=True, version=Version(0, 1, 0)) -> LocalStatus:
    return LocalStatus(entry=entry(name), path=tmp_path / name, installed=installed, version=version if installed else None)


def run(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


# ---------------------------------------------------------------- the labels of the table
@pytest.mark.parametrize("installed, version, remote_version, remote_error, expected", [
    (False, None, None, None, "not installed"),
    (True, None, Version(1, 0, 0), None, "unknown (local)"),
    (True, Version(1, 0, 0), "missing", None, "installed (not checked)"),
    (True, Version(1, 0, 0), None, "rate limited", "installed, GitHub unknown (rate limited)"),
    (True, Version(0, 1, 0), Version(0, 2, 0), None, "OUTDATED"),
    (True, Version(0, 3, 0), Version(0, 2, 0), None, "ahead of GitHub"),
    (True, Version(0, 2, 0), Version(0, 2, 0), None, "up to date"),
])
def test_the_state_of_a_project_in_the_table(tmp_path, installed, version, remote_version, remote_error, expected):
    status = LocalStatus(entry=entry(), path=tmp_path, installed=installed, version=version)
    remote = None if remote_version == "missing" else RemoteStatus(entry=entry(), version=remote_version, error=remote_error)
    assert main_module._state_label(status, remote) == expected


# ---------------------------------------------------------------- status without GitHub
def test_the_offline_table_lists_every_project_and_counts_without_asking_github(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path), local(tmp_path, "ARMOR-TWO", installed=False)), errors=()))
    assert run(["status", "--offline", "--workspace", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "ARMOR-ONE" in out and "ARMOR-TWO" in out and "not installed" in out
    assert "1/2 installed, 0 outdated (GitHub not checked)" in out
    assert "Signature policy:" in out


def test_notes_are_printed_below_the_table_when_asked(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path),), errors=()))
    run(["status", "--offline", "--notes", "--workspace", str(tmp_path)])
    out = capsys.readouterr().out
    assert "Notes (what's actually real per project" in out and "ARMOR-ONE [" in out and "no notes recorded" in out


def test_a_github_without_a_token_or_down_still_gives_the_local_state(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path),), errors=()))
    monkeypatch.setattr(main_module, "fetch_all", lambda entries: {})        # the raw version reads that follow a failed discovery are a network call too
    for error in (MissingTokenError("a token is needed"), RuntimeError("rate limit")):
        def fail(error=error):
            raise error
        monkeypatch.setattr(main_module, "discover_remote_projects", fail)
        assert run(["status", "--workspace", str(tmp_path)]) == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.err and "ARMOR-ONE" in captured.out


def test_an_outdated_project_is_counted_and_never_updated_by_itself(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path),), errors=()))
    monkeypatch.setattr(main_module, "discover_remote_projects", lambda: RemoteDiscovery(projects=(RemoteStatus(entry=entry(), version=Version(0, 9, 0)),), errors=("one repo said no",)))
    monkeypatch.setattr(main_module, "install_or_update", lambda *a, **k: pytest.fail("status must never install"))
    assert run(["status", "--workspace", str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert "OUTDATED" in captured.out and "1 outdated" in captured.out and "never automatic" in captured.out
    assert "WARNING: one repo said no" in captured.err


# ---------------------------------------------------------------- install and update
class Recorder:
    def __init__(self, ok=True):
        self.calls: list[tuple] = []
        self.ok = ok

    def __call__(self, entry, workspace, build=True):
        self.calls.append((entry.name, workspace, build))
        return [InstallResult(ok=self.ok, message="done" if self.ok else "broke", code="ok" if self.ok else "failed")]


def remote_with(*entries: ProjectEntry):
    return lambda: RemoteDiscovery(projects=tuple(RemoteStatus(entry=item, version=Version(1, 0, 0)) for item in entries), errors=())


def test_an_update_of_an_installed_project_never_asks_github_which_projects_exist(monkeypatch, capsys, tmp_path):
    (tmp_path / "ARMOR-ONE").mkdir()
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path),), errors=()))
    recorder = Recorder()
    monkeypatch.setattr(main_module, "install_or_update", recorder)
    assert run(["update", "ARMOR-ONE", "--workspace", str(tmp_path), "--no-build"]) == 0
    assert recorder.calls == [("ARMOR-ONE", tmp_path.resolve(), False)]
    assert "Updating ARMOR-ONE" in capsys.readouterr().out


def test_install_finds_a_project_that_exists_only_on_github(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(), errors=()))
    monkeypatch.setattr(main_module, "discover_remote_projects", remote_with(entry("ARMOR-NEW", note="Needs a camera")))
    recorder = Recorder()
    monkeypatch.setattr(main_module, "install_or_update", recorder)
    assert run(["install", "ARMOR-NEW", "--workspace", str(tmp_path)]) == 0
    assert recorder.calls == [("ARMOR-NEW", tmp_path.resolve(), True)]
    out = capsys.readouterr().out
    assert "Note: Needs a camera" in out and "Installing ARMOR-NEW" in out and "OK  done" in out


def test_a_name_nobody_knows_is_refused_and_nothing_is_installed(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(), errors=()))
    monkeypatch.setattr(main_module, "discover_remote_projects", remote_with(entry("ARMOR-OTHER")))
    monkeypatch.setattr(main_module, "install_or_update", lambda *a, **k: pytest.fail("nothing should be installed"))
    assert run(["install", "ARMOR-NOPE", "--workspace", str(tmp_path)]) == 1
    assert "Unknown ecosystem project: 'ARMOR-NOPE'" in capsys.readouterr().err


def test_github_being_unreachable_is_said_and_stops_an_install(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(), errors=()))

    def down():
        raise RuntimeError("no network")
    monkeypatch.setattr(main_module, "discover_remote_projects", down)
    assert run(["install", "ARMOR-NEW", "--workspace", str(tmp_path)]) == 1
    assert "Unable to discover GitHub projects: no network" in capsys.readouterr().err


def test_install_does_not_overwrite_a_checkout_and_update_does_not_invent_one(monkeypatch, capsys, tmp_path):
    (tmp_path / "ARMOR-ONE").mkdir()
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path),), errors=()))
    monkeypatch.setattr(main_module, "discover_remote_projects", remote_with(entry("ARMOR-ONE"), entry("ARMOR-NEW")))
    monkeypatch.setattr(main_module, "install_or_update", lambda *a, **k: pytest.fail("a guard should have stopped this"))
    assert run(["install", "ARMOR-ONE", "--workspace", str(tmp_path)]) == 1
    assert "already exists" in capsys.readouterr().err
    assert run(["update", "ARMOR-NEW", "--workspace", str(tmp_path)]) == 1
    assert "use `install`" in capsys.readouterr().err


def test_update_of_a_project_that_is_not_installed_says_to_install_it(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path, installed=True),), errors=()))
    monkeypatch.setattr(main_module, "install_or_update", lambda *a, **k: pytest.fail("a guard should have stopped this"))
    assert run(["update", "ARMOR-ONE", "--workspace", str(tmp_path)]) == 1                 # known locally, but its folder is not there
    assert "use `install`" in capsys.readouterr().err


def test_a_failed_build_is_a_failed_command(monkeypatch, capsys, tmp_path):
    (tmp_path / "ARMOR-ONE").mkdir()
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(local(tmp_path),), errors=()))
    monkeypatch.setattr(main_module, "install_or_update", Recorder(ok=False))
    assert run(["update", "ARMOR-ONE", "--workspace", str(tmp_path)]) == 1
    assert "FAIL broke" in capsys.readouterr().out


# ---------------------------------------------------------------- rollback and backups
def make_backup(workspace: Path, name: str, marker: str) -> Path:
    backup = new_backup_path(workspace, name, marker)
    backup.mkdir(parents=True)
    (backup / "marker.txt").write_text(marker, encoding="utf-8")
    return backup


def test_rollback_puts_the_newest_copy_back(tmp_path, capsys):
    project = tmp_path / "ARMOR-ONE"
    project.mkdir()
    (project / "marker.txt").write_text("current", encoding="utf-8")
    make_backup(tmp_path, "ARMOR-ONE", "previous")
    assert run(["rollback", "ARMOR-ONE", "--workspace", str(tmp_path)]) == 0
    assert (project / "marker.txt").read_text(encoding="utf-8") == "previous"


def test_rollback_without_a_copy_is_a_message_and_a_failure(tmp_path, capsys):
    (tmp_path / "ARMOR-ONE").mkdir()
    assert run(["rollback", "ARMOR-ONE", "--workspace", str(tmp_path)]) == 1
    assert capsys.readouterr().err.strip()


def test_rollback_refuses_while_another_run_holds_the_workspace(tmp_path, capsys):
    from armor_updater.promotion import WorkspaceLock
    (tmp_path / "ARMOR-ONE").mkdir()
    make_backup(tmp_path, "ARMOR-ONE", "previous")
    with WorkspaceLock(tmp_path):
        assert run(["rollback", "ARMOR-ONE", "--workspace", str(tmp_path)]) == 1
    assert capsys.readouterr().err.strip()
    assert (tmp_path / "ARMOR-ONE").is_dir()


def test_the_backups_are_listed_per_project_with_their_size_and_a_total(tmp_path, capsys):
    make_backup(tmp_path, "ARMOR-ONE", "one")
    make_backup(tmp_path, "ARMOR-ONE", "two")
    make_backup(tmp_path, "ARMOR-TWO", "three")
    assert run(["backups", "--workspace", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.count("ARMOR-ONE  ") == 2 and out.count("ARMOR-TWO  ") == 1 and "total " in out
    assert run(["backups", "ARMOR-TWO", "--workspace", str(tmp_path)]) == 0
    assert "ARMOR-ONE" not in capsys.readouterr().out


def test_without_backups_it_says_so(tmp_path, capsys):
    assert run(["backups", "--workspace", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "no backups"


def test_prune_keeps_only_the_newest_ones_and_says_what_it_deleted(tmp_path, capsys):
    for marker in ("one", "two", "three"):
        make_backup(tmp_path, "ARMOR-ONE", marker)
    assert run(["backups", "ARMOR-ONE", "--prune", "1", "--workspace", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert out.count("deleted") == 2
    from armor_updater.promotion import list_backups
    assert len(list_backups(tmp_path, "ARMOR-ONE")) == 1
    assert run(["backups", "ARMOR-ONE", "--prune", "-5", "--workspace", str(tmp_path)]) == 0     # a negative number keeps nothing, it does not crash
    assert list_backups(tmp_path, "ARMOR-ONE") == []


# ---------------------------------------------------------------- the entry point
def test_the_command_line_is_chosen_by_the_flag_or_the_first_word(monkeypatch, capsys, tmp_path):
    called = []
    monkeypatch.setattr(main_module, "cmd_backups", lambda args: called.append(args.command) or 0)
    for argv in (["armor-updater", "--cli", "backups"], ["armor-updater", "backups"]):
        monkeypatch.setattr(sys, "argv", argv)
        assert main_module.main() == 0
    assert called == ["backups", "backups"]


def test_the_command_line_with_no_command_prints_the_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["armor-updater", "--cli"])
    assert main_module.main() == 0
    assert "usage:" in capsys.readouterr().out


def test_a_workspace_nobody_named_is_exit_2_with_the_reason(monkeypatch, capsys):
    def unknown():
        raise main_module.WorkspaceUnknown("name the folder with --workspace")
    monkeypatch.setattr(main_module, "default_workspace_root", unknown)
    monkeypatch.setattr(sys, "argv", ["armor-updater", "status", "--offline"])
    assert main_module.main() == 2
    assert "--workspace" in capsys.readouterr().err


def test_the_version_is_printed_and_ends_the_program(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["armor-updater", "--cli", "--version"])
    with pytest.raises(SystemExit) as caught:
        main_module.main()
    assert caught.value.code == 0
    assert capsys.readouterr().out.startswith("armor-updater ")
