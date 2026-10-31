# =============================================================================
# ARMOR-UPDATER - What an update must not lose: promotion.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The three things an update needs around the two renames that put a new checkout in place of the old one, with only the standard library:

* a lock, so that two updaters (the window and a command line, two windows, a scheduled job) never work on one workspace at the same time;
* a journal, written to disk before the first rename and removed after the second, so that a crash, a power cut or a kill between the two renames is healed the next time the updater
  runs (the old checkout comes back to its place) instead of leaving the project without a folder;
* the backups of the checkouts that were replaced, kept inside `<workspace>/.armor-updater/backups/<project>/` (outside the scan of the workspace, so they never look like projects),
  the newest few kept and the rest deleted, and a way to put the newest one back (`rollback`).
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

STATE_DIRECTORY = ".armor-updater"
LOCK_FILE = "lock"
JOURNAL_FILE = "promotion.json"
BACKUPS_DIRECTORY = "backups"
#: How many backups of a project are kept; the older ones are deleted after a successful update.
DEFAULT_KEEP = 3
#: A lock older than this is taken for a leftover of a process that died.
LOCK_STALE_SECONDS = 6 * 3600


class WorkspaceBusy(RuntimeError):
    """Another updater holds the workspace."""


def state_directory(workspace_root: Path) -> Path:
    return workspace_root / STATE_DIRECTORY


# ---- the lock -------------------------------------------------------------------------------------------------------------------------------------

def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)   # type: ignore[attr-defined,unused-ignore]  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)   # type: ignore[attr-defined,unused-ignore]
            return True
        except Exception:  # noqa: BLE001 - when in doubt the process is taken to be alive, the age of the file decides
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class WorkspaceLock:
    """`with WorkspaceLock(root):` - raises WorkspaceBusy when another live updater holds it. The file holds the pid and the time; one left by a process that is gone, or older than
    LOCK_STALE_SECONDS, is taken over."""

    def __init__(self, workspace_root: Path, *, stale_after: float = LOCK_STALE_SECONDS, now: Callable[[], float] = time.time) -> None:
        self.path = state_directory(workspace_root) / LOCK_FILE
        self._stale_after = stale_after
        self._now = now
        self._held = False

    def _holder(self) -> tuple[int, float] | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return int(data["pid"]), float(data["at"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(3):
            try:
                descriptor = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                holder = self._holder()
                if holder is not None:
                    pid, started = holder
                    if _process_is_alive(pid) and self._now() - started < self._stale_after:
                        raise WorkspaceBusy(f"another updater (process {pid}) is working on this workspace; wait for it to finish") from None
                try:
                    self.path.unlink()   # a leftover of a process that is gone
                except OSError:
                    pass
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump({"pid": os.getpid(), "at": self._now()}, stream)
            self._held = True
            return
        raise WorkspaceBusy("could not take the lock of this workspace")

    def release(self) -> None:
        if self._held:
            try:
                self.path.unlink()
            except OSError:
                pass
            self._held = False

    def __enter__(self) -> "WorkspaceLock":
        self.acquire()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()


# ---- the journal ----------------------------------------------------------------------------------------------------------------------------------

@dataclass
class Promotion:
    project: str
    path: str
    staging: str
    backup: str
    phase: str = "begun"   # begun -> backed_up -> promoted -> (removed)


def _write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class PromotionJournal:
    """One record: the promotion in progress. Written before the first rename of a promotion and removed after the second."""

    def __init__(self, workspace_root: Path) -> None:
        self.path = state_directory(workspace_root) / JOURNAL_FILE

    def begin(self, promotion: Promotion) -> None:
        _write_atomically(self.path, json.dumps(promotion.__dict__))

    def advance(self, phase: str) -> None:
        current = self.read()
        if current is not None:
            current.phase = phase
            _write_atomically(self.path, json.dumps(current.__dict__))

    def complete(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass

    def read(self) -> Promotion | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return Promotion(str(data["project"]), str(data["path"]), str(data["staging"]), str(data["backup"]), str(data.get("phase", "begun")))
        except (OSError, ValueError, KeyError, TypeError):
            return None


def recover_interrupted_promotion(workspace_root: Path) -> list[str]:
    """Heals a promotion that a crash left half done. Called before any work. Returns what it did (empty when nothing was pending).

    - phase `begun`: nothing was renamed; the candidate in staging is thrown away.
    - phase `backed_up`: the old checkout was renamed away and the new one may not be in place: when the project's folder is missing the old one comes back (the candidate in staging is
      thrown away); when it is there the update did finish and the journal is just cleared.
    - phase `promoted`: both renames are done; the journal is cleared.
    """
    journal = PromotionJournal(workspace_root)
    promotion = journal.read()
    if promotion is None:
        if journal.path.exists():   # a damaged record cannot be trusted nor repeated
            journal.complete()
            return ["a damaged promotion record was removed"]
        return []
    path, staging, backup = Path(promotion.path), Path(promotion.staging), Path(promotion.backup)
    actions: list[str] = []
    if promotion.phase == "backed_up" and not path.exists():
        if backup.exists():
            try:
                backup.rename(path)
                actions.append(f"{promotion.project}: an interrupted update was undone, the previous checkout is back in {path}")
            except OSError as error:
                actions.append(f"{promotion.project}: an interrupted update could not be undone ({error}); the previous checkout is at {backup}")
                return actions   # the record stays: the next run tries again
        else:
            actions.append(f"{promotion.project}: an interrupted update left no checkout in {path} and no backup at {backup}")
    if promotion.phase != "promoted" and staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    journal.complete()
    return actions


# ---- the backups ----------------------------------------------------------------------------------------------------------------------------------

def backups_directory(workspace_root: Path, project: str) -> Path:
    return state_directory(workspace_root) / BACKUPS_DIRECTORY / project


def new_backup_path(workspace_root: Path, project: str, commit: str | None) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    label = (commit or "unknown")[:8]
    candidate = backups_directory(workspace_root, project) / f"{stamp}-{label}"
    number = 2
    while candidate.exists():   # two in the same second
        candidate = backups_directory(workspace_root, project) / f"{stamp}-{label}-{number}"
        number += 1
    return candidate


def list_backups(workspace_root: Path, project: str) -> list[Path]:
    """The backups of a project, the newest first."""
    directory = backups_directory(workspace_root, project)
    if not directory.is_dir():
        return []
    return sorted((p for p in directory.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True)


def prune_backups(workspace_root: Path, project: str, keep: int = DEFAULT_KEEP, *, remover: Callable[[Path], None] | None = None) -> list[Path]:
    """Deletes all but the newest `keep` backups of a project; returns the ones deleted."""
    removed: list[Path] = []
    remove = remover or (lambda p: shutil.rmtree(p, ignore_errors=True))
    for old in list_backups(workspace_root, project)[max(0, keep):]:
        remove(old)
        removed.append(old)
    return removed


def disk_used(path: Path) -> int:
    total = 0
    for root, _directories, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def rollback(workspace_root: Path, project: str) -> str:
    """Puts the newest backup of `project` back in its place. The checkout that was there is kept as the newest backup (so a rollback can itself be undone). Returns what it did;
    raises RuntimeError when there is nothing to restore."""
    backups = list_backups(workspace_root, project)
    if not backups:
        raise RuntimeError(f"{project} has no backup to go back to")
    path = workspace_root / project
    chosen = backups[0]
    if path.exists():
        displaced = new_backup_path(workspace_root, project, "replaced")
        displaced.parent.mkdir(parents=True, exist_ok=True)
        path.rename(displaced)
    try:
        chosen.rename(path)
    except OSError:
        if not path.exists() and "displaced" in locals():   # put the checkout back where it was
            displaced.rename(path)
        raise
    return f"{project}: the backup {chosen.name} is back in {path}"
