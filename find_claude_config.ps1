# Busca ampla por config MCP
Write-Host "Conteudo de claude-cli-nodejs:" -ForegroundColor Yellow
Get-ChildItem "$env:LOCALAPPDATA\claude-cli-nodejs" -Recurse -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "  $($_.FullName)" -ForegroundColor White }

Write-Host ""
Write-Host "Buscando 'metatrader' em AppData\Local..." -ForegroundColor Yellow
Get-ChildItem "$env:LOCALAPPDATA" -Recurse -Filter "*.json" -ErrorAction SilentlyContinue |
    Select-String "metatrader" -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "  $($_.Path)" -ForegroundColor Green }

Write-Host ""
Write-Host "Buscando 'mcpServers' em AppData\Local..." -ForegroundColor Yellow
Get-ChildItem "$env:LOCALAPPDATA" -Recurse -Filter "*.json" -ErrorAction SilentlyContinue |
    Select-String "mcpServers" -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "  $($_.Path)" -ForegroundColor Green }

Read-Host "Enter para fechar"
