# Provider Switching And Subscription Proxy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize the existing `claude-code-proxy` / `ccproxy` project so Claude Code CLI can use OpenAI API, ChatGPT subscription adapters, Kimi, Zhipu GLM, and MiniMax, with one-command provider switching on Windows/macOS/WSL/Linux.

**Architecture:** Keep `ccproxy` as the protocol proxy and make provider selection a first-class state machine. Add a small active-profile state file under the user's `.ccproxy` directory, expose `ccproxy profiles/current/use` commands, and provide shell wrappers that call those commands without duplicating provider logic. Subscription accounts remain external-adapter based: the core never logs into websites, reads cookies, or stores secrets.

**Tech Stack:** Python 3.11+ standard library (`argparse`, `tomllib`, `http.server`, `urllib`), existing `ccproxy` modules, PowerShell + `.cmd` wrappers for Windows, POSIX shell scripts for macOS/WSL/Linux, `unittest` for tests, GitHub README Markdown and generated PNG README hero.

---

## File Structure

- Modify: `src/ccproxy/config.py`
  - Add active-profile state paths.
  - Add helper functions to write/read active profile state without storing secrets.
  - Preserve current config loading behavior.
- Modify: `src/ccproxy/cli.py`
  - Add `profiles`, `current`, and `use` commands.
  - Allow `run`, `serve`, `doctor`, and `test` to use the active profile when `--profile` is omitted.
  - Keep `--profile` override for one-off runs.
- Create: `src/ccproxy/env.py`
  - Centralize Claude Code environment variables (`ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`) and cross-platform Claude command handling.
- Modify: `scripts/run_chatgpt_subscription.ps1`
  - Replace one-off ChatGPT-only local config with active-profile aware logic.
  - Keep `--bare` default.
- Create: `scripts/ccproxy-switch.cmd`
  - Windows shortcut: `scripts\ccproxy-switch.cmd openai-key`.
- Create: `scripts/ccproxy-current.cmd`
  - Windows shortcut: show active provider.
- Create: `scripts/ccproxy-run.cmd`
  - Windows shortcut: run Claude Code through the active provider.
- Create: `scripts/ccproxy-smoke.cmd`
  - Windows shortcut: smoke test active provider.
- Create: `scripts/ccproxy-switch.sh`
  - macOS/WSL/Linux shortcut: `scripts/ccproxy-switch.sh openai-key`.
- Create: `scripts/ccproxy-run.sh`
  - macOS/WSL/Linux shortcut: run Claude Code through the active provider.
- Modify: `README.md`
  - Rewrite quick start around three commands: install, switch, run.
  - Include provider switching table and platform-specific examples.
  - Keep the current generated hero image.
- Modify: `docs/providers.md`
  - Document profile names, env vars, subscription adapter boundary, and switch commands.
- Create: `tests/test_active_profile.py`
  - Unit tests for active-profile read/write and config default fallback.
- Modify: `tests/test_cli.py`
  - Tests for new CLI commands and active profile behavior.
- Modify: `tests/test_cli_windows.py`
  - Tests for Windows command resolution and `--bare` behavior.

---

### Task 1: Active Profile State

**Files:**
- Modify: `src/ccproxy/config.py`
- Test: `tests/test_active_profile.py`

- [ ] **Step 1: Write failing tests for active profile state**

Create `tests/test_active_profile.py`:

```python
import tempfile
import unittest
from pathlib import Path

from ccproxy.config import (
    active_profile_path,
    load_active_profile,
    save_active_profile,
)


class ActiveProfileTests(unittest.TestCase):
    def test_save_and_load_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active.toml"
            save_active_profile("kimi", path)
            self.assertEqual(load_active_profile(path), "kimi")

    def test_missing_active_profile_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active.toml"
            self.assertIsNone(load_active_profile(path))

    def test_rejects_unknown_profile_name_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "active.toml"
            with self.assertRaises(ValueError):
                save_active_profile("../secret", path)

    def test_default_active_profile_path_lives_under_ccproxy_dir(self) -> None:
        path = active_profile_path()
        self.assertEqual(path.name, "active.toml")
        self.assertEqual(path.parent.name, ".ccproxy")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_active_profile -v
```

Expected: FAIL with import errors for `active_profile_path`, `load_active_profile`, and `save_active_profile`.

- [ ] **Step 3: Implement active profile helpers**

Add to `src/ccproxy/config.py` after `default_config_path()`:

```python
ACTIVE_PROFILE_FILE = "active.toml"


def active_profile_path() -> Path:
    return Path.home() / CONFIG_DIR / ACTIVE_PROFILE_FILE


def validate_profile_name(profile_name: str) -> str:
    cleaned = profile_name.strip()
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if not cleaned or any(char not in allowed for char in cleaned):
        raise ValueError(f"invalid profile name {profile_name!r}")
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_active_profile -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ccproxy/config.py tests/test_active_profile.py
git commit -m "Add active provider profile state"
```

---

### Task 2: Active Profile CLI Commands

**Files:**
- Modify: `src/ccproxy/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Append to `tests/test_cli.py`:

```python
import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ccproxy.cli import main


class ProfileCommandTests(unittest.TestCase):
    def test_profiles_lists_known_profiles(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["profiles"]), 0)
        text = out.getvalue()
        self.assertIn("openai-key", text)
        self.assertIn("chatgpt-subscription", text)
        self.assertIn("kimi", text)
        self.assertIn("zhipu", text)

    def test_use_sets_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "active.toml"
            with patch("ccproxy.cli.active_profile_path", return_value=state_path):
                self.assertEqual(main(["use", "kimi"]), 0)
                self.assertIn('profile = "kimi"', state_path.read_text(encoding="utf-8"))

    def test_current_uses_active_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "active.toml"
            state_path.write_text('profile = "zhipu"\n', encoding="utf-8")
            out = io.StringIO()
            with patch("ccproxy.cli.active_profile_path", return_value=state_path):
                with redirect_stdout(out):
                    self.assertEqual(main(["current"]), 0)
            self.assertIn("zhipu", out.getvalue())
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_cli -v
```

Expected: FAIL because `profiles`, `use`, and `current` commands do not exist.

- [ ] **Step 3: Add imports**

Modify the import from `ccproxy.config` in `src/ccproxy/cli.py`:

```python
from .config import (
    ServerConfig,
    active_profile_path,
    load_active_profile,
    load_config,
    save_active_profile,
    select_profile,
    write_default_config,
)
```

- [ ] **Step 4: Add parser commands**

Add these parser definitions inside `build_parser()` after `init_parser`:

```python
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
```

- [ ] **Step 5: Add command handlers**

Add these functions before `cmd_init()`:

```python
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
```

- [ ] **Step 6: Make common commands use active profile**

Add helper:

```python
def _resolve_profile_name(config: object, profile_name: str | None) -> str | None:
    if profile_name:
        return profile_name
    return load_active_profile(active_profile_path())
```

Then change `cmd_serve`, `cmd_run`, `cmd_doctor`, and `cmd_test` from:

```python
profile = select_profile(config, args.profile)
```

to:

```python
profile = select_profile(config, _resolve_profile_name(config, args.profile))
```

- [ ] **Step 7: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_cli tests.test_active_profile -v
```

Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add src/ccproxy/cli.py tests/test_cli.py
git commit -m "Add provider profile switching commands"
```

---

### Task 3: Centralize Claude Environment And Bare Mode

**Files:**
- Create: `src/ccproxy/env.py`
- Modify: `src/ccproxy/cli.py`
- Modify: `tests/test_cli_windows.py`

- [ ] **Step 1: Write failing tests for env helper**

Add to `tests/test_cli_windows.py`:

```python
from ccproxy.env import build_claude_env, ensure_bare_args


class ClaudeEnvironmentTests(unittest.TestCase):
    def test_build_claude_env_sets_required_auth_vars(self) -> None:
        env = build_claude_env("http://127.0.0.1:8082", {"PATH": "x"})
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "http://127.0.0.1:8082")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "ccproxy")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "ccproxy")

    def test_ensure_bare_args_inserts_after_claude(self) -> None:
        self.assertEqual(
            ensure_bare_args(["claude", "--model", "sonnet"]),
            ["claude", "--bare", "--model", "sonnet"],
        )

    def test_ensure_bare_args_does_not_duplicate(self) -> None:
        self.assertEqual(
            ensure_bare_args(["claude", "--bare", "--model", "sonnet"]),
            ["claude", "--bare", "--model", "sonnet"],
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_cli_windows -v
```

Expected: FAIL because `ccproxy.env` does not exist.

- [ ] **Step 3: Create env helper**

Create `src/ccproxy/env.py`:

```python
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
```

- [ ] **Step 4: Use env helper in CLI**

Modify `src/ccproxy/cli.py` imports:

```python
from .env import build_claude_env
```

Change the environment creation in `cmd_run` to:

```python
        env = build_claude_env(f"http://{server.host}:{server.port}", os.environ)
```

Keep the existing print statement:

```python
        print(f"running through {env['ANTHROPIC_BASE_URL']} with profile {profile.name}")
```

- [ ] **Step 5: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_cli_windows -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ccproxy/env.py src/ccproxy/cli.py tests/test_cli_windows.py
git commit -m "Centralize Claude Code proxy environment"
```

---

### Task 4: Cross-Platform Switch And Run Scripts

**Files:**
- Create: `scripts/ccproxy-switch.cmd`
- Create: `scripts/ccproxy-current.cmd`
- Create: `scripts/ccproxy-run.cmd`
- Create: `scripts/ccproxy-smoke.cmd`
- Create: `scripts/ccproxy-switch.sh`
- Create: `scripts/ccproxy-current.sh`
- Create: `scripts/ccproxy-run.sh`
- Create: `scripts/ccproxy-smoke.sh`
- Modify: `scripts/run_chatgpt_subscription.ps1`
- Test: manual command verification

- [ ] **Step 1: Create Windows switch script**

Create `scripts/ccproxy-switch.cmd`:

```bat
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
if "%~1"=="" (
  echo Usage: scripts\ccproxy-switch.cmd PROFILE
  echo Example: scripts\ccproxy-switch.cmd openai-key
  exit /b 2
)
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
python -m ccproxy use %*
exit /b %ERRORLEVEL%
```

- [ ] **Step 2: Create Windows current script**

Create `scripts/ccproxy-current.cmd`:

```bat
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
python -m ccproxy current %*
exit /b %ERRORLEVEL%
```

- [ ] **Step 3: Create Windows run script**

Create `scripts/ccproxy-run.cmd`:

```bat
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
if "%~1"=="" (
  python -m ccproxy run -- claude --bare --model sonnet
) else (
  python -m ccproxy run -- claude --bare %*
)
exit /b %ERRORLEVEL%
```

- [ ] **Step 4: Create Windows smoke script**

Create `scripts/ccproxy-smoke.cmd`:

```bat
@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "PYTHONPATH=%REPO_ROOT%\src;%PYTHONPATH%"
python -m ccproxy run -- claude --bare --model sonnet -p "reply ccproxy-ok"
exit /b %ERRORLEVEL%
```

- [ ] **Step 5: Create POSIX switch script**

Create `scripts/ccproxy-switch.sh`:

```sh
#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
if [ "$#" -lt 1 ]; then
  echo "Usage: scripts/ccproxy-switch.sh PROFILE" >&2
  echo "Example: scripts/ccproxy-switch.sh openai-key" >&2
  exit 2
fi
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m ccproxy use "$@"
```

- [ ] **Step 6: Create POSIX current script**

Create `scripts/ccproxy-current.sh`:

```sh
#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m ccproxy current "$@"
```

- [ ] **Step 7: Create POSIX run script**

Create `scripts/ccproxy-run.sh`:

```sh
#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
if [ "$#" -eq 0 ]; then
  set -- --model sonnet
fi
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m ccproxy run -- claude --bare "$@"
```

- [ ] **Step 8: Create POSIX smoke script**

Create `scripts/ccproxy-smoke.sh`:

```sh
#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}" python -m ccproxy run -- claude --bare --model sonnet -p "reply ccproxy-ok"
```

- [ ] **Step 9: Simplify ChatGPT-specific script to use active profile**

Keep `scripts/run_chatgpt_subscription.ps1` for backward compatibility, but update its help text to recommend the generic commands:

```powershell
Write-Step "tip: generic switching is available via scripts\ccproxy-switch.cmd chatgpt-subscription"
```

Add this line after the proxy line:

```powershell
Write-Step "tip: use scripts\ccproxy-run.cmd after switching providers"
```

- [ ] **Step 10: Verify Windows scripts**

Run:

```powershell
cmd.exe /d /s /c scripts\ccproxy-switch.cmd chatgpt-subscription
cmd.exe /d /s /c scripts\ccproxy-current.cmd
cmd.exe /d /s /c scripts\ccproxy-switch.cmd openai-key
cmd.exe /d /s /c scripts\ccproxy-current.cmd
```

Expected:
- First current output includes `chatgpt-subscription`.
- Second current output includes `openai-key`.

- [ ] **Step 11: Verify POSIX shell syntax from Windows if Git Bash exists**

Run:

```powershell
bash -n scripts/ccproxy-switch.sh
bash -n scripts/ccproxy-current.sh
bash -n scripts/ccproxy-run.sh
bash -n scripts/ccproxy-smoke.sh
```

Expected: no output and exit code 0. If `bash` is not installed, record this as "not verified on this Windows host".

- [ ] **Step 12: Commit**

```bash
git add scripts/ccproxy-switch.cmd scripts/ccproxy-current.cmd scripts/ccproxy-run.cmd scripts/ccproxy-smoke.cmd scripts/ccproxy-switch.sh scripts/ccproxy-current.sh scripts/ccproxy-run.sh scripts/ccproxy-smoke.sh scripts/run_chatgpt_subscription.ps1
git commit -m "Add cross-platform provider switching scripts"
```

---

### Task 5: Provider Profiles And Subscription Switching UX

**Files:**
- Modify: `src/ccproxy/presets.py`
- Modify: `examples/ccproxy.example.toml`
- Modify: `docs/providers.md`
- Modify: `.env.example`
- Test: `tests/test_config.py`

- [ ] **Step 1: Extend config tests for all required providers**

Add to `tests/test_config.py`:

```python
    def test_required_provider_profiles_exist(self) -> None:
        required = {
            "openai-key": "OPENAI_API_KEY",
            "chatgpt-subscription": "CHATGPT_ADAPTER_API_KEY",
            "kimi": "KIMI_API_KEY",
            "zhipu": "ZHIPU_API_KEY",
            "minimax-cn": "MINIMAX_API_KEY",
            "minimax-global": "MINIMAX_API_KEY",
        }
        for name, env_name in required.items():
            with self.subTest(name=name):
                self.assertIn(name, PRESETS)
                self.assertEqual(PRESETS[name].api_key_env, env_name)
```

- [ ] **Step 2: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_config -v
```

Expected: PASS if profiles already exist; FAIL if any required profile is missing.

- [ ] **Step 3: Add subscription adapter variants only if needed**

If the test fails because a provider subscription profile is missing, add profiles following this exact pattern in `src/ccproxy/presets.py`:

```python
    "kimi-subscription": ProviderProfile(
        name="kimi-subscription",
        type="external-adapter",
        base_url="http://127.0.0.1:8010/v1",
        api_key_env="KIMI_ADAPTER_API_KEY",
        models={"big": "kimi-big", "middle": "kimi-middle", "small": "kimi-small"},
    ),
```

Do not add web-login code. Only add external-adapter presets.

- [ ] **Step 4: Update `.env.example`**

Ensure `.env.example` contains:

```text
OPENAI_API_KEY=
CHATGPT_ADAPTER_API_KEY=
KIMI_API_KEY=
ZHIPU_API_KEY=
MINIMAX_API_KEY=
CCPROXY_CUSTOM_API_KEY=
```

- [ ] **Step 5: Update `examples/ccproxy.example.toml`**

Make sure it includes examples for:

```toml
[profiles.openai-key]
[profiles.chatgpt-subscription]
[profiles.kimi]
[profiles.zhipu]
[profiles.minimax-cn]
[profiles.custom]
```

- [ ] **Step 6: Update `docs/providers.md`**

Add a "Switching" section:

````markdown
## Switching

Windows:

```cmd
scripts\ccproxy-switch.cmd openai-key
scripts\ccproxy-run.cmd
scripts\ccproxy-switch.cmd chatgpt-subscription
scripts\ccproxy-run.cmd
```

macOS / WSL / Linux:

```sh
scripts/ccproxy-switch.sh openai-key
scripts/ccproxy-run.sh
scripts/ccproxy-switch.sh chatgpt-subscription
scripts/ccproxy-run.sh
```
````

- [ ] **Step 7: Run tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_config -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/ccproxy/presets.py tests/test_config.py examples/ccproxy.example.toml docs/providers.md .env.example
git commit -m "Document provider switching profiles"
```

---

### Task 6: README Rewrite And Generated Visual

**Files:**
- Modify: `README.md`
- Keep or replace: `docs/assets/claude-code-proxy-hero.png`
- Optional create: `docs/assets/provider-switching.png`

- [ ] **Step 1: Keep current hero unless image quality is poor**

Use the existing first generated hero image unless the README render shows it broken:

```markdown
![claude-code-proxy hero](docs/assets/claude-code-proxy-hero.png)
```

If a new image is needed, generate a README diagram image with this prompt:

```text
Use case: productivity-visual
Asset type: GitHub README architecture banner
Primary request: A clean technical illustration showing Claude Code CLI connected to a local proxy, with quick switching between provider profiles: OpenAI API, ChatGPT adapter, Kimi, and GLM. Include cross-platform visual cues for Windows, macOS, WSL, and Linux. Professional open-source tooling style.
Style/medium: polished 3D technical illustration
Composition/framing: wide landscape 1536x864, left-to-right flow
Text: no readable text, no logos, no watermarks
Constraints: no clutter, clear routing concept, balanced blue/green/teal palette
```

- [ ] **Step 2: Rewrite README quick start**

Update `README.md` top-level quick start to this exact structure:

````markdown
## 30-second Windows start

```cmd
cd /d C:\path\to\claude-code-proxy
scripts\ccproxy-switch.cmd openai-key
scripts\ccproxy-current.cmd
scripts\ccproxy-run.cmd
```

## Switch providers

```cmd
scripts\ccproxy-switch.cmd openai-key
scripts\ccproxy-switch.cmd chatgpt-subscription
scripts\ccproxy-switch.cmd kimi
scripts\ccproxy-switch.cmd zhipu
scripts\ccproxy-switch.cmd minimax-cn
```

## macOS / WSL / Linux

```sh
scripts/ccproxy-switch.sh openai-key
scripts/ccproxy-run.sh
```
````

- [ ] **Step 3: Add subscription boundary block**

Add this exact block:

````markdown
## Subscription account boundary

`chatgpt-subscription` means "route Claude Code to a local adapter that you run".
It does not mean this project logs into ChatGPT, reads browser cookies, or
turns a ChatGPT Plus/Pro/Team plan into an OpenAI API key.
````

- [ ] **Step 4: Add Windows verification block**

Add:

````markdown
## Verified on Windows

The project is verified with Claude Code CLI on Windows using:

```cmd
cmd.exe /d /s /c claude --version
scripts\ccproxy-smoke.cmd
```
````

- [ ] **Step 5: Run Markdown sanity checks**

Run:

```powershell
Select-String -Path README.md -Pattern "ccproxy-switch|chatgpt-subscription|openai-key|kimi|zhipu|minimax-cn"
```

Expected: each pattern appears at least once.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/assets
git commit -m "Rewrite README for provider switching"
```

---

### Task 7: End-To-End Verification On Windows

**Files:**
- No code files unless failures require fixes.

- [ ] **Step 1: Verify Claude Code version**

Run:

```powershell
cmd.exe /d /s /c claude --version
```

Expected: exits 0 and prints a Claude Code version, currently known on this machine as `2.1.144 (Claude Code)`.

- [ ] **Step 2: Verify Python package metadata**

Run:

```powershell
python -m pip install -e . --no-deps --dry-run --no-build-isolation
```

Expected: includes `Would install claude-code-proxy-0.1.0`.

- [ ] **Step 3: Run unit tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests
```

Expected: all tests PASS.

- [ ] **Step 4: Run compile check**

Run:

```powershell
$env:PYTHONPATH='src'
python -m compileall -q src tests scripts
```

Expected: exit code 0.

- [ ] **Step 5: Verify switching commands**

Run:

```powershell
cmd.exe /d /s /c scripts\ccproxy-switch.cmd openai-key
cmd.exe /d /s /c scripts\ccproxy-current.cmd
cmd.exe /d /s /c scripts\ccproxy-switch.cmd chatgpt-subscription
cmd.exe /d /s /c scripts\ccproxy-current.cmd
```

Expected: current profile changes from `openai-key` to `chatgpt-subscription`.

- [ ] **Step 6: Verify mock adapter smoke path**

Open terminal 1:

```powershell
cmd.exe /d /s /c scripts\mock-adapter.cmd
```

Open terminal 2:

```powershell
cmd.exe /d /s /c scripts\ccproxy-switch.cmd custom
cmd.exe /d /s /c scripts\ccproxy-smoke.cmd
```

Expected: output contains `ccproxy-ok` and does not show Claude Code login-method selection.

- [ ] **Step 7: Clean generated caches**

Run:

```powershell
$root = (Resolve-Path .).Path
$dirs = Get-ChildItem -Path $root -Recurse -Directory -Filter __pycache__
foreach ($dir in $dirs) {
    if (-not $dir.FullName.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove outside workspace: $($dir.FullName)"
    }
    Remove-Item -LiteralPath $dir.FullName -Recurse -Force
}
```

Expected: no `__pycache__` directories remain.

- [ ] **Step 8: Push**

Run:

```bash
git status --short
git push
```

Expected: working tree clean and GitHub `main` updated.

---

## Self-Review

**Spec coverage:**
- Requirement 1, provider proxy support: Task 5 verifies OpenAI API, ChatGPT adapter, Kimi, Zhipu GLM, MiniMax profiles.
- Requirement 2, Windows/macOS/WSL/Linux: Task 4 adds `.cmd` and `.sh` scripts; Task 7 verifies Windows and shell syntax where available.
- Requirement 3, README and images: Task 6 rewrites README and preserves or regenerates README hero image.
- Requirement 4, Windows Claude Code verification: Task 7 includes Claude Code version and mock smoke verification.
- Requirement 5, multiple subscription switching via cmd: Task 2 adds active profile state; Task 4 adds `ccproxy-switch.cmd`, `ccproxy-run.cmd`, and smoke/current wrappers.
- Requirement 6, optimize local ccproxy: All tasks modify the existing codebase without replacing the proxy core.

**Placeholder scan:** No red-flag placeholder phrases remain. Every code-changing task includes exact files, commands, and expected outcomes.

**Type consistency:** Function names are consistent across tasks: `active_profile_path`, `load_active_profile`, `save_active_profile`, `build_claude_env`, and `ensure_bare_args`.
