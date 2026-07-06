# NEXUS Trader - Agenda bot para iniciar com o Windows (ao fazer login)
# Execute como Administrador

$taskName   = "NEXUS_Trader_24H"
$vbsScript  = "C:\Users\TGL Solutions\Desktop\NEXUS\iniciar_bot.vbs"

# Acao: rodar o VBScript (inicia o bot sem janela)
$action = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument """$vbsScript"""

# Dispara no login do usuario atual
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Aguarda 30s apos login para o Windows estabilizar
$trigger.Delay = "PT30S"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# Remove versao anterior se existir
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
# Remove tambem a tarefa diaria antiga se existir
Unregister-ScheduledTask -TaskName "NEXUS_Trader_Bot" -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "NEXUS Trader Bot 24H - inicia automaticamente ao fazer login"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NEXUS 24H registrado!" -ForegroundColor Green
Write-Host "  Inicia automaticamente ao ligar o PC" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Para iniciar agora sem reiniciar:" -ForegroundColor White
Write-Host "  Start-ScheduledTask -TaskName NEXUS_Trader_24H" -ForegroundColor Gray
Write-Host ""
Write-Host "  Logs em: NEXUS\logs\" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Enter para fechar"
