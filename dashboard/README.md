# FRIDAY Dashboard

Local dashboard:

```text
http://localhost:8888
```

It shows:

- System status
- VRAM usage
- Active Ollama model
- Memory count and follow-ups
- Recent routing decisions
- Recent conversation availability
- Quick action buttons

The browser receives live updates through a local WebSocket at `/ws`.

## Start

```powershell
Set-Location D:\Friday
.\dashboard\start-dashboard.ps1
```

## Test

```powershell
.\dashboard\test-dashboard.ps1
```

## Stop

```powershell
.\dashboard\stop-dashboard.ps1
```
