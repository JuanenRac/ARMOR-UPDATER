# =============================================================================
# ARMOR-UPDATER - tests/test_signed_tags.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The "only signed tags" mode: off by default; with it on, a revision is installed only when an annotated tag on it verifies against an allowed-signers file pinned by its SHA-256.
The decision is tested with doubles, and with real keys generated in the test where ssh-keygen exists."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from armor_updater import install, settings, signature
from armor_updater.install import clone_or_pull
from armor_updater.signature import SignaturePolicy, current_policy, file_sha256, signed_tag_refusal, signers_file_for_tags, verify_range, verify_revision
from test_install import entry, git, write_build_script, write_manifest
from test_signature import _signing_key, needs_ssh_keygen


def _clean_env(monkeypatch, tmp_path: Path) -> None:
    for name in ("ARMOR_UPDATER_REQUIRE_SIGNED", "ARMOR_UPDATER_SIGNED_TAGS_ONLY", "ARMOR_UPDATER_ALLOWED_SIGNERS", "ARMOR_UPDATER_ALLOWED_SIGNERS_SHA256"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")


def test_the_mode_is_off_by_default(monkeypatch, tmp_path: Path):
    _clean_env(monkeypatch, tmp_path)
    policy = current_policy()
    assert policy.signed_tags_only is False and policy.signers_sha256 is None
    assert signed_tag_refusal(tmp_path, "HEAD", policy) is None


def test_the_mode_and_the_pin_come_from_the_settings_and_the_environment(monkeypatch, tmp_path: Path):
    _clean_env(monkeypatch, tmp_path)
    settings.save_settings(signed_tags_only=True, allowed_signers_file="/x/signers", allowed_signers_sha256="ABC123")
    policy = current_policy()
    assert policy.signed_tags_only and policy.allowed_signers_file == "/x/signers" and policy.signers_sha256 == "abc123"
    monkeypatch.setenv("ARMOR_UPDATER_SIGNED_TAGS_ONLY", "0")
    assert current_policy().signed_tags_only is False


def test_a_damaged_settings_file_does_not_switch_the_mode_off(monkeypatch, tmp_path: Path):
    _clean_env(monkeypatch, tmp_path)
    (tmp_path / "settings.json").write_text("{not json", encoding="utf-8")
    assert current_policy().signed_tags_only is True


def test_a_chosen_signers_file_needs_its_pin(tmp_path: Path):
    signers = tmp_path / "allowed_signers"
    signers.write_text("a@example.invalid ssh-ed25519 AAAA\n", encoding="utf-8")
    path, reason = signers_file_for_tags(SignaturePolicy(False, str(signers), True, None))
    assert path is None and reason and "allowed_signers_sha256" in reason
    path, reason = signers_file_for_tags(SignaturePolicy(False, str(signers), True, "0" * 64))
    assert path is None and reason and "does not match" in reason
    path, reason = signers_file_for_tags(SignaturePolicy(False, str(signers), True, file_sha256(signers)))
    assert (path, reason) == (str(signers), None)
    path, reason = signers_file_for_tags(SignaturePolicy(False, str(tmp_path / "missing"), True, "0" * 64))
    assert path is None and reason and "does not exist" in reason


def test_the_decision_with_doubles(monkeypatch, tmp_path: Path):
    signers = tmp_path / "allowed_signers"
    signers.write_text("a@example.invalid ssh-ed25519 AAAA\n", encoding="utf-8")
    policy = SignaturePolicy(False, str(signers), True, file_sha256(signers))
    answers: dict[tuple[str, ...], tuple[int, str]] = {}

    def fake(_repo, *args):
        key = args[0] if args[0] != "-c" else "verify-tag"
        return answers.get((key,), (1, "unexpected"))

    monkeypatch.setattr(signature, "_git_text", fake)
    answers[("rev-parse",)] = (0, "abc")
    answers[("tag",)] = (0, "")
    assert "no tag" in (signed_tag_refusal(tmp_path, "HEAD", policy) or "")
    answers[("tag",)] = (0, "v1")
    answers[("cat-file",)] = (0, "commit")
    assert "lightweight" in (signed_tag_refusal(tmp_path, "HEAD", policy) or "")
    answers[("cat-file",)] = (0, "tag")
    answers[("verify-tag",)] = (1, "Good\nerror: no principal matched")
    assert "not signed by a trusted key" in (signed_tag_refusal(tmp_path, "HEAD", policy) or "")
    answers[("verify-tag",)] = (0, "Good signature")
    assert signed_tag_refusal(tmp_path, "HEAD", policy) is None
    assert verify_revision(tmp_path, "HEAD", policy) is None and verify_range(tmp_path, "a", "b", policy) is None


def _tagged_remote(tmp_path: Path, key: Path, *, tag: str | None, lightweight: bool = False) -> Path:
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    for name, value in (("user.email", "contract@example.invalid"), ("user.name", "Contract"), ("gpg.format", "ssh"), ("user.signingkey", str(key))):
        git("config", name, value, cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v1", cwd=seed)
    if tag:
        git("tag", tag, cwd=seed) if lightweight else git("tag", "-s", "-m", "release", tag, cwd=seed)
    git("push", "origin", "HEAD", "--tags", cwd=seed)
    return remote


def _clone(tmp_path: Path, remote: Path) -> Path:
    local = tmp_path / "local"
    git("clone", str(remote), str(local), cwd=tmp_path)
    return local


@needs_ssh_keygen
def test_a_tag_signed_by_the_pinned_key_is_accepted_and_the_others_are_refused(tmp_path: Path):
    key, allowed = _signing_key(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    other_key, other_allowed = _signing_key(other)
    local = _clone(tmp_path, _tagged_remote(tmp_path, key, tag="v1.0.0"))
    good = SignaturePolicy(False, str(allowed), True, file_sha256(allowed))
    assert verify_revision(local, "HEAD", good) is None
    wrong_key = SignaturePolicy(False, str(other_allowed), True, file_sha256(other_allowed))
    assert "not signed by a trusted key" in (verify_revision(local, "HEAD", wrong_key) or "")
    assert "does not match" in (verify_revision(local, "HEAD", SignaturePolicy(False, str(allowed), True, "f" * 64)) or "")
    assert other_key.exists()


@needs_ssh_keygen
def test_untagged_and_lightweight_revisions_are_refused(tmp_path: Path):
    key, allowed = _signing_key(tmp_path)
    policy = SignaturePolicy(False, str(allowed), True, file_sha256(allowed))
    assert "no tag" in (verify_revision(_clone(tmp_path, _tagged_remote(tmp_path, key, tag=None)), "HEAD", policy) or "")
    again = tmp_path / "again"
    again.mkdir()
    key2, allowed2 = _signing_key(again)
    policy2 = SignaturePolicy(False, str(allowed2), True, file_sha256(allowed2))
    assert "lightweight" in (verify_revision(_clone(again, _tagged_remote(again, key2, tag="v1", lightweight=True)), "HEAD", policy2) or "")


@needs_ssh_keygen
def test_install_needs_the_signed_tag_and_leaves_nothing_when_refused(tmp_path: Path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    key, allowed = _signing_key(tmp_path)
    remote = _tagged_remote(tmp_path, key, tag="v1.0.0")
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_SIGNED_TAGS_ONLY", "1")
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS", str(allowed))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    refused = clone_or_pull(entry(), workspace, verify_build=False)   # no pin: refused
    assert not refused.ok and refused.code == "signature_refused" and "allowed_signers_sha256" in refused.message
    assert list(workspace.iterdir()) == []
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS_SHA256", file_sha256(allowed))
    accepted = clone_or_pull(entry(), workspace, verify_build=False)
    assert accepted.ok, accepted.message


@needs_ssh_keygen
def test_an_update_to_an_untagged_commit_is_refused(tmp_path: Path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    key, allowed = _signing_key(tmp_path)
    remote = _tagged_remote(tmp_path, key, tag="v1.0.0")
    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip()
    seed = tmp_path / "seed"
    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v2 untagged", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_SIGNED_TAGS_ONLY", "1")
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS", str(allowed))
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS_SHA256", file_sha256(allowed))
    result = clone_or_pull(entry(), tmp_path)
    assert not result.ok and "no tag" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == head


def test_the_skip_marker_is_a_real_skip_without_ssh_keygen():
    assert isinstance(needs_ssh_keygen, pytest.MarkDecorator)
