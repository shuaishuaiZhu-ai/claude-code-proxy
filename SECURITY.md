# Security Policy

`claude-code-proxy` is a local proxy. Treat provider credentials as sensitive.

## Supported Boundary

- API keys are read from environment variables.
- Config files store environment variable names, not secret values.
- Subscription account integrations must run in an external adapter controlled
  by the user.

## Not Supported

The core proxy does not:

- Store provider API keys.
- Log into web subscription accounts.
- Read browser cookies.
- Manage browser sessions.

## Reporting

If you find a security issue, open a private report through GitHub Security
Advisories when available, or contact the repository owner directly.
