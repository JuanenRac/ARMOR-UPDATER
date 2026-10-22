# =============================================================================
# ARMOR-UPDATER - tests/test_signers_pin.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The allowed-signers file of the ecosystem is shipped with the updater and trusted only while its keys are the pinned ones."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from armor_updater import signature
from armor_updater.signature import (
    ECOSYSTEM_SIGNERS_FILE,
    PINNED_SIGNER_FINGERPRINTS,
    SignaturePolicy,
    ecosystem_signers_problem,
    signer_fingerprints,
    unsigned_reason,
    verify_range,
)
from test_install import git, write_build_script, write_manifest

needs_ssh_keygen = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen not available")


def test_the_shipped_file_holds_exactly_the_pinned_keys():
    """Fails when the file and the fingerprint pinned in signature.py drift apart."""
    assert ECOSYSTEM_SIGNERS_FILE.is_file()
    assert signer_fingerprints(ECOSYSTEM_SIGNERS_FILE) == set(PINNED_SIGNER_FINGERPRINTS)
    assert ecosystem_signers_problem() is None


@needs_ssh_keygen
def test_the_pure_python_fingerprint_equals_the_one_ssh_keygen_prints(tmp_path: Path):
    key = tmp_path / "k"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    printed = subprocess.run(["ssh-keygen", "-lf", str(key) + ".pub"], capture_output=True, text=True, check=True).stdout.split()[1]
    allowed = tmp_path / "allowed"
    allowed.write_text("who " + (tmp_path / "k.pub").read_text(), encoding="utf-8")
    assert signer_fingerprints(allowed) == {printed}


def test_a_swapped_key_is_not_trusted(tmp_path: Path):
    other = tmp_path / "allowed_signers"
    other.write_text("x ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGJ1c3RlZGtleWJ1c3RlZGtleWJ1c3RlZGtleWJ1c3Q\n", encoding="utf-8")
    assert ecosystem_signers_problem(other)


def test_an_added_key_is_not_trusted(tmp_path: Path):
    extra = tmp_path / "allowed_signers"
    extra.write_text(ECOSYSTEM_SIGNERS_FILE.read_text(encoding="utf-8") + "x ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGJ1c3RlZGtleWJ1c3RlZGtleWJ1c3RlZGtleWJ1c3Q\n", encoding="utf-8")
    assert ecosystem_signers_problem(extra)


def test_a_missing_or_damaged_file_is_not_trusted(tmp_path: Path):
    assert ecosystem_signers_problem(tmp_path / "nope")
    bad = tmp_path / "bad"
    bad.write_text("principal only-no-key\n", encoding="utf-8")
    assert ecosystem_signers_problem(bad)


def test_a_tampered_shipped_file_makes_the_check_fail_closed(tmp_path: Path, monkeypatch):
    tampered = tmp_path / "allowed_signers"
    tampered.write_text("x ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGJ1c3RlZGtleWJ1c3RlZGtleWJ1c3RlZGtleWJ1c3Q\n", encoding="utf-8")
    monkeypatch.setattr(signature, "ECOSYSTEM_SIGNERS_FILE", tampered)
    reason = unsigned_reason(tmp_path, "HEAD", SignaturePolicy(True))
    assert reason and "allowed-signers" in reason


@needs_ssh_keygen
def test_a_commit_signed_by_a_pinned_key_passes_and_by_another_key_is_refused(tmp_path: Path, monkeypatch):
    trusted, stranger = tmp_path / "trusted", tmp_path / "stranger"
    for key in (trusted, stranger):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    shipped = tmp_path / "allowed_signers"
    shipped.write_text("armor namespaces=\"git\" " + (tmp_path / "trusted.pub").read_text(), encoding="utf-8")
    monkeypatch.setattr(signature, "ECOSYSTEM_SIGNERS_FILE", shipped)
    monkeypatch.setattr(signature, "PINNED_SIGNER_FINGERPRINTS", frozenset(signer_fingerprints(shipped)))

    repo = tmp_path / "repo"
    git("init", str(repo), cwd=tmp_path)
    git("config", "user.email", "a@example.invalid", cwd=repo)
    git("config", "user.name", "A", cwd=repo)
    git("config", "gpg.format", "ssh", cwd=repo)
    git("config", "commit.gpgsign", "true", cwd=repo)
    write_manifest(repo, "1.0.0")
    write_build_script(repo, ok=True)
    git("add", "-A", cwd=repo)
    git("config", "user.signingkey", str(trusted), cwd=repo)
    git("commit", "-m", "base", cwd=repo)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    (repo / "a.txt").write_text("a", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-m", "by the ecosystem key", cwd=repo)
    policy = SignaturePolicy(True)   # no file chosen by the person: the shipped, pinned one
    assert unsigned_reason(repo, "HEAD", policy) is None
    assert verify_range(repo, base, "HEAD", policy) is None

    git("config", "user.signingkey", str(stranger), cwd=repo)
    (repo / "b.txt").write_text("b", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-m", "by a stranger", cwd=repo)
    assert unsigned_reason(repo, "HEAD", policy) is not None
    assert verify_range(repo, base, "HEAD", policy) is not None
