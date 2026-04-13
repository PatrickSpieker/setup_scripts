import { run } from "./helpers/exec.js";

type SimState = "unknown" | "booting" | "booted" | "shutting-down";

const states = new Map<string, SimState>();
const bootPromises = new Map<string, Promise<void>>();

/**
 * Ensure a simulator is booted. Called lazily before any tool that needs it.
 * Deduplicates concurrent boot requests for the same UDID.
 */
export async function ensureBooted(udid: string): Promise<void> {
  const state = states.get(udid) ?? "unknown";

  if (state === "booted") return;

  // If already booting, wait for that boot to finish
  const existing = bootPromises.get(udid);
  if (existing) return existing;

  const promise = bootSimulator(udid);
  bootPromises.set(udid, promise);

  try {
    await promise;
  } finally {
    bootPromises.delete(udid);
  }
}

async function bootSimulator(udid: string): Promise<void> {
  states.set(udid, "booting");

  const result = await run("xcrun", ["simctl", "boot", udid], {
    timeoutMs: 30_000,
  });

  if (result.exitCode === 0) {
    states.set(udid, "booted");
    return;
  }

  // simctl boot fails if already booted — that's fine
  if (result.output.includes("current state: Booted")) {
    states.set(udid, "booted");
    return;
  }

  states.set(udid, "unknown");
  throw new Error(`Failed to boot simulator ${udid}: ${result.output}`);
}

export async function shutdownSimulator(udid: string): Promise<string> {
  states.set(udid, "shutting-down");
  const result = await run("xcrun", ["simctl", "shutdown", udid], {
    timeoutMs: 15_000,
  });
  states.set(udid, "unknown");

  if (result.exitCode !== 0 && !result.output.includes("current state: Shutdown")) {
    return `Warning: shutdown may have failed: ${result.output}`;
  }
  return "Simulator shut down.";
}

export async function getSimulatorStatus(udid: string): Promise<string> {
  const result = await run(
    "xcrun",
    ["simctl", "list", "devices", "-j"],
    { timeoutMs: 10_000, maxOutputChars: 200_000 },
  );

  if (result.exitCode !== 0) return `Error listing devices: ${result.output}`;

  try {
    const data = JSON.parse(result.output);
    for (const runtime of Object.values(data.devices) as Array<
      Array<{ udid: string; state: string; name: string }>
    >) {
      for (const device of runtime) {
        if (device.udid === udid) {
          // Sync our state tracking
          if (device.state === "Booted") states.set(udid, "booted");
          else if (device.state === "Shutdown") states.set(udid, "unknown");
          return `${device.name}: ${device.state}`;
        }
      }
    }
  } catch {
    return `Could not parse device list`;
  }

  return `Simulator ${udid} not found`;
}

/** Shut down all booted simulators. Called on process exit. */
export async function shutdownAll(): Promise<void> {
  const booted = [...states.entries()]
    .filter(([, s]) => s === "booted")
    .map(([udid]) => udid);

  await Promise.allSettled(
    booted.map((udid) => shutdownSimulator(udid)),
  );
}
