# =============================================================================
# ARMOR-UPDATER - tests/test_registry_tool.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The tool that makes, signs and checks the registry of releases, tried with a key made for each test (an ephemeral one in a folder that is deleted); no real key is ever read."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from armor_updater import registry_tool as tool, release_registry as rr
from test_signature import needs_ssh_keygen

COMMIT = "d" * 40


def _key(folder: Path, name: str = "key") -> Path:
    key = folder / name
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, timeout=60)
    return key


def _signers(folder: Path, key: Path) -> Path:
    pub = key.with_name(key.name + ".pub").read_text(encoding="utf-8").split()
    signers = folder / "allowed_signers"
    signers.write_text(f'{rr.IDENTITY} namespaces="git" {pub[0]} {pub[1]}\n', encoding="utf-8")
    return signers


def _registry(folder: Path) -> Path:
    registry = folder / "releases.json"
    registry.write_text(rr.render_registry([rr.Release("ARMOR-SERVER", "0.8.1.7", commit=COMMIT)]), encoding="utf-8")
    return registry


def _git(folder: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], check=True, capture_output=True, timeout=60)


def _repo(root: Path, name: str, version: str, tagged: bool) -> str:
    folder = root / name
    folder.mkdir()
    subprocess.run(["git", "init", "-q", str(folder)], check=True, timeout=60)
    (folder / "armor.project.json").write_text(json.dumps({"version": version}), encoding="utf-8")
    _git(folder, "add", "armor.project.json")
    _git(folder, "commit", "-q", "-m", "x")
    if tagged:
        _git(folder, "tag", f"v{version}")
    return subprocess.run(["git", "-C", str(folder), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


@needs_ssh_keygen
def test_a_registry_is_signed_with_the_key_of_the_signers_and_verifies(tmp_path: Path):
    key = _key(tmp_path)
    signers = _signers(tmp_path, key)
    registry = _registry(tmp_path)
    signature = tool.sign(registry, key, signers)
    assert signature.name == "releases.json.sig" and signature.is_file()
    releases = tool.verify(registry, signers)
    assert releases == [rr.Release("ARMOR-SERVER", "0.8.1.7", commit=COMMIT)]


@needs_ssh_keygen
def test_a_key_that_is_not_one_of_the_signers_signs_nothing(tmp_path: Path):
    signers = _signers(tmp_path, _key(tmp_path, "pinned"))
    stranger = _key(tmp_path, "stranger")
    registry = _registry(tmp_path)
    with pytest.raises(tool.RegistryToolError, match="not one of the keys"):
        tool.sign(registry, stranger, signers)
    assert not registry.with_name("releases.json.sig").exists()


@needs_ssh_keygen
def test_a_changed_registry_or_another_signer_does_not_verify(tmp_path: Path):
    key = _key(tmp_path)
    signers = _signers(tmp_path, key)
    registry = _registry(tmp_path)
    tool.sign(registry, key, signers)
    registry.write_text(registry.read_text(encoding="utf-8").replace(COMMIT, "e" * 40), encoding="utf-8")
    with pytest.raises(tool.RegistryToolError, match="not signed by a trusted key"):
        tool.verify(registry, signers)
    other = tmp_path / "other"
    other.mkdir()
    registry2 = _registry(other)
    tool.sign(registry2, key, signers)
    with pytest.raises(tool.RegistryToolError):
        tool.verify(registry2, _signers(other, _key(other, "elsewhere")))


def test_a_missing_signature_or_registry_is_refused(tmp_path: Path):
    registry = _registry(tmp_path)
    signers = tmp_path / "allowed_signers"
    signers.write_text("", encoding="utf-8")
    with pytest.raises(tool.RegistryToolError, match="no signature"):
        tool.verify(registry, signers)
    with pytest.raises(tool.RegistryToolError, match="does not exist"):
        tool.sign(tmp_path / "nothing.json", tmp_path / "key", signers)


def test_a_registry_that_is_not_valid_is_not_signed(tmp_path: Path):
    bad = tmp_path / "releases.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(tool.RegistryToolError, match="not valid"):
        tool.sign(bad, tmp_path / "key", tmp_path / "allowed_signers")


def test_the_registry_lists_the_commit_under_each_tag_and_names_what_it_left_out(tmp_path: Path):
    tagged = _repo(tmp_path, "ARMOR-SERVER", "0.8.2.2", True)
    _repo(tmp_path, "ARMOR-STUDIO", "0.8.2.4", False)
    (tmp_path / "ARMOR-DOCS").mkdir()   # no manifest: not a project
    releases, notes = tool.build(tmp_path)
    assert releases == [rr.Release("ARMOR-SERVER", "0.8.2.2", commit=tagged)]
    assert notes == ["ARMOR-STUDIO: no tag v0.8.2.4 (left out)"]
    assert rr.parse_registry(rr.render_registry(releases)) == releases


@needs_ssh_keygen
def test_the_command_line_makes_signs_and_verifies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    _repo(tmp_path, "ARMOR-SERVER", "0.8.2.2", True)
    key = _key(tmp_path)
    signers = _signers(tmp_path, key)
    out = tmp_path / "out" / "releases.json"
    out.parent.mkdir()
    assert tool.main(["build", "--root", str(tmp_path), "--out", str(out)]) == 0
    monkeypatch.delenv(tool.KEY_VARIABLE, raising=False)
    assert tool.main(["sign", str(out), "--signers", str(signers)]) == 1   # no key given: nothing is looked for
    monkeypatch.setenv(tool.KEY_VARIABLE, str(key))
    assert tool.main(["sign", str(out), "--signers", str(signers)]) == 0
    assert tool.main(["verify", str(out), "--signers", str(signers)]) == 0
    captured = capsys.readouterr()
    assert "REGISTRY=SIGNED" in captured.out and "REGISTRY=PASS releases=1" in captured.out and "no key" in captured.err
    assert tool.main(["keys"]) == 0
    assert "SHA256:" in capsys.readouterr().out
