import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ccproxy.cli import main


class CliTests(unittest.TestCase):
    def test_local_smoke_test(self) -> None:
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["test", "--profile", "minimax-cn"]), 0)

    def test_claude_smoke_test_command_runs_real_claude_path(self) -> None:
        with patch("ccproxy.cli._run_claude_through_proxy", return_value=0) as runner:
            self.assertEqual(main(["test", "--profile", "custom", "--claude", "--prompt", "reply ccproxy-ok"]), 0)
        self.assertEqual(
            runner.call_args.args[2],
            ["claude", "--bare", "--model", "sonnet", "-p", "reply ccproxy-ok"],
        )
        self.assertEqual(runner.call_args.kwargs["expected_text"], "ccproxy-ok")


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
                with redirect_stdout(io.StringIO()):
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


class ModelCommandTests(unittest.TestCase):
    def test_model_set_non_interactive_sets_provider_and_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "active.toml"
            model_path = Path(tmp) / "models.toml"
            with patch("ccproxy.cli.active_profile_path", return_value=profile_path):
                with patch("ccproxy.cli.active_models_path", return_value=model_path):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(
                            main(["model", "set", "--provider", "chatgpt-subscription", "--model", "ChatGPT5.5"]),
                            0,
                        )
            self.assertIn('profile = "chatgpt-subscription"', profile_path.read_text(encoding="utf-8"))
            self.assertIn('"chatgpt-subscription" = "ChatGPT5.5"', model_path.read_text(encoding="utf-8"))

    def test_model_set_interactive_accepts_custom_model_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "active.toml"
            model_path = Path(tmp) / "models.toml"
            answers = iter(["chatgpt-subscription", "ChatGPT5.4"])
            with patch("ccproxy.cli.active_profile_path", return_value=profile_path):
                with patch("ccproxy.cli.active_models_path", return_value=model_path):
                    with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
                        with redirect_stdout(io.StringIO()):
                            self.assertEqual(main(["model", "set"]), 0)
            self.assertIn('"chatgpt-subscription" = "ChatGPT5.4"', model_path.read_text(encoding="utf-8"))

    def test_model_current_prints_active_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "active.toml"
            model_path = Path(tmp) / "models.toml"
            profile_path.write_text('profile = "chatgpt-subscription"\n', encoding="utf-8")
            model_path.write_text('[models]\n"chatgpt-subscription" = "ChatGPT5.5"\n', encoding="utf-8")
            out = io.StringIO()
            with patch("ccproxy.cli.active_profile_path", return_value=profile_path):
                with patch("ccproxy.cli.active_models_path", return_value=model_path):
                    with redirect_stdout(out):
                        self.assertEqual(main(["model", "current"]), 0)
            self.assertIn("chatgpt-subscription", out.getvalue())
            self.assertIn("ChatGPT5.5", out.getvalue())

    def test_model_clear_removes_active_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "active.toml"
            model_path = Path(tmp) / "models.toml"
            profile_path.write_text('profile = "chatgpt-subscription"\n', encoding="utf-8")
            model_path.write_text('[models]\n"chatgpt-subscription" = "ChatGPT5.5"\n', encoding="utf-8")
            with patch("ccproxy.cli.active_profile_path", return_value=profile_path):
                with patch("ccproxy.cli.active_models_path", return_value=model_path):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(main(["model", "clear"]), 0)
            self.assertNotIn("ChatGPT5.5", model_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
