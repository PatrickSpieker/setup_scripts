"""Adapters for paginated item history and legacy JSONL rollout events."""

import json
import math
import re
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from .model import CATEGORIES, Action, canonical, layout, milliseconds


class TraceError(Exception):
    pass


def decode(text):
    def finite(number):
        value = float(number)
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        return value

    return json.loads(text, parse_float=finite, parse_constant=finite)


def thread_id(link):
    parts = urlsplit(link)
    if (
        parts.scheme != "codex"
        or parts.netloc != "threads"
        or parts.query
        or parts.fragment
    ):
        raise TraceError("Expected codex://threads/<UUID>")
    try:
        return str(UUID(parts.path.removeprefix("/")))
    except ValueError as exc:
        raise TraceError("Expected codex://threads/<UUID>") from exc


def fields(data):
    return {canonical(k): v for k, v in data.items()}


def message_text(data):
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return "\n".join(message_text(value) for value in data)
    if isinstance(data, dict):
        for key in ("text", "message", "content", "summary_text", "summary"):
            if key in data:
                return message_text(data[key])
    return ""


def database(home, prefix, required, diagnostics):
    paths = sorted(
        home.glob(f"{prefix}_*.sqlite"),
        key=lambda p: (
            int(re.search(r"_(\d+)\.sqlite$", p.name)[1])
            if re.search(r"_(\d+)\.sqlite$", p.name)
            else -1
        ),
        reverse=True,
    )
    if not paths:
        diagnostics.append(
            f"{prefix}: database absent; using available rollout records"
        )
        return None
    path = paths[0]
    db = None
    try:
        db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        for table, columns in required.items():
            actual = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
            if not set(columns) <= actual:
                raise TraceError(
                    f"unsupported {path.name} schema: {table} requires {', '.join(columns)}"
                )
        return db
    except (sqlite3.Error, TraceError) as exc:
        if db:
            db.close()
        diagnostics.append(str(exc))
        return None


def snapshot(home, root):
    home = Path(home).expanduser().resolve()
    diagnostics, boundaries = [], []
    state = database(home, "state", {"threads": ["id", "rollout_path"]}, diagnostics)
    history = database(
        home,
        "thread_history",
        {"thread_items": ["thread_id", "item_id", "item_json"]},
        diagnostics,
    )
    try:
        return _snapshot(home, root, state, history, diagnostics, boundaries)
    finally:
        for db in (state, history):
            if db:
                db.close()


def _snapshot(home, root, state, history, diagnostics, boundaries):
    threads, edges = {}, {}
    if state:
        threads = {r["id"]: dict(r) for r in state.execute("SELECT * FROM threads")}
        tables = {
            r[0]
            for r in state.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "thread_spawn_edges" in tables:
            try:
                for r in state.execute(
                    "SELECT parent_thread_id, child_thread_id FROM thread_spawn_edges"
                ):
                    edges.setdefault(r[0], set()).add(r[1])
            except sqlite3.Error:
                diagnostics.append(
                    "unsupported thread_spawn_edges schema; descendants may be incomplete"
                )
        else:
            diagnostics.append(
                "spawn edges absent; descendants inferred only from explicit rollout records"
            )
        for tid, row in threads.items():
            try:
                source = json.loads(row.get("source", "null"))
                parent = (
                    source.get("subagent", {})
                    .get("thread_spawn", {})
                    .get("parent_thread_id")
                    if isinstance(source, dict)
                    else None
                )
                if parent:
                    edges.setdefault(parent, set()).add(tid)
            except (ValueError, AttributeError):
                pass
        boundaries.append(
            {
                "source": "state",
                "threads": len(threads),
                "edges": sum(map(len, edges.values())),
            }
        )
    actions, agents, visited = [], [], set()

    def load(tid, parent=None):
        if tid in visited:
            diagnostics.append(f"{tid}: repeated/cyclic descendant edge skipped")
            return
        visited.add(tid)
        row = threads.get(tid, {})
        path = Path(row["rollout_path"]) if row.get("rollout_path") else None
        if not path or not path.is_file():
            matches = sorted(
                [
                    *home.glob(f"sessions/**/rollout-*{tid}.jsonl"),
                    *home.glob(f"archived_sessions/**/rollout-*{tid}.jsonl"),
                ]
            )
            path = matches[0] if matches else None
            if len(matches) > 1:
                diagnostics.append(f"{tid}: multiple rollouts found; using {path.name}")
        records, items = [], []
        if history:
            items = [
                dict(r)
                for r in history.execute(
                    "SELECT * FROM thread_items WHERE thread_id=? ORDER BY item_id",
                    (tid,),
                )
            ]
            boundaries.append(
                {
                    "source": "history",
                    "thread": tid,
                    "items": len(items),
                    "last_ordinal": max(
                        (
                            r.get("updated_at_ordinal", r.get("rollout_ordinal", 0))
                            or 0
                            for r in items
                        ),
                        default=0,
                    ),
                }
            )
        readable = False
        if path:
            try:
                with path.open("rb") as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(0)
                    data = f.read(size)
                readable = True
                boundaries.append(
                    {"source": "rollout", "thread": tid, "bytes": len(data)}
                )
                for number, line in enumerate(data.splitlines(), 1):
                    try:
                        record = decode(line)
                        if (
                            not isinstance(record, dict)
                            or not isinstance(record.get("payload"), dict)
                            or not isinstance(record.get("type"), str)
                        ):
                            raise ValueError("expected record and payload objects")
                        records.append((number, record))
                    except (ValueError, UnicodeDecodeError):
                        diagnostics.append(
                            f"{tid}: malformed rollout line {number} omitted (possibly truncated)"
                        )
            except OSError:
                diagnostics.append(f"{tid}: rollout unreadable")
        if not readable:
            diagnostics.append(
                f"{tid}: rollout missing/unreadable; response-only actions may be missing"
            )
        if not readable and not items and tid == root:
            raise TraceError(f"Conversation {root} cannot be found or read in {home}")
        label = (
            row.get("agent_path")
            or row.get("agent_nickname")
            or ("Main agent" if parent is None else tid)
        )
        agents.append(
            {"id": tid, "parent": parent, "label": label, "title": row.get("title", "")}
        )
        normalized, children = normalize(tid, records, items, diagnostics)
        actions.extend(normalized)
        if not normalized:
            diagnostics.append(f"{tid}: no supported recorded actions found")
        descendants = edges.get(tid, set()) | set(children)

        def child_key(child):
            stamp = children.get(child)
            if stamp is None:
                stamp = threads.get(child, {}).get("created_at_ms")
            return (stamp if isinstance(stamp, (float, int)) else float("inf"), child)

        for child in sorted(descendants, key=child_key):
            load(child, tid)

    load(root)
    height = layout(actions, agents, diagnostics)
    actions.sort(
        key=lambda a: (
            a.thread,
            a.anchor if a.anchor is not None else float("inf"),
            a.id,
        )
    )
    return {
        "thread": root,
        "agents": agents,
        "actions": [a.export() for a in actions],
        "diagnostics": sorted(set(diagnostics)),
        "boundaries": boundaries,
        "rows": height,
    }


def normalize(tid, records, items, diagnostics):
    actions, aliases, children = {}, {}, {}
    owned_turns = {str(r.get("turn_id")) for r in items if r.get("turn_id")}
    owner = tid
    for _, record in records:
        p = record["payload"]
        if record["type"] == "session_meta":
            owner = p.get("id", tid)
        if p.get("thread_id") == tid:
            owner = tid
        if p.get("thread_id") == tid and p.get("turn_id"):
            owned_turns.add(str(p["turn_id"]))
        if (
            owner == tid
            and p.get("type") in ("task_started", "turn_started")
            and p.get("turn_id")
        ):
            owned_turns.add(str(p["turn_id"]))

    def add(
        item,
        start=None,
        end=None,
        observed=None,
        turn="",
        source="",
        identity=None,
        completed=False,
        cached=False,
    ):
        f = fields(item)
        raw_id = str(identity or f.get("id") or f.get("callid") or source)
        key = aliases.get(raw_id, raw_id)
        action = actions.setdefault(key, Action(id=f"{tid}/{key}", thread=tid))
        kind = canonical(f.get("type", "other"))
        action.category = CATEGORIES.get(
            kind, "Approval" if "approval" in kind else "Other"
        )
        action.name = str(
            f.get("tool")
            or f.get("name")
            or f.get("command")
            or f.get("query")
            or action.name
            or f.get("type", "action")
        )
        if kind == "subagentactivity":
            action.name = "agent " + str(f.get("kind", "activity"))
            if f.get("kind") == "started" and f.get("agentthreadid"):
                children[str(f["agentthreadid"])] = milliseconds(start) or milliseconds(
                    observed
                )
        if kind == "collabagenttoolcall" and canonical(f.get("tool")) in (
            "spawn",
            "spawnagent",
        ):
            for child in f.get("receiverthreadids") or []:
                children[str(child)] = milliseconds(start) or milliseconds(observed)
        if f.get("server") and not action.name.startswith(str(f["server"]) + "."):
            action.name = str(f["server"]) + "." + action.name
        action.turn = str(turn or action.turn)
        status = str(f.get("status") or ("completed" if completed else action.status))
        if cached and action.status != "completion unknown":
            if status != action.status:
                action.notes.append("conflicting cached status; retained rollout status")
        else:
            action.status = status
        parent_id = f.get("parentitemid") or f.get("parentcallid")
        if parent_id:
            action.parent = f"{tid}/{parent_id}"
        for attr, value in (("start", start), ("end", end)):
            stamp = milliseconds(value)
            if value is not None and stamp is None:
                action.notes.append(f"invalid {attr} timestamp")
            if stamp is not None:
                previous = getattr(action, attr)
                if previous is not None and previous != stamp:
                    action.notes.append(
                        f"conflicting {attr} timestamp; retained first record"
                    )
                else:
                    setattr(action, attr, stamp)
        stamp = milliseconds(observed)
        if stamp is not None and action.observed_start is None:
            action.observed_start = stamp
        action.details[source] = item
        action.sources.append(source)
        for alias in (f.get("callid"), f.get("id")):
            if alias:
                aliases[str(alias)] = key
        return action

    # The rollout has higher fidelity than its cached database projection.
    for number, record in records:
        p = record["payload"]
        if (
            p.get("type") in ("item_started", "item_completed")
            and p.get("thread_id", tid) == tid
        ):
            item = p.get("item")
            if isinstance(item, dict):
                add(
                    item,
                    p.get("started_at_ms"),
                    p.get("completed_at_ms"),
                    record.get("timestamp"),
                    p.get("turn_id", ""),
                    f"rollout:{number}",
                    completed=p["type"] == "item_completed",
                )
            else:
                diagnostics.append(f"{tid}: malformed item at rollout:{number}")
    for row in items:
        try:
            item = decode(row["item_json"])
            if not isinstance(item, dict):
                raise ValueError()
            add(
                item,
                row.get("started_at_ms"),
                row.get("completed_at_ms"),
                row.get("created_at_ms"),
                row.get("turn_id", ""),
                "history:" + str(row["item_id"]),
                identity=row["item_id"],
                cached=True,
            )
        except (ValueError, TypeError):
            diagnostics.append(
                f"{tid}: malformed history item {row['item_id']} omitted"
            )

    structured = {(a.turn, a.category) for a in actions.values()}
    matched_transcripts = set()
    prompt_counts = Counter()
    for _, record in records:
        payload = record["payload"]
        metadata = payload.get("internal_chat_message_metadata_passthrough") or {}
        if not isinstance(metadata, dict):
            continue
        kinds = metadata.get("content_item_kinds") or []
        if (
            record["type"] == "response_item"
            and payload.get("role") == "user"
            and (not kinds or any(str(k).startswith("user.") for k in kinds))
        ):
            prompt_counts[metadata.get("turn_id", "")] += 1
    projected_prompts = {}
    for action in actions.values():
        if action.category == "Prompt":
            projected_prompts.setdefault(action.turn, []).append(action)
    for group in projected_prompts.values():
        group.sort(
            key=lambda a: (a.anchor if a.anchor is not None else float("inf"), a.id)
        )

    def transcript(payload, kind, turn, source, observed, representation):
        identity = payload.get("id")
        action = actions.get(aliases.get(str(identity))) if identity else None
        text = message_text(payload)
        if action is None and text:
            candidates = [
                a
                for a in actions.values()
                if a.turn == turn
                and a.category == CATEGORIES[canonical(kind)]
                and (representation, a.id) not in matched_transcripts
                and any(message_text(v) == text for v in a.details.values())
            ]
            if len(candidates) == 1:
                action = candidates[0]
                action.notes.append("transcript matched by turn and exact text")
        # User inputs can be expanded into image/file representations in the model
        # transcript. Only align by turn order when both representations agree on
        # the number of submissions; unmatched inputs remain separate actions.
        if action is None and kind == "userMessage" and representation == "response":
            group = projected_prompts.get(turn, [])
            if group and prompt_counts[turn] == len(group):
                action = next(
                    (
                        a
                        for a in group
                        if (representation, a.id) not in matched_transcripts
                    ),
                    None,
                )
                if action is not None:
                    action.notes.append(
                        "prompt transcript aligned by turn and submission order"
                    )
        if action is None:
            action = add(
                {**payload, "type": kind},
                observed=observed,
                turn=turn,
                source=source,
                completed=True,
            )
        else:
            action.details[source] = payload
            action.sources.append(source)
            if identity:
                aliases[str(identity)] = action.id.removeprefix(tid + "/")
        matched_transcripts.add((representation, action.id))

    current_turn = ""
    legacy_pairs = {
        "exec_command": ("commandExecution", "Command"),
        "mcp_tool_call": ("mcpToolCall", "Tool"),
        "patch_apply": ("fileChange", "File change"),
        "web_search": ("webSearch", "Search"),
    }
    ignored_events = {
        "token_count",
        "thread_settings_applied",
        "item_started",
        "item_completed",
    }
    for number, record in records:
        p = record["payload"]
        typ = p.get("type", "")
        src = f"rollout:{number}"
        ts = record.get("timestamp")
        if p.get("thread_id") and p["thread_id"] != tid:
            continue
        if record["type"] == "turn_context":
            current_turn = p.get("turn_id", "")
            continue
        metadata = p.get("internal_chat_message_metadata_passthrough")
        metadata = metadata if isinstance(metadata, dict) else {}
        turn = p.get("turn_id") or metadata.get("turn_id") or current_turn
        if owned_turns and turn and turn not in owned_turns:
            continue
        if record["type"] == "response_item":
            if typ in ("function_call", "custom_tool_call"):
                identity = p.get("call_id") or p.get("id") or src
                a = actions.get(aliases.get(str(identity), str(identity)))
                if a is None:
                    a = add(p, observed=ts, turn=turn, source=src, identity=identity)
                    # Response status describes model output, not tool execution.
                    a.status = "completion unknown"
                else:
                    a.details[src] = p
                    a.sources.append(src)
                stamp = milliseconds(ts)
                if stamp is not None:
                    a.observed_start = (
                        min(a.observed_start, stamp)
                        if a.observed_start is not None
                        else stamp
                    )
            elif typ in ("function_call_output", "custom_tool_call_output"):
                identity = str(p.get("call_id") or p.get("id") or src)
                a = actions.get(aliases.get(identity, identity))
                if a is None:
                    a = add(
                        {"type": "toolCall", "name": "orphan tool output"},
                        turn=turn,
                        source=src,
                        identity=identity,
                    )
                    a.notes.append("call record missing")
                a.details[src] = p
                a.sources.append(src)
                a.observed_end = milliseconds(ts)
                if a.status == "completion unknown":
                    a.status = "output recorded"
            elif typ == "agent_message":
                a = add(p, observed=ts, turn=turn, source=src, completed=True)
                a.category = "Agent message"
            elif typ in ("message", "reasoning"):
                role = p.get("role")
                if typ == "message" and role not in ("user", "assistant"):
                    continue
                kinds = metadata.get("content_item_kinds") or []
                if (
                    role == "user"
                    and kinds
                    and not any(str(k).startswith("user.") for k in kinds)
                ):
                    continue
                kind = (
                    "reasoning"
                    if typ == "reasoning"
                    else "userMessage"
                    if role == "user"
                    else "agentMessage"
                )
                transcript(p, kind, turn, src, ts, "response")
            else:
                add(p, observed=ts, turn=turn, source=src)
                diagnostics.append(
                    f"{tid}: unclassified response item {typ!r} at {src}; raw payload retained"
                )
        elif record["type"] == "event_msg":
            if typ in ignored_events:
                continue
            matched = False
            for prefix, (kind, _) in legacy_pairs.items():
                if typ in (prefix + "_begin", prefix + "_end"):
                    identity = p.get("call_id") or p.get("id") or src
                    a = add(
                        {**p, "type": kind},
                        start=ts if typ.endswith("_begin") else None,
                        end=ts if typ.endswith("_end") else None,
                        turn=turn,
                        source=src,
                        identity=identity,
                        completed=typ.endswith("_end"),
                    )
                    if typ.endswith("_begin"):
                        a.status = "in progress"
                    matched = True
                    break
            if matched:
                continue
            message_kinds = {
                "user_message": "userMessage",
                "agent_message": "agentMessage",
                "agent_reasoning": "reasoning",
            }
            if typ in message_kinds:
                kind = message_kinds[typ]
                transcript(p, kind, turn, src, ts, "event")
            else:
                # Lifecycle, approvals, and future event kinds remain inspectable.
                a = add(
                    p,
                    observed=ts,
                    turn=turn,
                    source=src,
                    identity=p.get("id") or src,
                    completed=True,
                )
                if (
                    typ
                    not in (
                        "task_started",
                        "task_complete",
                        "turn_started",
                        "turn_complete",
                        "turn_aborted",
                    )
                    and "approval" not in typ
                ):
                    a.notes.append("unclassified event; raw payload retained")
        elif record["type"] == "compacted":
            if (turn, "Compaction") not in structured:
                add(
                    {**p, "type": "contextCompaction"},
                    observed=ts,
                    turn=turn,
                    source=src,
                    completed=True,
                )
        elif record["type"] not in (
            "session_meta",
            "world_state",
            "token_usage_record",
            "inter_agent_communication_metadata",
        ):
            add({**p, "type": record["type"]}, observed=ts, turn=turn, source=src)
            diagnostics.append(
                f"{tid}: unclassified record type {record['type']!r} at {src}; raw payload retained"
            )
    for a in actions.values():
        if a.parent:
            raw = a.parent.removeprefix(tid + "/")
            a.parent = tid + "/" + aliases.get(raw, raw)
        if a.start is not None and a.end is not None and a.end < a.start:
            a.notes.append("end precedes start; rendered as marker")
        if (
            a.observed_start is not None
            and a.observed_end is not None
            and a.observed_end < a.observed_start
        ):
            a.notes.append("output observed before call; rendered as marker")
        a.notes = sorted(set(a.notes))
        a.sources = sorted(set(a.sources))
    return list(actions.values()), children
