# =============================================================================
# ARMOR-UPDATER - tests/test_registry.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Tests for generic runtime entries; no fixed ecosystem project list."""

from armor_updater.project_manifest import parse_manifest
from armor_updater.registry import entry_from_manifest, github_raw_url, github_repo_url


def test_runtime_entry_uses_repository_owned_data():
    manifest = parse_manifest(
        r'''{
          "schema_version": "1.0", "ecosystem": "A.R.M.O.R.",
          "name": "ARMOR-EXAMPLE", "version": "1.2.3",
          "role": "An example service", "stack": "python", "technologies": ["Python"],
          "deployment_target": "the central server", "maturity": "functional",
          "family": "Examples", "parent": null,
          "native_version": "1.2.3",
          "build": "python -m example", "notes": "Example."
        }''',
        expected_name="ARMOR-EXAMPLE",
    )
    entry = entry_from_manifest(manifest)

    assert entry.native_version == "1.2.3"
    assert entry.stack == "python"
    assert github_raw_url(entry).endswith("/ARMOR-EXAMPLE/main/armor.project.json")
    assert github_repo_url(entry).endswith("/ARMOR-EXAMPLE")
