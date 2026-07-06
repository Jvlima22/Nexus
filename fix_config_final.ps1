# Corrige claude_desktop_config.json para usar Python 3.13 (sem credenciais nos args)
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"

# Localiza metatrader-mcp-server.exe no Python 3.13
$candidates = @(
    "$env:APPDATA\Python\Python313\Scripts\metatrader-mcp-server.exe",
    "C:\Program Files\Python313\Scripts\metatrader-mcp-server.exe",
    "C:\Python313\Scripts\metatrader-mcp-server.exe"
)
$mcpExe = $null
foreach ($c in $candidates) {
    if (Test-Path $c) { $mcpExe = $c; break }
}
if (-not $mcpExe) {
    Write-Host "ERRO: metatrader-mcp-server.exe nao encontrado." -ForegroundColor Red
    Read-Host "Enter para fechar"
    exit 1
}
Write-Host "Encontrado: $mcpExe" -ForegroundColor Green

# Le config atual
$raw = Get-Content $configPath -Raw | ConvertFrom-Json

# Atualiza apenas mcpServers
$raw.mcpServers = [pscustomobject]@{
    metatrader = [pscustomobject]@{
        command = $mcpExe
        args    = @("--transport", "stdio")
    }
}

# Salva
$raw | ConvertTo-Json -Depth 10 | Out-File $configPath -Encoding UTF8 -Force
Write-Host "Config atualizado com: $mcpExe" -ForegroundColor Green
Write-Host ""
Write-Host "Agora: feche o Cowork, abra o MT5 (logado), reabra o Cowork." -ForegroundColor Cyan
Read-Host "Enter para fechar"
