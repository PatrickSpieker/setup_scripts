import { exec } from "./exec.js";

export async function extractBundleId(appPath: string): Promise<string> {
  const result = await exec(
    "/usr/libexec/PlistBuddy",
    ["-c", "Print :CFBundleIdentifier", `${appPath}/Info.plist`],
    { timeoutMs: 5_000 }
  );

  if (result.exitCode !== 0) {
    throw new Error(
      `Failed to extract bundle ID from ${appPath}/Info.plist: ${result.stderr || result.stdout}`
    );
  }

  const bundleId = result.stdout.trim();
  if (!bundleId) {
    throw new Error(`CFBundleIdentifier is empty in ${appPath}/Info.plist`);
  }

  return bundleId;
}
