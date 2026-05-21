import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ccproxy.cli import main


class CliTests(unittest.TestCase):
    def test_local_smoke_test(self) -> None:
        self.assertEqual(main(["test", "--profile", "minimax-cn"]), 0)


class ProfileCommandTests(unittest.TestCase):
    def test_profiles_lists_known_profiles(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["profiles"]), 0)
        text = out.getvalue()
        self.assertIn("openai-key", text)
        self.assertIn("chatgpt-subscription", text)
        self.assertIn("kimi", text)
        self.assertIn("zhipu", text)

    def test_use_sets_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "active.toml"
            with patch("ccproxy.cli.active_profile_path", return_value=state_path):
                self.assertEqual(main(["use", "kimi"]), 0)
                self.assertIn('profile = "kimi"', state_path.read_text(encoding="utf-8"))

    def test_current_uses_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "active.toml"
            state_path.write_text('profile = "zhipu"\n', encoding="utf-8")
            out = io.StringIO()
            with patch("ccproxy.cli.active_profile_path", return_value=state_path):
                with redirect_stdout(out):
                    self.assertEqual(main(["current"]), 0)
            self.assertIn("zhipu", out.getvalue())


if __name__ == "__main__":
    unittest.main()
