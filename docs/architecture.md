# Architecture

```mermaid
flowchart LR
  Claude["Claude Code CLI"] -->|"Anthropic /v1/messages"| Proxy["ccproxy local server"]
  Proxy -->|"profile routing"| Router["Provider profile"]
  Router -->|"OpenAI-compatible"| OpenAI["OpenAI / DeepSeek / Kimi / GLM / MiniMax"]
  Router -->|"Anthropic-compatible"| Anthropic["MiniMax Anthropic endpoint"]
  Router -->|"chatgpt-subscription"| Managed["Managed auth2api adapter"]
  Router -->|"custom external-adapter"| Adapter["User-managed local adapter"]
  Managed --> ChatGPT["ChatGPT / Codex subscription"]
  Adapter --> Provider["Other subscription provider"]
```

`ccproxy` keeps provider secrets outside the repository. Profiles reference an
environment variable name. The runtime reads that variable first, then falls
back to a user-pasted key saved under `~/.ccproxy/secrets.toml`.

For OpenAI-compatible providers, `ccproxy` translates Anthropic Messages payloads
into Chat Completions payloads and maps the response back. For
Anthropic-compatible providers, the request is forwarded with only model mapping
and authentication applied.

For ChatGPT subscription mode, `ccproxy` manages a local auth2api checkout under
`~/.ccproxy/adapters/auth2api`, runs the ChatGPT/Codex OAuth login flow when no
token exists, and starts auth2api on `http://127.0.0.1:8317`.
