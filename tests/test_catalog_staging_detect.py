# =============================================================================
# ARMOR-UPDATER - tests/test_catalog_staging_detect.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""The discovery catalog, the workspace scan, the folders the updater builds in (what it carries over, what it never does) and the way it runs git. Real git, in temporary folders."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from armor_updater import git_ops, staging
from armor_updater.detect import discover_workspace, scan_workspace
from armor_updater.ecosystem_catalog import CatalogValidationError, parse_catalog
from armor_updater.registry import ProjectEntry

CATALOG = {"schema_version": "1.0", "ecosystem": "A.R.M.O.R.", "github_owner": "JuanenRac", "manifest_file": "armor.project.json", "dashboard_exclude": ["JuanenRac"]}


def catalog_text(**changes) -> str:
    data = dict(CATALOG)
    data.update(changes)
    return json.dumps({key: value for key, value in data.items() if value is not ...})


def manifest(name: str, **changes) -> dict:
    data = {"schema_version": "1.0", "ecosystem": "A.R.M.O.R.", "name": name, "version": "0.1.2", "role": "service", "stack": "Python", "technologies": ["Python"],
            "deployment_target": "any", "maturity": "functional", "family": "tools", "parent": None, "build": "python -m pytest", "notes": "x", "native_version": "0.1.2"}
    data.update(changes)
    return data


def git(path: Path, *args: str) -> str:
    environment = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.org"}
    done = subprocess.run(["git", *args], cwd=str(path), capture_output=True, text=True, env=environment, check=True)
    return done.stdout.strip()


def repo(path: Path, files: dict[str, str] | None = None, branch: str = "main") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", branch)
    for relative, text in (files or {"file.txt": "one\n"}).items():
        (path / relative).parent.mkdir(parents=True, exist_ok=True)
        (path / relative).write_text(text, encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "first")
    return path


# ---------------------------------------------------------------- the catalog
def test_a_good_catalog_is_read():
    parsed = parse_catalog(catalog_text())
    assert (parsed.github_owner, parsed.manifest_file, parsed.dashboard_exclude) == ("JuanenRac", "armor.project.json", ("JuanenRac",))


def test_the_exclude_list_may_be_empty():
    assert parse_catalog(catalog_text(dashboard_exclude=[])).dashboard_exclude == ()


@pytest.mark.parametrize("text, fragment", [
    ("{not json", "invalid JSON"),
    ("[]", "root must be an object"),
    ('"text"', "root must be an object"),
    (catalog_text(schema_version="2.0"), "schema_version"),
    (catalog_text(schema_version=...), "schema_version"),
    (catalog_text(ecosystem="Other"), "ecosystem"),
    (catalog_text(github_owner=""), "github_owner"),
    (catalog_text(github_owner="   "), "github_owner"),
    (catalog_text(github_owner=5), "github_owner"),
    (catalog_text(manifest_file="project.json"), "manifest_file"),
    (catalog_text(dashboard_exclude="all"), "dashboard_exclude"),
    (catalog_text(dashboard_exclude=["a", 5]), "dashboard_exclude"),
    (catalog_text(dashboard_exclude=...), "dashboard_exclude"),
])
def test_a_catalog_that_cannot_route_safely_is_refused_with_the_reason(text, fragment):
    with pytest.raises(CatalogValidationError, match=fragment):
        parse_catalog(text)


# ---------------------------------------------------------------- the workspace
def write_project(workspace: Path, folder: str, **changes) -> Path:
    path = workspace / folder
    path.mkdir(parents=True)
    (path / "armor.project.json").write_text(json.dumps(manifest(changes.pop("name", folder), **changes)), encoding="utf-8")
    return path


def test_only_folders_with_their_own_manifest_are_projects(tmp_path: Path):
    write_project(tmp_path, "ARMOR-ONE")
    write_project(tmp_path, "armor-two")
    (tmp_path / "just-a-folder").mkdir()
    (tmp_path / "ARMOR-NOTES.txt").write_text("a file", encoding="utf-8")
    found = discover_workspace(tmp_path)
    assert [status.entry.name for status in found.projects] == ["ARMOR-ONE", "armor-two"]
    assert found.errors == ()
    assert all(status.installed and str(status.version) == "0.1.2" for status in found.projects)


def test_the_updaters_own_folders_and_old_backups_are_not_projects(tmp_path: Path):
    write_project(tmp_path, ".staging-ARMOR-ONE", name=".staging-ARMOR-ONE")
    write_project(tmp_path, "ARMOR-ONE.backup-20200101", name="ARMOR-ONE.backup-20200101")
    assert discover_workspace(tmp_path).projects == ()


def test_a_manifest_that_is_wrong_is_reported_and_the_others_are_still_found(tmp_path: Path):
    write_project(tmp_path, "ARMOR-GOOD")
    write_project(tmp_path, "ARMOR-LIAR", name="ARMOR-SOMETHING-ELSE")
    broken = tmp_path / "ARMOR-BROKEN"
    broken.mkdir()
    (broken / "armor.project.json").write_text("{nope", encoding="utf-8")
    found = discover_workspace(tmp_path)
    assert [status.entry.name for status in found.projects] == ["ARMOR-GOOD"]
    assert len(found.errors) == 2
    assert any(error.startswith("ARMOR-LIAR: invalid manifest") for error in found.errors)
    assert any(error.startswith("ARMOR-BROKEN: invalid manifest") for error in found.errors)


def test_a_workspace_that_is_not_there_is_an_error_not_a_crash(tmp_path: Path):
    found = discover_workspace(tmp_path / "missing")
    assert found.projects == () and "does not exist" in found.errors[0]
    assert scan_workspace(tmp_path / "missing") == []


def test_projects_are_listed_in_name_order_whatever_the_case(tmp_path: Path):
    for name in ("ARMOR-B", "armor-a", "ARMOR-C"):
        write_project(tmp_path, name)
    assert [status.entry.name for status in scan_workspace(tmp_path)] == ["armor-a", "ARMOR-B", "ARMOR-C"]


# ---------------------------------------------------------------- running git
def test_a_program_that_is_not_there_is_exit_127_not_an_exception(tmp_path: Path):
    done = git_ops._run(["no-such-program-armor"], cwd=tmp_path, capture_output=True)
    assert done.returncode == 127 and "Error" in done.stderr
    assert git_ops._run(["no-such-program-armor"], cwd=tmp_path / "missing-folder").returncode == 127


def test_the_output_of_a_child_is_joined_without_blank_ends():
    done = subprocess.CompletedProcess(["x"], 0, stdout="out\n", stderr="err\n")
    assert git_ops._command_output(done) == "out\n\nerr" or git_ops._command_output(done) == "out\nerr"
    assert git_ops._command_output(subprocess.CompletedProcess(["x"], 0, stdout="", stderr="")) == ""
    assert git_ops._command_output(subprocess.CompletedProcess(["x"], 0, stdout=None, stderr="only err")) == "only err"


def test_a_revision_is_read_without_touching_the_working_tree(tmp_path: Path):
    path = repo(tmp_path / "ARMOR-ONE", {"armor.project.json": json.dumps(manifest("ARMOR-ONE"))})
    revision = git(path, "rev-parse", "HEAD")
    assert git_ops._rev_parse(path, "HEAD") == revision
    entry = ProjectEntry(name="ARMOR-ONE", stack="Python")
    assert git_ops._manifest_from_revision(path, revision, entry).name == "ARMOR-ONE"
    (path / "armor.project.json").write_text("changed on disk", encoding="utf-8")
    assert git_ops._manifest_from_revision(path, revision, entry).version == "0.1.2"   # the committed manifest, not the edit


def test_a_revision_that_is_another_project_or_has_no_manifest_is_refused(tmp_path: Path):
    from armor_updater.project_manifest import ManifestValidationError
    path = repo(tmp_path / "ARMOR-ONE", {"armor.project.json": json.dumps(manifest("ARMOR-TWO"))})
    with pytest.raises(ManifestValidationError):
        git_ops._manifest_from_revision(path, "HEAD", ProjectEntry(name="ARMOR-ONE", stack="Python"))
    plain = repo(tmp_path / "ARMOR-PLAIN")
    with pytest.raises(ManifestValidationError, match="no readable"):
        git_ops._manifest_from_revision(plain, "HEAD", ProjectEntry(name="ARMOR-PLAIN", stack="Python"))
    with pytest.raises(ManifestValidationError, match="no readable"):
        git_ops._manifest_from_revision(plain, "no-such-revision", ProjectEntry(name="ARMOR-PLAIN", stack="Python"))


def test_the_branch_of_a_checkout_is_compared_with_the_default_one(tmp_path: Path):
    path = repo(tmp_path / "ARMOR-ONE")
    entry = ProjectEntry(name="ARMOR-ONE", stack="Python", default_branch="main")
    assert git_ops._wrong_branch_message(path, entry) == ""
    git(path, "checkout", "-q", "-b", "feature")
    message = git_ops._wrong_branch_message(path, entry)
    assert "'feature'" in message and "'main'" in message
    assert git_ops._wrong_branch_message(path, ProjectEntry(name="ARMOR-ONE", stack="Python")) == ""      # no default known: no opinion


def test_a_detached_head_and_a_folder_that_is_not_a_repository_are_not_refused(tmp_path: Path):
    path = repo(tmp_path / "ARMOR-ONE")
    git(path, "checkout", "-q", "--detach")
    assert git_ops._wrong_branch_message(path, ProjectEntry(name="ARMOR-ONE", stack="Python", default_branch="main")) == ""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git_ops._wrong_branch_message(plain, ProjectEntry(name="x", stack="Python", default_branch="main")) == ""


def test_the_remote_default_branch_wins_over_the_one_in_the_entry(tmp_path: Path):
    path = repo(tmp_path / "ARMOR-ONE", branch="trunk")
    git(path, "update-ref", "refs/remotes/origin/trunk", "HEAD")
    git(path, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    assert git_ops._wrong_branch_message(path, ProjectEntry(name="ARMOR-ONE", stack="Python", default_branch="main")) == ""
    git(path, "checkout", "-q", "-b", "other")
    assert "not the default branch 'trunk'" in git_ops._wrong_branch_message(path, ProjectEntry(name="ARMOR-ONE", stack="Python", default_branch="main"))


# ---------------------------------------------------------------- the folders the updater builds in
def test_checkpoints_reach_the_window_only_when_there_is_one():
    seen: list[tuple[str, str]] = []
    staging._checkpoint(lambda phase, message: seen.append((phase, message)), "build", "building")
    staging._checkpoint(None, "build", "nobody listens")
    assert seen == [("build", "building")]


def test_the_environments_of_the_build_are_removed_and_the_caller_is_told(tmp_path: Path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("#!/abs/path", encoding="utf-8")
    (tmp_path / "venv").mkdir()
    (tmp_path / "pkg.egg-info").mkdir()
    (tmp_path / "src" / "pkg.egg-info").mkdir(parents=True)
    (tmp_path / "__editable__pkg.pth").write_text("/abs", encoding="utf-8")
    (tmp_path / "src" / "keep.py").write_text("x = 1", encoding="utf-8")
    assert staging.remove_generated_environments(tmp_path) is True
    assert not (tmp_path / ".venv").exists() and not (tmp_path / "venv").exists()
    assert not (tmp_path / "pkg.egg-info").exists() and not (tmp_path / "src" / "pkg.egg-info").exists() and not (tmp_path / "__editable__pkg.pth").exists()
    assert (tmp_path / "src" / "keep.py").is_file()


def test_without_an_environment_nothing_is_removed_not_even_look_alikes(tmp_path: Path):
    (tmp_path / "pkg.egg-info").mkdir()
    (tmp_path / "__editable__pkg.pth").write_text("x", encoding="utf-8")
    assert staging.remove_generated_environments(tmp_path) is False
    assert (tmp_path / "pkg.egg-info").exists() and (tmp_path / "__editable__pkg.pth").exists()


def test_read_only_files_are_removed_too_and_a_missing_folder_is_not_an_error(tmp_path: Path):
    tree = tmp_path / "tree"
    (tree / "objects").mkdir(parents=True)
    locked = tree / "objects" / "pack.idx"
    locked.write_text("x", encoding="utf-8")
    locked.chmod(0o400)                                     # git leaves its object files like this, and Windows refuses to delete them
    staging._rmtree_best_effort(tree)
    assert not tree.exists()
    staging._rmtree_best_effort(tmp_path / "never-existed")


def test_untracked_and_ignored_files_are_the_local_data(tmp_path: Path):
    path = repo(tmp_path / "ARMOR-ONE", {"tracked.txt": "t\n", ".gitignore": "secret.env\ncache/\n"})
    (path / "secret.env").write_text("TOKEN=x", encoding="utf-8")
    (path / "cache").mkdir()
    (path / "cache" / "a.bin").write_text("c", encoding="utf-8")
    (path / "notes.txt").write_text("n", encoding="utf-8")
    (path / "tracked.txt").write_text("modified\n", encoding="utf-8")
    assert sorted(staging._real_untracked_paths(path)) == ["cache/a.bin", "notes.txt", "secret.env"]
    (tmp_path / "plain").mkdir()
    assert staging._real_untracked_paths(tmp_path / "plain") == []                     # not a repository: nothing to carry


def test_a_modified_tracked_file_blocks_and_untracked_data_does_not(tmp_path: Path):
    path = repo(tmp_path / "ARMOR-ONE", {"tracked.txt": "t\n", ".gitignore": "secret.env\n"})
    (path / "secret.env").write_text("x", encoding="utf-8")
    (path / "new.txt").write_text("n", encoding="utf-8")
    assert staging._tracked_dirty_paths(path) == []
    (path / "tracked.txt").write_text("edited\n", encoding="utf-8")
    assert staging._tracked_dirty_paths(path) == ["tracked.txt"]


def test_not_being_able_to_check_is_not_the_same_as_clean(tmp_path: Path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(staging.DirtyCheckError, match="could not verify"):
        staging._tracked_dirty_paths(plain)


def test_local_data_is_carried_into_the_candidate_but_build_output_never_is(tmp_path: Path):
    old = repo(tmp_path / "ARMOR-ONE", {"tracked.txt": "t\n", ".gitignore": "*.env\nnode_modules/\nbuild/\napp/build/\n.venv/\n"})
    (old / "users.env").write_text("ADMIN=1", encoding="utf-8")
    (old / "data").mkdir()
    (old / "data" / "db.sqlite").write_text("rows", encoding="utf-8")
    (old / "node_modules" / "dep").mkdir(parents=True)
    (old / "node_modules" / "dep" / "index.js").write_text("js", encoding="utf-8")
    (old / "app" / "build").mkdir(parents=True)
    (old / "app" / "build" / "out.apk").write_text("apk", encoding="utf-8")
    (old / ".venv").mkdir()
    (old / ".venv" / "marker").write_text("v", encoding="utf-8")
    candidate = tmp_path / "staging"
    candidate.mkdir()
    messages: list[str] = []
    staging._carry_over_local_data(old, candidate, progress=lambda phase, message: messages.append(message))
    carried = sorted(str(path.relative_to(candidate)).replace(os.sep, "/") for path in candidate.rglob("*") if path.is_file())
    assert carried == ["data/db.sqlite", "users.env"]
    assert messages and "Carried 2" in messages[0]


def test_nothing_to_carry_says_nothing(tmp_path: Path):
    old = repo(tmp_path / "ARMOR-ONE")
    candidate = tmp_path / "staging"
    candidate.mkdir()
    messages: list[str] = []
    staging._carry_over_local_data(old, candidate, progress=lambda phase, message: messages.append(message))
    assert messages == [] and list(candidate.iterdir()) == []


def test_cmake_build_trees_are_removed_only_when_they_are_cmake_trees(tmp_path: Path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "CMakeCache.txt").write_text("cache", encoding="utf-8")
    (tmp_path / "build-test").mkdir()
    (tmp_path / "build-test" / "something.txt").write_text("not cmake", encoding="utf-8")
    staging.forget_build_trees(tmp_path)
    assert not (tmp_path / "build").exists()
    assert (tmp_path / "build-test" / "something.txt").is_file()
