<#
.SYNOPSIS
Run Claude Code through ccproxy using a local ChatGPT subscription adapter.

.DESCRIPTION
This script does not log in to ChatGPT, read browser cookies, or turn a ChatGPT
subscription into an OpenAI API key. It expects you to already have a local
OpenAI-compatible adapter for your ChatGPT subscription.

The adapter must expose:
  <AdapterBaseUrl>/chat/completions

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\scripts\run_chatgpt_subscription.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\scripts\run_chatgpt_subscription.ps1 -Prompt "reply ccproxy-ok"

.EXAMPLE
powershell -ExecutionPolicy Bypass -File .\scripts\run_chatgpt_subscription.ps1 -AdapterBaseUrl "http://127.0.0.1:8000/v1" -Model sonnet

.NOTES
The script adds Claude Code's --bare flag by default. In current Claude Code
versions, --bare skips OAuth/keychain login selection and uses ANTHROPIC_API_KEY
for custom endpoints.
#>

[CmdletBinding()]
param(
    [string]$AdapterBaseUrl = "http://127.0.0.1:8000/v1",
    [string]$AdapterApiKey = $env:CHATGPT_ADAPTER_API_KEY,
    [string]$ProxyHost = "127.0.0.1",
    [int]$ProxyPort = 8082,
    [string]$Model = "sonnet",
    [string]$Prompt,
    [string[]]$ClaudeArgs = @(),
    [switch]$NoBare,
    [switch]$DoctorOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ConfigDir = Join-Path $RepoRoot ".ccproxy"
$ConfigPath = Join-Path $ConfigDir "chatgpt-subscription.local.toml"
$PythonPath = Join-Path $RepoRoot "src"

function Write-Step {
    param([string]$Message)
    Write-Host "[ccproxy] $Message" -ForegroundColor Cyan
}

function Quote-TomlString {
    param([string]$Value)
    return '"' + ($Value -replace '\\', '\\' -replace '"', '\"') + '"'
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python was not found on PATH."
}

if (-not (Get-Command claude.cmd -ErrorAction SilentlyContinue) -and -not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw "Claude Code CLI was not found on PATH. Install Claude Code first, then rerun this script."
}

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null

$CleanAdapterBaseUrl = $AdapterBaseUrl.TrimEnd("/")
if (-not $AdapterApiKey) {
    $AdapterApiKey = "ccproxy"
}
$env:CHATGPT_ADAPTER_API_KEY = $AdapterApiKey
$env:ANTHROPIC_API_KEY = "ccproxy"
$env:ANTHROPIC_AUTH_TOKEN = $env:ANTHROPIC_API_KEY

$config = @"
default_profile = "chatgpt-subscription"

[server]
host = $(Quote-TomlString $ProxyHost)
port = $ProxyPort

[profiles.chatgpt-subscription]
type = "external-adapter"
base_url = $(Quote-TomlString $CleanAdapterBaseUrl)
api_key_env = "CHATGPT_ADAPTER_API_KEY"

[profiles.chatgpt-subscription.models]
big = "chatgpt-big"
middle = "chatgpt-middle"
small = "chatgpt-small"
"@

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ConfigPath, $config + [Environment]::NewLine, $Utf8NoBom)

if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$PythonPath;$($env:PYTHONPATH)"
} else {
    $env:PYTHONPATH = $PythonPath
}

Write-Step "config: $ConfigPath"
Write-Step "adapter: $CleanAdapterBaseUrl/chat/completions"
Write-Step "proxy: http://${ProxyHost}:${ProxyPort}"
Write-Step "tip: generic switching is available via scripts\ccproxy-switch.cmd chatgpt-subscription"
Write-Step "tip: use scripts\ccproxy-run.cmd after switching providers"

$doctorCommand = @("-m", "ccproxy", "doctor", "--config", $ConfigPath, "--profile", "chatgpt-subscription")
& python @doctorCommand
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if ($DoctorOnly) {
    exit 0
}

if ($Prompt) {
    $ResolvedClaudeArgs = @("claude", "--model", $Model, "-p", $Prompt)
} elseif ($ClaudeArgs.Count -gt 0) {
    if ($ClaudeArgs[0] -eq "claude" -or $ClaudeArgs[0] -like "*claude.cmd") {
        $ResolvedClaudeArgs = $ClaudeArgs
    } else {
        $ResolvedClaudeArgs = @("claude") + $ClaudeArgs
    }
} else {
    $ResolvedClaudeArgs = @("claude", "--model", $Model)
}

if (-not $NoBare -and -not ($ResolvedClaudeArgs -contains "--bare")) {
    if ($ResolvedClaudeArgs.Count -gt 0) {
        if ($ResolvedClaudeArgs.Count -eq 1) {
            $ResolvedClaudeArgs = @($ResolvedClaudeArgs[0], "--bare")
        } else {
            $ResolvedClaudeArgs = @($ResolvedClaudeArgs[0], "--bare") + $ResolvedClaudeArgs[1..($ResolvedClaudeArgs.Count - 1)]
        }
    } else {
        $ResolvedClaudeArgs = @("claude", "--bare")
    }
}

Write-Step "starting Claude Code through chatgpt-subscription profile"
$runCommand = @("-m", "ccproxy", "run", "--config", $ConfigPath, "--profile", "chatgpt-subscription", "--") + $ResolvedClaudeArgs
& python @runCommand
exit $LASTEXITCODE
