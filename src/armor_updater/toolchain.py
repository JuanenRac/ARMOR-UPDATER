# =============================================================================
# ARMOR-UPDATER - Check of the tools a project needs: toolchain.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Tells, before a project is cloned, which build tools its stack needs and which of them are missing.

The rules are data (``data/toolchain_rules.json``): a rule applies when one of its words appears in the stack,
the technologies or the build command of the project manifest. A rule asks for a program on the PATH (and, when
it has a ``minimum``, a version at least that), or for an environment variable. The check only reads: it runs
``<tool> --version`` with a fixed argument list and a short time limit, never through a shell, and it never
blocks an install: the result is advice.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import resources
from typing import Any

from .console_flags import NO_WINDOW
from .registry import ProjectEntry

RULES_FILE = "toolchain_rules.json"
RUN_TIMEOUT_S = 5
VERSION = re.compile(r"(\d+)(?:\.(\d+))?")


@dataclass(frozen=True)
class ToolFinding:
    tool: str
    status: str          # "ok", "missing" or "old"
    detail: str
    hint: str = ""


def load_rules(text: str | None = None) -> list[dict[str, Any]]:
    """The rules shipped with the updater (or the given JSON text); a rule that is not well formed is an error, never skipped."""
    if text is None:
        text = (resources.files("armor_updater") / "data" / RULES_FILE).read_text(encoding="utf-8")
    rules = json.loads(text).get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("toolchain rules: 'rules' must be a non-empty list")
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("tool"), str) or not rule.get("words") or not all(isinstance(w, str) for w in rule["words"]):
            raise ValueError(f"toolchain rules: a rule needs a tool name and a list of words: {rule!r}")
        if not (isinstance(rule.get("command"), list) and all(isinstance(a, str) for a in rule["command"])) and not isinstance(rule.get("environment"), list):
            raise ValueError(f"toolchain rules: {rule['tool']} needs a command or an environment list")
    return rules


def _words(entry: ProjectEntry) -> str:
    return " ".join([entry.stack, *entry.tech, entry.note]).lower()


def needed_rules(entry: ProjectEntry, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = _words(entry)
    return [rule for rule in rules if any(re.search(rf"(?<![\w.-]){re.escape(word.lower())}(?![\w-])", text) for word in rule["words"])]


def parse_version(output: str) -> tuple[int, int] | None:
    """The first version number in the output; Java's old `1.8` means 8."""
    match = VERSION.search(output)
    if not match:
        return None
    major, minor = int(match.group(1)), int(match.group(2) or 0)
    return (minor, 0) if major == 1 and match.group(2) else (major, minor)


def _run(command: list[str]) -> str:
    done = subprocess.run(command, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, shell=False, check=False, creationflags=NO_WINDOW)
    return (done.stdout or "") + (done.stderr or "")


def check_tools(entry: ProjectEntry, rules: list[dict[str, Any]] | None = None, *, which: Callable[[str], str | None] = shutil.which,
                run: Callable[[list[str]], str] = _run, environ: Mapping[str, str] | None = None) -> list[ToolFinding]:
    environ = os.environ if environ is None else environ
    findings: list[ToolFinding] = []
    for rule in needed_rules(entry, rules if rules is not None else load_rules()):
        tool, hint = rule["tool"], str(rule.get("hint", ""))
        if "command" in rule:
            program = rule["command"][0]
            if not which(program):
                findings.append(ToolFinding(tool, "missing", f"{program} is not on the PATH", hint))
                continue
            minimum = rule.get("minimum")
            if minimum:
                try:
                    found = parse_version(run(rule["command"]))
                except (OSError, subprocess.SubprocessError):
                    found = None
                wanted = parse_version(str(minimum))
                if found is None:
                    findings.append(ToolFinding(tool, "old", f"the version of {program} could not be read (needs {minimum} or newer)", hint))
                    continue
                if wanted and found < wanted:
                    findings.append(ToolFinding(tool, "old", f"{program} {found[0]}.{found[1]} found, {minimum} or newer needed", hint))
                    continue
            findings.append(ToolFinding(tool, "ok", f"{program} found"))
        else:
            names = rule["environment"]
            present = [name for name in names if environ.get(name)]
            findings.append(ToolFinding(tool, "ok", f"{present[0]} is set") if present else ToolFinding(tool, "missing", f"{' or '.join(names)} is not set", hint))
    return findings


def format_findings(entry: ProjectEntry, findings: list[ToolFinding]) -> list[str]:
    if not findings:
        return [f"{entry.name}: no build tool is known for its stack ({entry.stack})"]
    lines = []
    for finding in findings:
        mark = {"ok": "OK  ", "missing": "MISSING ", "old": "OLD "}[finding.status]
        lines.append(f"{mark}{finding.tool}: {finding.detail}" + (f" - {finding.hint}" if finding.hint and finding.status != "ok" else ""))
    return lines
