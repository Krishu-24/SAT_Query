# SatQuery AI - one-click local launcher (Windows PowerShell 5.1 + 7)
# Role-aware: Controller / Model Host / Full System.
# Always asks for device role every launch (never reuses a previous role).
# On exit: stops services, unloads Ollama models, clears role config.
#
# Double-click:  START_SATQUERY.bat
# Or run:        powershell -ExecutionPolicy Bypass -File .\scripts\start-satquery.ps1

[CmdletBinding()]
param(
    [switch]$SkipOllama,
    [switch]$SkipBrowser,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$NodePort = 8100
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
$DeviceJson  = Join-Path $RepoRoot ".satquery\device.json"
$ConfigurePy = Join-Path $ScriptDir "configure_role.py"
$PairPy      = Join-Path $ScriptDir "pair_host.py"

$FrontendUrl = "http://localhost:$FrontendPort"
$BackendUrl  = "http://127.0.0.1:$BackendPort"
$OllamaUrl   = "http://127.0.0.1:11434"
$PlannerModel = "qwen3:4b-instruct"
# Official Ollama vision package (same Qwen2.5-VL-7B Instruct family).
# "Qwen2.5-VL-7B-Instruct-GGUF:Q4_K_M" is NOT a registry name - pull fails.
$HostVlmModel = "qwen2.5vl:7b"
$HostVlmFallbacks = @(
    "qwen2.5vl:7b",
    "qwen2.5vl:latest",
    "qwen2.5vl",
    "hf.co/bartowski/Qwen_Qwen2.5-VL-7B-Instruct-GGUF:Q4_K_M"
)

$script:BackendProc  = $null
$script:FrontendProc = $null
$script:NodeProc     = $null
$script:OllamaProc   = $null
$script:Failures     = New-Object System.Collections.Generic.List[string]
$script:Warnings     = New-Object System.Collections.Generic.List[string]
$script:Role         = "full_system"
$script:NodeId       = ""
$script:PairingCode  = ""

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
    $machine = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user    = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    if ($machine -or $user) {
        $joined = $machine + [char]59 + $user
        [System.Environment]::SetEnvironmentVariable('Path', $joined, 'Process')
    }
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

function Clear-DeviceRoleConfig {
    try {
        if (Test-Path $DeviceJson) {
            Remove-Item -Force $DeviceJson -ErrorAction SilentlyContinue
            Write-Info "Cleared device role config (.satquery/device.json)"
        }
        $satDir = Join-Path $RepoRoot ".satquery"
        if ((Test-Path $satDir) -and -not (Get-ChildItem $satDir -Force -ErrorAction SilentlyContinue)) {
            Remove-Item -Force $satDir -ErrorAction SilentlyContinue
        }
    } catch {}
}

function Stop-OllamaModels {
    if (-not (Test-Cmd "ollama")) { return }
    try {
        $running = & ollama ps 2>$null
        if ($running) {
            Write-Info "Unloading Ollama models from memory..."
            $lines = @($running | Select-Object -Skip 1)
            foreach ($line in $lines) {
                if (-not $line) { continue }
                $name = ($line -split "\s+")[0]
                if ($name) {
                    try {
                        & ollama stop $name 2>$null | Out-Null
                        Write-Ok ("Unloaded Ollama model: {0}" -f $name)
                    } catch {}
                }
            }
        }
        # Also stop known SatQuery models even if not listed
        foreach ($m in @($PlannerModel, $HostVlmModel, "qwen2.5vl:7b", "qwen2.5vl", "qwen3:4b-instruct")) {
            try { & ollama stop $m 2>$null | Out-Null } catch {}
        }
    } catch {}
}

function Invoke-CleanShutdown {
    Write-Host ""
    Write-Host "Shutting down SatQuery (freeing ports + model memory)..." -ForegroundColor Yellow

    foreach ($p in @($script:FrontendProc, $script:BackendProc, $script:NodeProc)) {
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
    $script:FrontendProc = $null
    $script:BackendProc = $null
    $script:NodeProc = $null

    Stop-PortListeners $BackendPort
    Stop-PortListeners $FrontendPort
    Stop-PortListeners $NodePort
    if ($script:BackendPortEff) { Stop-PortListeners ([int]$script:BackendPortEff) }
    if ($script:NodePortEff) { Stop-PortListeners ([int]$script:NodePortEff) }

    Stop-OllamaModels

    if ($null -ne $script:OllamaProc) {
        try {
            if (-not $script:OllamaProc.HasExited) {
                Start-Process -FilePath "taskkill" -ArgumentList "/PID", "$($script:OllamaProc.Id)", "/T", "/F" `
                    -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue | Out-Null
            }
        } catch {}
        $script:OllamaProc = $null
    }

    Clear-DeviceRoleConfig
    Write-Host "Stopped. Role cleared - next launch will ask again." -ForegroundColor Gray
}

function Get-VenvPython {
    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) { throw "venv python missing - run dependency setup first" }
    return $venvPython
}

function Ensure-DeviceRole {
    # Always wipe previous role and ask fresh - never reuse last session's choice.
    $venvPython = Get-VenvPython
    Clear-DeviceRoleConfig

    Write-Step "Device role (asked every launch)"
    Write-Host ""
    Write-Host "  Select this device's SatQuery role:" -ForegroundColor White
    Write-Host "    1. Controller   (frontend + backend + small planner Qwen)"
    Write-Host "    2. Model Host   (node API + $HostVlmModel)"
    Write-Host "    3. Full System  (controller + local host when capable)"
    Write-Host ""
    & $venvPython $ConfigurePy --change
    if ($LASTEXITCODE -ne 0) { throw "Role configuration cancelled or failed" }

    if (-not (Test-Path $DeviceJson)) { throw "No device role saved at $DeviceJson" }
    $cfg = Get-Content $DeviceJson -Raw | ConvertFrom-Json
    $script:Role = [string]$cfg.role
    $script:NodeId = [string]$cfg.node_id
    $script:PairingCode = [string]$cfg.pairing_code
    if ($cfg.node_port) { $script:NodePortEff = [int]$cfg.node_port } else { $script:NodePortEff = $NodePort }
    if ($cfg.port) { $script:BackendPortEff = [int]$cfg.port } else { $script:BackendPortEff = $BackendPort }
    Write-Ok ("Role: {0}  node_id: {1}" -f $script:Role, $script:NodeId)
}

function Ensure-OllamaRunning {
    if ($SkipOllama) { Write-Info "Skipping Ollama (-SkipOllama)"; return $false }
    $ollamaOk = $false
    if (Test-Cmd "ollama") {
        Write-Ok "Ollama found"
        $ollamaOk = $true
    } else {
        $guess = @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'),
            (Join-Path $env:ProgramFiles 'Ollama\ollama.exe')
        ) | Where-Object { Test-Path $_ }
        if ($guess.Count -gt 0) {
            $ollamaDir = Split-Path $guess[0]
            $curPath = [System.Environment]::GetEnvironmentVariable('Path', 'Process')
            $newPath = $ollamaDir + [char]59 + $curPath
            [System.Environment]::SetEnvironmentVariable('Path', $newPath, 'Process')
            $ollamaOk = $true
            Write-Ok ('Ollama found at {0}' -f $guess[0])
        } else {
            Write-Warn 'Ollama not found - attempting winget install...'
            [void](Try-WingetInstall 'Ollama.Ollama' 'Ollama')
            Refresh-Path
            $p1 = Get-CmdPath 'ollama'
            if ($p1) {
                $curPath = [System.Environment]::GetEnvironmentVariable('Path', 'Process')
                $newPath = (Split-Path $p1) + [char]59 + $curPath
                [System.Environment]::SetEnvironmentVariable('Path', $newPath, 'Process')
                $ollamaOk = $true
                Write-Ok 'Ollama installed'
            } else {
                Write-Warn "Ollama missing - see https://ollama.com/download"
            }
        }
    }
    if (-not $ollamaOk) { return $false }

    try {
        $null = Invoke-WebRequest -Uri "$OllamaUrl/api/tags" -UseBasicParsing -TimeoutSec 2
        Write-Ok "Ollama API already running"
        return $true
    } catch {
        Write-Info "Starting Ollama serve..."
        $ollamaLog = Join-Path $LogDir "ollama.log"
        $script:OllamaProc = Start-Process -FilePath "ollama" -ArgumentList "serve" `
            -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $ollamaLog -RedirectStandardError $ollamaLog
        if (Wait-Http "$OllamaUrl/api/tags" 60 "Ollama") {
            Write-Ok "Ollama API ready"
            return $true
        }
        return $false
    }
}

function Get-OllamaModelNames {
    try {
        $tags = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 10
        if ($tags.models) { return @($tags.models | ForEach-Object { [string]$_.name }) }
    } catch {}
    return @()
}

function Test-OllamaHasModel([string]$ModelName, [string[]]$Names) {
    if (-not $Names) { $Names = Get-OllamaModelNames }
    foreach ($n in $Names) {
        if ($n -eq $ModelName) { return $n }
        if ($n -like ($ModelName + "*")) { return $n }
        if ($n.ToLower() -eq $ModelName.ToLower()) { return $n }
    }
    # Fuzzy: any local VL-ish qwen name
    $key = $ModelName.ToLower()
    if ($key -like "*qwen*" -and ($key -like "*vl*" -or $key -like "*2.5vl*")) {
        foreach ($n in $Names) {
            $nl = $n.ToLower()
            if ($nl -like "*qwen2.5vl*" -or $nl -like "*qwen2.5-vl*" -or $nl -like "*qwen_qwen2.5-vl*") {
                return $n
            }
        }
    }
    return $null
}

function Ensure-OllamaModel([string]$ModelName, [string]$Label) {
    try {
        $names = Get-OllamaModelNames
        $found = Test-OllamaHasModel $ModelName $names
        if ($found) {
            Write-Ok ("{0} already downloaded: {1}" -f $Label, $found)
            return $true
        }
        Write-Info "Downloading $ModelName ($Label) - large download, please wait..."
        & ollama pull $ModelName
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "$Label ready: $ModelName"
            return $true
        }
        Write-Warn "Could not pull $ModelName"
        return $false
    } catch {
        Write-Warn ("Could not query/pull Ollama model {0}: {1}" -f $ModelName, $_.Exception.Message)
        return $false
    }
}

function Ensure-HostVlmModel {
    $names = Get-OllamaModelNames
    $found = Test-OllamaHasModel $HostVlmModel $names
    if ($found) {
        Write-Ok ("Host VLM already present: {0}" -f $found)
        $script:HostVlmModel = $found
        return $true
    }
    foreach ($cand in $HostVlmFallbacks) {
        Write-Info "Trying Host VLM candidate: $cand"
        if (Ensure-OllamaModel $cand "Host VLM (VQA/caption)") {
            $script:HostVlmModel = $cand
            # Persist resolved tag into device.json when possible
            try {
                $venvPython = Get-VenvPython
                & $venvPython -c @"
import json
from pathlib import Path
p = Path(r'$DeviceJson')
if p.is_file():
    d = json.loads(p.read_text(encoding='utf-8'))
    for m in d.get('hosted_models') or []:
        if m.get('id') == 'qwen-vl':
            m['ollama_tag'] = r'$cand'
    p.write_text(json.dumps(d, indent=2), encoding='utf-8')
"@
            } catch {}
            return $true
        }
    }
    Write-Warn "No Host VLM available. Install with: ollama pull qwen2.5vl:7b"
    Write-Warn "Node API will start, but /node/inference will fail until a VL model is present."
    return $false
}

try {
    Write-Banner "SatQuery AI - One-Click Setup"
    Write-Host "Repo: $RepoRoot"
    Ensure-Dir $LogDir

    Write-Step "1/9  Checking project folders"
    foreach ($pair in @(
        @{ Path = $BackendDir;  Name = "Backend" },
        @{ Path = $FrontendDir; Name = "Frontend" },
        @{ Path = $RouterDir;   Name = "Router" }
    )) {
        if (Test-Path $pair.Path) { Write-Ok $pair.Name }
        else { Write-Fail ("{0} missing: {1}" -f $pair.Name, $pair.Path) }
    }
    if ($script:Failures.Count -gt 0) { throw "Required project folders are missing." }

    Write-Step "2/9  Checking system requirements"

    $pythonOk = $false
    $usePyLauncher = $false
    $pythonCmd = $null
    # Prefer 3.12 / 3.13 / 3.11 - pydantic-core does not build on 3.14 yet
    foreach ($cand in @("py", "python")) {
        if (-not (Test-Cmd $cand)) { continue }
        try {
            if ($cand -eq "py") {
                foreach ($spec in @("-3.12", "-3.13", "-3.11")) {
                    $verOut = & py $spec --version 2>&1 | Out-String
                    if ($verOut -match "Python (\d+)\.(\d+)") {
                        $major = [int]$Matches[1]
                        $minor = [int]$Matches[2]
                        if ($major -eq 3 -and $minor -ge 11 -and $minor -le 13) {
                            $pythonOk = $true
                            $usePyLauncher = $true
                            $script:PyLauncherSpec = $spec
                            $pythonCmd = "py $spec"
                            Write-Ok ("Python {0}.{1} found (py {2})" -f $major, $minor, $spec)
                            break
                        }
                    }
                }
                if ($pythonOk) { break }
            } else {
                $verOut = & $cand --version 2>&1 | Out-String
                if ($verOut -match "Python (\d+)\.(\d+)") {
                    $major = [int]$Matches[1]
                    $minor = [int]$Matches[2]
                    if ($major -eq 3 -and $minor -ge 11 -and $minor -le 13) {
                        $pythonOk = $true
                        $usePyLauncher = $false
                        $pythonCmd = $cand
                        Write-Ok ("Python {0}.{1} found" -f $major, $minor)
                        break
                    }
                    if ($major -eq 3 -and $minor -ge 14) {
                        Write-Warn ("Python {0}.{1} is too new (need 3.11-3.13; pydantic unsupported on 3.14)" -f $major, $minor)
                    } else {
                        Write-Warn ("Python {0}.{1} is unsupported (need 3.11-3.13)" -f $major, $minor)
                    }
                }
            }
        } catch {}
    }
    if (-not $pythonOk) {
        Write-Warn "Compatible Python 3.11-3.13 not found - attempting winget install of 3.12..."
        [void](Try-WingetInstall "Python.Python.3.12" "Python 3.12")
        Refresh-Path
        if (Test-Cmd "py") {
            $verOut = & py -3.12 --version 2>&1 | Out-String
            if ($verOut -match "Python 3\.12") {
                $pythonOk = $true
                $usePyLauncher = $true
                $script:PyLauncherSpec = "-3.12"
                Write-Ok ("Python installed: {0}" -f $verOut.Trim())
            }
        }
        if (-not $pythonOk -and (Test-Cmd "python")) {
            $verOut = & python --version 2>&1 | Out-String
            if ($verOut -match "Python (\d+)\.(\d+)") {
                $major = [int]$Matches[1]; $minor = [int]$Matches[2]
                if ($major -eq 3 -and $minor -ge 11 -and $minor -le 13) {
                    $pythonOk = $true
                    Write-Ok $verOut.Trim()
                }
            }
        }
        if (-not $pythonOk) {
            Write-Fail "Install Python 3.12 from https://www.python.org/downloads/ (enable Add to PATH), then re-run. Do not use 3.14."
        }
    }

    # Node only required for Controller / Full System
    $needFrontend = $true
    # Role unknown until after venv - install node if missing for those roles later

    $nodeOk = Test-Cmd "node"
    $npmOk  = Test-Cmd "npm"
    if ($nodeOk) {
        Write-Ok ("Node.js {0}" -f ((& node --version 2>&1 | Out-String).Trim()))
    } else {
        Write-Warn "Node.js not found (needed for Controller / Full System)"
    }
    if ($npmOk) {
        Write-Ok ("npm {0}" -f ((& npm --version 2>&1 | Out-String).Trim()))
    }

    if ($script:Failures.Count -gt 0) {
        throw "Fix the failed system requirements above, then re-run."
    }

    Write-Step "3/9  Backend virtualenv + Python packages"
    if (-not (Test-Path $ReqLite)) { throw "Missing $ReqLite" }
    Write-Ok "requirements-lite.txt present (pinned deps)"

    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    $venvPip    = Join-Path $VenvDir "Scripts\pip.exe"
    $needVenv = $false
    if (-not (Test-Path $venvPython)) {
        $needVenv = $true
    } else {
        try {
            $venvVer = & $venvPython -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>&1 | Out-String
            $venvVer = $venvVer.Trim()
            if ($venvVer -match "^(\d+)\.(\d+)$") {
                $vm = [int]$Matches[1]; $vn = [int]$Matches[2]
                if ($vm -ne 3 -or $vn -lt 11 -or $vn -gt 13) {
                    Write-Warn ("Existing venv is Python {0} (unsupported) - recreating" -f $venvVer)
                    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
                    $needVenv = $true
                } else {
                    Write-Ok ("venv already exists (Python {0}) - skipping recreate" -f $venvVer)
                }
            } else {
                Write-Warn "Could not read venv Python version - recreating"
                Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
                $needVenv = $true
            }
        } catch {
            $needVenv = $true
        }
    }

    if ($needVenv) {
        Write-Info "Creating venv with compatible Python 3.11-3.13..."
        if ($usePyLauncher) {
            $spec = if ($script:PyLauncherSpec) { $script:PyLauncherSpec } else { "-3.12" }
            & py $spec -m venv $VenvDir
        } else {
            & python -m venv $VenvDir
        }
        if (-not (Test-Path $venvPython)) { throw "venv creation failed" }
        Write-Ok ("venv created: {0}" -f ((& $venvPython --version 2>&1 | Out-String).Trim()))
    }

    # Clean interrupted pip leftovers (e.g. ~yproj) that spam stderr as "errors"
    $sitePkgs = Join-Path $VenvDir "Lib\site-packages"
    if (Test-Path $sitePkgs) {
        Get-ChildItem $sitePkgs -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "~*" } |
            ForEach-Object {
                Write-Info ("Removing broken package leftover: {0}" -f $_.Name)
                Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
            }
    }

    Write-Info "Installing pinned packages from requirements-lite.txt..."
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $venvPython -m pip install --upgrade pip -q 2>&1 | Out-Null
        # -q keeps the console readable; 2>&1 avoids WARNING lines aborting the .bat UI
        $pipOut = & $venvPip install -r $ReqLite -q 2>&1
        $pipCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($pipCode -ne 0) {
        if ($pipOut) { $pipOut | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray } }
        throw "pip install failed. Use Python 3.11-3.13 (not 3.14). See backend/requirements-lite.txt"
    }
    Write-Ok "Backend dependencies ready (pinned)"

    Ensure-DeviceRole
    $role = $script:Role
    $needFrontend = ($role -eq "controller" -or $role -eq "full_system")
    $needPlanner = ($role -eq "controller" -or $role -eq "full_system")
    $needHostVlm = ($role -eq "model_host" -or $role -eq "full_system")
    $BackendPort = $script:BackendPortEff
    $NodePort = $script:NodePortEff
    $BackendUrl = "http://127.0.0.1:$BackendPort"
    $FrontendUrl = "http://localhost:$FrontendPort"

    if ($needFrontend -and -not $nodeOk) {
        Write-Warn "Node.js not found - attempting winget install..."
        [void](Try-WingetInstall "OpenJS.NodeJS.LTS" "Node.js LTS")
        Refresh-Path
        $nodeOk = Test-Cmd "node"
        $npmOk  = Test-Cmd "npm"
        if ($nodeOk) { Write-Ok ("Node.js installed: {0}" -f ((& node --version 2>&1 | Out-String).Trim())) }
        else { Write-Fail "Install Node.js LTS from https://nodejs.org/ then re-run." }
    }
    if ($needFrontend -and -not $npmOk -and $nodeOk) {
        Write-Fail "npm missing - repair/reinstall Node.js"
    }
    if ($script:Failures.Count -gt 0) { throw "Fix Node.js requirements for Controller/Full System." }

    $env:USE_SHIVEN_ROUTER = "true"
    $env:SKIP_MODEL_INFERENCE = "true"
    $env:SHIVEN_ROUTER_ROOT = $RouterDir
    $env:OLLAMA_BASE_URL = $OllamaUrl
    $env:OLLAMA_PLANNER_MODEL = $PlannerModel
    $env:SATQUERY_ROLE = $role
    $env:SATQUERY_NODE_PORT = "$NodePort"

    if ($needFrontend) {
        Write-Step "4/9  Frontend .env + npm packages"
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
                Write-Ok "node_modules present - skipping full reinstall"
                & npm.cmd install --prefer-offline
                if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
                Write-Ok "Frontend dependencies verified"
            }
        } finally {
            Pop-Location
        }
    } else {
        Write-Step "4/9  Frontend skipped (Model Host role)"
        Write-Ok "Not installing or starting Next.js on Model Host"
    }

    Write-Step "5/9  Ollama models"
    $ollamaUp = Ensure-OllamaRunning
    if ($ollamaUp) {
        if ($needPlanner) {
            [void](Ensure-OllamaModel $PlannerModel "Planner")
        } else {
            Write-Info "Skipping planner model pull (Model Host)"
        }
        if ($needHostVlm) {
            [void](Ensure-HostVlmModel)
        } else {
            Write-Info "Skipping Host VLM pull (Controller) - remote Model Host provides $HostVlmModel"
        }
    } else {
        Write-Warn "Ollama unavailable"
    }

    Stop-PortListeners $BackendPort
    if ($needFrontend) { Stop-PortListeners $FrontendPort }
    if ($role -eq "model_host") { Stop-PortListeners $NodePort }
    Start-Sleep -Seconds 1

    $uvicorn = Join-Path $VenvDir "Scripts\uvicorn.exe"
    if (-not (Test-Path $uvicorn)) { throw "uvicorn.exe missing in venv - pip install may have failed" }

    if ($role -eq "model_host") {
        Write-Step "6/9  Starting Model Host node API on :$NodePort (foreground — live traffic)"
        # Run uvicorn in THIS window so pairing + query traffic is visible.
        # (Previously logs were redirected to scripts/logs and the console looked idle.)
        Stop-PortListeners $NodePort
        Start-Sleep -Seconds 1

        Write-Banner "SatQuery Model Host is running"
        Write-Host ""
        Write-Host "  Node ID:       $script:NodeId" -ForegroundColor Green
        Write-Host "  Port:          $NodePort" -ForegroundColor Gray
        Write-Host "  Pairing code:  $script:PairingCode" -ForegroundColor Yellow
        Write-Host "  VLM model:     $HostVlmModel" -ForegroundColor Gray
        Write-Host "  Docs:          http://127.0.0.1:$NodePort/docs" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  On the Controller, pair with:" -ForegroundColor Cyan
        Write-Host "    python scripts/pair_host.py <THIS_LAN_IP> $NodePort $script:PairingCode" -ForegroundColor White
        Write-Host ""
        Write-Host "  Live pairing / query / answer logs will print below." -ForegroundColor DarkCyan
        Write-Host "  Leave this window open. Press Ctrl+C to stop." -ForegroundColor Yellow
        Write-Host ""

        $env:PYTHONUNBUFFERED = "1"
        Push-Location $BackendDir
        try {
            & $uvicorn "app.node.host_app:app" "--host" "0.0.0.0" "--port" "$NodePort" "--log-level" "info"
        } finally {
            Pop-Location
        }
    } else {
        Write-Step "6/9  Starting FastAPI backend on :$BackendPort"
        $backendLog = Join-Path $LogDir "backend.log"
        $backendErr = Join-Path $LogDir "backend.err.log"
        # Truncate old logs so the live tail only shows this session
        "" | Set-Content $backendLog -Encoding UTF8
        "" | Set-Content $backendErr -Encoding UTF8
        $script:BackendProc = Start-Process -FilePath $uvicorn `
            -ArgumentList @("app.main:app", "--host", "0.0.0.0", "--port", "$BackendPort") `
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

        Write-Step "7/9  Starting Next.js frontend on :$FrontendPort"
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

        Write-Step "8/9  Model Host pairing (optional)"
        $cfgNow = Get-Content $DeviceJson -Raw | ConvertFrom-Json
        $paired = @($cfgNow.paired_hosts)
        if ($paired.Count -gt 0) {
            Write-Ok ("Already paired: {0}" -f (($paired | ForEach-Object { $_.node_id }) -join ", "))
        } else {
            Write-Host "  No Model Host paired. Enter LAN address to pair now, or press Enter to skip." -ForegroundColor DarkCyan
            Write-Host "  Format:  <ip> <port> <pairing_code>   e.g. 192.168.1.20 8100 482913" -ForegroundColor Gray
            $line = Read-Host "  Pair"
            if ($line.Trim()) {
                $parts = $line.Trim() -split "\s+"
                if ($parts.Count -ge 3) {
                    & (Get-VenvPython) $PairPy $parts[0] $parts[1] $parts[2]
                    if ($LASTEXITCODE -eq 0) { Write-Ok "Paired successfully" }
                    else { Write-Warn "Pairing failed - you can retry later via scripts/pair_host.py" }
                } else {
                    Write-Warn "Need: address port code"
                }
            } else {
                Write-Info "Skipped pairing - VQA/captioning needs a Model Host with $HostVlmModel"
            }
        }

        Write-Step "9/9  Ready"
        @{
            role       = $role
            website    = $FrontendUrl
            backend    = $BackendUrl
            docs       = "$BackendUrl/docs"
            health     = "$BackendUrl/api/health"
            ollama     = $OllamaUrl
            planner    = $PlannerModel
            host_vlm   = $HostVlmModel
            logs       = $LogDir
            started_at = (Get-Date).ToString("s")
        } | ConvertTo-Json | Set-Content $StateFile -Encoding UTF8

        Write-Banner "SatQuery Controller / Full System is running"
        Write-Host ""
        Write-Host "  OPEN THE WEBSITE:" -ForegroundColor White
        Write-Host "  $FrontendUrl" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Backend API:   $BackendUrl" -ForegroundColor Gray
        Write-Host "  Role:          $role" -ForegroundColor Gray
        Write-Host "  Host VLM:      $HostVlmModel (on Model Host via /node/inference)" -ForegroundColor Gray
        Write-Host "  Logs:          $LogDir" -ForegroundColor Gray
        Write-Host "  Change role:   close this window and relaunch (asked every time)" -ForegroundColor DarkCyan
        Write-Host ""

        if (-not $SkipBrowser) {
            Write-Info "Opening browser..."
            Start-Process $FrontendUrl | Out-Null
        }

        Write-Host "  Leave this window open. Press Ctrl+C to stop (clears role + unloads models)." -ForegroundColor Yellow
        Write-Host "  Live analyze / remote-host traffic will appear below (from backend.log)." -ForegroundColor DarkCyan
        Write-Host ""

        # Mirror backend log into this console so Controllers see OUTGOING/INCOMING lines
        $logPos = 0
        while ($true) {
            Start-Sleep -Milliseconds 800
            if ($null -ne $script:BackendProc -and $script:BackendProc.HasExited) {
                Write-Fail ("Backend exited (code {0}). See {1}" -f $script:BackendProc.ExitCode, $backendErr)
                break
            }
            if ($null -ne $script:FrontendProc -and $script:FrontendProc.HasExited) {
                Write-Fail ("Frontend exited (code {0}). See {1}" -f $script:FrontendProc.ExitCode, $frontendErr)
                break
            }
            if (Test-Path $backendLog) {
                try {
                    $lines = Get-Content $backendLog -ErrorAction SilentlyContinue
                    if ($null -eq $lines) { $lines = @() }
                    if (-not ($lines -is [System.Array])) { $lines = @($lines) }
                    if ($lines.Count -gt $logPos) {
                        for ($i = $logPos; $i -lt $lines.Count; $i++) {
                            $line = [string]$lines[$i]
                            if ([string]::IsNullOrWhiteSpace($line)) { continue }
                            # Highlight remote traffic; still show other useful lines
                            if ($line -match "OUTGOING|INCOMING|Remote VLM|paired Model Host|No Model Host|analyze") {
                                Write-Host "  $line" -ForegroundColor Cyan
                            } elseif ($line -match "ERROR|Error|failed|WARNING") {
                                Write-Host "  $line" -ForegroundColor Yellow
                            }
                        }
                        $logPos = $lines.Count
                    }
                } catch {}
            }
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
    Invoke-CleanShutdown
}
