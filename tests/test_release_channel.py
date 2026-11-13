# =============================================================================
# ARMOR-UPDATER - tests/test_release_channel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The channel of the updates: by default the newest signed release tag vX.Y.Z (a tag whose signature verifies against the pinned keys of the ecosystem), never the tip of the branch;
"development" follows the branch as the updater always did and is an option. The decision is tested with doubles, and end to end with real keys where ssh-keygen exists."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from armor_updater import install, settings, signature
from armor_updater.install import clone_or_pull
from armor_updater.signature import CHANNEL_DEVELOPMENT, CHANNEL_RELEASE, SignaturePolicy, current_policy, file_sha256, latest_signed_release, release_tags
from test_install import entry, git, write_manifest
from test_signature import _signing_key, needs_ssh_keygen
from test_signed_tags import _tagged_remote


def _head(path: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def _env(monkeypatch, tmp_path: Path, channel: str | None) -> None:
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    if channel is None:
        monkeypatch.delenv("ARMOR_UPDATER_CHANNEL", raising=False)
    else:
        monkeypatch.setenv("ARMOR_UPDATER_CHANNEL", channel)


class TestWhichChannelIsInForce:
    def test_the_default_is_the_release_channel(self, monkeypatch, tmp_path):
        _env(monkeypatch, tmp_path, None)
        assert current_policy().channel == CHANNEL_RELEASE == "release"

    def test_development_comes_from_the_environment_or_the_settings_and_the_environment_wins(self, monkeypatch, tmp_path):
        _env(monkeypatch, tmp_path, None)
        settings.save_settings(update_channel="development")
        assert current_policy().channel == CHANNEL_DEVELOPMENT
        monkeypatch.setenv("ARMOR_UPDATER_CHANNEL", "release")
        assert current_policy().channel == CHANNEL_RELEASE
        monkeypatch.setenv("ARMOR_UPDATER_CHANNEL", " Development ")
        assert current_policy().channel == CHANNEL_DEVELOPMENT

    @pytest.mark.parametrize("value", ["", "main", "dev", "nightly", "0", "off"])
    def test_anything_else_is_the_safe_channel(self, monkeypatch, tmp_path, value):
        _env(monkeypatch, tmp_path, value)
        assert current_policy().channel == CHANNEL_RELEASE

    def test_a_damaged_settings_file_is_the_safe_channel(self, monkeypatch, tmp_path):
        _env(monkeypatch, tmp_path, None)
        (tmp_path / "settings.json").write_text("{not json", encoding="utf-8")
        assert current_policy().channel == CHANNEL_RELEASE


class TestTheReleaseTags:
    def fake(self, monkeypatch, answers):
        monkeypatch.setattr(signature, "_git_text", lambda _repo, *args: answers(args))

    def test_only_release_names_count_and_the_newest_is_first(self, monkeypatch, tmp_path):
        names = "v0.9.0 v0.10.0 v0.10.0.1 v1.0.0 vNext v1.0 release-1 v1.0.0-rc1 v2"
        self.fake(monkeypatch, lambda args: (0, names) if args[0] == "tag" else (1, ""))
        assert [name for _, name in release_tags(tmp_path)] == ["v1.0.0", "v0.10.0.1", "v0.10.0", "v0.9.0"]

    def test_a_repository_that_cannot_list_its_tags_has_none(self, monkeypatch, tmp_path):
        self.fake(monkeypatch, lambda args: (128, "fatal"))
        assert release_tags(tmp_path) == []


class TestTheNewestSignedRelease:
    def signers(self, tmp_path) -> SignaturePolicy:
        file = tmp_path / "allowed_signers"
        file.write_text("a@example.invalid ssh-ed25519 AAAA\n", encoding="utf-8")
        return SignaturePolicy(False, str(file), False, file_sha256(file))

    def scripted(self, monkeypatch, tags: str, kinds: dict[str, str], signed: set[str]):
        def fake(_repo, *args):
            if args[0] == "tag":
                return 0, tags
            if args[0] == "cat-file":
                return (0, kinds[args[-1].removeprefix("refs/tags/")])
            if args[0] == "-c":
                tag = args[-1].removeprefix("refs/tags/")
                return (0, "Good signature") if tag in signed else (1, "Good\nerror: no principal matched")
            if args[0] == "rev-parse":
                return 0, "sha-of-" + args[-1].removeprefix("refs/tags/").removesuffix("^{commit}")
            return 1, "unexpected"
        monkeypatch.setattr(signature, "_git_text", fake)

    def test_the_newest_tag_that_verifies_is_chosen_and_a_newer_one_that_does_not_is_skipped(self, monkeypatch, tmp_path):
        self.scripted(monkeypatch, "v1.0.0 v1.1.0 v1.2.0", {"v1.0.0": "tag", "v1.1.0": "tag", "v1.2.0": "commit"}, {"v1.0.0", "v1.1.0"})
        assert latest_signed_release(tmp_path, self.signers(tmp_path)) == ("sha-of-v1.1.0", "v1.1.0")

    def test_a_tag_signed_by_another_key_is_never_taken_and_the_reason_names_it(self, monkeypatch, tmp_path):
        self.scripted(monkeypatch, "v1.0.0", {"v1.0.0": "tag"}, set())
        sha, reason = latest_signed_release(tmp_path, self.signers(tmp_path))
        assert sha is None and "no release tag is signed by a trusted key" in reason and "v1.0.0" in reason and "development" in reason

    def test_lightweight_tags_do_not_count(self, monkeypatch, tmp_path):
        self.scripted(monkeypatch, "v1.0.0", {"v1.0.0": "commit"}, {"v1.0.0"})
        sha, reason = latest_signed_release(tmp_path, self.signers(tmp_path))
        assert sha is None and "lightweight" in reason

    def test_no_release_tag_at_all_says_so_and_how_to_follow_the_branch(self, monkeypatch, tmp_path):
        monkeypatch.setattr(signature, "_git_text", lambda _repo, *args: (0, ""))
        sha, reason = latest_signed_release(tmp_path, self.signers(tmp_path))
        assert sha is None and "no release tag" in reason and "update_channel" in reason

    def test_a_signers_file_that_is_not_trusted_stops_everything(self, monkeypatch, tmp_path):
        policy = self.signers(tmp_path)
        bad = SignaturePolicy(False, policy.allowed_signers_file, False, "0" * 64)
        sha, reason = latest_signed_release(tmp_path, bad)
        assert sha is None and "does not match" in reason


def _commit_on(seed: Path, version: str, message: str) -> str:
    write_manifest(seed, version)
    git("add", "-A", cwd=seed)
    git("commit", "-m", message, cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    return _head(seed)


def _release_env(monkeypatch, tmp_path: Path, allowed: Path, remote: Path, channel: str = "release") -> Path:
    _env(monkeypatch, tmp_path, channel)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS", str(allowed))
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS_SHA256", file_sha256(allowed))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    return workspace


@needs_ssh_keygen
def test_a_fresh_install_takes_the_signed_release_and_not_the_newer_tip_of_the_branch(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _tagged_remote(tmp_path, key, tag="v1.0.0")
    released = _head(tmp_path / "seed")
    tip = _commit_on(tmp_path / "seed", "1.1.0", "work in progress, not released")
    assert tip != released
    workspace = _release_env(monkeypatch, tmp_path, allowed, remote)
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok, result.message
    assert _head(workspace / entry().name) == released


@needs_ssh_keygen
def test_a_fresh_install_from_a_repository_with_no_signed_release_is_refused_and_leaves_nothing(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _tagged_remote(tmp_path, key, tag=None)
    workspace = _release_env(monkeypatch, tmp_path, allowed, remote)
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert not result.ok and result.code == "signature_refused" and "no signed release" in result.message and "update_channel" in result.message
    assert list(workspace.iterdir()) == []


@needs_ssh_keygen
def test_an_update_goes_to_the_new_signed_release_only_when_there_is_one(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _tagged_remote(tmp_path, key, tag="v1.0.0")
    seed = tmp_path / "seed"
    workspace = _release_env(monkeypatch, tmp_path, allowed, remote)
    assert clone_or_pull(entry(), workspace, verify_build=False).ok
    local = workspace / entry().name
    first = _head(local)
    _commit_on(seed, "1.1.0", "work after the release")
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok and "up to date" in result.message, result.message
    assert _head(local) == first, "an untagged commit on the branch is not installed"
    second = _head(seed)
    git("tag", "-s", "-m", "release", "v1.1.0", cwd=seed)
    git("push", "origin", "--tags", cwd=seed)
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok, result.message
    assert _head(local) == second


@needs_ssh_keygen
def test_a_newer_tag_that_is_lightweight_is_not_installed(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _tagged_remote(tmp_path, key, tag="v1.0.0")
    seed = tmp_path / "seed"
    workspace = _release_env(monkeypatch, tmp_path, allowed, remote)
    assert clone_or_pull(entry(), workspace, verify_build=False).ok
    local = workspace / entry().name
    first = _head(local)
    _commit_on(seed, "1.1.0", "work after the release")
    git("tag", "v1.1.0", cwd=seed)
    git("push", "origin", "--tags", cwd=seed)
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok and _head(local) == first


@needs_ssh_keygen
def test_the_development_channel_follows_the_branch(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _tagged_remote(tmp_path, key, tag=None)
    seed = tmp_path / "seed"
    workspace = _release_env(monkeypatch, tmp_path, allowed, remote, channel="development")
    assert clone_or_pull(entry(), workspace, verify_build=False).ok
    local = workspace / entry().name
    tip = _commit_on(seed, "1.1.0", "the next work")
    assert clone_or_pull(entry(), workspace, verify_build=False).ok
    assert _head(local) == tip
