import { readFileSync } from "node:fs";
import { z } from "zod";
import { configPath } from "./helpers/paths.js";

const ConfigSchema = z.object({
  slots: z.record(z.string(), z.string()), // branch -> simulator UDID
});

export type Config = z.infer<typeof ConfigSchema>;

let loaded: Config | null = null;
let loadedRepoId: string | null = null;

export function loadConfig(repoId: string): Config {
  if (loaded && loadedRepoId === repoId) return loaded;

  const path = configPath(repoId);
  let raw: unknown;
  try {
    raw = JSON.parse(readFileSync(path, "utf-8"));
  } catch (e) {
    throw new Error(
      `Could not read config at ${path}. Run setup-xcode-agents.sh first.`,
    );
  }

  loaded = ConfigSchema.parse(raw);
  loadedRepoId = repoId;
  return loaded;
}

export function getSimUdid(config: Config, branch: string): string {
  const udid = config.slots[branch];
  if (!udid) {
    const available = Object.keys(config.slots).join(", ");
    throw new Error(
      `Branch "${branch}" not in config. Available slots: ${available}`,
    );
  }
  return udid;
}
