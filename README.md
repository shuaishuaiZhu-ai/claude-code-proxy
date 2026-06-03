# claude-code-proxy

**Run Claude Code through the provider you already use.**

[English](README.md) · [简体中文](README.zh-CN.md)

![claude-code-proxy routes Claude Code through a local proxy to multiple provider types](docs/assets/readme-hero-generated.png)

`claude-code-proxy` (`ccproxy`) starts a local Anthropic-compatible proxy for
Claude Code. Pick a provider once, then run Claude Code through the same local
entry point whether your upstream is an OpenAI API key, a ChatGPT subscription,
DeepSeek, Kimi, Zhipu GLM, MiniMax, or your own OpenAI-compatible adapter.

The day-to-day workflow is intentionally small:

```sh
ccproxy model set
ccproxy run -- -p "reply ccproxy-ok"
```

Claude Code still runs locally. Its tools, plugins, skills, and MCP setup stay
available unless you deliberately pass Claude Code flags that disable them.

## 30-second quickstart

```sh
git clone https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
cd claude-code-proxy
sh scripts/install.sh
ccproxy model set
ccproxy run -- -p "reply ccproxy-ok"
```

Windows PowerShell:

```powershell
git clone https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
cd claude-code-proxy
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
ccproxy model set
ccproxy run -- -p "reply ccproxy-ok"
```

If the response contains `ccproxy-ok`, the proxy path is working. PyPI
publishing is not available yet, so installation is currently from a git clone.

## Choose one provider path

![Multiple provider types flow into one local ccproxy router](docs/assets/readme-provider-switching.png)

| What you already have | Choose this profile | Notes |
| --- | --- | --- |
| OpenAI API key | `openai-key` | Uses `OPENAI_API_KEY` or a pasted key saved by `ccproxy model set`. |
| ChatGPT subscription | `chatgpt-subscription` | Managed local adapter. Requires Node.js 20+ and git. |
| DeepSeek API key | `deepseek` | OpenAI-compatible endpoint. |
| Kimi / Moonshot API key | `kimi` | OpenAI-compatible endpoint. |
| Zhipu GLM API key | `zhipu` | OpenAI-compatible endpoint. |
| MiniMax API key | `minimax-cn` or `minimax-global` | Pick the region matching your account. |
| Your own local adapter | `custom` | Defaults to `http://127.0.0.1:8000/v1`. |

Useful commands:

```sh
ccproxy profiles
ccproxy profiles --all
ccproxy model set --provider deepseek --model deepseek-v4-pro
ccproxy model current
ccproxy model clear
```

For the complete provider list and setup URLs, see
[docs/providers.md](docs/providers.md).

## Install and uninstall

Requirements:

- Python 3.11+
- `pip`
- Claude Code CLI on `PATH`
- Node.js 20+ and git only if you use `chatgpt-subscription`

macOS, Linux, and WSL:

```sh
sh scripts/install.sh
sh scripts/install.sh --with-server
sh scripts/install.sh --no-init
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -WithServer
```

The install scripts run `pip install -e .` and initialize `~/.ccproxy` unless
you pass the no-init option.

Uninstall:

```sh
sh scripts/uninstall.sh
sh scripts/uninstall.sh --keep-state
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

Uninstalling ccproxy does not remove Python, pip, Node.js, git, or Claude Code.

## Run Claude Code through ccproxy

Everything after `--` is passed to Claude Code:

```sh
ccproxy run -- -p "summarize this repository"
ccproxy run -- --model sonnet -p "reply ccproxy-ok"
ccproxy run --profile kimi --upstream-model moonshot-v1-128k -- -p "explain this file"
```

`ccproxy run` starts a local proxy, sets `ANTHROPIC_BASE_URL` for the child
Claude Code process, waits for Claude Code to exit, then shuts the proxy down.

Default proxy port: `8082`.

```sh
ccproxy run --port 8090 -- -p "reply ccproxy-ok"
```

You can also serve only the proxy:

```sh
ccproxy serve --profile custom --port 8090
```

## Local security boundary

![API keys and subscription tokens stay inside the local machine boundary while ccproxy routes requests outward](docs/assets/readme-local-security.png)

ccproxy is designed as a local sidecar:

- The proxy listens on `127.0.0.1` by default.
- API keys can come from environment variables such as `OPENAI_API_KEY`.
- Pasted keys are saved under `~/.ccproxy/secrets.toml`.
- `ccproxy doctor` reports whether keys are present, but does not print key values.
- ChatGPT subscription mode uses your browser login through a managed local adapter; it does not turn a ChatGPT subscription into an OpenAI Platform API key.

For the full boundary, see [SECURITY.md](SECURITY.md).

## Troubleshooting

Start with diagnostics:

```sh
ccproxy doctor
ccproxy doctor --profile chatgpt-subscription
```

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Claude Code says `Not logged in` | You ran plain `claude`, not `ccproxy run`. | Run `ccproxy run -- ...` so `ANTHROPIC_BASE_URL` is set. |
| `/skills` appears empty | Claude Code was launched with `--bare`. | Remove `--bare` for normal use. |
| API key setup exits immediately | Empty key was pasted. | Run `ccproxy model set` again and paste the actual key. |
| Browser consent page hangs | Browser callback flow is blocked. | Use the default device-code login; do not pass `--browser-login`. |
| Adapter unreachable | A local subscription adapter is not running. | Run `ccproxy model set`, start the adapter, or switch to an API-key profile. |
| Port conflict | The proxy or callback port is already in use. | Pass `--port` for the proxy, or close the process using the callback port. |
| PowerShell blocks scripts | Local execution policy. | Use `-ExecutionPolicy Bypass` for the install/uninstall script. |

Try ccproxy without a real provider:

```sh
python scripts/mock_openai_provider.py --port 8000
ccproxy model set --provider custom --model custom-big
ccproxy run -- -p "reply ccproxy-ok"
```

## How it works

Claude Code speaks the Anthropic Messages API. Most non-Anthropic providers
speak OpenAI Chat Completions or expose a local adapter. ccproxy translates
requests and responses between those shapes, including streaming and tool-call
payloads.

For implementation details, read:

- [docs/architecture.md](docs/architecture.md)
- [wiki/Architecture.md](wiki/Architecture.md)
- [wiki/Providers-And-Models.md](wiki/Providers-And-Models.md)
- [wiki/Testing.md](wiki/Testing.md)

## Contributing

The core code is small and has no required runtime dependencies beyond the
standard library. FastAPI and uvicorn are optional extras for server mode.

Common entry points:

| Goal | Start here |
| --- | --- |
| Add a built-in provider | `src/ccproxy/presets.py`, `src/ccproxy/provider_setup.py`, `tests/test_provider_setup.py` |
| Fix request/response translation | `src/ccproxy/translator.py`, `tests/test_translator.py` |
| Improve ChatGPT subscription adapter behavior | `src/ccproxy/adapter.py`, `tests/test_adapter.py` |
| Improve CLI behavior | `src/ccproxy/cli.py`, `tests/test_cli.py` |

Before opening a PR:

```sh
python -m pip install -e .
python -m unittest discover -s tests
python -m compileall -q src tests scripts
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and
[docs/architecture-review.md](docs/architecture-review.md) for the current
technical-debt map.

## Roadmap

- Publish to PyPI.
- Add CI coverage for Windows, macOS, and Linux.
- Pin the managed `auth2api` adapter to a tagged release or commit.
- Add structured logging with debug and quiet modes.
- Add `ccproxy doctor --fix`.
- Add optional keyring-backed secret storage.

## License

MIT. See [LICENSE](LICENSE).
