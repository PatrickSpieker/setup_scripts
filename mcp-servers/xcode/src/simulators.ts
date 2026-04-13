import { exec } from "./lib/exec.js";
import type { Config } from "./config.js";

export class SimulatorCapacityError extends Error {
  code = "SIMULATOR_CAPACITY";
  constructor(max: number) {
    super(`Maximum simulator count (${max}) reached. Shut down an existing branch's simulator first.`);
  }
}

interface SimulatorDevice {
  udid: string;
  name: string;
  state: string;
}

export class SimulatorManager {
  private branchToUdid = new Map<string, string>();
  private latestRuntime: string | null = null;
  private config: Config;

  constructor(config: Config) {
    this.config = config;
  }

  async init(): Promise<void> {
    await this.cleanupLeftovers();
    this.latestRuntime = await this.findLatestRuntime();
    console.log(`[simulators] Using iOS runtime: ${this.latestRuntime}`);
  }

  async getSimulator(branch: string): Promise<string> {
    const existing = this.branchToUdid.get(branch);
    if (existing) return existing;

    if (this.branchToUdid.size >= this.config.maxSimulators) {
      throw new SimulatorCapacityError(this.config.maxSimulators);
    }

    const name = `Moat-${branch}`;
    const runtime = this.latestRuntime!;
    const result = await exec(
      "xcrun",
      ["simctl", "create", name, this.config.deviceType, runtime],
      { timeoutMs: 30_000 }
    );

    if (result.exitCode !== 0) {
      throw new Error(`Failed to create simulator '${name}': ${result.stderr || result.stdout}`);
    }

    const udid = result.stdout.trim();
    this.branchToUdid.set(branch, udid);
    console.log(`[simulators] Created ${name} (${udid}) for branch '${branch}'`);
    return udid;
  }

  async cleanup(): Promise<void> {
    for (const [branch, udid] of this.branchToUdid) {
      console.log(`[simulators] Cleaning up Moat-${branch} (${udid})`);
      await exec("xcrun", ["simctl", "shutdown", udid], { timeoutMs: 10_000 });
      await exec("xcrun", ["simctl", "delete", udid], { timeoutMs: 10_000 });
    }
    this.branchToUdid.clear();
  }

  private async cleanupLeftovers(): Promise<void> {
    const devices = await this.listMoatDevices();
    for (const device of devices) {
      console.log(`[simulators] Removing leftover simulator: ${device.name} (${device.udid})`);
      await exec("xcrun", ["simctl", "shutdown", device.udid], { timeoutMs: 10_000 });
      await exec("xcrun", ["simctl", "delete", device.udid], { timeoutMs: 10_000 });
    }
  }

  private async listMoatDevices(): Promise<SimulatorDevice[]> {
    const result = await exec("xcrun", ["simctl", "list", "devices", "-j"], {
      timeoutMs: 10_000,
    });
    if (result.exitCode !== 0) return [];

    const data = JSON.parse(result.stdout);
    const devices: SimulatorDevice[] = [];

    for (const runtime of Object.values(data.devices) as SimulatorDevice[][]) {
      for (const device of runtime) {
        if (device.name.startsWith("Moat-")) {
          devices.push(device);
        }
      }
    }

    return devices;
  }

  private async findLatestRuntime(): Promise<string> {
    const result = await exec("xcrun", ["simctl", "list", "runtimes", "-j"], {
      timeoutMs: 10_000,
    });

    if (result.exitCode !== 0) {
      throw new Error(`Failed to list runtimes: ${result.stderr || result.stdout}`);
    }

    const data = JSON.parse(result.stdout);
    const iosRuntimes = (data.runtimes as Array<{ identifier: string; name: string; isAvailable: boolean }>)
      .filter((r) => r.name.startsWith("iOS") && r.isAvailable);

    if (iosRuntimes.length === 0) {
      throw new Error("No available iOS runtimes found. Install one via Xcode.");
    }

    // Last entry is the newest
    return iosRuntimes[iosRuntimes.length - 1].identifier;
  }
}
