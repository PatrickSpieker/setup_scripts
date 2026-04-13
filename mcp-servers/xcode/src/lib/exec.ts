import { spawn } from "node:child_process";

export interface ExecResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  timedOut: boolean;
}

export interface ExecOptions {
  cwd?: string;
  timeoutMs?: number;
  maxOutputChars?: number;
  mergeStderr?: boolean;
  env?: Record<string, string>;
}

export function exec(
  command: string,
  args: string[],
  options: ExecOptions = {}
): Promise<ExecResult> {
  const { cwd, timeoutMs, maxOutputChars, mergeStderr, env } = options;

  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd,
      stdio: "pipe",
      detached: true,
      env: env ? { ...process.env, ...env } : undefined,
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk: Buffer) => {
      if (mergeStderr) {
        stdout += chunk.toString();
      } else {
        stderr += chunk.toString();
      }
    });

    if (timeoutMs) {
      timer = setTimeout(() => {
        timedOut = true;
        try {
          process.kill(-child.pid!, "SIGKILL");
        } catch {
          child.kill("SIGKILL");
        }
      }, timeoutMs);
    }

    child.on("close", (code) => {
      if (timer) clearTimeout(timer);

      if (maxOutputChars && stdout.length > maxOutputChars) {
        stdout =
          `[...truncated, showing last ${maxOutputChars} chars...]\n` +
          stdout.slice(-maxOutputChars);
      }

      resolve({
        stdout,
        stderr,
        exitCode: code ?? 1,
        timedOut,
      });
    });

    child.on("error", (err) => {
      if (timer) clearTimeout(timer);
      resolve({
        stdout,
        stderr: stderr || err.message,
        exitCode: 1,
        timedOut: false,
      });
    });
  });
}
