# FRIDAY Phase 10 - Model Router

Local router:

```text
http://localhost:8790
```

Routes:

- Simple chat, quick math, lookup: `friday:phi4`
- Complex reasoning: `llama3.1:70b-instruct-q4_K_M`
- Code generation/debugging: `friday:phi4`
- Image analysis: `llava:13b`
- Tiny classifier: `qwen2.5:0.5b-instruct`

## Start

```powershell
Set-Location D:\Friday
.\router\start-router.ps1
```

## Stop

```powershell
.\router\stop-router.ps1
```

## Test

```powershell
.\router\test-router.ps1
```

## API

Route only:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8790/route' -Method Post -ContentType 'application/json' -Body (@{ prompt='Debug this Python error' } | ConvertTo-Json)
```

Route and answer:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8790/chat' -Method Post -ContentType 'application/json' -Body (@{ prompt='Who are you?' } | ConvertTo-Json)
```

Logs:

```text
D:\Friday\router\logs\routing-decisions.jsonl
```
