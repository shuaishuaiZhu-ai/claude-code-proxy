import tempfile
import unittest
from pathlib import Path

from ccproxy.config import (
    active_profile_path,
    load_active_profile,
    save_active_profile,
)


class ActiveProfileTests(unittest.TestCase):
    def test_save_and_load_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active.toml"
            save_active_profile("kimi", path)
            self.assertEqual(load_active_profile(path), "kimi")

    def test_missing_active_profile_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active.toml"
            self.assertIsNone(load_active_profile(path))

    def test_rejects_unknown_profile_name_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active.toml"
            with self.assertRaises(ValueError):
                save_active_profile("../secret", path)

    def test_default_active_profile_path_lives_under_ccproxy_dir(self) -> None:
        path = active_profile_path()
        self.assertEqual(path.name, "active.toml")
        self.assertEqual(path.parent.name, ".ccproxy")


if __name__ == "__main__":
    unittest.main()
