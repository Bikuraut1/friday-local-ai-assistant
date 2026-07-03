# CODEX TASK PROMPT — Harden & Improve the FRIDAY Project (Phase-Wise)

> Paste this entire file to Codex as the task. Do not summarize it. Follow it exactly.

---

## ROLE

You are a senior platform/DevOps engineer working inside `D:\Friday`, a local-first Windows 11 AI assistant stack (Ollama, Open WebUI, Qdrant/Mem0, SearXNG, Kokoro, n8n, voice, router, dashboard). You are improving an existing, **currently running** system. You optimize for safety and reproducibility, not speed.

## NON-NEGOTIABLE RULES

1. **Do NOT touch git in any way.** No `git init`, `git add`, `git commit`, no `.git/` edits, no `.gitignore`. Version control is explicitly out of scope. If a step seems to need git, skip it and note why.
2. **Work strictly one phase at a time, in order.** Do not start a phase until the previous phase's acceptance criteria pass and I reply `APPROVED`.
3. **Propose before you change.** At the start of each phase, output: (a) the exact files you will touch, (b) a unified diff or full new-file contents, (c) the verification commands you will run. Wait for my `APPROVED` before writing anything to disk.
4. **Never delete data.** No removing `mem0/qdrant/`, `open-webui/data/`, `ollama/models/`, `backups/`, or any `.db`. Moves/cleanups of data require an explicit confirmation step and a backup first.
5. **Do not break running services.** Assume containers and scripts may be live. Prefer additive/idempotent changes. For any change to ports, env, or compose, state the restart command and expected health check, and let me run it.
6. **No new heavy dependencies, no cloud services, no telemetry.** Keep everything local. Don't introduce a new language, framework, or package manager.
7. **Preserve behavior and naming.** Keep the `friday-*` container/script naming convention and existing ports/URLs unless a phase explicitly changes them.
8. **Idempotent & reversible.** Every change must be safe to re-run. For each phase, provide a one-line rollback.
9. **Windows + PowerShell environment.** Scripts are `.ps1`. Honor existing conventions. Use `127.0.0.1`, not `localhost`, where binding matters.
10. **Stay in scope.** Do only what the current phase defines. Log any new issue you spot under "Out-of-scope findings" — do not fix it.

## WORKFLOW PER PHASE

```
1. Restate the phase goal in one sentence.
2. List files to be touched.
3. Show full proposed changes (diffs / new files) + new .env keys.
4. List exact verification commands and expected output.
5. STOP. Wait for "APPROVED".
6. On approval: apply changes, run verification, paste results.
7. Provide the rollback command.
8. STOP. Wait for "APPROVED" before next phase.
```

If any verification fails, **stop, report, and propose a fix** — never proceed on a failed check.

---

## PHASE 1 — Network exposure hardening (highest priority)

**Problem:** Every `docker-compose.yml` publishes ports on all interfaces (`0.0.0.0`) and Open WebUI runs `WEBUI_AUTH: "False"`, so the stack is reachable unauthenticated on the LAN.

**Do:**
- In every compose file (`mem0`, `n8n`, `open-webui`, `searxng`, `voice/kokoro`), rewrite each published port to bind to loopback only, e.g. `"3000:8080"` → `"127.0.0.1:3000:8080"`. Apply to all ports (6333, 6334, 5678, 8788, 3000, 8081, 8880).
- Do **not** change container-internal ports or the `host.docker.internal` references the services use to talk to each other.
- Leave `WEBUI_AUTH` as-is in this phase but add a clearly commented TODO line directly above it noting it must be enabled before any non-loopback exposure.

**Acceptance criteria:**
- `grep -rn "ports:" -A2` across compose files shows every published port prefixed with `127.0.0.1:`.
- After `docker compose ... up -d`, all health endpoints in the phase report still return HTTP 200 from the host.
- No service-to-service call breaks (Open WebUI still reaches Ollama/Qdrant/SearXNG/Kokoro).

**Rollback:** restore the original port strings.

---

## PHASE 2 — Externalize secrets to `.env`

**Problem:** Hardcoded values in compose/code: `FRIDAY_OPENWEBUI_PASSWORD: "admin"` (n8n, ×2), `SEARXNG_SECRET`, and shared `friday-local-*` API keys (`open-webui` compose, `rag/reranker.py`).

**Do:**
- For each service with secrets, create a `.env` next to its compose file containing the keys, and reference them in compose via `${VAR}` + an `env_file:` entry. Do the same for `rag/reranker.py` (read the key from `os.environ`, with a safe default only for local dev).
- Create a committed-safe `*.env.example` template per service documenting every variable (no real values). Model it on the existing `voice/.env.example`.
- Replace the `admin`/`admin` n8n password default with a generated strong placeholder in `.env` and document that the operator must set it.
- **Do not** print real secret values back to me in plaintext; refer to them by key name.

**Acceptance criteria:**
- No literal password/secret/api-key values remain in any tracked `*.yml` or `*.py` (verify with a grep you include in output).
- Every `.env` has a matching `.env.example`.
- Services start and pass health checks using the `.env` values.

**Rollback:** revert compose/code to inline values (state this only; do not actually revert unless asked).

---

## PHASE 3 — Dependency reproducibility

**Problem:** Only `mem0/requirements.txt` exists. `agent`, `voice`, `dashboard`, `rag`, `router`, `vision`, and `n8n/scripts` run code with no pinned manifest.

**Do:**
- For each Python service without one, generate a `requirements.txt` with pinned versions. Derive versions from the existing `.venv` where present (e.g. `pip freeze`), otherwise from imports. Do **not** install, upgrade, or modify any existing `.venv`.
- For `n8n/scripts` (`.mjs`), add a minimal `package.json` capturing the Node deps actually used.
- Add a one-line header comment to each manifest noting which service/phase it belongs to.

**Acceptance criteria:**
- Each Python service dir contains a `requirements.txt`; `n8n/scripts` contains `package.json`.
- Each manifest lists only modules actually imported by that service (no copying the global freeze blindly — justify inclusions).
- No `.venv` was modified.

**Rollback:** delete the newly added manifests.

---

## PHASE 4 — Output & log retention

**Problem:** `logs/` (44 files), `maintenance/reports/` (14), `n8n/output/` (timestamped briefings), and `vision/screenshots/` grow unbounded.

**Do:**
- Add one PowerShell script `maintenance/cleanup-friday.ps1` that prunes these locations by policy: keep the newest N per folder and/or delete files older than X days. Make N and X parameters with sensible defaults (e.g. keep 20, delete >30 days). Never touch `latest-*.json` files or `backups/`.
- Support a `-DryRun` switch that lists what would be deleted without deleting.
- Document it in `maintenance/OPERATIONS.md`.

**Acceptance criteria:**
- `cleanup-friday.ps1 -DryRun` runs clean and lists candidates without deleting anything.
- Default (non-dry) run respects keep/age rules and preserves `latest-*` files and `backups/`.
- `OPERATIONS.md` updated.

**Rollback:** delete the script and its OPERATIONS.md entry.

---

## PHASE 5 — Unified orchestration (compose)

**Problem:** Five separate compose files; no single command brings the Docker layer up.

**Do:**
- Add a root `docker-compose.yml` that uses Compose `include:` to pull in the five existing compose files (do not move or rewrite them). Goal: `docker compose up -d` from `D:\Friday` brings up all Docker services with the Phase 1 loopback bindings intact.
- If `include:` is unavailable in the installed Compose version, instead add a thin `start-stack.ps1` wrapper that invokes each compose file in dependency order. Detect and state which approach you used and why.
- Do not change the existing per-service `start-*.ps1` scripts; this is additive.

**Acceptance criteria:**
- One command brings the full Docker layer up; `docker ps` shows all `friday-*` containers healthy.
- Native services (Ollama, voice, router, dashboard) are untouched.

**Rollback:** delete the root compose / wrapper script.

---

## PHASE 6 — Documentation & dead-tree cleanup

**Do:**
- Add a concise top-level `README.md`: one-paragraph description, prerequisites, the start/status/stop commands, and links to per-module READMEs and the phase report. Do not duplicate the full phase report.
- Remove the empty `agent/config/` directory **only after confirming it is empty and unreferenced** by any script (grep for it first); if referenced, leave it and report.
- Add a short "Security posture" section to the README summarizing the Phase 1/2 outcomes (loopback-only, auth TODO, secrets in `.env`).

**Acceptance criteria:**
- `README.md` exists and is accurate; commands in it actually work.
- `agent/config/` removed only if proven safe; otherwise documented.

**Rollback:** delete README; recreate the empty dir if removed.

---

## PHASE 7 — Final verification

**Do:**
- Run the existing `maintenance/health-report.ps1` and `status-friday.ps1`. Confirm all endpoints report OK.
- Produce a short closeout summary: what changed per phase, current security posture, remaining risks, and an "Out-of-scope findings" list for anything you deferred.
- Recommend (do not perform) the next steps that require my decision (e.g. enabling `WEBUI_AUTH`, moving Qdrant data out of the source tree, scheduling backups/cleanup).

**Acceptance criteria:**
- Health report: all endpoints OK.
- Closeout summary delivered.

---

## EXPLICITLY OUT OF SCOPE (do not do)

- Anything git-related (init, commit, ignore).
- Deleting or relocating Qdrant / Open WebUI / Ollama data (only *recommend* in Phase 7).
- Changing model routing logic, voice/STT behavior, or AI features.
- Upgrading container images or model versions.
- Enabling `WEBUI_AUTH` automatically (recommend only — it changes the login flow).

## START

Begin with **Phase 1, step 1 only** (restate goal, list files, show proposed diffs, list verification commands), then stop and wait for `APPROVED`.
