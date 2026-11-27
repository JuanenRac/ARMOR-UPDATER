# =============================================================================
# ARMOR-UPDATER - The tool of the signed registry of releases: registry_tool.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Makes, signs and checks the registry of releases (`releases.json` and `releases.json.sig`, see release_registry.py).

    python -m armor_updater.registry_tool build --root DIR --out releases.json      the registry of the releases found next to each other
    python -m armor_updater.registry_tool sign releases.json                        signs it with the key named by ARMOR_RELEASE_SIGNING_KEY (or --key PATH)
    python -m armor_updater.registry_tool verify releases.json                      anyone can run it: is the registry signed by a pinned key, and what does it list
    python -m armor_updater.registry_tool keys                                      the fingerprints of the keys the updater pins (what the key to sign with must be one of)

The key. `sign` takes the PATH of an OpenSSH private key without passphrase from the environment variable ARMOR_RELEASE_SIGNING_KEY or from --key. The tool never looks for a key by itself,
never reads the key into Python, never prints it and never copies it: it asks `ssh-keygen -y` for the PUBLIC half and refuses to go on unless that half is one of the pinned keys (or of the
file given with --signers), hands `ssh-keygen -Y sign` only the path, and checks the signature it made before it says it is done. To choose the key: set the variable to its path, run `keys`,
and run `ssh-keygen -l -f <path>`: the fingerprint has to be in the list.

What is signed. The exact bytes of the registry file in the namespace `armor-releases`; the registry says, for each release, which commit of which project (and, for a firmware image, which
file with which SHA-256) it is. `build` lists, for every repository `ARMOR-*` that has an `armor.project.json` and a tag `v<version>` in its own git, the commit under that tag; a repository whose
tag does not exist (a version that was not tagged) is left out and named, never guessed. Where it is published: next to the release notes in ARMOR-DOCS (`data/releases.json` and
`data/releases.json.sig`), outside the repositories it describes, so a release cannot list itself. Standard library only; it needs `ssh-keygen` and `git` on the path.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from . import release_registry as rr
from .console_flags import NO_WINDOW
from .signature import PINNED_SIGNER_FINGERPRINTS, key_fingerprint, signer_fingerprints, signers_file_for_tags, SignaturePolicy

KEY_VARIABLE = "ARMOR_RELEASE_SIGNING_KEY"
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class RegistryToolError(Exception):
    """Something the person has to know, in words."""


def _run(command: list[str], runner: Runner) -> "subprocess.CompletedProcess[str]":
    return runner(command, capture_output=True, encoding="utf-8", errors="replace", timeout=120, creationflags=NO_WINDOW)


def build(root: Path, *, runner: Runner = subprocess.run) -> tuple[list[rr.Release], list[str]]:
    """The releases found under `root` (one folder per project) and the notes of what was left out."""
    releases: list[rr.Release] = []
    notes: list[str] = []
    for folder in sorted(root.glob("ARMOR-*")):
        manifest = folder / "armor.project.json"
        if not manifest.is_file():
            continue
        try:
            version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
        except (OSError, ValueError, KeyError, TypeError):
            notes.append(f"{folder.name}: the manifest cannot be read")
            continue
        done = _run(["git", "-C", str(folder), "rev-parse", "--verify", "--quiet", f"v{version}^{{commit}}"], runner)
        commit = done.stdout.strip()
        if done.returncode != 0 or not commit:
            notes.append(f"{folder.name}: no tag v{version} (left out)")
            continue
        releases.append(rr.Release(folder.name, version, commit=commit))
    return releases, notes


def public_half(key: Path, *, runner: Runner = subprocess.run) -> tuple[str, str]:
    """(type, base64 blob) of the public half of a private key, asked of ssh-keygen (the private key is never read here)."""
    done = _run(["ssh-keygen", "-y", "-f", str(key)], runner)
    parts = done.stdout.split()
    if done.returncode != 0 or len(parts) < 2:
        raise RegistryToolError("ssh-keygen cannot read that key (a missing file, a passphrase or not an OpenSSH key)")
    return parts[0], parts[1]


def sign(registry: Path, key: Path, signers: Path, *, runner: Runner = subprocess.run) -> Path:
    """Signs `registry` with `key` and checks the signature. Refuses a key that is not one of the pinned ones of `signers`."""
    if not registry.is_file():
        raise RegistryToolError(f"{registry} does not exist")
    try:
        rr.parse_registry(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryToolError(f"the registry is not valid ({exc})") from exc
    _kind, blob = public_half(key, runner=runner)
    if key_fingerprint(blob) not in signer_fingerprints(signers):
        raise RegistryToolError(f"the key has the fingerprint {key_fingerprint(blob)}, which is not one of the keys of {signers.name}: nothing was signed")
    signature = registry.with_name(registry.name + ".sig")
    if signature.exists():
        signature.unlink()
    done = _run(rr.sign_command(registry, key), runner)
    if done.returncode != 0 or not signature.is_file():
        raise RegistryToolError("ssh-keygen could not sign (a key with a passphrase needs an agent, which this tool does not use)")
    problem = rr.signature_problem(registry, signers, runner=runner)
    if problem:
        signature.unlink(missing_ok=True)
        raise RegistryToolError(f"the signature that was made does not verify: {problem}")
    return signature


def verify(registry: Path, signers: Path, *, runner: Runner = subprocess.run) -> list[rr.Release]:
    """The releases of a registry whose signature is valid; RegistryToolError with the reason when it is not."""
    problem = rr.signature_problem(registry, signers, runner=runner)
    if problem:
        raise RegistryToolError(problem)
    try:
        return rr.parse_registry(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryToolError(f"the registry cannot be read ({exc})") from exc


def _signers(args: argparse.Namespace) -> Path:
    if args.signers:
        return Path(args.signers)
    path, problem = signers_file_for_tags(SignaturePolicy())
    if problem or path is None:
        raise RegistryToolError(problem or "no usable allowed signers file (give one with --signers)")
    return Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="registry_tool", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    build_p = sub.add_parser("build", help="the registry of the releases found next to each other")
    build_p.add_argument("--root", required=True, help="the folder that holds the ARMOR-* repositories")
    build_p.add_argument("--out", required=True)
    sign_p = sub.add_parser("sign", help="sign a registry")
    sign_p.add_argument("registry")
    sign_p.add_argument("--key", help=f"path of the private key (default: the variable {KEY_VARIABLE})")
    sign_p.add_argument("--signers", help="file of allowed signers (default: the one the updater ships)")
    verify_p = sub.add_parser("verify", help="check a signed registry")
    verify_p.add_argument("registry")
    verify_p.add_argument("--signers", help="file of allowed signers (default: the one the updater ships)")
    sub.add_parser("keys", help="the fingerprints the updater pins")
    args = parser.parse_args(argv)
    try:
        if args.command == "keys":
            for fingerprint in sorted(PINNED_SIGNER_FINGERPRINTS):
                print(fingerprint)
            return 0
        if args.command == "build":
            releases, notes = build(Path(args.root))
            Path(args.out).write_text(rr.render_registry(releases), encoding="utf-8", newline="\n")
            for note in notes:
                print("note:", note)
            print(f"REGISTRY=WRITTEN releases={len(releases)} left_out={len(notes)}")
            return 0
        if args.command == "sign":
            key_text = args.key or os.environ.get(KEY_VARIABLE, "")
            if not key_text:
                raise RegistryToolError(f"no key: give --key PATH or set {KEY_VARIABLE} to the path of the private key")
            signature = sign(Path(args.registry), Path(key_text), _signers(args))
            print(f"REGISTRY=SIGNED {signature}")
            return 0
        releases = verify(Path(args.registry), _signers(args))
        for release in releases:
            print(f"{release.project} {release.version} {release.commit or release.sha256}")
        print(f"REGISTRY=PASS releases={len(releases)}")
        return 0
    except RegistryToolError as exc:
        print(f"REGISTRY=FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
