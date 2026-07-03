import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { extname, join } from "node:path";

const ROOT = process.env.FRIDAY_ROOT || "/friday";
const OUT_DIR = join(ROOT, "n8n", "output");
const STATE_DIR = join(ROOT, "n8n", "state");
const KNOWLEDGE_DIR = join(ROOT, "knowledge-base");

const OLLAMA = process.env.FRIDAY_OLLAMA_URL || "http://host.docker.internal:11434";
const OPEN_WEBUI = process.env.FRIDAY_OPEN_WEBUI_URL || "http://host.docker.internal:3000";
const MEMORY = process.env.FRIDAY_MEMORY_BRIDGE_URL || "http://host.docker.internal:8765";
const SEARXNG = process.env.FRIDAY_SEARXNG_URL || "http://host.docker.internal:8081/search";
const MODEL = process.env.FRIDAY_MODEL || "friday:phi4";

const MEMORY_CATEGORIES = [
  "USER_PROFILE",
  "GOALS",
  "PROJECTS",
  "PREFERENCES",
  "RELATIONSHIPS",
  "DECISIONS_MADE",
  "FOLLOW_UPS",
];

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required.`);
  return value;
}

function ensureDirs() {
  mkdirSync(OUT_DIR, { recursive: true });
  mkdirSync(STATE_DIR, { recursive: true });
}

function writeJson(name, data) {
  ensureDirs();
  const path = join(OUT_DIR, name);
  writeFileSync(path, JSON.stringify(data, null, 2), "utf8");
  return path;
}

function writeText(name, text) {
  ensureDirs();
  const path = join(OUT_DIR, name);
  writeFileSync(path, text, "utf8");
  return path;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${text.slice(0, 500)}`);
  }
  const text = await response.text();
  return text ? JSON.parse(text) : {};
}

async function ollamaGenerate(prompt, timeoutMs = 180000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const data = await requestJson(`${OLLAMA}/api/generate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ model: MODEL, prompt, stream: false }),
      signal: controller.signal,
    });
    return String(data.response || "").trim();
  } finally {
    clearTimeout(timer);
  }
}

async function memoryList(category = null, topK = 20) {
  try {
    const url = new URL(`${MEMORY}/memory`);
    url.searchParams.set("top_k", String(topK));
    if (category) url.searchParams.set("category", category);
    const data = await requestJson(url);
    return Array.isArray(data.results) ? data.results : [];
  } catch {
    return [];
  }
}

async function memoryAdd(text, category, source) {
  return requestJson(`${MEMORY}/memory`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ text, category, source, infer: false }),
  });
}

async function searx(query, count = 6) {
  try {
    const url = new URL(SEARXNG);
    url.searchParams.set("q", query);
    url.searchParams.set("format", "json");
    url.searchParams.set("language", "en");
    const data = await requestJson(url);
    return (data.results || []).slice(0, count).map((item) => ({
      title: String(item.title || ""),
      url: String(item.url || ""),
      content: String(item.content || ""),
    }));
  } catch (error) {
    return [{ title: "Search unavailable", url: "", content: String(error.message || error) }];
  }
}

function compactMemoryItems(items) {
  return items
    .slice(0, 60)
    .map((item) => {
      const text = item.memory || item.text || item.content || JSON.stringify(item);
      const meta = item.metadata || {};
      const category = meta.category || item.category || "UNKNOWN";
      return `- [${category}] ${text}`;
    })
    .join("\n");
}

async function mondayBriefing() {
  const now = new Date();
  const memories = [];
  for (const category of ["USER_PROFILE", "GOALS", "PROJECTS", "FOLLOW_UPS", "DECISIONS_MADE"]) {
    memories.push(...(await memoryList(category, 10)));
  }
  const news = await searx("India top news today", 8);
  const weatherLocation = process.env.FRIDAY_WEATHER_LOCATION || "";
  const weather = weatherLocation ? await searx(`today weather ${weatherLocation}`, 3) : [];
  const prompt = `You are FRIDAY preparing Boss's Monday briefing.
Date/time: ${now.toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}

Relevant memory:
${compactMemoryItems(memories) || "- No memory returned."}

News search results:
${JSON.stringify(news, null, 2)}

Weather search results:
${weatherLocation ? JSON.stringify(weather, null, 2) : "No weather location configured."}

Write a concise briefing with sections:
1. Priorities
2. Pending follow-ups
3. News that may matter
4. Weather note
5. Suggested first action
No filler. Address Boss directly.
Do not invent tasks, meetings, deadlines, weather location, or personal facts.
If memory does not contain a priority or follow-up, write "No stored item found."
If no weather location is configured, write "No weather location configured."`;
  const briefing = (await ollamaGenerate(prompt)).replace(/\n+If you need[\s\S]*$/i, "").trim();
  const stamp = now.toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
  const briefingFile = writeText(`monday-briefing-${stamp}.md`, `${briefing}\n`);
  const latest = writeJson("latest-monday-briefing.json", {
    ok: true,
    created_at: now.toISOString(),
    briefing_file: briefingFile,
    briefing,
  });
  console.log(JSON.stringify({ ok: true, briefing_file: briefingFile, latest, preview: briefing.slice(0, 1000) }, null, 2));
}

function walkFiles(root) {
  const files = [];
  if (!existsSync(root)) return files;
  for (const name of readdirSync(root)) {
    const path = join(root, name);
    const stats = statSync(path);
    if (stats.isDirectory()) files.push(...walkFiles(path));
    else files.push(path);
  }
  return files;
}

function fileHash(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function mimeFor(path) {
  const ext = extname(path).toLowerCase();
  if (ext === ".pdf") return "application/pdf";
  if (ext === ".docx") return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (ext === ".md") return "text/markdown";
  if (ext === ".txt") return "text/plain";
  return "application/octet-stream";
}

async function openWebUiToken() {
  const email = process.env.FRIDAY_OPENWEBUI_EMAIL || "admin@localhost";
  const password = requiredEnv("FRIDAY_OPENWEBUI_PASSWORD");
  const data = await requestJson(`${OPEN_WEBUI}/api/v1/auths/signin`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!data.token) throw new Error("Open WebUI signin did not return a token.");
  return data.token;
}

async function uploadToOpenWebUi(path, token) {
  const form = new FormData();
  const blob = new Blob([readFileSync(path)], { type: mimeFor(path) });
  form.append("file", blob, path.split(/[\\/]/).pop());
  const response = await fetch(`${OPEN_WEBUI}/api/v1/files/?process=true&process_in_background=true`, {
    method: "POST",
    headers: { authorization: `Bearer ${token}` },
    body: form,
  });
  if (!response.ok) throw new Error(`Upload failed HTTP ${response.status}: ${(await response.text()).slice(0, 500)}`);
  return response.json();
}

async function autoIngest() {
  ensureDirs();
  const stateFile = join(STATE_DIR, "ingested-files.json");
  const previous = existsSync(stateFile) ? JSON.parse(readFileSync(stateFile, "utf8")) : {};
  const allowed = new Set([".pdf", ".docx", ".txt", ".md"]);
  const candidates = walkFiles(KNOWLEDGE_DIR).filter((path) => allowed.has(extname(path).toLowerCase()));
  const uploaded = [];
  let skipped = 0;
  let token = null;
  for (const path of candidates) {
    const digest = fileHash(path);
    if (previous[path]?.sha256 === digest) {
      skipped += 1;
      continue;
    }
    token ||= await openWebUiToken();
    const result = await uploadToOpenWebUi(path, token);
    previous[path] = { sha256: digest, uploaded_at: new Date().toISOString(), openwebui_id: result.id };
    uploaded.push({ path, openwebui_id: result.id });
  }
  writeFileSync(stateFile, JSON.stringify(previous, null, 2), "utf8");
  const output = { ok: true, uploaded, skipped, state_file: stateFile };
  writeJson("latest-auto-ingest.json", output);
  console.log(JSON.stringify(output, null, 2));
}

async function memoryConsolidation() {
  const items = [];
  for (const category of MEMORY_CATEGORIES) items.push(...(await memoryList(category, 25)));
  const prompt = `Consolidate FRIDAY's long-term memory for Boss.

Raw memory:
${compactMemoryItems(items) || "- No memory returned."}

Return:
- durable facts worth keeping
- duplicates or contradictions to review
- pending follow-ups
- project status summary
Keep it concise and operational.`;
  const summary = await ollamaGenerate(prompt);
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "");
  const summaryFile = writeText(`memory-consolidation-${stamp}.md`, `${summary}\n`);
  await memoryAdd(`Weekly memory consolidation created at ${summaryFile}. Key summary: ${summary.slice(0, 1200)}`, "DECISIONS_MADE", "n8n-memory-consolidation");
  const output = { ok: true, summary_file: summaryFile, summary };
  writeJson("latest-memory-consolidation.json", output);
  console.log(JSON.stringify(output, null, 2));
}

async function emailDigest() {
  const latest = join(OUT_DIR, "latest-monday-briefing.json");
  const briefing = existsSync(latest) ? JSON.parse(readFileSync(latest, "utf8")).briefing || "" : "No Monday briefing has been generated yet.";
  const digest = await ollamaGenerate(`Create a concise email digest for Boss from this briefing. Include subject and body.\n\n${briefing}`, 120000);
  const digestFile = writeText("latest-email-digest.txt", `${digest}\n`);
  const output = {
    ok: true,
    digest_file: digestFile,
    sent: false,
    note: "SMTP send is intentionally disabled in the Node-only n8n runner. Digest file was generated locally.",
  };
  writeJson("latest-email-digest.json", output);
  console.log(JSON.stringify(output, null, 2));
}

async function status() {
  const checks = {};
  for (const [name, url] of Object.entries({
    ollama: `${OLLAMA}/api/tags`,
    open_webui: `${OPEN_WEBUI}/health`,
    memory: `${MEMORY}/health`,
  })) {
    try {
      const response = await fetch(url);
      checks[name] = { ok: response.ok, status_code: response.status };
    } catch (error) {
      checks[name] = { ok: false, error: String(error.message || error) };
    }
  }
  const output = { ok: Object.values(checks).every((item) => item.ok), checks };
  console.log(JSON.stringify(output, null, 2));
  if (!output.ok) process.exitCode = 1;
}

const command = process.argv[2];
try {
  if (command === "monday-briefing") await mondayBriefing();
  else if (command === "auto-ingest") await autoIngest();
  else if (command === "memory-consolidation") await memoryConsolidation();
  else if (command === "email-digest") await emailDigest();
  else if (command === "status") await status();
  else {
    console.error(JSON.stringify({ ok: false, error: `Unknown command: ${command}` }, null, 2));
    process.exitCode = 2;
  }
} catch (error) {
  console.error(JSON.stringify({ ok: false, error: `${error.name}: ${error.message}` }, null, 2));
  process.exitCode = 1;
}
