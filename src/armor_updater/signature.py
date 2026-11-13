# =============================================================================
# ARMOR-UPDATER - Optional commit-signature policy: signature.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
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

"Only signed tags" (`"signed_tags_only": true`, or `ARMOR_UPDATER_SIGNED_TAGS_ONLY=1`; off by default) goes further: the candidate revision must be pointed at by an annotated
git tag whose signature `git verify-tag` accepts against an allowed-signers file pinned by its SHA-256 (`"allowed_signers_sha256"`). No tag, a lightweight tag, or a tag signed by
another key means nothing is installed, with the reason. The check runs before the manifest is read or anything is built.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .settings import load_settings, settings_damaged
from .console_flags import NO_WINDOW
from .updater_core import PROFILE as _PROFILE


#: The allowed-signers file of the ecosystem, shipped inside the package, and the fingerprints of the keys it may hold. The file is only trusted while the keys in it are exactly
#: these: a changed or added key makes every check against it fail closed until the pin below is changed on purpose (and the change reviewed).
ECOSYSTEM_SIGNERS_FILE = Path(__file__).with_name("data") / "allowed_signers"
PINNED_SIGNER_FINGERPRINTS = frozenset({"SHA256:LQHmQZS0+NAsDvpTOX81NgvP4J+ROX4j319Bby/D+NE"})
_KEY_TYPES = ("ssh-", "ecdsa-", "sk-")
CHANNEL_RELEASE = "release"
CHANNEL_DEVELOPMENT = "development"
_RELEASE_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?")


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
    #: "Only signed tags" mode (off by default): only a revision that a git tag points at, with a signature `git verify-tag` accepts, is installed.
    signed_tags_only: bool = False
    #: The SHA-256 (hex) the allowed-signers file must have; the file is not used while its content differs. Required with a signers file chosen by the person.
    signers_sha256: str | None = None
    #: Where updates come from: "release" (the default) installs the newest tag vX.Y.Z whose signature verifies against the pinned keys of the ecosystem; "development" follows the tip of
    #: the default branch, as the updater always did (an option for people who test, never the default).
    channel: str = CHANNEL_RELEASE

    @property
    def mode(self) -> str:
        """"require" refuses an unsigned revision, "warn" (the default) installs it and says so."""
        return "require" if self.required else "warn"


def current_policy() -> SignaturePolicy:
    """The policy in force: the environment variables win over the saved
    settings, so a CI job or a one-off run can require signatures without
    touching the user's settings file."""
    settings = load_settings()
    env_required = _PROFILE.env_text("REQUIRE_SIGNED").strip().lower()
    if env_required in {"1", "true", "yes"}:
        required = True
    elif env_required in {"0", "false", "no"}:
        required = False
    elif settings_damaged():
        required = True   # the file that holds the policy cannot be read: it is not taken as "off"
    else:
        required = settings.get("signature_policy") == "require" or settings.get("require_signed_commits") is True
    env_tags = _PROFILE.env_text("SIGNED_TAGS_ONLY").strip().lower()
    if env_tags in {"1", "true", "yes"}:
        tags_only = True
    elif env_tags in {"0", "false", "no"}:
        tags_only = False
    elif settings_damaged():
        tags_only = True   # as above: an unreadable settings file never switches a protection off
    else:
        tags_only = settings.get("signed_tags_only") is True
    channel_text = _PROFILE.env_text("CHANNEL").strip().lower() or str(settings.get("update_channel", "")).strip().lower()
    channel = CHANNEL_DEVELOPMENT if channel_text == CHANNEL_DEVELOPMENT else CHANNEL_RELEASE   # anything else, a damaged file included, is the safe channel
    signers = os.environ.get(_PROFILE.env_name("ALLOWED_SIGNERS")) or settings.get("allowed_signers_file")
    pin = os.environ.get(_PROFILE.env_name("ALLOWED_SIGNERS_SHA256")) or settings.get("allowed_signers_sha256")
    return SignaturePolicy(
        required,
        signers if isinstance(signers, str) and signers else None,
        tags_only,
        pin.strip().lower() if isinstance(pin, str) and pin.strip() else None,
        channel,
    )


def file_sha256(path: Path) -> str:
    """The SHA-256 (lowercase hex) of a file's bytes: the fingerprint an allowed-signers file is pinned by."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signers_file_for_tags(policy: SignaturePolicy) -> tuple[str | None, str | None]:
    """(path, None) of the allowed-signers file the signed-tags mode may use, or (None, reason). A file chosen by the person is used only when its SHA-256 equals the one pinned in the
    settings (`allowed_signers_sha256`); without a pin it is refused. The file shipped with the updater is used only while it holds the pinned keys."""
    if policy.allowed_signers_file:
        path = Path(policy.allowed_signers_file)
        if not path.is_file():
            return None, f"allowed signers file {policy.allowed_signers_file} does not exist"
        if not policy.signers_sha256:
            return None, "signed-tags mode needs allowed_signers_sha256 (the SHA-256 of the allowed signers file) in the settings; the file is not used without it"
        try:
            actual = file_sha256(path)
        except OSError as exc:
            return None, f"allowed signers file cannot be read ({exc})"
        if actual != policy.signers_sha256:
            return None, "allowed signers file does not match the SHA-256 pinned in the settings; it is not trusted"
        return str(path), None
    problem = ecosystem_signers_problem()
    if problem:
        return None, problem
    if policy.signers_sha256 and file_sha256(ECOSYSTEM_SIGNERS_FILE) != policy.signers_sha256:
        return None, "the ecosystem allowed signers file does not match the SHA-256 pinned in the settings; it is not trusted"
    return str(ECOSYSTEM_SIGNERS_FILE), None


def _git_text(repo: Path, *args: str) -> tuple[int, str]:
    try:
        done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return done.returncode, (done.stdout if done.returncode == 0 else (done.stderr or done.stdout)).strip()


def signed_tag_refusal(repo: Path, revision: str, policy: SignaturePolicy) -> str | None:
    """None when an annotated tag points at `revision` and `git verify-tag` accepts its signature against the pinned allowed-signers file, otherwise the reason. Only git objects are
    read and ssh-keygen checks the signature: nothing of the downloaded repository is run. With the mode switched off it accepts everything."""
    if not policy.signed_tags_only:
        return None
    signers, problem = signers_file_for_tags(policy)
    if problem or signers is None:
        return problem or "signed-tags mode: no usable allowed signers file"
    code, sha = _git_text(repo, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if code != 0:
        return "signed-tags mode could not resolve the candidate revision"
    code, listing = _git_text(repo, "tag", "--points-at", sha)
    tags = listing.split() if code == 0 else []
    if not tags:
        return "signed-tags mode: no tag points at the candidate revision (an untagged revision is not installed)"
    last = ""
    for tag in tags:
        ref = f"refs/tags/{tag}"
        code, kind = _git_text(repo, "cat-file", "-t", ref)
        if code != 0 or kind != "tag":
            last = f"tag {tag} is lightweight (not annotated and signed)"
            continue
        code, detail = _git_text(repo, "-c", "gpg.format=ssh", "-c", f"gpg.ssh.allowedSignersFile={signers}", "verify-tag", ref)
        if code == 0:
            return None
        last = f"tag {tag} is not signed by a trusted key" + (f" ({detail.splitlines()[-1]})" if detail else "")
    return f"signed-tags mode: {last}"


def release_tags(repo: Path) -> list[tuple[tuple[int, ...], str]]:
    """The tags vX.Y.Z (or vX.Y.Z.W) of the repository, newest first. Any other tag name is not a release."""
    code, listing = _git_text(repo, "tag", "--list", "v[0-9]*")
    found = []
    for name in (listing.split() if code == 0 else []):
        match = _RELEASE_TAG.fullmatch(name)
        if match:
            found.append((tuple(int(part or 0) for part in match.groups()), name))
    return sorted(found, reverse=True)


def latest_signed_release(repo: Path, policy: SignaturePolicy) -> tuple[str | None, str]:
    """(commit, tag) of the newest release tag whose annotated tag `git verify-tag` accepts against the pinned allowed-signers file of the ecosystem, or (None, reason). A newer tag that is
    lightweight or signed by another key is skipped (and named in the reason when nothing older is acceptable): only a signed release is ever installed on this channel. Only git objects
    are read and ssh-keygen checks the signature: nothing of the repository is run."""
    signers, problem = signers_file_for_tags(policy)
    if problem or signers is None:
        return None, problem or "no usable allowed signers file"
    tags = release_tags(repo)
    if not tags:
        return None, "the repository has no release tag vX.Y.Z; set update_channel to development to follow its main branch"
    skipped = ""
    for _, tag in tags:
        ref = f"refs/tags/{tag}"
        code, kind = _git_text(repo, "cat-file", "-t", ref)
        if code != 0 or kind != "tag":
            skipped = skipped or f"{tag} is lightweight (not an annotated, signed tag)"
            continue
        code, detail = _git_text(repo, "-c", "gpg.format=ssh", "-c", f"gpg.ssh.allowedSignersFile={signers}", "verify-tag", ref)
        if code != 0:
            skipped = skipped or f"{tag} is not signed by a trusted key" + (f" ({detail.splitlines()[-1]})" if detail else "")
            continue
        code, sha = _git_text(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
        if code == 0 and sha:
            return sha, tag
    return None, "no release tag is signed by a trusted key" + (f" ({skipped})" if skipped else "") + "; set update_channel to development to follow the main branch"


def verify_range(repo: Path, base: str, tip: str, policy: SignaturePolicy, *, limit: int = 200) -> str | None:
    """None when every commit that `tip` brings over `base` is acceptable under `policy`, otherwise the reason. Verifying only the tip would let an unsigned commit ride in under a
    signed one. A disabled policy accepts everything; a range longer than `limit` commits is refused (a person reads it first)."""
    if policy.signed_tags_only:   # the signed tag covers the whole history under it, so the tip is what is checked
        refused = signed_tag_refusal(repo, tip, policy)
        if refused:
            return refused
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
    if policy.signed_tags_only:
        refused = signed_tag_refusal(repo, revision, policy)
        if refused:
            return refused
    if not policy.required:
        return None
    return unsigned_reason(repo, revision, policy)
