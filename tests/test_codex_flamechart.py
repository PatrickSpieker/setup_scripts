"""Real SQLite/JSONL fixtures; no live user records or network required."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from codex_trace.model import Action, layout, utc  # noqa: E402
from codex_trace.render import render  # noqa: E402
from codex_trace.sources import TraceError, normalize, snapshot, thread_id  # noqa: E402

ROOT = "00000000-0000-4000-8000-000000000001"
CHILD = "00000000-0000-4000-8000-000000000002"
GRANDCHILD = "00000000-0000-4000-8000-000000000003"
MISSING = "00000000-0000-4000-8000-000000000004"
BASE = 1700000000000


def event(kind, payload, stamp=BASE):
    return {"type": kind, "timestamp": utc(stamp), "payload": payload}


def item(identity, kind="commandExecution", start=BASE, end=BASE + 100, **extra):
    return event(
        "event_msg",
        {
            "type": "item_completed",
            "thread_id": ROOT,
            "turn_id": "turn",
            "started_at_ms": start,
            "completed_at_ms": end,
            "item": {"type": kind, "id": identity, **extra},
        },
        end or start or BASE,
    )


@pytest.fixture
def home(tmp_path):
    state = sqlite3.connect(tmp_path / "state_5.sqlite")
    state.executescript(
        "CREATE TABLE threads(id TEXT, rollout_path TEXT, title TEXT, agent_path TEXT, created_at_ms INTEGER); CREATE TABLE thread_spawn_edges(parent_thread_id TEXT, child_thread_id TEXT);"
    )
    history = sqlite3.connect(tmp_path / "thread_history_1.sqlite")
    history.execute(
        "CREATE TABLE thread_items(thread_id TEXT,item_id TEXT,item_json TEXT,turn_id TEXT,started_at_ms INTEGER,completed_at_ms INTEGER,created_at_ms INTEGER,rollout_ordinal INTEGER)"
    )

    class Home:
        path = tmp_path

        def put(self, tid, records, archived=False, projected=False):
            folder = tmp_path / (
                "archived_sessions" if archived else "sessions/2026/10/12"
            )
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"rollout-example-{tid}.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in records))
            state.execute(
                "INSERT INTO threads VALUES(?,?,?,?,?)",
                (
                    tid,
                    str(path),
                    "Test",
                    "Main agent" if tid == ROOT else "Worker",
                    BASE,
                ),
            )
            state.commit()
            if projected:
                for i, r in enumerate(records):
                    p = r["payload"]
                    if p.get("type") == "item_completed":
                        history.execute(
                            "INSERT INTO thread_items VALUES(?,?,?,?,?,?,?,?)",
                            (
                                tid,
                                p["item"]["id"],
                                json.dumps(p["item"]),
                                p.get("turn_id"),
                                p.get("started_at_ms"),
                                p.get("completed_at_ms"),
                                BASE,
                                i,
                            ),
                        )
                history.commit()
            return path

        def edge(self, parent, child):
            state.execute("INSERT INTO thread_spawn_edges VALUES(?,?)", (parent, child))
            state.commit()

    yield Home()
    state.close()
    history.close()


def test_link_validation():
    assert thread_id(f"codex://threads/{ROOT}") == ROOT
    for bad in [
        "https://threads/" + ROOT,
        "../x",
        "codex://threads/no",
        f"codex://threads/{ROOT}/extra",
        f"codex://threads/{ROOT}?x=1",
    ]:
        with pytest.raises(TraceError):
            thread_id(bad)


def test_read_only_recursive_archived_snapshot(home):
    home.put(ROOT, [item("a")], projected=True)
    child = item("b")
    child["payload"]["thread_id"] = CHILD
    home.put(CHILD, [child], archived=True)
    home.edge(ROOT, CHILD)
    grand = item("c")
    grand["payload"]["thread_id"] = GRANDCHILD
    home.put(GRANDCHILD, [grand])
    home.edge(CHILD, GRANDCHILD)
    home.edge(GRANDCHILD, ROOT)
    home.edge(ROOT, MISSING)
    before = {
        p: hashlib.sha256(p.read_bytes()).digest()
        for p in home.path.rglob("*")
        if p.is_file()
    }
    r = snapshot(home.path, ROOT)
    assert [a["id"] for a in r["agents"]] == [ROOT, CHILD, GRANDCHILD, MISSING]
    assert len(r["actions"]) == 3
    assert len(r["actions"][0]["sources"]) == 2
    assert any("cyclic" in x for x in r["diagnostics"])
    assert any(MISSING in x for x in r["diagnostics"])
    assert all(
        hashlib.sha256(p.read_bytes()).digest() == digest
        for p, digest in before.items()
    )


def test_wrappers_nested_items_and_call_output_pairing(home):
    call = event(
        "response_item",
        {
            "type": "custom_tool_call",
            "call_id": "wrapper",
            "id": "response",
            "name": "functions.exec",
            "input": "tools.exec_command(...)",
            "status": "completed",
            "parent_call_id": None,
        },
        BASE,
    )
    output = event(
        "response_item",
        {"type": "custom_tool_call_output", "call_id": "wrapper", "output": "ok"},
        BASE + 300,
    )
    home.put(
        ROOT,
        [
            call,
            item("nested", parent_call_id="wrapper", start=BASE + 20, end=BASE + 100),
            output,
        ],
    )
    r = snapshot(home.path, ROOT)
    actions = {a["id"].split("/")[-1]: a for a in r["actions"]}
    assert len(actions) == 2
    assert actions["nested"]["parent"] == ROOT + "/wrapper"
    assert actions["nested"]["depth"] == 1
    assert actions["wrapper"]["duration_ms"] is None
    assert "observation only" in actions["wrapper"]["timing"]
    assert actions["wrapper"]["observed_end"] == BASE + 300


def test_explicit_id_dedup(home):
    home.put(
        ROOT,
        [
            item("call-a"),
            event(
                "response_item",
                {"type": "function_call", "call_id": "call-a", "name": "exec"},
                BASE,
            ),
            event(
                "response_item",
                {"type": "function_call_output", "call_id": "call-a", "output": "done"},
                BASE + 100,
            ),
        ],
        projected=True,
    )
    r = snapshot(home.path, ROOT)
    assert len(r["actions"]) == 1
    assert r["actions"][0]["category"] == "Command"
    assert len(r["actions"][0]["sources"]) == 4


def test_overlaps_do_not_imply_parentage():
    a = Action("a", "t", start=0, end=100)
    b = Action("b", "t", start=10, end=50)
    c = Action("c", "t", parent="a", start=20, end=40)
    agents = [{"id": "t"}]
    layout([a, b, c], agents, [])
    assert a.depth == b.depth == 0 and c.depth == 1
    assert len({a.row, b.row, c.row}) == 3
    assert b.parent is None


def test_uncertain_timing_and_unfinished(home):
    records = [
        item("zero", start=BASE, end=BASE),
        item("inverted", start=BASE + 5, end=BASE),
        item("active", start=BASE, end=None, status="inProgress"),
        item("unknown", start=BASE, end=None),
        item("untimed", start=None, end=None),
    ]
    records[3]["payload"]["type"] = "item_started"
    records[-1].pop("timestamp")
    home.put(ROOT, records)
    r = snapshot(home.path, ROOT)
    a = {x["id"].split("/")[-1]: x for x in r["actions"]}
    assert a["active"]["duration_ms"] is None and a["active"]["end"] is None
    assert a["active"]["status"] == "inProgress"
    assert a["unknown"]["status"] == "completion unknown"
    assert a["untimed"]["start"] is None and a["untimed"]["observed_start"] is None
    assert "end precedes start" in a["inverted"]["timing"]
    assert "precision unknown" in a["zero"]["timing"]


def test_conflicting_timing_is_visible():
    records = [(1, item("a")), (2, item("a", start=BASE + 50))]
    a, _ = normalize(ROOT, records, [], [])
    assert len(a) == 1 and a[0].start == BASE
    assert any("conflicting" in s for s in a[0].notes)


def test_legacy_begin_end_and_orphan_output(home):
    home.put(
        ROOT,
        [
            event(
                "event_msg",
                {
                    "type": "exec_command_begin",
                    "call_id": "cmd",
                    "command": ["echo", "ok"],
                },
                BASE,
            ),
            event(
                "event_msg",
                {"type": "exec_command_end", "call_id": "cmd", "exit_code": 0},
                BASE + 200,
            ),
            event(
                "response_item",
                {"type": "function_call_output", "call_id": "orphan", "output": "x"},
                BASE + 300,
            ),
        ],
    )
    a = {x["id"].split("/")[-1]: x for x in snapshot(home.path, ROOT)["actions"]}
    assert a["cmd"]["duration_ms"] == 200 and a["cmd"]["status"] == "completed"
    assert a["orphan"]["duration_ms"] is None
    assert "call record missing" in a["orphan"]["timing"]


def test_categories_and_approval(home):
    kinds = [
        "userMessage",
        "agentMessage",
        "reasoning",
        "commandExecution",
        "mcpToolCall",
        "webSearch",
        "fileChange",
        "subAgentActivity",
        "approvalRequest",
    ]
    home.put(ROOT, [item(str(i), kind) for i, kind in enumerate(kinds)])
    assert {a["category"] for a in snapshot(home.path, ROOT)["actions"]} == {
        "Prompt",
        "Assistant",
        "Reasoning",
        "Command",
        "Tool",
        "Search",
        "File change",
        "Agent lifecycle",
        "Approval",
    }


def test_inherited_context_not_replayed(home):
    own = item("own", "agentMessage")
    own["payload"]["thread_id"] = CHILD
    inherited = event(
        "response_item",
        {
            "type": "message",
            "role": "assistant",
            "id": "old",
            "content": [],
            "internal_chat_message_metadata_passthrough": {"turn_id": "parent-turn"},
        },
    )
    home.put(CHILD, [inherited, own])
    r = snapshot(home.path, CHILD)
    assert len(r["actions"]) == 1 and r["actions"][0]["id"].endswith("/own")


def test_malformed_records_and_schema_diagnostics(home):
    path = home.put(ROOT, [item("ok")])
    path.write_text(path.read_text() + '42\n{"type":')
    r = snapshot(home.path, ROOT)
    assert len(r["actions"]) == 1
    assert sum("malformed rollout" in x for x in r["diagnostics"]) == 2
    db = sqlite3.connect(home.path / "state_6.sqlite")
    db.execute("CREATE TABLE other(x)")
    db.close()
    r = snapshot(home.path, ROOT)
    assert any("unsupported state_6.sqlite schema" in x for x in r["diagnostics"])
    assert len(r["actions"]) == 1


def test_missing_thread_fails(home):
    with pytest.raises(TraceError, match="cannot be found"):
        snapshot(home.path, ROOT)


def test_cli_failure_preserves_output(home):
    target = home.path / "existing.html"
    target.write_text("keep")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "codex_flamechart.py"),
            f"codex://threads/{ROOT}",
            "--codex-home",
            str(home.path),
            "--output",
            str(target),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and target.read_text() == "keep"


def test_deterministic_offline_html_and_escaping(home, monkeypatch):
    pytest.importorskip("altair")
    pytest.importorskip("vl_convert")
    hostile = "</script><script>window.PWNED=true</script> @@REPORT@@"
    home.put(ROOT, [item("safe", command=hostile, aggregatedOutput=hostile * 100)])
    r = snapshot(home.path, ROOT)
    first = render(r)
    monkeypatch.setenv("TZ", "Pacific/Honolulu")
    second = render(snapshot(home.path, ROOT))
    assert first == second
    assert hostile not in first
    assert "\\u003c/script\\u003e" in first
    assert "<script src=" not in first
    assert utc(BASE) == "2023-11-14T22:13:20.000Z"


def test_cli_output_path_independence(home):
    pytest.importorskip("altair")
    pytest.importorskip("vl_convert")
    home.put(ROOT, [item("ok")])
    outputs = [home.path / "one.html", home.path / "two.html"]
    for output in outputs:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "codex_flamechart.py"),
                f"codex://threads/{ROOT}",
                "--codex-home",
                str(home.path),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    assert outputs[0].read_bytes() == outputs[1].read_bytes()


def test_offline_browser_interactions(home, tmp_path):
    browser_path = os.environ.get("CODEX_FLAMECHART_TEST_BROWSER")
    if not browser_path:
        pytest.skip("Set CODEX_FLAMECHART_TEST_BROWSER to a Chromium executable")
    pytest.importorskip("altair")
    pytest.importorskip("vl_convert")
    from playwright.sync_api import sync_playwright

    home.put(
        ROOT,
        [
            item(
                "a",
                command="echo example",
                aggregatedOutput="</script><script>window.PWNED=true</script>"
                + "long output " * 2000,
                end=BASE + 1000,
            ),
            item("b", "userMessage", start=BASE + 200, end=BASE + 200),
            item("untimed", start=None, end=None),
        ],
    )
    home.edge(ROOT, MISSING)
    report = snapshot(home.path, ROOT)
    output = tmp_path / "browser.html"
    output.write_text(render(report))
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=browser_path, headless=True)
        page = browser.new_page(offline=True, viewport={"width": 1600, "height": 1000})
        errors = []
        requests = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: requests.append(r.url))
        page.goto(output.as_uri())
        page.wait_for_function("window.chartReady || window.chartError")
        assert not page.evaluate("window.chartError")
        assert page.locator(".lane").count() == 2
        assert "Incomplete data" in page.locator("#notices").inner_text()
        coordinates = page.evaluate(
            "({x:chartView.padding().left + chartView.origin()[0] + chartView.scale('x')(0.5), y:chartView.padding().top + chartView.origin()[1] + chartView.scale('y')(0.39)})"
        )
        page.locator("canvas").click(position=coordinates)
        assert "echo example" in page.locator("#details h2").inner_text()
        assert page.evaluate("window.PWNED") is None
        initial_domain = page.evaluate('chartView.scale("x").domain()')
        page.get_by_role("button", name="Zoom to action").click()
        page.wait_for_function('chartView.scale("x").domain()[0] < 0')
        assert page.evaluate('chartView.scale("x").domain()') != initial_domain
        page.locator("#action-list button").filter(has_text="echo example").click()
        assert "echo example" in page.locator("#details h2").inner_text()
        page.locator("#details summary").filter(has_text="rollout:1").click()
        assert "long output " * 10 in page.locator("#details").inner_text()
        page.locator("select").select_option("Prompt")
        assert page.locator("#action-list button").count() == 1
        page.locator("#reset").click()
        page.wait_for_function('window.chartView.signal("category") === "All"')
        before = page.evaluate('window.chartView.scale("x").domain()')
        page.locator("canvas").hover(position={"x": 500, "y": 70})
        page.mouse.wheel(0, -200)
        page.wait_for_timeout(200)
        after = page.evaluate('window.chartView.scale("x").domain()')
        assert before != after
        page.mouse.move(700, 220)
        page.mouse.down()
        page.mouse.move(800, 220, steps=5)
        page.mouse.up()
        page.screenshot(path=str(tmp_path / "preview.png"))
        assert not errors
        assert not any(u.startswith(("https:", "http:")) for u in requests)
        browser.close()


def test_copied_session_tasks_excluded(home):
    records = [
        event("session_meta", {"id": CHILD}),
        event("session_meta", {"id": ROOT}),
        event("event_msg", {"type": "task_started", "turn_id": "inherited"}),
        event("turn_context", {"turn_id": "inherited"}),
        event(
            "response_item",
            {
                "type": "message",
                "role": "assistant",
                "id": "old",
                "internal_chat_message_metadata_passthrough": {"turn_id": "inherited"},
            },
        ),
        event("event_msg", {"type": "task_complete", "turn_id": "inherited"}),
        event("event_msg", {"type": "thread_settings_applied", "thread_id": CHILD}),
        event("event_msg", {"type": "task_started", "turn_id": "own"}),
        event("turn_context", {"turn_id": "own"}),
        event(
            "response_item",
            {
                "type": "agent_message",
                "id": "new",
                "author": "/root",
                "recipient": "/root/child",
                "content": [],
            },
        ),
    ]
    home.put(CHILD, records)
    report = snapshot(home.path, CHILD)
    assert len(report["actions"]) == 2
    assert all(a["turn"] == "own" for a in report["actions"])
    assert any(a["category"] == "Agent message" for a in report["actions"])


def test_invalid_record_shape_and_numbers(home):
    path = home.put(ROOT, [item("ok")])
    path.write_text(
        path.read_text()
        + '{"payload": {}}\n'
        + '{"type":"event_msg","payload":{"number":NaN}}\n'
        + '{"type":"event_msg","payload":{"number":1e999}}\n'
    )
    report = snapshot(home.path, ROOT)
    assert len(report["actions"]) == 1
    assert len(report["diagnostics"]) == 3


def test_unknown_actions_are_retained(home):
    home.put(
        ROOT,
        [
            event(
                "response_item",
                {"type": "future_tool", "id": "new", "content": "details"},
            )
        ],
    )
    r = snapshot(home.path, ROOT)
    assert len(r["actions"]) == 1
    assert "future_tool" in r["diagnostics"][0]


def test_lagging_projection_preserves_new_messages(home):
    records = [
        item("projected", "agentMessage", text="first"),
        event(
            "response_item",
            {
                "type": "message",
                "role": "assistant",
                "id": "projected",
                "content": [{"text": "first"}],
                "internal_chat_message_metadata_passthrough": {"turn_id": "turn"},
            },
        ),
        event(
            "response_item",
            {
                "type": "message",
                "role": "assistant",
                "id": "new",
                "content": [{"text": "second"}],
                "internal_chat_message_metadata_passthrough": {"turn_id": "turn"},
            },
        ),
    ]
    home.put(ROOT, records)
    assert len(snapshot(home.path, ROOT)["actions"]) == 2


def test_prompt_transcript_reconciliation_is_exact(home):
    home.put(
        ROOT,
        [
            item(
                "projected", "userMessage", content=[{"type": "text", "text": "hello"}]
            ),
            event(
                "response_item",
                {
                    "type": "message",
                    "role": "user",
                    "id": "transcript",
                    "content": [{"type": "input_text", "text": "hello"}],
                    "internal_chat_message_metadata_passthrough": {"turn_id": "turn"},
                },
            ),
            event(
                "response_item",
                {
                    "type": "message",
                    "role": "user",
                    "id": "steer",
                    "content": [{"type": "input_text", "text": "different"}],
                    "internal_chat_message_metadata_passthrough": {"turn_id": "turn"},
                },
            ),
        ],
    )
    r = snapshot(home.path, ROOT)
    assert len(r["actions"]) == 2
    assert any("exact text" in a["timing"] for a in r["actions"])


def test_injected_context_is_not_a_prompt(home):
    records = [item("prompt", "userMessage", content=[{"text": "attached image"}])]
    for identity, kinds, text in [
        ("context", ["agents_md.instructions"], "instructions"),
        ("input", ["user.image"], "expanded image representation"),
    ]:
        records.append(
            event(
                "response_item",
                {
                    "type": "message",
                    "role": "user",
                    "id": identity,
                    "content": [{"text": text}],
                    "internal_chat_message_metadata_passthrough": {
                        "turn_id": "turn",
                        "content_item_kinds": kinds,
                    },
                },
            )
        )
    home.put(ROOT, records)
    r = snapshot(home.path, ROOT)
    assert len(r["actions"]) == 1
    assert "submission order" in r["actions"][0]["timing"]
