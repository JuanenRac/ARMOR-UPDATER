# =============================================================================
# ARMOR-UPDATER - tests/test_releases.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The optional releases layout: the project folder is a link to a release folder that was built where it stays; a failed build changes nothing; going back is a link switch; the
default layout and the updater itself are left alone."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from armor_updater import install, releases
from armor_updater.install import clone_or_pull, restore_previous_copy
from test_install import entry, git, write_build_script, write_manifest


def _head(path: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def _remote(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v1", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    return remote, seed


def _push(seed: Path, version: str, *, build_ok: bool = True) -> str:
    write_manifest(seed, version)
    write_build_script(seed, ok=build_ok)
    git("add", "-A", cwd=seed)
    git("commit", "-m", f"v{version}", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    return _head(seed)


@pytest.fixture
def releases_layout(monkeypatch):
    monkeypatch.setenv("ARMOR_UPDATER_LAYOUT", "releases")
    monkeypatch.setenv("ARMOR_UPDATER_REQUIRE_SIGNED", "0")


def test_the_default_layout_is_releases_and_checkout_is_a_choice(monkeypatch):
    monkeypatch.delenv("ARMOR_UPDATER_LAYOUT", raising=False)
    monkeypatch.setattr(releases, "load_settings", lambda: {})
    assert releases.current_layout() == "releases"
    monkeypatch.setenv("ARMOR_UPDATER_LAYOUT", "nonsense")
    assert releases.current_layout() == "releases"
    monkeypatch.setenv("ARMOR_UPDATER_LAYOUT", "checkout")
    assert releases.current_layout() == "checkout" and releases.wants_releases("ARMOR-SERVER") is False


def test_the_updater_is_moved_like_any_other_project(monkeypatch):
    monkeypatch.setenv("ARMOR_UPDATER_LAYOUT", "releases")
    assert releases.wants_releases("ARMOR-UPDATER") is True
    assert releases.wants_releases("ARMOR-SERVER") is True


def test_without_links_and_without_a_choice_the_old_layout_is_used(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ARMOR_UPDATER_LAYOUT", raising=False)
    monkeypatch.setattr(releases, "load_settings", lambda: {})
    monkeypatch.setattr(releases, "_LINK_SUPPORT", {})
    def refuse(link, target):
        raise OSError("no links here")
    monkeypatch.setattr(releases, "make_link", refuse)
    assert releases.wants_releases("ARMOR-SERVER", tmp_path) is False
    monkeypatch.setenv("ARMOR_UPDATER_LAYOUT", "releases")   # an explicit choice is respected (and then fails loudly)
    assert releases.wants_releases("ARMOR-SERVER", tmp_path) is True


def test_the_first_update_migrates_a_checkout_with_a_backup_and_says_it_in_eight_languages(tmp_path: Path, monkeypatch):
    from armor_updater.result_text import localized_message
    _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("ARMOR_UPDATER_LAYOUT", "checkout")
    assert clone_or_pull(entry(), workspace).ok   # an installation made in the old layout
    name = entry().name
    assert releases.link_target(workspace / name) is None
    first_head = _head(workspace / name)
    _push(tmp_path / "seed", "1.1.0")
    monkeypatch.delenv("ARMOR_UPDATER_LAYOUT", raising=False)
    monkeypatch.setattr(releases, "load_settings", lambda: {})

    result = clone_or_pull(entry(), workspace)

    assert result.ok and result.code == "layout_migrated", result.message
    serving = releases.in_service(workspace, name)
    assert serving is not None and _head(workspace / name) != first_head
    assert any(r.name == first_head[:12] for r in releases.list_releases(workspace, name)), "the old checkout is kept as a release"
    bundle = workspace / ".armor-updater" / "layout-backups" / name / f"{first_head[:12]}.bundle"
    assert bundle.is_file(), "a backup of the history was written before the move"
    for language in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
        said = localized_message(language, result)
        assert name in said and "1.1.0" in said, language


def test_a_checkout_that_cannot_be_moved_is_updated_in_the_old_layout(tmp_path: Path, monkeypatch):
    """The running updater on Windows cannot rename its own folder: nothing is lost and the update goes on in the checkout layout."""
    _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setenv("ARMOR_UPDATER_LAYOUT", "checkout")
    assert clone_or_pull(entry(), workspace).ok
    name = entry().name
    served = workspace / name
    first_head = _head(served)
    _push(tmp_path / "seed", "1.1.0")
    monkeypatch.delenv("ARMOR_UPDATER_LAYOUT", raising=False)
    monkeypatch.setattr(releases, "load_settings", lambda: {})
    real_rename = Path.rename
    def locked(self, target):
        if self == served and "releases" in str(target):
            raise PermissionError("in use")
        return real_rename(self, target)
    monkeypatch.setattr(Path, "rename", locked)

    result = clone_or_pull(entry(), workspace)

    monkeypatch.undo()
    assert result.ok, result.message
    assert releases.link_target(served) is None and (served / ".git").is_dir()
    assert _head(served) != first_head, "the update was applied in the older layout"
    assert releases.list_releases(workspace, name) == []


def test_a_fresh_install_is_built_where_it_stays_and_linked(tmp_path: Path, monkeypatch, releases_layout):
    _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace)
    assert result.ok, result.message
    link = workspace / entry().name
    target = releases.in_service(workspace, entry().name)
    assert target is not None and releases.link_target(link) is not None
    assert (link / "built.txt").exists() and (target / "built.txt").exists()
    assert not list(workspace.glob(".*.clone-*"))


def test_a_real_checkout_is_migrated_by_an_update_and_the_old_one_is_kept(tmp_path: Path, monkeypatch, releases_layout):
    remote, seed = _remote(tmp_path, monkeypatch)
    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    old = _head(local)
    new = _push(seed, "1.1.0")

    result = clone_or_pull(entry(), tmp_path)

    assert result.ok, result.message
    assert releases.link_target(local) is not None
    assert _head(local) == new
    assert (local / "built.txt").exists()
    kept = releases.list_releases(tmp_path, entry().name)
    assert sorted(_head(r) for r in kept) == sorted([old, new])
    assert releases.in_service(tmp_path, entry().name).name == new[:12]


def test_a_failed_build_leaves_the_link_and_the_release_in_service_untouched(tmp_path: Path, monkeypatch, releases_layout):
    remote, seed = _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert clone_or_pull(entry(), workspace).ok
    serving = releases.in_service(workspace, entry().name)
    served_head = _head(workspace / entry().name)
    _push(seed, "1.1.0", build_ok=False)

    result = clone_or_pull(entry(), workspace)

    assert not result.ok and "build failed" in result.message
    assert releases.in_service(workspace, entry().name) == serving
    assert _head(workspace / entry().name) == served_head
    assert [r.name for r in releases.list_releases(workspace, entry().name)] == [serving.name], "the failed release folder must be removed"


def test_going_back_is_a_switch_of_the_link_and_can_be_undone(tmp_path: Path, monkeypatch, releases_layout):
    remote, seed = _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert clone_or_pull(entry(), workspace).ok
    first = _head(workspace / entry().name)
    second = _push(seed, "1.1.0")
    assert clone_or_pull(entry(), workspace).ok
    assert _head(workspace / entry().name) == second

    back = restore_previous_copy(workspace, entry().name)
    assert back.ok, back.message
    assert _head(workspace / entry().name) == first
    again = restore_previous_copy(workspace, entry().name)
    assert again.ok and _head(workspace / entry().name) == second


def test_only_the_newest_releases_are_kept_and_never_the_one_in_service(tmp_path: Path, monkeypatch, releases_layout):
    remote, seed = _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert clone_or_pull(entry(), workspace).ok
    for number in range(1, 5):
        _push(seed, f"1.{number}.0")
        assert clone_or_pull(entry(), workspace).ok
    names = [r.name for r in releases.list_releases(workspace, entry().name)]
    assert len(names) == releases.DEFAULT_KEEP_RELEASES
    assert releases.in_service(workspace, entry().name).name in names


def test_a_crash_between_the_two_steps_of_a_windows_switch_is_finished_by_the_next_run(tmp_path: Path):
    target = tmp_path / "rel"
    target.mkdir()
    fresh = tmp_path / ".proj.link-new"
    releases.make_link(fresh, target)
    assert releases.heal_link(tmp_path) == ["proj: an interrupted switch of the release in service was finished"]
    assert releases.link_target(tmp_path / "proj") is not None


def test_the_check_after_the_switch_sees_a_good_release_and_each_way_it_can_be_wrong(tmp_path: Path, monkeypatch, releases_layout):
    _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert clone_or_pull(entry(), workspace).ok
    name = entry().name
    serving = releases.in_service(workspace, name)
    head = _head(workspace / name)
    assert releases.verify_in_service(workspace, name, serving, head) is None
    assert "another release" in releases.verify_in_service(workspace, name, tmp_path / "elsewhere", head)
    assert "not at the commit" in releases.verify_in_service(workspace, name, serving, "0" * 40)
    manifest = serving / "armor.project.json"
    saved = manifest.read_text(encoding="utf-8")
    manifest.write_text("{ not json", encoding="utf-8")
    assert "cannot be read" in releases.verify_in_service(workspace, name, serving, head)
    manifest.write_text("[]", encoding="utf-8")
    assert "no version" in releases.verify_in_service(workspace, name, serving, head)
    manifest.unlink()
    assert "cannot be read" in releases.verify_in_service(workspace, name, serving, head)
    manifest.write_text(saved, encoding="utf-8")
    assert releases.verify_in_service(workspace, name, serving, head) is None
    plain = tmp_path / "plain"
    (plain / "P").mkdir(parents=True)
    assert "not a link" in releases.verify_in_service(plain, "P", plain / "P", head)


def test_a_release_that_fails_its_check_after_the_switch_is_taken_out_of_service_by_itself(tmp_path: Path, monkeypatch, releases_layout):
    from armor_updater.result_text import localized_message
    _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert clone_or_pull(entry(), workspace).ok
    name = entry().name
    serving = releases.in_service(workspace, name)
    served_head = _head(workspace / name)
    seed = tmp_path / "seed"
    _push(seed, "1.1.0")
    real = releases.verify_in_service
    monkeypatch.setattr(install, "verify_in_service", lambda *args: "the manifest of the new release cannot be read (OSError)")

    result = clone_or_pull(entry(), workspace)

    assert not result.ok and result.code == "rolled_back", result.message
    assert releases.in_service(workspace, name) == serving, "the link is back on the release that was in service"
    assert _head(workspace / name) == served_head
    assert [r.name for r in releases.list_releases(workspace, name)] == [serving.name], "the release that failed is gone"
    for language in ("en", "es", "de", "fr", "it", "ja", "zh", "pt"):
        said = localized_message(language, result)
        assert name in said and "cannot be read" in said, language
    # nothing is stuck: the next update, whose check passes, goes through
    monkeypatch.setattr(install, "verify_in_service", real)
    again = clone_or_pull(entry(), workspace)
    assert again.ok, again.message
    assert _head(workspace / name) != served_head


def test_a_first_install_that_fails_its_check_leaves_no_link_and_no_folder(tmp_path: Path, monkeypatch, releases_layout):
    _remote(tmp_path, monkeypatch)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr(install, "verify_in_service", lambda *args: "the new release is not at the commit that was built")

    result = clone_or_pull(entry(), workspace)

    assert not result.ok and result.code == "rolled_back", result.message
    assert not (workspace / entry().name).exists() and releases.link_target(workspace / entry().name) is None
    assert releases.list_releases(workspace, entry().name) == []
