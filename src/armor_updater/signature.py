# =============================================================================
# ARMOR-UPDATER - Optional commit-signature policy: signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Commit-signature policy: warn by default, require on request.

By default the updater trusts whatever the GitHub remote serves (a
compromised account or repository could push a commit that this tool would
then build and run). The policy decides what happens with a revision that
carries no valid GPG or SSH signature (`git verify-commit`):

* `warn` (the default): the install or update goes ahead, and the window and
  the command line state that the revision is not signed.
* `require`: the candidate revision - the fresh clone's HEAD, or every new
  commit of the fetched FETCH_HEAD of an update - must carry a valid
  signature BEFORE its manifest is read or anything in it is built. A refused
  candidate leaves the installed checkout untouched.

Require signatures in `~/.armor_updater_settings.json`:

    {"signature_policy": "require",
     "allowed_signers_file": "/home/me/.config/armor/allowed_signers"}

(`"signature_policy": "warn"` is the default and needs no entry; the older
`"require_signed_commits": true` still means `require`), or with the
environment variable `ARMOR_UPDATER_REQUIRE_SIGNED=1` (and
`ARMOR_UPDATER_ALLOWED_SIGNERS=<file>`). `allowed_signers_file` is the
OpenSSH allowed-signers file used for SSH-signed commits; GPG-signed
commits are checked against the user's own GPG keyring.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .settings import load_settings, settings_damaged


@dataclass(frozen=True)
class SignaturePolicy:
    required: bool = False
    allowed_signers_file: str | None = None

    @property
    def mode(self) -> str:
        """"require" refuses an unsigned revision, "warn" (the default) installs it and says so."""
        return "require" if self.required else "warn"


def current_policy() -> SignaturePolicy:
    """The policy in force: the environment variables win over the saved
    settings, so a CI job or a one-off run can require signatures without
    touching the user's settings file."""
    settings = load_settings()
    env_required = os.environ.get("ARMOR_UPDATER_REQUIRE_SIGNED", "").strip().lower()
    if env_required in {"1", "true", "yes"}:
        required = True
    elif env_required in {"0", "false", "no"}:
        required = False
    elif settings_damaged():
        required = True   # the file that holds the policy cannot be read: it is not taken as "off"
    else:
        required = settings.get("signature_policy") == "require" or settings.get("require_signed_commits") is True
    signers = os.environ.get("ARMOR_UPDATER_ALLOWED_SIGNERS") or settings.get("allowed_signers_file")
    return SignaturePolicy(required, signers if isinstance(signers, str) and signers else None)


def verify_range(repo: Path, base: str, tip: str, policy: SignaturePolicy, *, limit: int = 200) -> str | None:
    """None when every commit that `tip` brings over `base` is acceptable under `policy`, otherwise the reason. Verifying only the tip would let an unsigned commit ride in under a
    signed one. A disabled policy accepts everything; a range longer than `limit` commits is refused (a person reads it first)."""
    if not policy.required:
        return None
    try:
        listing = subprocess.run(["git", "rev-list", f"{base}..{tip}"], cwd=repo, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"could not list the new commits: {exc}"
    if listing.returncode != 0:
        return "could not list the new commits (is the installed commit part of the remote history?)"
    commits = listing.stdout.split()
    if len(commits) > limit:
        return f"{len(commits)} new commits are too many to verify one by one; update by hand after reading them"
    for commit in commits:
        refused = verify_revision(repo, commit, policy)
        if refused:
            return f"{refused} [{commit[:12]}]"
    return None


def unsigned_reason(repo: Path, revision: str, policy: SignaturePolicy) -> str | None:
    """None when `revision` carries a signature that verifies, otherwise why it does not (not signed, signed by a key that is not trusted, or git could not check). It does not
    depend on the policy mode: the warning of the default mode and the refusal of the strict one are built from it."""
    cmd = ["git"]
    if policy.allowed_signers_file:
        if not Path(policy.allowed_signers_file).is_file():
            return f"allowed signers file {policy.allowed_signers_file} does not exist"
        cmd += ["-c", f"gpg.ssh.allowedSignersFile={policy.allowed_signers_file}"]
    cmd += ["verify-commit", revision]
    try:
        result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"could not run git verify-commit: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return "candidate commit is not signed by a trusted key" + (f" ({detail[-1]})" if detail else "")
    return None


def verify_revision(repo: Path, revision: str, policy: SignaturePolicy) -> str | None:
    """None when `revision` is acceptable under `policy`, otherwise the reason it is refused. Only the strict mode refuses; the default mode accepts everything (the caller
    asks `unsigned_reason` to warn)."""
    if not policy.required:
        return None
    return unsigned_reason(repo, revision, policy)
