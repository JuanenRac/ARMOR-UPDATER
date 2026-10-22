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
OpenSSH allowed-signers file used for SSH-signed commits. Without it the file
shipped with the updater (`data/allowed_signers`, the keys of the ecosystem)
is used, and only while its keys match the fingerprints pinned in this module;
GPG-signed commits are checked against the user's own GPG keyring.
"""
from __future__ import annotations

import base64
import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .settings import load_settings, settings_damaged
from .console_flags import NO_WINDOW


#: The allowed-signers file of the ecosystem, shipped inside the package, and the fingerprints of the keys it may hold. The file is only trusted while the keys in it are exactly
#: these: a changed or added key makes every check against it fail closed until the pin below is changed on purpose (and the change reviewed).
ECOSYSTEM_SIGNERS_FILE = Path(__file__).with_name("data") / "allowed_signers"
PINNED_SIGNER_FINGERPRINTS = frozenset({"SHA256:LQHmQZS0+NAsDvpTOX81NgvP4J+ROX4j319Bby/D+NE"})
_KEY_TYPES = ("ssh-", "ecdsa-", "sk-")


def key_fingerprint(base64_blob: str) -> str:
    """The OpenSSH SHA256 fingerprint (`SHA256:...`) of a public key given as the base64 blob of an authorized-keys line."""
    digest = hashlib.sha256(base64.b64decode(base64_blob)).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def signer_fingerprints(path: Path) -> set[str]:
    """The fingerprints of every public key in an allowed-signers file. An entry that cannot be read raises ValueError (a damaged file is never half-trusted)."""
    found: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        for index, token in enumerate(tokens):
            if token.startswith(_KEY_TYPES) and index + 1 < len(tokens):
                try:
                    found.add(key_fingerprint(tokens[index + 1]))
                except ValueError as exc:
                    raise ValueError(f"unreadable key in {path.name}: {exc}") from exc
                break
        else:
            raise ValueError(f"line without a public key in {path.name}")
    return found


def ecosystem_signers_problem(path: Path | None = None, pinned: frozenset[str] | None = None) -> str | None:
    """None when the ecosystem signers file holds exactly the pinned keys, otherwise why it is not trusted."""
    path = ECOSYSTEM_SIGNERS_FILE if path is None else path
    pinned = PINNED_SIGNER_FINGERPRINTS if pinned is None else pinned
    if not path.is_file():
        return f"the ecosystem allowed-signers file {path.name} is missing from this installation"
    try:
        found = signer_fingerprints(path)
    except (OSError, ValueError) as exc:
        return f"the ecosystem allowed-signers file cannot be read ({exc})"
    if found != set(pinned):
        return f"the ecosystem allowed-signers file does not match the pinned fingerprint(s) (found {', '.join(sorted(found)) or 'none'}); it is not trusted"
    return None


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
        listing = subprocess.run(["git", "rev-list", f"{base}..{tip}"], cwd=repo, capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
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
    if policy.allowed_signers_file:   # chosen on purpose by the person: used as it is
        if not Path(policy.allowed_signers_file).is_file():
            return f"allowed signers file {policy.allowed_signers_file} does not exist"
        cmd += ["-c", f"gpg.ssh.allowedSignersFile={policy.allowed_signers_file}"]
    else:   # the signers of the ecosystem, only while the file still holds the pinned keys
        problem = ecosystem_signers_problem()
        if problem:
            return problem
        cmd += ["-c", f"gpg.ssh.allowedSignersFile={ECOSYSTEM_SIGNERS_FILE}"]
    cmd += ["verify-commit", revision]
    try:
        result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
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
