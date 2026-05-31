$ErrorActionPreference = 'SilentlyContinue'
try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $j = $raw | ConvertFrom-Json

    $file = $null
    if ($j.tool_response -and $j.tool_response.filePath) {
        $file = $j.tool_response.filePath
    }
    if (-not $file -and $j.tool_input -and $j.tool_input.file_path) {
        $file = $j.tool_input.file_path
    }
    if (-not $file) { exit 0 }

    $vault = 'C:\Users\TGL Solutions\Desktop\NEXUS\NEXUS'
    $projRoot = 'C:\Users\TGL Solutions\Desktop\NEXUS'

    # Skip writes inside the vault itself (avoid noise/recursion)
    if ($file -like "$vault*") { exit 0 }
    # Skip .claude internals
    if ($file -like "*\.claude\*") { exit 0 }
    # Skip node_modules
    if ($file -like "*\node_modules\*") { exit 0 }
    # Skip the memory directory
    if ($file -like "*\memory\*") { exit 0 }

    $diary = Join-Path $vault "40_Registros\Diario\$(Get-Date -Format 'yyyy-MM-dd').md"

    # If diary doesn't exist yet (SessionStart hasn't run or new day), create skeleton
    if (-not (Test-Path $diary)) {
        $diaryDir = Split-Path $diary -Parent
        if (-not (Test-Path $diaryDir)) {
            New-Item -ItemType Directory -Force -Path $diaryDir | Out-Null
        }
        $date = Get-Date -Format 'yyyy-MM-dd'
        $skeleton = @"
---
tipo: diario
data: $date
tags:
  - registro/diario
---

# $date

## O que foi feito


## Tocado hoje (auto-log)


## Decisões


## Exclusões


## Bloqueios / pendências


## Aprendizados

"@
        $skeleton | Out-File -FilePath $diary -Encoding utf8
    }

    # Build the log line
    $rel = $file
    if ($file.StartsWith($projRoot + '\')) {
        $rel = $file.Substring($projRoot.Length + 1)
    }
    $time = Get-Date -Format 'HH:mm'
    $tool = $j.tool_name
    if (-not $tool) { $tool = '?' }
    $line = "- $time ``[$tool]`` ``$rel``"

    # Insert line under "## Tocado hoje (auto-log)" header (idempotent append below it)
    $lines = Get-Content -Path $diary -Encoding utf8
    $headerIdx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^##\s+Tocado hoje') {
            $headerIdx = $i
            break
        }
    }

    if ($headerIdx -ge 0) {
        # Find end of this section (next header or end of file)
        $insertIdx = $lines.Count
        for ($k = $headerIdx + 1; $k -lt $lines.Count; $k++) {
            if ($lines[$k] -match '^##\s+') {
                $insertIdx = $k
                break
            }
        }
        # Walk back past trailing blank lines to find true end of section
        while ($insertIdx -gt $headerIdx + 1 -and [string]::IsNullOrWhiteSpace($lines[$insertIdx - 1])) {
            $insertIdx--
        }
        $newLines = @()
        if ($insertIdx -gt 0) { $newLines += $lines[0..($insertIdx - 1)] }
        $newLines += $line
        if ($insertIdx -lt $lines.Count) { $newLines += $lines[$insertIdx..($lines.Count - 1)] }
        $newLines -join "`r`n" | Out-File -FilePath $diary -Encoding utf8
    } else {
        # Header not found — just append at end
        Add-Content -Path $diary -Value $line -Encoding utf8
    }
} catch {
    exit 0
}
exit 0
