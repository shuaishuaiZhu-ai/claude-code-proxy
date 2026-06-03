# claude-code-proxy

**Use Claude Code with your existing AI provider.**

<!-- Maintain links for both languages -->
[English](README.md) · [简体中文](README.zh-CN.md)

<!-- Hero image with alt text explaining the concept -->
![An abstract diagram showing a local machine connecting to various AI providers through a central proxy hub](docs/assets/readme-hero-new.png)

Claude Code speaks the Anthropic Messages API. Many AI providers—like OpenAI, DeepSeek, Kimi, Zhipu and MiniMax—speak the OpenAI Chat Completions API, and a ChatGPT subscription only works through a browser. `claude-code-proxy` (`ccproxy`) runs a local sidecar that translates between them so you can continue using Claude Code without changing your workflow. You keep your API keys and tokens on your machine; ccproxy routes the requests through the provider you choose.

### Why ccproxy?

Use ccproxy when you already have an AI account or key and want to take advantage of Claude Code without reconfiguring your environment. ccproxy lets you:

* Pick a provider once and continue using Claude Code’s tools and plugins as usual.
* Keep API keys and subscription tokens local — ccproxy never uploads them.
* Translate between Anthropic and OpenAI request formats seamlessly.
* Support multiple providers and switch between them with a single command.

## Quick start in 30 seconds

PyPI publishing is not yet available. To install from source and test the connection:

```sh
git clone https://github.com/shuaishuaiZhu-ai/claude-code-proxy.git
cd claude-code-proxy
sh scripts/install.sh        # for macOS, Linux or WSL
ccproxy model set            # choose your provider and paste a key when prompted
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

If you see `ccproxy-ok` in the output, the proxy path is working. The install scripts accept flags such as `--with-server` and `--no-init`; see `scripts/install.sh` and `scripts/install.ps1` for details.

## Choose your provider

Pick a profile based on the account or API key you already have. To see all available profiles run `ccproxy profiles` or `ccproxy profiles --all`.

| What you already have | Profile name | Notes |
| --- | --- | --- |
| OpenAI API key | `openai-key` | Uses the `OPENAI_API_KEY` environment variable or a pasted key saved by `ccproxy model set`. |
| ChatGPT subscription | `chatgpt-subscription` | Managed local adapter. Requires Node.js 20+ and git. The subscription token stays local in your browser session. |
| DeepSeek (Moonshot) API key | `deepseek` | OpenAI‑compatible endpoint. |
| Kimi API key | `kimi` | OpenAI‑compatible endpoint. |
| Zhipu GLM API key | `zhipu` | OpenAI‑compatible endpoint. |
| MiniMax API key | `minimax-cn` or `minimax-global` | Pick the region matching your account. |
| Self‑hosted adapter | `custom` | Defaults to `http://127.0.0.1:8000/v1`; change with `--base-url`. |

Examples:

```sh
ccproxy model set --provider openai-key --model gpt-4-turbo
ccproxy model current        # show the active provider and model
ccproxy model clear          # remove the saved key or subscription
ccproxy run --profile kimi --upstream-model moonshot-v1-128k -- -p "explain this file"
```

For a complete list of providers and model names see [docs/providers.md](docs/providers.md).

## Everyday usage

Once a profile is configured, run Claude Code through ccproxy:

```sh
ccproxy run -- -p "summarize this repository"
ccproxy run -- --model sonnet -p "reply ccproxy-ok"    # specify the Anthropic model for Claude Code
ccproxy serve --profile custom --port 8090              # expose only the proxy and call from another process
```

`ccproxy run` launches a local proxy on port 8082 (configurable), sets `ANTHROPIC_BASE_URL` for the child Claude Code process, waits for Claude Code to exit and then shuts down the proxy.

### ChatGPT subscription

The `chatgpt-subscription` profile uses a managed adapter that logs in through your browser or device code. It does **not** convert your ChatGPT subscription into an OpenAI Platform API key. You need Node.js 20+, git and a browser. Running `ccproxy model set --provider chatgpt-subscription` will guide you through the login process. The token stays on your machine and is never printed or uploaded.

## Local security boundary

![A diagram showing that API keys and subscription tokens remain within the local machine while requests are sent to the provider](docs/assets/local-security-diagram-new.png)

ccproxy is designed as a local sidecar. The proxy listens on `127.0.0.1` by default. API keys can come from environment variables or be pasted into the setup prompt and are stored in `~/.ccproxy/secrets.toml`. `ccproxy doctor` tells you whether keys are present but never prints their values. When using a ChatGPT subscription the managed adapter keeps your login token in your browser profile. For more information see [SECURITY.md](SECURITY.md).

## Troubleshooting

Start with diagnostics:

```sh
ccproxy doctor
ccproxy doctor --profile chatgpt-subscription
```

Common symptoms and fixes:

| Symptom | Likely cause | How to fix |
| --- | --- | --- |
| Claude Code prints `Not logged in` | You ran `claude` directly and `ANTHROPIC_BASE_URL` was not set. | Use `ccproxy run -- …` so the environment is configured. |
| `/skills` appears empty | Claude Code was started with `--bare`, disabling tools. | Remove the `--bare` flag for normal use. |
| Key setup exits immediately | You pressed enter without pasting a key. | Run `ccproxy model set` again and paste the actual key. |
| Browser consent page hangs | The browser callback is blocked or popped up in the wrong tab. | Use the default device‑code login; avoid using `--browser-login` unless you know it works. |
| Adapter unreachable | The local subscription adapter is not running. | Run `ccproxy model set`, start the adapter, or switch to an API-key profile. |
| Port conflict | Another service is using the proxy or callback port. | Pass `--port` to choose a different port or close the conflicting process. |
| PowerShell blocks scripts | Execution policy is too restrictive. | Use `-ExecutionPolicy Bypass` when running the install/uninstall scripts. |

You can experiment without a real provider by using a mock:

```sh
python scripts/mock_openai_provider.py --port 8000
ccproxy model set --provider custom --model custom-big
ccproxy run -- -p "reply ccproxy-ok"
```

## Learn more

ccproxy is small by design. It translates between Anthropic Messages and OpenAI Chat Completions (including streaming and tool calls) and launches managed adapters for providers that require them.

- **Architecture**: [docs/architecture.md](docs/architecture.md) describes the system context, module boundaries, request translation pipeline, provider profile model, adapter lifecycle and extension points.
- **Providers**: [docs/providers.md](docs/providers.md) lists supported providers, setup URLs and model names.
- **Testing**: [wiki/Testing.md](wiki/Testing.md) covers test suites and how to run them.
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting issues and pull requests.
- **Roadmap and technical debt**: [docs/architecture-review.md](docs/architecture-review.md) outlines current limitations and planned improvements.

## Contributing

Pull requests are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) to learn about our coding standards, how to run the test suite and how to get involved. We maintain a dual‑language README and check for parity between `README.md` and `README.zh-CN.md` on each change.
