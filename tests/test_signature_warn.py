# =============================================================================
# ARMOR-UPDATER - tests/test_signature_warn.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The default signature policy is "warn": an unsigned revision is installed or updated, and the result says that it is not signed (in the window, in the language chosen).
"Require" stays available in the settings and by environment variable."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from armor_updater import i18n, install, settings
from armor_updater.install import clone_or_pull
from armor_updater.result_text import localized_message
from armor_updater.signature import current_policy, unsigned_reason, SignaturePolicy
from test_install import entry, git, write_manifest
from test_signature import _remote_with_one_commit, _signing_key, needs_ssh_keygen


def test_the_default_policy_is_warn(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ARMOR_UPDATER_REQUIRE_SIGNED", raising=False)
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    policy = current_policy()
    assert policy.required is False and policy.mode == "warn"


def test_require_can_be_chosen_in_the_settings_both_ways(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ARMOR_UPDATER_REQUIRE_SIGNED", raising=False)
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_PATH", path)
    path.write_text(json.dumps({"signature_policy": "require"}), encoding="utf-8")
    assert current_policy().mode == "require"
    path.write_text(json.dumps({"require_signed_commits": True}), encoding="utf-8")
    assert current_policy().mode == "require"
    path.write_text(json.dumps({"signature_policy": "warn"}), encoding="utf-8")
    assert current_policy().mode == "warn"


def test_an_unreadable_settings_file_still_fails_closed(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("ARMOR_UPDATER_REQUIRE_SIGNED", raising=False)
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(settings, "SETTINGS_PATH", path)
    assert current_policy().mode == "require"


def test_unsigned_reason_does_not_depend_on_the_mode(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_commit(tmp_path, signing_key=None)
    clone = tmp_path / "clone"
    git("clone", str(remote), str(clone), cwd=tmp_path)
    assert unsigned_reason(clone, "HEAD", SignaturePolicy(required=False)) is not None


def test_an_unsigned_fresh_install_goes_ahead_and_says_it_is_not_signed(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_commit(tmp_path, signing_key=None)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok, result.message
    assert (workspace / entry().name / "armor.project.json").is_file()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace / entry().name, text=True).strip()
    assert result.unsigned == commit[:12]
    assert "not signed" in result.message and "WARNING" in result.message


def test_the_warning_is_said_in_every_language(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_commit(tmp_path, signing_key=None)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)
    texts = set()
    for code, _label in i18n.LANGUAGES:
        text = localized_message(code, result)
        assert result.unsigned in text and entry().name in text and "{" not in text
        texts.add(text)
    assert len(texts) == len(i18n.LANGUAGES)
    # the English sentence is not repeated in front of the translation
    assert "WARNING: revision" not in localized_message("es", result)


def test_require_still_refuses_an_unsigned_revision_and_says_why_in_the_language(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_commit(tmp_path, signing_key=None)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_REQUIRE_SIGNED", "1")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert not result.ok and result.code == "signature_refused" and result.unsigned == ""
    assert entry().name in localized_message("pt", result)
    assert list(workspace.iterdir()) == []


def test_an_unsigned_update_goes_ahead_with_the_warning(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_commit(tmp_path, signing_key=None)
    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    seed = tmp_path / "seed"
    write_manifest(seed, "1.1.0")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v2 unsigned", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    result = clone_or_pull(entry(), tmp_path, verify_build=False)
    assert result.ok, result.message
    assert result.unsigned and "not signed" in result.message
    assert json.loads((local / "armor.project.json").read_text(encoding="utf-8"))["version"] == "1.1.0"


def test_an_update_that_changes_nothing_does_not_warn(tmp_path: Path, monkeypatch):
    remote = _remote_with_one_commit(tmp_path, signing_key=None)
    local = tmp_path / entry().name
    git("clone", str(remote), str(local), cwd=tmp_path)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    result = clone_or_pull(entry(), tmp_path, verify_build=False)
    assert result.ok and result.unsigned == ""


@needs_ssh_keygen
def test_a_signed_revision_installs_without_a_warning(tmp_path: Path, monkeypatch):
    key, allowed = _signing_key(tmp_path)
    remote = _remote_with_one_commit(tmp_path, signing_key=key)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    monkeypatch.setenv("ARMOR_UPDATER_ALLOWED_SIGNERS", str(allowed))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok, result.message
    assert result.unsigned == "" and "WARNING" not in result.message
