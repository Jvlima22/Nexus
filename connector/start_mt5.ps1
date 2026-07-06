# NEXUS MT5 Connector — startup script
# Uso: .\start_mt5.ps1
# Requer: Python 3.10–3.12 (64-bit), terminal MT5 aberto e logado.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Verifica se .env existe
if (-not (Test-Path ".env")) {
    Write-Host "[ERRO] Arquivo .env não encontrado. Copie .env.example e preencha." -ForegroundColor Red
    exit 1
}

# ── Seleciona Python compatível (MT5 lib suporta 3.7–3.12) ──────────────────
# Tenta: py -3.12 > py -3.11 > py -3.10 > python (sistema)
$PythonExe = $null
foreach ($ver in @("3.12", "3.11", "3.10")) {
    try {
        $test = & py -$ver --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $PythonExe = "py -$ver"
            Write-Host "[NEXUS] Python $ver encontrado." -ForegroundColor Cyan
            break
        }
    } catch { }
}

if (-not $PythonExe) {
    # Fallback: python do sistema (pode ser 3.13 — tenta mesmo assim)
    $sysVer = & python --version 2>&1
    Write-Host "[AVISO] Python 3.10/3.11/3.12 não encontrado. Usando: $sysVer" -ForegroundColor Yellow
    Write-Host "         MetaTrader5 pode falhar em Python 3.13+." -ForegroundColor Yellow
    Write-Host "         Instale Python 3.11: https://www.python.org/downloads/release/python-3119/" -ForegroundColor Yellow
    $PythonExe = "python"
}

# ── Cria/recria venv se necessário ──────────────────────────────────────────
$VenvPython = ".\.venv\Scripts\python.exe"
$NeedsNewVenv = $false

if (Test-Path $VenvPython) {
    # Verifica se o venv é Python 3.13 (incompatível)
    $venvVer = & $VenvPython --version 2>&1
    if ($venvVer -match "3\.13") {
        Write-Host "[NEXUS] Venv com Python 3.13 detectado — recriando com versão compatível..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force ".venv"
        $NeedsNewVenv = $true
    }
} else {
    $NeedsNewVenv = $true
}

if ($NeedsNewVenv) {
    Write-Host "[NEXUS] Criando ambiente virtual..." -ForegroundColor Cyan
    if ($PythonExe -eq "python") {
        python -m venv .venv
    } else {
        $verNum = $PythonExe -replace "py -", ""
        & py -$verNum -m venv .venv
    }
}

# ── Instala dependências ─────────────────────────────────────────────────────
Write-Host "[NEXUS] Instalando dependências..." -ForegroundColor Cyan
& $VenvPython -m pip install --quiet --upgrade pip
& $VenvPython -m pip install --quiet -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao instalar dependências. Verifique o requirements.txt." -ForegroundColor Red
    exit 1
}

# ── Verifica MetaTrader5 ─────────────────────────────────────────────────────
Write-Host "[NEXUS] Verificando MetaTrader5..." -ForegroundColor Cyan
$mt5Check = & $VenvPython -c "import MetaTrader5; print('ok')" 2>&1
if ($mt5Check -ne "ok") {
    Write-Host "[ERRO] MetaTrader5 não instalou: $mt5Check" -ForegroundColor Red
    Write-Host ""
    Write-Host "Soluções:" -ForegroundColor Yellow
    Write-Host "  1. Instale Python 3.11 (64-bit): https://www.python.org/downloads/release/python-3119/" -ForegroundColor Yellow
    Write-Host "  2. Rode: .\.venv\Scripts\pip install MetaTrader5" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   NEXUS MT5 Connector — OK               ║" -ForegroundColor Green
Write-Host "║   http://localhost:8000                  ║" -ForegroundColor Green
Write-Host "║   Docs: http://localhost:8000/docs       ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ── Sobe o servidor ──────────────────────────────────────────────────────────
& $VenvPython -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
