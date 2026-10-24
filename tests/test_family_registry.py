# =============================================================================
# ARMOR-UPDATER - tests/test_family_registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The updater keeps no list of the repositories of the family (each one publishes its own manifest), but the family does keep one, in ARMOR-COMMON/registry/repositories.json.

These tests hold the two together: every repository the registry names has a manifest this updater accepts, with the name and the group the registry gives it, and the projects a
manifest says must be installed first are projects of the family. The repositories that are not checked out beside this one are skipped.
"""

import json
from pathlib import Path

import pytest

from armor_updater.project_manifest import MANIFEST_FILE, parse_manifest
from armor_updater.registry import entry_from_manifest

FAMILY = Path(__file__).resolve().parents[2]
REGISTRY = FAMILY / "ARMOR-COMMON" / "registry" / "repositories.json"

pytestmark = pytest.mark.skipif(not REGISTRY.is_file(), reason="ARMOR-COMMON is not next to this repository")


def repositories() -> list[dict]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["repositories"]


def present() -> list[tuple[dict, Path]]:
    return [(entry, FAMILY / entry["name"] / MANIFEST_FILE) for entry in repositories() if (FAMILY / entry["name"] / MANIFEST_FILE).is_file()]


def test_every_repository_beside_this_one_publishes_a_manifest_the_updater_accepts_under_the_name_and_group_of_the_registry():
    found = present()
    if not found:
        pytest.skip("no other repository of the family is beside this one")
    for entry, manifest_path in found:
        manifest = parse_manifest(manifest_path.read_text(encoding="utf-8"), expected_name=entry["name"])
        assert entry_from_manifest(manifest).family.upper() == entry["group"], entry["name"]


def test_what_a_manifest_requires_to_be_installed_first_is_in_the_registry():
    names = {entry["name"] for entry in repositories()}
    for entry, manifest_path in present():
        manifest = parse_manifest(manifest_path.read_text(encoding="utf-8"), expected_name=entry["name"])
        assert set(manifest.requires) <= names, entry["name"]


def test_the_registry_names_a_repository_once_and_this_one_is_in_it():
    names = [entry["name"] for entry in repositories()]
    assert len(names) == len(set(names))
    assert "ARMOR-UPDATER" in names
