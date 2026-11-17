# =============================================================================
# ARMOR-UPDATER - tests/test_signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
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
    assert current_policy() == SignaturePolicy(True, "/x/allowed", channel="development")   # the tests run on the development channel (conftest)
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


def _commit_with_header(tmp_path: Path, header: str) -> tuple[Path, str]:
    """A repository whose HEAD~0 is a plain commit and whose second value is a commit that carries the given gpgsig header text: no key is needed to read what kind of signature it claims."""
    repo = tmp_path / "forged"
    git("init", str(repo), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=repo)
    git("config", "user.name", "Contract", cwd=repo)
    (repo / "a.txt").write_text("a", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-m", "plain", cwd=repo)
    plain = subprocess.run(["git", "cat-file", "commit", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout
    head, message = plain.split("\n\n", 1)
    forged = head + "\ngpgsig " + header + "\n \n AAAA\n " + header.replace("BEGIN", "END") + "\n\n" + message
    made = subprocess.run(["git", "hash-object", "-t", "commit", "-w", "--stdin"], cwd=repo, input=forged.encode(), capture_output=True, check=True).stdout.decode().strip()
    return repo, made


def test_the_kind_of_signature_is_read_from_the_header(tmp_path: Path):
    from armor_updater.signature import signature_kind
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    repo, ssh_commit = _commit_with_header(tmp_path / "one", "-----BEGIN SSH SIGNATURE-----")
    assert signature_kind(repo, ssh_commit) == "ssh"
    assert signature_kind(repo, "HEAD") == "none"
    repo2, pgp_commit = _commit_with_header(tmp_path / "two", "-----BEGIN PGP SIGNATURE-----")
    assert signature_kind(repo2, pgp_commit) == "pgp"
    assert signature_kind(repo2, "no-such-revision") == "none"


def test_only_ssh_signatures_are_accepted_when_the_setting_says_so(tmp_path: Path):
    allowed = tmp_path / "allowed"
    allowed.write_text("contract@example.invalid ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n", encoding="utf-8")
    (tmp_path / "pgp").mkdir()
    repo, pgp_commit = _commit_with_header(tmp_path / "pgp", "-----BEGIN PGP SIGNATURE-----")
    strict = SignaturePolicy(True, str(allowed), signature_formats="ssh")
    reason = verify_revision(repo, pgp_commit, strict)
    assert reason and "no SSH signature" in reason and "PGP" in reason
    unsigned = verify_revision(repo, "HEAD", strict)   # the plain commit below the forged one
    assert unsigned and "no SSH signature" in unsigned
    # the default does not look at the kind: the refusal there is git's own, about the key
    default = verify_revision(repo, pgp_commit, SignaturePolicy(True, str(allowed)))
    assert default and "no SSH signature" not in default


def test_the_format_comes_from_the_environment_or_the_settings(monkeypatch):
    assert current_policy().signature_formats == "any"
    monkeypatch.setenv("ARMOR_UPDATER_SIGNATURE_FORMATS", "SSH")
    assert current_policy().signature_formats == "ssh"
    monkeypatch.setenv("ARMOR_UPDATER_SIGNATURE_FORMATS", "gpg")
    assert current_policy().signature_formats == "any"      # anything else is the default


@needs_ssh_keygen
def test_a_really_signed_commit_passes_when_only_ssh_signatures_are_accepted(tmp_path: Path):
    key, allowed = _signing_key(tmp_path)
    remote = _remote_with_one_commit(tmp_path, signing_key=key)
    clone = tmp_path / "clone"
    git("clone", str(remote), str(clone), cwd=tmp_path)
    assert verify_revision(clone, "HEAD", SignaturePolicy(True, str(allowed), signature_formats="ssh")) is None
