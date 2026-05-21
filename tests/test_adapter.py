import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ccproxy import adapter


class AdapterTests(unittest.TestCase):
    def test_write_auth2api_config_uses_localhost_and_known_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = adapter.AdapterPaths(
                root=root,
                repo=root / "repo",
                auth_dir=root / "auth",
                config=root / "repo" / "config.yaml",
                log=root / "auth2api.log",
            )
            paths.repo.mkdir()
            adapter._write_auth2api_config(paths)
            text = paths.config.read_text(encoding="utf-8")
        self.assertIn("port: 8317", text)
        self.assertIn('auth-dir:', text)
        self.assertIn('"ccproxy-local"', text)

    def test_windows_npm_prefers_cmd_shim(self) -> None:
        with patch("ccproxy.adapter.platform.system", return_value="Windows"):
            with patch("ccproxy.adapter.shutil.which", side_effect=lambda name: f"C:/{name}" if name == "npm.cmd" else None):
                self.assertEqual(adapter._npm_command(), "C:/npm.cmd")

    def test_run_checked_wraps_subprocess_failures(self) -> None:
        with patch("ccproxy.adapter.subprocess.check_call", side_effect=subprocess.CalledProcessError(7, ["x"])):
            with self.assertRaisesRegex(adapter.ManagedAdapterError, "install failed with exit code 7"):
                adapter._run_checked(["x"], cwd=None, action="install")

    def test_ensure_chatgpt_adapter_installs_logs_in_and_starts(self) -> None:
        with patch("ccproxy.adapter.default_adapter_paths") as paths_factory:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                paths = adapter.AdapterPaths(
                    root=root,
                    repo=root / "repo",
                    auth_dir=root / "auth",
                    config=root / "repo" / "config.yaml",
                    log=root / "auth2api.log",
                )
                paths.repo.mkdir(parents=True)
                paths_factory.return_value = paths
                with patch("ccproxy.adapter._ensure_node"):
                    with patch("ccproxy.adapter._auth2api_installed", return_value=False):
                        with patch("ccproxy.adapter._install_auth2api") as install:
                            with patch("ccproxy.adapter._has_codex_token", return_value=False):
                                with patch("ccproxy.adapter._login_auth2api") as login:
                                    with patch("ccproxy.adapter.is_auth2api_running", return_value=False):
                                        with patch("ccproxy.adapter._start_auth2api") as start:
                                            with patch("ccproxy.adapter.wait_for_auth2api", return_value=True):
                                                adapter.ensure_chatgpt_adapter()
        install.assert_called_once()
        login.assert_called_once()
        start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
