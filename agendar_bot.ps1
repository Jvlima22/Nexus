# NEXUS Trader - Agendador de Tarefa Windows
# Execute este script como Administrador

$cmd = Get-Command python -ErrorAction SilentlyContinue
if ($cmd) {
    $pythonPath = $cmd.Source
} else {
    $pythonPath = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
}

$botScript = "C:\Users\TGL Solutions\Desktop\NEXUS\nexus_bot.py"
$logDir    = "C:\Users\TGL Solutions\Desktop\NEXUS\logs"
$taskName  = "NEXUS_Trader_Bot"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument """$botScript""" `
    -WorkingDirectory "C:\Users\TGL Solutions\Desktop\NEXUS"

$trigger = New-ScheduledTaskTrigger -Daily -At "04:00"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
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
    -Description "NEXUS Trader Bot - analise e execucao automatica diaria"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Tarefa registrada com sucesso!" -ForegroundColor Green
Write-Host "  Roda todo dia as 04:00 BRT (07:00 UTC)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Verificar: Agendador de Tarefas > Biblioteca" -ForegroundColor White
Write-Host "  Para testar agora rode:" -ForegroundColor White
Write-Host "  Start-ScheduledTask -TaskName NEXUS_Trader_Bot" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Enter para fechar"
