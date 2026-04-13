import { z } from "zod";
import { readdirSync } from "node:fs";
import { exec } from "../lib/exec.js";
import { resolveWorktree } from "../worktree.js";
import type { SimulatorManager } from "../simulators.js";
import type { Config } from "../config.js";

export const xcodebuildSchema = z.object({
  action: z.enum(["build", "test", "clean"]).describe("Xcode build action"),
  scheme: z.string().describe("Xcode scheme name"),
  branch: z
    .string()
    .describe("Git branch name from `git branch --show-current`"),
  configuration: z
    .enum(["Debug", "Release"])
    .optional()
    .default("Debug")
    .describe("Build configuration (default: Debug)"),
  extra_args: z
    .string()
    .optional()
    .describe(
      "Additional xcodebuild arguments, e.g. CODE_SIGNING_ALLOWED=NO"
    ),
});

function findXcodeProject(worktreePath: string): { flag: string; path: string } {
  const entries = readdirSync(worktreePath);

  // Prefer .xcworkspace over .xcodeproj (CocoaPods/SPM convention)
  const workspace = entries.find((e) => e.endsWith(".xcworkspace"));
  if (workspace) return { flag: "-workspace", path: workspace };

  const project = entries.find((e) => e.endsWith(".xcodeproj"));
  if (project) return { flag: "-project", path: project };

  throw new Error(
    `No Xcode project or workspace found in worktree at ${worktreePath}`
  );
}

export async function handleXcodebuild(
  params: z.infer<typeof xcodebuildSchema>,
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

  let project: { flag: string; path: string };
  try {
    project = findXcodeProject(worktreePath);
  } catch (err: any) {
    return { content: [{ type: "text" as const, text: `Error: ${err.message}` }], isError: true };
  }

  const args = [
    params.action,
    project.flag,
    project.path,
    "-scheme",
    params.scheme,
    "-configuration",
    params.configuration,
    "-destination",
    `platform=iOS Simulator,id=${udid}`,
    "-derivedDataPath",
    "./DerivedData",
  ];

  if (params.extra_args) {
    args.push(...params.extra_args.split(/\s+/));
  }

  const result = await exec("xcodebuild", args, {
    cwd: worktreePath,
    timeoutMs: 300_000,
    maxOutputChars: 4000,
    mergeStderr: true,
  });

  if (result.timedOut) {
    return {
      content: [
        {
          type: "text" as const,
          text: `Build timed out after 5 minutes.\n\n${result.stdout}`,
        },
      ],
      isError: true,
    };
  }

  return {
    content: [{ type: "text" as const, text: result.stdout || "(no output)" }],
    isError: result.exitCode !== 0,
  };
}
