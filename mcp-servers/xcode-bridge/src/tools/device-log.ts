import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { run } from "../helpers/exec.js";
import { loadConfig, getSimUdid } from "../config.js";
import { ensureBooted } from "../simulator.js";

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "device_log",
    "Read recent simulator system log, optionally filtered by subsystem or process.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
      subsystem: z.string().optional().describe("Filter by subsystem (e.g. com.myapp.bundle)"),
      process_name: z.string().optional().describe("Filter by process name"),
      minutes: z.number().optional().default(5).describe("How many minutes of logs to fetch"),
    },
    async ({ branch, subsystem, process_name, minutes }) => {
      const config = loadConfig(repoId);
      const udid = getSimUdid(config, branch);

      await ensureBooted(udid);

      // Build predicate for log filtering
      const predicates: string[] = [];
      if (subsystem) predicates.push(`subsystem == "${subsystem}"`);
      if (process_name) predicates.push(`process == "${process_name}"`);

      const args = [
        "simctl", "spawn", udid,
        "log", "show",
        "--last", `${minutes}m`,
        "--style", "compact",
      ];

      if (predicates.length > 0) {
        args.push("--predicate", predicates.join(" AND "));
      }

      const result = await run("xcrun", args, {
        timeoutMs: 30_000,
        maxOutputChars: 40_000,
      });

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Failed to read device log:\n${result.output}` }],
          isError: true,
        };
      }

      const logLines = result.output.trim().split("\n").length;

      return {
        content: [{
          type: "text" as const,
          text: `Device log (last ${minutes}m, ${logLines} lines${result.truncated ? ", truncated" : ""}):\n\n${result.output}`,
        }],
      };
    },
  );
}
