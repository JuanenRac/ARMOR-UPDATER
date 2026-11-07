"""Put the APK of ARMOR-ANDROID-CONTROL on a phone connected with ``adb``, after checking it.

The updater already knows which version of a project is on GitHub; this is the other half for the phone app: take the APK of a release (or a file given by hand),
refuse it unless its SHA-256 is the one the release publishes, optionally refuse it unless the certificate it is signed with is one the owner pinned, and only then run
``adb install -r`` on ONE device that is authorised. Nothing is changed without ``--apply``: the default is a plan that says what would be done.

Every outside thing (the network, ``adb``, ``apksigner``) is reached through a function that is passed in, so the checks run in tests without a phone.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

OWNER = "JuanenRac"
DEFAULT_PROJECT = "ARMOR-ANDROID-CONTROL"
MAX_APK_BYTES = 200 * 1024 * 1024
HEX64 = re.compile(r"\b([0-9a-fA-F]{64})\b")
SIGNER_DIGEST = re.compile(r"certificate SHA-256 digest:\s*([0-9a-fA-F:]{64,95})")

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    model: str = ""


@dataclass
class ApkInstall:
    ok: bool = False
    applied: bool = False
    steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    refusal: str = ""

    def refuse(self, reason: str) -> "ApkInstall":
        self.ok = False
        self.refusal = reason
        return self


def parse_devices(text: str) -> list[Device]:
    """The devices of ``adb devices -l``: serial, state (device, unauthorized, offline) and the model when it says one."""
    found: list[Device] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2 or parts[0] == "List" or parts[0].startswith("*"):
            continue
        model = next((item[6:] for item in parts[2:] if item.startswith("model:")), "")
        found.append(Device(parts[0], parts[1], model))
    return found


def expected_hash(text: str) -> str | None:
    """The first 64-digit hexadecimal word of a published hash file (``<hash>  <name>`` or the hash alone), in lower case."""
    match = HEX64.search(text)
    return match.group(1).lower() if match else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalise_fingerprint(value: str) -> str:
    return value.replace(":", "").strip().lower()


def signer_fingerprints(apksigner_output: str) -> set[str]:
    """The SHA-256 digests of the certificates in the output of ``apksigner verify --print-certs``."""
    return {normalise_fingerprint(item) for item in SIGNER_DIGEST.findall(apksigner_output)}


def release_assets(project: str = DEFAULT_PROJECT, owner: str = OWNER, opener: Callable[[str], bytes] | None = None) -> tuple[str, dict[str, str]]:
    """(tag, {asset name: download address}) of the newest release of the project."""
    fetch = opener or _fetch
    data = json.loads(fetch(f"https://api.github.com/repos/{owner}/{project}/releases/latest").decode("utf-8"))
    return str(data.get("tag_name", "")), {str(item["name"]): str(item["browser_download_url"]) for item in data.get("assets", []) if "name" in item and "browser_download_url" in item}


def _fetch(address: str) -> bytes:
    if not address.startswith("https://"):
        raise ValueError("only https addresses are fetched")
    request = urllib.request.Request(address, headers={"User-Agent": "armor-updater"})
    with urllib.request.urlopen(request, timeout=30) as answer:   # noqa: S310 - https only, checked above
        data = answer.read(MAX_APK_BYTES + 1)
    if len(data) > MAX_APK_BYTES:
        raise ValueError("the download is larger than an APK of this app can be")
    return data


def choose_assets(assets: dict[str, str]) -> tuple[str, str] | None:
    """(apk name, hash file name) of a release: one ``.apk`` and the file ``<apk>.sha256`` (or ``.sha256sum``) next to it."""
    apks = sorted(name for name in assets if name.lower().endswith(".apk"))
    if len(apks) != 1:
        return None
    for suffix in (".sha256", ".sha256sum"):
        if apks[0] + suffix in assets:
            return apks[0], apks[0] + suffix
    return None


def pick_device(devices: list[Device], serial: str = "") -> tuple[Device | None, str]:
    """The one device to install on, or why there is none: with a serial it must be that one, without it there must be exactly one ready device."""
    if serial:
        match = next((item for item in devices if item.serial == serial), None)
        if match is None:
            return None, f"no device with the serial {serial} is connected"
        if match.state != "device":
            return None, f"{serial} is {match.state}" + (" - accept the debugging question on the phone" if match.state == "unauthorized" else "")
        return match, ""
    ready = [item for item in devices if item.state == "device"]
    if not ready:
        waiting = [item for item in devices if item.state != "device"]
        return None, "no authorised device is connected" + (f" ({waiting[0].serial} is {waiting[0].state})" if waiting else "")
    if len(ready) > 1:
        return None, "more than one device is connected: say which with --serial (" + ", ".join(item.serial for item in ready) + ")"
    return ready[0], ""


def install_apk(
    apk: Path,
    sha256: str,
    *,
    apply: bool = False,
    serial: str = "",
    cert_sha256: str = "",
    adb: str = "adb",
    apksigner: str = "",
    run: Runner | None = None,
) -> ApkInstall:
    """Check the APK and, with ``apply``, install it on the one authorised device. ``sha256`` is the hash the release publishes (required: an APK without one is refused)."""
    execute = run or _run
    result = ApkInstall()
    wanted = (sha256 or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", wanted):
        return result.refuse("the hash the release publishes is missing or is not a SHA-256: the APK is not installed without it")
    if not apk.is_file():
        return result.refuse(f"{apk} is not a file")
    actual = file_sha256(apk)
    if actual != wanted:
        return result.refuse("the APK does not match the hash the release publishes: nothing was installed")
    result.steps.append("the SHA-256 of the APK is the one the release publishes")

    pinned = normalise_fingerprint(cert_sha256)
    if pinned:
        if not re.fullmatch(r"[0-9a-f]{64}", pinned):
            return result.refuse("--cert-sha256 is not a SHA-256 fingerprint")
        tool = apksigner or shutil.which("apksigner") or ""
        if not tool:
            return result.refuse("a certificate was pinned but apksigner (Android build-tools) is not available to read the one in the APK")
        verified = execute([tool, "verify", "--print-certs", str(apk)])
        if verified.returncode != 0:
            return result.refuse("apksigner does not accept the signature of the APK")
        if pinned not in signer_fingerprints(verified.stdout):
            return result.refuse("the APK is signed with a certificate other than the pinned one: nothing was installed")
        result.steps.append("it is signed with the pinned certificate")
    else:
        result.warnings.append("no certificate was pinned (--cert-sha256): the hash proves the file is the release's, not who signed it")

    listing = execute([adb, "devices", "-l"])
    if listing.returncode != 0:
        return result.refuse("adb could not list the devices")
    device, why = pick_device(parse_devices(listing.stdout), serial)
    if device is None:
        return result.refuse(why)
    result.steps.append(f"the phone is {device.serial}" + (f" ({device.model})" if device.model else ""))
    if not apply:
        result.ok = True
        result.steps.append("dry run: add --apply to run adb install -r")
        return result
    done = execute([adb, "-s", device.serial, "install", "-r", str(apk)])
    if done.returncode != 0 or "Success" not in (done.stdout or ""):
        reason = next((line.strip() for line in reversed(((done.stdout or "") + (done.stderr or "")).splitlines()) if line.strip()), "no answer")
        return result.refuse(f"adb install failed: {reason[:200]}")
    result.ok = True
    result.applied = True
    result.steps.append("installed over the previous version (data is kept)")
    return result


def _run(command: list[str]) -> "subprocess.CompletedProcess[str]":
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(command, 127, "", str(error))
