import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ccproxy.client import UpstreamClient
from ccproxy.presets import PRESETS
from ccproxy.secrets import get_api_key, save_api_key


class SecretStoreTests(unittest.TestCase):
    def test_saved_api_key_is_loaded_when_environment_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secrets.toml"
            save_api_key("OPENAI_API_KEY", "sk-saved", path)
            self.assertEqual(get_api_key("OPENAI_API_KEY", environ={}, path=path), "sk-saved")

    def test_environment_api_key_wins_over_saved_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secrets.toml"
            save_api_key("OPENAI_API_KEY", "sk-saved", path)
            self.assertEqual(get_api_key("OPENAI_API_KEY", environ={"OPENAI_API_KEY": "sk-env"}, path=path), "sk-env")

    def test_upstream_client_uses_saved_secret(self) -> None:
        with patch("ccproxy.client.get_api_key", return_value="sk-saved"):
            client = UpstreamClient(PRESETS["openai-key"])
            self.assertEqual(client._api_key(), "sk-saved")


if __name__ == "__main__":
    unittest.main()
