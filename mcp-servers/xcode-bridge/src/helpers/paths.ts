import { homedir } from "node:os";
import { join } from "node:path";

const HOME = homedir();

export function worktreePath(repoId: string, branch: string): string {
  return join(HOME, ".moat", "worktrees", repoId, branch);
}

export function derivedDataPath(repoId: string, branch: string): string {
  return join(worktreePath(repoId, branch), "DerivedData");
}

export function configPath(repoId: string): string {
  return join(HOME, ".moat", "xcode-bridge", repoId + ".json");
}

export function simLogDir(simUdid: string): string {
  return join(HOME, "Library", "Logs", "CoreSimulator", simUdid);
}

export function crashLogDir(): string {
  return join(HOME, "Library", "Logs", "DiagnosticReports");
}
