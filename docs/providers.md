# Provider Profiles

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

`openai-key` is the direct OpenAI API key mode. `chatgpt-subscription` is the
ChatGPT subscription mode, but it intentionally goes through a user-managed
local adapter. The adapter must expose an OpenAI-compatible `/chat/completions`
API. `ccproxy` does not log into web subscription accounts, manage browser
sessions, or store cookies.
