import unittest
from unittest.mock import patch

from ccproxy.cli import _claude_command


class WindowsCliTests(unittest.TestCase):
    def test_replaces_plain_claude_with_cmd_shim_on_windows(self) -> None:
        with patch("ccproxy.cli.platform.system", return_value="Windows"):
            with patch("ccproxy.cli._find_claude", return_value="C:\\Users\\me\\AppData\\Roaming\\npm\\claude.cmd"):
                self.assertEqual(
                    _claude_command(["--", "claude", "-p", "ping"]),
                    ["C:\\Users\\me\\AppData\\Roaming\\npm\\claude.cmd", "-p", "ping"],
                )


if __name__ == "__main__":
    unittest.main()
