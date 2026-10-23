# =============================================================================
# ARMOR-UPDATER - Optional "releases + current link" layout: releases.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""An optional way to lay out an installed project, chosen with `"deploy_layout": "releases"` in `~/.armor_updater_settings.json` (or `ARMOR_UPDATER_LAYOUT=releases`).

The default layout (`"checkout"`) is the one the updater has always used: `<workspace>/<project>` is the checkout, a candidate is built in a staging folder and moved into place
with two renames. Its weak point is that a build that bakes absolute paths (a virtual environment, an editable install) was made in the staging folder and has to be made again in
the final place.

In the `releases` layout `<workspace>/<project>` is a LINK (a symbolic link, or a junction on Windows) to a folder
`<workspace>/.armor-updater/releases/<project>/<commit>/`. A candidate is cloned and built directly in its final folder, so nothing has to be rebuilt afterwards, and it is put in
service by switching the link: the previous release stays on disk untouched, so going back is one more switch of the link (`rollback`).

Safeguards:
* the default stays `checkout`; nothing changes unless the person asks for it;
* a failed clone or build deletes only its own new release folder and never touches the link or the release in service;
* the first switch of a project that is a real checkout moves that checkout to `releases/<project>/<commit>/` (journalled, undone by the next run after a crash) and, if the link
  cannot be made, moves it back;
* ARMOR-UPDATER itself is never moved to this layout by an update (the running program would change folders under its own feet): it keeps the checkout flow;
* only the newest few releases are kept, and never the one in service.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .console_flags import NO_WINDOW
from .promotion import Promotion, state_directory
from .settings import load_settings
from .staging import _rmtree_best_effort

LAYOUT_CHECKOUT = "checkout"
LAYOUT_RELEASES = "releases"
RELEASES_DIRECTORY = "releases"
#: How many releases of a project are kept (the one in service included).
DEFAULT_KEEP_RELEASES = 3
#: The updater never moves itself to the releases layout.
SELF_PROJECT = "ARMOR-UPDATER"


def current_layout() -> str:
    """`checkout` (the default) or `releases`. The environment wins over the saved settings; anything unknown means `checkout`."""
    chosen = os.environ.get("ARMOR_UPDATER_LAYOUT", "").strip().lower() or str(load_settings().get("deploy_layout", "")).strip().lower()
    return LAYOUT_RELEASES if chosen == LAYOUT_RELEASES else LAYOUT_CHECKOUT


def wants_releases(project: str) -> bool:
    return current_layout() == LAYOUT_RELEASES and project != SELF_PROJECT


def releases_directory(workspace_root: Path, project: str) -> Path:
    return state_directory(workspace_root) / RELEASES_DIRECTORY / project


def release_path(workspace_root: Path, project: str, commit: str) -> Path:
    return releases_directory(workspace_root, project) / commit[:12]


def link_target(path: Path) -> Path | None:
    """Where the link at `path` points, or None when `path` is not a link (a real folder, or missing). Works for symbolic links and Windows junctions."""
    try:
        target = os.readlink(path)
    except (OSError, ValueError):
        return None
    if target.startswith("\\\\?\\"):   # Windows returns the extended-length form of a junction's target
        target = target[4:]
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = path.parent / target_path
    return target_path


def make_link(link: Path, target: Path) -> None:
    """Creates `link` pointing at the folder `target`: a junction on Windows (no administrator rights needed), a symbolic link elsewhere."""
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True, creationflags=NO_WINDOW)
        if result.returncode != 0:
            raise OSError((result.stdout + result.stderr).strip() or "mklink /J failed")
    else:
        os.symlink(target, link, target_is_directory=True)


def _remove_link(link: Path) -> None:
    if os.name == "nt":
        os.rmdir(link)   # removes the junction only, never what it points at
    else:
        link.unlink()


def switch_link(link: Path, target: Path) -> None:
    """Points the existing link `link` at `target`. A new link is made beside it first; on POSIX the switch is one atomic rename, on Windows the old junction is removed and the new
    one renamed in its place (a window of two operations; the next run finishes it, see `heal_link`)."""
    fresh = link.with_name(f".{link.name}.link-new")
    if link_target(fresh) is not None:
        _remove_link(fresh)
    make_link(fresh, target)
    if os.name == "nt":
        _remove_link(link)
        os.rename(fresh, link)
    else:
        os.replace(fresh, link)


def heal_link(workspace_root: Path) -> list[str]:
    """Finishes a link switch a crash cut in two on Windows: the project's link is missing and the new one waits beside it."""
    actions: list[str] = []
    for fresh in workspace_root.glob(".*.link-new"):
        name = fresh.name[1:-len(".link-new")]
        link = workspace_root / name
        if link_target(fresh) is not None and not link.exists() and link_target(link) is None:
            try:
                os.rename(fresh, link)
                actions.append(f"{name}: an interrupted switch of the release in service was finished")
            except OSError:
                pass
    return actions


def list_releases(workspace_root: Path, project: str) -> list[Path]:
    """The release folders of a project, the newest first."""
    directory = releases_directory(workspace_root, project)
    if not directory.is_dir():
        return []
    return sorted((p for p in directory.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)


def in_service(workspace_root: Path, project: str) -> Path | None:
    """The release the project's link points at, when the project is in the releases layout."""
    target = link_target(workspace_root / project)
    if target is None:
        return None
    try:
        target.resolve().relative_to(releases_directory(workspace_root, project).resolve())
    except ValueError:
        return None
    return target


def prune_releases(workspace_root: Path, project: str, keep: int = DEFAULT_KEEP_RELEASES) -> list[Path]:
    """Deletes all but the newest `keep` releases of a project, never the one in service. Returns the ones deleted."""
    serving = in_service(workspace_root, project)
    serving_resolved = serving.resolve() if serving is not None else None
    removed: list[Path] = []
    kept = 0
    for release in list_releases(workspace_root, project):
        if serving_resolved is not None and release.resolve() == serving_resolved:
            kept += 1
            continue
        if kept < keep:
            kept += 1
            continue
        _rmtree_best_effort(release)
        removed.append(release)
    return removed


def activate(workspace_root: Path, project: str, path: Path, new_release: Path, journal, commit_of_current: str | None) -> Path | None:  # noqa: ANN001 - PromotionJournal
    """Puts `new_release` in service at `path`. When `path` is a link it is switched; when it is a real checkout that checkout is moved to its own release folder first. Returns the
    folder the previous installation is in now (None for a first install). Raises OSError after undoing what it had done when the link could not be made."""
    previous_link = link_target(path)
    if previous_link is not None:
        switch_link(path, new_release)
        return previous_link
    if not path.exists():
        make_link(path, new_release)
        return None
    commit = commit_of_current or "unknown"
    moved = release_path(workspace_root, project, commit)
    number = 2
    while moved.exists():
        moved = releases_directory(workspace_root, project) / f"{commit[:12]}-{number}"
        number += 1
    moved.parent.mkdir(parents=True, exist_ok=True)
    journal.begin(Promotion(project, str(path), str(new_release), str(moved), "begun"))
    path.rename(moved)
    journal.advance("backed_up")
    try:
        make_link(path, new_release)
    except OSError:
        moved.rename(path)
        journal.complete()
        raise
    journal.advance("promoted")
    journal.complete()
    return moved


def verify_in_service(workspace_root: Path, project: str, release: Path, expected_commit: str) -> str | None:
    """The check made right after a link was switched, on what a program will really meet: the project's path leads to the new release, its manifest is there and can be read, and the
    commit that is checked out is the one that was built. Returns what is wrong in one sentence, or None when all is well."""
    link = workspace_root / project
    target = link_target(link)
    if target is None:
        return "the project's path is not a link to a release"
    try:
        if target.resolve() != release.resolve():
            return "the project's path leads to another release than the new one"
    except OSError as exc:
        return f"the new release cannot be reached ({exc})"
    manifest = link / "armor.project.json"
    try:
        document = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"the manifest of the new release cannot be read ({exc.__class__.__name__})"
    if not isinstance(document, dict) or not isinstance(document.get("version"), str):
        return "the manifest of the new release has no version"
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=link, capture_output=True, text=True, creationflags=NO_WINDOW, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "the commit of the new release cannot be read"
    if expected_commit and not head.startswith(expected_commit[:12]):
        return "the new release is not at the commit that was built"
    return None


def revert_to(workspace_root: Path, project: str, previous: Path | None, new_release: Path) -> str:
    """Undoes a switch whose check failed: the link goes back to the release that was in service, or - for a project that had none - the link is removed. The release that failed is
    deleted either way. Returns what was done, in one sentence."""
    link = workspace_root / project
    if previous is not None and previous.is_dir():
        switch_link(link, previous)
        what = f"{project} is back on the release it was on ({previous.name})"
    else:
        if link_target(link) is not None:
            _remove_link(link)
        what = f"{project} was not put in service"
    _rmtree_best_effort(new_release)
    return what


def go_back(workspace_root: Path, project: str) -> str:
    """Switches the link of `project` to the newest release that is not the one in service. Raises RuntimeError when there is none."""
    serving = in_service(workspace_root, project)
    if serving is None:
        raise RuntimeError(f"{project} is not in the releases layout")
    others = [r for r in list_releases(workspace_root, project) if r.resolve() != serving.resolve()]
    if not others:
        raise RuntimeError(f"{project} has no previous release to go back to")
    switch_link(workspace_root / project, others[0])
    return f"{project}: the release {others[0].name} is back in service (the one it replaces, {serving.name}, is kept)"
