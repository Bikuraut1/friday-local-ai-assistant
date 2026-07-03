$ErrorActionPreference = 'Stop'

$KokoroCompose = 'D:\Friday\voice\kokoro\docker-compose.yml'

$wakeProcesses = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*wake_listener.py*'
}

$visualizerProcesses = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python|pythonw' -and $_.CommandLine -like '*voice_visualizer.py*'
}

foreach ($process in $wakeProcesses) {
  Stop-Process -Id $process.ProcessId -Force
}

foreach ($process in $visualizerProcesses) {
  Stop-Process -Id $process.ProcessId -Force
}

docker compose -f $KokoroCompose stop
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to stop Kokoro TTS.'
}

Write-Host 'FRIDAY voice services stopped.'
if ($wakeProcesses) {
  Write-Host 'Wake listener stopped.'
}
if ($visualizerProcesses) {
  Write-Host 'Voice visualizer stopped.'
}
