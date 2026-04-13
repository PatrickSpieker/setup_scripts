import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { run } from "../helpers/exec.js";
import { loadConfig, getSimUdid } from "../config.js";
import { resolveWorktree } from "../worktree.js";
import { ensureBooted } from "../simulator.js";

/**
 * Find the .app bundle in DerivedData/Build/Products/<config>-iphonesimulator/
 */
function findAppBundle(derivedData: string): string | null {
  const productsDir = join(derivedData, "Build", "Products");
  if (!existsSync(productsDir)) return null;

  for (const config of readdirSync(productsDir)) {
    if (!config.endsWith("-iphonesimulator")) continue;
    const configDir = join(productsDir, config);
    for (const entry of readdirSync(configDir)) {
      if (entry.endsWith(".app")) {
        return join(configDir, entry);
      }
    }
  }
  return null;
}

/**
 * Extract CFBundleIdentifier from Info.plist inside the .app
 */
async function getBundleId(appPath: string): Promise<string | null> {
  const result = await run(
    "/usr/libexec/PlistBuddy",
    ["-c", "Print:CFBundleIdentifier", join(appPath, "Info.plist")],
    { timeoutMs: 5_000 },
  );
  return result.exitCode === 0 ? result.output.trim() : null;
}

export function register(server: McpServer, repoId: string): void {
  server.tool(
    "install_and_launch",
    "Install the built .app on the simulator and launch it.",
    {
      branch: z.string().describe("Your current git branch (from `git branch --show-current`)"),
      bundle_id: z.string().optional().describe("Bundle identifier (auto-detected from .app if omitted)"),
    },
    async ({ branch, bundle_id }) => {
      const config = loadConfig(repoId);
      const udid = getSimUdid(config, branch);
      const wt = resolveWorktree(repoId, branch);

      await ensureBooted(udid);

      const appPath = findAppBundle(wt.derivedData);
      if (!appPath) {
        return {
          content: [{ type: "text" as const, text: "No .app found in DerivedData. Build first with xcodebuild." }],
          isError: true,
        };
      }

      // Install
      const install = await run(
        "xcrun", ["simctl", "install", udid, appPath],
        { timeoutMs: 30_000 },
      );
      if (install.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Install failed:\n${install.output}` }],
          isError: true,
        };
      }

      // Resolve bundle ID
      const resolvedBundleId = bundle_id ?? await getBundleId(appPath);
      if (!resolvedBundleId) {
        return {
          content: [{ type: "text" as const, text: "Installed app but could not determine bundle ID to launch. Pass bundle_id explicitly." }],
          isError: true,
        };
      }

      // Launch
      const launch = await run(
        "xcrun", ["simctl", "launch", udid, resolvedBundleId],
        { timeoutMs: 15_000 },
      );

      if (launch.exitCode !== 0) {
        return {
          content: [{ type: "text" as const, text: `Installed but launch failed:\n${launch.output}` }],
          isError: true,
        };
      }

      return {
        content: [{
          type: "text" as const,
          text: `Installed and launched ${resolvedBundleId} on simulator.\nApp: ${appPath}\n${launch.output}`,
        }],
      };
    },
  );
}
