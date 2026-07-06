# Substitui apenas mcpServers no backup original (sem reprocessar JSON inteiro)
$configPath = "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json"
$backup     = "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.backup.json"

# Le o backup original (JSON valido)
$content = [System.IO.File]::ReadAllText($backup, [System.Text.Encoding]::UTF8)

$mcpBlock = @'
"mcpServers": {
    "metatrader": {
      "command": "C:\\Users\\TGL Solutions\\AppData\\Roaming\\Python\\Python313\\Scripts\\metatrader-mcp-server.exe",
      "args": ["--login", "108960873", "--password", "H_3vClCm", "--server", "MetaQuotes-Demo", "--transport", "stdio"]
    }
  }
'@

# Substitui "mcpServers": {} pelo bloco correto
$newContent = $content -replace '"mcpServers":\s*\{\}', $mcpBlock

# Valida
try {
    $newContent | ConvertFrom-Json | Out-Null
    Write-Host "JSON valido!" -ForegroundColor Green
} catch {
    Write-Host "ERRO: $_ " -ForegroundColor Red
    Write-Host "Restaurando backup sem alteracao..." -ForegroundColor Yellow
    [System.IO.File]::WriteAllText($configPath, $content, (New-Object System.Text.UTF8Encoding $false))
    Read-Host "Enter"
    exit 1
}

# Salva sem BOM
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($configPath, $newContent, $utf8NoBom)

Write-Host "Salvo! Reabra o Cowork agora." -ForegroundColor Green
Read-Host "Enter"
