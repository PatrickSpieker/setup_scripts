import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readFileSync, unlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { run } from "../helpers/exec.js";
import { loadConfig, getSimUdid } from "../config.js";
import { ensureBooted } from "../simulator.js";

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "screenshot",
    "Capture a screenshot of the simulator screen. Returns a PNG image.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
    },
    async ({ branch }) => {
      const config = loadConfig(repoId);
      const udid = getSimUdid(config, branch);

      await ensureBooted(udid);

      const tmpPath = join(tmpdir(), `screenshot-${udid}-${Date.now()}.png`);

      const result = await run(
        "xcrun", ["simctl", "io", udid, "screenshot", tmpPath],
        { timeoutMs: 15_000 },
      );

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Screenshot failed:\n${result.output}` }],
          isError: true,
        };
      }

      try {
        const data = readFileSync(tmpPath);
        const base64 = data.toString("base64");

        return {
          content: [{
            type: "image" as const,
            data: base64,
            mimeType: "image/png" as const,
          }],
        };
      } finally {
        try { unlinkSync(tmpPath); } catch { /* ignore cleanup errors */ }
      }
    },
  );
}
