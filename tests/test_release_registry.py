# =============================================================================
# ARMOR-UPDATER - tests/test_release_registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The signed registry of releases: read whole or not at all, checked with a real SSH key where ssh-keygen exists, and off by default (a damaged settings file never switches it off)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from armor_updater import install, release_registry as rr, settings
from armor_updater.signature import SignaturePolicy, current_policy
from test_signature import needs_ssh_keygen

COMMIT = "a" * 40
OTHER = "b" * 40
HASH = "c" * 64


def _registry(tmp_path: Path, releases: list[rr.Release] | None = None) -> Path:
    path = tmp_path / "releases.json"
    path.write_text(rr.render_registry(releases or [rr.Release("ARMOR-SERVER", "0.8.1.7", commit=COMMIT), rr.Release("ARMOR-NODE-RADAR", "0.8.1.0", board="s3-eth", sha256=HASH)]), encoding="utf-8", newline="\n")
    return path


def _signed(tmp_path: Path, releases: list[rr.Release] | None = None) -> tuple[Path, Path]:
    key = tmp_path / "key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, timeout=60)
    pub = (tmp_path / "key.pub").read_text(encoding="utf-8").split()
    signers = tmp_path / "allowed_signers"
    signers.write_text(f'{rr.IDENTITY} namespaces="git" {pub[0]} {pub[1]}\n', encoding="utf-8")
    registry = _registry(tmp_path, releases)
    subprocess.run(rr.sign_command(registry, key), check=True, capture_output=True, timeout=60)
    return registry, signers


def test_a_registry_is_written_in_one_layout_and_read_back():
    text = rr.render_registry([rr.Release("B", "0.1.0", commit=COMMIT), rr.Release("A", "0.2.0", commit=OTHER)])
    assert text.index('"A"') < text.index('"B"')
    assert rr.parse_registry(text)[0] == rr.Release("A", "0.2.0", commit=OTHER)
    assert rr.render_registry(rr.parse_registry(text)) == text


@pytest.mark.parametrize("text", ["{not json", "[]", '{"schema_version": 2, "releases": []}', '{"schema_version": 1}',
                                  '{"schema_version": 1, "releases": [1]}',
                                  '{"schema_version": 1, "releases": [{"project": "A", "version": "x"}]}',
                                  '{"schema_version": 1, "releases": [{"project": "A", "version": "1.0.0"}]}',
                                  '{"schema_version": 1, "releases": [{"project": "A", "version": "1.0.0", "commit": "abc"}]}',
                                  '{"schema_version": 1, "releases": [{"project": "A", "version": "1.0.0", "sha256": "ABC"}]}',
                                  '{"schema_version": 1, "releases": [{"project": "A", "version": "1.0.0", "commit": "' + "a" * 40 + '"}, {"project": "A", "version": "1.0.0", "commit": "' + "b" * 40 + '"}]}'])
def test_a_registry_outside_the_format_is_refused_whole(text: str):
    with pytest.raises(ValueError):
        rr.parse_registry(text)


@needs_ssh_keygen
def test_a_signed_registry_that_lists_the_commit_accepts_it(tmp_path: Path):
    registry, signers = _signed(tmp_path)
    assert rr.registry_refusal(registry, "ARMOR-SERVER", "0.8.1.7", COMMIT, signers=signers) is None
    assert rr.file_refusal(registry, "ARMOR-NODE-RADAR", "0.8.1.0", "s3-eth", HASH.upper(), signers=signers) is None


@needs_ssh_keygen
def test_a_commit_the_registry_does_not_list_is_refused(tmp_path: Path):
    registry, signers = _signed(tmp_path)
    assert "does not list this commit" in (rr.registry_refusal(registry, "ARMOR-SERVER", "0.8.1.7", OTHER, signers=signers) or "")
    assert "another version" in (rr.registry_refusal(registry, "ARMOR-SERVER", "0.9.0", COMMIT, signers=signers) or "")
    assert "does not list ARMOR-STUDIO" in (rr.registry_refusal(registry, "ARMOR-STUDIO", None, COMMIT, signers=signers) or "")
    assert rr.file_refusal(registry, "ARMOR-NODE-RADAR", "0.8.1.0", "other-board", HASH, signers=signers)


@needs_ssh_keygen
def test_a_registry_changed_after_signing_or_without_signature_is_refused(tmp_path: Path):
    registry, signers = _signed(tmp_path)
    registry.write_text(registry.read_text(encoding="utf-8").replace(COMMIT, OTHER), encoding="utf-8", newline="\n")
    assert "not signed by a trusted key" in (rr.registry_refusal(registry, "ARMOR-SERVER", "0.8.1.7", OTHER, signers=signers) or "")
    registry.with_name("releases.json.sig").unlink()
    assert "no signature" in (rr.registry_refusal(registry, "ARMOR-SERVER", "0.8.1.7", OTHER, signers=signers) or "")
    assert "does not exist" in (rr.registry_refusal(tmp_path / "missing.json", "A", None, COMMIT, signers=signers) or "")


@needs_ssh_keygen
def test_a_signature_by_another_key_is_refused(tmp_path: Path):
    (tmp_path / "mine").mkdir()
    (tmp_path / "other").mkdir()
    registry, _ = _signed(tmp_path / "mine")
    _, other_signers = _signed(tmp_path / "other")
    assert "not signed by a trusted key" in (rr.registry_refusal(registry, "ARMOR-SERVER", "0.8.1.7", COMMIT, signers=other_signers) or "")


def test_a_tool_that_cannot_run_refuses_instead_of_accepting(tmp_path: Path):
    registry = _registry(tmp_path)
    registry.with_name("releases.json.sig").write_text("x", encoding="utf-8")
    signers = tmp_path / "allowed_signers"
    signers.write_text(f"{rr.IDENTITY} ssh-ed25519 AAAA\n", encoding="utf-8")

    def broken(*_a, **_k):
        raise OSError("no ssh-keygen")

    reason = rr.registry_refusal(registry, "ARMOR-SERVER", "0.8.1.7", COMMIT, signers=signers, runner=broken)
    assert reason and "could not be verified" in reason


def test_the_mode_is_off_by_default_and_comes_from_the_settings_and_the_environment(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ARMOR_UPDATER_RELEASE_REGISTRY", raising=False)
    monkeypatch.delenv("ARMOR_UPDATER_RELEASE_REGISTRY_FILE", raising=False)
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    policy = current_policy()
    assert policy.registry_required is False and policy.registry_file is None
    assert install._registry_refusal(policy, "ARMOR-SERVER", "v0.8.1.7", COMMIT) is None
    settings.save_settings(release_registry_required=True, release_registry_file="/x/releases.json")
    policy = current_policy()
    assert policy.registry_required and policy.registry_file == "/x/releases.json"
    monkeypatch.setenv("ARMOR_UPDATER_RELEASE_REGISTRY", "0")
    assert current_policy().registry_required is False


def test_the_mode_on_without_a_file_refuses(monkeypatch):
    reason = install._registry_refusal(SignaturePolicy(registry_required=True), "ARMOR-SERVER", "v0.8.1.7", COMMIT)
    assert reason and "no registry file" in reason


def test_a_damaged_settings_file_does_not_switch_the_mode_off(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ARMOR_UPDATER_RELEASE_REGISTRY", raising=False)
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    (tmp_path / "settings.json").write_text("{not json", encoding="utf-8")
    assert current_policy().registry_required is True


@needs_ssh_keygen
def test_the_install_check_strips_the_v_of_the_tag(monkeypatch, tmp_path: Path):
    registry, signers = _signed(tmp_path)
    monkeypatch.setattr(rr, "signers_file_for_tags", lambda _policy: (str(signers), None))
    policy = SignaturePolicy(registry_file=str(registry), registry_required=True)
    assert install._registry_refusal(policy, "ARMOR-SERVER", "v0.8.1.7", COMMIT) is None
    assert install._registry_refusal(policy, "ARMOR-SERVER", "v0.8.1.7", OTHER)
