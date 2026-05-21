from __future__ import annotations

from collections.abc import Mapping


def build_claude_env(base_url: str, current_env: Mapping[str, str]) -> dict[str, str]:
    env = dict(current_env)
    env["ANTHROPIC_BASE_URL"] = base_url
    env.setdefault("ANTHROPIC_API_KEY", "ccproxy")
    env.setdefault("ANTHROPIC_AUTH_TOKEN", env["ANTHROPIC_API_KEY"])
    return env


def ensure_bare_args(args: list[str]) -> list[str]:
    if "--bare" in args:
        return args
    if not args:
        return ["claude", "--bare"]
    return [args[0], "--bare", *args[1:]]
