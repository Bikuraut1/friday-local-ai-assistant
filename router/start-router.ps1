param(
  [switch]$Visible
)

$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Python = Join-Path $Root 'voice\.venv\Scripts\python.exe'
$Script = Join-Path $Root 'router\model_router.py'
$Logs = Join-Path $Root 'router\logs'
$OutLog = Join-Path $Logs 'router.log'
$ErrLog = Join-Path $Logs 'router.err.log'

if (-not (Test-Path $Python)) {
  throw "Missing Python runtime: $Python"
}
if (-not (Test-Path $Script)) {
  throw "Missing router script: $Script"
}

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python' -and $_.CommandLine -like '*model_router.py*serve*'
}
foreach ($process in $existing) {
  Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

if ($Visible) {
  Start-Process -FilePath 'powershell.exe' -ArgumentList @(
    '-NoExit',
    '-ExecutionPolicy',
    'Bypass',
    '-Command',
    "Set-Location '$Root'; `$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; & '$Python' -u '$Script' serve"
  )
} else {
  Remove-Item -LiteralPath $OutLog,$ErrLog -Force -ErrorAction SilentlyContinue
  Start-Process -FilePath $Python `
    -ArgumentList @($Script, 'serve') `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog
}

$deadline = (Get-Date).AddSeconds(90)
do {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8790/health' -TimeoutSec 15
    if ($response.StatusCode -eq 200) {
      Write-Host 'FRIDAY router online: http://localhost:8790'
      exit 0
    }
  } catch {}
  Start-Sleep -Seconds 1
} while ((Get-Date) -lt $deadline)

if (Test-Path $ErrLog) {
  Get-Content $ErrLog -Tail 80
}
throw 'FRIDAY router did not become healthy.'
