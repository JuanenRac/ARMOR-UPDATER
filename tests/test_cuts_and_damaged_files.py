# =============================================================================
# ARMOR-UPDATER - tests/test_cuts_and_damaged_files.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Downloads cut in the middle, and files of the updater or of a workspace that are damaged or saved in another encoding.
The network is replaced by functions, so nothing leaves the machine."""
from __future__ import annotations

import argparse
import http.client
import io
import json
import sys
import urllib.error

import pytest

from armor_updater import android_apk, detect, evidence, github_client, profiles, settings
from armor_updater import main as main_module


def manifest_text(name: str) -> str:
    return json.dumps({
        "schema_version": "1.0", "ecosystem": "A.R.M.O.R.", "name": name, "version": "1.0.0", "role": "service", "stack": "python", "technologies": ["Python"],
        "deployment_target": "The central server", "maturity": "functional", "family": "Test", "parent": None, "native_version": "1.0.0", "build": "", "notes": "x",
    })


@pytest.fixture(autouse=True)
def _own_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(settings, "_LEGACY_LANG_PATH", tmp_path / "lang.json")


@pytest.mark.parametrize("raw", [
    '{"lang": "es"}'.encode("utf-16"),
    b'{"workspace_root": "C:\\\\proyectos\\\\se\xf1al"}',   # latin-1
    '{"nota": "日'.encode()[:-1],                            # cut inside a character
])
def test_a_settings_file_in_another_encoding_or_cut_never_raises(raw):
    settings.SETTINGS_PATH.write_bytes(raw)
    settings._LEGACY_LANG_PATH.write_bytes(raw)
    assert settings.load_settings() == {}
    assert settings.get_saved_lang() is None
    assert settings.settings_damaged()
    settings.save_settings(lang="es")
    assert settings.SETTINGS_PATH.read_bytes() == raw   # left as it was, not overwritten


def test_a_settings_file_with_a_byte_order_mark_is_read():
    settings.SETTINGS_PATH.write_bytes(b'\xef\xbb\xbf{"lang": "es", "backups_to_keep": 3}')
    assert settings.load_settings()["backups_to_keep"] == 3
    assert settings.get_saved_lang() == "es"
    assert not settings.settings_damaged()


def test_one_folder_with_an_unreadable_manifest_does_not_hide_the_others(tmp_path):
    workspace = tmp_path / "workspace"
    for name, raw in (("ARMOR-GOOD", manifest_text("ARMOR-GOOD").encode()), ("ARMOR-LATIN", b'{"notes": "se\xf1al"}')):
        (workspace / name).mkdir(parents=True)
        (workspace / name / "armor.project.json").write_bytes(raw)
    found = detect.discover_workspace(workspace)
    assert [status.entry.name for status in found.projects] == ["ARMOR-GOOD"]
    assert len(found.errors) == 1 and "ARMOR-LATIN" in found.errors[0]


@pytest.mark.parametrize("raw", [b"[1, 2]", b'"text"', b"\xff\xfe{", b"{ cut"])
def test_the_installed_state_of_a_damaged_manifest_is_unknown(tmp_path, raw):
    (tmp_path / "armor.project.json").write_bytes(raw)
    assert evidence.installed_state(tmp_path)["version"] is None


def test_a_cut_line_of_evidence_hides_neither_the_others_nor_the_next_one(tmp_path):
    path = tmp_path / evidence.EVIDENCE_DIRECTORY / evidence.EVIDENCE_FILE
    path.parent.mkdir()
    path.write_bytes(b'{"project": "A"}\n[1]\n{"project": "\xf1"}\n{"project": "B", "mess')   # the last line was cut: no end
    evidence.record_attempt(tmp_path, project="C", before={}, after={}, ok=True, message="")
    assert [line["project"] for line in evidence.read_attempts(tmp_path)] == ["A", "C"]


def test_a_profiles_file_of_the_workspace_in_another_encoding_falls_back_to_the_shipped_one(tmp_path):
    damaged = tmp_path.joinpath(*profiles.DOCS_PROFILES)
    damaged.parent.mkdir(parents=True)
    damaged.write_bytes('{"schema_version": "1.0"}'.encode("utf-16"))
    assert profiles.load_profiles(tmp_path) == profiles.parse_profiles(profiles.BUNDLED_PROFILES.read_text(encoding="utf-8"))


class CutAnswer(io.BytesIO):
    headers = None

    def read(self, *args):
        raise http.client.IncompleteRead(b"{", 100)


def test_a_download_cut_in_the_middle_is_asked_again():
    answers = [CutAnswer(), CutAnswer(), io.BytesIO(b"whole")]
    body = github_client._urlopen_with_retries(object(), timeout=1, max_attempts=3, opener=lambda request, timeout: answers.pop(0), sleep=lambda s: None)
    assert body == b"whole"


def _network(monkeypatch, answers):
    """`answers(url)` returns bytes or raises; the real retry loop runs around it."""
    original = github_client._urlopen_with_retries

    def opener(request, **_kwargs):
        return io.BytesIO(answers(request.full_url))

    monkeypatch.setattr(github_client, "_urlopen_with_retries", lambda request, **kw: original(request, opener=opener, sleep=lambda s: None, **kw))
    monkeypatch.setattr(github_client, "_remote_tip", lambda *a: None)


def test_a_cut_repository_listing_is_a_message(monkeypatch):
    def answers(url):
        raise http.client.IncompleteRead(b"[", 100)

    _network(monkeypatch, answers)
    with pytest.raises(RuntimeError, match="unable to list"):
        github_client.discover_remote_projects("someone", token="")


def test_a_cut_manifest_does_not_end_the_discovery_of_the_others(monkeypatch):
    def answers(url):
        if "/users/" in url:
            return json.dumps([{"name": "ARMOR-CUT"}, {"name": "ARMOR-GOOD"}]).encode()
        if "ARMOR-CUT" in url:
            raise http.client.IncompleteRead(b"{", 100)
        if "ARMOR-GOOD" in url:
            return manifest_text("ARMOR-GOOD").encode()
        raise urllib.error.HTTPError(url, 404, "not found", None, None)

    _network(monkeypatch, answers)
    found = github_client.discover_remote_projects("someone", token="")
    assert [status.entry.name for status in found.projects] == ["ARMOR-GOOD"]
    assert len(found.errors) == 1 and "ARMOR-CUT" in found.errors[0]


class Download(io.BytesIO):
    def __init__(self, body: bytes, declared: int) -> None:
        super().__init__(body)
        self.headers = {"Content-Length": str(declared)}


def test_an_apk_that_arrives_short_is_reported_as_cut(monkeypatch):
    monkeypatch.setattr(android_apk.urllib.request, "urlopen", lambda *a, **k: Download(b"half", 100))
    with pytest.raises(ValueError, match="cut: 4 of 100"):
        android_apk._fetch("https://example.invalid/a.apk")
    monkeypatch.setattr(android_apk.urllib.request, "urlopen", lambda *a, **k: Download(b"whole", 5))
    assert android_apk._fetch("https://example.invalid/a.apk") == b"whole"


def test_an_apk_download_that_breaks_is_a_value_error(monkeypatch):
    monkeypatch.setattr(android_apk.urllib.request, "urlopen", lambda *a, **k: CutAnswer())
    with pytest.raises(ValueError, match="cut"):
        android_apk._fetch("https://example.invalid/a.apk")


def test_a_release_answer_that_is_not_an_object_is_refused():
    with pytest.raises(ValueError):
        android_apk.release_assets(opener=lambda address: b"[]")


@pytest.mark.parametrize("error", [urllib.error.URLError("no network"), http.client.RemoteDisconnected("gone"), TimeoutError("slow")])
def test_a_notice_that_cannot_be_sent_is_a_message_and_a_code(monkeypatch, capsys, error):
    def status(args: argparse.Namespace) -> int:
        print(json.dumps({"offline": False, "projects": [{"name": "ARMOR-A", "state": "OUTDATED", "local_version": "1.0.0", "github_version": "1.0.1"}]}))
        return 0

    def send(*_args):
        raise error

    monkeypatch.setattr(main_module, "cmd_status", status)
    monkeypatch.setattr(main_module, "send", send)
    args = main_module.build_parser().parse_args(["notify", "--ntfy-url", "https://ntfy.sh/topic"])
    assert args.func(args) == 2
    assert "could not be sent" in capsys.readouterr().err


def test_a_name_the_console_cannot_hold_is_printed_with_a_mark(monkeypatch):
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp1252", newline="\n")
    monkeypatch.setattr(sys, "stdout", console)
    main_module._print_whatever_the_console_holds()
    print("changed: ログ.txt")
    console.flush()
    assert raw.getvalue() == b"changed: ??.txt\n"
