"""Tests for the SwiftBar token-usage plugin.

The plugin renders silently broken zeros when ccusage's JSON shape drifts
(empirically: ccusage v19 renamed `date` → `period` and absorbed the
@ccusage/codex CLI, and the plugin showed $0.00 for weeks before anyone
noticed). It also used to show identical per-agent costs on any day both
tools ran, because the *merged* `ccusage daily` collapses such days into one
record with no per-agent split. v3 fixes that by calling the per-agent
subcommands (`ccusage claude daily` / `ccusage codex daily`) and normalizing
their two different schemas. The fixtures in tests/fixtures/ capture the
current per-agent shapes; bump them deliberately when bumping the major in
the plugin's CCUSAGE_PKG.
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
PLUGIN = REPO_DIR / "swiftbar_plugins" / "ai_token_usage.1m.py"
FIXTURES = REPO_DIR / "tests" / "fixtures"


def _load_plugin():
    # The plugin filename contains a SwiftBar refresh-interval token
    # ("1m"), so it can't be imported by name. Load it via importlib.
    spec = importlib.util.spec_from_file_location("ai_token_usage", PLUGIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def plugin():
    return _load_plugin()


@pytest.fixture
def claude_data():
    return json.loads((FIXTURES / "ccusage_claude_daily.json").read_text())


@pytest.fixture
def codex_data():
    return json.loads((FIXTURES / "ccusage_codex_daily.json").read_text())


# ─── parse_records ──────────────────────────────────────────────────────────

def test_parse_records_unwraps_daily_key(plugin, claude_data):
    records = plugin.parse_records(claude_data, required=("date", "totalCost"))
    assert len(records) == 3
    assert records[0]["date"] == "2026-05-19"


def test_parse_records_accepts_bare_list(plugin, claude_data):
    # Some ccusage versions might emit a top-level list instead of {"daily":...}.
    records = plugin.parse_records(claude_data["daily"], required=("date", "totalCost"))
    assert len(records) == 3


def test_parse_records_validates_per_agent_cost_key(plugin, codex_data):
    # Codex uses costUSD, not totalCost — parse_records must accept the key the
    # caller declares, and reject when it's absent.
    records = plugin.parse_records(codex_data, required=("date", "costUSD"))
    assert len(records) == 2
    with pytest.raises(plugin.CcusageError, match="missing fields"):
        plugin.parse_records(codex_data, required=("date", "totalCost"))


def test_parse_records_raises_on_missing_required_fields(plugin):
    bad = {"daily": [{"day": "2026-05-19", "cost": 1.0}]}  # old/foreign shape
    with pytest.raises(plugin.CcusageError, match="missing fields"):
        plugin.parse_records(bad, required=("date", "totalCost"))


def test_parse_records_raises_on_unexpected_shape(plugin):
    with pytest.raises(plugin.CcusageError, match="unexpected ccusage shape"):
        plugin.parse_records("use npx ccusage instead")  # a deprecation msg


def test_parse_records_accepts_empty_list(plugin):
    """An empty record list is valid — it means 'no usage in the window' —
    and must not be confused with a schema break."""
    assert plugin.parse_records({"daily": []}) == []


# ─── normalize ──────────────────────────────────────────────────────────────

def test_normalize_claude_maps_canonical_keys(plugin, claude_data):
    records = plugin.normalize(claude_data["daily"], "claude")
    r = records[0]
    assert r["period"] == "2026-05-19"          # date → period
    assert r["totalCost"] == pytest.approx(1.23)
    assert r["cacheReadTokens"] == 10000
    assert r["cacheCreationTokens"] == 500


def test_normalize_codex_translates_divergent_schema(plugin, codex_data):
    records = plugin.normalize(codex_data["daily"], "codex")
    r = records[0]
    assert r["period"] == "2026-05-15"
    assert r["totalCost"] == pytest.approx(1.00)         # costUSD → totalCost
    assert r["cacheReadTokens"] == 250000                 # cachedInputTokens → cacheReadTokens
    assert r["cacheCreationTokens"] == 0                  # codex has no cache-creation


# ─── extract_totals ─────────────────────────────────────────────────────────

def test_extract_totals_filters_by_period_prefix(plugin, claude_data, codex_data):
    claude = plugin.normalize(claude_data["daily"], "claude")
    codex = plugin.normalize(codex_data["daily"], "codex")

    today_claude = plugin.extract_totals(claude, period_filter="2026-05-19")
    assert today_claude["cost"] == pytest.approx(1.23)
    assert today_claude["output"] == 2000

    month_claude = plugin.extract_totals(claude, period_filter="2026-05")
    assert month_claude["cost"] == pytest.approx(1.23 + 4.00 + 2.00)

    month_codex = plugin.extract_totals(codex, period_filter="2026-05")
    assert month_codex["cost"] == pytest.approx(1.00 + 0.50)


def test_extract_totals_no_filter_sums_all(plugin, claude_data):
    claude = plugin.normalize(claude_data["daily"], "claude")
    total = plugin.extract_totals(claude)
    assert total["cost"] == pytest.approx(1.23 + 4.00 + 2.00)


def test_mixed_day_splits_per_agent(plugin, claude_data, codex_data):
    """Regression for the bug that motivated v3: on a day both tools ran, the
    old merged-daily approach showed each agent the full combined cost (so the
    two rows were identical). With per-agent subcommands the split is real and
    the combined total is their sum."""
    claude = plugin.normalize(claude_data["daily"], "claude")
    codex = plugin.normalize(codex_data["daily"], "codex")

    claude_15 = plugin.extract_totals(claude, period_filter="2026-05-15")
    codex_15 = plugin.extract_totals(codex, period_filter="2026-05-15")

    assert claude_15["cost"] == pytest.approx(4.00)
    assert codex_15["cost"] == pytest.approx(1.00)
    assert claude_15["cost"] != codex_15["cost"]                 # no longer identical
    assert claude_15["cost"] + codex_15["cost"] == pytest.approx(5.00)


# ─── cache line rendering ───────────────────────────────────────────────────

def test_codex_cache_line_omits_creation(plugin, capsys):
    """Codex reports no cache-creation metric, so its cache line must show only
    reads — never a misleading '/ 0 created'."""
    codex_today = {"cost": 5.81, "output": 20123, "cache_read": 6316800, "cache_create": 0}
    plugin._print_agent_today("🟢", "Codex", codex_today, plugin.COLOR_CODEX,
                              show_cache_create=False)
    out = capsys.readouterr().out
    assert "read" in out
    assert "created" not in out


def test_claude_cache_line_keeps_creation(plugin, capsys):
    claude_today = {"cost": 70.0, "output": 1000, "cache_read": 100000, "cache_create": 5000}
    plugin._print_agent_today("🟠", "Claude Code", claude_today, plugin.COLOR_CLAUDE,
                              show_cache_create=True)
    out = capsys.readouterr().out
    assert "read" in out and "created" in out
