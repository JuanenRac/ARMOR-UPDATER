# =============================================================================
# ARMOR-UPDATER - tests/test_main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

from armor_updater import main as main_module
from armor_updater.detect import LocalDiscovery, LocalStatus
from armor_updater.github_client import RemoteDiscovery, RemoteStatus
from armor_updater.main import build_parser
from armor_updater.registry import ProjectEntry
from armor_updater.version_parse import Version


def test_status_command_parses() -> None:
    args = build_parser().parse_args(["status"])
    assert args.command == "status"
    assert args.json is False


def test_status_json_flag_parses() -> None:
    args = build_parser().parse_args(["status", "--json"])
    assert args.json is True


def test_status_json_output_is_real_machine_readable_json(monkeypatch, capsys, tmp_path) -> None:
    """Real end-to-end of cmd_status's own --json branch, against fake
    (not network/filesystem) local+remote discovery - discover_workspace/
    discover_remote_projects already have their own real coverage
    elsewhere; this test is about the CLI's own JSON shape."""
    installed_entry = ProjectEntry(name="ARMOR-COMMON", stack="python", native_version="0.0.2", maturity="established", role="library")
    missing_entry = ProjectEntry(name="ARMOR-GHOST", stack="python", native_version="1.0.0", maturity="scaffolding", role="service")

    local_discovery = LocalDiscovery(
        projects=(
            LocalStatus(entry=installed_entry, path=tmp_path / "ARMOR-COMMON", installed=True, version=Version(0, 0, 2)),
        ),
        errors=(),
    )
    remote_discovery = RemoteDiscovery(
        projects=(
            RemoteStatus(entry=installed_entry, version=Version(0, 0, 3)),
            RemoteStatus(entry=missing_entry, version=Version(1, 0, 0)),
        ),
        errors=(),
    )
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: local_discovery)
    monkeypatch.setattr(main_module, "discover_remote_projects", lambda: remote_discovery)

    args = build_parser().parse_args(["status", "--json", "--workspace", str(tmp_path)])
    exit_code = args.func(args)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["workspace_root"] == str(tmp_path)
    assert payload["total"] == 2
    assert payload["installed_count"] == 1
    assert payload["outdated_count"] == 1
    by_name = {p["name"]: p for p in payload["projects"]}
    assert by_name["ARMOR-COMMON"]["installed"] is True
    assert by_name["ARMOR-COMMON"]["local_version"] == "0.0.2"
    assert by_name["ARMOR-COMMON"]["github_version"] == "0.0.3"
    assert by_name["ARMOR-COMMON"]["state"] == "OUTDATED"
    assert by_name["ARMOR-GHOST"]["installed"] is False
    assert by_name["ARMOR-GHOST"]["local_version"] is None


# =============================================================================
# resolve_workspace_root() - real user request: remember a chosen
# workspace root across GUI launches instead of resetting to
# default_workspace_root() every time.
# =============================================================================


def test_resolve_workspace_root_uses_the_real_saved_one_when_present(monkeypatch, tmp_path) -> None:
    from armor_updater import settings

    real_dir = tmp_path / "saved-workspace"
    real_dir.mkdir()
    monkeypatch.setattr(settings, "get_saved_workspace_root", lambda: real_dir)
    assert main_module.resolve_workspace_root() == real_dir


def test_resolve_workspace_root_falls_back_to_the_real_default_when_nothing_saved(monkeypatch) -> None:
    from armor_updater import settings

    monkeypatch.setattr(settings, "get_saved_workspace_root", lambda: None)
    assert main_module.resolve_workspace_root() == main_module.default_workspace_root()
