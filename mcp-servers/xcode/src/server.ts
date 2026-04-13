import express from "express";
import cors from "cors";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { loadConfig } from "./config.js";
import { SimulatorManager } from "./simulators.js";
import { xcodebuildSchema, handleXcodebuild } from "./tools/xcodebuild.js";
import { simulatorSchema, handleSimulator } from "./tools/simulator.js";
import {
  installAndLaunchSchema,
  handleInstallAndLaunch,
} from "./tools/install-and-launch.js";
import { screenshotSchema, handleScreenshot } from "./tools/screenshot.js";

const config = loadConfig();
const simulators = new SimulatorManager(config);

function createServer(): McpServer {
  const server = new McpServer({
    name: "xcode",
    version: "0.1.0",
  });

  server.tool(
    "xcodebuild",
    "Build, test, or clean an Xcode project. Requires branch to route to the correct worktree and simulator.",
    xcodebuildSchema.shape,
    async (params) => handleXcodebuild(params as any, config, simulators)
  );

  server.tool(
    "simulator",
    "Boot, shutdown, or check status of the iOS Simulator assigned to a branch.",
    simulatorSchema.shape,
    async (params) => handleSimulator(params as any, simulators)
  );

  server.tool(
    "install_and_launch",
    "Install a built .app on the simulator and launch it.",
    installAndLaunchSchema.shape,
    async (params) => handleInstallAndLaunch(params as any, config, simulators)
  );

  server.tool(
    "screenshot",
    "Take a screenshot of the simulator and save it to the worktree root.",
    screenshotSchema.shape,
    async (params) => handleScreenshot(params as any, config, simulators)
  );

  return server;
}

const app = express();
app.use(cors({ exposedHeaders: ["Mcp-Session-Id"] }));
app.use(express.json());

const transports = new Map<string, StreamableHTTPServerTransport>();

app.post("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;

  if (sessionId && transports.has(sessionId)) {
    const transport = transports.get(sessionId)!;
    await transport.handleRequest(req, res);
    return;
  }

  if (!sessionId && isInitializeRequest(req.body)) {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => crypto.randomUUID(),
      onsessioninitialized: (id) => {
        transports.set(id, transport);
      },
    });

    transport.onclose = () => {
      const id = [...transports.entries()].find(
        ([, t]) => t === transport
      )?.[0];
      if (id) transports.delete(id);
    };

    const server = createServer();
    await server.connect(transport);
    await transport.handleRequest(req, res);
    return;
  }

  res.status(400).json({ error: "Bad request. Send an initialize request first." });
});

app.get("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (!sessionId || !transports.has(sessionId)) {
    res.status(400).json({ error: "Invalid or missing session ID." });
    return;
  }
  await transports.get(sessionId)!.handleRequest(req, res);
});

app.delete("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;
  if (!sessionId || !transports.has(sessionId)) {
    res.status(400).json({ error: "Invalid or missing session ID." });
    return;
  }
  await transports.get(sessionId)!.handleRequest(req, res);
});

async function shutdown() {
  console.log("\n[server] Shutting down...");
  for (const transport of transports.values()) {
    await transport.close();
  }
  await simulators.cleanup();
  console.log("[server] Cleanup complete.");
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

async function main() {
  await simulators.init();

  app.listen(config.port, () => {
    console.log(`[server] Xcode MCP server listening on http://localhost:${config.port}/mcp`);
    console.log(`[server] Repo: ${config.repoPath}`);
    console.log(`[server] Device: ${config.deviceType}, max simulators: ${config.maxSimulators}`);
  });
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
