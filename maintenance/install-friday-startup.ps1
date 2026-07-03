param(
  [switch]$Remove
)

$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$startup = [Environment]::GetFolderPath('Startup')
$cmdPath = Join-Path $startup 'Start FRIDAY.cmd'
$loginScript = Join-Path $Root 'maintenance\start-friday-on-login.ps1'

if ($Remove) {
  if (Test-Path $cmdPath) {
    Remove-Item -LiteralPath $cmdPath -Force
    Write-Host "Removed startup entry: $cmdPath"
  } else {
    Write-Host "Startup entry was not installed: $cmdPath"
  }
  exit 0
}

$content = @"
@echo off
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$loginScript"
"@

Set-Content -Encoding ASCII -Path $cmdPath -Value $content
Write-Host "Installed startup entry: $cmdPath"
Write-Host 'FRIDAY will start after Windows login. Remove it with:'
Write-Host "powershell -NoProfile -ExecutionPolicy Bypass -File `"$Root\maintenance\install-friday-startup.ps1`" -Remove"
