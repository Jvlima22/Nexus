<#
  NEXUS Trader - launcher unico.
  Sobe frontend + connector em paralelo e derruba tudo no Ctrl+C.

    Frontend   (Vite + React)     npm run dev        :5173
    Connector  (FastAPI + MT5)    python main.py     :8000

  Uso:
    npm start
    powershell -ExecutionPolicy Bypass -File start.ps1

  Requer: terminal MetaTrader 5 aberto e logado antes de rodar.
#>
param(
  [switch]$SkipConnector
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

function Fail($msg) {
  Write-Host "[NEXUS] ERRO: $msg" -ForegroundColor Red
  exit 1
}

# ---------------------------------------------------------------------------
# Preflight: node_modules
# ---------------------------------------------------------------------------
Write-Host "[NEXUS] Verificando pre-requisitos..." -ForegroundColor Yellow

if (-not (Test-Path (Join-Path $root "node_modules"))) {
  Write-Host "[NEXUS] node_modules ausente - instalando..." -ForegroundColor Yellow
  & npm install
}

# ---------------------------------------------------------------------------
# Preflight: Python + MetaTrader5
# ---------------------------------------------------------------------------
$connDir = Join-Path $root "connector"
$venvPy  = Join-Path $connDir ".venv\Scripts\python.exe"

if (-not $SkipConnector) {

  # Seleciona Python 3.10-3.12 (MT5 nao suporta 3.13+)
  $selectedPy = $null
  foreach ($ver in @("3.12", "3.11", "3.10")) {
    try {
      $null = & py -$ver --version 2>&1
      if ($LASTEXITCODE -eq 0) {
        $selectedPy = $ver
        Write-Host "[NEXUS] Python $ver encontrado." -ForegroundColor Cyan
        break
      }
    } catch { }
  }

  # Recria venv se estiver em Python 3.13
  $needsNewVenv = $false
  if (Test-Path $venvPy) {
    $venvVer = & $venvPy --version 2>&1
    if ($venvVer -match "3\.13") {
      if ($selectedPy) {
        Write-Host "[NEXUS] Venv 3.13 detectado - recriando com Python $selectedPy..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force (Join-Path $connDir ".venv")
        $needsNewVenv = $true
      } else {
        Write-Host "[NEXUS] AVISO: Python 3.10-3.12 nao encontrado. MT5 pode falhar em 3.13." -ForegroundColor Yellow
        Write-Host "        Instale: https://www.python.org/downloads/release/python-3119/" -ForegroundColor Yellow
      }
    }
  } else {
    $needsNewVenv = $true
  }

  if ($needsNewVenv) {
    Write-Host "[NEXUS] Criando venv..." -ForegroundColor Cyan
    if ($selectedPy) {
      & py -$selectedPy -m venv (Join-Path $connDir ".venv")
    } else {
      & python -m venv (Join-Path $connDir ".venv")
    }
  }

  # Instala dependencias
  Write-Host "[NEXUS] Instalando dependencias do connector..." -ForegroundColor Cyan
  & $venvPy -m pip install --quiet --upgrade pip
  & $venvPy -m pip install --quiet -r (Join-Path $connDir "requirements.txt")

  if ($LASTEXITCODE -ne 0) {
    Fail "Falha ao instalar dependencias do connector."
  }

  # Verifica MetaTrader5
  $mt5Check = & $venvPy -c "import MetaTrader5; print('ok')" 2>&1
  if ($mt5Check -eq "ok") {
    Write-Host "[NEXUS] MetaTrader5 OK." -ForegroundColor Green
  } else {
    Write-Host "[NEXUS] AVISO: MetaTrader5 nao importou: $mt5Check" -ForegroundColor Yellow
  }

  if (-not (Test-Path (Join-Path $connDir ".env"))) {
    Write-Host "[NEXUS] AVISO: connector/.env ausente." -ForegroundColor Yellow
  }
}

# ---------------------------------------------------------------------------
# Definicao dos servicos
# ---------------------------------------------------------------------------
$services = @()
$services += [pscustomobject]@{
  Name  = "WEB"
  Color = "Cyan"
  File  = "cmd.exe"
  Args  = "/c npm run dev"
  Wd    = $root
}
if (-not $SkipConnector) {
  $services += [pscustomobject]@{
    Name  = "CONNECTOR"
    Color = "Green"
    File  = $venvPy
    Args  = "-m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    Wd    = $connDir
  }
}

$script:procs = @()
$script:subs  = @()

function Stop-All {
  Write-Host "`n[NEXUS] Encerrando servicos..." -ForegroundColor Yellow
  foreach ($s in $script:subs) {
    Unregister-Event -SubscriptionId $s.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $s.Id -Force -ErrorAction SilentlyContinue
  }
  foreach ($p in $script:procs) {
    if ($p.Proc -and -not $p.Proc.HasExited) {
      & taskkill /PID $p.Proc.Id /T /F 2>$null | Out-Null
    }
  }
  Write-Host "[NEXUS] Tudo parado." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
try {
  foreach ($svc in $services) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = $svc.File
    $psi.Arguments              = $svc.Args
    $psi.WorkingDirectory       = $svc.Wd
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $proc.EnableRaisingEvents = $true

    $tag   = $svc.Name
    $color = $svc.Color
    $action = {
      if ($null -ne $EventArgs.Data) {
        $md = $Event.MessageData
        Write-Host ("[{0}] " -f $md.Tag) -ForegroundColor $md.Color -NoNewline
        Write-Host $EventArgs.Data
      }
    }
    $msg    = [pscustomobject]@{ Tag=$tag; Color=$color }
    $subOut = Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $action -MessageData $msg
    $subErr = Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived  -Action $action -MessageData $msg
    $script:subs += $subOut
    $script:subs += $subErr

    [void]$proc.Start()
    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()

    $script:procs += [pscustomobject]@{ Name=$tag; Proc=$proc }
    Write-Host ("[NEXUS] {0} iniciado (PID {1})" -f $tag, $proc.Id) -ForegroundColor $color
  }

  Write-Host ""
  Write-Host "[NEXUS] Frontend  -> http://localhost:5173" -ForegroundColor Cyan
  Write-Host "[NEXUS] Connector -> http://localhost:8000" -ForegroundColor Green
  Write-Host "[NEXUS] API Docs  -> http://localhost:8000/docs" -ForegroundColor Green
  Write-Host "[NEXUS] Ctrl+C para parar tudo." -ForegroundColor White
  Write-Host ""

  while ($true) {
    Start-Sleep -Milliseconds 600
    $dead = $script:procs | Where-Object { $_.Proc.HasExited }
    if ($dead) {
      foreach ($d in $dead) {
        Write-Host ("[NEXUS] {0} saiu (exit {1}). Encerrando os demais." -f $d.Name, $d.Proc.ExitCode) -ForegroundColor Red
      }
      break
    }
  }
}
finally {
  Stop-All
}
