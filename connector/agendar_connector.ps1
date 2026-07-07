# NEXUS Connector - Agenda o servico (IQ Option + MT5, porta 8010) para iniciar com o Windows
# Execute como Administrador

$taskName  = "NEXUS_Connector"
$vbsScript = "C:\Users\TGL Solutions\Desktop\NEXUS\connector\iniciar_connector.vbs"

$action = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument """$vbsScript"""

# Dispara no login do usuario atual, um pouco depois do bot MT5 (que tem delay de 30s)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT45S"

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

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "NEXUS Connector (IQ Option + MT5, porta 8010) - inicia automaticamente ao fazer login"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NEXUS Connector registrado!" -ForegroundColor Green
Write-Host "  Inicia automaticamente ao ligar o PC (porta 8010)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Para iniciar agora sem reiniciar:" -ForegroundColor White
Write-Host "  Start-ScheduledTask -TaskName NEXUS_Connector" -ForegroundColor Gray
Write-Host ""
Write-Host "  Logs em: connector\_connector_run.log / _connector_err.log" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
