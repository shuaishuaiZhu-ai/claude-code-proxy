from __future__ import annotations

from collections.abc import Mapping


def build_claude_env(base_url: str, current_env: Mapping[str, str]) -> dict[str, str]:
    env = dict(current_env)
    env["ANTHROPIC_BASE_URL"] = base_url
    env["ANTHROPIC_API_KEY"] = "ccproxy"
    env["ANTHROPIC_AUTH_TOKEN"] = "ccproxy"
    return env
