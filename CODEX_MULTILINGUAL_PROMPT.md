# CODEX TASK PROMPT — Trilingual Voice for FRIDAY (Indian English + Hindi + Hinglish)

> Paste this entire file to Codex as the task. Do not summarize it. Follow it exactly.
> Goal: FRIDAY should understand and reply in Indian English, Hindi, and Hinglish — all three treated equally, auto-detected per utterance.

---

## ROLE

You are a senior speech/ML engineer working inside `D:\Friday`, a local-first Windows 11 AI assistant. The voice pipeline is: openWakeWord → Whisper STT → model router → Ollama LLM → Kokoro TTS. The system is **currently running and working in English**. You are adding trilingual support without breaking the working English path.

## HARD CONSTRAINTS (read first)

- **GPU budget: 8 GB VRAM (RTX 3070), 64 GB RAM.** `friday:phi4` (~9 GB) already spills. Do NOT propose a config that loads two large models into VRAM at once. Prefer models ≤9B for anything that must co-reside; anything larger runs CPU/partial-offload and must be flagged as "slow, optional."
- **Do NOT touch git** (no init/commit/ignore) — out of scope.
- **Do NOT break the working English voice loop.** Every change must keep English STT/LLM/TTS working. Keep a fallback to the current behavior behind an env flag or try/except.
- **Work one phase at a time.** Propose → wait for `APPROVED` → apply → verify → give rollback → wait for `APPROVED` before the next phase.
- **Propose before changing.** Per phase, output: files to touch, full diffs/new files, new env vars, exact verification commands (including a mic or audio-file test). Wait for `APPROVED`.
- **Model downloads:** state the exact `ollama pull` / HF download command and size before running; wait for approval; verify the download before wiring it in.
- **Idempotent + reversible.** One-line rollback per phase. Never delete existing models, data, or the working config — additive/flagged changes only.
- **Secrets stay in `.env`** (the project already uses per-service `.env` files). Do not hardcode.
- **Windows + PowerShell.** Scripts are `.ps1`. Use `127.0.0.1`.
- **Stay in scope per phase.** Log anything else under "Out-of-scope findings"; do not fix it.

## CURRENT STATE (verify, don't assume)

- STT (Open WebUI): `WHISPER_MODEL: "medium.en"`, `WHISPER_MULTILINGUAL: "False"`, `WHISPER_LANGUAGE: "en"` in `open-webui/docker-compose.yml`. **`.en` models are English-only — this is the primary blocker.**
- STT (voice loop): `voice/wake_listener.py` uses `FRIDAY_STT_LANGUAGE` (default `en`) and a local Whisper path (`FRIDAY_LOCAL_WHISPER_MODEL_DIR`).
- TTS: Kokoro via OpenAI-compatible API, fixed voice `af_bella` (US English). Kokoro DOES ship Hindi voices: `hf_alpha`, `hf_beta` (female), `hm_omega`, `hm_psi` (male). It has NO Indian-English accent voice.
- LLM: `friday:phi4` primary, `llama3.1:70b` for complex. Router at `router/model_router.py` classifies by task type only (no language dimension yet).
- History: `large-v3-turbo` previously caused Open WebUI transcription HTTP 500 — validate any large STT model out-of-band before wiring.

---

## PHASE 1 — Multilingual STT baseline

**Goal:** replace English-only Whisper with a multilingual model and auto-detect language, keeping English quality.

**Do:**
- In `open-webui/docker-compose.yml`: set `WHISPER_MODEL: "medium"` (drop `.en`), `WHISPER_MULTILINGUAL: "True"`, and `WHISPER_LANGUAGE: ""` (auto-detect). Keep `WHISPER_COMPUTE_TYPE: "int8"`.
- In `voice/wake_listener.py`: make STT language auto-detect (empty/`auto`) via a new env var (e.g. `FRIDAY_STT_LANGUAGE=auto`) and capture Whisper's detected language code for later phases. Preserve the old behavior when the var is `en`.
- Add the new env keys to the relevant `.env` and `.env.example`.

**Acceptance criteria (all three, equally):**
- Speaking Indian-English, Hindi, and a Hinglish sentence each transcribes into sensible text (Hindi in Devanagari; Hinglish acceptable even if imperfect — Phase 2 improves it).
- English transcription quality is not worse than before.
- Provide a repeatable test: 3 short WAV files (one per language) piped through the STT and the transcripts printed.

**Rollback:** restore `medium.en` / `MULTILINGUAL=False` / `LANGUAGE=en`.

---

## PHASE 2 — Code-switch STT upgrade (Hinglish accuracy)

**Goal:** real Hindi↔English code-switch transcription (Devanagari for Hindi, Roman for English loanwords).

**Do:**
- Evaluate a code-switch fine-tune via faster-whisper: candidates — **Trelis "Whisper Hinglish"** and **AI4Bharat IndicWhisper**. Download one, benchmark against Phase-1 `medium` on the same 3+ test clips (report WER/qualitative diff).
- Wire the winner into the voice loop's local-whisper path behind an env flag (`FRIDAY_STT_ENGINE=hinglish|medium`), with automatic fallback to `medium` on load/inference error.
- Keep model files under the existing local whisper models dir; document size and source.

**Acceptance criteria:**
- On a Hinglish clip, the fine-tune visibly beats `medium` (fewer wrong/translated words) — show both transcripts side by side.
- English and Hindi clips are no worse than Phase 1.
- Latency reported; if it regresses badly, keep `medium` as default and mark the fine-tune opt-in.

**Rollback:** set `FRIDAY_STT_ENGINE=medium`.

---

## PHASE 3 — Language detection + routing

**Goal:** know per-utterance whether it's English / Hindi / Hinglish, and pass that downstream.

**Do:**
- Use Whisper's detected language code as the primary signal. Add a lightweight **Hinglish heuristic** (Whisper often tags Hinglish as `hi` or `en`): e.g. mixed Devanagari+Latin, or romanized-Hindi function words (`hai`, `kya`, `nahi`, `kaise`, `matlab`, etc.) → classify `hinglish`.
- Extend `router/model_router.py` with a `language` field on each decision (`en`/`hi`/`hinglish`) and log it in `routing-decisions.jsonl` (the dashboard already reads this file).
- Do not change task-type routing behavior; only add the language dimension.

**Acceptance criteria:**
- Router log entries include a correct `language` for English, Hindi, and Hinglish test prompts.
- Existing task routing (simple_chat/code/complex/image/quick_math) is unchanged.

**Rollback:** ignore/remove the `language` field.

---

## PHASE 4 — Indic-capable LLM (fits 8 GB)

**Goal:** better Hindi/Hinglish generation, routed only when needed, without blowing VRAM.

**Do:**
- Pull and A/B **candidates that fit 8 GB**: `gemma2:9b`, `qwen2.5:7b` (or `:14b` if it fits with headroom), `aya-expanse:8b`. Compare Hindi + Hinglish quality on a fixed prompt set.
- Optionally evaluate **Sarvam-M (24B)** GGUF as a CPU/partial-offload option — mark explicitly as "high quality but slow, optional." (Note: Sarvam-30B/105B are not yet supported by Ollama/llama.cpp — do not attempt.)
- Route `language in {hi, hinglish}` to the chosen Indic model; keep `friday:phi4` for English. Ensure only one heavy model is resident at a time (rely on Ollama keep-alive/unload; document the expected swap latency).

**Acceptance criteria:**
- Hindi and Hinglish replies from the Indic model are clearly better than phi4 on the test set (show examples).
- English path still uses phi4; VRAM never needs two large models simultaneously (show `ollama ps` during a language switch).

**Rollback:** route all languages back to phi4.

---

## PHASE 5 — Language-aware responses

**Goal:** FRIDAY replies in the same language and script the user used.

**Do:**
- Update `FRIDAY_VOICE_SYSTEM_PROMPT` (in `voice/wake_listener.py`) to instruct: detect the user's language (Indian English / Hindi / Hinglish) and reply in the same language and script; for Hinglish, reply in natural romanized Hinglish. Include 1–2 few-shot Hinglish examples.
- Make the script policy explicit and configurable (e.g. `FRIDAY_HINGLISH_SCRIPT=roman|devanagari`).
- Keep replies concise (existing voice-mode brevity rule).

**Acceptance criteria:**
- Same 3 test utterances produce replies in the matching language/script.
- English behavior/brevity unchanged.

**Rollback:** restore the previous system prompt (keep a copy).

---

## PHASE 6 — Multilingual TTS

**Goal:** speak each language naturally.

**Do:**
- Select the Kokoro voice by detected language: Hindi → `hf_alpha`/`hm_omega` (choose one female + one male, make it configurable); English → keep current voice. Wire voice selection into the voice loop / TTS call (`voice/wake_listener.py`, `FRIDAY_TTS_VOICE` per language).
- Hinglish policy: pick the voice by the reply's dominant language (document the rule). Optionally test transliterating English words to Devanagari before sending to a Hindi voice for smoother Hinglish.
- **Optional (only if approved):** add Piper `en_IN` or AI4Bharat Indic-TTS for authentic Indian-accent English as a separate voice option. Do not replace Kokoro; add alongside.

**Acceptance criteria:**
- Hindi text is spoken by a Hindi voice; English by the English voice; Hinglish uses the documented rule and is intelligible.
- TTS latency reported; no regression for English.

**Rollback:** revert to fixed `af_bella`.

---

## PHASE 7 — End-to-end verification

**Do:**
- Full mic test (or WAV playback into the pipeline) for all three languages: wake → transcribe → route → reply → speak. Capture transcript, detected language, model used, and spoken output for each.
- Run `maintenance/health-report.ps1` and confirm all endpoints still OK.
- Report latency per stage per language, remaining weaknesses, and an "Out-of-scope findings" list.
- Recommend (don't perform) any follow-ups that need a decision.

**Acceptance criteria:** all three languages complete the full loop; health report OK.

---

## EXPLICITLY OUT OF SCOPE
- Git anything. Enabling WEBUI_AUTH. Moving data stores. Changing the dashboard. Upgrading unrelated images.
- Sarvam-30B/105B (unsupported by Ollama today). Cloud STT/TTS/LLM APIs (stay local).
- Loading two large models into VRAM at once.

## START
Begin with **Phase 1, step 1 only** (restate goal, list files, show diffs, list verification commands incl. the 3-language audio test), then stop and wait for `APPROVED`.
