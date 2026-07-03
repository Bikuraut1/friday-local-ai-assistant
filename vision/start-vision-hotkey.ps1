param(
  [switch]$Visible,
  [switch]$NoSpeak
)

$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Python = Join-Path $Root 'voice\.venv\Scripts\python.exe'
$Script = Join-Path $Root 'vision\analyze_screen.py'
$Logs = Join-Path $Root 'vision\logs'
$OutLog = Join-Path $Logs 'vision-hotkey.log'
$ErrLog = Join-Path $Logs 'vision-hotkey.err.log'

if (-not (Test-Path $Python)) {
  throw "Missing Python runtime: $Python"
}
if (-not (Test-Path $Script)) {
  throw "Missing vision script: $Script"
}

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*analyze_screen.py*--hotkey*'
}
foreach ($process in $existing) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

$argsList = @($Script, '--hotkey')
if ($NoSpeak) {
  $argsList += '--no-speak'
}

if ($Visible) {
  Start-Process -FilePath 'powershell.exe' -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy',
    'Bypass',
    '-Command',
    "Set-Location '$Root'; `$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; & '$Python' -u '$Script' --hotkey$(if ($NoSpeak) { ' --no-speak' } else { '' })"
  )
} else {
  Remove-Item -LiteralPath $OutLog,$ErrLog -Force -ErrorAction SilentlyContinue
  Start-Process -FilePath $Python `
    -ArgumentList $argsList `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog
}

Start-Sleep -Seconds 2
$running = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*analyze_screen.py*--hotkey*'
}
if (-not $running) {
  if (Test-Path $ErrLog) {
    Get-Content $ErrLog -Tail 40
  }
  throw 'FRIDAY vision hotkey did not start.'
}

Write-Host 'FRIDAY vision hotkey online. Press Win + Shift + F.'
