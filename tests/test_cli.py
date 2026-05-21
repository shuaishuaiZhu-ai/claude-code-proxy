import io
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ccproxy.cli import _local_upstream_error, main
from ccproxy.config import ProviderProfile


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

    def test_local_upstream_preflight_reports_missing_adapter(self) -> None:
        profile = ProviderProfile(
            name="chatgpt-subscription",
            type="external-adapter",
            base_url="http://127.0.0.1:1/v1",
            api_key_env="",
        )
        error = _local_upstream_error(profile)
        self.assertIsNotNone(error)
        self.assertIn("upstream adapter is not reachable", error or "")

    def test_local_upstream_preflight_allows_reachable_adapter(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        try:
            port = listener.getsockname()[1]
            profile = ProviderProfile(
                name="custom",
                type="external-adapter",
                base_url=f"http://127.0.0.1:{port}/v1",
                api_key_env="CCPROXY_CUSTOM_API_KEY",
            )
            self.assertIsNone(_local_upstream_error(profile))
        finally:
            listener.close()

    def test_init_runs_model_selection_and_prepares_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            profile_path = Path(tmp) / "active.toml"
            model_path = Path(tmp) / "models.toml"
            with patch("ccproxy.cli.active_profile_path", return_value=profile_path):
                with patch("ccproxy.cli.active_models_path", return_value=model_path):
                    with patch("ccproxy.cli.ensure_chatgpt_adapter") as adapter:
                        with redirect_stdout(io.StringIO()):
                            self.assertEqual(
                                main(
                                    [
                                        "init",
                                        "--config",
                                        str(config_path),
                                        "--profile",
                                        "chatgpt-subscription",
                                        "--model",
                                        "ChatGPT5.5",
                                    ]
                                ),
                                0,
                            )
            adapter.assert_called_once()
            self.assertTrue(config_path.exists())
            self.assertIn('default_profile = "chatgpt-subscription"', config_path.read_text(encoding="utf-8"))
            self.assertIn('profile = "chatgpt-subscription"', profile_path.read_text(encoding="utf-8"))


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
                            main(["model", "set", "--provider", "chatgpt-subscription", "--model", "ChatGPT5.5", "--no-adapter-start"]),
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
                            self.assertEqual(main(["model", "set", "--no-adapter-start"]), 0)
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

    def test_model_set_prepares_chatgpt_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "active.toml"
            model_path = Path(tmp) / "models.toml"
            with patch("ccproxy.cli.active_profile_path", return_value=profile_path):
                with patch("ccproxy.cli.active_models_path", return_value=model_path):
                    with patch("ccproxy.cli.ensure_chatgpt_adapter") as adapter:
                        with redirect_stdout(io.StringIO()):
                            self.assertEqual(
                                main(["model", "set", "--provider", "chatgpt-subscription", "--model", "ChatGPT5.5"]),
                                0,
                            )
            adapter.assert_called_once()

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
