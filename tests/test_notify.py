# =============================================================================
# ARMOR-UPDATER - tests/test_notify.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The notice of outdated projects for a scheduled task: the summary, the address check, the ntfy POST against a local server and the command's exit codes."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from armor_updater import main as main_module
from armor_updater.notify import check_url, send, summarize


def payload(*states, offline=False):
    return {"offline": offline, "projects": [{"name": f"ARMOR-{i}", "state": s, "local_version": "0.1.0", "github_version": "0.2.0"} for i, s in enumerate(states)]}


def test_nothing_outdated_is_no_message():
    assert summarize(payload("up to date", "not installed")) is None
    assert summarize({}) is None


def test_the_message_lists_what_is_outdated():
    title, body = summarize(payload("OUTDATED", "up to date", "OUTDATED"))
    assert title == "A.R.M.O.R.: 2 projects to update"
    assert body.splitlines() == ["ARMOR-0: 0.1.0 -> 0.2.0", "ARMOR-2: 0.1.0 -> 0.2.0"]
    assert summarize(payload("OUTDATED"))[0].endswith("1 project to update")


def test_a_long_list_is_cut():
    _title, body = summarize(payload(*["OUTDATED"] * 25))
    assert len(body.splitlines()) == 21 and body.splitlines()[-1] == "... and 5 more"


@pytest.mark.parametrize("url", ["ftp://x/y", "https://user:pw@ntfy.sh/t", "https://", "ntfy.sh/topic", "https://ntfy.sh/t#frag", ""])
def test_only_a_plain_address_is_accepted(url):
    with pytest.raises(ValueError):
        check_url(url)


class Topic(BaseHTTPRequestHandler):
    seen: list[tuple[str, str]] = []
    status = 200

    def do_POST(self):  # noqa: N802
        Topic.seen.append((self.headers.get("Title", ""), self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")))
        self.send_response(Topic.status)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture()
def topic():
    Topic.seen, Topic.status = [], 200
    server = HTTPServer(("127.0.0.1", 0), Topic)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/armor"
    server.shutdown()
    server.server_close()


def fake_status(monkeypatch, data, code=0):
    def status(args):
        print(json.dumps(data))
        return code
    monkeypatch.setattr(main_module, "cmd_status", status)


def run(*argv):
    args = main_module.build_parser().parse_args(["notify", *argv])
    return args.func(args)


def test_the_message_reaches_the_topic(monkeypatch, topic, capsys):
    fake_status(monkeypatch, payload("OUTDATED"))
    assert run("--ntfy-url", topic) == 0
    assert Topic.seen == [("A.R.M.O.R.: 1 project to update", "ARMOR-0: 0.1.0 -> 0.2.0")]
    assert "ARMOR-0" in capsys.readouterr().out


def test_without_an_address_it_only_prints(monkeypatch, capsys):
    fake_status(monkeypatch, payload("OUTDATED"))
    assert run() == 0
    assert "1 project to update" in capsys.readouterr().out


def test_nothing_outdated_sends_nothing(monkeypatch, topic, capsys):
    fake_status(monkeypatch, payload("up to date"))
    assert run("--ntfy-url", topic) == 0
    assert Topic.seen == [] and capsys.readouterr().out == ""


def test_a_refused_notice_or_a_bad_address_or_no_github_is_exit_2(monkeypatch, topic):
    fake_status(monkeypatch, payload("OUTDATED"))
    Topic.status = 500
    assert run("--ntfy-url", topic) == 2
    assert run("--ntfy-url", "https://user:pw@ntfy.sh/t") == 2
    fake_status(monkeypatch, payload("OUTDATED", offline=True))
    assert run() == 2
    fake_status(monkeypatch, payload("OUTDATED"), code=1)
    assert run() == 2
    monkeypatch.setattr(main_module, "cmd_status", lambda args: print("not json") or 0)
    assert run() == 2


def test_send_returns_the_status(topic):
    assert send(topic, "title", "body") == 200
    Topic.status = 404
    assert send(topic, "title", "body") == 404


def test_the_word_is_a_command_word():
    assert "notify" in main_module.COMMAND_WORDS
