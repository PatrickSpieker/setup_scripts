import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { run } from "../helpers/exec.js";
import { loadConfig, getSimUdid } from "../config.js";
import { resolveWorktree, findXcodeProject } from "../worktree.js";
import { ensureBooted } from "../simulator.js";

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "xcodebuild",
    "Build, test, or clean an Xcode project. Returns build output with error summary.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
      action: z.enum(["build", "test", "clean"]).describe("Xcode build action"),
      scheme: z.string().optional().describe("Scheme name (omit to use first discovered scheme)"),
      configuration: z.enum(["Debug", "Release"]).optional().default("Debug"),
    },
    async ({ branch, action, scheme, configuration }) => {
      const config = loadConfig(repoId);
      const udid = getSimUdid(config, branch);
      const wt = resolveWorktree(repoId, branch);
      const xcode = findXcodeProject(wt.path);

      // Boot simulator for build/test (not needed for clean)
      if (action !== "clean") {
        await ensureBooted(udid);
      }

      const args = [
        xcode.type === "workspace" ? "-workspace" : "-project",
        xcode.path,
        `-derivedDataPath`, wt.derivedData,
        `-configuration`, configuration,
        `-destination`, `id=${udid}`,
        action,
      ];

      // Resolve scheme if not provided
      if (scheme) {
        args.splice(2, 0, "-scheme", scheme);
      } else {
        // Auto-discover first scheme
        const listResult = await run("xcodebuild", [
          xcode.type === "workspace" ? "-workspace" : "-project",
          xcode.path,
          "-list", "-json",
        ], { timeoutMs: 15_000 });

        if (listResult.exitCode === 0) {
          try {
            const parsed = JSON.parse(listResult.output);
            const key = xcode.type === "workspace" ? "workspace" : "project";
            const schemes: string[] = parsed[key]?.schemes ?? [];
            if (schemes.length > 0) {
              args.splice(2, 0, "-scheme", schemes[0]);
            }
          } catch {
            // Fall through without scheme — xcodebuild may still work
          }
        }
      }

      const result = await run("xcodebuild", args, {
        cwd: wt.path,
        timeoutMs: 600_000, // 10 min for builds
      });

      // Extract error summary from output
      const lines = result.output.split("\n");
      const errors = lines
        .slice(-200)
        .filter((l) => l.includes("error:"))
        .slice(0, 20);

      const status = result.exitCode === 0 ? "SUCCEEDED" : "FAILED";
      const summary = [
        `## ${action.toUpperCase()} ${status} (exit ${result.exitCode}, ${(result.durationMs / 1000).toFixed(1)}s)`,
      ];

      if (errors.length > 0) {
        summary.push("", `### Errors (${errors.length}):`, ...errors);
      }

      if (result.truncated) {
        summary.push("", "### Full Output (truncated):");
      } else {
        summary.push("", "### Full Output:");
      }

      return {
        content: [{
          type: "text" as const,
          text: summary.join("\n") + "\n" + result.output,
        }],
        isError: result.exitCode !== 0,
      };
    },
  );
}
