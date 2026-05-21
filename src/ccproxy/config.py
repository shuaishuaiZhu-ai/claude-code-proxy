from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
import json
import os
import tomllib


CONFIG_DIR = ".ccproxy"
CONFIG_FILE = "config.toml"
ACTIVE_PROFILE_FILE = "active.toml"
ACTIVE_MODELS_FILE = "models.toml"


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
    upstream_model: str | None = None

    def with_name(self, name: str) -> "ProviderProfile":
        return replace(self, name=name)

    def with_upstream_model(self, model: str | None) -> "ProviderProfile":
        return replace(self, upstream_model=validate_model_name(model) if model else None)


@dataclass(frozen=True)
class ProxyConfig:
    server: ServerConfig
    profiles: dict[str, ProviderProfile]
    default_profile: str = "openai-key"


def default_config_path() -> Path:
    return Path.home() / CONFIG_DIR / CONFIG_FILE


def active_profile_path() -> Path:
    return Path.home() / CONFIG_DIR / ACTIVE_PROFILE_FILE


def active_models_path() -> Path:
    return Path.home() / CONFIG_DIR / ACTIVE_MODELS_FILE


def validate_profile_name(profile_name: str) -> str:
    cleaned = profile_name.strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if not cleaned or any(char not in allowed for char in cleaned):
        raise ValueError(f"invalid profile name {profile_name!r}")
    return cleaned


def validate_model_name(model_name: str) -> str:
    cleaned = model_name.strip()
    if not cleaned or any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise ValueError(f"invalid model name {model_name!r}")
    return cleaned


def save_active_profile(profile_name: str, path: str | os.PathLike[str] | None = None) -> Path:
    selected = validate_profile_name(profile_name)
    state_path = Path(path) if path else active_profile_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(f'profile = "{selected}"\n', encoding="utf-8")
    return state_path


def load_active_profile(path: str | os.PathLike[str] | None = None) -> str | None:
    state_path = Path(path) if path else active_profile_path()
    if not state_path.exists():
        return None
    data = tomllib.loads(state_path.read_text(encoding="utf-8"))
    profile = data.get("profile")
    if not isinstance(profile, str):
        return None
    return validate_profile_name(profile)


def load_active_models(path: str | os.PathLike[str] | None = None) -> dict[str, str]:
    state_path = Path(path) if path else active_models_path()
    if not state_path.exists():
        return {}
    data = tomllib.loads(state_path.read_text(encoding="utf-8"))
    models = data.get("models")
    if not isinstance(models, dict):
        return {}
    output: dict[str, str] = {}
    for profile_name, model_name in models.items():
        if isinstance(profile_name, str) and isinstance(model_name, str):
            output[validate_profile_name(profile_name)] = validate_model_name(model_name)
    return output


def load_active_model(profile_name: str, path: str | os.PathLike[str] | None = None) -> str | None:
    selected = validate_profile_name(profile_name)
    return load_active_models(path).get(selected)


def save_active_model(profile_name: str, model_name: str, path: str | os.PathLike[str] | None = None) -> Path:
    selected_profile = validate_profile_name(profile_name)
    selected_model = validate_model_name(model_name)
    state_path = Path(path) if path else active_models_path()
    models = load_active_models(state_path)
    models[selected_profile] = selected_model
    _write_active_models(state_path, models)
    return state_path


def clear_active_model(profile_name: str, path: str | os.PathLike[str] | None = None) -> bool:
    selected_profile = validate_profile_name(profile_name)
    state_path = Path(path) if path else active_models_path()
    models = load_active_models(state_path)
    removed = selected_profile in models
    models.pop(selected_profile, None)
    _write_active_models(state_path, models)
    return removed


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
        "# claude-code-proxy configuration",
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
                lines.append(f"{_toml_key(model_name)} = {_toml_string(profile.models[model_name])}")
        for model_name, value in sorted(profile.models.items()):
            if model_name not in {"big", "middle", "small"}:
                lines.append(f"{_toml_key(model_name)} = {_toml_string(value)}")
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


def _write_active_models(path: Path, models: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[models]"]
    for profile_name in sorted(models):
        lines.append(f"{_toml_string(profile_name)} = {_toml_string(models[profile_name])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_key(value: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if value and all(char in allowed for char in value):
        return value
    return _toml_string(value)
