# Codex exec guide

Use `codex exec` (or `codex e`) for non-interactive runs.

## Codex CLI features (context)
Interactive mode:
- `codex` launches the full-screen UI for conversational workflows.
- `codex "Explain this codebase to me"` starts with an initial prompt.
- Use `/exit` or Ctrl+C to close.

Resume sessions:
- `codex resume` opens the picker for interactive sessions.
- `codex resume --all` shows sessions across directories.
- `codex resume --last` jumps to the most recent session.
- `codex resume <SESSION_ID>` targets a specific run.
- `codex exec resume --last "<prompt>"` resumes a non-interactive run.
- `codex exec resume <SESSION_ID> "<prompt>"` resumes by ID.
- Use `--cd` or `--add-dir` when resuming to adjust roots.

Models and reasoning:
- Model and reasoning effort are separate knobs. Pin both in
  `~/.codex/config.toml`, or override on launch:
  `codex --model gpt-5.4 --config model_reasoning_effort=high`.
- Switch model mid-session with `/model`.

Image inputs:
- `codex -i screenshot.png "Explain this error"`
- `codex --image img1.png,img2.jpg "Summarize these diagrams"`

## Common flags
- `--cd PATH` set workspace root for the run
- `--json` output newline-delimited JSON events
- `--model NAME` override model
- `--full-auto` use low-friction automation preset
- `--sandbox read-only|workspace-write|danger-full-access` set sandbox
- `--output-last-message PATH` write final message to a file
- `--skip-git-repo-check` allow running outside a Git repo
- `resume <SESSION_ID>` continue a prior exec session

Avoid `--yolo` unless running in an isolated runner.

## Model selection

Two separate knobs:

- **Model**: `gpt-5.4` (recommended general-purpose) or `gpt-5.4-mini`
  (faster, lower-depth). Newer families (e.g. `gpt-5.5`) may exist — check
  `codex --help` or the Codex changelog.
- **Reasoning effort** (`model_reasoning_effort`): `minimal | low | medium |
  high | xhigh`. `xhigh` is model-dependent.

Defaults pinned in this repo:

- Host (`defaults/codex-config.toml`): `gpt-5.5` + `xhigh`
- Moat container (`defaults/codex-moat-config.toml`): `gpt-5.4` + `xhigh`

Heuristics:

- Light reads, scans, summaries → `gpt-5.4-mini` + `low` or `medium`.
- Default day-to-day work → `gpt-5.4` + `medium` or `high`.
- Hardest reasoning / multi-step refactors → top model + `high` or `xhigh`.

Override on launch:

```
codex --model gpt-5.4-mini --config model_reasoning_effort=low
```

## Code reading workflow
Start with discovery:
- `rg --files` to get a quick file list.
- `rg -n \"<keyword>\" -S` to find relevant locations.
- Read `AGENTS.md`/`CLAUDE.md`/`README.md` if present.

Minimize context bloat:
- Open only the files needed for the current step.
- Prefer small, targeted excerpts over whole files.
- Summarize long files instead of copying them wholesale.

When asked to change code:
- Locate the narrowest owning module.
- Trace call sites before editing.
- Note any tests or scripts affected.
