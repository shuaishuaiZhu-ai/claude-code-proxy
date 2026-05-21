from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
import os
import tomllib


CONFIG_DIR = ".ccproxy"
CONFIG_FILE = "config.toml"


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8082


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    type: str
    base_url: str
    api_key_env: str
    models: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)

    def with_name(self, name: str) -> "ProviderProfile":
        return replace(self, name=name)


@dataclass(frozen=True)
class ProxyConfig:
    server: ServerConfig
    profiles: dict[str, ProviderProfile]
    default_profile: str = "openai-key"


def default_config_path() -> Path:
    return Path.home() / CONFIG_DIR / CONFIG_FILE


def provider_from_mapping(name: str, data: dict[str, Any]) -> ProviderProfile:
    models = data.get("models") or {}
    headers = data.get("headers") or {}
    return ProviderProfile(
        name=name,
        type=str(data.get("type", "openai-compatible")),
        base_url=str(data["base_url"]).rstrip("/"),
        api_key_env=str(data.get("api_key_env", "")),
        models={str(k): str(v) for k, v in models.items()},
        headers={str(k): str(v) for k, v in headers.items()},
    )


def load_config(path: str | os.PathLike[str] | None = None) -> ProxyConfig:
    from .presets import PRESETS

    config_path = Path(path) if path else default_config_path()
    if not config_path.exists():
        return ProxyConfig(server=ServerConfig(), profiles=PRESETS.copy())

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    server_data = data.get("server", {})
    server = ServerConfig(
        host=str(server_data.get("host", "127.0.0.1")),
        port=int(server_data.get("port", 8082)),
    )
    profiles: dict[str, ProviderProfile] = {}
    for name, profile_data in (data.get("profiles") or {}).items():
        profiles[str(name)] = provider_from_mapping(str(name), profile_data)
    if not profiles:
        profiles = PRESETS.copy()
    default_profile = str(data.get("default_profile", "openai-key"))
    return ProxyConfig(server=server, profiles=profiles, default_profile=default_profile)


def render_config(default_profile: str, profiles: dict[str, ProviderProfile], server: ServerConfig | None = None) -> str:
    active_server = server or ServerConfig()
    lines = [
        "# cc-provider-proxy configuration",
        "# Secrets are read from environment variables named by api_key_env.",
        f'default_profile = "{default_profile}"',
        "",
        "[server]",
        f'host = "{active_server.host}"',
        f"port = {active_server.port}",
        "",
    ]
    for name in sorted(profiles):
        profile = profiles[name]
        lines.extend(
            [
                f"[profiles.{name}]",
                f'type = "{profile.type}"',
                f'base_url = "{profile.base_url}"',
                f'api_key_env = "{profile.api_key_env}"',
                "",
                f"[profiles.{name}.models]",
            ]
        )
        for model_name in ("big", "middle", "small"):
            if model_name in profile.models:
                lines.append(f'{model_name} = "{profile.models[model_name]}"')
        for model_name, value in sorted(profile.models.items()):
            if model_name not in {"big", "middle", "small"}:
                lines.append(f'{model_name} = "{value}"')
        if profile.headers:
            lines.extend(["", f"[profiles.{name}.headers]"])
            for header, value in sorted(profile.headers.items()):
                lines.append(f'{header} = "{value}"')
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_default_config(path: str | os.PathLike[str] | None, default_profile: str) -> Path:
    from .presets import PRESETS

    if default_profile not in PRESETS:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(f"unknown profile {default_profile!r}; choose one of: {known}")
    config_path = Path(path) if path else default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(render_config(default_profile, PRESETS), encoding="utf-8")
    return config_path


def select_profile(config: ProxyConfig, profile_name: str | None) -> ProviderProfile:
    name = profile_name or config.default_profile
    try:
        return config.profiles[name]
    except KeyError as exc:
        known = ", ".join(sorted(config.profiles))
        raise ValueError(f"unknown profile {name!r}; configured profiles: {known}") from exc
