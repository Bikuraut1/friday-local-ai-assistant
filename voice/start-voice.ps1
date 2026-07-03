$ErrorActionPreference = 'Stop'

$Root = 'D:\Friday'
$VoiceRoot = Join-Path $Root 'voice'
$KokoroCompose = Join-Path $VoiceRoot 'kokoro\docker-compose.yml'
$OpenWebUICompose = Join-Path $Root 'open-webui\docker-compose.yml'
$Python = Join-Path $VoiceRoot '.venv\Scripts\python.exe'
$WakeListener = Join-Path $VoiceRoot 'wake_listener.py'
$Visualizer = Join-Path $VoiceRoot 'voice_visualizer.py'
$WakeLog = Join-Path $Root 'logs\wake-listener.log'
$WakeErrLog = Join-Path $Root 'logs\wake-listener.err.log'
$VisualizerLog = Join-Path $Root 'logs\voice-visualizer.log'
$VisualizerErrLog = Join-Path $Root 'logs\voice-visualizer.err.log'
$TtsModel = if ($env:FRIDAY_TTS_MODEL) { $env:FRIDAY_TTS_MODEL } else { 'kokoro' }
$TtsVoice = if ($env:FRIDAY_TTS_VOICE) { $env:FRIDAY_TTS_VOICE } else { 'af_bella' }
$TtsFallbackVoice = if ($env:FRIDAY_TTS_FALLBACK_VOICE) { $env:FRIDAY_TTS_FALLBACK_VOICE } else { 'bf_emma' }
$AllowNonEnglishTts = ($env:FRIDAY_ALLOW_NON_ENGLISH_TTS -match '^(1|true|yes)$')
$SelectedTtsVoice = $null

New-Item -ItemType Directory -Force -Path (Join-Path $VoiceRoot 'wakewords') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $VoiceRoot 'recordings') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'open-webui\data\cache\whisper\models') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null

docker compose -f $KokoroCompose up -d
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to start Kokoro TTS.'
}

$deadline = (Get-Date).AddSeconds(180)
do {
  foreach ($voice in (@($TtsVoice, $TtsFallbackVoice, 'af_bella') | Select-Object -Unique)) {
    if (-not $AllowNonEnglishTts -and $voice -notmatch '^[ab][fm]_') {
      Write-Host "Skipping non-English TTS voice for English speech: $voice"
      continue
    }
    try {
      $body = @{
        model = $TtsModel
        voice = $voice
        input = 'FRIDAY voice system online.'
        response_format = 'mp3'
      } | ConvertTo-Json

      $response = Invoke-WebRequest `
        -UseBasicParsing `
        -Uri 'http://localhost:8880/v1/audio/speech' `
        -Method Post `
        -Body $body `
        -ContentType 'application/json' `
        -TimeoutSec 20

      if ($response.StatusCode -eq 200 -and $response.RawContentLength -gt 1000) {
        $SelectedTtsVoice = $voice
        break
      }
    } catch {}
  }
  if ($SelectedTtsVoice) {
    break
  }
  Start-Sleep -Seconds 4
} while ((Get-Date) -lt $deadline)

if ((Get-Date) -ge $deadline) {
  docker logs --tail 120 friday-kokoro
  throw 'Kokoro TTS did not become ready.'
}

docker compose -f $OpenWebUICompose up -d --force-recreate
if ($LASTEXITCODE -ne 0) {
  throw 'Failed to recreate Open WebUI with Phase 6 voice settings.'
}

$deadline = (Get-Date).AddSeconds(180)
do {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:3000/health' -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
      $wakeProcess = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match 'python' -and $_.CommandLine -like '*wake_listener.py*'
      } | Select-Object -First 1

      if (-not $wakeProcess) {
        if (-not (Test-Path $Python)) {
          throw "Python environment not found: $Python"
        }
        if (-not (Test-Path $WakeListener)) {
          throw "Wake listener not found: $WakeListener"
        }

        $env:PYTHONUTF8 = '1'
        $env:PYTHONIOENCODING = 'utf-8'
        $env:PYTHONUNBUFFERED = '1'
        $env:FRIDAY_USE_JARVIS_WAKE_WORD = '1'
        $env:FRIDAY_TTS_MODEL = $TtsModel
        $env:FRIDAY_TTS_VOICE = $SelectedTtsVoice
        $env:FRIDAY_TTS_FALLBACK_VOICE = $TtsFallbackVoice
        $env:FRIDAY_ALLOW_NON_ENGLISH_TTS = if ($AllowNonEnglishTts) { '1' } else { '0' }

        Start-Process -FilePath $Python `
          -ArgumentList @($WakeListener) `
          -WorkingDirectory $VoiceRoot `
          -RedirectStandardOutput $WakeLog `
          -RedirectStandardError $WakeErrLog `
          -WindowStyle Hidden

        Start-Sleep -Seconds 3
        $wakeProcess = Get-CimInstance Win32_Process | Where-Object {
          $_.Name -match 'python' -and $_.CommandLine -like '*wake_listener.py*'
        } | Select-Object -First 1

        if (-not $wakeProcess) {
          if (Test-Path $WakeErrLog) {
            Get-Content $WakeErrLog -Tail 80
          }
          throw 'Wake listener did not stay running.'
        }
      }

      $visualizerEnabled = ($env:FRIDAY_VOICE_VISUALIZER -match '^(1|true|yes)$')
      $visualizerProcess = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match 'python|pythonw' -and $_.CommandLine -like '*voice_visualizer.py*'
      } | Select-Object -First 1

      if ($visualizerEnabled -and -not $visualizerProcess -and (Test-Path $Visualizer)) {
        $pythonw = Join-Path $VoiceRoot '.venv\Scripts\pythonw.exe'
        $visualizerPython = if (Test-Path $pythonw) { $pythonw } else { $Python }
        Start-Process -FilePath $visualizerPython `
          -ArgumentList @($Visualizer) `
          -WorkingDirectory $VoiceRoot `
          -RedirectStandardOutput $VisualizerLog `
          -RedirectStandardError $VisualizerErrLog
      }

      Write-Host 'FRIDAY voice online.'
      Write-Host 'Open WebUI audio: http://localhost:3000'
      Write-Host 'Kokoro TTS:       http://localhost:8880'
      Write-Host "TTS voice:        $SelectedTtsVoice"
      Write-Host 'Wake listener:    Hey Jarvis'
      if ($visualizerEnabled) {
        Write-Host 'Voice window:     enabled'
      }
      exit 0
    }
  } catch {}
  Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

throw 'Open WebUI did not become healthy after Phase 6 voice configuration.'
