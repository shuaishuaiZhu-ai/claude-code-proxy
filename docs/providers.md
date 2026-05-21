# Provider Profiles

`ccproxy` keeps provider choice in a named profile. Secrets stay in environment
variables; config files only contain endpoint, model, and env-var names.

## Built-In Profiles

| Profile | Type | Base URL | API key env |
| --- | --- | --- | --- |
| `openai-key` | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `openai` | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `chatgpt-subscription` | `external-adapter` | `http://127.0.0.1:8317/v1` | managed local key |
| `kimi` | `openai-compatible` | `https://api.moonshot.cn/v1` | `KIMI_API_KEY` |
| `zhipu` | `openai-compatible` | `https://open.bigmodel.cn/api/paas/v4` | `ZHIPU_API_KEY` |
| `minimax-cn` | `openai-compatible` | `https://api.minimaxi.com/v1` | `MINIMAX_API_KEY` |
| `minimax-global` | `openai-compatible` | `https://api.minimax.io/v1` | `MINIMAX_API_KEY` |
| `minimax-cn-anthropic` | `anthropic-compatible` | `https://api.minimaxi.com/anthropic` | `MINIMAX_API_KEY` |
| `minimax-global-anthropic` | `anthropic-compatible` | `https://api.minimax.io/anthropic` | `MINIMAX_API_KEY` |
| `custom` | `external-adapter` | `http://127.0.0.1:8000/v1` | `CCPROXY_CUSTOM_API_KEY` |

## Command-First Selection

Use the same commands on Windows, macOS, WSL, and Linux:

```sh
ccproxy model set
ccproxy model current
ccproxy run -- -p "reply ccproxy-ok"
```

`ccproxy model set` asks for a provider first, then asks for a model. You can
choose a configured alias such as `big`, `middle`, or `small`, or type any
custom upstream model name.

Before asking for a model, `ccproxy model set` verifies that the selected
provider is usable:

- `chatgpt-subscription`: installs/starts the managed auth2api adapter and runs
  the ChatGPT/Codex login flow when no token exists.
- API-key providers: checks the configured environment variable. If it is
  missing, `ccproxy` opens the provider setup page, prints the exact environment
  variable command, and exits without saving an unusable provider/model state.
- `custom`: skips API-key enforcement because local adapters often use their own
  auth scheme or no auth at all.

Non-interactive examples:

```sh
ccproxy model set --provider openai-key --model gpt-4.1
ccproxy model set --provider chatgpt-subscription --model ChatGPT5.5
ccproxy model set --provider kimi --model moonshot-v1-128k
```

The active profile is stored at `~/.ccproxy/active.toml`. Active model choices
are stored per provider at `~/.ccproxy/models.toml`. Neither file stores API
keys.

Use `--no-open-login` when running on a headless server:

```sh
ccproxy model set --provider openai-key --model gpt-4.1 --no-open-login
```

## Subscription Boundary

`chatgpt-subscription` is a managed local adapter profile. `ccproxy init`,
`ccproxy model set`, `ccproxy serve`, and `ccproxy run` install and start
[auth2api](https://github.com/AmazingAng/auth2api) when that profile is active.
On first use, auth2api opens or prints a ChatGPT/Codex login URL. Finish login
in the browser, then return to the terminal.

This does not turn a ChatGPT Plus/Pro/Team plan into an OpenAI Platform API key.
The OpenAI API-key route is still `openai-key` with `OPENAI_API_KEY`; the
subscription route is a local adapter backed by your browser/OAuth login.

The same boundary applies to Kimi, GLM, MiniMax, or other subscription-backed
adapters. If a subscription provider does not expose an official API and
`ccproxy` does not have a managed adapter for it, run or write a local adapter
that exposes OpenAI-compatible `/v1/chat/completions`, then point a profile at
that adapter.

For local adapter profiles, `ccproxy run` checks whether the adapter host/port
is reachable before starting Claude Code. `chatgpt-subscription` tries to start
the managed adapter first; `custom` still expects you to own the adapter
process.

## Environment Variables

Set only the key for the profile you use:

```text
OPENAI_API_KEY=
KIMI_API_KEY=
ZHIPU_API_KEY=
MINIMAX_API_KEY=
CCPROXY_CUSTOM_API_KEY=
```

`chatgpt-subscription` uses a local managed key internally, so no
`CHATGPT_ADAPTER_API_KEY` is needed unless you override the profile with your
own unmanaged adapter.

## Type Behavior

- `openai-compatible`: `ccproxy` translates Claude Code's Anthropic Messages
  request to OpenAI Chat Completions and translates the response back.
- `anthropic-compatible`: `ccproxy` forwards the Anthropic-shaped request with
  provider auth and model mapping. This is useful for MiniMax Anthropic mode.
- `external-adapter`: same wire behavior as OpenAI-compatible. For
  `chatgpt-subscription`, `ccproxy` manages auth2api. For `custom`, you own the
  adapter process.
