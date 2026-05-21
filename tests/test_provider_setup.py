import unittest

from ccproxy.provider_setup import provider_key_missing, provider_setup_message, setup_for_profile
from ccproxy.presets import PRESETS


class ProviderSetupTests(unittest.TestCase):
    def test_api_key_provider_reports_missing_key(self) -> None:
        profile = PRESETS["openai-key"]
        self.assertTrue(provider_key_missing(profile, {}))
        self.assertFalse(provider_key_missing(profile, {"OPENAI_API_KEY": "sk-test"}))

    def test_custom_adapter_key_is_optional(self) -> None:
        self.assertFalse(provider_key_missing(PRESETS["custom"], {}))

    def test_known_providers_have_setup_urls(self) -> None:
        for name in ("openai-key", "kimi", "zhipu", "minimax-cn", "minimax-global"):
            with self.subTest(name=name):
                self.assertIsNotNone(setup_for_profile(PRESETS[name]))

    def test_setup_message_includes_env_and_url(self) -> None:
        message = provider_setup_message(PRESETS["openai-key"])
        self.assertIn("OPENAI_API_KEY", message)
        self.assertIn("https://platform.openai.com/api-keys", message)


if __name__ == "__main__":
    unittest.main()
