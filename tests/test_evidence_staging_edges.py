# =============================================================================
# ARMOR-UPDATER - Characterization of evidence and staging edge cases
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import subprocess
from pathlib import Path

from armor_updater import evidence, staging
from armor_updater.evidence import EVIDENCE_DIRECTORY, EVIDENCE_FILE, installed_state, read_attempts, record_attempt
from armor_updater.staging import forget_build_trees, remove_generated_environments


def test_the_state_of_a_folder_without_manifest_or_git_is_unknown(tmp_path: Path):
    assert installed_state(tmp_path) == {"version": None, "commit": None}


def test_a_damaged_manifest_leaves_the_version_unknown(tmp_path: Path):
    (tmp_path / "armor.project.json").write_text("{not json", encoding="utf-8")
    assert installed_state(tmp_path)["version"] is None


def test_git_failing_or_missing_leaves_the_commit_unknown(tmp_path: Path, monkeypatch):
    def failing(*args, **kwargs):  # noqa: ANN002, ANN003
        return subprocess.CompletedProcess(args, 128, stdout="", stderr="not a repository")

    monkeypatch.setattr(evidence.subprocess, "run", failing)
    assert installed_state(tmp_path)["commit"] is None

    def missing(*args, **kwargs):  # noqa: ANN002, ANN003
        raise FileNotFoundError("git")

    monkeypatch.setattr(evidence.subprocess, "run", missing)
    assert installed_state(tmp_path)["commit"] is None


def test_an_empty_commit_output_is_unknown(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(evidence.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="\n", stderr=""))
    assert installed_state(tmp_path)["commit"] is None


def test_a_commit_is_read_from_git_output(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(evidence.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="abc123\n", stderr=""))
    assert installed_state(tmp_path)["commit"] == "abc123"


def test_blank_lines_and_a_missing_file_read_as_no_attempts(tmp_path: Path):
    assert read_attempts(tmp_path) == []
    directory = tmp_path / EVIDENCE_DIRECTORY
    directory.mkdir()
    (directory / EVIDENCE_FILE).write_text('{"project": "A"}\n\n   \n{"project": "B"}\n', encoding="utf-8")
    assert [line["project"] for line in read_attempts(tmp_path)] == ["A", "B"]


def test_a_damaged_evidence_file_reads_as_no_attempts(tmp_path: Path):
    directory = tmp_path / EVIDENCE_DIRECTORY
    directory.mkdir()
    (directory / EVIDENCE_FILE).write_text("not json at all\n", encoding="utf-8")
    assert read_attempts(tmp_path) == []


def test_a_long_message_is_cut_and_the_duration_rounded(tmp_path: Path):
    record_attempt(tmp_path, project="P", before={}, after={}, ok=False, message="x" * 900, duration_s=1.26, now=0)
    (line,) = read_attempts(tmp_path)
    assert len(line["message"]) == 500
    assert line["durationS"] == 1.3
    assert line["at"] == "1970-01-01T00:00:00Z"
    assert line["versionBefore"] is None


def test_an_unwritable_workspace_gives_no_path_and_no_error(tmp_path: Path):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert record_attempt(blocker, project="P", before={}, after={}, ok=True, message="m") is None


def test_build_trees_with_a_cmake_cache_are_forgotten_and_the_others_kept(tmp_path: Path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "CMakeCache.txt").write_text("c", encoding="utf-8")
    (tmp_path / "build-test").mkdir()
    (tmp_path / "build-test" / "other.txt").write_text("o", encoding="utf-8")
    forget_build_trees(tmp_path)
    assert not (tmp_path / "build").exists()
    assert (tmp_path / "build-test" / "other.txt").exists()


def test_generated_environments_and_editable_leftovers_are_removed(tmp_path: Path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / "pkg.egg-info").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "x.egg-info").mkdir()
    (tmp_path / "__editable__pkg.pth").write_text("p", encoding="utf-8")
    (tmp_path / "keep.txt").write_text("k", encoding="utf-8")
    assert remove_generated_environments(tmp_path) is True
    assert not (tmp_path / ".venv").exists()
    assert not (tmp_path / "pkg.egg-info").exists()
    assert not (tmp_path / "src" / "x.egg-info").exists()
    assert not (tmp_path / "__editable__pkg.pth").exists()
    assert (tmp_path / "keep.txt").exists()


def test_without_an_environment_nothing_is_removed(tmp_path: Path):
    (tmp_path / "pkg.egg-info").mkdir()
    assert remove_generated_environments(tmp_path) is False
    assert (tmp_path / "pkg.egg-info").exists()


def test_removing_a_folder_that_is_not_there_returns_quietly(tmp_path: Path):
    staging._rmtree_best_effort(tmp_path / "missing")


def test_removing_a_folder_gives_up_after_five_attempts(tmp_path: Path, monkeypatch):
    calls = {"n": 0}

    def locked(path, **kwargs):  # noqa: ANN001, ANN003
        calls["n"] += 1
        raise PermissionError("in use")

    monkeypatch.setattr(staging, "rmtree", locked)
    monkeypatch.setattr(staging.time, "sleep", lambda seconds: None)
    staging._rmtree_best_effort(tmp_path)
    assert calls["n"] == 5


def test_the_retry_callback_makes_a_read_only_file_writable(tmp_path: Path):
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")
    seen: list[Path] = []
    staging._make_writable_and_retry(lambda path: seen.append(Path(path)), str(target), None)
    assert seen == [target]


def test_the_retry_callback_swallows_a_second_failure(tmp_path: Path):
    def refuse(path):  # noqa: ANN001
        raise OSError("still in use")

    staging._make_writable_and_retry(refuse, str(tmp_path / "missing"), None)
