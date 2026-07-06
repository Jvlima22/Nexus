# Atualiza mcpServers no claude_desktop_config real do Cowork (UWP)
$configPath = "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json"

if (-not (Test-Path $configPath)) {
    Write-Host "ERRO: Arquivo nao encontrado em $configPath" -ForegroundColor Red
    Read-Host "Enter"
    exit 1
}

# Backup
$backup = $configPath -replace "\.json$", ".backup.json"
Copy-Item $configPath $backup -Force
Write-Host "Backup salvo: $backup" -ForegroundColor Green

# Le e parseia
$raw = Get-Content $configPath -Raw -Encoding UTF8
$json = $raw | ConvertFrom-Json

# Atualiza mcpServers
$json.mcpServers = [PSCustomObject]@{
    metatrader = [PSCustomObject]@{
        command = "C:\Users\TGL Solutions\AppData\Roaming\Python\Python313\Scripts\metatrader-mcp-server.exe"
        args = @("--login", "108960873", "--password", "H_3vClCm", "--server", "MetaQuotes-Demo", "--transport", "stdio")
    }
}

# Salva com indentacao
$json | ConvertTo-Json -Depth 20 | Out-File $configPath -Encoding UTF8 -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " mcpServers atualizado com sucesso!" -ForegroundColor Green
Write-Host " Feche o Cowork e reabra com MT5 aberto" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Mostra o resultado
Write-Host "Config atual:" -ForegroundColor White
Get-Content $configPath | Select-Object -First 15
Write-Host ""
Read-Host "Enter para fechar"
