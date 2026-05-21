from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import platform

from .config import ProviderProfile
from .secrets import get_api_key


@dataclass(frozen=True)
class ProviderSetup:
    label: str
    url: str


API_KEY_SETUP: dict[str, ProviderSetup] = {
    "openai-key": ProviderSetup("OpenAI API keys", "https://platform.openai.com/api-keys"),
    "openai": ProviderSetup("OpenAI API keys", "https://platform.openai.com/api-keys"),
    "deepseek": ProviderSetup("DeepSeek API keys", "https://platform.deepseek.com/api_keys"),
    "kimi": ProviderSetup("Kimi Open Platform console", "https://platform.kimi.com/console/api-keys"),
    "zhipu": ProviderSetup("Zhipu BigModel API keys", "https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys"),
    "minimax-cn": ProviderSetup("MiniMax China API keys", "https://platform.minimaxi.com/user-center/basic-information/interface-key"),
    "minimax-global": ProviderSetup("MiniMax Global API keys", "https://platform.minimax.io/user-center/basic-information/interface-key"),
    "minimax-subscription": ProviderSetup("MiniMax Token Plan key", "https://platform.minimaxi.com/user-center/basic-information/interface-key"),
    "minimax-cn-anthropic": ProviderSetup("MiniMax China API keys", "https://platform.minimaxi.com/user-center/basic-information/interface-key"),
    "minimax-global-anthropic": ProviderSetup("MiniMax Global API keys", "https://platform.minimax.io/user-center/basic-information/interface-key"),
}


def provider_key_missing(profile: ProviderProfile, environ: Mapping[str, str] | None = None) -> bool:
    if not profile.api_key_env or profile.name == "custom":
        return False
    return not get_api_key(profile.api_key_env, environ=environ, include_saved=environ is None)


def setup_for_profile(profile: ProviderProfile) -> ProviderSetup | None:
    return API_KEY_SETUP.get(profile.name)


def provider_setup_message(profile: ProviderProfile) -> str:
    setup = setup_for_profile(profile)
    lines = [
        f"provider is not configured: {profile.name}",
        f"missing API key: {profile.api_key_env}",
    ]
    if setup:
        lines.append(f"get an API key here: {setup.url}")
    lines.extend(_env_command_lines(profile.api_key_env))
    lines.append("Or paste the key when ccproxy asks for it.")
    return "\n".join(lines)


def _env_command_lines(env_name: str) -> list[str]:
    if platform.system().lower() == "windows":
        return [
            "Set it for the current PowerShell session:",
            f'  $env:{env_name}="paste-your-api-key"',
            "Or for the current CMD session:",
            f"  set {env_name}=paste-your-api-key",
        ]
    return [
        "Set it for the current shell session:",
        f'  export {env_name}="paste-your-api-key"',
    ]
