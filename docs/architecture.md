# Architecture

```mermaid
flowchart LR
  Claude["Claude Code CLI"] -->|"Anthropic /v1/messages"| Proxy["ccproxy local server"]
  Proxy -->|"profile routing"| Router["Provider profile"]
  Router -->|"OpenAI-compatible"| OpenAI["OpenAI / Kimi / GLM / MiniMax"]
  Router -->|"Anthropic-compatible"| Anthropic["MiniMax Anthropic endpoint"]
  Router -->|"external-adapter"| Adapter["Local subscription adapter"]
  Adapter --> Provider["User-managed provider"]
```

`ccproxy` keeps provider secrets outside the repository. Profiles reference an
environment variable name, and the runtime reads that variable immediately before
calling the upstream provider.

For OpenAI-compatible providers, `ccproxy` translates Anthropic Messages payloads
into Chat Completions payloads and maps the response back. For
Anthropic-compatible providers, the request is forwarded with only model mapping
and authentication applied.
