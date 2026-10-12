# Codex conversation flame chart

Turn local Codex records into a fixed, offline HTML timeline. The main agent and its descendants have horizontal lanes on a shared time axis. The skill accepts a pasted `codex://threads/<UUID>` link.

## Install

Python 3.11 or newer. From the setup_scripts repository:

```bash
python3 -m venv ~/.local/share/codex-flamechart/venv
```

```bash
~/.local/share/codex-flamechart/venv/bin/python -m pip install -r scripts/codex_trace/requirements.lock
```

The lock pins the full rendering dependency set, including bundled Vega assets. No dependencies or server are needed to view the resulting HTML. Installation does not modify Codex records or configuration.

## Run

```bash
~/.local/share/codex-flamechart/venv/bin/python scripts/codex_flamechart.py codex://threads/01a116a6-54cb-7013-b78e-b06677c418d9 --output conversation.html --open
```

`--output` defaults to `~/Desktop/<thread-id>.html`. Supply `--output` to choose another destination. `--codex-home` overrides `CODEX_HOME`, otherwise `~/.codex` is used. Only `--open` launches a browser. An existing report is replaced atomically after successful generation. A failed run preserves it.

The skill's `scripts/run.py` resolves symlinks to this repository and uses the environment above. Set `CODEX_FLAMECHART_PYTHON` to use another compatible Python environment.

## Reading the report

- Drag horizontally to pan; scroll over the chart to zoom. Reset zoom restores the full snapshot. The details panel’s “Zoom to action” button focuses short events in long conversations. Filter by category or search action names/IDs.
- Bars show recorded intervals. Diamonds show point records, zero-duration records, or unfinished actions. Click either, or select an action from the searchable list, for full recorded details.
- Elapsed seconds appear on the axis; absolute timestamps use UTC. Observation-only bars represent call/output record arrival, **not measured execution duration**. Their execution duration stays unknown.
- Nesting requires explicit parent IDs. An overlapping call without parent evidence gets another row at the same depth; no relationship is inferred from time containment. Missing and conflicting timestamps remain visible in details.
- Unfinished actions have no fabricated duration. Untimed actions remain searchable and are labeled `[untimed]`. Long details are expandable; the action list is paginated without truncating the data.
- Incomplete-data notices identify missing sources, malformed records, unsupported formats, and unresolved descendants. The report contains raw conversation text and tool output; choose its destination accordingly.

## Source coverage

Adapters inspect schemas rather than relying solely on database filenames. The newest state/history database is used; unsupported schemas are diagnosed, with rollouts used where available. Tested against local Codex 0.160.0 and 0.162.0-alpha.17.2 records:

- `threads`, `thread_spawn_edges`, and `thread_items` projections, including archived rollout paths.
- JSONL `item_started`/`item_completed` events, response calls/results, user/assistant/reasoning fallbacks, and legacy command/MCP/search/patch begin/end pairs.
- Other event messages are retained as raw actions, including approvals and lifecycle events. Unknown top-level record types produce diagnostics.

Structured items take precedence over their transcript representations. IDs reconcile tool calls and outputs. Messages can also match by turn and exact text; attachment-expanded prompts align by submission order only when both representations have the same count. These matches are labeled in details. Unmatched messages remain visible, including when the history projection lags. Copied subagent context with a foreign turn ID is excluded. System/developer context, user-role content explicitly tagged as injected context, configuration/world-state records, token-accounting updates, communication metadata, and replacement history inside compaction records are not separate executed actions. Agent messages themselves are retained. Hidden reasoning and unlogged shell internals cannot be recovered.

Each database is read inside its own read-only transaction; each rollout is read only through its captured byte boundary. These boundaries are listed in the report. Sources are not globally atomic, so an active conversation may have unmatched calls or lagging projections. Byte determinism applies to identical captured inputs and pinned dependencies, not a thread that continues writing.

## Tests

Install `pytest` and `pyyaml` in the isolated environment, then:

```bash
~/.local/share/codex-flamechart/venv/bin/python -m pytest tests/test_codex_flamechart.py tests/test_skill_structure.py -v
```

The optional offline browser test also requires `playwright` and Chromium. Set `CODEX_FLAMECHART_TEST_BROWSER` to the Chromium executable and rerun the same command. The browser context disables networking and checks lanes, filtering, details, and zoom.

Large-trace and real-conversation validation results are recorded in the PR. No event-count performance guarantee is imposed; all captured actions remain in the report.
