import { execFile as cpExecFile } from "node:child_process";

export interface ExecResult {
  exitCode: number;
  output: string;
  truncated: boolean;
  durationMs: number;
}

/**
 * Run a command with timeout and tail-truncation.
 * Uses execFile (not exec) to avoid shell injection.
 */
export async function run(
  cmd: string,
  args: string[],
  opts?: {
    cwd?: string;
    timeoutMs?: number;
    maxOutputChars?: number;
    env?: Record<string, string>;
  },
): Promise<ExecResult> {
  const timeoutMs = opts?.timeoutMs ?? 300_000;
  const maxChars = opts?.maxOutputChars ?? 80_000;

  const start = Date.now();

  return new Promise((resolve) => {
    const proc = cpExecFile(
      cmd,
      args,
      {
        cwd: opts?.cwd,
        env: opts?.env ? { ...process.env, ...opts.env } : undefined,
        maxBuffer: 50 * 1024 * 1024, // 50 MB
        timeout: timeoutMs,
        killSignal: "SIGTERM",
      },
      (error, stdout, stderr) => {
        const durationMs = Date.now() - start;
        let combined = stdout + (stderr ? "\n" + stderr : "");
        let truncated = false;

        if (combined.length > maxChars) {
          const dropped = combined.length - maxChars;
          combined =
            `[...truncated ${dropped} chars from beginning...]\n` +
            combined.slice(-maxChars);
          truncated = true;
        }

        const exitCode = error
          ? (error as NodeJS.ErrnoException & { code?: number | string })
                .code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER"
            ? 1
            : (proc.exitCode ?? 1)
          : 0;

        resolve({ exitCode, output: combined, truncated, durationMs });
      },
    );
  });
}
