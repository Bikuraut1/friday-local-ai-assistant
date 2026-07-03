$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$Python = Join-Path $Root 'voice\.venv\Scripts\python.exe'
$Script = Join-Path $Root 'vision\analyze_screen.py'
$TtsModel = if ($env:FRIDAY_TTS_MODEL) { $env:FRIDAY_TTS_MODEL } else { 'kokoro' }
$TtsVoice = if ($env:FRIDAY_TTS_VOICE) { $env:FRIDAY_TTS_VOICE } else { 'af_bella' }
$TtsFallbackVoice = if ($env:FRIDAY_TTS_FALLBACK_VOICE) { $env:FRIDAY_TTS_FALLBACK_VOICE } else { 'bf_emma' }
$AllowNonEnglishTts = ($env:FRIDAY_ALLOW_NON_ENGLISH_TTS -match '^(1|true|yes)$')
$SelectedTtsVoice = $null

Write-Host '1. Verify llava:13b is installed'
$models = Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 10
$visionModel = $models.models | Where-Object { $_.name -eq 'llava:13b' }
if (-not $visionModel) {
  throw 'llava:13b is not installed in Ollama.'
}
$visionModel | Select-Object name, size

Write-Host '2. Verify Kokoro TTS'
foreach ($voice in (@($TtsVoice, $TtsFallbackVoice, 'af_bella') | Select-Object -Unique)) {
  if (-not $AllowNonEnglishTts -and $voice -notmatch '^[ab][fm]_') {
    Write-Host "Skipping non-English TTS voice for English speech: $voice"
    continue
  }
  try {
    $body = @{
      model = $TtsModel
      voice = $voice
      input = 'FRIDAY vision verification in Indian English.'
      response_format = 'wav'
    } | ConvertTo-Json
    $tts = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8880/v1/audio/speech' -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 60
    $SelectedTtsVoice = $voice
    break
  } catch {}
}
if (-not $SelectedTtsVoice) {
  throw 'No configured Kokoro TTS voice worked.'
}
if ($tts.RawContentLength -lt 1000) {
  throw 'Kokoro TTS returned too little audio data.'
}
Write-Host "Kokoro TTS voice: $SelectedTtsVoice bytes: $($tts.RawContentLength)"

Write-Host '3. Capture screen and analyze with llava:13b'
& $Python $Script --no-speak --prompt "Analyze what's on my screen. If a document or UI is visible, summarize the key visible text in 3 concise bullets."
if ($LASTEXITCODE -ne 0) {
  throw 'Vision screenshot analysis failed.'
}

Write-Host 'Phase 9 vision verification passed.'
