import unittest
from unittest.mock import patch

from ccproxy.cli import _claude_command
from ccproxy.env import build_claude_env


class WindowsCliTests(unittest.TestCase):
    def test_replaces_plain_claude_with_cmd_shim_on_windows(self) -> None:
        with patch("ccproxy.cli.platform.system", return_value="Windows"):
            with patch("ccproxy.cli._find_claude", return_value="C:\\Users\\me\\AppData\\Roaming\\npm\\claude.cmd"):
                self.assertEqual(
                    _claude_command(["--", "claude", "-p", "ping"]),
                    ["C:\\Users\\me\\AppData\\Roaming\\npm\\claude.cmd", "-p", "ping"],
                )

    def test_preserves_explicit_bare_mode(self) -> None:
        with patch("ccproxy.cli.platform.system", return_value="Windows"):
            with patch("ccproxy.cli._find_claude", return_value="C:\\Users\\me\\AppData\\Roaming\\npm\\claude.cmd"):
                self.assertEqual(
                    _claude_command(["--", "claude", "--bare", "-p", "ping"]),
                    ["C:\\Users\\me\\AppData\\Roaming\\npm\\claude.cmd", "--bare", "-p", "ping"],
                )

    def test_leaves_non_claude_command_unchanged(self) -> None:
        self.assertEqual(_claude_command(["python", "--version"]), ["python", "--version"])

    def test_prepends_claude_when_args_start_with_option(self) -> None:
        with patch("ccproxy.cli._find_claude", return_value="claude"):
            self.assertEqual(
                _claude_command(["--", "-p", "reply ccproxy-ok"]),
                ["claude", "-p", "reply ccproxy-ok"],
            )


class ClaudeEnvironmentTests(unittest.TestCase):
    def test_build_claude_env_sets_required_auth_vars(self) -> None:
        env = build_claude_env("http://127.0.0.1:8082", {"PATH": "x"})
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "http://127.0.0.1:8082")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "ccproxy")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "ccproxy")

    def test_build_claude_env_overrides_existing_anthropic_auth(self) -> None:
        env = build_claude_env(
            "http://127.0.0.1:8082",
            {"ANTHROPIC_API_KEY": "real-key", "ANTHROPIC_AUTH_TOKEN": "real-token"},
        )
        self.assertEqual(env["ANTHROPIC_API_KEY"], "ccproxy")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "ccproxy")


if __name__ == "__main__":
    unittest.main()
