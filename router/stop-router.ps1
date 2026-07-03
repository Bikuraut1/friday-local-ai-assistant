$ErrorActionPreference = 'Stop'

$running = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*model_router.py*serve*'
}

foreach ($process in $running) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host 'FRIDAY router stopped.'
