$ErrorActionPreference = 'Stop'

$Python = 'D:\Friday\voice\.venv\Scripts\python.exe'
$ModelRoot = 'D:\Friday\voice\wakewords\openwakeword'

New-Item -ItemType Directory -Force -Path $ModelRoot | Out-Null

& $Python -c "from openwakeword.utils import download_models; download_models(['hey_jarvis'], target_directory=r'$ModelRoot'); print('openWakeWord fallback ready')"

Get-ChildItem -LiteralPath $ModelRoot -Force | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
