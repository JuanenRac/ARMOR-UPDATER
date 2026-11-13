# =============================================================================
# ARMOR-UPDATER - tests/test_releases_gaps.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Corners of the releases layout that need neither a git remote nor a link: who is asked to use the layout, where a release lives, the list of releases newest first, what is pruned
(never the one in service, never fewer than asked), and the ways the backup of a history can fail. Everything is in a throwaway folder."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from armor_updater import releases


def make_release(workspace: Path, project: str, name: str, age: int) -> Path:
    path = releases.releases_directory(workspace, project) / name
    path.mkdir(parents=True)
    (path / "file.txt").write_text(name, encoding="utf-8")
    stamp = 1_800_000_000 - age
    os.utime(path, (stamp, stamp))
    return path


class TestWhoUsesTheLayout:
    def test_the_checkout_layout_never_uses_releases(self, monkeypatch, tmp_path):
        monkeypatch.setattr(releases, "chosen_layout", lambda: releases.LAYOUT_CHECKOUT)
        assert releases.current_layout() == releases.LAYOUT_CHECKOUT
        assert releases.wants_releases("ARMOR-SERVER", tmp_path) is False

    def test_an_unknown_choice_means_the_default_which_is_releases(self, monkeypatch, tmp_path):
        monkeypatch.setattr(releases, "chosen_layout", lambda: None)
        assert releases.current_layout() == releases.LAYOUT_RELEASES
        monkeypatch.setattr(releases, "links_supported", lambda _root: True)
        assert releases.wants_releases("ARMOR-SERVER", tmp_path) is True

    def test_nobody_chose_and_the_workspace_cannot_hold_links_so_the_old_layout_is_kept(self, monkeypatch, tmp_path):
        monkeypatch.setattr(releases, "chosen_layout", lambda: None)
        monkeypatch.setattr(releases, "links_supported", lambda _root: False)
        assert releases.wants_releases("ARMOR-SERVER", tmp_path) is False
        assert releases.wants_releases("ARMOR-SERVER") is True, "without a workspace there is nothing to try"

    def test_a_person_who_chose_releases_gets_them_even_if_links_look_unsupported(self, monkeypatch, tmp_path):
        monkeypatch.setattr(releases, "chosen_layout", lambda: releases.LAYOUT_RELEASES)
        monkeypatch.setattr(releases, "links_supported", lambda _root: False)
        assert releases.wants_releases("ARMOR-SERVER", tmp_path) is True


class TestWhereAReleaseLives:
    def test_a_release_folder_is_named_by_the_first_twelve_characters_of_its_commit(self, tmp_path):
        path = releases.release_path(tmp_path, "ARMOR-SERVER", "0123456789abcdef0123456789abcdef01234567")
        assert path.name == "0123456789ab"
        assert path.parent == releases.releases_directory(tmp_path, "ARMOR-SERVER")
        assert releases.release_path(tmp_path, "ARMOR-SERVER", "abc").name == "abc"

    def test_a_folder_and_a_missing_path_are_not_links(self, tmp_path):
        assert releases.link_target(tmp_path) is None
        assert releases.link_target(tmp_path / "missing") is None
        (tmp_path / "plain.txt").write_text("x", encoding="utf-8")
        assert releases.link_target(tmp_path / "plain.txt") is None


class TestTheListAndThePrune:
    def test_no_folder_means_no_releases(self, tmp_path):
        assert releases.list_releases(tmp_path, "ARMOR-SERVER") == []
        assert releases.prune_releases(tmp_path, "ARMOR-SERVER") == []

    def test_releases_are_listed_newest_first_and_a_stray_file_is_ignored(self, tmp_path):
        old = make_release(tmp_path, "ARMOR-SERVER", "aaaaaaaaaaaa", 300)
        new = make_release(tmp_path, "ARMOR-SERVER", "bbbbbbbbbbbb", 10)
        mid = make_release(tmp_path, "ARMOR-SERVER", "cccccccccccc", 100)
        (releases.releases_directory(tmp_path, "ARMOR-SERVER") / "notes.txt").write_text("not a release", encoding="utf-8")
        assert releases.list_releases(tmp_path, "ARMOR-SERVER") == [new, mid, old]

    def test_prune_keeps_the_newest_ones_and_deletes_the_rest(self, monkeypatch, tmp_path):
        made = [make_release(tmp_path, "ARMOR-SERVER", f"{index:012d}", index * 10) for index in range(5)]
        monkeypatch.setattr(releases, "in_service", lambda *_args: None)
        removed = releases.prune_releases(tmp_path, "ARMOR-SERVER", keep=2)
        assert sorted(removed) == sorted(made[2:])
        assert releases.list_releases(tmp_path, "ARMOR-SERVER") == made[:2]

    def test_prune_never_deletes_the_release_in_service_even_when_it_is_old(self, monkeypatch, tmp_path):
        newest = make_release(tmp_path, "ARMOR-SERVER", "bbbbbbbbbbbb", 1)
        second = make_release(tmp_path, "ARMOR-SERVER", "cccccccccccc", 2)
        serving = make_release(tmp_path, "ARMOR-SERVER", "aaaaaaaaaaaa", 900)
        oldest = make_release(tmp_path, "ARMOR-SERVER", "dddddddddddd", 950)
        monkeypatch.setattr(releases, "in_service", lambda *_args: serving)
        removed = releases.prune_releases(tmp_path, "ARMOR-SERVER", keep=2)
        assert removed == [oldest], "only the oldest goes: the one in service is skipped and counted"
        assert set(releases.list_releases(tmp_path, "ARMOR-SERVER")) == {newest, second, serving}

    def test_prune_with_fewer_releases_than_asked_deletes_nothing(self, monkeypatch, tmp_path):
        make_release(tmp_path, "ARMOR-SERVER", "aaaaaaaaaaaa", 5)
        monkeypatch.setattr(releases, "in_service", lambda *_args: None)
        assert releases.prune_releases(tmp_path, "ARMOR-SERVER", keep=3) == []


class TestTheBackupOfAHistory:
    class Done:
        def __init__(self, code: int, out: str = "") -> None:
            self.returncode, self.stdout = code, out

    def test_a_failed_bundle_is_no_backup(self, monkeypatch, tmp_path):
        calls: list[list[str]] = []

        def fake(command, **_kwargs):
            calls.append(command)
            return self.Done(0, "abcdef1234567890\n") if command[1] == "rev-parse" else self.Done(1)
        monkeypatch.setattr(subprocess, "run", fake)
        assert releases.backup_history(tmp_path, "ARMOR-SERVER", tmp_path) is None
        assert calls[1][:3] == ["git", "bundle", "create"] and calls[1][3].endswith("abcdef123456.bundle")

    def test_a_system_error_is_no_backup_and_a_bundle_that_is_not_written_is_no_backup(self, monkeypatch, tmp_path):
        def broken(command, **_kwargs):
            if command[1] == "rev-parse":
                return self.Done(0, "")
            raise OSError("git is not installed")
        monkeypatch.setattr(subprocess, "run", broken)
        assert releases.backup_history(tmp_path, "ARMOR-SERVER", tmp_path) is None
        monkeypatch.setattr(subprocess, "run", lambda command, **_k: self.Done(0, "") if command[1] == "rev-parse" else self.Done(0))
        assert releases.backup_history(tmp_path, "ARMOR-SERVER", tmp_path) is None, "a success code with no file is not a backup"

    def test_a_bundle_that_exists_is_the_backup_named_by_the_commit(self, monkeypatch, tmp_path):
        def writes(command, **_kwargs):
            if command[1] == "rev-parse":
                return self.Done(0, "0123456789abcdef\n")
            Path(command[3]).write_bytes(b"bundle")
            return self.Done(0)
        monkeypatch.setattr(subprocess, "run", writes)
        path = releases.backup_history(tmp_path, "ARMOR-SERVER", tmp_path)
        assert path is not None and path.name == "0123456789ab.bundle" and path.read_bytes() == b"bundle"


@pytest.mark.parametrize("name", ["checkout", "releases"])
def test_the_names_of_the_two_layouts_are_stable(name):
    assert name in (releases.LAYOUT_CHECKOUT, releases.LAYOUT_RELEASES)
