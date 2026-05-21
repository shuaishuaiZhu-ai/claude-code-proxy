<#
.SYNOPSIS
Legacy PowerShell wrapper for ChatGPT subscription mode.

.DESCRIPTION
Prefer the direct command:

  ccproxy model set --provider chatgpt-subscription --model ChatGPT5.5
  ccproxy run -- -p "reply ccproxy-ok"

This wrapper now delegates to those commands. It exists only for users who
already copied the old script command.
#>

[CmdletBinding()]
param(
    [string]$Model = "ChatGPT5.5",
    [string]$Prompt,
    [string[]]$ClaudeArgs = @(),
    [switch]$ManualLogin,
    [switch]$NoAdapterStart,
    [switch]$DoctorOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonPath = Join-Path $RepoRoot "src"

if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$PythonPath;$($env:PYTHONPATH)"
} else {
    $env:PYTHONPATH = $PythonPath
}

$adapterArgs = @("-m", "ccproxy", "model", "set", "--provider", "chatgpt-subscription", "--model", $Model)
if ($ManualLogin) {
    $adapterArgs += "--manual-login"
}
if ($NoAdapterStart) {
    $adapterArgs += "--no-adapter-start"
}

& python @adapterArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if ($DoctorOnly) {
    & python -m ccproxy doctor --profile chatgpt-subscription
    exit $LASTEXITCODE
}

if ($Prompt) {
    $ResolvedClaudeArgs = @("claude", "--bare", "--model", "sonnet", "-p", $Prompt)
} elseif ($ClaudeArgs.Count -gt 0) {
    if ($ClaudeArgs[0] -eq "claude" -or $ClaudeArgs[0] -like "*claude.cmd") {
        $ResolvedClaudeArgs = $ClaudeArgs
    } else {
        $ResolvedClaudeArgs = @("claude", "--bare") + $ClaudeArgs
    }
} else {
    $ResolvedClaudeArgs = @("claude", "--bare", "--model", "sonnet")
}

$runArgs = @("-m", "ccproxy", "run")
if ($ManualLogin) {
    $runArgs += "--manual-login"
}
if ($NoAdapterStart) {
    $runArgs += "--no-adapter-start"
}
$runArgs += "--"
$runArgs += $ResolvedClaudeArgs
& python @runArgs
exit $LASTEXITCODE
