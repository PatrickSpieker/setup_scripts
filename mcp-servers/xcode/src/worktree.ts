import { readdirSync, readFileSync, accessSync } from "node:fs";
import { join } from "node:path";

export class WorktreeNotFoundError extends Error {
  code = "WORKTREE_NOT_FOUND";
  constructor(branch: string) {
    super(`No active worktree found for branch '${branch}'. Is the agent running?`);
  }
}

export function resolveWorktree(branch: string, repoPath: string): string {
  const worktreesDir = join(repoPath, ".moat", "worktrees");

  let entries: string[];
  try {
    entries = readdirSync(worktreesDir);
  } catch {
    throw new WorktreeNotFoundError(branch);
  }

  for (const runId of entries) {
    const branchFile = join(worktreesDir, runId, "branch");
    try {
      const branchName = readFileSync(branchFile, "utf-8").trim();
      if (branchName === branch) {
        const workspace = join(worktreesDir, runId, "workspace");
        accessSync(workspace);
        return workspace;
      }
    } catch {
      continue;
    }
  }

  throw new WorktreeNotFoundError(branch);
}
