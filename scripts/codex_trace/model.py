import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def canonical(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def milliseconds(value):
    if isinstance(value, bool):
        return None
    if (
        isinstance(value, (int, float))
        and math.isfinite(value)
        and -62135596800000 <= value <= 253402300799999
    ):
        return value
    if isinstance(value, str):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is not None:
                return stamp.timestamp() * 1000
        except (ValueError, OverflowError):
            pass
    return None


def utc(value):
    if value is None:
        return None
    try:
        return (
            datetime.fromtimestamp(value / 1000, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
    except (ValueError, OverflowError, OSError):
        return None


CATEGORIES = {
    "usermessage": "Prompt",
    "agentmessage": "Assistant",
    "reasoning": "Reasoning",
    "commandexecution": "Command",
    "mcptoolcall": "Tool",
    "dynamictoolcall": "Tool",
    "functioncall": "Tool",
    "customtoolcall": "Tool",
    "toolcall": "Tool",
    "websearch": "Search",
    "filechange": "File change",
    "imageview": "Image",
    "imagegeneration": "Image",
    "collabagenttoolcall": "Agent lifecycle",
    "subagentactivity": "Agent lifecycle",
    "contextcompaction": "Compaction",
}


@dataclass
class Action:
    id: str
    thread: str
    turn: str = ""
    name: str = ""
    category: str = "Other"
    status: str = "completion unknown"
    parent: str | None = None
    start: float | None = None
    end: float | None = None
    observed_start: float | None = None
    observed_end: float | None = None
    details: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    row: int = 0
    depth: int = 0

    @property
    def anchor(self):
        return next(
            (
                x
                for x in (self.start, self.observed_start, self.end, self.observed_end)
                if x is not None
            ),
            None,
        )

    @property
    def finish(self):
        if self.start is not None:
            return (
                self.end
                if self.end is not None and self.end >= self.start
                else self.start
            )
        if self.observed_start is not None and self.observed_end is not None:
            return max(self.observed_start, self.observed_end)
        return self.anchor

    def export(self):
        d = asdict(self)
        d.update(
            start_utc=utc(self.start),
            end_utc=utc(self.end),
            observed_start_utc=utc(self.observed_start),
            observed_end_utc=utc(self.observed_end),
        )
        d["duration_ms"] = (
            self.end - self.start
            if self.start is not None
            and self.end is not None
            and self.end >= self.start
            else None
        )
        d["timing"] = (
            "recorded interval"
            if d["duration_ms"] not in (None, 0)
            else "zero-duration record; precision unknown"
            if d["duration_ms"] == 0
            else "start only"
            if self.start is not None
            else "observation only; execution timing unknown"
        )
        if self.notes:
            d["timing"] += "; " + "; ".join(self.notes)
        return d


def layout(actions, agents, diagnostics):
    """Pack overlaps separately; only explicit parent references add depth."""
    offset = 0
    for agent in agents:
        members = [a for a in actions if a.thread == agent["id"]]
        by_id = {a.id: a for a in members}
        for action in members:
            chain, current = {action.id}, action
            while current.parent:
                if current.parent in chain:
                    diagnostics.append(
                        f"{action.id}: cyclic action parent relationship; nesting omitted"
                    )
                    action.depth = 0
                    break
                chain.add(current.parent)
                current = by_id.get(current.parent)
                if current is None:
                    action.notes.append("parent not present in this lane")
                    break
                action.depth += 1
        rows = []
        for depth in sorted({a.depth for a in members}):
            ends = []
            group = sorted(
                (a for a in members if a.depth == depth and a.anchor is not None),
                key=lambda a: (a.anchor, a.id),
            )
            for action in group:
                slot = next(
                    (i for i, end in enumerate(ends) if end < action.anchor), len(ends)
                )
                if slot == len(ends):
                    ends.append(action.finish)
                else:
                    ends[slot] = action.finish
                action.row = offset + len(rows) + slot
            rows.extend(ends)
        agent["row_start"] = offset
        agent["row_count"] = max(len(rows), 1)
        offset += agent["row_count"] + 1
    return offset
