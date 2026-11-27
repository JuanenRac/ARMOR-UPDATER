# =============================================================================
# ARMOR-UPDATER - tests/test_git_text_encoding.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""git writes UTF-8 whatever the code page of the console is. The tests make Python believe the console uses cp1252 (the usual one of Windows) on every system, with real
local repositories: nothing leaves the machine."""
from __future__ import annotations

import json
import locale
import subprocess
from pathlib import Path

import pytest

from armor_updater import git_ops, staging
from armor_updater.registry import ProjectEntry

NAMES = {"configuración.json": "{}", "datos/mediciones_ñ.csv": "1;2", "ログ.txt": "x", "”comillas”.txt": "y"}


@pytest.fixture(autouse=True)
def _console_in_cp1252(monkeypatch):
    monkeypatch.setattr(locale, "getpreferredencoding", lambda *_args: "cp1252")
    monkeypatch.setattr(locale, "getencoding", lambda: "cp1252", raising=False)


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", "-c", "user.email=contract@example.invalid", "-c", "user.name=Contract", *args], cwd=cwd, check=True, capture_output=True)


def checkout(tmp_path: Path) -> Path:
    repo = tmp_path / "checkout"
    repo.mkdir()
    git("init", "-q", cwd=repo)
    (repo / "seguimiento_ñ.txt").write_text("base\n", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-q", "-m", "base", cwd=repo)
    return repo


def test_local_files_with_names_outside_ascii_are_carried_into_the_candidate(tmp_path: Path):
    repo = checkout(tmp_path)
    for name, content in NAMES.items():
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    staging._carry_over_local_data(repo, candidate)
    for name, content in NAMES.items():
        assert (candidate / name).is_file(), name
        assert (candidate / name).read_text(encoding="utf-8") == content, name


def test_a_changed_tracked_file_with_such_a_name_is_reported_with_its_name(tmp_path: Path):
    repo = checkout(tmp_path)
    (repo / "seguimiento_ñ.txt").write_text("changed\n", encoding="utf-8")
    assert staging._tracked_dirty_paths(repo) == ["seguimiento_ñ.txt"]


def test_a_manifest_with_text_outside_ascii_is_read_from_git(tmp_path: Path):
    repo = checkout(tmp_path)
    entry = ProjectEntry("ARMOR-EXAMPLE", "python", "1.0.0")
    manifest = {
        "schema_version": "1.0", "ecosystem": "A.R.M.O.R.", "name": entry.name, "version": "1.0.0", "role": "service", "stack": "python", "technologies": ["Python"],
        "deployment_target": "The central server", "maturity": "functional", "family": "Test", "parent": None, "native_version": "1.0.0", "build": "python -m compileall src",
        "notes": "Señal, Ü, 日本語の説明, 中文说明, ”quoted”",
    }
    (repo / "armor.project.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    git("add", "armor.project.json", cwd=repo)
    git("commit", "-q", "-m", "manifiesto ”日本”", cwd=repo)
    read = git_ops._manifest_from_revision(repo, "HEAD", entry)
    assert read.version == "1.0.0"
    result = git_ops._run(["git", "log", "-1", "--format=%s"], cwd=repo, capture_output=True)
    assert result.stdout.strip() == "manifiesto ”日本”"
