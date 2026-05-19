"""Tests for the SwiftBar token-usage plugin.

The plugin renders silently broken zeros when ccusage's JSON shape drifts
(empirically: ccusage v19 renamed `date` → `period` and absorbed the
@ccusage/codex CLI, and the plugin showed $0.00 for weeks before anyone
noticed). The fixture in tests/fixtures/ccusage_daily.json captures the
current ccusage v19 shape; bump it deliberately when bumping the major in
the plugin's CCUSAGE_PKG.
"""

import importlib.util
import json
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
PLUGIN = REPO_DIR / "swiftbar_plugins" / "ai_token_usage.1m.py"
FIXTURE = REPO_DIR / "tests" / "fixtures" / "ccusage_daily.json"


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
def fixture_data():
    return json.loads(FIXTURE.read_text())


def test_parse_records_unwraps_daily_key(plugin, fixture_data):
    records = plugin.parse_records(fixture_data)
    assert len(records) == 4
    assert records[0]["period"] == "2026-05-19"


def test_parse_records_accepts_bare_list(plugin, fixture_data):
    # Some ccusage versions might emit a top-level list instead of {"daily":...}.
    records = plugin.parse_records(fixture_data["daily"])
    assert len(records) == 4


def test_parse_records_raises_on_missing_required_fields(plugin):
    bad = {"daily": [{"date": "2026-05-19", "cost": 1.0}]}  # old v18 shape
    with pytest.raises(plugin.CcusageError, match="missing fields"):
        plugin.parse_records(bad)


def test_parse_records_raises_on_unexpected_shape(plugin):
    with pytest.raises(plugin.CcusageError, match="unexpected ccusage shape"):
        plugin.parse_records("use npx ccusage instead")  # the v18 deprecation msg


def test_parse_records_accepts_empty_list(plugin):
    """An empty record list is valid — it means 'no usage in the window' —
    and must not be confused with a schema break."""
    assert plugin.parse_records({"daily": []}) == []


def test_bucket_by_agent_splits_pure_records(plugin, fixture_data):
    records = plugin.parse_records(fixture_data)
    by_agent = plugin.bucket_by_agent(records)
    claude_periods = {r["period"] for r in by_agent["claude"]}
    codex_periods = {r["period"] for r in by_agent["codex"]}
    # 2026-05-15 is mixed and lands in both buckets
    assert claude_periods == {"2026-05-19", "2026-05-10", "2026-05-15"}
    assert codex_periods == {"2026-05-12", "2026-05-15"}


def test_extract_totals_filters_by_period_prefix(plugin, fixture_data):
    records = plugin.parse_records(fixture_data)
    by_agent = plugin.bucket_by_agent(records)

    # Today (2026-05-19): only the single claude record
    today_claude = plugin.extract_totals(by_agent["claude"], period_filter="2026-05-19")
    assert today_claude["cost"] == pytest.approx(1.23)
    assert today_claude["output"] == 2000

    # Whole month (2026-05): claude bucket includes its 3 records, incl mixed
    month_claude = plugin.extract_totals(by_agent["claude"], period_filter="2026-05")
    assert month_claude["cost"] == pytest.approx(1.23 + 2.00 + 5.00)

    # Whole month for codex includes its solo day + the mixed day
    month_codex = plugin.extract_totals(by_agent["codex"], period_filter="2026-05")
    assert month_codex["cost"] == pytest.approx(0.50 + 5.00)

    # The full record list is the source of truth for day/month totals
    month_total = plugin.extract_totals(records, period_filter="2026-05")
    assert month_total["cost"] == pytest.approx(1.23 + 2.00 + 0.50 + 5.00)


def test_extract_totals_no_filter_sums_all(plugin, fixture_data):
    records = plugin.parse_records(fixture_data)
    total = plugin.extract_totals(records)
    assert total["cost"] == pytest.approx(1.23 + 2.00 + 0.50 + 5.00)


def test_mixed_day_overcount_is_intentional(plugin, fixture_data):
    """Document the trade-off: per-agent totals on mixed days are double-
    counted because ccusage v19 doesn't expose a per-agent cost split. The
    full-record total stays correct, which is what the menu bar shows."""
    records = plugin.parse_records(fixture_data)
    by_agent = plugin.bucket_by_agent(records)

    claude = plugin.extract_totals(by_agent["claude"], period_filter="2026-05-15")
    codex = plugin.extract_totals(by_agent["codex"], period_filter="2026-05-15")
    total = plugin.extract_totals(records, period_filter="2026-05-15")

    # Both buckets see the full $5 on the mixed day...
    assert claude["cost"] == pytest.approx(5.00)
    assert codex["cost"] == pytest.approx(5.00)
    # ...but the source-of-truth total is the actual $5, not $10.
    assert total["cost"] == pytest.approx(5.00)


def test_fmt_cost_zero(plugin):
    assert plugin.fmt_cost(0) == "$0.00"
    assert plugin.fmt_cost(None) == "$0.00"


def test_fmt_cost_dollars(plugin):
    assert plugin.fmt_cost(1.5) == "$1.50"
    assert plugin.fmt_cost(1234.567) == "$1,234.57"
    assert plugin.fmt_cost(0.123) == "$0.123"


def test_fmt_tokens_scaling(plugin):
    assert plugin.fmt_tokens(0) == "0"
    assert plugin.fmt_tokens(500) == "500"
    assert plugin.fmt_tokens(12_345) == "12.3K"
    assert plugin.fmt_tokens(1_234_567) == "1.2M"
