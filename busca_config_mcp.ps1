# Busca ampla pelo arquivo de config do MCP no Cowork/Claude app
$out = @()

$out += "=== BUSCA CONFIG MCP COWORK ==="
$out += ""

# 1. Verifica pastas do app Claude (MSIX/UWP)
$out += "--- Pacotes Claude ---"
$pkgs = Get-ChildItem "$env:LOCALAPPDATA\Packages" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*Claude*" }
foreach ($p in $pkgs) {
    $out += "Pacote: $($p.FullName)"
    Get-ChildItem $p.FullName -Recurse -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        $out += "  JSON: $($_.FullName)"
        if (Select-String -Path $_.FullName -Pattern "mcp|metatrader|mcpServer" -Quiet -ErrorAction SilentlyContinue) {
            $out += "  *** CONTÉM MCP CONFIG ***"
            $out += (Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue)
        }
    }
}

# 2. claude-cli-nodejs
$out += ""
$out += "--- claude-cli-nodejs ---"
$cliPath = "$env:LOCALAPPDATA\claude-cli-nodejs"
if (Test-Path $cliPath) {
    Get-ChildItem $cliPath -Recurse -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        $out += "  JSON: $($_.FullName)"
        if (Select-String -Path $_.FullName -Pattern "mcp|metatrader|mcpServer" -Quiet -ErrorAction SilentlyContinue) {
            $out += "  *** CONTÉM MCP CONFIG ***"
            $out += (Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue)
        }
    }
}

# 3. AppData\Roaming\Claude
$out += ""
$out += "--- AppData Roaming Claude ---"
$roamPath = "$env:APPDATA\Claude"
if (Test-Path $roamPath) {
    Get-ChildItem $roamPath -Recurse -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        $out += "  JSON: $($_.FullName)"
        if (Select-String -Path $_.FullName -Pattern "mcp|metatrader|mcpServer" -Quiet -ErrorAction SilentlyContinue) {
            $out += "  *** CONTÉM MCP CONFIG ***"
            $out += (Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue)
        }
    }
    # Busca .db e .sqlite
    Get-ChildItem $roamPath -Recurse -Include "*.db","*.sqlite","*.sqlite3" -ErrorAction SilentlyContinue | ForEach-Object {
        $out += "  DB: $($_.FullName)"
    }
}

# 4. Busca por "metatrader" em todos os JSONs do AppData
$out += ""
$out += "--- Busca global por metatrader ---"
Get-ChildItem "$env:APPDATA" -Recurse -Filter "*.json" -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -lt 1MB } |
    Select-String "metatrader" -ErrorAction SilentlyContinue |
    ForEach-Object { $out += "  $($_.Path)" }

Get-ChildItem "$env:LOCALAPPDATA" -Recurse -Filter "*.json" -ErrorAction SilentlyContinue |
    Where-Object { $_.Length -lt 1MB } |
    Select-String "metatrader" -ErrorAction SilentlyContinue |
    ForEach-Object { $out += "  $($_.Path)" }

# Salva resultado
$result = $out -join "`n"
$result | Out-File "C:\Users\TGL Solutions\Desktop\NEXUS\resultado_busca_mcp.txt" -Encoding UTF8 -Force
Write-Host $result
Read-Host "Enter para fechar"
