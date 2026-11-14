# =============================================================================
# ARMOR-UPDATER - Signed registry of releases: release_registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""A signed list of the releases of the family (`releases.json` and its detached SSH signature `releases.json.sig`).

A release tag in one repository is not enough to trust it: whoever can push a signed-looking tag there could publish a release. The registry is a second, independent statement
made with the same ecosystem key the updater already pins (`signature.PINNED_SIGNER_FINGERPRINTS`): it says which commit (and, for firmware, which file with which SHA-256) is the
release `version` of a project. It lives outside the repository it describes, so a release cannot list itself.

Format (`schema_version` 1):

    {"schema_version": 1, "releases": [{"project": "ARMOR-SERVER", "version": "0.8.1.7", "commit": "<40 hex>"},
                                       {"project": "ARMOR-NODE-RADAR", "version": "0.8.1.0", "board": "s3-eth", "sha256": "<64 hex>"}]}

The mode is **off by default**. With `"release_registry_required": true` in the settings (or `ARMOR_UPDATER_RELEASE_REGISTRY=1` for one run) and `"release_registry_file"` naming the
registry (the signature is read from the same name plus `.sig`), a release is installed only when the registry has a valid signature and lists the commit of the tag. The signature is
checked with `ssh-keygen -Y verify` in the namespace `armor-releases`, against the keys of the ecosystem file only while that file holds the pinned keys; a damaged or missing
registry refuses the release (the mode never fails open).
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .console_flags import NO_WINDOW
from .signature import SignaturePolicy, signers_file_for_tags

NAMESPACE = "armor-releases"
IDENTITY = "armor-ecosystem@electrohobby3d.invalid"
SCHEMA_VERSION = 1
_COMMIT = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_VERSION = re.compile(r"\d+\.\d+\.\d+(\.\d+)?")

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class Release:
    project: str
    version: str
    commit: str | None = None
    board: str | None = None
    sha256: str | None = None


def parse_registry(text: str) -> list[Release]:
    """The releases of a registry text. Anything outside the format raises ValueError: a registry is read whole or not at all."""
    try:
        document = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"the registry is not JSON ({exc})") from exc
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION or not isinstance(document.get("releases"), list):
        raise ValueError("the registry is not schema_version 1 with a list of releases")
    found: list[Release] = []
    seen: set[tuple[str, str, str | None]] = set()
    for index, item in enumerate(document["releases"]):
        if not isinstance(item, dict):
            raise ValueError(f"release #{index} is not an object")
        project, version = item.get("project"), item.get("version")
        commit, board, sha256 = item.get("commit"), item.get("board"), item.get("sha256")
        if not isinstance(project, str) or not project or not isinstance(version, str) or not _VERSION.fullmatch(version):
            raise ValueError(f"release #{index} needs a project and a version")
        if commit is None and sha256 is None:
            raise ValueError(f"release #{index} ({project} {version}) names neither a commit nor a file hash")
        if commit is not None and (not isinstance(commit, str) or not _COMMIT.fullmatch(commit)):
            raise ValueError(f"release #{index} ({project} {version}) has a commit that is not 40 lowercase hex digits")
        if sha256 is not None and (not isinstance(sha256, str) or not _SHA256.fullmatch(sha256)):
            raise ValueError(f"release #{index} ({project} {version}) has a sha256 that is not 64 lowercase hex digits")
        if board is not None and (not isinstance(board, str) or not board):
            raise ValueError(f"release #{index} ({project} {version}) has an empty board")
        key = (project, version, board)
        if key in seen:
            raise ValueError(f"{project} {version} is listed twice")
        seen.add(key)
        found.append(Release(project, version, commit, board, sha256))
    return found


def render_registry(releases: list[Release]) -> str:
    """The registry text for a list of releases: sorted, one fixed layout, so the signed bytes are the same every time."""
    ordered = sorted(releases, key=lambda r: (r.project, r.version, r.board or ""))
    rows = []
    for release in ordered:
        row: dict[str, str] = {"project": release.project, "version": release.version}
        for name in ("board", "commit", "sha256"):
            value = getattr(release, name)
            if value is not None:
                row[name] = value
        rows.append(row)
    text = json.dumps({"schema_version": SCHEMA_VERSION, "releases": rows}, indent=2) + "\n"
    parse_registry(text)   # what is written is always readable back
    return text


def _namespaced_signers(source: Path, folder: Path) -> Path:
    """A copy of the allowed-signers file whose keys are valid for the registry namespace only (the shipped file allows its keys for git signatures only)."""
    lines = []
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(re.sub(r'namespaces="[^"]*"', f'namespaces="{NAMESPACE}"', line) if "namespaces=" in line else line.replace(" ssh-", f' namespaces="{NAMESPACE}" ssh-', 1))
    target = folder / "allowed_signers"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def signature_problem(registry: Path, signers: Path, *, runner: Runner = subprocess.run) -> str | None:
    """None when `<registry>.sig` is a valid signature of the registry by a key of `signers`, otherwise the reason."""
    signature = registry.with_name(registry.name + ".sig")
    if not registry.is_file():
        return f"the release registry {registry} does not exist"
    if not signature.is_file():
        return f"the release registry has no signature ({signature.name} is missing)"
    with tempfile.TemporaryDirectory() as folder:
        try:
            namespaced = _namespaced_signers(signers, Path(folder))
            with registry.open("rb") as data:
                done = runner(["ssh-keygen", "-Y", "verify", "-f", str(namespaced), "-I", IDENTITY, "-n", NAMESPACE, "-s", str(signature)],
                              stdin=data, capture_output=True, timeout=60, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"the release registry could not be verified ({exc})"
    if done.returncode != 0:
        return "the release registry is not signed by a trusted key"
    return None


def registry_refusal(registry: Path, project: str, version: str | None, commit: str, policy: SignaturePolicy | None = None, *, signers: Path | None = None,
                     runner: Runner = subprocess.run) -> str | None:
    """None when the signed registry lists `commit` as the release of `project` (and, when given, `version`), otherwise the reason. Fails closed on every doubt."""
    if signers is None:
        path, problem = signers_file_for_tags(policy or SignaturePolicy())
        if problem or path is None:
            return problem or "no usable allowed signers file"
        signers = Path(path)
    problem = signature_problem(registry, signers, runner=runner)
    if problem:
        return problem
    try:
        releases = parse_registry(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"the release registry cannot be read ({exc})"
    listed = [r for r in releases if r.project == project and r.commit is not None]
    if not listed:
        return f"the signed release registry does not list {project}"
    for release in listed:
        if release.commit == commit and (version is None or release.version == version):
            return None
    if any(release.commit == commit for release in listed):
        return f"the signed release registry lists this commit of {project} under another version"
    return f"the signed release registry does not list this commit of {project}"


def file_refusal(registry: Path, project: str, version: str, board: str | None, sha256: str, policy: SignaturePolicy | None = None, *, signers: Path | None = None,
                 runner: Runner = subprocess.run) -> str | None:
    """None when the signed registry lists a file with this SHA-256 as the release `version` of `project` for `board` (firmware images), otherwise the reason."""
    if signers is None:
        path, problem = signers_file_for_tags(policy or SignaturePolicy())
        if problem or path is None:
            return problem or "no usable allowed signers file"
        signers = Path(path)
    problem = signature_problem(registry, signers, runner=runner)
    if problem:
        return problem
    try:
        releases = parse_registry(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"the release registry cannot be read ({exc})"
    for release in releases:
        if release.project == project and release.version == version and release.board == board and release.sha256 == sha256.lower():
            return None
    return f"the signed release registry does not list this file of {project} {version}"


def sign_command(registry: Path, key: Path) -> list[str]:
    """The command that signs a registry (run by the person who holds the key; the key is never read or stored by this module)."""
    return ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(registry)]

