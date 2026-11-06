# =============================================================================
# ARMOR-UPDATER - tests/test_publish_allowed_signers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The files a release publishes for pinning the allowed-signers file by fingerprint are made only from the pinned file and are checked end to end."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

from armor_updater import signature

SPEC = importlib.util.spec_from_file_location("publish_allowed_signers", Path(__file__).resolve().parent.parent / "tools" / "publish_allowed_signers.py")
assert SPEC is not None and SPEC.loader is not None
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def test_the_three_files_are_made_from_the_shipped_file(tmp_path):
    written = tool.build(tmp_path)
    assert [path.name for path in written] == ["allowed_signers", "allowed_signers.sha256", "allowed_signers.fingerprints"]
    shipped = signature.ECOSYSTEM_SIGNERS_FILE.read_bytes()
    assert (tmp_path / "allowed_signers").read_bytes() == shipped
    assert (tmp_path / "allowed_signers.sha256").read_text().split() == [hashlib.sha256(shipped).hexdigest(), "allowed_signers"]
    assert set((tmp_path / "allowed_signers.fingerprints").read_text().split()) == set(signature.PINNED_SIGNER_FINGERPRINTS)
    assert tool.check(tmp_path) is None


def test_nothing_is_written_while_the_file_is_not_the_pinned_one(tmp_path):
    other = tmp_path / "other"
    other.write_text("a@b.invalid namespaces=\"git\" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n", encoding="utf-8")
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="pinned|cannot be read"):
        tool.build(out, source=other)
    assert not out.exists()


def test_a_published_set_that_was_changed_is_found(tmp_path):
    tool.build(tmp_path)
    (tmp_path / "allowed_signers").write_text((tmp_path / "allowed_signers").read_text() + "# a change\n", encoding="utf-8")
    assert "does not match" in tool.check(tmp_path)
    (tmp_path / "allowed_signers.sha256").unlink()
    assert "missing" in tool.check(tmp_path)


def test_a_fingerprint_list_that_lies_is_found(tmp_path):
    tool.build(tmp_path)
    (tmp_path / "allowed_signers.fingerprints").write_text("SHA256:other\n", encoding="utf-8")
    assert "does not list" in tool.check(tmp_path)


def test_the_command_line_exits_with_the_result(tmp_path, capsys):
    assert tool.main([str(tmp_path / "set")]) == 0
    assert tool.main(["--check", str(tmp_path / "set")]) == 0
    assert tool.main(["--check", str(tmp_path / "empty")]) == 1
    assert "missing" in capsys.readouterr().out
