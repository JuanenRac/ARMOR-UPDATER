"""The model the QML window reads (qt_gui.UpdaterBridge): its properties, the list of projects with their state, the filters, the update profiles, the language, the selection, the refresh and the
actions (install, update, the batch, restore, clean) with their worker threads run in the calling thread and the network and the installer replaced by stand-ins, and the way the steps of an operation
are marked. Nothing is read from or written to the home folder of the person who runs the tests; the Qt part is skipped where PySide6 is not installed."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from armor_updater import settings
from armor_updater.detect import LocalDiscovery, LocalStatus
from armor_updater.github_client import RemoteDiscovery, RemoteStatus
from armor_updater.install import InstallResult
from armor_updater.registry import ProjectEntry
from armor_updater.version_parse import Version

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
try:
    from armor_updater import qt_gui
except ImportError as error:   # PySide6 is there but a system library of Qt is not (a bare container): nothing to try here
    pytest.skip(f"Qt cannot be loaded: {error}", allow_module_level=True)


class SyncThread:
    """A thread that runs its work at once, in the caller, so the results arrive in the order they are asked for."""

    def __init__(self, target=None, daemon=None, name=None, **_ignored):
        self._target = target

    def start(self):
        self._target()


def entry(name: str, family: str = "ARMOR", parent: str | None = None, deploy: str = "ESP32-S3-ETH-PoE", **fields) -> ProjectEntry:
    return ProjectEntry(name=name, stack="python", deploy=deploy, tech=("python", "esp-idf"), notes=fields.pop("notes", "A note"), family=family, parent=parent, **fields)


def local(name: str, version: str | None = "0.2.0", installed: bool = True, **fields) -> LocalStatus:
    return LocalStatus(entry=entry(name, **fields), path=Path("/w") / name, installed=installed, version=Version.from_string(version) if version else None)


def remote(item: LocalStatus, version: str | None) -> RemoteStatus:
    return RemoteStatus(entry=item.entry, version=Version.from_string(version) if version else None)


@pytest.fixture()
def world(tmp_path, monkeypatch):
    """A bridge on a temporary workspace with a few local projects, no network and no home folder."""
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(settings, "_LEGACY_LANG_PATH", tmp_path / "lang.json")
    monkeypatch.setattr(qt_gui.threading, "Thread", SyncThread)
    locals_ = [
        local("ARMOR-COMMON", "0.2.0"),
        local("ARMOR-NODE-RADAR", "0.1.0", parent="ARMOR-COMMON"),
        local("ARMOR-STUDIO", "0.3.0", deploy="NVIDIA Jetson Orin NX"),
        local("ARMOR-DOCS", None),
    ]
    missing = local("ARMOR-VISION", None, installed=False)
    remotes = {"ARMOR-COMMON": remote(locals_[0], "0.2.0"), "ARMOR-NODE-RADAR": remote(locals_[1], "0.1.5"), "ARMOR-STUDIO": remote(locals_[2], "0.3.0"), "ARMOR-VISION": remote(missing, "0.1.0")}
    state = SimpleNamespace(locals=locals_, missing=missing, remotes=remotes, installs=[], results=None)

    monkeypatch.setattr(qt_gui, "discover_workspace", lambda root: LocalDiscovery(projects=tuple(state.locals), errors=()))
    monkeypatch.setattr(qt_gui, "discover_remote_projects", lambda: RemoteDiscovery(projects=tuple(state.remotes.values()), errors=()))

    def fake_install(item, root, build=True, progress=None):
        state.installs.append((item.name, build))
        if progress:
            progress("preflight", "checking")
            progress("build", "building")
        return state.results if state.results is not None else [InstallResult(True, "done")]

    monkeypatch.setattr(qt_gui, "install_or_update", fake_install)
    state.bridge = qt_gui.UpdaterBridge(tmp_path, tmp_path / "gui.log")
    state.bridge.setLanguage("en")
    state.bridge.setDeploy("all")   # the window starts on the CM5 filter on Linux
    state.bridge._remotes = state.remotes
    state.bridge._locals = [*locals_, missing]
    state.tmp = tmp_path
    return state


def names(bridge) -> list[str]:
    return [row["name"] for row in bridge.projects]


def test_the_plain_properties(world):
    bridge = world.bridge
    assert bridge.language == "en" and bridge.appVersion and bridge.logFilePath == str(world.tmp / "gui.log")
    assert bridge.workspaceRoot == str(world.tmp) and bridge.busy is False
    assert bridge.operationVisible is False and bridge.operationSteps == [] and bridge.operationProgress == 0
    assert bridge.operationDetail == bridge.text("checkpoint_waiting")
    assert bridge.operationHeading == bridge.text("checkpoint_title")
    assert bridge.selectedProject == bridge.text("selected_project_none")
    assert bridge.signedTagsOnly in (True, False)


def test_the_activity_strip_keeps_eight_lines_and_the_full_log_keeps_all(world):
    bridge = world.bridge
    bridge._activity.clear()
    for number in range(12):
        bridge._append_activity(f"line {number}\nwith a break")
    assert len(bridge.activity) == 8 and bridge.activity[-1] == "line 11 with a break"
    assert len(bridge.fullActivity) == 12


def test_the_projects_are_sorted_filtered_and_described(world):
    bridge = world.bridge
    bridge.setDeploy("all")
    rows = {row["name"]: row for row in bridge.projects}
    assert set(rows) == {"ARMOR-COMMON", "ARMOR-NODE-RADAR", "ARMOR-STUDIO", "ARMOR-DOCS", "ARMOR-VISION"}
    assert rows["ARMOR-NODE-RADAR"]["isChild"] and not rows["ARMOR-COMMON"]["isChild"]
    assert rows["ARMOR-NODE-RADAR"]["stateKey"] == "state_outdated"
    assert rows["ARMOR-COMMON"]["stateKey"] == "state_up_to_date"
    assert rows["ARMOR-DOCS"]["stateKey"] == "state_unknown_local" and rows["ARMOR-DOCS"]["local"] == "?"
    assert rows["ARMOR-VISION"]["stateKey"] == "state_not_installed" and rows["ARMOR-VISION"]["local"] == "-"
    assert rows["ARMOR-VISION"]["github"] == "0.1.0" and rows["ARMOR-COMMON"]["tech"] == "python, esp-idf"
    assert names(bridge).index("ARMOR-COMMON") < names(bridge).index("ARMOR-NODE-RADAR")   # a parent before its children
    bridge.setDeploy("not-a-category")
    assert len(names(bridge)) == 5
    bridge.setDeploy("server")
    assert names(bridge) == ["ARMOR-STUDIO"]
    options = bridge.deployOptions
    assert options[0]["key"] == "all" and str(len(world.bridge._locals)) in options[0]["label"]


@pytest.mark.parametrize(
    ("local_status", "remote_status", "expected"),
    [
        (lambda: local("A", installed=False, version=None), None, "state_not_installed"),
        (lambda: local("A", version=None), None, "state_unknown_local"),
        (lambda: local("A"), None, "state_installed_not_checked"),
        (lambda: local("A"), lambda item: remote(item, None), "state_installed_github_unknown"),
        (lambda: local("A", "0.1.0"), lambda item: remote(item, "0.2.0"), "state_outdated"),
        (lambda: local("A", "0.3.0"), lambda item: remote(item, "0.2.0"), "state_ahead"),
        (lambda: local("A", "0.2.0"), lambda item: remote(item, "0.2.0"), "state_up_to_date"),
    ],
)
def test_the_state_of_a_project(local_status, remote_status, expected):
    item = local_status()
    assert qt_gui._state_key(item, remote_status(item) if remote_status else None) == expected


def test_the_counts_and_what_can_be_done(world):
    bridge = world.bridge
    assert bridge.discoveredCount == 5 and bridge.installedCount == 4
    assert bridge.missingCount == 1 and bridge.canInstallAll is True
    assert bridge.updateCount == 1 and bridge.canUpdateAll is True
    bridge.selectProject("ARMOR-NODE-RADAR")
    assert bridge.selectedProject == "ARMOR-NODE-RADAR" and bridge.canUpdate is True and bridge.canInstall is False
    bridge.selectProject("ARMOR-VISION")
    assert bridge.canInstall is True and bridge.canUpdate is False
    bridge.selectProject("ARMOR-DOCS")
    assert bridge.canUpdate is False   # its local version is not known
    bridge.selectProject("ARMOR-COMMON")
    assert bridge.canUpdate is False
    bridge.selectProject("nothing")
    assert bridge.selectedProject == bridge.text("selected_project_none") and bridge.canInstall is False and bridge.canRestore is False
    assert bridge.backupsSummary == ""
    bridge.selectProject("ARMOR-COMMON")
    assert bridge.canRestore is False and bridge.backupsSummary == ""


def test_the_notes_of_the_selected_project(world):
    bridge = world.bridge
    assert bridge.selectedNotes() == bridge.text("note_default")
    bridge.selectProject("ARMOR-COMMON")
    text = bridge.selectedNotes()
    assert "A note" in text and "python, esp-idf" in text


def test_the_language_is_checked_and_remembered(world):
    bridge = world.bridge
    bridge.setLanguage("xx")
    assert bridge.language == "en"
    bridge.setLanguage("es")
    assert bridge.language == "es" and bridge.text("selected_project_none") != "" and settings.get_saved_lang() == "es"
    assert any(option["id"] == "cm5" for option in bridge.profileOptions) and bridge.profileOptions[0]["id"] == ""


def test_a_selection_is_refused_while_an_operation_is_shown_and_busy(world):
    bridge = world.bridge
    bridge.selectProject("ARMOR-COMMON")
    bridge._busy, bridge._operation_visible = True, True
    bridge.selectProject("ARMOR-STUDIO")
    assert bridge._selected == "ARMOR-COMMON"
    bridge._busy = False
    bridge.selectProject("ARMOR-STUDIO")
    assert bridge._selected == "ARMOR-STUDIO" and bridge._operation_visible is False


def test_a_profile_scopes_the_counts_and_can_be_adjusted(world):
    bridge = world.bridge
    assert bridge.profileSummary == "" and bridge.profileId == ""
    bridge.setProfile("nope")
    assert bridge.profileId == ""
    bridge.setProfile("operator-pc")   # ARMOR-STUDIO and ARMOR-UPDATER
    assert bridge.profileId == "operator-pc" and "1" in bridge.profileSummary and bridge.missingCount == 0 and bridge.updateCount == 0
    flags = {row["name"]: row["inProfile"] for row in bridge.projects}
    assert flags["ARMOR-STUDIO"] is True and flags["ARMOR-COMMON"] is False
    bridge.toggleProfileComponent("ARMOR-COMMON")
    assert bridge._profile_selection == {"ARMOR-STUDIO", "ARMOR-COMMON"}
    bridge.toggleProfileComponent("ARMOR-COMMON")
    bridge.toggleProfileComponent("not-discovered")
    assert bridge._profile_selection == {"ARMOR-STUDIO"}
    assert settings.load_settings()["update_profile_selection"] == ["ARMOR-STUDIO"]
    bridge.setProfile("")
    assert bridge._selected_components() is None
    bridge.toggleProfileComponent("ARMOR-COMMON")   # no profile, nothing to adjust
    assert bridge._profile_selection is None
    bridge.setProfile("cm5")
    assert "ARMOR-SERVER-AI" in bridge.profileSummary   # listed by the profile and not discovered: a warning, not an error


def test_the_signed_tags_switch_is_saved(world):
    world.bridge.setSignedTagsOnly(True)
    assert settings.load_settings()["signed_tags_only"] is True
    world.bridge.setSignedTagsOnly(False)
    assert settings.load_settings()["signed_tags_only"] is False


def test_the_workspace_can_be_changed_and_is_remembered(world, monkeypatch, tmp_path):
    bridge = world.bridge
    other = tmp_path / "other"
    other.mkdir()
    bridge.setWorkspaceUrl("")
    assert bridge._workspace_root == tmp_path
    bridge.setWorkspaceUrl(str(other))
    assert bridge.workspaceRoot == str(other) and settings.load_settings()["workspace_root"] == str(other)
    assert any(str(other) in line for line in bridge.fullActivity)
    bridge.setWorkspaceUrl(other.as_uri())
    assert bridge._workspace_root.resolve() == other.resolve()


def test_the_github_page_of_the_selection(world, monkeypatch):
    opened = []
    monkeypatch.setattr(qt_gui.webbrowser, "open", opened.append)
    world.bridge.openSelectedGithub()
    assert opened == []
    world.bridge.selectProject("ARMOR-COMMON")
    world.bridge.openSelectedGithub()
    assert opened == ["https://github.com/JuanenRac/ARMOR-COMMON"]


def test_refresh_offline_and_online(world):
    bridge = world.bridge
    bridge._busy = True
    bridge.refresh(True)   # ignored while busy
    bridge._busy = False
    bridge._notice = "a notice"
    bridge.refresh(True)
    assert bridge.status == "a notice" and bridge._remotes == {}
    bridge._notice = ""
    bridge.refresh(True)
    assert bridge.status == bridge.text("status_ready_offline")
    bridge.refresh(False)
    assert bridge.busy is False and "ARMOR-VISION" in bridge._remotes and bridge.status == bridge.text("status_ready")


def test_refresh_falls_back_to_the_known_projects_when_discovery_is_down(world, monkeypatch):
    def down():
        raise RuntimeError("no network")

    monkeypatch.setattr(qt_gui, "discover_remote_projects", down)
    monkeypatch.setattr(qt_gui, "fetch_all", lambda entries: {item.name: RemoteStatus(entry=item, version=Version.from_string("9.9.9")) for item in entries})
    world.bridge.refresh(False)
    assert world.bridge.status.startswith("Remote discovery unavailable")
    assert world.bridge._remotes["ARMOR-COMMON"].version == Version.from_string("9.9.9")


def test_install_and_update_refuse_what_cannot_be_done(world):
    bridge = world.bridge
    bridge.performSelected("install", False)
    assert bridge.fullActivity[-1] == bridge.text("msg_select_project_first")
    bridge.selectProject("ARMOR-COMMON")
    bridge.performSelected("install", False)
    assert "already" in bridge.fullActivity[-1].lower() or "ARMOR-COMMON" in bridge.fullActivity[-1]
    bridge.selectProject("ARMOR-VISION")
    bridge.performSelected("update", False)
    assert "ARMOR-VISION" in bridge.fullActivity[-1]
    bridge._busy = True
    bridge.performSelected("install", False)
    assert world.installs == []


def test_an_install_runs_the_installer_and_shows_the_steps(world):
    bridge = world.bridge
    bridge.selectProject("ARMOR-VISION")
    bridge.performSelected("install", False)
    assert world.installs == [("ARMOR-VISION", True)]
    assert bridge.operationVisible is True and bridge.busy is False
    assert [step["state"] for step in bridge.operationSteps] == ["done"] * 5 and bridge.operationProgress == 100
    assert bridge.operationDetail == bridge.text("checkpoint_complete_detail")
    assert bridge.status == bridge.text("status_ready")


def test_an_update_without_a_build_skips_that_step(world):
    bridge = world.bridge
    bridge.selectProject("ARMOR-NODE-RADAR")
    bridge.performSelected("update", True)
    assert world.installs == [("ARMOR-NODE-RADAR", False)]
    assert [step["state"] for step in bridge.operationSteps] == ["done", "done", "done", "skipped", "done"]


def test_a_failed_install_marks_the_step_and_says_why(world):
    bridge = world.bridge
    world.results = [InstallResult(False, "the build failed", output="line a\n\nline b\nline c\nline d\nline e\nline f")]
    bridge.selectProject("ARMOR-VISION")
    bridge.performSelected("install", False)
    assert any(step["state"] == "failed" for step in bridge.operationSteps)
    assert "build failed" in " ".join(step["detail"] for step in bridge.operationSteps)
    assert bridge.fullActivity[-3:-1] == ["  line e", "  line f"] or any("line f" in line for line in bridge.fullActivity)


def test_an_unsigned_revision_keeps_its_warning_in_the_status_line(world):
    bridge = world.bridge
    world.results = [InstallResult(True, "done", unsigned="abc1234")]
    bridge.selectProject("ARMOR-VISION")
    bridge.performSelected("install", False)
    assert "abc1234" in bridge.status


def test_the_batch_installs_everything_missing_in_order(world):
    bridge = world.bridge
    bridge.performBatch("install", False)
    assert [name for name, _ in world.installs] == ["ARMOR-VISION"]
    assert bridge.operationHeading != bridge.text("checkpoint_title") or bridge._batch_total == 1
    world.installs.clear()
    bridge.performBatch("update", True)
    assert world.installs == [("ARMOR-NODE-RADAR", False)]
    world.installs.clear()
    bridge.performBatch("other", False)
    assert world.installs == []


def test_a_batch_with_nothing_to_do_says_so(world):
    bridge = world.bridge
    bridge.setProfile("operator-pc")
    bridge.performBatch("install", False)
    assert bridge.fullActivity[-1] == bridge.text("msg_batch_nothing_to_do")
    bridge._busy = True
    bridge.performBatch("install", False)
    assert world.installs == []


def test_a_batch_names_its_projects_in_the_heading(world):
    bridge = world.bridge
    bridge._start_operation(False, batch_total=3)
    bridge._on_batch_project(2, 3, "ARMOR-STUDIO")
    assert "ARMOR-STUDIO" in bridge.operationHeading and "2" in bridge.operationHeading
    assert bridge._operation_progress == 33 and bridge._operation_steps[0]["state"] == "active"
    bridge._on_operation_checkpoint("build", "[2/3] building")
    assert 33 <= bridge._operation_progress <= 100
    bridge._on_operation_checkpoint("unknown phase", "x")
    assert bridge.operationDetail == "[2/3] building"
    bridge._on_batch_project(1, 3, "A")
    assert bridge.operationDetail == bridge.text("checkpoint_waiting")


def test_the_steps_of_a_single_operation_advance(world):
    bridge = world.bridge
    bridge._start_operation(True)
    assert [step["state"] for step in bridge.operationSteps] == ["pending", "pending", "pending", "skipped", "pending"]
    bridge._on_operation_checkpoint("validation", "checking")
    assert [step["state"] for step in bridge.operationSteps][:3] == ["done", "done", "active"]
    assert bridge.operationProgress == 40 and bridge.operationDetail == "checking"
    bridge._on_operation_checkpoint("complete", "all done")
    assert bridge.operationSteps[3]["state"] == "skipped" and bridge.operationSteps[2]["state"] == "done"


def test_restore_and_clean_use_the_previous_copies(world, monkeypatch):
    calls = []
    monkeypatch.setattr(qt_gui, "restore_previous_copy", lambda root, name: calls.append(("restore", name)) or InstallResult(True, "restored"))
    monkeypatch.setattr(qt_gui, "clean_previous_copies", lambda root, name: calls.append(("clean", name)) or InstallResult(True, "cleaned"))
    bridge = world.bridge
    bridge.restoreSelected()   # nothing selected
    assert calls == []
    bridge.selectProject("ARMOR-COMMON")
    bridge.restoreSelected()
    bridge.cleanSelectedBackups()
    assert calls == [("restore", "ARMOR-COMMON"), ("clean", "ARMOR-COMMON")]
    assert any("restored" in line for line in bridge.fullActivity) and any("cleaned" in line for line in bridge.fullActivity)
    bridge._busy = True
    bridge.restoreSelected()
    assert len(calls) == 2


def test_the_app_id_and_the_log_file(monkeypatch, tmp_path):
    monkeypatch.setattr(qt_gui, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)   # the set-up replaces the hook; the test puts it back
    path = qt_gui._setup_file_logging()
    assert path.parent == tmp_path / "logs" and path.name.endswith(".log")
    for handler in list(qt_gui._GUI_LOGGER.handlers):
        qt_gui._GUI_LOGGER.removeHandler(handler)
        handler.close()
    qt_gui._set_windows_app_id()   # does nothing off Windows and never raises on it
