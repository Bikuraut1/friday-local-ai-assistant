# FRIDAY Phase 9 - Vision

Phase 9 adds screenshot understanding with `llava:13b`.

## One-shot screen analysis

```powershell
Set-Location D:\Friday
D:\Friday\voice\.venv\Scripts\python.exe D:\Friday\vision\analyze_screen.py
```

## Hotkey listener

```powershell
Set-Location D:\Friday
.\vision\start-vision-hotkey.ps1
```

Then press:

```text
Win + Shift + F
```

FRIDAY will take a screenshot, send it to `llava:13b`, and speak the analysis using Kokoro.

## Stop hotkey

```powershell
.\vision\stop-vision-hotkey.ps1
```

## Test

```powershell
.\vision\test-vision.ps1
```

Screenshots are stored in `D:\Friday\vision\screenshots`.
Latest analysis is stored in `D:\Friday\vision\logs\latest-analysis.json`.
