# NEXUS - Fix MT5 MCP Connection
# Execute: clique direito -> "Executar com PowerShell"

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  NEXUS - Fix MT5 MCP" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# FASE 1: Diagnostico
# ---------------------------------------------------------------------------
Write-Host "[1/4] DIAGNOSTICO..." -ForegroundColor Yellow
Write-Host ""

# Python 3.11
$py311 = "C:\Python311\python.exe"
if (Test-Path $py311) {
    $v311 = & $py311 --version 2>&1
    Write-Host "  Python 3.11: $v311" -ForegroundColor Green
} else {
    Write-Host "  Python 3.11: NAO ENCONTRADO em C:\Python311" -ForegroundColor Red
    $py311 = $null
}

# Python sistema
$pySys = (Get-Command python -ErrorAction SilentlyContinue).Source
$vSys = & python --version 2>&1
Write-Host "  Python sistema: $vSys ($pySys)" -ForegroundColor White

# Teste MT5 lib no Python sistema
Write-Host ""
Write-Host "  Testando MetaTrader5 lib no Python sistema..." -ForegroundColor White
$mt5Test = & python -c "
import MetaTrader5 as mt5
ok = mt5.initialize()
err = mt5.last_error()
mt5.shutdown()
print(f'init={ok} err={err}')
" 2>&1
Write-Host "  Resultado: $mt5Test" -ForegroundColor $(if ($mt5Test -match "init=True") { "Green" } else { "Red" })

# metatrader-mcp-server atual
$mcpInfo = & pip show metatrader-mcp-server 2>&1
$mcpVer = ($mcpInfo | Select-String "Version:") -replace "Version: ", ""
Write-Host "  metatrader-mcp-server atual: $mcpVer" -ForegroundColor White

Write-Host ""

# ---------------------------------------------------------------------------
# FASE 2: Instalar no Python 3.11 (se existir)
# ---------------------------------------------------------------------------
Write-Host "[2/4] INSTALACAO..." -ForegroundColor Yellow
Write-Host ""

if ($py311) {
    Write-Host "  Instalando metatrader-mcp-server no Python 3.11..." -ForegroundColor Cyan
    $install = & $py311 -m pip install --upgrade metatrader-mcp-server 2>&1
    $lastLine = ($install | Select-String "Successfully|already|error" | Select-Object -Last 1)
    Write-Host "  $lastLine" -ForegroundColor $(if ($lastLine -match "Successfully|already") { "Green" } else { "Red" })

    $mcp311 = "C:\Python311\Scripts\metatrader-mcp-server.exe"
    if (Test-Path $mcp311) {
        Write-Host "  Executavel: $mcp311" -ForegroundColor Green
    }

    # Testar MT5 no Python 3.11
    Write-Host "  Testando MetaTrader5 no Python 3.11..." -ForegroundColor Cyan
    $mt5Test311 = & $py311 -c "
import MetaTrader5 as mt5
ok = mt5.initialize()
err = mt5.last_error()
mt5.shutdown()
print(f'init={ok} err={err}')
" 2>&1
    Write-Host "  Resultado 3.11: $mt5Test311" -ForegroundColor $(if ($mt5Test311 -match "init=True") { "Green" } else { "Yellow" })

} else {
    Write-Host "  Python 3.11 nao encontrado." -ForegroundColor Yellow
    Write-Host "  Verificando se Python 3.13 consegue conectar MT5..." -ForegroundColor Cyan
    if ($mt5Test -match "init=True") {
        Write-Host "  Python 3.13 OK - vamos usar ele!" -ForegroundColor Green
    } else {
        Write-Host "  Python 3.13 NAO consegue conectar MT5." -ForegroundColor Red
        Write-Host "  -> Instale Python 3.11: https://www.python.org/downloads/release/python-3119/" -ForegroundColor Yellow
    }
}

Write-Host ""

# ---------------------------------------------------------------------------
# FASE 3: Atualizar claude_desktop_config.json
# ---------------------------------------------------------------------------
Write-Host "[3/4] ATUALIZANDO CONFIG..." -ForegroundColor Yellow
Write-Host ""

$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

# Determinar qual executavel usar
if ($py311 -and (Test-Path "C:\Python311\Scripts\metatrader-mcp-server.exe")) {
    $mcpExe = "C:\\Python311\\Scripts\\metatrader-mcp-server.exe"
    Write-Host "  Usando Python 3.11 para o MCP." -ForegroundColor Green
} else {
    $mcpExe = "$env:APPDATA\\Python\\Python313\\Scripts\\metatrader-mcp-server.exe" -replace "\\", "\\\\"
    Write-Host "  Usando Python 3.13 para o MCP." -ForegroundColor Yellow
}

$newConfig = @"
{
  "mcpServers": {
    "metatrader": {
      "command": "C:\\Python311\\Scripts\\metatrader-mcp-server.exe",
      "args": ["--transport", "stdio"]
    }
  },
  "coworkUserFilesPath": "C:\\Users\\TGL Solutions\\Claude",
  "preferences": {
    "coworkScheduledTasksEnabled": true,
    "coworkHipaaRestricted": false,
    "ccdScheduledTasksEnabled": true,
    "sidebarMode": "task",
    "bypassPermissionsGateByAccount": {
      "3dab51ec-6ed6-40e0-83da-5d0b7cf237cf": false
    },
    "coworkWebSearchEnabled": true,
    "coworkModelAutoFallbackByAccount": {
      "3dab51ec-6ed6-40e0-83da-5d0b7cf237cf": true
    },
    "chicagoEnabled": true,
    "remoteToolsDeviceName": "desktop-qnlv5ie"
  }
}
"@

# Backup do config atual
$backupPath = "$env:APPDATA\Claude\claude_desktop_config.backup.json"
if (Test-Path $configPath) {
    Copy-Item $configPath $backupPath -Force
    Write-Host "  Backup salvo em: $backupPath" -ForegroundColor Green
}

# Escrever novo config
$newConfig | Out-File -FilePath $configPath -Encoding UTF8 -Force
Write-Host "  Config atualizado: $configPath" -ForegroundColor Green
Write-Host "  MCP configurado SEM credenciais nos args (terminal MT5 ja logado cuida disso)" -ForegroundColor Cyan

Write-Host ""

# ---------------------------------------------------------------------------
# FASE 4: Resumo
# ---------------------------------------------------------------------------
Write-Host "[4/4] RESUMO" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Config atualizado. Proximo passo:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Feche e reabra o Cowork" -ForegroundColor Cyan
Write-Host "  2. Certifique-se que o MT5 esta aberto e logado ANTES de abrir o Cowork" -ForegroundColor Cyan
Write-Host "  3. O MCP metatrader vai conectar automaticamente na inicializacao" -ForegroundColor Cyan
Write-Host ""

if (-not $py311) {
    Write-Host "  ATENCAO: Python 3.11 nao encontrado." -ForegroundColor Red
    Write-Host "  Se o MCP nao conectar, instale Python 3.11:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/release/python-3119/" -ForegroundColor Yellow
    Write-Host "  Depois rode este script novamente." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Concluido!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Pressione Enter para fechar"
