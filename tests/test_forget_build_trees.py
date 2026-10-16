import tempfile
import unittest
from pathlib import Path

from armor_updater.install import forget_build_trees


class ForgetBuildTreesTests(unittest.TestCase):
    def test_a_cmake_tree_goes_and_other_folders_stay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build").mkdir(); (root / "build" / "CMakeCache.txt").write_text("x")
            (root / "src").mkdir(); (root / "src" / "main.py").write_text("x")
            (root / "build-test").mkdir(); (root / "build-test" / "notes.txt").write_text("not a cmake tree")
            forget_build_trees(root)
            self.assertFalse((root / "build").exists())
            self.assertTrue((root / "src" / "main.py").exists())
            self.assertTrue((root / "build-test" / "notes.txt").exists())


if __name__ == "__main__":
    unittest.main()
