# =============================================================================
# ARMOR-UPDATER - tests/test_fetch_all.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The concurrent reading of the repositories' manifests: one that fails never takes the others with it, progress is reported, and the token is the one given or the environment's.
The single reading of one repository is replaced: nothing here asks GitHub."""
from __future__ import annotations

import pytest

from armor_updater import github_client
from armor_updater.github_client import RemoteStatus, fetch_all
from armor_updater.registry import ProjectEntry
from armor_updater.version_parse import Version


def entries(*names: str) -> list[ProjectEntry]:
    return [ProjectEntry(name=name, stack="python") for name in names]


def test_nothing_to_read_is_nothing_read(monkeypatch):
    monkeypatch.setattr(github_client, "_fetch_one", lambda entry, token: pytest.fail("nothing should be fetched"))
    assert fetch_all([]) == {}


def test_every_project_gets_its_own_result(monkeypatch):
    monkeypatch.setattr(github_client, "_fetch_one", lambda entry, token: RemoteStatus(entry=entry, version=Version(1, 2, 3)))
    results = fetch_all(entries("ARMOR-A", "ARMOR-B", "ARMOR-C"), token="t")
    assert sorted(results) == ["ARMOR-A", "ARMOR-B", "ARMOR-C"]
    assert all(status.version == Version(1, 2, 3) for status in results.values())


def test_a_worker_that_blows_up_becomes_an_error_of_that_project_only(monkeypatch):
    def fetch(entry, token):
        if entry.name == "ARMOR-BAD":
            raise ValueError("boom")
        return RemoteStatus(entry=entry, version=Version(0, 1, 0))
    monkeypatch.setattr(github_client, "_fetch_one", fetch)
    results = fetch_all(entries("ARMOR-OK", "ARMOR-BAD", "ARMOR-ALSO-OK"), token="t")
    assert results["ARMOR-OK"].version == Version(0, 1, 0) and results["ARMOR-ALSO-OK"].version == Version(0, 1, 0)
    bad = results["ARMOR-BAD"]
    assert bad.version is None and "worker failure: ValueError: boom" in bad.error
    assert "ARMOR-BAD" in bad.url and bad.url.endswith("armor.project.json")


def test_the_url_of_a_failed_project_uses_its_own_default_branch(monkeypatch):
    def fetch(entry, token):
        raise RuntimeError("down")
    monkeypatch.setattr(github_client, "_fetch_one", fetch)
    entry = ProjectEntry(name="ARMOR-TRUNK", stack="python", default_branch="trunk")
    assert "/trunk/" in fetch_all([entry], token="t")["ARMOR-TRUNK"].url


def test_progress_is_reported_once_per_project_and_ends_at_the_total(monkeypatch):
    monkeypatch.setattr(github_client, "_fetch_one", lambda entry, token: RemoteStatus(entry=entry, version=None, error="x"))
    seen: list[tuple[int, int]] = []
    fetch_all(entries("ARMOR-A", "ARMOR-B", "ARMOR-C", "ARMOR-D"), progress=lambda done, total: seen.append((done, total)), token="t")
    assert sorted(seen) == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_the_token_given_wins_over_the_environment_and_the_environment_over_nothing(monkeypatch):
    tokens: list[str] = []
    monkeypatch.setattr(github_client, "_fetch_one", lambda entry, token: tokens.append(token) or RemoteStatus(entry=entry, version=None))
    monkeypatch.setenv("GITHUB_TOKEN", "from-environment")
    fetch_all(entries("ARMOR-A"), token="given")
    fetch_all(entries("ARMOR-A"))
    monkeypatch.delenv("GITHUB_TOKEN")
    fetch_all(entries("ARMOR-A"))
    fetch_all(entries("ARMOR-A"), token="")
    assert tokens == ["given", "from-environment", "", ""]
