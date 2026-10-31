# =============================================================================
# ARMOR-UPDATER - Clone/pull + delegate to each project's own build
# script: install.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Deliberately does NOT reimplement per-stack build logic (npm, cargo, gradlew, flutter, pip, ESP-IDF, CMake...). Every project carries the common non-versioning
# build-test.sh/.bat entry point, which delegates to its own stack-aware check without incrementing a manifest or CHANGELOG, so fleet maintenance cannot manufacture a release merely
# by refreshing a checkout. Versioned build scripts remain an explicit human release action and are never selected here. This module's job ends at "clone/pull the source, run
# whichever build script this checkout has, and put the result in place without ever leaving the project without a working folder".
#
# What it guarantees (and what it does not):
#   * a new project and an update are both built in a staging folder first; the live folder is not touched until the build passes;
#   * the promotion is two renames, journalled on disk (promotion.py) so that a crash between them is healed at the next run; the replaced checkout is kept as a backup under
#     <workspace>/.armor-updater/backups/<project>/ (the newest few, `rollback` puts the newest back);
#   * only one updater works on a workspace at a time (a lock file);
#   * an update to the commit already installed does nothing;
#   * local data kept inside a checkout (ignored or untracked files) is carried into the candidate, except what a build makes again.
# It does NOT make a rename atomic with respect to a process that is running from the folder, and a project whose build leaves absolute paths in places this module does not know
# (it removes the CMake trees and the virtual environments) may need its own build run once in the final place.
#
# The work is split by what it touches: git_ops.py (running git, reading a revision), staging.py (the folders it builds in), promotion.py (the lock, the journal, the backups) and this
# module (the decisions: what to install, in which order, what to refuse).
# =============================================================================
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .evidence import installed_state, record_attempt
from .git_ops import (
    _command_output,
    _manifest_from_revision,
    _rev_parse,
    _run,
    _wrong_branch_message,
)
from .project_manifest import ManifestValidationError, ProjectManifest
from .promotion import (
    DEFAULT_KEEP,
    Promotion,
    PromotionJournal,
    WorkspaceBusy,
    WorkspaceLock,
    disk_used,
    list_backups,
    new_backup_path,
    prune_backups,
    recover_interrupted_promotion,
    rollback,
)
from .registry import ProjectEntry, github_repo_url
from .staging import (
    DirtyCheckError,
    ProgressCallback,
    _carry_over_local_data,
    _checkpoint,
    _rmtree_best_effort,
    _tracked_dirty_paths,
    forget_build_trees,
    remove_generated_environments,
)
from .releases import chosen_layout, activate as activate_release, go_back, heal_link, in_service, prune_releases, release_path, revert_to, verify_in_service, wants_releases, DEFAULT_KEEP_RELEASES
from .signature import current_policy, unsigned_reason, verify_range, verify_revision

#: Every project's build-test.sh runs ../ARMOR-COMMON/scripts/armor-project.sh: without that checkout next to it nothing builds.
COMMON_PROJECT = "ARMOR-COMMON"


def recover_interrupted_promotions(workspace_root: Path) -> list[str]:
    """Heals a promotion that a crash, a kill or a power cut left half done (see promotion.py). Returns what it did."""
    return recover_interrupted_promotion(workspace_root) + heal_link(workspace_root)


def install_order(entries: Iterable[ProjectEntry]) -> list[ProjectEntry]:
    """The order to install or update several projects in: ARMOR-COMMON first (every build needs it), then every project a manifest `requires` or names as `parent` before the
    project that needs it, then by name. A requirement that is not part of the batch is left to the check that refuses the project when it is not installed."""
    items = sorted(entries, key=lambda e: e.name.casefold())
    by_name = {e.name: e for e in items}
    ordered: list[ProjectEntry] = []
    placed: set[str] = set()

    def place(entry: ProjectEntry, trail: tuple[str, ...] = ()) -> None:
        if entry.name in placed or entry.name in trail:
            return
        before = ([entry.parent] if entry.parent else []) + list(entry.requires)
        for name in before:
            if name in by_name and name != entry.name:
                place(by_name[name], trail + (entry.name,))
        ordered.append(entry)
        placed.add(entry.name)

    for entry in items:
        if entry.name == COMMON_PROJECT:
            place(entry)
    for entry in items:
        place(entry)
    return ordered


def missing_requirements(workspace_root: Path, requires: Iterable[str]) -> list[str]:
    """The required projects that are not installed (a folder of that name) in the workspace."""
    return [name for name in requires if not (workspace_root / name).is_dir()]


def requirements_refusal(entry_name: str, workspace_root: Path, requires: Iterable[str]) -> "InstallResult | None":
    """A failed result when a project listed in `requires` is not installed, else None. The code and parameters let a window say it in the language of the person."""
    missing = missing_requirements(workspace_root, requires)
    if not missing:
        return None
    names = ", ".join(missing)
    return InstallResult(
        False,
        f"{entry_name} requires {names}, which {'is' if len(missing) == 1 else 'are'} not installed in {workspace_root}: install {'it' if len(missing) == 1 else 'them'} first "
        "(an ordered batch does it on its own)",
        code="requires_missing",
        params={"project": entry_name, "missing": names, "workspace": str(workspace_root)},
    )









BUILD_TEST_SCRIPT_POSIX = "build-test.sh"
BUILD_TEST_SCRIPT_WINDOWS = "build-test.bat"
BUILD_SCRIPT_POSIX = "build.sh"
BUILD_SCRIPT_WINDOWS = "build.bat"



@dataclass
class InstallResult:
    ok: bool
    message: str
    output: str = ""
    #: A short, stable name of the situation (for example "requires_missing") and its values: a window turns them into a sentence in the language of the person.
    code: str = ""
    params: dict[str, str] = field(default_factory=dict)
    #: The commit (short) of an installed revision that carried no valid signature. Empty when it was signed or the check could not be made.
    unsigned: str = ""




















def _version_tuple(manifest: ProjectManifest) -> tuple[int, int, int, int]:
    parts = [int(part) for part in manifest.version.split(".")]
    parts += [0] * (4 - len(parts))  # a missing fourth component compares as 0
    return tuple(parts)  # type: ignore[return-value]






def _rebuild_environment(path: Path, progress: ProgressCallback | None) -> InstallResult:
    """Makes the virtual environment again in the final place (the project's own build.sh/.bat is the script that makes it)."""
    name = BUILD_SCRIPT_WINDOWS if os.name == "nt" else BUILD_SCRIPT_POSIX
    script = path / name
    if not script.is_file():
        return InstallResult(True, f"no {name} to make the environment of {path.name} again; run its own set-up once")
    _checkpoint(progress, "build", f"Making the environment of {path.name} again in its final place with {name}.")
    cmd = ["cmd", "/c", str(script)] if os.name == "nt" else ["bash", str(script)]
    result = _run(cmd, cwd=path, capture_output=progress is not None)
    if result.returncode != 0:
        return InstallResult(False, f"{name} exited with code {result.returncode}: run it again in {path} to make the environment", _command_output(result))
    return InstallResult(True, f"{name} made the environment again", _command_output(result))


def _promote(entry: ProjectEntry, workspace_root: Path, path: Path, staging_path: Path, commit: str, progress: ProgressCallback | None) -> InstallResult | tuple[Path | None]:
    """The two renames that put `staging_path` in place of `path` (when there is one), journalled. Returns an InstallResult when it failed, else the backup folder (None for a new
    project)."""
    journal = PromotionJournal(workspace_root)
    backup_path: Path | None = None
    if path.exists():
        backup_path = new_backup_path(workspace_root, entry.name, _rev_parse(path, "HEAD") or None)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
    journal.begin(Promotion(entry.name, str(path), str(staging_path), str(backup_path or ""), "begun"))
    _checkpoint(progress, "validation", "Promoting the verified candidate; the previous installation is kept as a backup.")
    if backup_path is not None:
        try:
            path.rename(backup_path)
        except OSError as exc:
            journal.complete()
            _rmtree_best_effort(staging_path)
            return InstallResult(
                False,
                f"could not move the installed checkout aside ({exc}) - a program may have a file of {path} open (an editor, a service that runs from it): close it and try again; "
                f"{path} was left as it was",
            )
        journal.advance("backed_up")
    try:
        staging_path.rename(path)
    except OSError as exc:
        if backup_path is not None:
            try:
                backup_path.rename(path)
            except OSError:
                return InstallResult(
                    False,
                    f"promotion failed AND the restore also failed - {path} may not exist right now; the previous installation is at {backup_path}: {exc}",
                )
        journal.complete()
        return InstallResult(
            False,
            f"promotion failed ({exc}) - the previous installation is back in {path}; the verified candidate is still at {staging_path} for inspection",
        )
    journal.advance("promoted")
    journal.complete()
    return (backup_path,)




def _unsigned_commit(repo: Path, revision: str, policy) -> str:   # noqa: ANN001 - SignaturePolicy
    """The short commit of `revision` when it carries no valid signature and the policy only warns (a strict policy has already refused it), else an empty string."""
    if policy.required or unsigned_reason(repo, revision, policy) is None:
        return ""
    return (_rev_parse(repo, revision) or revision)[:12]


def _note_unsigned(result: InstallResult, unsigned: str, project: str) -> InstallResult:
    """Says on a successful result that the installed revision was not signed (the default policy installs it anyway; the window and the command show this sentence)."""
    if unsigned:
        result.unsigned = unsigned
        result.params = {**result.params, "project": project, "commit": unsigned}
        result.message += f"; WARNING: revision {unsigned} of {project} is not signed (or its signature could not be verified); it was installed because the signature policy is 'warn'"
    return result


def _activate_release(entry: ProjectEntry, workspace_root: Path, path: Path, new_release: Path, progress: ProgressCallback | None, *, migrating: bool = False) -> InstallResult | tuple[Path | None]:
    """Puts a built release in service (see releases.py). Returns an InstallResult when it failed - the release in service is then the one that was - else the folder the previous
    installation is in (None for a new project)."""
    _checkpoint(progress, "validation", "Switching the project to the verified release; the previous one is kept.")
    journal = PromotionJournal(workspace_root)
    current_commit = _rev_parse(path, "HEAD") if path.exists() else None
    try:
        previous = activate_release(workspace_root, entry.name, path, new_release, journal, current_commit)
    except OSError as exc:
        _rmtree_best_effort(new_release)
        return InstallResult(False, f"could not put the new release in service ({exc}); {path} was left as it was", code="layout_unavailable" if migrating and chosen_layout() is None else "",
                             params={"project": entry.name, "reason": str(exc)})
    return (previous,)


def _check_after_switch(entry: ProjectEntry, workspace_root: Path, path: Path, new_release: Path, commit: str, previous: Path | None, progress: ProgressCallback | None) -> InstallResult | None:
    """The check right after a link was switched (see releases.verify_in_service). When it finds a problem the link goes back by itself to what it was - nobody has to notice and ask for
    it - and the result says so. None when all is well."""
    _checkpoint(progress, "validation", "Checking what the project's path leads to now.")
    problem = verify_in_service(workspace_root, entry.name, new_release, commit)
    if problem is None:
        return None
    try:
        undone = revert_to(workspace_root, entry.name, previous, new_release)
    except OSError as exc:
        return InstallResult(False, f"the new release of {entry.name} failed its check ({problem}) AND going back failed ({exc}); the previous installation is at {previous}", code="rollback_failed",
                             params={"project": entry.name, "reason": problem, "previous": str(previous or "")})
    return InstallResult(False, f"the new release of {entry.name} failed its check ({problem}); it was taken out of service and removed: {undone}", code="rolled_back",
                         params={"project": entry.name, "reason": problem, "what": undone})


def _update_as_release(
    entry: ProjectEntry, workspace_root: Path, path: Path, installed: ProjectManifest, candidate: ProjectManifest, candidate_sha: str, unsigned: str, progress: ProgressCallback | None,
    *, migrating: bool = False,
) -> InstallResult:
    """The update of a project in the releases layout: the candidate is cloned and built in its own release folder (its final place) and the link is switched to it only when the
    build passed. Any failure removes only that new folder."""
    new_release = release_path(workspace_root, entry.name, candidate_sha)
    _rmtree_best_effort(new_release)   # a leftover of an earlier attempt at the same commit
    new_release.parent.mkdir(parents=True, exist_ok=True)
    _checkpoint(progress, "source", "Cloning the installed release into its own release folder for verification.")
    capture = progress is not None
    steps = (
        (["git", "clone", "--local", "--no-hardlinks", str(path), str(new_release)], workspace_root, "could not create the release folder"),
        (["git", "remote", "set-url", "origin", github_repo_url(entry)], new_release, "could not restore the real upstream remote on the new release"),
    )
    for cmd, cwd, what in steps:
        result = _run(cmd, cwd=cwd, capture_output=capture)
        if result.returncode != 0:
            _rmtree_best_effort(new_release)
            return InstallResult(False, f"{what} (exit {result.returncode}); {path} was not modified", _command_output(result))
    _carry_over_local_data(path, new_release, progress=progress)
    result = _run(["git", "merge", "--ff-only", candidate_sha], cwd=new_release, capture_output=capture)
    if result.returncode != 0:
        _rmtree_best_effort(new_release)
        return InstallResult(False, f"git merge --ff-only failed (exit {result.returncode}) in the new release; {path} was not modified.", _command_output(result))
    _checkpoint(progress, "build", "Building and verifying the candidate in its final folder before the link is switched.")
    build_result = _run_build_script_at(new_release, progress=progress)
    if not build_result.ok:
        _rmtree_best_effort(new_release)
        return InstallResult(False, f"candidate build failed - {path} was left completely untouched and remains the operative installation: {build_result.message}", build_result.output)
    promoted = _activate_release(entry, workspace_root, path, new_release, progress, migrating=migrating)
    if isinstance(promoted, InstallResult):
        return promoted
    (previous,) = promoted
    refused = _check_after_switch(entry, workspace_root, path, new_release, candidate_sha, previous, progress)
    if refused is not None:
        return refused
    pruned = prune_releases(workspace_root, entry.name, DEFAULT_KEEP_RELEASES)
    message = f"Updated {path} to v{candidate.version} (commit {candidate_sha[:12]}) after a verified build in its own release folder; previous installation kept at {previous}"
    if pruned:
        message += f" ({len(pruned)} older release(s) deleted)"
    if migrating:
        message += "; the project was moved to the releases layout (a backup of its history was written first)"
        return _note_unsigned(InstallResult(True, message, build_result.output, code="layout_migrated", params={"project": entry.name, "version": candidate.version, "previous": str(previous or "")}),
                              unsigned, entry.name)
    return _note_unsigned(InstallResult(True, message, build_result.output), unsigned, entry.name)


def clone_or_pull(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    verify_build: bool = True,
    progress: ProgressCallback | None = None,
) -> InstallResult:
    """Installs the project when it is not checked out under `workspace_root`, otherwise fetches and promotes the candidate - never a force-push-style reset.

    Both cases build in a staging folder first (unless `verify_build` is False): the live folder is not touched until the build of the candidate has passed. For an existing
    checkout the candidate manifest is read from the fetched revision before anything changes, a lower version is refused (an update can never silently become a rollback), a
    candidate that is the commit already installed does nothing, and uncommitted edits to tracked files stop the update (so real local work is never moved aside unnoticed).
    The staging folder is promoted by two journalled renames; the replaced checkout is kept under `<workspace>/.armor-updater/backups/<project>/` and the oldest are deleted."""
    path = workspace_root / entry.name
    _checkpoint(progress, "preflight", "Validating the selected workspace and project manifest.")
    if not path.exists():
        staging_path = workspace_root / f".{entry.name}.clone-{uuid4().hex}"
        _checkpoint(progress, "source", "Cloning the selected repository into a safe staging directory.")
        result = _run(["git", "clone", github_repo_url(entry), str(staging_path)], cwd=workspace_root, capture_output=progress is not None)
        if result.returncode != 0:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"git clone failed (exit {result.returncode})", _command_output(result))
        policy = current_policy()
        refused = verify_revision(staging_path, "HEAD", policy)
        if refused:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"cloned candidate refused by the signature policy: {refused}", code="signature_refused", params={"project": entry.name, "reason": refused})
        unsigned = _unsigned_commit(staging_path, "HEAD", policy)
        try:
            _checkpoint(progress, "validation", "Validating the fetched repository manifest before deployment.")
            candidate = _manifest_from_revision(staging_path, "HEAD", entry)
        except ManifestValidationError as exc:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"cloned checkout failed manifest validation: {exc}")
        unmet = requirements_refusal(entry.name, workspace_root, candidate.requires)
        if unmet is not None:
            _rmtree_best_effort(staging_path)
            return unmet
        environment_removed = False
        output = ""
        release_mode = verify_build and wants_releases(entry.name, workspace_root)
        if release_mode:   # the releases layout builds in the folder the project will stay in, so nothing has to be made again afterwards
            final = release_path(workspace_root, entry.name, _rev_parse(staging_path, "HEAD") or uuid4().hex)
            _rmtree_best_effort(final)
            final.parent.mkdir(parents=True, exist_ok=True)
            try:
                staging_path.rename(final)
            except OSError as exc:
                _rmtree_best_effort(staging_path)
                return InstallResult(False, f"could not prepare the release folder ({exc}); nothing was installed")
            staging_path = final
        if verify_build:
            _checkpoint(progress, "build", "Building and verifying the new project in the staging directory before it takes its place.")
            built = _run_build_script_at(staging_path, progress=progress)
            output = built.output
            if not built.ok:
                _rmtree_best_effort(staging_path)
                return InstallResult(False, f"the build failed, so {entry.name} was not installed: {built.message}", built.output)
            if not release_mode:
                forget_build_trees(staging_path)
                environment_removed = remove_generated_environments(staging_path)
        if path.exists() or in_service(workspace_root, entry.name) is not None:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"{path} appeared while cloning - not replacing it")
        if release_mode:
            promoted = _activate_release(entry, workspace_root, path, staging_path, progress)
            if not isinstance(promoted, InstallResult):
                refusal = _check_after_switch(entry, workspace_root, path, staging_path, _rev_parse(staging_path, "HEAD") or "", promoted[0], progress)
                if refusal is not None:
                    return refusal
        else:
            promoted = _promote(entry, workspace_root, path, staging_path, "", progress)
        if isinstance(promoted, InstallResult):
            return promoted
        message = f"Installed {path} (v{candidate.version})" + (" after a verified build" if verify_build else "")
        if environment_removed:
            rebuilt = _rebuild_environment(path, progress)
            message += "; " + rebuilt.message
            if not rebuilt.ok:
                return InstallResult(False, message, rebuilt.output or output)
        return _note_unsigned(InstallResult(True, message, output), unsigned, entry.name)

    if not (path / ".git").is_dir():
        return InstallResult(False, f"{path} exists but isn't a git checkout - not touching it")

    try:
        _checkpoint(progress, "preflight", "Validating the installed repository manifest.")
        installed = _manifest_from_revision(path, "HEAD", entry)
    except ManifestValidationError as exc:
        return InstallResult(False, f"installed checkout failed manifest validation: {exc}")

    try:
        dirty = _tracked_dirty_paths(path)
    except DirtyCheckError as exc:
        return InstallResult(False, str(exc))
    if dirty:
        preview = ", ".join(dirty[:5]) + (f" (+{len(dirty) - 5} more)" if len(dirty) > 5 else "")
        return InstallResult(
            False,
            f"{path} has uncommitted change(s) to real tracked file(s): {preview} - refusing to update; "
            "commit, stash, or discard them first so an update can never silently discard real local work",
        )

    wrong_branch = _wrong_branch_message(path, entry)
    if wrong_branch:
        return InstallResult(False, wrong_branch)

    # Fetch first and inspect FETCH_HEAD before changing the operator's working tree: a malformed or older remote manifest must not become an installed downgrade merely because
    # Git can fast-forward it.
    _checkpoint(progress, "source", "Fetching the remote candidate without changing the local checkout.")
    result = _run(["git", "fetch", "--quiet", "origin", "HEAD"], cwd=path, capture_output=progress is not None)
    if result.returncode != 0:
        return InstallResult(
            False,
            f"git fetch failed (exit {result.returncode}) - remote unavailable or authentication failed?",
            _command_output(result),
        )
    policy = current_policy()
    refused = verify_range(path, "HEAD", "FETCH_HEAD", policy)   # every new commit, not only the last one
    if refused:
        return InstallResult(False, f"remote candidate refused by the signature policy: {refused}", code="signature_refused", params={"project": entry.name, "reason": refused})
    try:
        _checkpoint(progress, "validation", "Checking the candidate manifest and anti-rollback rule.")
        candidate = _manifest_from_revision(path, "FETCH_HEAD", entry)
    except ManifestValidationError as exc:
        return InstallResult(False, f"remote candidate failed manifest validation: {exc}")
    unmet = requirements_refusal(entry.name, workspace_root, candidate.requires)
    if unmet is not None:
        return unmet
    if _version_tuple(candidate) < _version_tuple(installed):
        return InstallResult(
            False,
            f"remote candidate v{candidate.version} is older than installed v{installed.version}; anti-rollback refused update",
        )
    # Resolved as a real SHA: `FETCH_HEAD` means something different in every repo, and the staging clone copies this repository's whole object database, so the commit is present there.
    candidate_sha = _rev_parse(path, "FETCH_HEAD")
    if not candidate_sha:
        return InstallResult(False, f"could not resolve the fetched candidate to a real commit; {path} was not modified")
    if candidate_sha == _rev_parse(path, "HEAD"):
        return InstallResult(True, f"{entry.name} is already up to date (v{installed.version}, commit {candidate_sha[:12]}); nothing was changed")

    unsigned = _unsigned_commit(path, candidate_sha, policy)
    if not verify_build:
        _checkpoint(progress, "validation", "Applying the accepted candidate with a fast-forward-only merge.")
        result = _run(["git", "merge", "--ff-only", "FETCH_HEAD"], cwd=path, capture_output=progress is not None)
        if result.returncode != 0:
            return InstallResult(
                False,
                f"git merge --ff-only failed (exit {result.returncode}) - local changes or a diverged branch?",
                _command_output(result),
            )
        return _note_unsigned(InstallResult(True, f"Pulled latest into {path}"), unsigned, entry.name)

    if wants_releases(entry.name, workspace_root) or in_service(workspace_root, entry.name) is not None:   # a project already in the releases layout stays in it
        moved = in_service(workspace_root, entry.name) is None   # a real checkout: this update migrates it to the layout
        done = _update_as_release(entry, workspace_root, path, installed, candidate, candidate_sha, unsigned, progress, migrating=moved)
        if done.code != "layout_unavailable":
            return done
        _checkpoint(progress, "source", "The releases layout could not be used here; the update goes on in the older layout.")

    staging_path = workspace_root / f".{entry.name}.update-{uuid4().hex}"
    _checkpoint(progress, "source", "Cloning the installed checkout into an isolated staging area for verification.")
    # --no-hardlinks: a plain `git clone --local` hardlinks object files, and on Windows a build running inside the clone can leave them undeletable afterwards.
    result = _run(
        ["git", "clone", "--local", "--no-hardlinks", str(path), str(staging_path)],
        cwd=workspace_root,
        capture_output=progress is not None,
    )
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"could not create a staging clone for verification (exit {result.returncode}); {path} was not modified",
            _command_output(result),
        )

    # `git clone --local` points the new clone's `origin` at the local source path. Put the real upstream back before promotion, or the promoted checkout could never again discover an update.
    result = _run(["git", "remote", "set-url", "origin", github_repo_url(entry)], cwd=staging_path, capture_output=progress is not None)
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"could not restore the real upstream remote on the staging clone (exit {result.returncode}); {path} was not modified",
            _command_output(result),
        )

    _carry_over_local_data(path, staging_path, progress=progress)

    _checkpoint(progress, "validation", "Applying the accepted candidate in the isolated staging clone.")
    result = _run(["git", "merge", "--ff-only", candidate_sha], cwd=staging_path, capture_output=progress is not None)
    if result.returncode != 0:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"git merge --ff-only failed (exit {result.returncode}) in a staging clone - local changes or a diverged branch? {path} was not modified.",
            _command_output(result),
        )

    _checkpoint(progress, "build", "Building and verifying the candidate in isolation before touching the live installation.")
    build_result = _run_build_script_at(staging_path, progress=progress)
    if not build_result.ok:
        _rmtree_best_effort(staging_path)
        return InstallResult(
            False,
            f"candidate build failed - {path} was left completely untouched and remains the operative installation: {build_result.message}",
            build_result.output,
        )

    forget_build_trees(staging_path)
    environment_removed = remove_generated_environments(staging_path)
    promoted = _promote(entry, workspace_root, path, staging_path, candidate_sha, progress)
    if isinstance(promoted, InstallResult):
        return promoted
    (backup_path,) = promoted
    pruned = prune_backups(workspace_root, entry.name, DEFAULT_KEEP)
    message = f"Updated {path} to v{candidate.version} (commit {candidate_sha[:12]}) after a verified build; previous installation kept at {backup_path}"
    if pruned:
        message += f" ({len(pruned)} older backup(s) deleted)"
    if environment_removed:
        rebuilt = _rebuild_environment(path, progress)
        message += "; " + rebuilt.message
        if not rebuilt.ok:
            return InstallResult(False, message, rebuilt.output or build_result.output)
    return _note_unsigned(InstallResult(True, message, build_result.output), unsigned, entry.name)


def find_build_test_script(path: Path) -> Path | None:
    name = BUILD_TEST_SCRIPT_WINDOWS if os.name == "nt" else BUILD_TEST_SCRIPT_POSIX
    candidate = path / name
    return candidate if candidate.is_file() else None


def run_build_script(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    progress: ProgressCallback | None = None,
) -> InstallResult:
    return _run_build_script_at(workspace_root / entry.name, progress=progress)


def _run_build_script_at(path: Path, *, progress: ProgressCallback | None = None) -> InstallResult:
    """The work behind run_build_script(), taking an explicit path: shared with the staging-clone verification, which builds a candidate that is not (yet) the installed checkout."""
    script = find_build_test_script(path)
    if script is None:
        return InstallResult(False, f"No non-versioning build-test.sh/.bat found in {path} - upgrade this checkout or verify it manually before deployment.")

    cmd = ["cmd", "/c", str(script)] if os.name == "nt" else ["bash", str(script)]
    _checkpoint(progress, "build", f"Running {script.name}; this never increments the project version.")
    result = _run(cmd, cwd=path, capture_output=progress is not None)
    if result.returncode != 0:
        return InstallResult(
            False,
            f"{script.name} exited with code {result.returncode} - see the in-window evidence below for what failed.",
            _command_output(result),
        )
    return InstallResult(True, f"{script.name} completed successfully.", _command_output(result))


def install_or_update(
    entry: ProjectEntry,
    workspace_root: Path,
    *,
    build: bool = True,
    progress: ProgressCallback | None = None,
) -> list[InstallResult]:
    """The full manual install/update flow for ONE project. It never raises: whatever goes wrong (git missing, a folder in use, a full disk) comes back as a failed result, so the
    window that called it from a worker thread is never left busy for ever, and every attempt that gets as far as starting leaves its line in the evidence file.

    Takes the workspace lock first (one updater at a time), heals any promotion a previous run left half done, and refuses to build a project when ARMOR-COMMON is not installed next
    to it (every build-test.sh calls ARMOR-COMMON's script)."""
    started = time.time()
    try:
        with WorkspaceLock(workspace_root):
            return _install_or_update_locked(entry, workspace_root, build, progress, started)
    except WorkspaceBusy as busy:
        return [InstallResult(False, str(busy))]
    except Exception as error:  # noqa: BLE001 - see the docstring
        failure = InstallResult(False, f"{type(error).__name__}: {error}")
        try:
            record_attempt(
                workspace_root, project=entry.name, before={}, after=installed_state(workspace_root / entry.name), ok=False, message=failure.message,
                duration_s=time.time() - started,
            )
        except Exception:  # noqa: BLE001 - recording never turns a result into another failure
            pass
        return [failure]


def _install_or_update_locked(entry: ProjectEntry, workspace_root: Path, build: bool, progress: ProgressCallback | None, started: float) -> list[InstallResult]:
    healed = recover_interrupted_promotions(workspace_root)
    for action in healed:
        _checkpoint(progress, "preflight", action)
    before = installed_state(workspace_root / entry.name)
    unmet = requirements_refusal(entry.name, workspace_root, entry.requires)
    if unmet is not None:
        results = [unmet]
    elif build and entry.name != COMMON_PROJECT and not (workspace_root / COMMON_PROJECT).is_dir():
        results = [InstallResult(False, f"{COMMON_PROJECT} is not installed in {workspace_root}: every project's build runs its script, so install {COMMON_PROJECT} first (or choose to skip the build)")]
    else:
        results = [clone_or_pull(entry, workspace_root, verify_build=build, progress=progress)]
        if results[0].ok and not build:
            _checkpoint(progress, "build", "Build-test was deliberately skipped for this one approved source refresh.")
    after = installed_state(workspace_root / entry.name)
    record_attempt(
        workspace_root,
        project=entry.name,
        before=before,
        after=after,
        ok=all(r.ok for r in results),
        message="; ".join(r.message for r in results),
        duration_s=time.time() - started,
    )
    return healed_results(healed) + results


def healed_results(actions: list[str]) -> list[InstallResult]:
    """What a recovery did, as results (a recovered promotion is news the person should see)."""
    return [InstallResult(True, action) for action in actions]




# ---- the previous copies ----------------------------------------------------------------------------------------------------------------------

def backup_summary(workspace_root: Path, project: str | None = None) -> tuple[int, int]:
    """How many replaced checkouts are kept (of `project`, or of every project) and the bytes they take."""
    from .promotion import BACKUPS_DIRECTORY, state_directory
    root = state_directory(workspace_root) / BACKUPS_DIRECTORY
    if project is not None:
        names = [project]
    else:
        names = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    count = size = 0
    for name in names:
        for backup in list_backups(workspace_root, name):
            count += 1
            size += disk_used(backup)
    return count, size


def restore_previous_copy(workspace_root: Path, project: str) -> InstallResult:
    """Puts the newest previous copy of `project` back in its place (the checkout that is there becomes the newest copy, so the restore can be undone). It takes the workspace lock,
    heals an interrupted promotion first and never raises."""
    try:
        with WorkspaceLock(workspace_root):
            healed = recover_interrupted_promotions(workspace_root)
            if in_service(workspace_root, project) is not None:   # releases layout: going back is a switch of the link
                try:
                    what = go_back(workspace_root, project)
                except (RuntimeError, OSError) as error:
                    return InstallResult(False, f"{project}: the previous release could not be restored ({error})", code="restore_failed", params={"project": project, "reason": str(error)})
                return InstallResult(True, "; ".join(healed + [what]), code="restored", params={"project": project, "backup": ""})
            if not list_backups(workspace_root, project):
                return InstallResult(False, f"{project} has no previous copy to go back to", code="no_backup", params={"project": project})
            try:
                what = rollback(workspace_root, project)
            except (RuntimeError, OSError) as error:
                return InstallResult(False, f"{project}: the previous copy could not be restored ({error})", code="restore_failed", params={"project": project, "reason": str(error)})
            newest = list_backups(workspace_root, project)
            return InstallResult(True, "; ".join(healed + [what]), code="restored", params={"project": project, "backup": newest[0].name if newest else ""})
    except WorkspaceBusy as busy:
        return InstallResult(False, str(busy), code="busy")
    except Exception as error:  # noqa: BLE001 - a window calls this from a worker thread
        return InstallResult(False, f"{type(error).__name__}: {error}", code="restore_failed", params={"project": project, "reason": str(error)})


def clean_previous_copies(workspace_root: Path, project: str, keep: int = 0) -> InstallResult:
    """Deletes all but the newest `keep` previous copies of `project` and says how many went and how much disk came back. It takes the workspace lock and never raises."""
    try:
        with WorkspaceLock(workspace_root):
            freed = 0
            doomed = list_backups(workspace_root, project)[max(0, keep):]
            for old in doomed:
                freed += disk_used(old)
            removed = prune_backups(workspace_root, project, keep)
            megabytes = f"{freed / 1024 / 1024:.1f}"
            return InstallResult(True, f"{project}: {len(removed)} previous copy(ies) deleted, {megabytes} MB freed", code="cleaned",
                                 params={"project": project, "count": str(len(removed)), "size": megabytes})
    except WorkspaceBusy as busy:
        return InstallResult(False, str(busy), code="busy")
    except Exception as error:  # noqa: BLE001 - a window calls this from a worker thread
        return InstallResult(False, f"{type(error).__name__}: {error}", code="clean_failed", params={"project": project, "reason": str(error)})
