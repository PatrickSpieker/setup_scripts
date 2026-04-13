import { accessSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

export interface Config {
  port: number;
  repoPath: string;
  deviceType: string;
  maxSimulators: number;
}

const CONFIG_PATH = join(homedir(), ".config", "xcode-mcp", "config.json");

function loadJsonConfig(): Partial<Config> {
  try {
    const raw = readFileSync(CONFIG_PATH, "utf-8");
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

export function loadConfig(): Config {
  const json = loadJsonConfig();

  const repoPath = process.env.XCODE_MCP_REPO_PATH ?? json.repoPath;
  if (!repoPath) {
    console.error(
      "XCODE_MCP_REPO_PATH env var or repoPath in ~/.config/xcode-mcp/config.json is required"
    );
    process.exit(1);
  }

  try {
    accessSync(repoPath);
  } catch {
    console.error(`Repo path does not exist: ${repoPath}`);
    process.exit(1);
  }

  const port = Number(process.env.XCODE_MCP_PORT) || json.port || 3100;
  const deviceType =
    process.env.XCODE_MCP_DEVICE_TYPE ?? json.deviceType ?? "iPhone 16";
  const maxSimulators =
    Number(process.env.XCODE_MCP_MAX_SIMULATORS) || json.maxSimulators || 5;

  return { port, repoPath, deviceType, maxSimulators };
}
