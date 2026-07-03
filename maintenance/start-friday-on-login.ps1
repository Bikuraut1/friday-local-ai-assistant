$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Logs = Join-Path $Root 'logs'
$StartScript = Join-Path $Root 'start-friday.ps1'

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $Logs "startup-$stamp.log"
$stdout = Join-Path $Logs "startup-$stamp.out.log"
$stderr = Join-Path $Logs "startup-$stamp.err.log"
$latest = Join-Path $Logs 'startup-latest.log'

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

try {
  $process = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $StartScript) `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

  @(
    "FRIDAY startup launched: $(Get-Date -Format s)"
    "Launcher PID: $($process.Id)"
    "stdout: $stdout"
    "stderr: $stderr"
    'Check FRIDAY health with: D:\Friday\maintenance\health-report.ps1'
  ) | Set-Content -Encoding UTF8 -Path $log

  Copy-Item -LiteralPath $log -Destination $latest -Force
  exit 0
} catch {
  "FRIDAY startup failed: $($_.Exception.Message)" | Add-Content -Encoding UTF8 -Path $log
  Copy-Item -LiteralPath $log -Destination $latest -Force
  exit 1
}
