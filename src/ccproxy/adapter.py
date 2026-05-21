from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request


AUTH2API_REPO = "https://github.com/AmazingAng/auth2api.git"
AUTH2API_PORT = 8317
AUTH2API_API_KEY = "ccproxy-local"
CODEX_CALLBACK_PORT = 1455
CHATGPT_AUTH_ENDPOINTS = (
    "https://auth.openai.com/sign-in-with-chatgpt/codex/consent",
    "https://auth.openai.com/oauth/authorize",
    "https://chatgpt.com",
)


class ManagedAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterPaths:
    root: Path
    repo: Path
    auth_dir: Path
    config: Path
    log: Path


@dataclass(frozen=True)
class AdapterStatus:
    installed: bool
    logged_in: bool
    running: bool
    url: str
    repo: Path
    log: Path


@dataclass(frozen=True)
class EndpointStatus:
    url: str
    status: int | None
    issue: str


def default_adapter_paths() -> AdapterPaths:
    root = Path.home() / ".ccproxy" / "adapters" / "auth2api"
    return AdapterPaths(
        root=root,
        repo=root / "repo",
        auth_dir=root / "auth",
        config=root / "repo" / "config.yaml",
        log=root / "auth2api.log",
    )


def ensure_chatgpt_adapter(manual_login: bool = False, auto_install: bool = True) -> None:
    paths = default_adapter_paths()
    _ensure_node()
    if not _auth2api_installed(paths):
        if not auto_install:
            raise ManagedAdapterError("auth2api is not installed. Run ccproxy init or allow adapter installation.")
        _install_auth2api(paths)
    _write_auth2api_config(paths)
    if not _has_codex_token(paths):
        _login_auth2api(paths, manual=manual_login)
    if not is_auth2api_running():
        _start_auth2api(paths)
    if not wait_for_auth2api():
        raise ManagedAdapterError(f"auth2api did not become reachable at http://127.0.0.1:{AUTH2API_PORT}")


def chatgpt_adapter_status() -> AdapterStatus:
    paths = default_adapter_paths()
    return AdapterStatus(
        installed=_auth2api_installed(paths),
        logged_in=_has_codex_token(paths),
        running=is_auth2api_running(),
        url=f"http://127.0.0.1:{AUTH2API_PORT}",
        repo=paths.repo,
        log=paths.log,
    )


def codex_callback_port_busy() -> bool:
    return _is_port_in_use("127.0.0.1", CODEX_CALLBACK_PORT)


def chatgpt_auth_endpoint_statuses(timeout: int = 5) -> list[EndpointStatus]:
    return [_check_https_endpoint(url, timeout=timeout) for url in CHATGPT_AUTH_ENDPOINTS]


def is_auth2api_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", AUTH2API_PORT), timeout=1):
            return True
    except OSError:
        return False


def wait_for_auth2api(timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_auth2api_running():
            return True
        time.sleep(0.25)
    return False


def _auth2api_installed(paths: AdapterPaths) -> bool:
    return (paths.repo / "dist" / "index.js").exists()


def _install_auth2api(paths: AdapterPaths) -> None:
    git = shutil.which("git")
    npm = _npm_command()
    if not git:
        raise ManagedAdapterError("git was not found on PATH. Install Git, then rerun ccproxy init.")
    if not npm:
        raise ManagedAdapterError("npm was not found on PATH. Install Node.js 20+, then rerun ccproxy init.")

    paths.root.mkdir(parents=True, exist_ok=True)
    if not paths.repo.exists():
        print(f"installing auth2api into {paths.repo}")
        _run_checked([git, "clone", AUTH2API_REPO, str(paths.repo)], cwd=None, action="clone auth2api")

    print("installing auth2api npm dependencies")
    _run_checked([npm, "install"], cwd=paths.repo, action="install auth2api npm dependencies")
    print("building auth2api")
    _run_checked([npm, "run", "build"], cwd=paths.repo, action="build auth2api")


def _write_auth2api_config(paths: AdapterPaths) -> None:
    paths.auth_dir.mkdir(parents=True, exist_ok=True)
    config = f"""host: "127.0.0.1"
port: {AUTH2API_PORT}
auth-dir: "{_yaml_path(paths.auth_dir)}"
api-keys:
  - "{AUTH2API_API_KEY}"
debug: "errors"
"""
    paths.config.write_text(config, encoding="utf-8")


def _login_auth2api(paths: AdapterPaths, manual: bool = False) -> None:
    node = _node_command()
    callback_port_busy = codex_callback_port_busy()
    use_manual = manual or callback_port_busy
    command = [node, "dist/index.js", "--login", "--provider=codex"]
    if use_manual:
        command.append("--manual")
    print("starting ChatGPT subscription login via auth2api")
    if callback_port_busy and not manual:
        print(
            f"OAuth callback port 127.0.0.1:{CODEX_CALLBACK_PORT} is already in use; "
            "falling back to manual callback mode."
        )
    print("A browser login URL may open. Finish login, then return to this terminal.")
    print("If the consent page stays disabled before redirecting to localhost, run: ccproxy doctor --profile chatgpt-subscription")
    _run_checked(command, cwd=paths.repo, action="ChatGPT subscription login")


def _start_auth2api(paths: AdapterPaths) -> None:
    node = _node_command()
    paths.root.mkdir(parents=True, exist_ok=True)
    command = [node, "dist/index.js"]
    print(f"starting auth2api on http://127.0.0.1:{AUTH2API_PORT}")
    print(f"auth2api log: {paths.log}")
    with paths.log.open("a", encoding="utf-8") as log:
        try:
            if platform.system().lower() == "windows":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                subprocess.Popen(
                    command,
                    cwd=paths.repo,
                    stdout=log,
                    stderr=log,
                    stdin=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
            else:
                subprocess.Popen(
                    command,
                    cwd=paths.repo,
                    stdout=log,
                    stderr=log,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except OSError as exc:
            raise ManagedAdapterError(f"failed to start auth2api: {exc}") from exc


def _run_checked(command: list[str], cwd: Path | None, action: str) -> None:
    try:
        if cwd is None:
            subprocess.check_call(command)
        else:
            subprocess.check_call(command, cwd=cwd)
    except subprocess.CalledProcessError as exc:
        raise ManagedAdapterError(f"{action} failed with exit code {exc.returncode}") from exc
    except OSError as exc:
        raise ManagedAdapterError(f"{action} failed: {exc}") from exc


def _check_https_endpoint(url: str, timeout: int) -> EndpointStatus:
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "ccproxy/doctor"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return EndpointStatus(url, response.status, _endpoint_issue(response.status, response.headers))
    except urllib.error.HTTPError as exc:
        return EndpointStatus(url, exc.code, _endpoint_issue(exc.code, exc.headers))
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        reason = getattr(exc, "reason", exc)
        return EndpointStatus(url, None, f"network_error: {reason}")


def _endpoint_issue(status: int, headers: object) -> str:
    get = getattr(headers, "get", None)
    mitigated = get("Cf-Mitigated", "") if get else ""
    if str(mitigated).lower() == "challenge":
        return "cloudflare_challenge"
    if 200 <= status < 400:
        return "ok"
    return f"http_{status}"


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError:
            return True
    return False


def _has_codex_token(paths: AdapterPaths) -> bool:
    return paths.auth_dir.exists() and any(paths.auth_dir.glob("codex-*.json"))


def _ensure_node() -> None:
    node = _node_command()
    try:
        completed = subprocess.run([node, "--version"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ManagedAdapterError("Node.js 20+ is required for ChatGPT subscription adapter support.") from exc
    version = completed.stdout.strip().lstrip("v")
    major = int(version.split(".", 1)[0]) if version and version[0].isdigit() else 0
    if major < 20:
        raise ManagedAdapterError(f"Node.js 20+ is required; found {completed.stdout.strip()}")


def _node_command() -> str:
    node = shutil.which("node")
    if not node:
        raise ManagedAdapterError("node was not found on PATH. Install Node.js 20+, then rerun ccproxy init.")
    return node


def _npm_command() -> str | None:
    if platform.system().lower() == "windows":
        return shutil.which("npm.cmd") or shutil.which("npm")
    return shutil.which("npm")


def _yaml_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\")
