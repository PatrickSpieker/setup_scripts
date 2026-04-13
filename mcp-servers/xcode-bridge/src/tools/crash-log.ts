import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import { crashLogDir } from "../helpers/paths.js";

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "crash_log",
    "Read recent crash logs. Optionally filter by process name.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
      process_name: z.string().optional().describe("Filter by process name (e.g. app name)"),
      max_chars: z.number().optional().default(40_000),
    },
    async ({ branch: _branch, process_name, max_chars }) => {
      const dir = crashLogDir();
      if (!existsSync(dir)) {
        return {
          content: [{ type: "text" as const, text: "No DiagnosticReports directory found." }],
          isError: true,
        };
      }

      // Find recent crash/ips files (last 30 min)
      const cutoff = Date.now() - 30 * 60_000;
      let files = readdirSync(dir)
        .filter((f) => f.endsWith(".ips") || f.endsWith(".crash"))
        .map((f) => {
          const path = join(dir, f);
          return { name: f, path, mtime: statSync(path).mtimeMs };
        })
        .filter((f) => f.mtime > cutoff)
        .sort((a, b) => b.mtime - a.mtime);

      if (process_name) {
        files = files.filter((f) =>
          f.name.toLowerCase().includes(process_name.toLowerCase()),
        );
      }

      if (files.length === 0) {
        return {
          content: [{
            type: "text" as const,
            text: `No recent crash logs found${process_name ? ` for "${process_name}"` : ""} (checked last 30 min).`,
          }],
        };
      }

      // Read the most recent one
      const latest = files[0];
      let content = readFileSync(latest.path, "utf-8");

      if (content.length > max_chars) {
        content = content.slice(0, max_chars) + "\n[...truncated]";
      }

      return {
        content: [{
          type: "text" as const,
          text: `Crash log: ${latest.name}\n\n${content}`,
        }],
      };
    },
  );
}
