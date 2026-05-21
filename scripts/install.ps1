param(
    [switch]$WithServer,
    [switch]$NoInit
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Write-Step($Message) {
    Write-Host "[ccproxy] $Message"
}

function Find-Python {
    $candidates = @(
        @{ Command = "python"; Args = @() },
        @{ Command = "py"; Args = @("-3") }
    )
    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) {
            continue
        }
        & $candidate.Command @($candidate.Args) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }
    throw "Python 3.11 or newer was not found. Install Python from https://www.python.org/downloads/ and rerun this script."
}

function Invoke-Python($Python, [string[]]$PythonArgs, [switch]$AllowFailure) {
    if ($AllowFailure) {
        & $Python.Command @($Python.Args) @PythonArgs *> $null
    } else {
        & $Python.Command @($Python.Args) @PythonArgs
    }
    $code = $LASTEXITCODE
    if ($AllowFailure) {
        return $code
    }
    if ($code -ne 0) {
        throw "Python command failed with exit code ${code}: $($PythonArgs -join ' ')"
    }
}

Write-Step "checking Python 3.11+"
$Python = Find-Python
Invoke-Python -Python $Python -PythonArgs @("--version")

Write-Step "checking pip"
$pipStatus = Invoke-Python -Python $Python -PythonArgs @("-m", "pip", "--version") -AllowFailure 2>$null
if ($pipStatus -ne 0) {
    Write-Step "pip was not available; trying Python ensurepip"
    Invoke-Python -Python $Python -PythonArgs @("-m", "ensurepip", "--upgrade")
}

if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Step "Claude CLI found: $((Get-Command claude).Source)"
} elseif (Get-Command claude.cmd -ErrorAction SilentlyContinue) {
    Write-Step "Claude CLI found: $((Get-Command claude.cmd).Source)"
} else {
    Write-Warning "Claude CLI was not found on PATH. Install it before running ccproxy through Claude Code."
}

$InstallTarget = $RepoRoot
if ($WithServer) {
    $InstallTarget = "$RepoRoot[server]"
}

Write-Step "installing this project with pip install -e"
try {
    Invoke-Python -Python $Python -PythonArgs @("-m", "pip", "install", "-e", $InstallTarget)
} catch {
    Write-Error "pip install failed. If pip reports missing build dependencies such as setuptools, install/upgrade those dependencies or rerun with network access, then run this script again."
    throw
}

Write-Step "verifying ccproxy command"
ccproxy --version

if (-not $NoInit) {
    Write-Step "preparing default config without provider login"
    ccproxy init --skip-model-set
}

Write-Step "install complete. Try: ccproxy doctor"
