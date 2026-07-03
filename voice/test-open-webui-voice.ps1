$ErrorActionPreference = 'Stop'

$VoiceRoot = 'D:\Friday\voice'
$SpeechFile = Join-Path $VoiceRoot 'friday-openwebui-tts-test.mp3'
$TtsModel = if ($env:FRIDAY_TTS_MODEL) { $env:FRIDAY_TTS_MODEL } else { 'kokoro' }
$TtsVoice = if ($env:FRIDAY_TTS_VOICE) { $env:FRIDAY_TTS_VOICE } else { 'af_bella' }
$TtsFallbackVoice = if ($env:FRIDAY_TTS_FALLBACK_VOICE) { $env:FRIDAY_TTS_FALLBACK_VOICE } else { 'bf_emma' }
$AllowNonEnglishTts = ($env:FRIDAY_ALLOW_NON_ENGLISH_TTS -match '^(1|true|yes)$')
$SelectedTtsVoice = $null
$OpenWebUiEnv = 'D:\Friday\n8n\.env'

if (Test-Path $OpenWebUiEnv) {
  Get-Content $OpenWebUiEnv | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)\s*$') {
      [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), 'Process')
    }
  }
}

$OpenWebUiEmail = $env:FRIDAY_OPENWEBUI_EMAIL
$OpenWebUiPassword = $env:FRIDAY_OPENWEBUI_PASSWORD
if (-not $OpenWebUiEmail -or -not $OpenWebUiPassword) {
  throw 'Set FRIDAY_OPENWEBUI_EMAIL and FRIDAY_OPENWEBUI_PASSWORD in D:\Friday\n8n\.env.'
}

$SigninBody = @{
  email = $OpenWebUiEmail
  password = $OpenWebUiPassword
} | ConvertTo-Json

$Session = Invoke-RestMethod `
  -Uri 'http://localhost:3000/api/v1/auths/signin' `
  -Method Post `
  -Body $SigninBody `
  -ContentType 'application/json' `
  -TimeoutSec 30

$Headers = @{
  Authorization = "Bearer $($Session.token)"
}

foreach ($voice in (@($TtsVoice, $TtsFallbackVoice, 'af_bella') | Select-Object -Unique)) {
  if (-not $AllowNonEnglishTts -and $voice -notmatch '^[ab][fm]_') {
    Write-Host "Skipping non-English TTS voice for English speech: $voice"
    continue
  }
  try {
    $SpeechBody = @{
      model = $TtsModel
      voice = $voice
      input = 'Friday Indian English voice loop verification complete.'
    } | ConvertTo-Json

    Invoke-WebRequest `
      -UseBasicParsing `
      -Uri 'http://localhost:3000/api/v1/audio/speech' `
      -Method Post `
      -Headers $Headers `
      -Body $SpeechBody `
      -ContentType 'application/json' `
      -OutFile $SpeechFile `
      -TimeoutSec 120

    $SelectedTtsVoice = $voice
    break
  } catch {}
}

if (-not $SelectedTtsVoice) {
  throw 'No configured Open WebUI TTS voice worked.'
}

$Curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$TranscriptJson = & $Curl -sS `
  -X POST 'http://localhost:3000/api/v1/audio/transcriptions' `
  -H "Authorization: Bearer $($Session.token)" `
  -F "file=@$SpeechFile;type=audio/mpeg" `
  -F 'language=en'

if ($LASTEXITCODE -ne 0) {
  throw 'Open WebUI transcription request failed.'
}

$Transcript = $TranscriptJson | ConvertFrom-Json

$SpeechItem = Get-Item $SpeechFile
[ordered]@{
  tts_file = $SpeechItem.FullName
  tts_bytes = $SpeechItem.Length
  voice = $SelectedTtsVoice
  transcript = $Transcript.text
  status = ($SpeechItem.Length -gt 1000 -and $Transcript.text.Length -gt 0)
} | ConvertTo-Json
