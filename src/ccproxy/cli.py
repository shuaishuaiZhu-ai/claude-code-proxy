from __future__ import annotations

from dataclasses import replace
from typing import Sequence
import argparse
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

from . import __version__
from .client import UpstreamClient
from .config import (
    ServerConfig,
    active_profile_path,
    load_active_profile,
    load_config,
    save_active_profile,
    select_profile,
    write_default_config,
)
from .env import build_claude_env, ensure_bare_args
from .server import build_stdlib_server, serve_stdlib


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccproxy", description="Claude Code provider proxy.")
    parser.add_argument("--version", action="version", version=f"ccproxy {__version__}")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init", help="write a default config file")
    init_parser.add_argument("--profile", default="openai-key", help="default profile to select")
    init_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    init_parser.set_defaults(func=cmd_init)

    profiles_parser = subparsers.add_parser("profiles", help="list configured provider profiles")
    profiles_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    profiles_parser.set_defaults(func=cmd_profiles)

    current_parser = subparsers.add_parser("current", help="print active provider profile")
    current_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    current_parser.set_defaults(func=cmd_current)

    use_parser = subparsers.add_parser("use", help="set active provider profile")
    use_parser.add_argument("profile", help="profile name to activate")
    use_parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")
    use_parser.set_defaults(func=cmd_use)

    serve_parser = subparsers.add_parser("serve", help="serve the local Anthropic-compatible proxy")
    add_common_config_args(serve_parser)
    serve_parser.add_argument("--host")
    serve_parser.add_argument("--port", type=int)
    serve_parser.add_argument("--fastapi", action="store_true", help="serve through FastAPI/uvicorn if installed")
    serve_parser.set_defaults(func=cmd_serve)

    run_parser = subparsers.add_parser("run", help="serve proxy, then run Claude Code against it")
    add_common_config_args(run_parser)
    run_parser.add_argument("--host")
    run_parser.add_argument("--port", type=int)
    run_parser.add_argument("claude_args", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=cmd_run)

    doctor_parser = subparsers.add_parser("doctor", help="print environment diagnostics")
    add_common_config_args(doctor_parser)
    doctor_parser.set_defaults(func=cmd_doctor)

    test_parser = subparsers.add_parser("test", help="run a proxy smoke test")
    add_common_config_args(test_parser)
    test_parser.add_argument("--real", action="store_true", help="call the configured real provider")
    test_parser.set_defaults(func=cmd_test)

    return parser


def add_common_config_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", help="profile name")
    parser.add_argument("--config", help="config path; defaults to ~/.ccproxy/config.toml")


def cmd_profiles(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    active = load_active_profile(active_profile_path()) or config.default_profile
    for name in sorted(config.profiles):
        marker = "*" if name == active else " "
        profile = config.profiles[name]
        print(f"{marker} {name}\t{profile.type}\t{profile.api_key_env}\t{profile.base_url}")
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
    path = save_active_profile(profile.name, active_profile_path())
    print(f"active profile: {profile.name}")
    print(f"state: {path}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    path = write_default_config(args.config, args.profile)
    print(f"wrote {path}")
    print(f"default_profile = {args.profile}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = select_profile(config, _resolve_profile_name(args.profile))
    server = _server_from_args(config.server, args)
    if args.fastapi:
        return _serve_fastapi(server, profile)
    serve_stdlib(server, profile)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = select_profile(config, _resolve_profile_name(args.profile))
    server = _server_from_args(config.server, args)
    httpd = build_stdlib_server(server, profile)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        _wait_for_health(server)
        command = _claude_command(args.claude_args)
        env = build_claude_env(f"http://{server.host}:{server.port}", os.environ)
        print(f"running through {env['ANTHROPIC_BASE_URL']} with profile {profile.name}")
        return subprocess.call(command, env=env)
    finally:
        httpd.shutdown()
        httpd.server_close()


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = select_profile(config, _resolve_profile_name(args.profile))
    print(f"ccproxy: {__version__}")
    print(f"python: {sys.version.split()[0]}")
    print(f"platform: {platform.platform()}")
    print(f"profile: {profile.name} ({profile.type})")
    print(f"base_url: {profile.base_url}")
    print(f"api_key_env: {profile.api_key_env} ({'set' if os.environ.get(profile.api_key_env) else 'missing'})")
    print(f"claude: {_find_claude() or 'not found'}")
    for package in ("fastapi", "uvicorn"):
        print(f"{package}: {'installed' if importlib.util.find_spec(package) else 'missing'}")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    profile = select_profile(config, _resolve_profile_name(args.profile))
    if args.real:
        if profile.api_key_env and not os.environ.get(profile.api_key_env):
            print(f"missing {profile.api_key_env}; refusing real provider test")
            return 2
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


def _serve_fastapi(server: ServerConfig, profile: object) -> int:
    try:
        import uvicorn
        from .server import create_fastapi_app
    except ImportError:
        print("FastAPI/uvicorn is not installed. Run without --fastapi or install project dependencies.")
        return 2
    uvicorn.run(create_fastapi_app(profile), host=server.host, port=server.port)
    return 0


def _server_from_args(server: ServerConfig, args: argparse.Namespace) -> ServerConfig:
    return replace(
        server,
        host=args.host if getattr(args, "host", None) else server.host,
        port=args.port if getattr(args, "port", None) else server.port,
    )


def _resolve_profile_name(profile_name: str | None) -> str | None:
    if profile_name:
        return profile_name
    return load_active_profile(active_profile_path())


def _claude_command(raw_args: list[str]) -> list[str]:
    args = list(raw_args)
    if args and args[0] == "--":
        args = args[1:]
    if args:
        if platform.system().lower() == "windows" and args[0].lower() == "claude":
            claude = _find_claude()
            if claude:
                return ensure_bare_args([claude, *args[1:]])
        if _is_claude_executable(args[0]):
            return ensure_bare_args(args)
        return args
    claude = _find_claude()
    if not claude:
        raise RuntimeError("Claude Code CLI was not found on PATH")
    return ensure_bare_args([claude])


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
