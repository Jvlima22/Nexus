# Localiza e cria/atualiza claude_desktop_config.json com credenciais MT5

$exe = "C:\Users\TGL Solutions\AppData\Roaming\Python\Python313\Scripts\metatrader-mcp-server.exe"

# Possíveis locais do config
$candidates = @(
    "$env:APPDATA\Claude\claude_desktop_config.json",
    "$env:LOCALAPPDATA\Claude\claude_desktop_config.json",
    "$env:USERPROFILE\AppData\Roaming\Claude\claude_desktop_config.json",
    "$env:USERPROFILE\AppData\Local\Claude\claude_desktop_config.json"
)

Write-Host "Procurando config existente..." -ForegroundColor Yellow
$configPath = $null
foreach ($c in $candidates) {
    if (Test-Path $c) {
        $configPath = $c
        Write-Host "Encontrado: $c" -ForegroundColor Green
        break
    }
}

# Se nao encontrou, lista todos os arquivos .json na pasta Claude
if (-not $configPath) {
    Write-Host "Nao encontrado nos caminhos padrao. Buscando..." -ForegroundColor Yellow
    $found = Get-ChildItem "$env:APPDATA\Claude" -Recurse -Filter "*.json" -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "Arquivos encontrados em $env:APPDATA\Claude:" -ForegroundColor Cyan
        $found | ForEach-Object { Write-Host "  $($_.FullName)" }
    } else {
        Write-Host "Pasta $env:APPDATA\Claude nao existe ou esta vazia." -ForegroundColor Red
    }

    $found2 = Get-ChildItem "$env:LOCALAPPDATA\Claude" -Recurse -Filter "*.json" -ErrorAction SilentlyContinue
    if ($found2) {
        Write-Host "Arquivos encontrados em $env:LOCALAPPDATA\Claude:" -ForegroundColor Cyan
        $found2 | ForEach-Object { Write-Host "  $($_.FullName)" }
    }

    # Cria na pasta padrao
    $configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
    $dir = Split-Path $configPath
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Pasta criada: $dir" -ForegroundColor Cyan
    }
}

# Monta o JSON
$config = @{
    mcpServers = @{
        metatrader = @{
            command = $exe
            args    = @("--login", "108960873", "--password", "H_3vClCm", "--server", "MetaQuotes-Demo", "--transport", "stdio")
        }
    }
}

$config | ConvertTo-Json -Depth 10 | Out-File $configPath -Encoding UTF8 -Force
Write-Host ""
Write-Host "Config salvo em: $configPath" -ForegroundColor Green
Write-Host "Feche e reabra o Cowork agora." -ForegroundColor Cyan
Read-Host "Enter para fechar"
