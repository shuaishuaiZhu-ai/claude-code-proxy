from __future__ import annotations

from .config import ProviderProfile


PRESETS: dict[str, ProviderProfile] = {
    "openai-key": ProviderProfile(
        name="openai-key",
        type="openai-compatible",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        models={
            "big": "gpt-4.1",
            "middle": "gpt-4.1-mini",
            "small": "gpt-4.1-nano",
        },
    ),
    "openai": ProviderProfile(
        name="openai",
        type="openai-compatible",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        models={
            "big": "gpt-4.1",
            "middle": "gpt-4.1-mini",
            "small": "gpt-4.1-nano",
        },
    ),
    "chatgpt-subscription": ProviderProfile(
        name="chatgpt-subscription",
        type="external-adapter",
        base_url="http://127.0.0.1:8317/v1",
        api_key_env="",
        models={
            "big": "gpt-5.5",
            "middle": "gpt-5.4",
            "small": "gpt-5.4-mini",
            "ChatGPT5.5": "gpt-5.5",
            "ChatGPT5.4": "gpt-5.4",
        },
        headers={"Authorization": "Bearer ccproxy-local"},
    ),
    "kimi": ProviderProfile(
        name="kimi",
        type="openai-compatible",
        base_url="https://api.moonshot.cn/v1",
        api_key_env="KIMI_API_KEY",
        models={
            "big": "moonshot-v1-128k",
            "middle": "moonshot-v1-32k",
            "small": "moonshot-v1-8k",
        },
    ),
    "zhipu": ProviderProfile(
        name="zhipu",
        type="openai-compatible",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="ZHIPU_API_KEY",
        models={
            "big": "glm-4-plus",
            "middle": "glm-4-air",
            "small": "glm-4-flash",
        },
    ),
    "minimax-cn": ProviderProfile(
        name="minimax-cn",
        type="openai-compatible",
        base_url="https://api.minimaxi.com/v1",
        api_key_env="MINIMAX_API_KEY",
        models={
            "big": "MiniMax-M2.7",
            "middle": "MiniMax-M2.7-highspeed",
            "small": "MiniMax-M2.5",
        },
    ),
    "minimax-global": ProviderProfile(
        name="minimax-global",
        type="openai-compatible",
        base_url="https://api.minimax.io/v1",
        api_key_env="MINIMAX_API_KEY",
        models={
            "big": "MiniMax-M2.7",
            "middle": "MiniMax-M2.7-highspeed",
            "small": "MiniMax-M2.5",
        },
    ),
    "minimax-cn-anthropic": ProviderProfile(
        name="minimax-cn-anthropic",
        type="anthropic-compatible",
        base_url="https://api.minimaxi.com/anthropic",
        api_key_env="MINIMAX_API_KEY",
        models={
            "big": "MiniMax-M2.7",
            "middle": "MiniMax-M2.7-highspeed",
            "small": "MiniMax-M2.5",
        },
    ),
    "minimax-global-anthropic": ProviderProfile(
        name="minimax-global-anthropic",
        type="anthropic-compatible",
        base_url="https://api.minimax.io/anthropic",
        api_key_env="MINIMAX_API_KEY",
        models={
            "big": "MiniMax-M2.7",
            "middle": "MiniMax-M2.7-highspeed",
            "small": "MiniMax-M2.5",
        },
    ),
    "custom": ProviderProfile(
        name="custom",
        type="external-adapter",
        base_url="http://127.0.0.1:8000/v1",
        api_key_env="CCPROXY_CUSTOM_API_KEY",
        models={
            "big": "custom-big",
            "middle": "custom-middle",
            "small": "custom-small",
        },
    ),
}
