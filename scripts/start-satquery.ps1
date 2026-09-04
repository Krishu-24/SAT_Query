# SatQuery AI - one-click local launcher (Windows PowerShell 5.1 + 7)
# Checks requirements, installs missing deps, starts Ollama planner + API + UI.
#
# Double-click:  START_SATQUERY.bat
# Or run:        powershell -ExecutionPolicy Bypass -File .\scripts\start-satquery.ps1

[CmdletBinding()]
param(
    [switch]$SkipOllama,
    [switch]$SkipBrowser,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Split-Path -Parent $ScriptDir
$BackendDir  = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$RouterDir   = Join-Path $RepoRoot "router"
$VenvDir     = Join-Path $BackendDir ".venv"
$ReqLite     = Join-Path $BackendDir "requirements-lite.txt"
$EnvLocal    = Join-Path $FrontendDir ".env.local"
$LogDir      = Join-Path $RepoRoot "scripts\logs"
$StateFile   = Join-Path $LogDir "last-run.json"

$FrontendUrl = "http://localhost:$FrontendPort"
$BackendUrl  = "http://127.0.0.1:$BackendPort"
$OllamaUrl   = "http://127.0.0.1:11434"
$OllamaModel = "qwen3:4b-instruct"

$script:BackendProc  = $null
$script:FrontendProc = $null
$script:OllamaProc   = $null
$script:Failures     = New-Object System.Collections.Generic.List[string]
$script:Warnings     = New-Object System.Collections.Generic.List[string]

function Write-Banner([string]$Text) {
    Write-Host ""
    Write-Host ("=" * 64) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 64) -ForegroundColor Cyan
}
function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host ">> $Text" -ForegroundColor Yellow
}
function Write-Ok([string]$Text) { Write-Host "   [OK]  $Text" -ForegroundColor Green }
function Write-Warn([string]$Text) {
    Write-Host "   [!]   $Text" -ForegroundColor DarkYellow
    [void]$script:Warnings.Add($Text)
}
function Write-Fail([string]$Text) {
    Write-Host "   [X]   $Text" -ForegroundColor Red
    [void]$script:Failures.Add($Text)
}
function Write-Info([string]$Text) { Write-Host "   ...  $Text" -ForegroundColor Gray }

function Test-Cmd([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-CmdPath([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Refresh-Path {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($machine -or $user) { $env:Path = "$machine;$user" }
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSec = 90, [string]$Label = "service") {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    Write-Fail "$Label did not become ready at $Url within ${TimeoutSec}s"
    return $false
}

function Try-WingetInstall([string]$Id, [string]$Label) {
    if (-not (Test-Cmd "winget")) {
        Write-Warn "winget not available - cannot auto-install $Label"
        return $false
    }
    Write-Info "Installing $Label via winget ($Id)..."
    try {
        $p = Start-Process -FilePath "winget" -ArgumentList @(
            "install", "--id", $Id, "-e",
            "--accept-package-agreements", "--accept-source-agreements", "--silent"
        ) -Wait -PassThru -NoNewWindow
        Refresh-Path
        return ($p.ExitCode -eq 0 -or $p.ExitCode -eq -1978335189)
    } catch {
        Write-Warn ("winget install for {0} failed: {1}" -f $Label, $_.Exception.Message)
        return $false
    }
}

function Stop-PortListeners([int]$Port) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
        }
    } catch {}
}

function Stop-TrackedProcesses {
    foreach ($p in @($script:FrontendProc, $script:BackendProc)) {
        if ($null -ne $p) {
            try {
                if (-not $p.HasExited) {
                    $procId = $p.Id
                    Start-Process -FilePath "taskkill" -ArgumentList "/PID", "$procId", "/T", "/F" `
                        -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue | Out-Null
                }
            } catch {}
        }
    }
}

try {
    Write-Banner "SatQuery AI - One-Click Local Setup"
    Write-Host "Repo: $RepoRoot"
    Ensure-Dir $LogDir

    Write-Step "1/8  Checking project folders"
    foreach ($pair in @(
        @{ Path = $BackendDir;  Name = "Backend" },
        @{ Path = $FrontendDir; Name = "Frontend" },
        @{ Path = $RouterDir;   Name = "Router" }
    )) {
        if (Test-Path $pair.Path) { Write-Ok $pair.Name }
        else { Write-Fail ("{0} missing: {1}" -f $pair.Name, $pair.Path) }
    }
    if ($script:Failures.Count -gt 0) {
        throw "Required project folders are missing."
    }

    Write-Step "2/8  Checking system requirements"

    $pythonOk = $false
    $usePyLauncher = $false
    foreach ($cand in @("python", "py")) {
        if (Test-Cmd $cand) {
            try {
                $verOut = & $cand --version 2>&1 | Out-String
                if ($verOut -match "Python (\d+)\.(\d+)") {
                    $major = [int]$Matches[1]
                    $minor = [int]$Matches[2]
                    if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                        $pythonOk = $true
                        $usePyLauncher = ($cand -eq "py")
                        Write-Ok ("Python {0}.{1} found" -f $major, $minor)
                        break
                    }
                    Write-Warn ("Python {0}.{1} is too old (need 3.11+)" -f $major, $minor)
                }
            } catch {}
        }
    }
    if (-not $pythonOk) {
        Write-Warn "Python 3.11+ not found - attempting winget install..."
        [void](Try-WingetInstall "Python.Python.3.12" "Python 3.12")
        Refresh-Path
        if (Test-Cmd "python") {
            $pythonOk = $true
            Write-Ok ("Python installed: {0}" -f ((& python --version 2>&1 | Out-String).Trim()))
        } else {
            Write-Fail "Install Python 3.12 from https://www.python.org/downloads/ (enable Add to PATH), then re-run."
        }
    }

    $nodeOk = Test-Cmd "node"
    $npmOk  = Test-Cmd "npm"
    if ($nodeOk) {
        Write-Ok ("Node.js {0}" -f ((& node --version 2>&1 | Out-String).Trim()))
    } else {
        Write-Warn "Node.js not found - attempting winget install..."
        [void](Try-WingetInstall "OpenJS.NodeJS.LTS" "Node.js LTS")
        Refresh-Path
        $nodeOk = Test-Cmd "node"
        $npmOk  = Test-Cmd "npm"
        if ($nodeOk) {
            Write-Ok ("Node.js installed: {0}" -f ((& node --version 2>&1 | Out-String).Trim()))
        } else {
            Write-Fail "Install Node.js LTS from https://nodejs.org/ then re-run this script."
        }
    }
    if ($npmOk) {
        Write-Ok ("npm {0}" -f ((& npm --version 2>&1 | Out-String).Trim()))
    } elseif ($nodeOk) {
        Write-Fail "npm missing - repair/reinstall Node.js"
    }

    $ollamaOk = $false
    if (-not $SkipOllama) {
        if (Test-Cmd "ollama") {
            Write-Ok "Ollama found"
            $ollamaOk = $true
        } else {
            $guess = @(
                "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
                "$env:ProgramFiles\Ollama\ollama.exe"
            ) | Where-Object { Test-Path $_ }
            if ($guess.Count -gt 0) {
                $ollamaDir = Split-Path $guess[0]
                $env:Path = "$ollamaDir;$env:Path"
                $ollamaOk = $true
                Write-Ok ("Ollama found at {0}" -f $guess[0])
            } else {
                Write-Warn "Ollama not found - attempting winget install..."
                [void](Try-WingetInstall "Ollama.Ollama" "Ollama")
                Refresh-Path
                $guess2 = @()
                $p1 = Get-CmdPath "ollama"
                if ($p1) { $guess2 += $p1 }
                foreach ($candPath in @(
                    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
                    "$env:ProgramFiles\Ollama\ollama.exe"
                )) {
                    if (Test-Path $candPath) { $guess2 += $candPath }
                }
                if ($guess2.Count -gt 0) {
                    $ollamaDir = Split-Path $guess2[0]
                    $env:Path = "$ollamaDir;$env:Path"
                    $ollamaOk = $true
                    Write-Ok "Ollama installed"
                } else {
                    Write-Warn "Ollama missing - planner will use rule-based fallback. Install later from https://ollama.com/download"
                }
            }
        }
    } else {
        Write-Info "Skipping Ollama (-SkipOllama)"
    }

    if ($script:Failures.Count -gt 0) {
        throw "Fix the failed system requirements above, then re-run."
    }

    Write-Step "3/8  Backend virtualenv + Python packages"

    if (-not (Test-Path $ReqLite)) {
        throw "Missing $ReqLite"
    }
    Write-Ok "requirements-lite.txt present"

    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    $venvPip    = Join-Path $VenvDir "Scripts\pip.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Info "Creating venv..."
        if ($usePyLauncher) { & py -3 -m venv $VenvDir }
        else { & python -m venv $VenvDir }
        Write-Ok "venv created"
    } else {
        Write-Ok "venv already exists"
    }

    Write-Info "Installing / verifying Python packages..."
    & $venvPython -m pip install --upgrade pip -q
    & $venvPip install -r $ReqLite -q
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    Write-Ok "Backend dependencies ready"

    $env:USE_SHIVEN_ROUTER = "true"
    $env:SKIP_MODEL_INFERENCE = "true"
    $env:SHIVEN_ROUTER_ROOT = $RouterDir
    $env:OLLAMA_BASE_URL = $OllamaUrl
    $env:OLLAMA_PLANNER_MODEL = $OllamaModel

    Write-Step "4/8  Frontend .env + npm packages"

    $envContent = "NEXT_PUBLIC_API_URL=$BackendUrl"
    Set-Content -Path $EnvLocal -Value $envContent -Encoding ASCII
    Write-Ok "frontend/.env.local -> $envContent"

    Push-Location $FrontendDir
    try {
        $nextPkg = Join-Path $FrontendDir "node_modules\next"
        if (-not (Test-Path $nextPkg)) {
            Write-Info "Running npm install (first run can take several minutes)..."
            & npm.cmd install
            if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
            Write-Ok "Frontend dependencies installed"
        } else {
            Write-Ok "node_modules present - refreshing..."
            & npm.cmd install --prefer-offline
            if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
            Write-Ok "Frontend dependencies verified"
        }
    } finally {
        Pop-Location
    }

    Write-Step "5/8  Ollama planner model ($OllamaModel)"

    if ($ollamaOk -and -not $SkipOllama) {
        $ollamaUp = $false
        try {
            $null = Invoke-WebRequest -Uri "$OllamaUrl/api/tags" -UseBasicParsing -TimeoutSec 2
            $ollamaUp = $true
            Write-Ok "Ollama API already running"
        } catch {
            Write-Info "Starting Ollama serve..."
            $ollamaLog = Join-Path $LogDir "ollama.log"
            $script:OllamaProc = Start-Process -FilePath "ollama" -ArgumentList "serve" `
                -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput $ollamaLog -RedirectStandardError $ollamaLog
            if (Wait-Http "$OllamaUrl/api/tags" 60 "Ollama") {
                $ollamaUp = $true
                Write-Ok "Ollama API ready"
            }
        }

        if ($ollamaUp) {
            try {
                $tags = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 10
                $names = @()
                if ($tags.models) { $names = @($tags.models | ForEach-Object { $_.name }) }
                $have = $names | Where-Object { $_ -like "$OllamaModel*" }
                if ($have) {
                    Write-Ok "Model already downloaded: $OllamaModel"
                } else {
                    Write-Info "Downloading $OllamaModel (large download - please wait)..."
                    & ollama pull $OllamaModel
                    if ($LASTEXITCODE -eq 0) { Write-Ok "Model ready: $OllamaModel" }
                    else { Write-Warn "Could not pull $OllamaModel - rule fallback will be used" }
                }
            } catch {
                Write-Warn ("Could not query/pull Ollama models: {0}" -f $_.Exception.Message)
            }
        }
    } else {
        Write-Warn "Ollama unavailable - Debug panel will show planner fallback when used"
    }

    Write-Step "6/8  Starting FastAPI backend on :$BackendPort"

    Stop-PortListeners $BackendPort
    Stop-PortListeners $FrontendPort
    Start-Sleep -Seconds 1

    $backendLog = Join-Path $LogDir "backend.log"
    $backendErr = Join-Path $LogDir "backend.err.log"
    $uvicorn = Join-Path $VenvDir "Scripts\uvicorn.exe"
    if (-not (Test-Path $uvicorn)) { throw "uvicorn.exe missing in venv - pip install may have failed" }

    $script:BackendProc = Start-Process -FilePath $uvicorn `
        -ArgumentList @("app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $BackendDir `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr

    if (-not (Wait-Http "$BackendUrl/api/health" 90 "Backend")) {
        if (Test-Path $backendErr) {
            Write-Info "backend.err.log (tail):"
            Get-Content $backendErr -Tail 40 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
        }
        throw "Backend failed to start"
    }
    Write-Ok "Backend healthy: $BackendUrl/api/health"
    Write-Ok "API docs:        $BackendUrl/docs"

    Write-Step "7/8  Starting Next.js frontend on :$FrontendPort"

    $frontendLog = Join-Path $LogDir "frontend.log"
    $frontendErr = Join-Path $LogDir "frontend.err.log"
    $npmCmd = Get-CmdPath "npm.cmd"
    if (-not $npmCmd) { $npmCmd = Get-CmdPath "npm" }

    $script:FrontendProc = Start-Process -FilePath $npmCmd `
        -ArgumentList @("run", "dev", "--", "-p", "$FrontendPort") `
        -WorkingDirectory $FrontendDir `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr

    if (-not (Wait-Http $FrontendUrl 150 "Frontend")) {
        if (Test-Path $frontendErr) {
            Write-Info "frontend.err.log (tail):"
            Get-Content $frontendErr -Tail 50 | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray }
        }
        throw "Frontend failed to start"
    }
    Write-Ok "Frontend ready: $FrontendUrl"

    Write-Step "8/8  Ready"

    @{
        website    = $FrontendUrl
        backend    = $BackendUrl
        docs       = "$BackendUrl/docs"
        health     = "$BackendUrl/api/health"
        ollama     = $OllamaUrl
        model      = $OllamaModel
        logs       = $LogDir
        started_at = (Get-Date).ToString("s")
    } | ConvertTo-Json | Set-Content $StateFile -Encoding UTF8

    Write-Banner "SatQuery is running"
    Write-Host ""
    Write-Host "  OPEN THE WEBSITE:" -ForegroundColor White
    Write-Host "  $FrontendUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Backend API:   $BackendUrl" -ForegroundColor Gray
    Write-Host "  Swagger docs:  $BackendUrl/docs" -ForegroundColor Gray
    Write-Host "  Health:        $BackendUrl/api/health" -ForegroundColor Gray
    Write-Host "  Logs:          $LogDir" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Tip: Enable Debug Mode in the sidebar to inspect routing," -ForegroundColor DarkCyan
    Write-Host "       intent decomposition, and model-not-loaded steps." -ForegroundColor DarkCyan
    Write-Host ""

    if ($script:Warnings.Count -gt 0) {
        Write-Host "  Warnings:" -ForegroundColor DarkYellow
        $script:Warnings | ForEach-Object { Write-Host "    - $_" -ForegroundColor DarkYellow }
        Write-Host ""
    }

    if (-not $SkipBrowser) {
        Write-Info "Opening browser..."
        Start-Process $FrontendUrl | Out-Null
    }

    Write-Host "  Leave this window open. Press Ctrl+C to stop everything." -ForegroundColor Yellow
    Write-Host ""

    while ($true) {
        Start-Sleep -Seconds 2
        if ($null -ne $script:BackendProc -and $script:BackendProc.HasExited) {
            Write-Fail ("Backend exited (code {0}). See {1}" -f $script:BackendProc.ExitCode, $backendErr)
            break
        }
        if ($null -ne $script:FrontendProc -and $script:FrontendProc.HasExited) {
            Write-Fail ("Frontend exited (code {0}). See {1}" -f $script:FrontendProc.ExitCode, $frontendErr)
            break
        }
    }
}
catch {
    Write-Host ""
    Write-Host ("SETUP FAILED: {0}" -f $_.Exception.Message) -ForegroundColor Red
    Write-Host "Logs: $LogDir" -ForegroundColor Red
    Write-Host ""
    Write-Host "Press Enter to close..." -ForegroundColor Yellow
    try { [void](Read-Host) } catch {}
    exit 1
}
finally {
    Write-Host ""
    Write-Host "Shutting down SatQuery processes..." -ForegroundColor Yellow
    Stop-TrackedProcesses
    Write-Host "Stopped." -ForegroundColor Gray
}
