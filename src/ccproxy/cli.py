from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Sequence
import argparse
import importlib.util
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from urllib.parse import urlparse

from . import __version__
from .adapter import (
    CODEX_CALLBACK_PORT,
    ManagedAdapterError,
    chatgpt_adapter_status,
    chatgpt_auth_endpoint_statuses,
    codex_callback_port_busy,
    ensure_chatgpt_adapter,
)
from .client import UpstreamClient
from .config import (
    ProviderProfile,
    ProxyConfig,
    ServerConfig,
    active_models_path,
    active_profile_path,
    clear_active_model,
    default_config_path,
    load_active_model,
    load_active_profile,
    load_config,
    save_active_model,
    save_active_profile,
    select_profile,
    validate_model_name,
    write_default_config,
)
from .env import build_claude_env
from .provider_setup import provider_key_missing, provider_setup_message, setup_for_profile
from .server import build_stdlib_server, serve_stdlib
from .secrets import get_api_key, save_api_key
from .translator import select_model


INTERACTIVE_PROFILE_EXCLUDES = {
    "minimax-cn-anthropic",
    "minimax-global-anthropic",
    "openai",
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccproxy", description="Claude Code provider proxy.")
    parser.add_argument("--version", action="version", version=f"ccproxy {__version__}")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init", help="write a default config file")
    init_parser.add_argument("--profile", help="provider profile name; prompts when omitted")
    init_parser.add_argument("--model", help="upstream model name; prompts when omitted")
    init_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    init_parser.add_argument("--manual-login", action="store_true", help="print login URL and ask for redirected URL")
    init_parser.add_argument("--browser-login", action="store_true", help="use browser callback login instead of device-code login")
    init_parser.add_argument("--no-adapter-start", action="store_true", help="do not install/login/start managed adapters")
    init_parser.add_argument("--no-open-login", action="store_true", help="do not open a browser during subscription login")
    init_parser.add_argument("--skip-model-set", action="store_true", help="only write config; do not choose provider/model")
    init_parser.set_defaults(func=cmd_init)

    profiles_parser = subparsers.add_parser("profiles", help="list configured provider profiles")
    profiles_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    profiles_parser.add_argument("--all", action="store_true", help="include advanced/internal provider profiles")
    profiles_parser.set_defaults(func=cmd_profiles)

    current_parser = subparsers.add_parser("current", help="print active provider profile")
    current_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    current_parser.set_defaults(func=cmd_current)

    use_parser = subparsers.add_parser("use", help="set active provider profile")
    use_parser.add_argument("profile", help="profile name to activate")
    use_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    use_parser.add_argument("--manual-login", action="store_true", help="print adapter login URL and ask for redirected URL")
    use_parser.add_argument("--browser-login", action="store_true", help="use browser callback login instead of device-code login")
    use_parser.add_argument("--no-adapter-start", action="store_true", help="do not install/login/start managed adapters")
    use_parser.add_argument("--no-open-login", action="store_true", help="do not open a browser during subscription login")
    use_parser.set_defaults(func=cmd_use)

    model_parser = subparsers.add_parser("model", help="choose provider and upstream model")
    model_subparsers = model_parser.add_subparsers(required=True)

    model_set_parser = model_subparsers.add_parser("set", help="interactively set provider and upstream model")
    model_set_parser.add_argument("--provider", "--profile", dest="profile", help="provider profile name")
    model_set_parser.add_argument("--model", help="upstream model name")
    model_set_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    model_set_parser.add_argument("--manual-login", action="store_true", help="print login URL and ask for redirected URL")
    model_set_parser.add_argument("--browser-login", action="store_true", help="use browser callback login instead of device-code login")
    model_set_parser.add_argument("--no-adapter-start", action="store_true", help="do not install/login/start managed adapters")
    model_set_parser.add_argument("--no-open-login", action="store_true", help="do not open a browser during subscription login")
    model_set_parser.set_defaults(func=cmd_model_set)

    model_current_parser = model_subparsers.add_parser("current", help="print active provider and upstream model")
    model_current_parser.add_argument("--provider", "--profile", dest="profile", help="provider profile name")
    model_current_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    model_current_parser.set_defaults(func=cmd_model_current)

    model_clear_parser = model_subparsers.add_parser("clear", help="clear active upstream model for a provider")
    model_clear_parser.add_argument("--provider", "--profile", dest="profile", help="provider profile name")
    model_clear_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    model_clear_parser.set_defaults(func=cmd_model_clear)

    serve_parser = subparsers.add_parser("serve", help="serve the local Anthropic-compatible proxy")
    add_common_config_args(serve_parser)
    serve_parser.add_argument("--upstream-model", help="temporary upstream model override")
    serve_parser.add_argument("--host")
    serve_parser.add_argument("--port", type=int)
    serve_parser.add_argument("--manual-login", action="store_true", help="print adapter login URL and ask for redirected URL")
    serve_parser.add_argument("--browser-login", action="store_true", help="use browser callback login instead of device-code login")
    serve_parser.add_argument("--no-adapter-start", action="store_true", help="do not install/login/start managed adapters")
    serve_parser.add_argument("--no-open-login", action="store_true", help="do not open a browser during subscription login")
    serve_parser.add_argument("--fastapi", action="store_true", help="serve through FastAPI/uvicorn if installed")
    serve_parser.set_defaults(func=cmd_serve)

    run_parser = subparsers.add_parser("run", help="serve proxy, then run Claude Code against it")
    add_common_config_args(run_parser)
    run_parser.add_argument("--upstream-model", help="temporary upstream model override")
    run_parser.add_argument("--host")
    run_parser.add_argument("--port", type=int)
    run_parser.add_argument("--manual-login", action="store_true", help="print adapter login URL and ask for redirected URL")
    run_parser.add_argument("--browser-login", action="store_true", help="use browser callback login instead of device-code login")
    run_parser.add_argument("--no-adapter-start", action="store_true", help="do not install/login/start managed adapters")
    run_parser.add_argument("--no-open-login", action="store_true", help="do not open a browser during subscription login")
    run_parser.add_argument("claude_args", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=cmd_run)

    doctor_parser = subparsers.add_parser("doctor", help="print environment diagnostics")
    add_common_config_args(doctor_parser)
    doctor_parser.add_argument("--upstream-model", help="temporary upstream model override")
    doctor_parser.set_defaults(func=cmd_doctor)

    test_parser = subparsers.add_parser("test", help="run a proxy smoke test")
    add_common_config_args(test_parser)
    test_parser.add_argument("--upstream-model", help="temporary upstream model override")
    test_parser.add_argument("--host")
    test_parser.add_argument("--port", type=int)
    test_parser.add_argument("--manual-login", action="store_true", help="print adapter login URL and ask for redirected URL")
    test_parser.add_argument("--browser-login", action="store_true", help="use browser callback login instead of device-code login")
    test_parser.add_argument("--no-adapter-start", action="store_true", help="do not install/login/start managed adapters")
    test_parser.add_argument("--no-open-login", action="store_true", help="do not open a browser during subscription login")
    test_parser.add_argument("--real", action="store_true", help="call the configured real provider")
    test_parser.add_argument("--claude", action="store_true", help="run a real Claude Code CLI smoke test")
    test_parser.add_argument("--prompt", default="reply ccproxy-ok", help="prompt for --claude smoke test")
    test_parser.set_defaults(func=cmd_test)

    return parser


def add_common_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", help="profile name")
    parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")


def cmd_profiles(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    active = load_active_profile(active_profile_path()) or config.default_profile
    names = sorted(config.profiles) if getattr(args, "all", False) else _interactive_profile_names(config)
    for name in names:
        marker = "*" if name == active else " "
        profile = config.profiles[name]
        key_env = _profile_key_label(profile)
        print(f"{marker} {name}\t{profile.type}\t{key_env}\t{profile.base_url}")
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    active = load_active_profile(active_profile_path()) or config.default_profile
    profile = select_profile(config, active)
    print(f"{profile.name}\t{profile.type}\t{profile.base_url}")
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = select_profile(config, args.profile)
    ready = _ensure_provider_ready(profile, args)
    if ready != 0:
        return ready
    path = save_active_profile(profile.name, active_profile_path())
    print(f"active profile: {profile.name}")
    print(f"state: {path}")
    return 0


def cmd_model_set(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = _select_profile_for_model_set(config, args.profile)
    ready = _ensure_provider_ready(profile, args)
    if ready != 0:
        return ready
    model = validate_model_name(args.model) if args.model else _select_model_for_profile(profile)
    profile_path = save_active_profile(profile.name, active_profile_path())
    model_path = save_active_model(profile.name, model, active_models_path())
    print(f"active provider: {profile.name}")
    print(f"active model: {model}")
    print(f"profile state: {profile_path}")
    print(f"model state: {model_path}")
    return 0


def cmd_model_current(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = select_profile(config, _resolve_profile_name(args.profile))
    active_model = load_active_model(profile.name, active_models_path())
    effective = select_model(None, profile.with_upstream_model(active_model))
    source = "active" if active_model else "default"
    print(f"provider: {profile.name}")
    if active_model and active_model != effective:
        print(f"model: {active_model} -> {effective} ({source})")
    else:
        print(f"model: {effective} ({source})")
    return 0


def cmd_model_clear(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = select_profile(config, _resolve_profile_name(args.profile))
    removed = clear_active_model(profile.name, active_models_path())
    print(f"provider: {profile.name}")
    print("model cleared" if removed else "no active model was set")
    return 0


def _select_profile_for_model_set(config: ProxyConfig, profile_name: str | None) -> ProviderProfile:
    if profile_name:
        return select_profile(config, profile_name)

    active = load_active_profile(active_profile_path()) or config.default_profile
    names = _interactive_profile_names(config)
    print("Choose provider:")
    for index, name in enumerate(names, 1):
        profile = config.profiles[name]
        marker = "*" if name == active else " "
        print(f"{index}. {marker} {name} ({profile.type})")

    while True:
        choice = input("Provider number or name: ").strip()
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(names):
                return select_profile(config, names[index - 1])
        if choice in config.profiles:
            return select_profile(config, choice)
        print("Unknown provider. Choose a listed number or name.")


def _interactive_profile_names(config: ProxyConfig) -> list[str]:
    visible = [name for name in config.profiles if name not in INTERACTIVE_PROFILE_EXCLUDES]
    return sorted(visible)


def _select_model_for_profile(profile: ProviderProfile) -> str:
    choices = _ordered_model_choices(profile)
    print(f"Choose model for {profile.name}:")
    if choices:
        for index, (alias, model) in enumerate(choices, 1):
            print(f"{index}. {alias}: {model}")
    print("Or type any custom upstream model name, for example ChatGPT5.5.")

    while True:
        choice = input("Model number, alias, or custom model name: ").strip()
        if choice.isdigit() and choices:
            index = int(choice)
            if 1 <= index <= len(choices):
                return validate_model_name(choices[index - 1][1])
        for alias, model in choices:
            if choice == alias or choice.lower() == alias.lower():
                return validate_model_name(choice)
        try:
            return validate_model_name(choice)
        except ValueError:
            print("Model name cannot be empty or contain control characters.")


def _ordered_model_choices(profile: ProviderProfile) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    for alias in ("big", "middle", "small"):
        if alias in profile.models:
            choices.append((alias, profile.models[alias]))
    for alias in sorted(profile.models):
        if alias not in {"big", "middle", "small"}:
            choices.append((alias, profile.models[alias]))
    return choices


def _ensure_provider_ready(profile: ProviderProfile, args: argparse.Namespace) -> int:
    managed = _ensure_managed_adapter_if_needed(profile, args)
    if managed != 0:
        return managed
    if not provider_key_missing(profile):
        return 0
    print(provider_setup_message(profile), file=sys.stderr)
    pasted = prompt_api_key(profile)
    if not pasted:
        return 2
    path = save_api_key(profile.api_key_env, pasted)
    print(f"saved API key for {profile.name}: {path}", file=sys.stderr)
    return 0


def prompt_api_key(profile: ProviderProfile) -> str:
    setup = setup_for_profile(profile)
    if setup:
        print(f"Get your API key: {setup.url}", file=sys.stderr)
    print(f"Paste {profile.api_key_env} for {profile.name}, then press Enter.", file=sys.stderr)
    return input("API key: ").strip()


def _ensure_managed_adapter_if_needed(profile: ProviderProfile, args: argparse.Namespace) -> int:
    if getattr(args, "no_adapter_start", False):
        return 0
    if profile.name != "chatgpt-subscription":
        return 0
    try:
        ensure_chatgpt_adapter(
            manual_login=getattr(args, "manual_login", False),
            browser_login=getattr(args, "browser_login", False),
            open_browser=not getattr(args, "no_open_login", False),
        )
    except ManagedAdapterError as exc:
        print(f"failed to prepare ChatGPT subscription adapter: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    if args.skip_model_set:
        default_profile = args.profile or "openai-key"
        path = write_default_config(args.config, default_profile)
        print(f"wrote {path}")
        print(f"default_profile = {default_profile}")
        return 0

    config = load_config(args.config)
    profile = _select_profile_for_model_set(config, args.profile)
    path = _ensure_config_file(args.config, profile.name)
    print(f"config: {path}")
    ready = _ensure_provider_ready(profile, args)
    if ready != 0:
        return ready
    model = validate_model_name(args.model) if args.model else _select_model_for_profile(profile)
    profile_path = save_active_profile(profile.name, active_profile_path())
    model_path = save_active_model(profile.name, model, active_models_path())
    print(f"active provider: {profile.name}")
    print(f"active model: {model}")
    print(f"profile state: {profile_path}")
    print(f"model state: {model_path}")
    print("ready: run ccproxy run -- -p \"reply ccproxy-ok\"")
    return 0


def _ensure_config_file(config_path: str | None, default_profile: str) -> Path:
    path = default_config_path() if config_path is None else Path(config_path)
    if path.exists():
        return path
    return write_default_config(config_path, default_profile)


def cmd_serve(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = _resolve_profile(config, args)
    ready = _ensure_provider_ready(profile, args)
    if ready != 0:
        return ready
    server = _server_from_args(config.server, args)
    if args.fastapi:
        return _serve_fastapi(server, profile)
    serve_stdlib(server, profile)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = _resolve_profile(config, args)
    ready = _ensure_provider_ready(profile, args)
    if ready != 0:
        return ready
    server = _server_from_args(config.server, args)
    return _run_claude_through_proxy(server, profile, args.claude_args)


def _run_claude_through_proxy(
    server: ServerConfig,
    profile: ProviderProfile,
    claude_args: list[str],
    expected_text: str | None = None,
) -> int:
    preflight_error = _local_upstream_error(profile)
    if preflight_error:
        print(preflight_error, file=sys.stderr)
        return 2

    httpd = build_stdlib_server(server, profile)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        _wait_for_health(server)
        command = _claude_command(claude_args)
        env = build_claude_env(f"http://{server.host}:{server.port}", os.environ)
        print(f"running through {env['ANTHROPIC_BASE_URL']} with profile {profile.name}", flush=True)
        if expected_text is None:
            return subprocess.call(command, env=env)
        completed = subprocess.run(command, env=env, capture_output=True, text=True)
        output = completed.stdout + completed.stderr
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        if completed.returncode != 0:
            return completed.returncode
        if expected_text not in output:
            print(f"expected {expected_text!r} in Claude Code output")
            return 1
        return 0
    finally:
        httpd.shutdown()
        httpd.server_close()


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = _resolve_profile(config, args)
    print(f"ccproxy: {__version__}")
    print(f"python: {sys.version.split()[0]}")
    print(f"platform: {platform.platform()}")
    print(f"profile: {profile.name} ({profile.type})")
    print(f"base_url: {profile.base_url}")
    print(f"upstream_model: {select_model(None, profile)}")
    if profile.api_key_env:
        if os.environ.get(profile.api_key_env):
            key_state = "set"
        elif get_api_key(profile.api_key_env):
            key_state = "saved"
        else:
            key_state = "missing"
        print(f"api_key_env: {profile.api_key_env} ({key_state})")
        if provider_key_missing(profile):
            setup = setup_for_profile(profile)
            if setup:
                print(f"provider_setup_url: {setup.url}")
    else:
        print(f"api_key_env: {_profile_key_label(profile)}")
    print(f"claude: {_find_claude() or 'not found'}")
    if profile.name == "chatgpt-subscription":
        status = chatgpt_adapter_status()
        print("managed_adapter: auth2api")
        print(f"managed_adapter_url: {status.url}")
        print(f"managed_adapter_installed: {'yes' if status.installed else 'no'}")
        print(f"managed_adapter_logged_in: {'yes' if status.logged_in else 'no'}")
        print(f"managed_adapter_running: {'yes' if status.running else 'no'}")
        print(f"managed_adapter_repo: {status.repo}")
        print(f"managed_adapter_log: {status.log}")
        print(f"codex_callback_port_{CODEX_CALLBACK_PORT}: {'busy' if codex_callback_port_busy() else 'free'}")
        auth_statuses = chatgpt_auth_endpoint_statuses()
        for endpoint in auth_statuses:
            status_text = f"HTTP {endpoint.status}" if endpoint.status is not None else "no_http_response"
            print(f"chatgpt_auth_https: {endpoint.url} {status_text} {endpoint.issue}")
        if any(endpoint.issue == "cloudflare_challenge" for endpoint in auth_statuses):
            print("chatgpt_auth_hint: browser consent flow is being challenged; rerun without --browser-login to use default device-code login.")
    for package in ("fastapi", "uvicorn"):
        print(f"{package}: {'installed' if importlib.util.find_spec(package) else 'missing'}")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = _resolve_profile(config, args)
    if args.claude:
        ready = _ensure_provider_ready(profile, args)
        if ready != 0:
            return ready
        server = _server_from_args(config.server, args)
        claude_args = ["claude", "--bare", "--model", "sonnet", "-p", args.prompt]
        return _run_claude_through_proxy(server, profile, claude_args, expected_text="ccproxy-ok")
    if args.real:
        ready = _ensure_provider_ready(profile, args)
        if ready != 0:
            return ready
        client = UpstreamClient(profile, timeout=30)
        result = client.messages(
            {
                "model": "claude-3-5-sonnet-latest",
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "Reply with ccproxy-ok only."}],
            }
        )
        print(result.payload if hasattr(result, "payload") else "stream result")
        return 0 if getattr(result, "status", 500) < 400 else 1

    from .translator import anthropic_to_openai, openai_to_anthropic

    openai_payload = anthropic_to_openai(
        {
            "model": "claude-3-5-sonnet-latest",
            "max_tokens": 32,
            "system": "Be terse.",
            "messages": [{"role": "user", "content": "ping"}],
            "tools": [{"name": "echo", "description": "Echo input.", "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}}}],
        },
        profile,
    )
    anthropic_payload = openai_to_anthropic(
        {
            "id": "chatcmpl_test",
            "model": openai_payload["model"],
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "ccproxy-ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
        requested_model="claude-3-5-sonnet-latest",
    )
    if anthropic_payload["content"][0]["text"] != "ccproxy-ok":
        print("local translator smoke test failed")
        return 1
    print(f"local translator smoke test ok for {profile.name}: {openai_payload['model']}")
    return 0


def _serve_fastapi(server: ServerConfig, profile: ProviderProfile) -> int:
    try:
        import uvicorn
        from .server import create_fastapi_app
    except ImportError:
        print("FastAPI/uvicorn is not installed. Run without --fastapi or install project dependencies.")
        return 2
    uvicorn.run(create_fastapi_app(profile), host=server.host, port=server.port)
    return 0


def _local_upstream_error(profile: ProviderProfile) -> str | None:
    parsed = urlparse(profile.base_url)
    if parsed.scheme not in {"http", "https"}:
        return None
    host = parsed.hostname
    if host not in {"127.0.0.1", "localhost", "::1"}:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=1):
            return None
    except OSError as exc:
        if profile.name == "chatgpt-subscription":
            hint = "Run ccproxy init or ccproxy model set to install/login/start the managed ChatGPT adapter."
        elif profile.name.endswith("-subscription"):
            hint = "Start the local subscription adapter for this provider, or switch to its API-key provider."
        else:
            hint = "For a local fake adapter test from this repository, run: python scripts\\mock_openai_provider.py --port 8000"
        return (
            f"upstream adapter is not reachable: {profile.base_url}\n"
            f"provider: {profile.name}\n"
            f"reason: {exc}\n"
            f"{hint}"
        )


def _server_from_args(server: ServerConfig, args: argparse.Namespace) -> ServerConfig:
    return replace(
        server,
        host=args.host if getattr(args, "host", None) else server.host,
        port=args.port if getattr(args, "port", None) else server.port,
    )


def _resolve_profile(config: ProxyConfig, args: argparse.Namespace) -> ProviderProfile:
    profile = select_profile(config, _resolve_profile_name(args.profile))
    model = getattr(args, "upstream_model", None) or load_active_model(profile.name, active_models_path())
    if model:
        return profile.with_upstream_model(model)
    return profile


def _resolve_profile_name(profile_name: str | None) -> str | None:
    if profile_name:
        return profile_name
    return load_active_profile(active_profile_path())


def _profile_key_label(profile: ProviderProfile) -> str:
    if profile.api_key_env:
        return profile.api_key_env
    if profile.name == "chatgpt-subscription":
        return "managed"
    return "local-adapter"


def _claude_command(raw_args: list[str]) -> list[str]:
    args = list(raw_args)
    if args and args[0] == "--":
        args = args[1:]
    if args and args[0].startswith("-"):
        claude = _find_claude()
        if not claude:
            raise RuntimeError("Claude Code CLI was not found on PATH")
        return [claude, *args]
    if args:
        if platform.system().lower() == "windows" and args[0].lower() == "claude":
            claude = _find_claude()
            if claude:
                return [claude, *args[1:]]
        if _is_claude_executable(args[0]):
            return args
        return args
    claude = _find_claude()
    if not claude:
        raise RuntimeError("Claude Code CLI was not found on PATH")
    return [claude]


def _is_claude_executable(command: str) -> bool:
    name = command.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name in {"claude", "claude.cmd"}


def _find_claude() -> str | None:
    if platform.system().lower() == "windows":
        return shutil.which("claude.cmd") or shutil.which("claude")
    return shutil.which("claude")


def _wait_for_health(server: ServerConfig) -> None:
    url = f"http://{server.host}:{server.port}/health"
    deadline = time.time() + 5
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # pragma: no cover - diagnostic path
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"ccproxy did not start at {url}: {last_error}")
