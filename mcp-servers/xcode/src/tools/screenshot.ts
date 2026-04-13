import { z } from "zod";
import { join } from "node:path";
import { exec } from "../lib/exec.js";
import { resolveWorktree } from "../worktree.js";
import type { SimulatorManager } from "../simulators.js";
import type { Config } from "../config.js";

export const screenshotSchema = z.object({
  branch: z
    .string()
    .describe("Git branch name from `git branch --show-current`"),
  filename: z
    .string()
    .optional()
    .default("screenshot.png")
    .describe("Filename for the screenshot, saved to worktree root"),
});

export async function handleScreenshot(
  params: z.infer<typeof screenshotSchema>,
  config: Config,
  simulators: SimulatorManager
) {
  // Reject path traversal
  if (params.filename.includes("/") || params.filename.includes("..")) {
    return {
      content: [
        {
          type: "text" as const,
          text: "Filename must not contain path separators or '..'",
        },
      ],
      isError: true,
    };
  }

  let worktreePath: string;
  try {
    worktreePath = resolveWorktree(params.branch, config.repoPath);
  } catch (err: any) {
    return { content: [{ type: "text" as const, text: `Error: ${err.message}` }], isError: true };
  }

  let udid: string;
  try {
    udid = await simulators.getSimulator(params.branch);
  } catch (err: any) {
    return { content: [{ type: "text" as const, text: `Error: ${err.message}` }], isError: true };
  }

  const outputPath = join(worktreePath, params.filename);
  const result = await exec(
    "xcrun",
    ["simctl", "io", udid, "screenshot", outputPath],
    { timeoutMs: 15_000 }
  );

  if (result.exitCode !== 0) {
    const hint = result.stderr?.includes("device is not booted")
      ? " Boot the simulator first using the simulator tool with action='boot'."
      : "";
    return {
      content: [
        {
          type: "text" as const,
          text: `Screenshot failed: ${result.stderr || result.stdout}${hint}`,
        },
      ],
      isError: true,
    };
  }

  return {
    content: [
      {
        type: "text" as const,
        text: `Screenshot saved to ${params.filename} in worktree root.`,
      },
    ],
  };
}
