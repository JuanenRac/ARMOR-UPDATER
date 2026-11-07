# =============================================================================
# ARMOR-UPDATER - tests/test_android_apk.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The APK of the phone app: refused unless its hash is the published one (and its certificate the pinned one), installed over the previous version on one authorised
phone, and only with --apply. adb, apksigner and the network are replaced by functions that record what they were asked."""
from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from armor_updater import android_apk, main as main_module
from armor_updater.android_apk import Device, choose_assets, expected_hash, install_apk, parse_devices, pick_device, signer_fingerprints

APK_BYTES = b"PK\x03\x04 not really an apk, only bytes with a hash"
HASH = hashlib.sha256(APK_BYTES).hexdigest()
CERT = "ab" * 32
DEVICES = "List of devices attached\nR58M123ABC          device usb:1-1 product:x model:Pixel_8 device:y transport_id:1\n"


def completed(code=0, out="", err=""):
    return subprocess.CompletedProcess([], code, out, err)


class Recorder:
    """A stand-in for subprocess.run that answers by the program asked."""

    def __init__(self, devices=DEVICES, install=(0, "Performing Streamed Install\nSuccess\n"), signer=(0, f"Signer #1 certificate SHA-256 digest: {CERT}\n")):
        self.calls, self.devices, self.install, self.signer = [], devices, install, signer

    def __call__(self, command):
        self.calls.append(command)
        if "devices" in command:
            return completed(0, self.devices)
        if "install" in command:
            return completed(self.install[0], self.install[1])
        return completed(self.signer[0], self.signer[1])

    def installs(self):
        return [call for call in self.calls if "install" in call]


@pytest.fixture
def apk(tmp_path):
    path = tmp_path / "ARMOR-ANDROID-CONTROL-release.apk"
    path.write_bytes(APK_BYTES)
    return path


def test_the_devices_of_adb_are_read_with_their_state_and_model():
    text = "List of devices attached\nR58 device usb:1 model:Pixel_8 device:y\nEMU offline\n* daemon started *\n\nQ1 unauthorized usb:2\n"
    assert parse_devices(text) == [Device("R58", "device", "Pixel_8"), Device("EMU", "offline", ""), Device("Q1", "unauthorized", "")]
    assert parse_devices("") == []


def test_the_published_hash_is_found_in_either_format_and_lowered():
    assert expected_hash(f"{HASH.upper()}  app.apk\n") == HASH
    assert expected_hash(HASH) == HASH
    assert expected_hash("not a hash") is None
    assert expected_hash("abc123") is None


def test_the_certificates_are_read_from_the_output_of_apksigner():
    out = f"Signer #1 certificate DN: CN=x\nSigner #1 certificate SHA-256 digest: {CERT}\nSigner #2 certificate SHA-256 digest: {':'.join(['cd'] * 32)}\n"
    assert signer_fingerprints(out) == {CERT, "cd" * 32}
    assert signer_fingerprints("nothing") == set()


def test_one_apk_and_its_hash_file_are_chosen_from_a_release_and_nothing_else_is_guessed():
    assert choose_assets({"a.apk": "u1", "a.apk.sha256": "u2", "notes.txt": "u3"}) == ("a.apk", "a.apk.sha256")
    assert choose_assets({"a.apk": "u1", "a.apk.sha256sum": "u2"}) == ("a.apk", "a.apk.sha256sum")
    assert choose_assets({"a.apk": "u1"}) is None
    assert choose_assets({"a.apk": "u1", "b.apk": "u2", "a.apk.sha256": "u3"}) is None
    assert choose_assets({}) is None


def test_the_release_is_read_from_the_api_with_its_assets():
    answer = json.dumps({"tag_name": "v1", "assets": [{"name": "a.apk", "browser_download_url": "https://x/a.apk"}, {"name": "broken"}]}).encode()
    asked = []
    tag, assets = android_apk.release_assets("ARMOR-ANDROID-CONTROL", opener=lambda address: asked.append(address) or answer)
    assert (tag, assets) == ("v1", {"a.apk": "https://x/a.apk"})
    assert asked == ["https://api.github.com/repos/JuanenRac/ARMOR-ANDROID-CONTROL/releases/latest"]


def test_nothing_is_fetched_over_a_plain_address():
    with pytest.raises(ValueError):
        android_apk._fetch("http://example.invalid/a.apk")


@pytest.mark.parametrize("devices, serial, expected", [
    ([], "", "no authorised device is connected"),
    ([Device("A", "unauthorized")], "", "A is unauthorized"),
    ([Device("A", "device"), Device("B", "device")], "", "more than one device"),
    ([Device("A", "device")], "Z", "no device with the serial Z"),
    ([Device("A", "unauthorized")], "A", "accept the debugging question"),
    ([Device("A", "offline")], "A", "A is offline"),
])
def test_the_phone_is_never_guessed(devices, serial, expected):
    chosen, why = pick_device(devices, serial)
    assert chosen is None and expected in why


def test_one_ready_phone_is_taken_and_a_serial_picks_among_several():
    assert pick_device([Device("A", "device")], "")[0] == Device("A", "device")
    assert pick_device([Device("A", "device"), Device("B", "device")], "B")[0] == Device("B", "device")


def test_without_apply_it_checks_everything_and_installs_nothing(apk):
    run = Recorder()
    result = install_apk(apk, HASH, run=run)
    assert result.ok and not result.applied
    assert "dry run" in result.steps[-1]
    assert run.installs() == []
    assert any("no certificate was pinned" in warning for warning in result.warnings)


def test_with_apply_it_installs_over_the_previous_version_on_that_phone_only(apk):
    run = Recorder()
    result = install_apk(apk, HASH, apply=True, run=run)
    assert result.ok and result.applied
    assert run.installs() == [["adb", "-s", "R58M123ABC", "install", "-r", str(apk)]]


def test_a_hash_that_is_missing_or_wrong_refuses_before_adb_is_asked(apk):
    for wrong, why in (("", "missing"), ("abc", "missing"), ("0" * 64, "does not match")):
        run = Recorder()
        result = install_apk(apk, wrong, apply=True, run=run)
        assert not result.ok and why in result.refusal
        assert run.calls == []


def test_a_file_that_is_not_there_is_refused(tmp_path):
    result = install_apk(tmp_path / "nope.apk", HASH, apply=True, run=Recorder())
    assert not result.ok and "is not a file" in result.refusal


def test_a_pinned_certificate_must_be_the_one_in_the_apk(apk):
    ok = install_apk(apk, HASH, apply=True, cert_sha256=CERT.upper(), apksigner="apksigner", run=Recorder())
    assert ok.ok and not ok.warnings
    other = install_apk(apk, HASH, apply=True, cert_sha256="cd" * 32, apksigner="apksigner", run=(run := Recorder()))
    assert not other.ok and "other than the pinned one" in other.refusal
    assert run.installs() == []
    bad_pin = install_apk(apk, HASH, apply=True, cert_sha256="12", apksigner="apksigner", run=Recorder())
    assert not bad_pin.ok and "not a SHA-256" in bad_pin.refusal
    unsigned = install_apk(apk, HASH, apply=True, cert_sha256=CERT, apksigner="apksigner", run=Recorder(signer=(1, "")))
    assert not unsigned.ok and "does not accept the signature" in unsigned.refusal


def test_a_pinned_certificate_without_apksigner_is_refused_not_skipped(apk, monkeypatch):
    monkeypatch.setattr(android_apk.shutil, "which", lambda name: None)
    result = install_apk(apk, HASH, apply=True, cert_sha256=CERT, run=Recorder())
    assert not result.ok and "apksigner" in result.refusal


def test_an_install_that_adb_does_not_confirm_is_a_failure(apk):
    result = install_apk(apk, HASH, apply=True, run=Recorder(install=(1, "Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]\n")))
    assert not result.ok and not result.applied and "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in result.refusal
    silent = install_apk(apk, HASH, apply=True, run=Recorder(install=(0, "")))
    assert not silent.ok
    listing = install_apk(apk, HASH, apply=True, run=lambda command: completed(1))
    assert not listing.ok and "could not list" in listing.refusal


def test_the_command_checks_a_file_and_says_what_it_would_do(apk, monkeypatch, capsys):
    recorder = Recorder()
    monkeypatch.setattr(android_apk, "_run", recorder)
    args = main_module.build_parser().parse_args(["android", "--apk", str(apk), "--sha256", HASH])
    code = args.func(args)
    out = capsys.readouterr().out
    assert code == 0
    assert "dry run" in out and recorder.installs() == []


def test_the_command_reads_the_hash_from_the_published_file_and_refuses_a_wrong_one(apk, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(android_apk, "_run", Recorder())
    published = tmp_path / "apk.sha256"
    published.write_text(f"{'1' * 64}  {apk.name}\n", encoding="utf-8")
    args = main_module.build_parser().parse_args(["android", "--apk", str(apk), "--sha256-file", str(published), "--apply"])
    assert args.func(args) == 1
    assert "does not match" in capsys.readouterr().err
    published.write_text(f"{HASH}  {apk.name}\n", encoding="utf-8")
    args = main_module.build_parser().parse_args(["android", "--apk", str(apk), "--sha256-file", str(published), "--apply"])
    assert args.func(args) == 0


def test_the_command_downloads_the_release_when_no_file_is_given(monkeypatch, capsys):
    recorder = Recorder()
    monkeypatch.setattr(android_apk, "_run", recorder)
    assets = {"app.apk": "https://x/app.apk", "app.apk.sha256": "https://x/app.apk.sha256"}
    monkeypatch.setattr(android_apk, "release_assets", lambda project, *a, **k: ("v9", assets))
    monkeypatch.setattr(android_apk, "_fetch", lambda address: APK_BYTES if address.endswith(".apk") else f"{HASH}  app.apk\n".encode())
    args = main_module.build_parser().parse_args(["android", "--apply"])
    assert args.func(args) == 0
    assert "release v9: app.apk" in capsys.readouterr().out
    assert len(recorder.installs()) == 1
    monkeypatch.setattr(android_apk, "release_assets", lambda project, *a, **k: ("v9", {"app.apk": "https://x/app.apk"}))
    assert args.func(args) == 1
    assert "nothing to install" in capsys.readouterr().err


def test_a_download_that_fails_is_an_error_not_a_crash(monkeypatch, capsys):
    monkeypatch.setattr(android_apk, "release_assets", lambda project, *a, **k: (_ for _ in ()).throw(ValueError("offline")))
    args = main_module.build_parser().parse_args(["android"])
    assert args.func(args) == 1
    assert "could not be fetched" in capsys.readouterr().err


def test_the_word_android_runs_the_command_line_without_a_window():
    assert "android" in main_module.COMMAND_WORDS
