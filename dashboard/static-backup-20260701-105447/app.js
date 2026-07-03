const servicesEl = document.querySelector("#services");
const modelsEl = document.querySelector("#models");
const vramEl = document.querySelector("#vram");
const memoryCountEl = document.querySelector("#memory-count");
const followupsEl = document.querySelector("#followups");
const routingEl = document.querySelector("#routing");
const conversationsEl = document.querySelector("#conversations");
const outputEl = document.querySelector("#action-output");
const clockEl = document.querySelector("#clock");

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

function serviceName(name) {
  return name.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function renderServices(services) {
  servicesEl.innerHTML = Object.entries(services).map(([name, status]) => {
    const ok = status && status.ok;
    const detail = status.status || status.error || "";
    return `<div class="service"><span>${esc(serviceName(name))}</span><span class="pill ${ok ? "ok" : "bad"}">${ok ? "online" : "down"} ${esc(detail)}</span></div>`;
  }).join("");
}

function renderModels(models) {
  const active = models.active || [];
  if (!active.length) {
    modelsEl.innerHTML = `<p class="muted">No active Ollama model.</p>`;
    return;
  }
  modelsEl.innerHTML = active.map((model) => {
    const vram = model.size_vram ? `${Math.round(model.size_vram / 1024 / 1024)} MB VRAM` : "VRAM unknown";
    return `<div class="row"><span>${esc(model.name)}</span><span class="pill">${esc(vram)}</span></div>`;
  }).join("");
}

function renderVram(vram) {
  if (!vram.ok || !vram.gpus.length) {
    vramEl.innerHTML = `<p class="muted">${esc(vram.error || "No GPU data.")}</p>`;
    return;
  }
  vramEl.innerHTML = vram.gpus.map((gpu) => {
    const pct = gpu.total_mb ? Math.round((gpu.used_mb / gpu.total_mb) * 100) : 0;
    return `<div>
      <div class="row"><span>${esc(gpu.name)}</span><span class="pill">${pct}%</span></div>
      <div class="bar"><div class="fill" style="width:${pct}%"></div></div>
      <p class="muted">${gpu.used_mb} MB used / ${gpu.total_mb} MB total, ${gpu.utilization_percent}% utilization</p>
    </div>`;
  }).join("");
}

function renderMemory(memory) {
  memoryCountEl.textContent = memory.count || 0;
  const followups = memory.followups || [];
  followupsEl.innerHTML = followups.length
    ? followups.map((item) => `<div class="row"><span>${esc(item.text)}</span><span class="pill">${esc(item.category)}</span></div>`).join("")
    : `<p class="muted">No pending follow-ups.</p>`;
}

function renderRouting(rows) {
  routingEl.innerHTML = rows && rows.length
    ? rows.slice().reverse().map((row) => `<div class="row"><span>${esc(row.route)} -> ${esc(row.model)}</span><span class="pill">${esc(row.timestamp)}</span></div>`).join("")
    : `<p class="muted">No routing decisions logged yet.</p>`;
}

function renderConversations(rows) {
  conversationsEl.innerHTML = rows && rows.length
    ? rows.map((row) => `<div class="row"><span>${esc(row.title)}</span><span class="pill">${esc(row.detail)}</span></div>`).join("")
    : `<p class="muted">No conversation data.</p>`;
}

function render(state) {
  clockEl.textContent = `Live ${state.timestamp}`;
  renderServices(state.services || {});
  renderModels(state.models || {});
  renderVram(state.vram || {});
  renderMemory(state.memory || {});
  renderRouting(state.routing || []);
  renderConversations(state.conversations || []);
}

async function fallbackPoll() {
  try {
    const res = await fetch("/api/status");
    render(await res.json());
  } catch (error) {
    clockEl.textContent = `Disconnected: ${error.message}`;
  }
}

function connect() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = (event) => render(JSON.parse(event.data));
  ws.onclose = () => setTimeout(connect, 2000);
  ws.onerror = () => ws.close();
}

document.querySelectorAll("button[data-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "Running...";
    outputEl.textContent = `Running ${button.dataset.action}...`;
    try {
      const res = await fetch("/api/action", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action: button.dataset.action }),
      });
      outputEl.textContent = JSON.stringify(await res.json(), null, 2);
      fallbackPoll();
    } catch (error) {
      outputEl.textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  });
});

connect();
setInterval(fallbackPoll, 15000);
