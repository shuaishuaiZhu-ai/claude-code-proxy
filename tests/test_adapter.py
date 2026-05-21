import subprocess
import tempfile
import unittest
import base64
import json
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

    def test_login_uses_manual_mode_when_callback_port_is_busy(self) -> None:
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
            with patch("ccproxy.adapter._node_command", return_value="node"):
                with patch("ccproxy.adapter._is_port_in_use", return_value=True):
                    with patch("ccproxy.adapter._run_checked") as runner:
                        adapter._login_auth2api(paths)
        self.assertIn("--manual", runner.call_args.args[0])

    def test_login_uses_callback_mode_when_callback_port_is_free(self) -> None:
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
            with patch("ccproxy.adapter._node_command", return_value="node"):
                with patch("ccproxy.adapter._is_port_in_use", return_value=False):
                    with patch("ccproxy.adapter._run_checked") as runner:
                        adapter._login_auth2api(paths)
        self.assertNotIn("--manual", runner.call_args.args[0])

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
                                    with patch("ccproxy.adapter._login_codex_device_auth", side_effect=adapter.ManagedAdapterError("device failed")):
                                        with patch("ccproxy.adapter.is_auth2api_running", return_value=False):
                                            with patch("ccproxy.adapter._start_auth2api") as start:
                                                with patch("ccproxy.adapter.wait_for_auth2api", return_value=True):
                                                    adapter.ensure_chatgpt_adapter()
        install.assert_called_once()
        login.assert_called_once()
        start.assert_called_once()

    def test_ensure_chatgpt_adapter_uses_device_auth_before_browser_login(self) -> None:
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
                    with patch("ccproxy.adapter._auth2api_installed", return_value=True):
                        with patch("ccproxy.adapter._has_codex_token", side_effect=[False, True]):
                            with patch("ccproxy.adapter._login_codex_device_auth") as device:
                                with patch("ccproxy.adapter._login_auth2api") as browser:
                                    with patch("ccproxy.adapter.is_auth2api_running", return_value=True):
                                        with patch("ccproxy.adapter.wait_for_auth2api", return_value=True):
                                            adapter.ensure_chatgpt_adapter()
        device.assert_called_once()
        browser.assert_not_called()

    def test_login_codex_device_auth_saves_token_without_browser_callback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = adapter.AdapterPaths(
                root=root,
                repo=root / "repo",
                auth_dir=root / "auth",
                config=root / "repo" / "config.yaml",
                log=root / "auth2api.log",
            )
            with patch(
                "ccproxy.adapter._request_codex_device_code",
                return_value=adapter.DeviceCode(
                    verification_url="https://auth.openai.com/codex/device",
                    user_code="ABCD-1234",
                    device_auth_id="device-id",
                    interval=1,
                ),
            ):
                with patch("ccproxy.adapter.webbrowser.open"):
                    with patch(
                        "ccproxy.adapter._poll_codex_device_code",
                        return_value={
                            "authorization_code": "auth-code",
                            "code_verifier": "verifier",
                            "code_challenge": "challenge",
                        },
                    ):
                        with patch(
                            "ccproxy.adapter._exchange_codex_device_code",
                            return_value={
                                "id_token": _jwt(
                                    {
                                        "email": "user@example.com",
                                        "https://api.openai.com/auth": {
                                            "chatgpt_account_id": "acct-id",
                                            "chatgpt_plan_type": "pro",
                                        },
                                    }
                                ),
                                "access_token": _jwt({"exp": 4102444800}),
                                "refresh_token": "refresh-token",
                            },
                        ):
                            adapter._login_codex_device_auth(paths, open_browser=True)

            imported = paths.auth_dir / "codex-user@example.com.json"
            storage = json.loads(imported.read_text(encoding="utf-8"))
        self.assertEqual(storage["type"], "codex")
        self.assertEqual(storage["refresh_token"], "refresh-token")


def _jwt(payload: dict) -> str:
    header = {"alg": "none", "typ": "JWT"}
    return ".".join((_b64(header), _b64(payload), "sig"))


def _b64(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


if __name__ == "__main__":
    unittest.main()
