$ErrorActionPreference = 'SilentlyContinue'
try {
    $vault = 'C:\Users\TGL Solutions\Desktop\NEXUS\NEXUS'
    $date = Get-Date -Format 'yyyy-MM-dd'
    $diary = Join-Path $vault "40_Registros\Diario\$date.md"

    if (-not (Test-Path $diary)) {
        $dir = Split-Path $diary -Parent
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
        $content = @"
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
        $content | Out-File -FilePath $diary -Encoding utf8
    }
} catch {
    exit 0
}
exit 0
