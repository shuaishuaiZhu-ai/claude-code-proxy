# Architecture

This document provides a high‑level overview of the `claude-code-proxy` (ccproxy) architecture. It explains the goals, system context, module boundaries, request translation pipeline, provider profile model, managed adapter lifecycle, error handling, observability, extension points and testing strategy. The intention is to guide maintenance and extension rather than to serve as a tutorial. For background on current limitations and technical debt, see [`docs/architecture-review.md`](architecture-review.md).

## 1 Goals and non‑goals

**Goals:**

* Provide a local sidecar for Claude Code that translates between Anthropic Messages and other chat completion protocols.
* Allow users to choose a provider profile (OpenAI key, ChatGPT subscription, DeepSeek, Kimi, Zhipu, MiniMax or custom) without modifying Claude Code itself.
* Keep API keys and tokens on the user’s machine; never leak secrets to remote servers or logs.
* Require only the Python standard library for core functionality; optional extras for server mode should be installable via extras (`[server]`).
* Be easily extensible to support new providers, translators and adapters without scattered `if/elif` logic.

**Non‑goals:**

* Running remote tasks or forwarding arbitrary network traffic — ccproxy is intentionally scoped to the Anthropic API shape.
* Acting as a global HTTP proxy — it only proxies Claude Code traffic and never intercepts other requests.
* Becoming a general authentication broker — each managed adapter stays in its own lifecycle and is not exposed to other processes.

## 2 System context

The user runs the `ccproxy` CLI on their machine. When they run `ccproxy run` the following sequence occurs:

1. The CLI resolves the active provider profile and model from `~/.ccproxy/config.toml` and `~/.ccproxy/secrets.toml`.
2. If a profile requires a managed adapter (e.g. ChatGPT subscription), the adapter manager checks whether the adapter binary is installed, starts it if necessary and ensures it is ready.
3. ccproxy starts an HTTP server bound to `127.0.0.1` (default port 8082). When Claude Code connects to this server it sets the `ANTHROPIC_BASE_URL` environment variable so that Claude Code sends its API calls to ccproxy.
4. For each request from Claude Code, the translator module maps the Anthropic request into the appropriate upstream protocol and sends it via the client to the chosen provider.
5. Responses (streaming or JSON) are converted back into Anthropic payloads and returned to Claude Code.
6. When `ccproxy run` exits, the proxy shuts down. Secrets remain on disk; adapters may continue running or be shut down depending on the profile’s configuration.

## 3 Runtime topology

At runtime there are up to three processes on the user’s machine:

* **Claude Code** – The CLI tool from Anthropic that executes user prompts. It speaks the Anthropic Messages API.
* **ccproxy** – A Python process that acts as a local proxy. It translates requests and responses, manages secrets and adapter lifecycles.
* **Managed adapter (optional)** – An executable (e.g. [auth2api](https://github.com/richardyc/auth2api) for ChatGPT subscriptions) that handles provider‑specific authentication flows such as OAuth or device‑code login.

ccproxy communicates with the managed adapter over HTTP on a callback port. The adapter communicates with the provider’s servers. Secrets and tokens are stored locally.

## 4 Core modules

The core code is organised into a few cohesive modules under `src/ccproxy`:

* **cli/** – Builds the argument parser and dispatches commands (`model`, `profiles`, `run`, `serve`, `doctor`, etc.). Each command lives in its own module and uses shared helpers.
* **config.py** – Reads and writes the configuration and secrets files (`~/.ccproxy/config.toml` and `~/.ccproxy/secrets.toml`). Provides dataclasses for `ProviderProfile`, `ModelConfig` and user settings.
* **providers.py** – Defines built‑in provider profiles (OpenAI, ChatGPT subscription, DeepSeek, Kimi, Zhipu, MiniMax, custom). Profiles are plain data: name, base URL, headers, environment variable names, supported models, optional setup URL, managed adapter information and hidden flags.
* **translators/** – Contains translator implementations for each protocol pair. The `openai` translator maps Anthropic requests to OpenAI Chat Completions and vice versa. A registry maps provider type strings to translator classes. Translators must implement methods for `to_upstream`, `from_upstream` and `stream_from_upstream`.
* **client.py** – Sends HTTP requests to upstream providers. Handles connection and read timeouts. Provides streaming support and basic retry logic for non‑streaming calls.
* **adapters/** – Defines an interface for managed adapters and a manager that resolves an adapter by name, installs it if necessary, starts it and checks its status. Each adapter implementation lives in its own module (e.g. `auth2api.py`).
* **server.py** – Implements the FastAPI‑based HTTP proxy. The server exposes only the endpoints necessary for the Anthropic Messages API and uses translators and the client to satisfy requests.
* **logging.py** – Configures logging levels and output. Logging never prints secrets.

## 5 Request translation pipeline

The translation pipeline converts between Anthropic and upstream formats. Given an Anthropic request:

1. The CLI obtains the active provider profile and selects the translator based on the profile’s `type` field (e.g. `openai-compatible`, `anthropic-compatible`).
2. The translator’s `to_upstream()` method receives the Anthropic request and the provider profile. It constructs an upstream request: URL path, method, headers and JSON body. It may also adjust model names (e.g. mapping Anthropic model `sonnet` to upstream model `gpt-4o`).
3. The client sends the upstream request. For streaming responses the client yields SSE events chunk by chunk.
4. For each upstream response or SSE event the translator’s `from_upstream()`/`stream_from_upstream()` method maps it back to the Anthropic schema, remapping roles and tool‑call payloads as necessary.
5. The proxy returns the translated payload to Claude Code.

## 6 Provider profile model

Provider profiles are pure data structures describing how to call a particular provider. A `ProviderProfile` includes:

* **name** – Identifier used on the command line (e.g. `openai-key`).
* **type** – A key used to look up the translator (`openai-compatible`, `anthropic-compatible`, etc.).
* **base URL** – The upstream API base; `http://127.0.0.1:8000/v1` for custom adapters.
* **headers** – Additional HTTP headers to send on each request (e.g. `Authorization`).
* **api_key_env** – Environment variable used to fetch API keys (e.g. `OPENAI_API_KEY`).
* **models** – Mapping of Anthropic model names to upstream model names.
* **setup_label/setup_url** – Optional label and URL where users can obtain an API key. If specified the CLI can open this URL during setup.
* **managed_adapter** – Name of the managed adapter required for this profile (e.g. `auth2api`). If `None` the provider does not need an adapter.
* **hidden** – Flag for internal profiles that are not shown in the default profile list.

Profiles are declared once and consumed by the CLI, translator registry and adapter manager. Adding a new provider means adding a new entry to the profiles list and implementing a translator if the protocol is not already supported.

## 7 Managed adapter lifecycle

Some providers require a local adapter to handle authentication flows. For example, ChatGPT subscriptions use [auth2api](https://github.com/richardyc/auth2api). The adapter manager is responsible for:

1. **Discovery** – Resolving the adapter module based on the provider profile’s `managed_adapter` field.
2. **Installation** – Downloading or building the adapter binary at a fixed version (pinned by tag or commit) the first time it is needed.
3. **Start** – Launching the adapter process on demand and listening on a callback port.
4. **Status** – Checking whether the adapter is installed and running; reporting statuses in `ccproxy doctor`.
5. **Clean up** – Shutting down or restarting the adapter if it becomes unhealthy.

Adapter implementations are fully isolated. They do not embed business logic in ccproxy; ccproxy communicates with them over HTTP and treats them as black boxes.

## 8 Error handling model

Errors may arise during translation, networking or authentication. ccproxy follows these principles:

* **Fail fast on missing credentials** – `ccproxy run` checks for required keys/tokens and asks the user to run `ccproxy model set` if they are absent.
* **Propagate upstream errors** – HTTP status codes and error messages from the provider are passed back to Claude Code through the translated schema.
* **Do not retry streaming calls** – Retrying streaming calls risks duplicating tool invocations; ccproxy only retries non‑streaming calls once on transient 5xx errors.
* **Never print secrets** – Logs and error messages must not include API keys or tokens.

## 9 Observability

ccproxy logs a small number of events: proxy start/stop, provider and model selection, adapter status, and warning/error messages. Users can enable more verbose output via `--debug` or suppress it with `--quiet`. A health endpoint (`/v1/health`) can be enabled in server mode (`ccproxy serve`) and returns basic status information such as uptime and adapter readiness. Metrics and detailed tracing are intentionally out of scope for the core library but could be added as an extension.

## 10 Extension model

To add a new provider or protocol:

1. **Define a provider profile** in the profiles registry (`providers.py`). At minimum specify `name`, `type`, `base_url`, `api_key_env` and any model mappings.
2. **Implement or reuse a translator**. If the protocol differs from existing ones, add a new translator under `translators/` and register it in the translator registry. Translators should not refer to specific providers; they operate on protocol categories.
3. **Implement a managed adapter** if the provider requires non‑HTTP authentication. Add the adapter under `adapters/` and register it in the adapter manager.
4. **Write tests** covering request/response translation, adapter lifecycle and CLI integration. Tests live in `tests/` and should run with no network connectivity.
5. **Update documentation** including `docs/providers.md`, `README.md`/`README.zh-CN.md` and `docs/readme-parity.md`.

## 11 Testing strategy

The `tests/` directory contains unit tests covering configuration management, CLI commands, provider profiles, translator logic, managed adapters and the HTTP client. Tests run under Python 3.11+ and do not require live network access. Use `python -m unittest discover -s tests` to run all tests. A `scripts/mock_openai_provider.py` is provided to simulate an OpenAI‑compatible endpoint for integration testing. Continuous integration (CI) runs tests on Linux, macOS and Windows across multiple Python versions and checks code formatting (with `ruff`) and Markdown link validity.

---

This architecture document is a living document. As new providers and protocols are added, and as technical debt is addressed, please update this file to reflect the current design.