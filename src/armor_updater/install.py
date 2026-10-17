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
# =============================================================================
from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2, copytree, rmtree
from typing import Callable, Iterable
from uuid import uuid4

from .evidence import installed_state, record_attempt
from .project_manifest import ManifestValidationError, ProjectManifest, parse_manifest
from .promotion import (
    DEFAULT_KEEP,
    Promotion,
    PromotionJournal,
    WorkspaceBusy,
    WorkspaceLock,
    new_backup_path,
    prune_backups,
    recover_interrupted_promotion,
)
from .registry import ProjectEntry, github_repo_url
from .signature import current_policy, verify_range, verify_revision

#: Every project's build-test.sh runs ../ARMOR-COMMON/scripts/armor-project.sh: without that checkout next to it nothing builds.
COMMON_PROJECT = "ARMOR-COMMON"


def recover_interrupted_promotions(workspace_root: Path) -> list[str]:
    """Heals a promotion that a crash, a kill or a power cut left half done (see promotion.py). Returns what it did."""
    return recover_interrupted_promotion(workspace_root)


def install_order(entries: Iterable[ProjectEntry]) -> list[ProjectEntry]:
    """The order to install or update several projects in: ARMOR-COMMON first (every build needs it), then a parent before its children, then by name."""
    items = sorted(entries, key=lambda e: e.name.casefold())
    names = {e.name for e in items}
    ordered: list[ProjectEntry] = []
    placed: set[str] = set()

    def place(entry: ProjectEntry, trail: tuple[str, ...] = ()) -> None:
        if entry.name in placed or entry.name in trail:
            return
        if entry.parent and entry.parent in names and entry.parent != entry.name:
            place(next(e for e in items if e.name == entry.parent), trail + (entry.name,))
        ordered.append(entry)
        placed.add(entry.name)

    for entry in items:
        if entry.name == COMMON_PROJECT:
            place(entry)
    for entry in items:
        place(entry)
    return ordered


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


BUILD_TEST_SCRIPT_POSIX = "build-test.sh"
BUILD_TEST_SCRIPT_WINDOWS = "build-test.bat"
BUILD_SCRIPT_POSIX = "build.sh"
BUILD_SCRIPT_WINDOWS = "build.bat"

# The GUI consumes these events to show the same real work that the CLI does. A callback is deliberately optional: command-line users retain normal child process output, while the
# GUI captures it so Windows never needs a second terminal window merely to show a project's build output.
ProgressCallback = Callable[[str, str], None]


@dataclass
class InstallResult:
    ok: bool
    message: str
    output: str = ""


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


def _checkpoint(progress: ProgressCallback | None, phase: str, message: str) -> None:
    if progress is not None:
        progress(phase, message)


def _real_untracked_paths(path: Path) -> list[str]:
    """Every path (relative to `path`) git considers untracked or ignored (`??`/`!!`): the local data that `git clone --local` never copies (it only copies the committed objects).
    A modified TRACKED file is never included - that already blocks the update separately."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--ignored", "-uall", "-z"],
        cwd=str(path), check=False, capture_output=True, text=True,
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
        cwd=str(path), check=False, capture_output=True, text=True,
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


def _validated_manifest_text(text: str, entry: ProjectEntry) -> ProjectManifest:
    """The repository-owned manifest used as an update precondition: the revision must still identify itself as the selected project."""
    return parse_manifest(text, expected_name=entry.name)


def _version_tuple(manifest: ProjectManifest) -> tuple[int, int, int, int]:
    parts = [int(part) for part in manifest.version.split(".")]
    parts += [0] * (4 - len(parts))  # a missing fourth component compares as 0
    return tuple(parts)  # type: ignore[return-value]


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


def _rev_parse(path: Path, revision: str) -> str:
    return subprocess.run(["git", "rev-parse", revision], cwd=str(path), check=False, capture_output=True, text=True).stdout.strip()


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
        refused = verify_revision(staging_path, "HEAD", current_policy())
        if refused:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"cloned candidate refused by the signature policy: {refused}")
        try:
            _checkpoint(progress, "validation", "Validating the fetched repository manifest before deployment.")
            candidate = _manifest_from_revision(staging_path, "HEAD", entry)
        except ManifestValidationError as exc:
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"cloned checkout failed manifest validation: {exc}")
        environment_removed = False
        output = ""
        if verify_build:
            _checkpoint(progress, "build", "Building and verifying the new project in the staging directory before it takes its place.")
            built = _run_build_script_at(staging_path, progress=progress)
            output = built.output
            if not built.ok:
                _rmtree_best_effort(staging_path)
                return InstallResult(False, f"the build failed, so {entry.name} was not installed: {built.message}", built.output)
            forget_build_trees(staging_path)
            environment_removed = remove_generated_environments(staging_path)
        if path.exists():
            _rmtree_best_effort(staging_path)
            return InstallResult(False, f"{path} appeared while cloning - not replacing it")
        promoted = _promote(entry, workspace_root, path, staging_path, "", progress)
        if isinstance(promoted, InstallResult):
            return promoted
        message = f"Installed {path} (v{candidate.version})" + (" after a verified build" if verify_build else "")
        if environment_removed:
            rebuilt = _rebuild_environment(path, progress)
            message += "; " + rebuilt.message
            if not rebuilt.ok:
                return InstallResult(False, message, rebuilt.output or output)
        return InstallResult(True, message, output)

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
    refused = verify_range(path, "HEAD", "FETCH_HEAD", current_policy())   # every new commit, not only the last one
    if refused:
        return InstallResult(False, f"remote candidate refused by the signature policy: {refused}")
    try:
        _checkpoint(progress, "validation", "Checking the candidate manifest and anti-rollback rule.")
        candidate = _manifest_from_revision(path, "FETCH_HEAD", entry)
    except ManifestValidationError as exc:
        return InstallResult(False, f"remote candidate failed manifest validation: {exc}")
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

    if not verify_build:
        _checkpoint(progress, "validation", "Applying the accepted candidate with a fast-forward-only merge.")
        result = _run(["git", "merge", "--ff-only", "FETCH_HEAD"], cwd=path, capture_output=progress is not None)
        if result.returncode != 0:
            return InstallResult(
                False,
                f"git merge --ff-only failed (exit {result.returncode}) - local changes or a diverged branch?",
                _command_output(result),
            )
        return InstallResult(True, f"Pulled latest into {path}")

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
    return InstallResult(True, message, build_result.output)


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
    if build and entry.name != COMMON_PROJECT and not (workspace_root / COMMON_PROJECT).is_dir():
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


def _command_output(result: subprocess.CompletedProcess[str]) -> str:
    """Compact child evidence when a GUI captured it: the full command output stays in the process result while the desktop surface keeps a bounded, readable activity trace."""
    return "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
