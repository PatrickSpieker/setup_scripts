import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { run } from "../helpers/exec.js";
import { resolveWorktree, findXcodeProject } from "../worktree.js";

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "list_schemes",
    "Discover available schemes and targets in the Xcode project.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
    },
    async ({ branch }) => {
      const wt = resolveWorktree(repoId, branch);
      const xcode = findXcodeProject(wt.path);

      const result = await run("xcodebuild", [
        xcode.type === "workspace" ? "-workspace" : "-project",
        xcode.path,
        "-list", "-json",
      ], { timeoutMs: 15_000 });

      if (result.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Failed to list schemes:\n${result.output}` }],
          isError: true,
        };
      }

      try {
        const parsed = JSON.parse(result.output);
        const key = xcode.type === "workspace" ? "workspace" : "project";
        const info = parsed[key];

        const lines = [
          `Project: ${info?.name ?? "unknown"} (${xcode.type})`,
          `Path: ${xcode.path}`,
          "",
          "Schemes:",
          ...(info?.schemes ?? []).map((s: string) => `  - ${s}`),
        ];

        if (info?.targets) {
          lines.push("", "Targets:", ...info.targets.map((t: string) => `  - ${t}`));
        }

        return { content: [{ type: "text" as const, text: lines.join("\n") }] };
      } catch {
        return { content: [{ type: "text" as const, text: result.output }] };
      }
    },
  );
}
