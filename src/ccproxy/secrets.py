from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
import json
import os
import tomllib

from .config import CONFIG_DIR


SECRETS_FILE = "secrets.toml"


def secrets_path() -> Path:
    return Path.home() / CONFIG_DIR / SECRETS_FILE


def get_api_key(
    env_name: str,
    environ: Mapping[str, str] | None = None,
    path: str | os.PathLike[str] | None = None,
    include_saved: bool = True,
) -> str:
    name = _validate_secret_name(env_name)
    env_value = (environ or os.environ).get(name, "").strip()
    if env_value:
        return env_value
    if not include_saved:
        return ""
    return load_api_keys(path).get(name, "")


def save_api_key(env_name: str, api_key: str, path: str | os.PathLike[str] | None = None) -> Path:
    name = _validate_secret_name(env_name)
    cleaned = api_key.strip()
    if not cleaned:
        raise ValueError("API key cannot be empty")
    state_path = Path(path) if path else secrets_path()
    keys = load_api_keys(state_path)
    keys[name] = cleaned
    _write_api_keys(state_path, keys)
    return state_path


def load_api_keys(path: str | os.PathLike[str] | None = None) -> dict[str, str]:
    state_path = Path(path) if path else secrets_path()
    if not state_path.exists():
        return {}
    data = tomllib.loads(state_path.read_text(encoding="utf-8"))
    api_keys = data.get("api_keys")
    if not isinstance(api_keys, dict):
        return {}
    return {
        _validate_secret_name(name): value.strip()
        for name, value in api_keys.items()
        if isinstance(name, str) and isinstance(value, str) and value.strip()
    }


def _write_api_keys(path: Path, keys: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[api_keys]"]
    for name in sorted(keys):
        lines.append(f"{json.dumps(name)} = {json.dumps(keys[name])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _validate_secret_name(env_name: str) -> str:
    cleaned = env_name.strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
    if not cleaned or any(char not in allowed for char in cleaned):
        raise ValueError(f"invalid secret name {env_name!r}")
    return cleaned
