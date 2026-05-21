# claude-code-proxy

[English](README.md) | [简体中文](README.zh-CN.md)

Claude Code provider switching, wrapped in one local command: `ccproxy`.

![claude-code-proxy overview](docs/assets/readme-hero.svg)

`claude-code-proxy` lets Claude Code talk to OpenAI-compatible,
Anthropic-compatible, and local adapter backends without hand-editing Claude
Code environment variables every time you switch models.

## Why This Exists

- **One command to switch providers:** `ccproxy model set`.
- **Two OpenAI paths:** OpenAI API key billing and ChatGPT subscription login are
  separate modes.
- **Works on Windows, macOS, WSL, and Linux:** Windows uses `claude.cmd` instead
  of the PowerShell `.ps1` shim.
- **Secrets stay outside the repository:** API keys are read from environment
  variables. ChatGPT subscription tokens live under `~/.ccproxy`.

## Quick Start

Pick the path that matches how you pay for the model.

### ChatGPT Subscription

Use this when you want Claude Code to use a ChatGPT subscription account instead
of an OpenAI API key.

```sh
python -m pip install git+https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
ccproxy model set --provider chatgpt-subscription --model ChatGPT5.5
ccproxy run -- -p "reply ccproxy-ok"
```

The first command run starts a device-code login. Open the printed URL, enter
the one-time code, and return to the terminal. This default flow avoids the
older `localhost:1455` browser callback that can hang in Edge, Chrome, WSL, or
multi-window setups.

### OpenAI API Key

Use this when you have an OpenAI API key and want normal API billing.

```sh
export OPENAI_API_KEY="your-openai-api-key"
python -m pip install git+https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
ccproxy model set --provider openai-key --model gpt-4.1
ccproxy run -- -p "reply ccproxy-ok"
```

PowerShell:

```powershell
$env:OPENAI_API_KEY="your-openai-api-key"
ccproxy model set --provider openai-key --model gpt-4.1
ccproxy run -- -p "reply ccproxy-ok"
```

### Kimi, Zhipu GLM, or MiniMax

```sh
export KIMI_API_KEY="your-kimi-key"
ccproxy model set --provider kimi --model moonshot-v1-128k
ccproxy run -- -p "reply ccproxy-ok"
```

Replace `KIMI_API_KEY` and the provider name with `ZHIPU_API_KEY` / `zhipu` or
`MINIMAX_API_KEY` / `minimax-cn`.

## Provider Map

![provider modes](docs/assets/readme-provider-map.svg)

| What you have | Provider | Model examples | Secret source |
| --- | --- | --- | --- |
| OpenAI API key | `openai-key` | `gpt-4.1`, `gpt-4.1-mini` | `OPENAI_API_KEY` |
| ChatGPT subscription | `chatgpt-subscription` | `ChatGPT5.5`, `ChatGPT5.4` | managed device-code login |
| Kimi / Moonshot API key | `kimi` | `moonshot-v1-128k` | `KIMI_API_KEY` |
| Zhipu GLM API key | `zhipu` | `glm-4-plus` | `ZHIPU_API_KEY` |
| MiniMax CN API key | `minimax-cn` | `MiniMax-M2.7` | `MINIMAX_API_KEY` |
| MiniMax Global API key | `minimax-global` | `MiniMax-M2.7` | `MINIMAX_API_KEY` |
| MiniMax Anthropic-compatible | `minimax-cn-anthropic`, `minimax-global-anthropic` | provider native | `MINIMAX_API_KEY` |
| Your own adapter | `custom` | whatever it exposes | `CCPROXY_CUSTOM_API_KEY` or local policy |

## How It Works

Claude Code speaks the Anthropic Messages API. `ccproxy` starts a local
Anthropic-compatible endpoint, translates or forwards the request, and then runs
Claude Code with a clean child-process environment:

```text
ANTHROPIC_BASE_URL=http://127.0.0.1:8082
ANTHROPIC_API_KEY=ccproxy
ANTHROPIC_AUTH_TOKEN=ccproxy
```

That keeps any real Anthropic credentials in your shell from leaking into a
proxy run.

## ChatGPT Subscription Login

![ChatGPT subscription login flow](docs/assets/readme-login-flow.svg)

The default `chatgpt-subscription` flow uses OpenAI Codex device-code login:

```sh
ccproxy model set --provider chatgpt-subscription --model ChatGPT5.5
```

You will see:

```text
Open this URL in your browser and enter the one-time code:
https://auth.openai.com/codex/device
Code: ABCD-1234
```

Open the URL, enter the code, and wait for the terminal to continue. No
`localhost:1455` callback is used.

If you explicitly need the older browser callback flow, opt in:

```sh
ccproxy model set --provider chatgpt-subscription --model ChatGPT5.5 --browser-login
```

Use `--browser-login` only when you specifically want to test or debug the old
Codex consent-page flow.

## Commands You Will Actually Use

```sh
ccproxy init
ccproxy model set
ccproxy model current
ccproxy run -- -p "reply ccproxy-ok"
ccproxy doctor --profile chatgpt-subscription
ccproxy test --profile custom --claude
```

`ccproxy model set` is the main switchboard. It selects a provider, prepares the
provider if needed, asks for a model, and saves the active provider/model under
`~/.ccproxy`.

State files:

- `~/.ccproxy/active.toml`: active provider profile
- `~/.ccproxy/models.toml`: active upstream model per provider
- `~/.ccproxy/adapters/auth2api/auth/`: managed ChatGPT subscription tokens

API keys are not written to those state files.

## Install From Source

```sh
git clone https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
cd claude-code-proxy
python -m pip install -e .
ccproxy --version
```

If `ccproxy` is not on `PATH`, use:

```sh
python -m ccproxy model set
```

## Platform Notes

| Platform | Recommendation |
| --- | --- |
| Windows PowerShell | Use normal `ccproxy` commands. `ccproxy run` prefers `claude.cmd` to avoid `.ps1` execution-policy failures. |
| Windows CMD | Use `set OPENAI_API_KEY=...` for API-key modes. |
| macOS / Linux | Use `export OPENAI_API_KEY=...` or the provider-specific key variable. |
| WSL | Keep Claude Code, `ccproxy`, and local adapters in the same environment when possible. |
| Remote/headless | Prefer ChatGPT device-code login or `--no-open-login` for API-key setup pages. |

## Troubleshooting

Run this first:

```sh
ccproxy doctor --profile chatgpt-subscription
```

Common findings:

| Symptom | Meaning | Fix |
| --- | --- | --- |
| Claude Code says `Not logged in` | You ran `claude` directly, not through `ccproxy run`. | Use `ccproxy run -- -p "reply ccproxy-ok"`. |
| Browser spins on Codex consent page | You are using the old browser callback flow. | Stop it and rerun without `--browser-login`. |
| `codex_callback_port_1455: busy` | Another app owns the old callback port. | Device-code login ignores this. It only matters with `--browser-login`. |
| API-key provider refuses to save | The required env var is missing. | Set `OPENAI_API_KEY`, `KIMI_API_KEY`, `ZHIPU_API_KEY`, or `MINIMAX_API_KEY`. |
| Local custom adapter unreachable | `custom` is user-managed. | Start your adapter and verify its `base_url`. |

## Configuration

Create or refresh the user config:

```sh
ccproxy init
```

Minimal profile example:

```toml
default_profile = "openai-key"

[server]
host = "127.0.0.1"
port = 8082

[profiles.openai-key]
type = "openai-compatible"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"

[profiles.openai-key.models]
big = "gpt-4.1"
middle = "gpt-4.1-mini"
small = "gpt-4.1-nano"
```

Profile types:

- `openai-compatible`: translate Anthropic Messages to OpenAI Chat Completions.
- `anthropic-compatible`: forward Anthropic Messages with auth and model
  mapping.
- `external-adapter`: OpenAI-compatible wire shape. `chatgpt-subscription` is
  managed by `ccproxy`; `custom` is user-managed.

See [docs/providers.md](docs/providers.md) and
[examples/ccproxy.example.toml](examples/ccproxy.example.toml).

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src tests scripts
```

Optional FastAPI mode:

```sh
python -m pip install ".[server]"
ccproxy serve --fastapi
```

## License

MIT. See [LICENSE](LICENSE).

Third-party names, platform marks, and documentation imagery belong to their
respective owners. This project is independent and is not affiliated with
OpenAI, Anthropic, MiniMax, Moonshot AI, Zhipu AI, Microsoft, Apple, or Linux
distributors.
