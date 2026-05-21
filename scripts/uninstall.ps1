param(
    [switch]$KeepState
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[ccproxy] $Message"
}

function Find-Python {
    foreach ($command in @("python", "py")) {
        if (Get-Command $command -ErrorAction SilentlyContinue) {
            return $command
        }
    }
    return $null
}

Write-Step "uninstalling package with pip uninstall"
$Python = Find-Python
if ($Python) {
    if ($Python -eq "py") {
        & py -3 -m pip uninstall -y claude-code-proxy
    } else {
        & $Python -m pip uninstall -y claude-code-proxy
    }
} else {
    Write-Warning "Python was not found, so pip uninstall could not run."
}

$StateDir = Join-Path $HOME ".ccproxy"
if ($KeepState) {
    Write-Step "keeping state directory: $StateDir"
} elseif (Test-Path $StateDir) {
    Write-Step "removing state directory: $StateDir"
    Remove-Item -LiteralPath $StateDir -Recurse -Force
} else {
    Write-Step "state directory not found: $StateDir"
}

Write-Step "uninstall complete. This script does not uninstall Python, pip, or Claude CLI."
Write-Step "It does not uninstall Python, pip, or Claude without user confirmation."
