import tempfile
import unittest
from pathlib import Path

from ccproxy.config import (
    clear_active_model,
    load_active_model,
    load_active_models,
    save_active_model,
    validate_model_name,
)


class ActiveModelTests(unittest.TestCase):
    def test_save_and_load_active_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.toml"
            save_active_model("chatgpt-subscription", "ChatGPT5.5", path)
            self.assertEqual(load_active_model("chatgpt-subscription", path), "ChatGPT5.5")

    def test_preserves_multiple_provider_models(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.toml"
            save_active_model("chatgpt-subscription", "ChatGPT5.5", path)
            save_active_model("kimi", "moonshot-v1-128k", path)
            self.assertEqual(
                load_active_models(path),
                {"chatgpt-subscription": "ChatGPT5.5", "kimi": "moonshot-v1-128k"},
            )

    def test_clear_active_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.toml"
            save_active_model("chatgpt-subscription", "ChatGPT5.5", path)
            self.assertTrue(clear_active_model("chatgpt-subscription", path))
            self.assertIsNone(load_active_model("chatgpt-subscription", path))

    def test_rejects_empty_or_control_model_name(self) -> None:
        with self.assertRaises(ValueError):
            validate_model_name(" ")
        with self.assertRaises(ValueError):
            validate_model_name("bad\nmodel")


if __name__ == "__main__":
    unittest.main()
