import { z } from "zod";
import { accessSync } from "node:fs";
import { join } from "node:path";
import { exec } from "../lib/exec.js";
import { extractBundleId } from "../lib/plist.js";
import { resolveWorktree } from "../worktree.js";
import type { SimulatorManager } from "../simulators.js";
import type { Config } from "../config.js";

export const installAndLaunchSchema = z.object({
  branch: z
    .string()
    .describe("Git branch name from `git branch --show-current`"),
  app_path: z
    .string()
    .describe(
      "Path to .app bundle relative to worktree root, e.g. DerivedData/Build/Products/Debug-iphonesimulator/MyApp.app"
    ),
  bundle_id: z
    .string()
    .optional()
    .describe("CFBundleIdentifier. Extracted from Info.plist if omitted."),
});

export async function handleInstallAndLaunch(
  params: z.infer<typeof installAndLaunchSchema>,
  config: Config,
  simulators: SimulatorManager
) {
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

  const absoluteAppPath = join(worktreePath, params.app_path);
  try {
    accessSync(absoluteAppPath);
  } catch {
    return {
      content: [
        {
          type: "text" as const,
          text: `App bundle not found at ${params.app_path}. Did you run xcodebuild first?`,
        },
      ],
      isError: true,
    };
  }

  let bundleId = params.bundle_id;
  if (!bundleId) {
    try {
      bundleId = await extractBundleId(absoluteAppPath);
    } catch (err: any) {
      return {
        content: [
          {
            type: "text" as const,
            text: `Failed to extract bundle ID: ${err.message}. Pass bundle_id explicitly.`,
          },
        ],
        isError: true,
      };
    }
  }

  // Install
  const installResult = await exec(
    "xcrun",
    ["simctl", "install", udid, absoluteAppPath],
    { timeoutMs: 60_000 }
  );
  if (installResult.exitCode !== 0) {
    const hint = installResult.stderr?.includes("device is not booted")
      ? " Boot the simulator first using the simulator tool with action='boot'."
      : "";
    return {
      content: [
        {
          type: "text" as const,
          text: `Install failed: ${installResult.stderr || installResult.stdout}${hint}`,
        },
      ],
      isError: true,
    };
  }

  // Launch
  const launchResult = await exec(
    "xcrun",
    ["simctl", "launch", udid, bundleId],
    { timeoutMs: 30_000 }
  );
  if (launchResult.exitCode !== 0) {
    return {
      content: [
        {
          type: "text" as const,
          text: `App installed but launch failed: ${launchResult.stderr || launchResult.stdout}`,
        },
      ],
      isError: true,
    };
  }

  return {
    content: [
      {
        type: "text" as const,
        text: `Installed and launched ${bundleId}.\n${launchResult.stdout}`.trim(),
      },
    ],
  };
}
