# =============================================================================
# ARMOR-UPDATER - Staging folders: cleanup, local data, environments: staging.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""What the updater does with the folders it builds in: reporting progress, removing a folder it made, carrying the local data of a checkout into the candidate and removing what a build makes that cannot be moved."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from shutil import copy2, copytree, rmtree
from typing import Callable
from .console_flags import NO_WINDOW


# The GUI consumes these events to show the same real work that the CLI does. A callback is deliberately optional: command-line users retain normal child process output, while the
# GUI captures it so Windows never needs a second terminal window merely to show a project's build output.
ProgressCallback = Callable[[str, str], None]


def _checkpoint(progress: ProgressCallback | None, phase: str, message: str) -> None:
    if progress is not None:
        progress(phase, message)


#: Build output and environments that are made again by a build and must not be carried over, whatever folder of the checkout they are in.
_NEVER_CARRIED_OVER_DIR_NAMES = {
    ".git", "node_modules", "dist", "build", "target", ".venv", "venv", "env",
    "__pycache__", ".next", ".cache", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".gradle", ".kotlin", ".idea", ".dart_tool", "coverage", ".build", "build-test",
}


#: Virtual environments: a `venv` holds the absolute path it was made in (activate scripts, the first line of every script in bin/), and an editable install points at its
#: sources by absolute path, so neither survives the rename that puts the staging folder in its place.
_ENVIRONMENT_NAMES = (".venv", "venv")


def forget_build_trees(root: Path) -> None:
    """Remove the CMake build directories the candidate's build-test left in the staging clone. CMake writes absolute paths into its cache, and the clone is about to be renamed to
    its real place: a build-test run by hand there would stop with "CMakeCache.txt directory is different". They are only build output (and ignored by git), so the next build makes them again."""
    for name in ("build", "build-test", ".build"):
        tree = root / name
        if (tree / "CMakeCache.txt").is_file():
            rmtree(tree, ignore_errors=True)


def remove_generated_environments(root: Path) -> bool:
    """Removes the virtual environments (and the metadata of editable installs) the build-test made in the staging clone: they cannot be moved. True when there was one, which tells
    the caller to make the environment again in the final place."""
    removed = False
    for name in _ENVIRONMENT_NAMES:
        tree = root / name
        if tree.is_dir():
            _rmtree_best_effort(tree)
            removed = True
    if removed:
        for pattern in ("*.egg-info", "src/*.egg-info", "__editable__*"):
            for leftover in root.glob(pattern):
                if leftover.is_dir():
                    _rmtree_best_effort(leftover)
                else:
                    try:
                        leftover.unlink()
                    except OSError:
                        pass
    return removed


def _make_writable_and_retry(function, target, _excinfo) -> None:  # noqa: ANN001 - the signature of shutil's error callback
    """git leaves its object files read-only, which Windows refuses to delete: make the file writable and try again."""
    try:
        os.chmod(target, 0o700)
        function(target)
    except OSError:
        pass


def _rmtree_best_effort(path: Path) -> None:
    """Removes a folder this module created and no longer needs, tolerating a Windows rough edge: a child process (git, or a project's own build-test) can leave a file handle open for
    a brief moment after it has exited. Retries a few times instead of raising: this is always best-effort cleanup of our own temporary folder, never something that should fail the
    caller's real result."""
    for attempt in range(5):
        try:
            if sys.version_info >= (3, 12):
                rmtree(path, onexc=_make_writable_and_retry)
            else:
                rmtree(path, onerror=_make_writable_and_retry)
            if not path.exists():
                return
            raise PermissionError(str(path))
        except FileNotFoundError:
            return
        except OSError:
            if attempt == 4:
                return
            time.sleep(0.2)


def _real_untracked_paths(path: Path) -> list[str]:
    """Every path (relative to `path`) git considers untracked or ignored (`??`/`!!`): the local data that `git clone --local` never copies (it only copies the committed objects).
    A modified TRACKED file is never included - that already blocks the update separately."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--ignored", "-uall", "-z"],
        cwd=str(path), check=False, capture_output=True, text=True, creationflags=NO_WINDOW,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    paths: list[str] = []
    for entry in result.stdout.split("\0"):
        if len(entry) < 4:
            continue
        status_code, rel_path = entry[:2], entry[3:]
        if status_code in ("??", "!!"):
            paths.append(rel_path)
    return paths


class DirtyCheckError(RuntimeError):
    """`git status` itself failed to run against a checkout (not a git repository, git missing, a permissions error): not being able to verify clean is not the same as clean."""


def _tracked_dirty_paths(path: Path) -> list[str]:
    """Every path git considers a TRACKED file with an uncommitted change. Checked upfront because the staging clone only copies the committed objects: a local edit to a tracked file
    would be invisible to it, the build would pass, and the promotion would move the edit away to a backup while reporting success."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "-z"],
        cwd=str(path), check=False, capture_output=True, text=True, creationflags=NO_WINDOW,
    )
    if result.returncode != 0:
        raise DirtyCheckError(
            f"could not verify {path} has no uncommitted changes - `git status` itself failed "
            f"(exit {result.returncode}): {result.stderr.strip() or '(no stderr)'}"
        )
    if not result.stdout:
        return []
    paths: list[str] = []
    for entry_text in result.stdout.split("\0"):
        if len(entry_text) < 4:
            continue
        status_code, rel_path = entry_text[:2], entry_text[3:]
        if status_code in ("??", "!!"):
            continue
        paths.append(rel_path)
    return paths


def _carry_over_local_data(old_path: Path, staging_path: Path, *, progress: ProgressCallback | None = None) -> None:
    """Copies the untracked/ignored data of `old_path` (a project's own settings, users, database, certificates kept inside its checkout) into `staging_path` before the candidate
    is built or promoted. Anything that has a build-output or environment folder among the components of its path is left out, however deep it is (`app/build`, `.gradle`, a
    nested `node_modules`): a build makes them again, and carrying them over would make the verified build reuse stale artifacts."""
    carried = 0
    for rel_path in _real_untracked_paths(old_path):
        if any(part in _NEVER_CARRIED_OVER_DIR_NAMES for part in Path(rel_path).parts):
            continue
        source = old_path / rel_path
        if not source.exists():
            continue  # removed between `git status` and now
        destination = staging_path / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            copytree(source, destination, dirs_exist_ok=True)
        else:
            copy2(source, destination)
        carried += 1
    if carried:
        _checkpoint(
            progress, "validation",
            f"Carried {carried} local data file(s)/director(y/ies) from the installed checkout into the verified candidate.",
        )
