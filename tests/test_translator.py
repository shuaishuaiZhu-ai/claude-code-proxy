import json
import unittest

from ccproxy.presets import PRESETS
from ccproxy.translator import anthropic_to_openai, openai_stream_to_anthropic_sse, openai_to_anthropic, select_model


class TranslatorTests(unittest.TestCase):
    def test_model_mapping(self) -> None:
        profile = PRESETS["minimax-cn"]
        self.assertEqual(select_model("claude-3-opus-latest", profile), "MiniMax-M2.7")
        self.assertEqual(select_model("claude-3-5-sonnet-latest", profile), "MiniMax-M2.7-highspeed")
        self.assertEqual(select_model("claude-3-haiku-latest", profile), "MiniMax-M2.5")

    def test_active_upstream_model_overrides_mapping(self) -> None:
        profile = PRESETS["chatgpt-subscription"].with_upstream_model("ChatGPT5.5")
        self.assertEqual(select_model("claude-3-5-sonnet-latest", profile), "gpt-5.5")

    def test_custom_alias_maps_before_heuristics(self) -> None:
        profile = PRESETS["chatgpt-subscription"].with_upstream_model(None)
        profile = profile.__class__(
            name=profile.name,
            type=profile.type,
            base_url=profile.base_url,
            api_key_env=profile.api_key_env,
            models={"big": "fallback-big", "thinking": "ChatGPT5.5", "openrouter/qwen3-coder:free": "qwen3"},
        )
        self.assertEqual(select_model("thinking", profile), "ChatGPT5.5")
        self.assertEqual(select_model("openrouter/qwen3-coder:free", profile), "qwen3")

    def test_anthropic_text_and_tool_to_openai(self) -> None:
        profile = PRESETS["openai"]
        payload = anthropic_to_openai(
            {
                "model": "claude-3-5-sonnet-latest",
                "max_tokens": 64,
                "system": "You are terse.",
                "messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
                "tools": [{"name": "echo", "description": "Echo.", "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}}}],
            },
            profile,
        )
        self.assertEqual(payload["messages"][0], {"role": "system", "content": "You are terse."})
        self.assertEqual(payload["messages"][1], {"role": "user", "content": "hello"})
        self.assertEqual(payload["tools"][0]["function"]["name"], "echo")

    def test_assistant_tool_use_to_openai_tool_call(self) -> None:
        payload = anthropic_to_openai(
            {
                "model": "claude-3-opus-latest",
                "messages": [
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "calling"},
                            {"type": "tool_use", "id": "toolu_1", "name": "echo", "input": {"text": "x"}},
                        ],
                    }
                ],
            },
            PRESETS["openai"],
        )
        assistant = payload["messages"][0]
        self.assertEqual(assistant["tool_calls"][0]["id"], "toolu_1")
        self.assertEqual(json.loads(assistant["tool_calls"][0]["function"]["arguments"]), {"text": "x"})

    def test_openai_response_to_anthropic_tool_use(self) -> None:
        payload = openai_to_anthropic(
            {
                "id": "chatcmpl_1",
                "model": "gpt-test",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {"id": "call_1", "type": "function", "function": {"name": "echo", "arguments": "{\"text\":\"x\"}"}}
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3},
            },
            requested_model="claude-test",
        )
        self.assertEqual(payload["stop_reason"], "tool_use")
        self.assertEqual(payload["content"][0]["name"], "echo")
        self.assertEqual(payload["usage"]["input_tokens"], 2)

    def test_openai_stream_to_anthropic_sse(self) -> None:
        chunks = [
            {"choices": [{"delta": {"content": "ccproxy"}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": "-ok"}, "finish_reason": "stop"}]},
        ]
        raw = b"".join(openai_stream_to_anthropic_sse(chunks, "test-model")).decode("utf-8")
        self.assertIn("event: message_start", raw)
        self.assertIn("ccproxy", raw)
        self.assertIn("event: message_stop", raw)


if __name__ == "__main__":
    unittest.main()
