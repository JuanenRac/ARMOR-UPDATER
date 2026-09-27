# =============================================================================
# ARMOR-UPDATER - tests/test_deploy_category.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Real regression coverage for deploy_category.py, keyed on the actual
`deployment_target` text every real A.R.M.O.R. repository ships today -
not synthetic examples. Before this module existed, the desktop GUI
compared these same strings against HYDRA-UMC's own closed enum
(cm5/user-pc/mobile/wearable/dev-server) with `==`; none of them ever
matched, so every filter button except "all" silently showed zero
projects, and the Deploy column tried to translate the raw free text
itself as an i18n key."""

from armor_updater.deploy_category import DEPLOY_CATEGORIES, categorize_deployment_target
from armor_updater.project_manifest import parse_manifest
from armor_updater.registry import entry_from_manifest


# name -> (real deployment_target text, expected category)
_REAL_MANIFEST_VALUES = {
    "ARMOR-ANDROID-CONTROL": ("Android 10+", "mobile"),
    "ARMOR-COMMON": ("All A.R.M.O.R. services and tools", "shared"),
    "ARMOR-DEVOPS": ("NVIDIA Jetson Orin NX and administration host", "server"),
    "ARMOR-DOCS": ("All users and maintainers", "shared"),
    "ARMOR-ELECTRICAL": (
        "ESP32-S3 nodes inside the electrical panels (the firmware builds; it has never run on a board)",
        "field-node",
    ),
    "ARMOR-HARDWARE": ("Outdoor field nodes", "field-node"),
    "ARMOR-NETWORK": (
        "Any machine on the network being watched (a PC, the CM5, a Raspberry Pi); it reports to ARMOR-SERVER",
        "workstation",
    ),
    "ARMOR-RADAR": ("ESP32-S3-ETH-PoE", "field-node"),
    "ARMOR-SERVER-AI": ("NVIDIA Jetson Orin NX", "server"),
    "ARMOR-SERVER": ("NVIDIA Jetson Orin NX", "server"),
    "ARMOR-SIMULATOR": ("Developer workstation and CI", "workstation"),
    "ARMOR-SOLAR": (
        "ESP32-S3 gateway nodes: N16R8 on Wi-Fi, or Waveshare ESP32-S3-ETH on Ethernet",
        "field-node",
    ),
    "ARMOR-STUDIO": ("Browser served by central server", "browser"),
    "ARMOR-UPDATER": (
        "Any machine that installs or updates A.R.M.O.R. repositories (a developer PC or the central server)",
        "workstation",
    ),
    "ARMOR-VOICE-AI": ("NVIDIA Jetson Orin NX", "server"),
}


def test_every_real_armor_manifest_value_is_categorized_as_expected():
    for repo, (raw, expected) in _REAL_MANIFEST_VALUES.items():
        assert categorize_deployment_target(raw) == expected, repo


def test_every_category_used_above_is_a_real_declared_category():
    used = {expected for _raw, expected in _REAL_MANIFEST_VALUES.values()}
    assert used <= set(DEPLOY_CATEGORIES)
    assert "all" in DEPLOY_CATEGORIES  # the GUI's own "no filter" option


def test_an_unrecognized_value_falls_back_to_shared_not_silence():
    # A real, visible bucket - never a project that matches no rule and
    # therefore never appears under any specific filter at all.
    assert categorize_deployment_target("Something nobody wrote yet") == "shared"


def test_matching_is_case_insensitive():
    assert categorize_deployment_target("ANDROID 10+") == "mobile"
    assert categorize_deployment_target("nvidia jetson orin nx") == "server"


def test_project_entry_exposes_the_category_computed_from_deploy():
    manifest = parse_manifest(
        r'''{
          "schema_version": "1.0", "ecosystem": "A.R.M.O.R.",
          "name": "ARMOR-EXAMPLE", "version": "1.2.3",
          "role": "An example service", "stack": "python", "technologies": ["Python"],
          "deployment_target": "Android 10+", "maturity": "functional",
          "family": "Examples", "parent": null,
          "native_version": "1.2.3",
          "build": "python -m example", "notes": "Example."
        }''',
        expected_name="ARMOR-EXAMPLE",
    )
    entry = entry_from_manifest(manifest)

    assert entry.deploy == "Android 10+"  # unchanged: the project's own real text
    assert entry.deploy_category == "mobile"  # what the GUI filter actually uses
