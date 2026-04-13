import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import { gunzipSync } from "node:zlib";
import { resolveWorktree } from "../worktree.js";

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "build_log",
    "Read the most recent Xcode build log for debugging build failures.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
      max_chars: z.number().optional().default(80_000).describe("Max characters to return (tail-truncated)"),
    },
    async ({ branch, max_chars }) => {
      const wt = resolveWorktree(repoId, branch);
      const logsDir = join(wt.derivedData, "Logs", "Build");

      if (!existsSync(logsDir)) {
        return {
          content: [{ type: "text" as const, text: "No build logs found. Build first with xcodebuild." }],
          isError: true,
        };
      }

      // Find most recent .xcactivitylog
      const logs = readdirSync(logsDir)
        .filter((f) => f.endsWith(".xcactivitylog"))
        .map((f) => ({
          name: f,
          path: join(logsDir, f),
          mtime: statSync(join(logsDir, f)).mtimeMs,
        }))
        .sort((a, b) => b.mtime - a.mtime);

      if (logs.length === 0) {
        return {
          content: [{ type: "text" as const, text: "No .xcactivitylog files found in DerivedData." }],
          isError: true,
        };
      }

      const latest = logs[0];
      let content: string;

      try {
        const compressed = readFileSync(latest.path);
        const decompressed = gunzipSync(compressed);
        content = decompressed.toString("utf-8");
      } catch {
        return {
          content: [{ type: "text" as const, text: `Could not decompress build log: ${latest.name}` }],
          isError: true,
        };
      }

      let truncated = false;
      if (content.length > max_chars) {
        const dropped = content.length - max_chars;
        content = `[...truncated ${dropped} chars from beginning...]\n` + content.slice(-max_chars);
        truncated = true;
      }

      return {
        content: [{
          type: "text" as const,
          text: `Build log: ${latest.name}${truncated ? " (truncated)" : ""}\n\n${content}`,
        }],
      };
    },
  );
}
