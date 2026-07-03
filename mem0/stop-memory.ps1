$ErrorActionPreference = 'Continue'

$Root = 'D:\Friday'
$Mem0Root = Join-Path $Root 'mem0'
$PidFile = Join-Path $Mem0Root 'bridge\memory-bridge.pid'
$Compose = Join-Path $Mem0Root 'docker-compose.yml'

if (Test-Path $PidFile) {
  $pidValue = Get-Content $PidFile | Select-Object -First 1
  if ($pidValue) {
    Stop-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
  }
  Remove-Item $PidFile -ErrorAction SilentlyContinue
}

$bridgeProcesses = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*bridge.memory_bridge*'
}

foreach ($process in $bridgeProcesses) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

docker compose -f $Compose stop
Write-Host 'FRIDAY memory services stopped.'
if ($bridgeProcesses) {
  Write-Host 'Memory bridge process stopped.'
}
