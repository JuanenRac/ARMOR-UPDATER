# =============================================================================
# ARMOR-UPDATER - tests/test_integration_environment.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""An end-to-end install of a project whose build-test makes a virtual environment, from a local git repository: the environment made in the staging folder cannot be moved, so
the updater removes it and the project's own build script makes it again in the final place."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from armor_updater import install
from armor_updater.install import clone_or_pull
from test_install import entry, git, write_manifest


def _scripts(seed: Path) -> None:
    python = sys.executable
    (seed / "build-test.sh").write_text(f'#!/usr/bin/env bash\n"{python}" -m venv --without-pip .venv\n', encoding="utf-8")
    (seed / "build.sh").write_text(f'#!/usr/bin/env bash\n"{python}" -m venv --without-pip .venv\n', encoding="utf-8")
    (seed / "build-test.bat").write_text(f'@echo off\r\n"{python}" -m venv --without-pip .venv\r\nexit /b %ERRORLEVEL%\r\n', encoding="utf-8")
    (seed / "build.bat").write_text(f'@echo off\r\n"{python}" -m venv --without-pip .venv\r\nexit /b %ERRORLEVEL%\r\n', encoding="utf-8")


def test_a_project_that_builds_an_environment_ends_with_one_made_in_its_final_place(tmp_path: Path, monkeypatch):
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    _scripts(seed)
    (seed / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v1", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))

    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace)

    assert result.ok, result.message + result.output
    project = workspace / entry().name
    config = (project / ".venv" / "pyvenv.cfg")
    assert config.is_file(), "the environment was not made again in the final place"
    assert not list(workspace.glob(f".{entry().name}.clone-*")), "no staging folder is left"
    # the environment works from where it is
    interpreter = project / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    assert subprocess.run([str(interpreter), "-c", "print(1)"], capture_output=True, text=True).stdout.strip() == "1"
