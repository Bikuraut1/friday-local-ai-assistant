import { createServer } from "node:http";
import { spawn } from "node:child_process";

const PORT = Number(process.env.FRIDAY_AUTOMATION_PORT || 8788);
const ALLOWED = new Set(["monday-briefing", "auto-ingest", "memory-consolidation", "email-digest", "status"]);

function sendJson(res, status, body) {
  const text = JSON.stringify(body, null, 2);
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(text),
  });
  res.end(text);
}

function runCommand(command) {
  return new Promise((resolve) => {
    const child = spawn("node", ["/friday/n8n/scripts/friday_automation.mjs", command], {
      cwd: "/friday",
      env: process.env,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (code) => {
      let parsed = null;
      try {
        parsed = JSON.parse(stdout);
      } catch {
        parsed = null;
      }
      resolve({ ok: code === 0, code, stdout, stderr, result: parsed });
    });
  });
}

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
    if (req.method === "GET" && url.pathname === "/health") {
      sendJson(res, 200, { ok: true, service: "friday-n8n-automation" });
      return;
    }

    const match = url.pathname.match(/^\/run\/([a-z-]+)$/);
    if (req.method !== "POST" || !match) {
      sendJson(res, 404, { ok: false, error: "Use POST /run/<command>." });
      return;
    }

    const command = match[1];
    if (!ALLOWED.has(command)) {
      sendJson(res, 400, { ok: false, error: `Unknown command: ${command}` });
      return;
    }

    const result = await runCommand(command);
    sendJson(res, result.ok ? 200 : 500, result);
  } catch (error) {
    sendJson(res, 500, { ok: false, error: `${error.name}: ${error.message}` });
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`FRIDAY n8n automation API listening on ${PORT}`);
});
