/* ==========================================================================
   FRIDAY // Core — Jarvis HUD front-end
   Consumes the unchanged dashboard_server.py contract:
     GET  /api/status  -> full state (also pushed over /ws every ~3s)
     POST /api/action  -> { action: <name> }
   State shape: { timestamp, services, models, vram, memory, routing, conversations }
   ========================================================================== */

const $ = (id) => document.getElementById(id);

/* pretty service labels */
const SERVICE_LABELS = {
  open_webui: "Open WebUI",
  ollama: "Ollama",
  memory: "Memory Bridge",
  rag_reranker: "RAG Reranker",
  searxng: "SearXNG",
  kokoro: "Kokoro TTS",
  n8n: "n8n",
  n8n_automation: "n8n Automation",
  router: "Model Router",
  dashboard: "Dashboard",
  wake_listener: "Wake Listener",
  vision_hotkey: "Vision Hotkey",
};

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function label(key) {
  return SERVICE_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function serviceDetail(status) {
  if (!status) return "down";
  if (status.ok) {
    if (status.pid) return `PID ${status.pid}`;
    if (status.status) return `HTTP ${status.status}`;
    return "online";
  }

  const error = String(status.error || "down");
  const port = error.match(/port=(\d+)/) || error.match(/port (\d+)/i);
  if (/process not running/i.test(error)) return "not running";
  if (/connection refused|actively refused/i.test(error)) {
    return port ? `port ${port[1]} refused` : "connection refused";
  }
  if (/timed out|timeout/i.test(error)) {
    return port ? `port ${port[1]} timeout` : "timeout";
  }
  return error.length > 42 ? `${error.slice(0, 39)}...` : error;
}

/* ---------- top bar ---------- */
function tickClock() {
  const now = new Date();
  $("clock").textContent = now.toLocaleTimeString("en-GB");
  const h = now.getHours();
  const part = h < 12 ? "morning" : h < 17 ? "afternoon" : "evening";
  $("greeting").textContent = `Good ${part}, Boss`;
}
setInterval(tickClock, 1000);
tickClock();

/* ---------- services ---------- */
function renderServices(services) {
  const entries = Object.entries(services || {});
  let up = 0;
  const html = entries.map(([key, s]) => {
    const ok = !!(s && s.ok);
    if (ok) up++;
    const detail = serviceDetail(s);
    const rawDetail = ok ? detail : (s && s.error ? s.error : detail);
    return `<div class="srow">
      <span class="sd ${ok ? "up" : "down"}"></span>
      <span class="sname">${esc(label(key))}</span>
      <span class="sp ${ok ? "" : "down"}" title="${esc(rawDetail)}">${esc(detail)}</span>
    </div>`;
  }).join("");
  $("services").innerHTML = html || `<div class="srow">No services reported.</div>`;
  $("systems-count").textContent = `${up}/${entries.length}`;
}

/* ---------- reactor (active model + core state) ---------- */
function renderReactor(state) {
  const wrap = document.querySelector(".reactor-wrap");
  const active = (state.models && state.models.active) || [];
  const routerOk = state.services && state.services.router && state.services.router.ok;
  const coreOnline = state.services && state.services.ollama && state.services.ollama.ok;

  wrap.classList.remove("active", "offline");
  if (!coreOnline) {
    wrap.classList.add("offline");
    $("active-model").textContent = "OFFLINE";
    $("core-state").textContent = "NO CORE";
    $("reactor-sub").textContent = "Ollama unreachable";
    return;
  }

  if (active.length) {
    const m = active[0];
    wrap.classList.add("active");
    $("active-model").textContent = m.name || "loaded";
    $("core-state").textContent = "MODEL LOADED";
    const vram = m.size_vram ? `${Math.round(m.size_vram / 1048576)} MB VRAM` : "";
    $("reactor-sub").textContent = [routerOk ? "router active" : "router idle", vram].filter(Boolean).join(" · ");
  } else {
    $("active-model").textContent = "IDLE";
    $("core-state").textContent = routerOk ? "ROUTER READY" : "STANDBY";
    $("reactor-sub").textContent = `${(state.models?.installed || []).length} models installed`;
  }
}

/* ---------- GPU gauge + bars ---------- */
const GAUGE_CIRC = 2 * Math.PI * 50; // r=50 -> ~314.159
function renderVram(vram) {
  const gpu = vram && vram.ok && vram.gpus && vram.gpus[0];
  if (!gpu) {
    $("gpu-name").textContent = "—";
    $("vram-pct").textContent = "--%";
    $("vram-detail").textContent = (vram && vram.error) ? "no GPU data" : "– / – GB";
    $("vram-arc").style.strokeDashoffset = GAUGE_CIRC;
    $("gpu-util").textContent = "–%";
    $("gpu-util-bar").style.width = "0%";
    return;
  }
  const pct = gpu.total_mb ? Math.round((gpu.used_mb / gpu.total_mb) * 100) : 0;
  $("gpu-name").textContent = gpu.name || "GPU";
  $("vram-pct").textContent = `${pct}%`;
  $("vram-detail").textContent = `${(gpu.used_mb / 1024).toFixed(1)} / ${(gpu.total_mb / 1024).toFixed(1)} GB`;
  $("vram-arc").style.strokeDashoffset = GAUGE_CIRC * (1 - pct / 100);
  $("gpu-util").textContent = `${gpu.utilization_percent}%`;
  $("gpu-util-bar").style.width = `${gpu.utilization_percent}%`;
}

/* ---------- memory ---------- */
function renderMemory(memory) {
  const count = (memory && memory.count) || 0;
  $("mem-count").textContent = `${count} note${count === 1 ? "" : "s"}`;
  // soft visual scale (caps at 25 notes -> full bar)
  $("mem-bar").style.width = `${Math.min(100, count * 4)}%`;

  const fus = (memory && memory.followups) || [];
  $("followups").innerHTML = fus.length
    ? fus.slice(0, 4).map((f) => `<div class="fu"><b>${esc(f.category)}</b><span>${esc(f.text)}</span></div>`).join("")
    : `<div class="empty">No pending follow-ups.</div>`;
}

/* ---------- router log ---------- */
function renderRouting(rows) {
  const list = (rows || []).slice().reverse();
  $("routing").innerHTML = list.length
    ? list.map((r) => {
        const q = r.prompt_preview ? `"${esc(r.prompt_preview)}" ` : "";
        const t = (r.timestamp || "").replace("T", " ").slice(5, 19);
        return `<div class="rrow">
          <span class="rq">${q}<em>&rarr;</em> ${esc(r.route)} <em>&rarr;</em> <b>${esc(r.model)}</b></span>
          <span class="rt">${esc(t)}</span>
        </div>`;
      }).join("")
    : `<div class="empty">No routing decisions logged yet.</div>`;
}

/* ---------- voice state ---------- */
function renderVoice(services) {
  const wakeOk = services && services.wake_listener && services.wake_listener.ok;
  const wave = $("wave");
  wave.classList.toggle("live", !!wakeOk);
  const wakeEl = $("wake");
  const dot = $("wake-dot");
  if (wakeOk) {
    wakeEl.classList.remove("off");
    $("wake-text").textContent = "HEY JARVIS · LISTENING";
    $("voice-sub").textContent = "whisper · listening";
  } else {
    wakeEl.classList.add("off");
    $("wake-text").textContent = "VOICE OFFLINE";
    $("voice-sub").textContent = "whisper → kokoro";
  }
}

/* build static waveform bars once */
(function buildWave() {
  const wave = $("wave");
  let html = "";
  for (let i = 0; i < 40; i++) {
    html += `<i style="animation-delay:${(-(Math.random())).toFixed(2)}s"></i>`;
  }
  wave.innerHTML = html;
})();

/* ---------- master render ---------- */
function render(state) {
  renderServices(state.services || {});
  renderReactor(state);
  renderVram(state.vram || {});
  renderMemory(state.memory || {});
  renderRouting(state.routing || []);
  renderVoice(state.services || {});
}

/* ---------- transport: websocket + polling fallback ---------- */
async function poll() {
  try {
    const res = await fetch("/api/status");
    render(await res.json());
  } catch (e) {
    const w = $("wake");
    w.classList.add("off");
    $("wake-text").textContent = "DISCONNECTED";
  }
}

function connect() {
  let ws;
  try {
    ws = new WebSocket(`ws://${location.host}/ws`);
  } catch (e) {
    return poll();
  }
  ws.onmessage = (ev) => {
    try { render(JSON.parse(ev.data)); } catch (e) { /* ignore malformed frame */ }
  };
  ws.onclose = () => setTimeout(connect, 2000);
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
}

/* ---------- quick actions ---------- */
document.querySelectorAll("button[data-action]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const out = $("action-output");
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Running…";
    out.hidden = false;
    out.textContent = `Running ${btn.dataset.action}…`;
    try {
      const res = await fetch("/api/action", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: btn.dataset.action }),
      });
      out.textContent = JSON.stringify(await res.json(), null, 2);
      poll();
    } catch (e) {
      out.textContent = String(e && e.message ? e.message : e);
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  });
});

/* ---------- boot ---------- */
poll();
connect();
setInterval(poll, 15000);
