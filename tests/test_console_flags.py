"""Every child process of the updater must be started without a console window of its own (the GUI runs under pythonw.exe on Windows)."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "armor_updater"
SPAWNERS = {"run", "Popen", "call", "check_call", "check_output"}


def _spawn_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in SPAWNERS:
            owner = node.func.value
            if isinstance(owner, ast.Name) and owner.id == "subprocess":
                yield node


class NoConsoleWindowTests(unittest.TestCase):
    def test_every_child_process_hides_its_console(self) -> None:
        missing: list[str] = []
        for source in sorted(PACKAGE.glob("*.py")):
            for call in _spawn_calls(ast.parse(source.read_text(encoding="utf-8"))):
                keywords = {k.arg for k in call.keywords}
                if "creationflags" not in keywords and None not in keywords:   # None = **kwargs built by the caller
                    missing.append(f"{source.name}:{call.lineno}")
        self.assertEqual(missing, [], "subprocess call without creationflags=NO_WINDOW: " + ", ".join(missing))

    def test_the_helper_is_a_noop_off_windows(self) -> None:
        from armor_updater import console_flags
        import os
        if os.name != "nt":
            self.assertEqual(console_flags.NO_WINDOW, 0)
            self.assertFalse(console_flags.headless())


if __name__ == "__main__":
    unittest.main()
