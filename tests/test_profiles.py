# =============================================================================
# ARMOR-UPDATER - tests/test_profiles.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Update profiles by machine role: the file, its loading, the components that are not discovered (a warning, never a failure), what is remembered in the settings, and the Qt
selector (off screen)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from armor_updater import i18n, profiles, settings
from armor_updater.detect import LocalStatus
from armor_updater.profiles import ProfilesError, load_profiles, parse_profiles, resolve_components
from armor_updater.registry import ProjectEntry
from armor_updater.version_parse import Version

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _settings_file(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")


def test_the_bundled_profiles_are_valid_marked_as_a_proposal_and_in_eight_languages():
    loaded = load_profiles(None)
    assert loaded.proposal is True
    assert [item.id for item in loaded.profiles] == ["cm5", "operator-pc", "development-pc"]
    for item in loaded.profiles:
        assert set(item.title) == set(profiles.LANGUAGE_CODES) and set(item.description) == set(profiles.LANGUAGE_CODES)
    cm5 = loaded.get("cm5")
    assert cm5 and cm5.components == ("ARMOR-SERVER", "ARMOR-STUDIO", "ARMOR-NETWORK", "ARMOR-SERVER-AI", "ARMOR-VOICE-AI", "ARMOR-VISION", "ARMOR-DEVOPS")
    assert loaded.get("operator-pc").components == ("ARMOR-STUDIO", "ARMOR-UPDATER")  # type: ignore[union-attr]
    development = loaded.get("development-pc")
    assert development and development.all_installable and "ARMOR-SIMULATOR" in development.components


def test_the_copy_in_the_docs_repository_is_the_same_file():
    docs = ROOT.parent / "ARMOR-DOCS" / "data" / "update-profiles.json"
    if not docs.is_file():
        pytest.skip("ARMOR-DOCS is not checked out next to this repository")
    assert json.loads(docs.read_text(encoding="utf-8")) == json.loads(profiles.BUNDLED_PROFILES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("text", ["not json", "[]", '{"schema_version": "9"}', '{"schema_version": "1.0", "profiles": []}'])
def test_a_wrong_file_is_refused(text: str):
    with pytest.raises(ProfilesError):
        parse_profiles(text)


def test_the_workspace_file_wins_and_a_damaged_one_falls_back_to_the_copy(tmp_path: Path):
    target = tmp_path.joinpath(*profiles.DOCS_PROFILES)
    target.parent.mkdir(parents=True)
    data = json.loads(profiles.BUNDLED_PROFILES.read_text(encoding="utf-8"))
    data["profiles"] = data["profiles"][:1]
    target.write_text(json.dumps(data), encoding="utf-8")
    assert [item.id for item in load_profiles(tmp_path).profiles] == ["cm5"]
    target.write_text("{broken", encoding="utf-8")
    assert len(load_profiles(tmp_path).profiles) == 3


def test_components_that_are_not_discovered_are_reported_not_fatal():
    cm5 = load_profiles(None).get("cm5")
    assert cm5
    present, missing = resolve_components(cm5, ["armor-server", "ARMOR-STUDIO", "ARMOR-OTHER"])
    assert present == ["armor-server", "ARMOR-STUDIO"]
    assert missing == ["ARMOR-NETWORK", "ARMOR-SERVER-AI", "ARMOR-VOICE-AI", "ARMOR-VISION", "ARMOR-DEVOPS"]
    assert resolve_components(cm5, []) == ([], list(cm5.components))


def test_all_installable_takes_every_discovered_project_and_still_reports_a_missing_extra():
    development = load_profiles(None).get("development-pc")
    assert development
    present, missing = resolve_components(development, ["ARMOR-A", "ARMOR-B"])
    assert present == ["ARMOR-A", "ARMOR-B"] and missing == ["ARMOR-SIMULATOR"]


def test_the_profile_and_its_adjustment_are_remembered():
    assert profiles.saved_profile() == ("", None)
    profiles.save_profile("cm5", ["ARMOR-STUDIO", "ARMOR-SERVER"])
    assert profiles.saved_profile() == ("cm5", ["ARMOR-SERVER", "ARMOR-STUDIO"])
    profiles.save_profile("", None)
    assert profiles.saved_profile() == ("", None)


def test_every_language_has_the_profile_texts():
    keys = {"profile_label", "profile_none", "profile_summary", "profile_proposal", "profile_missing_warning", "profile_member_tip", "signed_tags_checkbox", "signed_tags_hint"}
    english = {key: i18n.t("en", key) for key in keys}
    for code, _label in i18n.LANGUAGES:
        for key in keys:
            assert i18n.t(code, key) != key
            if code != "en":
                assert i18n.t(code, key) != english[key] or key == "profile_label" and code in {"fr", "de"}


def _local(name: str, installed: bool, version: Version | None = None) -> LocalStatus:
    return LocalStatus(entry=ProjectEntry(name, "python"), path=Path(name), installed=installed, version=version)


def _bridge(names: list[str], installed: bool = False):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QObject

    from armor_updater import qt_gui
    bridge = qt_gui.UpdaterBridge.__new__(qt_gui.UpdaterBridge)
    QObject.__init__(bridge)
    bridge._workspace_root = ROOT
    bridge._locals = [_local(name, installed, Version(1, 0, 0) if installed else None) for name in names]
    bridge._remotes, bridge._activity = {}, []
    bridge._busy, bridge._status, bridge._notice, bridge._selected = False, "", "", ""
    bridge._deploy, bridge._lang = "all", "en"
    bridge._profiles = load_profiles(None)
    return bridge


def test_the_selector_preselects_the_roles_components_and_warns_about_the_missing_ones():
    bridge = _bridge(["ARMOR-SERVER", "ARMOR-STUDIO", "ARMOR-UPDATER", "ARMOR-HARDWARE"])
    assert bridge.missingCount == 4 and bridge.profileSummary == ""
    bridge.setProfile("cm5")
    assert bridge.profileId == "cm5" and bridge.missingCount == 2
    in_profile = {row["name"] for row in bridge.projects if row["inProfile"]}
    assert in_profile == {"ARMOR-SERVER", "ARMOR-STUDIO"}
    summary = bridge.profileSummary
    assert "Selected: 2" in summary and "proposal" in summary and "ARMOR-NETWORK" in summary and "Not found on this machine" in summary
    assert profiles.saved_profile() == ("cm5", None)


def test_the_selection_can_be_adjusted_and_is_remembered():
    bridge = _bridge(["ARMOR-SERVER", "ARMOR-STUDIO", "ARMOR-UPDATER"])
    bridge.setProfile("operator-pc")
    bridge.toggleProfileComponent("ARMOR-UPDATER")
    bridge.toggleProfileComponent("ARMOR-SERVER")
    bridge.toggleProfileComponent("ARMOR-NOT-HERE")   # not discovered: ignored
    assert {row["name"] for row in bridge.projects if row["inProfile"]} == {"ARMOR-STUDIO", "ARMOR-SERVER"}
    assert profiles.saved_profile() == ("operator-pc", ["ARMOR-SERVER", "ARMOR-STUDIO"])
    bridge.setProfile("")   # no profile: every project again
    assert bridge.missingCount == 3 and all(row["inProfile"] is False for row in bridge.projects)


def test_a_profile_with_nothing_discovered_gives_a_warning_and_no_failure():
    bridge = _bridge(["ARMOR-HARDWARE"])
    bridge.setProfile("operator-pc")
    assert bridge.missingCount == 0 and bridge.canInstallAll is False
    assert "ARMOR-STUDIO" in bridge.profileSummary and "skipped" in bridge.profileSummary


def test_an_unknown_profile_is_ignored():
    bridge = _bridge(["ARMOR-SERVER"])
    bridge.setProfile("nope")
    assert bridge.profileId == ""


def test_the_signed_tags_switch_is_off_by_default_and_is_saved(monkeypatch):
    monkeypatch.delenv("ARMOR_UPDATER_SIGNED_TAGS_ONLY", raising=False)
    bridge = _bridge([])
    assert bridge.signedTagsOnly is False
    bridge.setSignedTagsOnly(True)
    assert bridge.signedTagsOnly is True and settings.load_settings()["signed_tags_only"] is True
