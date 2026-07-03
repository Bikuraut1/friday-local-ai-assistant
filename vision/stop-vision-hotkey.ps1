$ErrorActionPreference = 'Stop'

$running = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*analyze_screen.py*--hotkey*'
}

foreach ($process in $running) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Host 'FRIDAY vision hotkey stopped.'
