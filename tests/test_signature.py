# =============================================================================
# ARMOR-UPDATER - tests/test_signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The optional "only install signed commits" policy, against real git
repositories and a real SSH signing key: an unsigned candidate is refused
before anything is validated or built (fresh install and update), a commit
signed by an allowed key is accepted, and a disabled policy changes
nothing."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from armor_updater import install
from armor_updater.install import clone_or_pull
from armor_updater.signature import SignaturePolicy, current_policy, verify_revision
from test_install import entry, git, write_build_script, write_manifest

needs_ssh_keygen = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen not available")


def _signing_key(tmp_path: Path) -> tuple[Path, Path]:
    key = tmp_path / "signing_key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    allowed = tmp_path / "allowed_signers"
    allowed.write_text("contract@example.invalid " + (tmp_path / "signing_key.pub").read_text(), encoding="utf-8")
    return key, allowed


def _remote_with_one_commit(tmp_path: Path, *, signing_key: Path | None) -> Path:
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    if signing_key is not None:
        git("config", "gpg.format", "ssh", cwd=seed)
        git("config", "user.signingkey", str(signing_key), cwd=seed)
        git("config", "commit.gpgsign", "true", cwd=seed)
    write_manifest(seed, "1.0.0")
    write_build_script(seed, ok=True)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v1", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    return remote


def test_disabled_policy_accepts_anything(tmp_path: Path):
    assert verify_revision(tmp_path, "HEAD", SignaturePolicy(required=False)) is None


def test_policy_comes_from_the_environment_first(monkeypatch):
    monkeypatch.setenv("ARMOR_UPDATER_REQUIRE_SIGNED", "1")
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS", "/x/allowed")
    assert current_policy() == SignaturePolicy(True, "/x/allowed")
    monkeypatch.setenv("ARMOR_UPDATER_REQUIRE_SIGNED", "0")
    assert current_policy().required is False


def test_missing_allowed_signers_file_is_refused(tmp_path: Path):
    reason = verify_revision(tmp_path, "HEAD", SignaturePolicy(True, str(tmp_path / "nope")))
    assert reason and "does not exist" in reason


def test_unsigned_fresh_install_is_refused_and_leaves_nothing_behind(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_commit(tmp_path, signing_key=None)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_REQUIRE_SIGNED", "1")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert not result.ok and "signature policy" in result.message
    assert list(workspace.iterdir()) == [], "a refused candidate must not leave a checkout or a staging directory"


@needs_ssh_keygen
def test_signed_fresh_install_is_accepted(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _remote_with_one_commit(tmp_path, signing_key=key)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_REQUIRE_SIGNED", "1")
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS", str(allowed))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok, result.message


@needs_ssh_keygen
def test_unsigned_update_is_refused_and_the_installed_checkout_is_untouched(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _remote_with_one_commit(tmp_path, signing_key=key)
    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    installed_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip()

    # An attacker (or a mistake) pushes an UNSIGNED v2.
    seed = tmp_path / "seed"
    git("config", "commit.gpgsign", "false", cwd=seed)
    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v2 unsigned", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)

    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_REQUIRE_SIGNED", "1")
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS", str(allowed))
    result = clone_or_pull(entry(), tmp_path)
    assert not result.ok and "signature policy" in result.message
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=local, text=True).strip() == installed_head
