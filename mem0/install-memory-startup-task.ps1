$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$TaskName = 'FRIDAY Memory Bridge'
$StartupScript = Join-Path $Root 'mem0\start-memory-on-login.ps1'

if (-not (Test-Path $StartupScript)) {
  throw "Missing startup script: $StartupScript"
}

$action = New-ScheduledTaskAction `
  -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$StartupScript`"" `
  -WorkingDirectory $Root

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -StartWhenAvailable

$principal = New-ScheduledTaskPrincipal `
  -UserId "$env:USERDOMAIN\$env:USERNAME" `
  -LogonType Interactive `
  -RunLevel Limited

try {
  Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description 'Starts FRIDAY Mem0 memory bridge, Qdrant, Docker, and Ollama at Windows logon.' `
    -Force | Out-Null

  Write-Host "Installed scheduled task: $TaskName"
  Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName,State
} catch {
  $startupFolder = [Environment]::GetFolderPath('Startup')
  $cmdSource = Join-Path $Root 'mem0\FRIDAY-Memory-Startup.cmd'
  $cmdTarget = Join-Path $startupFolder 'FRIDAY Memory Bridge.cmd'

  if (-not (Test-Path $cmdSource)) {
    throw "Task Scheduler failed and fallback launcher is missing: $cmdSource"
  }

  Copy-Item -LiteralPath $cmdSource -Destination $cmdTarget -Force
  Write-Host "Task Scheduler unavailable: $($_.Exception.Message)"
  Write-Host "Installed Startup folder fallback: $cmdTarget"
}
