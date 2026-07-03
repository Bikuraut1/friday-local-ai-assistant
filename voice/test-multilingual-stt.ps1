param(
  [Parameter(Mandatory = $true)]
  [string]$EnglishWav,

  [Parameter(Mandatory = $true)]
  [string]$HindiWav,

  [Parameter(Mandatory = $true)]
  [string]$HinglishWav,

  [string]$Model = "medium",
  [string]$Language = "auto"
)

$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Python = Join-Path $Root 'voice\.venv\Scripts\python.exe'
$Script = Join-Path $Root 'voice\test_multilingual_stt.py'

if (-not (Test-Path $Python)) {
  throw "Missing Python runtime: $Python"
}
if (-not (Test-Path $Script)) {
  throw "Missing test helper: $Script"
}

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:FRIDAY_STT_ENGINE = 'local'
$env:FRIDAY_LOCAL_WHISPER_MODEL = $Model
$env:FRIDAY_STT_LANGUAGE = $Language

& $Python $Script `
  --english $EnglishWav `
  --hindi $HindiWav `
  --hinglish $HinglishWav `
  --model $Model `
  --language $Language
