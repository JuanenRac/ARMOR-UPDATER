# =============================================================================
# ARMOR-UPDATER - tests/test_toolchain.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The check of the build tools a project needs: which rules apply, versions, environment variables, the command and that nothing is blocked."""
from __future__ import annotations

import json

import pytest

from armor_updater import main as main_module
from armor_updater.detect import LocalDiscovery, LocalStatus
from armor_updater.registry import ProjectEntry
from armor_updater.toolchain import check_tools, format_findings, load_rules, needed_rules, parse_version
from armor_updater.version_parse import Version


def entry(stack="TypeScript / Node.js", tech=("Node.js", "SQLite"), note="npm run build", name="ARMOR-X"):
    return ProjectEntry(name=name, stack=stack, tech=tuple(tech), note=note)


def test_the_shipped_rules_are_well_formed():
    rules = load_rules()
    assert {r["tool"] for r in rules} >= {"Node.js", "Java JDK", "ESP-IDF", "OpenSCAD"}


@pytest.mark.parametrize("text", ['{"rules": []}', '{"rules": [{"tool": "x"}]}', '{"rules": [{"tool": "x", "words": ["a"]}]}', "{}"])
def test_a_rule_that_is_not_well_formed_is_an_error(text):
    with pytest.raises(ValueError):
        load_rules(text)


def test_the_rules_that_apply_follow_the_stack():
    rules = load_rules()
    assert [r["tool"] for r in needed_rules(entry(), rules)] == ["Node.js"]
    android = entry("Kotlin / Jetpack Compose", ("Android", "Gradle"), "gradlew assembleDebug")
    assert {r["tool"] for r in needed_rules(android, rules)} == {"Java JDK", "Android SDK"}
    firmware = entry("C++ / ESP-IDF", ("ESP32-S3",), "idf.py build")
    assert [r["tool"] for r in needed_rules(firmware, rules)] == ["ESP-IDF"]
    assert needed_rules(entry("Python 3.10+", ("Python",), "pytest"), rules) == []


@pytest.mark.parametrize("text, expected", [("v22.11.0", (22, 11)), ('openjdk version "17.0.9" 2023', (17, 0)), ('java version "1.8.0_392"', (8, 0)), ("nothing", None)])
def test_versions_are_read_from_the_output(text, expected):
    assert parse_version(text) == expected


def test_a_missing_program_an_old_one_and_a_good_one():
    rules = load_rules()
    found = {"node": "/usr/bin/node"}
    missing = check_tools(entry(), rules, which=lambda p: None, run=lambda c: "", environ={})
    assert [(f.status, f.tool) for f in missing] == [("missing", "Node.js")] and "22" in missing[0].hint
    old = check_tools(entry(), rules, which=found.get, run=lambda c: "v20.1.0", environ={})
    assert old[0].status == "old" and "22 or newer" in old[0].detail
    good = check_tools(entry(), rules, which=found.get, run=lambda c: "v22.3.0", environ={})
    assert good[0].status == "ok"
    unreadable = check_tools(entry(), rules, which=found.get, run=lambda c: "garbled", environ={})
    assert unreadable[0].status == "old"


def test_an_environment_variable_rule():
    firmware = entry("C++ / ESP-IDF", ("ESP32-S3",), "idf.py build")
    rules = load_rules()
    assert check_tools(firmware, rules, environ={})[0].status == "missing"
    assert check_tools(firmware, rules, environ={"IDF_PATH": "/opt/esp-idf"})[0].status == "ok"


def test_a_program_that_fails_to_run_is_not_a_crash():
    def fails(command):
        raise OSError("boom")
    assert check_tools(entry(), load_rules(), which={"node": "x"}.get, run=fails, environ={})[0].status == "old"


def test_the_lines_say_what_to_do_and_a_stack_without_rules_is_said_so():
    findings = check_tools(entry(), load_rules(), which=lambda p: None, run=lambda c: "", environ={})
    assert format_findings(entry(), findings)[0].startswith("MISSING Node.js") and "install Node.js" in format_findings(entry(), findings)[0]
    assert "no build tool is known" in format_findings(entry("Python", ("Python",), ""), [])[0]


def test_the_command_reports_with_its_exit_code(tmp_path, monkeypatch, capsys):
    status = LocalStatus(entry=entry(), path=tmp_path / "ARMOR-X", installed=True, version=Version(0, 1, 0))
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: LocalDiscovery(projects=(status,), errors=()))
    monkeypatch.setattr(main_module, "check_tools", lambda e: check_tools(e, load_rules(), which=lambda p: None, run=lambda c: "", environ={}))
    args = main_module.build_parser().parse_args(["tools", "ARMOR-X", "--workspace", str(tmp_path)])
    assert args.func(args) == 1
    assert "MISSING Node.js" in capsys.readouterr().out
    args = main_module.build_parser().parse_args(["tools", "ARMOR-NOPE", "--workspace", str(tmp_path)])
    monkeypatch.setattr(main_module, "discover_remote_projects", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    assert args.func(args) == 2
    assert "tools" in main_module.COMMAND_WORDS


def test_the_rules_file_is_valid_json_in_the_package():
    from importlib import resources
    json.loads((resources.files("armor_updater") / "data" / "toolchain_rules.json").read_text(encoding="utf-8"))
