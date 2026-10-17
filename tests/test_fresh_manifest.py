# =============================================================================
# ARMOR-UPDATER - tests/test_fresh_manifest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A manifest is read without the stale cache of raw.githubusercontent.com: through the contents API when there is a token, and at the exact commit of the branch (found with
`git ls-remote`) when there is not; the branch URL of raw is only the fallback."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from armor_updater import github_client
from armor_updater.github_client import _fetch_one, _read_manifest, _remote_tip, discover_remote_projects
from armor_updater.registry import ProjectEntry
from test_github_client import fixture_server, valid_manifest

SHA = "0123456789abcdef0123456789abcdef01234567"


def body(version: str) -> bytes:
    return json.dumps(valid_manifest("ARMOR-EXAMPLE", version)).encode()


def point_at(monkeypatch, base_url: str) -> None:
    monkeypatch.setattr(github_client, "GITHUB_API_BASE", base_url)
    monkeypatch.setattr(github_client, "GITHUB_RAW_BASE", base_url)


def test_with_a_token_the_contents_api_is_read_not_the_cached_branch_url(monkeypatch):
    routes = {
        "/repos/JuanenRac/ARMOR-EXAMPLE/contents/armor.project.json?ref=main": (200, body("2.0.0")),
        "/JuanenRac/ARMOR-EXAMPLE/main/armor.project.json": (200, body("1.0.0")),   # the stale copy of the CDN
    }
    with fixture_server(routes) as base_url:
        point_at(monkeypatch, base_url)
        text, url = _read_manifest("JuanenRac", "ARMOR-EXAMPLE", "main", "token")
    assert json.loads(text)["version"] == "2.0.0"
    assert "/contents/" in url and url.endswith("?ref=main")


def test_without_a_token_the_file_is_read_at_the_commit_the_branch_points_to_now(monkeypatch):
    routes = {
        f"/JuanenRac/ARMOR-EXAMPLE/{SHA}/armor.project.json": (200, body("2.0.0")),
        "/JuanenRac/ARMOR-EXAMPLE/main/armor.project.json": (200, body("1.0.0")),   # the stale copy of the CDN
    }
    monkeypatch.setattr(github_client, "_remote_tip", lambda owner, name, branch: SHA)
    with fixture_server(routes) as base_url:
        point_at(monkeypatch, base_url)
        text, url = _read_manifest("JuanenRac", "ARMOR-EXAMPLE", "main")
    assert json.loads(text)["version"] == "2.0.0"
    assert SHA in url


def test_without_git_or_a_tip_the_branch_url_is_the_fallback(monkeypatch):
    routes = {"/JuanenRac/ARMOR-EXAMPLE/main/armor.project.json": (200, body("1.0.0"))}
    monkeypatch.setattr(github_client, "_remote_tip", lambda owner, name, branch: None)
    with fixture_server(routes) as base_url:
        point_at(monkeypatch, base_url)
        text, _url = _read_manifest("JuanenRac", "ARMOR-EXAMPLE", "main")
    assert json.loads(text)["version"] == "1.0.0"


def test_a_refused_api_call_falls_back_to_the_branch_url(monkeypatch):
    routes = {
        "/repos/JuanenRac/ARMOR-EXAMPLE/contents/armor.project.json?ref=main": (500, b"{}"),
        "/JuanenRac/ARMOR-EXAMPLE/main/armor.project.json": (200, body("1.0.0")),
    }
    monkeypatch.setattr(github_client, "RETRY_MAX_ATTEMPTS", 1)
    with fixture_server(routes) as base_url:
        point_at(monkeypatch, base_url)
        text, _url = _read_manifest("JuanenRac", "ARMOR-EXAMPLE", "main", "token")
    assert json.loads(text)["version"] == "1.0.0"


def test_a_404_is_an_answer_and_is_not_second_guessed_with_the_cache(monkeypatch):
    routes = {"/JuanenRac/ARMOR-EXAMPLE/main/armor.project.json": (200, body("1.0.0"))}   # the cache still has an old file
    with fixture_server(routes) as base_url:
        point_at(monkeypatch, base_url)
        with pytest.raises(Exception) as caught:
            _read_manifest("JuanenRac", "ARMOR-EXAMPLE", "main", "token")   # the API says there is no file at that ref
    assert getattr(caught.value, "code", None) == 404


def test_a_branch_with_a_slash_is_encoded_in_the_ref(monkeypatch):
    routes = {"/repos/JuanenRac/ARMOR-EXAMPLE/contents/armor.project.json?ref=release%2F1": (200, body("3.0.0"))}
    with fixture_server(routes) as base_url:
        point_at(monkeypatch, base_url)
        text, _url = _read_manifest("JuanenRac", "ARMOR-EXAMPLE", "release/1", "token")
    assert json.loads(text)["version"] == "3.0.0"


def test_fetch_one_and_discovery_use_the_fresh_path(monkeypatch):
    routes = {
        f"/JuanenRac/ARMOR-EXAMPLE/{SHA}/armor.project.json": (200, body("2.0.0")),
        "/JuanenRac/ARMOR-EXAMPLE/main/armor.project.json": (200, body("1.0.0")),
        "/users/JuanenRac/repos?type=owner&per_page=100&page=1": (200, json.dumps([{"name": "ARMOR-EXAMPLE", "default_branch": "main"}]).encode()),
    }
    monkeypatch.setattr(github_client, "_remote_tip", lambda owner, name, branch: SHA)
    with fixture_server(routes) as base_url:
        point_at(monkeypatch, base_url)
        status = _fetch_one(ProjectEntry("ARMOR-EXAMPLE", "python", default_branch="main"))
        discovery = discover_remote_projects()
    assert str(status.version) == "2.0.0"
    assert [str(project.version) for project in discovery.projects] == ["2.0.0"]


def test_remote_tip_reads_the_branch_of_a_real_repository(tmp_path: Path, monkeypatch):
    remote = tmp_path / "base" / "JuanenRac" / "ARMOR-EXAMPLE"
    remote.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "-C", str(remote), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    head = subprocess.check_output(["git", "-C", str(remote), "rev-parse", "HEAD"], text=True).strip()
    monkeypatch.setattr(github_client, "GITHUB_GIT_BASE", str(tmp_path / "base"))
    assert _remote_tip("JuanenRac", "ARMOR-EXAMPLE", "main") == head
    assert _remote_tip("JuanenRac", "ARMOR-EXAMPLE", "no-such-branch") is None
    assert _remote_tip("JuanenRac", "NoSuchRepository", "main") is None
