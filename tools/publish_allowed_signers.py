#!/usr/bin/env python3
# =============================================================================
# ARMOR-UPDATER - tools/publish_allowed_signers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Makes the three files a release publishes so that the allowed-signers file can be fixed by fingerprint, and checks a published set.

    publish_allowed_signers.py OUT_DIR            writes allowed_signers, allowed_signers.sha256 and allowed_signers.fingerprints
    publish_allowed_signers.py --check OUT_DIR    exits 0 only when a published set is complete, its SHA-256 matches the file and its keys are exactly the pinned ones

It refuses to write anything while the shipped file does not hold exactly the keys pinned in `armor_updater.signature` (the same rule the updater applies before it trusts the file),
so a release never publishes a file the updater itself would reject. The release workflow runs it and uploads the three files next to the other assets; nothing is signed here.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from armor_updater import signature  # noqa: E402

NAME = "allowed_signers"
SUM_NAME = NAME + ".sha256"
PRINTS_NAME = NAME + ".fingerprints"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out_dir: Path, source: Path | None = None, pinned: frozenset[str] | None = None) -> list[Path]:
    """Writes the three files; raises ValueError (and writes nothing) when the file is not the pinned one."""
    source = signature.ECOSYSTEM_SIGNERS_FILE if source is None else source
    problem = signature.ecosystem_signers_problem(source, pinned)
    if problem:
        raise ValueError(problem)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    (out_dir / NAME).write_bytes(data)
    (out_dir / SUM_NAME).write_text(f"{hashlib.sha256(data).hexdigest()}  {NAME}\n", encoding="utf-8")
    (out_dir / PRINTS_NAME).write_text("".join(f"{item}\n" for item in sorted(signature.signer_fingerprints(source))), encoding="utf-8")
    return [out_dir / NAME, out_dir / SUM_NAME, out_dir / PRINTS_NAME]


def check(out_dir: Path, pinned: frozenset[str] | None = None) -> str | None:
    """None when a published set is complete and consistent, otherwise why not."""
    pinned = signature.PINNED_SIGNER_FINGERPRINTS if pinned is None else pinned
    for name in (NAME, SUM_NAME, PRINTS_NAME):
        if not (out_dir / name).is_file():
            return f"{name} is missing"
    published = out_dir / NAME
    words = (out_dir / SUM_NAME).read_text(encoding="utf-8").split()
    if len(words) != 2 or words[1] != NAME or words[0] != sha256_of(published):
        return f"{SUM_NAME} does not match {NAME}"
    try:
        found = signature.signer_fingerprints(published)
    except (OSError, ValueError) as error:
        return f"{NAME} cannot be read ({error})"
    if found != set(pinned):
        return f"the keys of {NAME} are not the pinned ones"
    listed = {line.strip() for line in (out_dir / PRINTS_NAME).read_text(encoding="utf-8").splitlines() if line.strip()}
    if listed != found:
        return f"{PRINTS_NAME} does not list the keys of {NAME}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--check", action="store_true", help="check a published set instead of writing one")
    arguments = parser.parse_args(argv)
    if arguments.check:
        problem = check(arguments.out_dir)
        print(problem or "the published allowed-signers set is complete and consistent")
        return 1 if problem else 0
    try:
        written = build(arguments.out_dir)
    except ValueError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
