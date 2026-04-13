import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { run } from "../helpers/exec.js";
import { resolveWorktree, findXcodeProject } from "../worktree.js";

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "resolve_dependencies",
    "Resolve Swift Package Manager dependencies for the project.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
    },
    async ({ branch }) => {
      const wt = resolveWorktree(repoId, branch);
      const xcode = findXcodeProject(wt.path);

      const result = await run("xcodebuild", [
        xcode.type === "workspace" ? "-workspace" : "-project",
        xcode.path,
        "-resolvePackageDependencies",
        "-derivedDataPath", wt.derivedData,
      ], {
        cwd: wt.path,
        timeoutMs: 300_000, // SPM resolution can be slow
      });

      const status = result.exitCode === 0 ? "RESOLVED" : "FAILED";

      return {
        content: [{
          type: "text" as const,
          text: `## Dependencies ${status} (${(result.durationMs / 1000).toFixed(1)}s)\n\n${result.output}`,
        }],
        isError: result.exitCode !== 0,
      };
    },
  );
}
