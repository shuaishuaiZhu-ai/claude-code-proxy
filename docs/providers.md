# Provider Profiles

`ccproxy` keeps provider choice in a named profile. Secrets stay in environment
variables; config files only contain endpoint, model, and env-var names.

## Built-In Profiles

| Profile | Type | Base URL | API key env |
| --- | --- | --- | --- |
| `openai-key` | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `openai` | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `chatgpt-subscription` | `external-adapter` | `http://127.0.0.1:8000/v1` | `CHATGPT_ADAPTER_API_KEY` |
| `kimi` | `openai-compatible` | `https://api.moonshot.cn/v1` | `KIMI_API_KEY` |
| `zhipu` | `openai-compatible` | `https://open.bigmodel.cn/api/paas/v4` | `ZHIPU_API_KEY` |
| `minimax-cn` | `openai-compatible` | `https://api.minimaxi.com/v1` | `MINIMAX_API_KEY` |
| `minimax-global` | `openai-compatible` | `https://api.minimax.io/v1` | `MINIMAX_API_KEY` |
| `minimax-cn-anthropic` | `anthropic-compatible` | `https://api.minimaxi.com/anthropic` | `MINIMAX_API_KEY` |
| `minimax-global-anthropic` | `anthropic-compatible` | `https://api.minimax.io/anthropic` | `MINIMAX_API_KEY` |
| `custom` | `external-adapter` | `http://127.0.0.1:8000/v1` | `CCPROXY_CUSTOM_API_KEY` |

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

The active profile is stored at `~/.ccproxy/active.toml`. It contains only a
profile name, never an API key.

## Subscription Boundary

`chatgpt-subscription` means "route Claude Code to a local adapter that you
run". It does not mean `ccproxy` logs into ChatGPT, reads browser cookies, or
turns a ChatGPT Plus/Pro/Team plan into an OpenAI API key.

The same boundary applies to Kimi, GLM, MiniMax, or other subscription-backed
adapters. If a subscription provider does not expose an official API, run or
write a local adapter that exposes OpenAI-compatible `/v1/chat/completions`,
then point a profile at that adapter.

## Environment Variables

Set only the key for the profile you use:

```text
OPENAI_API_KEY=
CHATGPT_ADAPTER_API_KEY=
KIMI_API_KEY=
ZHIPU_API_KEY=
MINIMAX_API_KEY=
CCPROXY_CUSTOM_API_KEY=
```

## Type Behavior

- `openai-compatible`: `ccproxy` translates Claude Code's Anthropic Messages
  request to OpenAI Chat Completions and translates the response back.
- `anthropic-compatible`: `ccproxy` forwards the Anthropic-shaped request with
  provider auth and model mapping. This is useful for MiniMax Anthropic mode.
- `external-adapter`: same wire behavior as OpenAI-compatible, but named for
  local subscription adapters so users know they own the adapter process.
