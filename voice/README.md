# FRIDAY Phase 6 - Voice Interface

Local endpoints:

- Open WebUI audio: `http://localhost:3000/api/v1/audio`
- Kokoro TTS: `http://localhost:8880/v1/audio/speech`

Commands:

```powershell
py -3.11 -m venv D:\Friday\voice\.venv
D:\Friday\voice\.venv\Scripts\python.exe -m pip install --upgrade pip
D:\Friday\voice\.venv\Scripts\python.exe -m pip install openai-whisper sounddevice soundfile requests python-dotenv openwakeword
powershell -ExecutionPolicy Bypass -File D:\Friday\voice\start-voice.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\voice\test-tts.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\voice\download-whisper-models.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\voice\download-openwebui-whisper-models.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\voice\download-openwakeword-models.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\voice\test-openwakeword.ps1
powershell -ExecutionPolicy Bypass -File D:\Friday\voice\test-open-webui-voice.ps1
```

Wake-word configuration:

- openWakeWord requires no API key.
- `FRIDAY_WAKE_WORD_MODEL_PATH` should point to a custom `hey_friday.onnx` model when available.
- FRIDAY uses the bundled `hey_jarvis_v0.1.onnx` wake model by default. Set `FRIDAY_USE_JARVIS_WAKE_WORD=0` to use `hey_friday.onnx` instead.

Example `.env` is available at `D:\Friday\voice\.env.example`.

```text
FRIDAY_WAKE_WORD_MODEL_PATH=D:\Friday\voice\wakewords\hey_friday.onnx
FRIDAY_WAKE_WORD_FALLBACK_MODEL=D:\Friday\voice\wakewords\openwakeword\hey_jarvis_v0.1.onnx
FRIDAY_USE_JARVIS_WAKE_WORD=1
FRIDAY_WAKE_WORD_THRESHOLD=0.65
FRIDAY_WAKE_WORD_CONFIRM_FRAMES=1
FRIDAY_WAKE_WORD_POST_RESPONSE_MUTE_SECONDS=8.0
FRIDAY_SESSION_END_SILENCE_SECONDS=0.75
FRIDAY_SESSION_ENERGY_THRESHOLD=420.0
FRIDAY_SESSION_NOISE_MULTIPLIER=3.5
FRIDAY_SESSION_EMPTY_TURN_LIMIT=2
FRIDAY_CHAT_NUM_PREDICT=70
FRIDAY_MEMORY_BRIDGE_URL=http://localhost:8765
FRIDAY_SEARXNG_URL=http://localhost:8081/search
FRIDAY_WEB_SPOKEN_RESULT_COUNT=5
FRIDAY_TTS_MODEL=kokoro
FRIDAY_TTS_VOICE=af_bella
FRIDAY_TTS_FALLBACK_VOICE=bf_emma
FRIDAY_ALLOW_NON_ENGLISH_TTS=0
```

Wake listener:

```powershell
D:\Friday\voice\.venv\Scripts\python.exe D:\Friday\voice\wake_listener.py
```

Interaction behavior:

- Say the wake phrase once to start a session.
- Continue speaking naturally after each response; no wake phrase is needed between turns.
- Say `goodbye`, `stop listening`, or `go to sleep` to return to wake-word mode.

Indian English, Hinglish, and TTS:

- FRIDAY replies in polished Indian English by default.
- Hinglish is understood for commands like `Chrome kholo`, `aaj ki khabar`, `mausam`, and `gaana bajao`; replies stay English unless the user's turn is Hinglish.
- Kokoro uses English speech voices by default: `af_bella`, then `bf_emma`, then `af_bella` as final fallback.
- The current local Kokoro voice set does not include a reliable Indian-English voice. Indian English is handled in FRIDAY's wording; non-English voice IDs are blocked unless `FRIDAY_ALLOW_NON_ENGLISH_TTS=1`.
- Override with `FRIDAY_TTS_VOICE`, `FRIDAY_TTS_FALLBACK_VOICE`, `FRIDAY_TTS_MODEL`, and `FRIDAY_ALLOW_NON_ENGLISH_TTS`.
