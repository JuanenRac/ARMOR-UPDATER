# =============================================================================
# ARMOR-UPDATER - tests/test_requires.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The optional `requires` field of the manifest: validation, the order of a batch and the refusal of a project whose requirement is not installed (said in the eight
languages)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from armor_updater import i18n, install
from armor_updater.install import InstallResult, clone_or_pull, install_or_update, install_order, missing_requirements
from armor_updater.project_manifest import ManifestValidationError, parse_manifest
from armor_updater.registry import ProjectEntry, entry_from_manifest
from armor_updater.result_text import localized_message
from test_install import entry, git, write_build_script, write_manifest


def manifest_text(**extra: object) -> str:
    data = {
        "schema_version": "1.0", "ecosystem": "A.R.M.O.R.", "name": "ARMOR-EXAMPLE", "version": "1.0.0", "role": "service", "stack": "python",
        "technologies": ["Python"], "deployment_target": "The central server", "maturity": "functional", "family": "Test", "parent": None,
        "native_version": "1.0.0", "build": "python -m compileall src", "notes": "Test manifest.",
    }
    data.update(extra)
    return json.dumps(data)


# ---- the field -----------------------------------------------------------------------------------------------------------------------------------

def test_a_manifest_without_requires_is_unchanged():
    manifest = parse_manifest(manifest_text())
    assert manifest.requires == ()
    assert entry_from_manifest(manifest).requires == ()


def test_requires_is_a_list_of_project_names():
    manifest = parse_manifest(manifest_text(requires=["ARMOR-COMMON", "ARMOR-SERVER"]))
    assert manifest.requires == ("ARMOR-COMMON", "ARMOR-SERVER")
    assert entry_from_manifest(manifest).requires == ("ARMOR-COMMON", "ARMOR-SERVER")


def test_an_empty_requires_list_is_allowed():
    assert parse_manifest(manifest_text(requires=[])).requires == ()


@pytest.mark.parametrize("bad", ["ARMOR-COMMON", [1], [""], ["a b"], ["../x"], ["ARMOR-COMMON", "ARMOR-COMMON"], ["ARMOR-EXAMPLE"], {"x": 1}])
def test_requires_that_is_not_a_list_of_distinct_other_projects_is_rejected(bad):
    with pytest.raises(ManifestValidationError, match="requires"):
        parse_manifest(manifest_text(requires=bad))


# ---- the order ------------------------------------------------------------------------------------------------------------------------------------

def names(entries) -> list[str]:
    return [e.name for e in entries]


def test_a_required_project_goes_before_the_project_that_requires_it():
    batch = [ProjectEntry("A-CLIENT", "x", requires=("Z-LIBRARY",)), ProjectEntry("Z-LIBRARY", "x"), ProjectEntry("M-OTHER", "x")]
    order = names(install_order(batch))
    assert order.index("Z-LIBRARY") < order.index("A-CLIENT")


def test_common_stays_first_then_requirements_then_parents():
    batch = [
        ProjectEntry("ARMOR-APP", "x", parent="ARMOR-SERVER", requires=("ARMOR-TOOLS",)),
        ProjectEntry("ARMOR-TOOLS", "x"),
        ProjectEntry("ARMOR-SERVER", "x"),
        ProjectEntry("ARMOR-COMMON", "x"),
    ]
    order = names(install_order(batch))
    assert order[0] == "ARMOR-COMMON"
    assert order.index("ARMOR-TOOLS") < order.index("ARMOR-APP")
    assert order.index("ARMOR-SERVER") < order.index("ARMOR-APP")


def test_a_requirement_that_is_not_in_the_batch_is_ignored_by_the_order_and_a_cycle_does_not_hang():
    batch = [ProjectEntry("B", "x", requires=("NOT-IN-BATCH", "C")), ProjectEntry("C", "x", requires=("B",))]
    assert sorted(names(install_order(batch))) == ["B", "C"]


# ---- the refusal ----------------------------------------------------------------------------------------------------------------------------------

def test_missing_requirements_looks_for_a_folder_of_that_name(tmp_path: Path):
    (tmp_path / "ARMOR-COMMON").mkdir()
    assert missing_requirements(tmp_path, ["ARMOR-COMMON", "ARMOR-TOOLS"]) == ["ARMOR-TOOLS"]


def test_a_project_whose_requirement_is_not_installed_is_refused_before_anything_is_cloned(tmp_path: Path, monkeypatch):
    called: list[str] = []
    monkeypatch.setattr(install, "clone_or_pull", lambda *a, **k: called.append("clone") or InstallResult(True, "x"))
    needing = ProjectEntry("ARMOR-EXAMPLE", "python", requires=("ARMOR-TOOLS",))
    results = install_or_update(needing, tmp_path, build=False)
    assert called == []
    assert [r.ok for r in results] == [False]
    assert results[0].code == "requires_missing"
    assert "ARMOR-TOOLS" in results[0].message
    assert list(tmp_path.glob("ARMOR-EXAMPLE*")) == []
    # the refusal is also in the evidence file
    assert "requires ARMOR-TOOLS" in (tmp_path / ".armor-updater" / "evidence.jsonl").read_text(encoding="utf-8")


def test_the_refusal_is_said_in_every_language_of_the_window(tmp_path: Path):
    needing = ProjectEntry("ARMOR-EXAMPLE", "python", requires=("ARMOR-TOOLS",))
    result = install_or_update(needing, tmp_path, build=False)[0]
    english = localized_message("en", result)
    seen = {english}
    for code, _label in i18n.LANGUAGES:
        text = localized_message(code, result)
        assert "ARMOR-TOOLS" in text and "ARMOR-EXAMPLE" in text and str(tmp_path) in text
        assert "{" not in text
        seen.add(text)
    assert len(seen) == len(i18n.LANGUAGES), "each language has its own sentence"


def remote_with_requires(tmp_path: Path, requires: list[str]) -> Path:
    remote = tmp_path / "remote.git"
    git("init", "--bare", str(remote), cwd=tmp_path)
    seed = tmp_path / "seed"
    git("clone", str(remote), str(seed), cwd=tmp_path)
    git("config", "user.email", "contract@example.invalid", cwd=seed)
    git("config", "user.name", "Contract", cwd=seed)
    write_manifest(seed, "1.0.0")
    manifest = json.loads((seed / "armor.project.json").read_text(encoding="utf-8"))
    manifest["requires"] = requires
    (seed / "armor.project.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_build_script(seed, ok=True)
    git("add", "-A", cwd=seed)
    git("commit", "-m", "v1", cwd=seed)
    git("push", "origin", "HEAD", cwd=seed)
    return remote


def test_a_requirement_declared_only_by_the_candidate_manifest_also_refuses_and_leaves_nothing(tmp_path: Path, monkeypatch):
    remote = remote_with_requires(tmp_path, ["ARMOR-TOOLS"])
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)   # the entry does not know the requirement, the cloned manifest does
    assert not result.ok and result.code == "requires_missing"
    assert list(workspace.iterdir()) == []


def test_the_project_installs_once_its_requirement_is_there(tmp_path: Path, monkeypatch):
    remote = remote_with_requires(tmp_path, ["ARMOR-TOOLS"])
    monkeypatch.setattr(install, "github_repo_url", lambda _entry: str(remote))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "ARMOR-TOOLS").mkdir()
    result = clone_or_pull(entry(), workspace, verify_build=False)
    assert result.ok, result.message
    assert (workspace / entry().name / "armor.project.json").is_file()
