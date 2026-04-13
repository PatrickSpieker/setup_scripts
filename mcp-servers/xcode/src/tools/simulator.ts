import { z } from "zod";
import { exec } from "../lib/exec.js";
import type { SimulatorManager } from "../simulators.js";

export const simulatorSchema = z.object({
  action: z
    .enum(["boot", "shutdown", "status"])
    .describe("Simulator action"),
  branch: z
    .string()
    .describe("Git branch name from `git branch --show-current`"),
});

export async function handleSimulator(
  params: z.infer<typeof simulatorSchema>,
  simulators: SimulatorManager
) {
  let udid: string;
  try {
    udid = await simulators.getSimulator(params.branch);
  } catch (err: any) {
    return { content: [{ type: "text" as const, text: `Error: ${err.message}` }], isError: true };
  }

  switch (params.action) {
    case "boot": {
      const result = await exec("xcrun", ["simctl", "boot", udid], {
        timeoutMs: 30_000,
      });
      // Exit code 149 = already booted
      if (result.exitCode === 0 || result.exitCode === 149) {
        return {
          content: [
            {
              type: "text" as const,
              text:
                result.exitCode === 149
                  ? "Simulator already booted."
                  : "Simulator booted successfully.",
            },
          ],
        };
      }
      return {
        content: [
          {
            type: "text" as const,
            text: `Failed to boot simulator: ${result.stderr || result.stdout}`,
          },
        ],
        isError: true,
      };
    }

    case "shutdown": {
      const result = await exec("xcrun", ["simctl", "shutdown", udid], {
        timeoutMs: 15_000,
      });
      if (result.exitCode === 0 || result.exitCode === 149) {
        return {
          content: [{ type: "text" as const, text: "Simulator shut down." }],
        };
      }
      return {
        content: [
          {
            type: "text" as const,
            text: `Failed to shut down simulator: ${result.stderr || result.stdout}`,
          },
        ],
        isError: true,
      };
    }

    case "status": {
      const result = await exec(
        "xcrun",
        ["simctl", "list", "devices", "-j"],
        { timeoutMs: 10_000 }
      );
      if (result.exitCode !== 0) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Failed to query simulator status: ${result.stderr}`,
            },
          ],
          isError: true,
        };
      }

      const data = JSON.parse(result.stdout);
      for (const devices of Object.values(data.devices) as Array<
        Array<{ udid: string; name: string; state: string }>
      >) {
        const device = devices.find((d) => d.udid === udid);
        if (device) {
          return {
            content: [
              {
                type: "text" as const,
                text: `${device.name}: ${device.state}`,
              },
            ],
          };
        }
      }

      return {
        content: [
          {
            type: "text" as const,
            text: `Simulator ${udid} not found in device list.`,
          },
        ],
        isError: true,
      };
    }
  }
}
