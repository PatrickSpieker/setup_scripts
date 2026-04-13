import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { worktreePath, derivedDataPath } from "./helpers/paths.js";

export interface ResolvedWorktree {
  path: string;
  derivedData: string;
}

export function resolveWorktree(
  repoId: string,
  branch: string,
): ResolvedWorktree {
  const wt = worktreePath(repoId, branch);
  if (!existsSync(wt)) {
    throw new Error(
      `Worktree not found at ${wt}. Is the agent container running on branch "${branch}"?`,
    );
  }
  return {
    path: wt,
    derivedData: derivedDataPath(repoId, branch),
  };
}

/**
 * Find the Xcode workspace or project in a worktree.
 * Prefers .xcworkspace over .xcodeproj (CocoaPods/SPM generate workspaces).
 * Searches root and one level deep (handles ios/ subdirs in monorepos).
 */
export function findXcodeProject(
  worktreePath: string,
): { type: "workspace" | "project"; path: string } {
  // Check root first, then one level deep
  const dirsToCheck = [worktreePath];

  try {
    for (const entry of readdirSync(worktreePath, { withFileTypes: true })) {
      if (entry.isDirectory() && !entry.name.startsWith(".")) {
        dirsToCheck.push(join(worktreePath, entry.name));
      }
    }
  } catch {
    // If we can't read the dir, just check root
  }

  for (const dir of dirsToCheck) {
    let entries: string[];
    try {
      entries = readdirSync(dir).filter(
        (e) => !e.startsWith("."),
      );
    } catch {
      continue;
    }

    // Prefer workspace, but skip the one nested inside .xcodeproj
    const workspace = entries.find(
      (e) => e.endsWith(".xcworkspace") && !dir.endsWith(".xcodeproj"),
    );
    if (workspace) {
      return { type: "workspace", path: join(dir, workspace) };
    }

    const project = entries.find((e) => e.endsWith(".xcodeproj"));
    if (project) {
      return { type: "project", path: join(dir, project) };
    }
  }

  throw new Error(
    `No .xcworkspace or .xcodeproj found in ${worktreePath} (checked root + 1 level deep)`,
  );
}
