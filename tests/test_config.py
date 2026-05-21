import tempfile
import unittest
from pathlib import Path

from ccproxy.config import ProviderProfile, ServerConfig, load_config, render_config, write_default_config
from ccproxy.presets import PRESETS


class ConfigTests(unittest.TestCase):
    def test_minimax_presets(self) -> None:
        self.assertEqual(PRESETS["minimax-cn"].base_url, "https://api.minimaxi.com/v1")
        self.assertEqual(PRESETS["minimax-global"].base_url, "https://api.minimax.io/v1")
        self.assertEqual(PRESETS["minimax-cn-anthropic"].type, "anthropic-compatible")

    def test_required_provider_profiles_exist(self) -> None:
        required = {
            "openai-key": "OPENAI_API_KEY",
            "chatgpt-subscription": "CHATGPT_ADAPTER_API_KEY",
            "kimi": "KIMI_API_KEY",
            "zhipu": "ZHIPU_API_KEY",
            "minimax-cn": "MINIMAX_API_KEY",
            "minimax-global": "MINIMAX_API_KEY",
        }
        for name, env_name in required.items():
            with self.subTest(name=name):
                self.assertIn(name, PRESETS)
                self.assertEqual(PRESETS[name].api_key_env, env_name)

    def test_write_and_load_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            write_default_config(path, "minimax-cn")
            config = load_config(path)
            self.assertEqual(config.default_profile, "minimax-cn")
            self.assertIn("openai-key", config.profiles)
            self.assertIn("chatgpt-subscription", config.profiles)
            self.assertIn("minimax-cn", config.profiles)

    def test_render_config_quotes_custom_model_aliases(self) -> None:
        profile = ProviderProfile(
            name="chatgpt-subscription",
            type="external-adapter",
            base_url="http://127.0.0.1:8000/v1",
            api_key_env="CHATGPT_ADAPTER_API_KEY",
            models={"ChatGPT5.5": "ChatGPT5.5"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(render_config("chatgpt-subscription", {profile.name: profile}, ServerConfig()), encoding="utf-8")
            config = load_config(path)
        self.assertEqual(config.profiles["chatgpt-subscription"].models["ChatGPT5.5"], "ChatGPT5.5")


if __name__ == "__main__":
    unittest.main()
