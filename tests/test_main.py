# =============================================================================
# ARMOR-UPDATER - tests/test_main.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import json
import sys
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


def test_status_table_never_runs_a_long_real_role_into_the_stack_column(monkeypatch, capsys, tmp_path) -> None:
    """Real bug: A.R.M.O.R.'s own manifest schema deliberately keeps
    `role` as free text (several real repos declare a whole sentence, not
    HYDRA-UMC/URTC's short enum) - the plain-text table used to pad it to
    a fixed 10 characters, which does nothing once the real text is
    longer than that, running it straight into STACK with no separator
    at all (e.g. "Android operator clientKotlin / Jetpack Compose")."""
    long_role = "Shared contracts and validation library"
    entry = ProjectEntry(name="ARMOR-COMMON", stack="Python 3.11+", native_version="0.2.6", maturity="functional", role=long_role)
    local_discovery = LocalDiscovery(
        projects=(LocalStatus(entry=entry, path=tmp_path / "ARMOR-COMMON", installed=True, version=Version(0, 2, 6)),),
        errors=(),
    )
    remote_discovery = RemoteDiscovery(projects=(RemoteStatus(entry=entry, version=Version(0, 2, 6)),), errors=())
    monkeypatch.setattr(main_module, "discover_workspace", lambda root: local_discovery)
    monkeypatch.setattr(main_module, "discover_remote_projects", lambda: remote_discovery)

    args = build_parser().parse_args(["status", "--workspace", str(tmp_path)])
    exit_code = args.func(args)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert f"{long_role} " in out  # a real separating space survives after the role
    assert long_role + "Python" not in out  # never glued straight into the stack


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


def test_the_command_words_run_the_command_line_without_cli(monkeypatch, capsys) -> None:
    # a script or a cron job that runs `armor-updater status` must never open a window
    called = []
    monkeypatch.setattr(main_module, "cmd_status", lambda args: called.append(args.command) or 0)
    monkeypatch.setattr(sys, "argv", ["armor-updater", "status", "--offline"])
    # the parser stores the function at build time, so the monkeypatched one is the one it holds
    assert main_module.main() == 0
    assert called == ["status"]


def test_without_any_window_the_bare_command_fails_instead_of_pretending(monkeypatch, capsys) -> None:
    import builtins
    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name in {"armor_updater.qt_gui", "armor_updater.gui"} or (name in {"qt_gui", "gui"}) or (args and len(args) > 2 and args[2] and any(f in ("qt_gui", "gui") for f in args[2])):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse)
    monkeypatch.setattr(sys, "argv", ["armor-updater"])
    assert main_module.main() == 1
    assert "--cli" in capsys.readouterr().err


def test_installed_as_a_package_the_workspace_must_be_named(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main_module, "__file__", str(tmp_path / "lib" / "site-packages" / "armor_updater" / "main.py"))
    monkeypatch.delenv("ARMOR_WORKSPACE", raising=False)
    monkeypatch.setattr(main_module.settings, "get_saved_workspace_root", lambda: None)
    try:
        main_module.default_workspace_root()
    except main_module.WorkspaceUnknown as error:
        assert "--workspace" in str(error)
    else:
        raise AssertionError("it must not guess the folder of the Python environment")
    workspace = tmp_path / "projects"
    workspace.mkdir()
    monkeypatch.setenv("ARMOR_WORKSPACE", str(workspace))
    assert main_module.default_workspace_root() == workspace.resolve()
