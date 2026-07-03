# FRIDAY Phase 7 - Agentic Tool Use

This phase installs Open Interpreter locally and gives FRIDAY a guarded Windows tool layer.

## Start Open Interpreter

```powershell
Set-Location D:\Friday
.\agent\start-interpreter.ps1
```

Default backend:

- Model: `ollama/friday:phi4`
- API base: `http://localhost:11434`
- Safe mode: `ask`
- Telemetry: disabled

## Tool Safety Policy

Allowed file roots:

- `D:\Friday`
- `%USERPROFILE%\Desktop`
- `%USERPROFILE%\Documents`
- `%USERPROFILE%\Downloads`

Blocked file roots:

- `C:\Windows`
- `C:\Windows\System32`
- `C:\Boot`
- `C:\EFI`
- `C:\Recovery`
- registry paths such as `HKLM:` and `HKCU:`

This is a practical tool-layer sandbox. It restricts the FRIDAY tool scripts, but it is not a kernel-level sandbox for every arbitrary command Open Interpreter could generate.

## Verification

```powershell
Set-Location D:\Friday
.\agent\test-phase7.ps1
```

## Common Commands

```powershell
D:\Friday\agent\.venv\Scripts\python.exe D:\Friday\agent\tools\file_manager.py search "$env:USERPROFILE\Desktop" --pattern "*.pdf" --files-only
D:\Friday\agent\.venv\Scripts\python.exe D:\Friday\agent\tools\file_manager.py summarize-largest-pdf "$env:USERPROFILE\Desktop"
D:\Friday\agent\.venv\Scripts\python.exe D:\Friday\agent\tools\sysinfo.py summary
D:\Friday\agent\.venv\Scripts\python.exe D:\Friday\agent\tools\scheduler.py list
```
