import tempfile
import unittest
from pathlib import Path

from ccproxy.config import load_config, write_default_config
from ccproxy.presets import PRESETS


class ConfigTests(unittest.TestCase):
    def test_minimax_presets(self) -> None:
        self.assertEqual(PRESETS["minimax-cn"].base_url, "https://api.minimaxi.com/v1")
        self.assertEqual(PRESETS["minimax-global"].base_url, "https://api.minimax.io/v1")
        self.assertEqual(PRESETS["minimax-cn-anthropic"].type, "anthropic-compatible")

    def test_write_and_load_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            write_default_config(path, "minimax-cn")
            config = load_config(path)
            self.assertEqual(config.default_profile, "minimax-cn")
            self.assertIn("openai-key", config.profiles)
            self.assertIn("chatgpt-subscription", config.profiles)
            self.assertIn("minimax-cn", config.profiles)


if __name__ == "__main__":
    unittest.main()
