$ErrorActionPreference = 'Stop'

$OutFile = 'D:\Friday\voice\friday-tts-test.mp3'
$TtsModel = if ($env:FRIDAY_TTS_MODEL) { $env:FRIDAY_TTS_MODEL } else { 'kokoro' }
$TtsVoice = if ($env:FRIDAY_TTS_VOICE) { $env:FRIDAY_TTS_VOICE } else { 'af_bella' }
$TtsFallbackVoice = if ($env:FRIDAY_TTS_FALLBACK_VOICE) { $env:FRIDAY_TTS_FALLBACK_VOICE } else { 'bf_emma' }
$AllowNonEnglishTts = ($env:FRIDAY_ALLOW_NON_ENGLISH_TTS -match '^(1|true|yes)$')
$SelectedTtsVoice = $null

$Body = @{
  model = $TtsModel
  voice = $TtsVoice
  input = 'FRIDAY text to speech verification complete in Indian English.'
  response_format = 'mp3'
} | ConvertTo-Json

foreach ($voice in (@($TtsVoice, $TtsFallbackVoice, 'af_bella') | Select-Object -Unique)) {
  if (-not $AllowNonEnglishTts -and $voice -notmatch '^[ab][fm]_') {
    Write-Host "Skipping non-English TTS voice for English speech: $voice"
    continue
  }
  try {
    $Body = @{
      model = $TtsModel
      voice = $voice
      input = 'FRIDAY text to speech verification complete in Indian English.'
      response_format = 'mp3'
    } | ConvertTo-Json

    Invoke-WebRequest `
      -UseBasicParsing `
      -Uri 'http://localhost:8880/v1/audio/speech' `
      -Method Post `
      -Body $Body `
      -ContentType 'application/json' `
      -OutFile $OutFile `
      -TimeoutSec 60

    $SelectedTtsVoice = $voice
    break
  } catch {}
}

if (-not $SelectedTtsVoice) {
  throw 'No configured Kokoro TTS voice worked.'
}

$Item = Get-Item $OutFile
[ordered]@{
  file = $Item.FullName
  bytes = $Item.Length
  voice = $SelectedTtsVoice
  status = ($Item.Length -gt 1000)
} | ConvertTo-Json
