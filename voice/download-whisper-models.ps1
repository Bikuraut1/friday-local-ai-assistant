$ErrorActionPreference = 'Stop'

$Python = 'D:\Friday\voice\.venv\Scripts\python.exe'
$ModelRoot = 'D:\Friday\voice\whisper\models'

New-Item -ItemType Directory -Force -Path $ModelRoot | Out-Null

& $Python -c "import whisper; whisper.load_model('base.en', download_root=r'$ModelRoot'); print('base.en ready')"
& $Python -c "import whisper; whisper.load_model('medium.en', download_root=r'$ModelRoot'); print('medium.en ready')"

Get-ChildItem -LiteralPath $ModelRoot | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
