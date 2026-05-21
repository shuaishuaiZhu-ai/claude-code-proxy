# Contributing

Thanks for improving `cc-provider-proxy`.

## Local Checks

Run these before opening a pull request:

```bash
python -m pip install -e .
python -m unittest discover -s tests
python -m compileall -q src tests scripts
```

For a local Claude Code smoke test without a real provider key:

```bash
python scripts/mock_openai_provider.py --port 8000
ccproxy init --profile custom --config ./mock.toml
ccproxy run --config ./mock.toml --profile custom -- claude --model sonnet -p "reply ccproxy-ok"
```

## Provider Changes

- Keep secrets in environment variables, never in config files.
- Add or update tests when changing request/response translation.
- Prefer provider presets over special-case code paths.
- Keep subscription account support behind `external-adapter`; do not add browser
  cookie/session handling to the core proxy.

## Documentation

Public README examples should be copy-pasteable on Windows, macOS, WSL, and
Linux. If a command is shell-specific, label the shell.
