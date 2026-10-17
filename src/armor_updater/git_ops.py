# =============================================================================
# ARMOR-UPDATER - Running git and reading a revision: git_ops.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Running a child process without ever raising, and reading the manifest or the branch of a checkout through git."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .project_manifest import ManifestValidationError, ProjectManifest, parse_manifest
from .registry import ProjectEntry


def _run(
    cmd: list[str], cwd: Path, *, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, object] = {"cwd": str(cwd), "check": False}
    if capture_output:
        kwargs.update({"capture_output": True, "text": True})
    # The GUI is started with pythonw on Windows. Do not let git or a child build script create a surprise console while its output is captured for the in-window checkpoint log.
    if capture_output and os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    if os.name == "nt":
        # Ecosystem .bat files finish with `pause` when an operator double-clicks them. Here they run as a child, so give them one harmless newline and never leave a hidden child
        # waiting for a keypress (also without a captured output: the Tk window starts them too).
        kwargs["input"] = "\n"
        kwargs.setdefault("text", True)
    else:
        kwargs["stdin"] = subprocess.DEVNULL
    try:
        return subprocess.run(cmd, **kwargs)  # type: ignore[arg-type]
    except OSError as error:   # git or the shell is not there, the folder is not usable
        return subprocess.CompletedProcess(cmd, 127, stdout="", stderr=f"{type(error).__name__}: {error}")


def _command_output(result: subprocess.CompletedProcess[str]) -> str:
    """Compact child evidence when a GUI captured it: the full command output stays in the process result while the desktop surface keeps a bounded, readable activity trace."""
    return "\n".join(part for part in (result.stdout, result.stderr) if part).strip()


def _rev_parse(path: Path, revision: str) -> str:
    return subprocess.run(["git", "rev-parse", revision], cwd=str(path), check=False, capture_output=True, text=True).stdout.strip()


def _validated_manifest_text(text: str, entry: ProjectEntry) -> ProjectManifest:
    """The repository-owned manifest used as an update precondition: the revision must still identify itself as the selected project."""
    return parse_manifest(text, expected_name=entry.name)


def _manifest_from_revision(path: Path, revision: str, entry: ProjectEntry) -> ProjectManifest:
    """Read a manifest from Git without modifying the working tree."""
    result = subprocess.run(
        ["git", "show", f"{revision}:armor.project.json"],
        cwd=str(path),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ManifestValidationError("candidate revision has no readable armor.project.json")
    return _validated_manifest_text(result.stdout, entry)


def _wrong_branch_message(path: Path, entry: ProjectEntry) -> str:
    """A message when the checkout sits on a branch other than the repository's default one (the update fetches the remote default branch, so merging it there would mix
    branches), else an empty string. A detached HEAD, or a default branch that cannot be told, is not refused."""
    current = _run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=path, capture_output=True)
    if current.returncode != 0:
        return ""
    branch = (current.stdout or "").strip()
    expected = ""
    remote_head = _run(["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd=path, capture_output=True)
    if remote_head.returncode == 0:
        expected = (remote_head.stdout or "").strip().removeprefix("origin/")
    expected = expected or entry.default_branch
    if branch and expected and branch != expected:
        return f"{path} is on branch '{branch}', not the default branch '{expected}' - switch back to '{expected}' before updating"
    return ""
