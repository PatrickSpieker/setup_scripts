import { parseArgs } from "node:util";
import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { loadConfig } from "./config.js";
import { shutdownAll } from "./simulator.js";
import { register as registerXcodebuild } from "./tools/xcodebuild.js";
import { register as registerListSchemes } from "./tools/list-schemes.js";
import { register as registerInstallLaunch } from "./tools/install-launch.js";
import { register as registerScreenshot } from "./tools/screenshot.js";
import { register as registerBuildLog } from "./tools/build-log.js";
import { register as registerCrashLog } from "./tools/crash-log.js";
import { register as registerResolveDeps } from "./tools/resolve-deps.js";
import { register as registerDeviceLog } from "./tools/device-log.js";

// --- CLI args ---
const { values } = parseArgs({
  options: {
    "repo-id": { type: "string" },
    port: { type: "string", default: "3100" },
  },
});

const repoId = values["repo-id"];
const port = parseInt(values.port ?? "3100", 10);

if (!repoId) {
  console.error("Usage: xcode-bridge --repo-id <repo-id> [--port 3100]");
  process.exit(1);
}

// Validate config exists before starting
const config = loadConfig(repoId);
const slotCount = Object.keys(config.slots).length;

// --- MCP server ---
const server = new McpServer({
  name: "xcode-bridge",
  version: "0.1.0",
});

// Register all tools
registerXcodebuild(server, repoId);
registerListSchemes(server, repoId);
registerInstallLaunch(server, repoId);
registerScreenshot(server, repoId);
registerBuildLog(server, repoId);
registerCrashLog(server, repoId);
registerResolveDeps(server, repoId);
registerDeviceLog(server, repoId);

// --- HTTP transport ---
const app = express();

// StreamableHTTP uses a single /mcp endpoint for POST (tool calls) and
// GET (SSE event stream) and DELETE (session cleanup).
app.all("/mcp", async (req, res) => {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined, // stateless — no session tracking needed
  });
  await server.connect(transport);
  await transport.handleRequest(req, res);
});

// Health check for the launcher script
app.get("/health", (_req, res) => {
  res.json({ ok: true, repoId, slots: slotCount });
});

// --- Shutdown ---
let shuttingDown = false;

async function cleanup() {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log("\nShutting down simulators...");
  await shutdownAll();
  console.log("Done.");
  process.exit(0);
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);

// --- Start ---
app.listen(port, () => {
  console.log(`xcode-bridge MCP server`);
  console.log(`  repo:  ${repoId}`);
  console.log(`  slots: ${slotCount}`);
  console.log(`  url:   http://localhost:${port}/mcp`);
});
