"""World Bank WDI 保健支出 3 指標: fetch → stage → mart の状態検証と純粋変換のテスト。"""

import json
from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import wdi_health as mod
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
GHED = FIXTURES / "sh_xpd_ghed_ch_zs_sample.json"
CHEX_GDP = FIXTURES / "sh_xpd_chex_gd_zs_sample.json"
CHEX_PC = FIXTURES / "sh_xpd_chex_pc_cd_sample.json"
PAYLOADS = {
    "SH.XPD.GHED.CH.ZS": GHED.read_bytes(),
    "SH.XPD.CHEX.GD.ZS": CHEX_GDP.read_bytes(),
    "SH.XPD.CHEX.PC.CD": CHEX_PC.read_bytes(),
}


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


# ---- 定数・契約


def test_module_exposes_the_source_contract() -> None:
    assert mod.SOURCE == "wdi_health"
    assert "CC BY 4.0" in mod.LICENSE
    assert mod.MAGIC == b"["
    assert mod.INDICATORS == {
        "SH.XPD.GHED.CH.ZS": "gov_share_pct",
        "SH.XPD.CHEX.GD.ZS": "chex_gdp_pct",
        "SH.XPD.CHEX.PC.CD": "chex_pc_usd",
    }
    assert mod.url("SH.XPD.CHEX.GD.ZS") == (
        "https://api.worldbank.org/v2/country/all/indicator/SH.XPD.CHEX.GD.ZS"
        "?format=json&per_page=20000&date=2010:2024"
    )
    assert mod.raw_name("SH.XPD.CHEX.GD.ZS") == "sh_xpd_chex_gd_zs_2010_2024.json"
    assert mod.staged_table("SH.XPD.CHEX.GD.ZS") == "staged/wdi_health/sh_xpd_chex_gd_zs"
    assert mod.MART_TABLE == "marts/wdi_health_expenditure"


# ---- parse（純粋変換）


def test_parse_drops_aggregates_without_iso3_and_null_values_and_sorts() -> None:
    rows = mod.parse(GHED.read_bytes(), "SH.XPD.GHED.CH.ZS")
    assert rows == [
        {"iso3": "JPN", "year": 2020, "indicator": "SH.XPD.GHED.CH.ZS", "value": 85.3972702},
        {"iso3": "JPN", "year": 2021, "indicator": "SH.XPD.GHED.CH.ZS", "value": 86.26395416},
        {"iso3": "USA", "year": 2021, "indicator": "SH.XPD.GHED.CH.ZS", "value": 55.45219421},
    ]


def test_parse_is_deterministic_regardless_of_input_order() -> None:
    meta, pts = json.loads(GHED.read_bytes())
    a = mod.parse(json.dumps([meta, pts]).encode(), "SH.XPD.GHED.CH.ZS")
    b = mod.parse(json.dumps([meta, list(reversed(pts))]).encode(), "SH.XPD.GHED.CH.ZS")
    assert a == b


def _doc(meta_over: dict[str, object] | None = None, pts: list[object] | None = None) -> bytes:
    meta, points = json.loads(GHED.read_bytes())
    return json.dumps([{**meta, **(meta_over or {})}, points if pts is None else pts]).encode()


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b'{"page": 1}',
        b"[]",
        b'[{"page": 1, "pages": 1, "total": 0}]',  # data array missing
        b'[{"page": 1, "pages": 1, "total": 0}, {"a": 1}]',  # data is not an array
        _doc({"pages": 2}),  # paginated
        _doc({"total": 999}),  # truncated
        _doc(pts=[{"countryiso3code": "JPN", "date": "2021"}]),  # point without value key
        _doc(pts=[{"countryiso3code": "JPN", "value": 1.0}]),  # point without date
        _doc(pts=[{"countryiso3code": "JPN", "date": "2021", "value": "n/a"}]),  # non-numeric
    ],
)
def test_parse_fails_closed_on_malformed_payload(payload: bytes) -> None:
    with pytest.raises(ValueError, match="wdi_health"):
        mod.parse(payload, "SH.XPD.GHED.CH.ZS")


def test_parse_rejects_payload_for_a_different_indicator() -> None:
    with pytest.raises(ValueError, match="indicator"):
        mod.parse(GHED.read_bytes(), "SH.XPD.CHEX.GD.ZS")


def test_parse_rejects_unknown_indicator() -> None:
    with pytest.raises(ValueError, match="indicator"):
        mod.parse(GHED.read_bytes(), "NY.GDP.MKTP.CN")


# ---- build_mart（純粋変換）


def test_build_mart_pivots_wide_by_iso3_year_with_nulls_for_missing_indicators() -> None:
    staged = [r for ind in mod.INDICATORS for r in mod.parse(PAYLOADS[ind], ind)]
    out = mod.build_mart(list(reversed(staged)))
    assert [tuple(r) for r in out] == [
        ("iso3", "year", "gov_share_pct", "chex_gdp_pct", "chex_pc_usd", "source")
    ] * 4
    assert [(r["iso3"], r["year"]) for r in out] == [
        ("JPN", 2020),
        ("JPN", 2021),
        ("USA", 2020),
        ("USA", 2021),
    ]
    assert out[1] == {
        "iso3": "JPN",
        "year": 2021,
        "gov_share_pct": 86.26395416,
        "chex_gdp_pct": 12.08108234,
        "chex_pc_usd": 4843.94433594,
        "source": "worldbank_wdi",
    }
    # USA 2020 is only in the per-capita fixture -> other columns are None
    assert out[2] == {
        "iso3": "USA",
        "year": 2020,
        "gov_share_pct": None,
        "chex_gdp_pct": None,
        "chex_pc_usd": 11648.49511719,
        "source": "worldbank_wdi",
    }


def test_build_mart_rejects_duplicate_keys_and_unknown_indicators() -> None:
    staged = mod.parse(GHED.read_bytes(), "SH.XPD.GHED.CH.ZS")
    with pytest.raises(ValueError, match="duplicate"):
        mod.build_mart([*staged, dict(staged[0])])
    with pytest.raises(ValueError, match="indicator"):
        mod.build_mart([{**staged[0], "indicator": "NY.GDP.MKTP.CN"}])


# ---- fetch / stage / mart（状態検証）


def test_fetch_writes_one_raw_per_indicator_and_skips_failures_and_non_json() -> None:
    ctx = make_ctx(
        {
            mod.url("SH.XPD.GHED.CH.ZS"): PAYLOADS["SH.XPD.GHED.CH.ZS"],
            mod.url("SH.XPD.CHEX.GD.ZS"): b"<html>maintenance</html>",
            # SH.XPD.CHEX.PC.CD: no response -> FetchError
        }
    )
    written, skipped = mod.fetch(ctx, [], [])
    assert written == [f"{THEME}/wdi_health/sh_xpd_ghed_ch_zs_2010_2024.json"]
    assert skipped == [
        "sh_xpd_chex_gd_zs_2010_2024.json: non-JSON payload",
        "sh_xpd_chex_pc_cd_2010_2024.json: no fake response for " + mod.url("SH.XPD.CHEX.PC.CD"),
    ]
    recs = ctx.raw.records()
    assert [(r.name, r.url) for r in recs] == [
        ("sh_xpd_ghed_ch_zs_2010_2024.json", mod.url("SH.XPD.GHED.CH.ZS"))
    ]
    assert recs[0].license == mod.LICENSE and recs[0].theme == THEME
    assert ctx.fetcher.requested == [mod.url(i) for i in mod.INDICATORS]


def test_stage_without_raw_skips_and_writes_nothing() -> None:
    ctx = make_ctx()
    written, skipped = mod.stage(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.raw_name(i)}: no raw" for i in mod.INDICATORS]
    assert ctx.tables.list_tables() == []


def test_mart_without_staged_skips() -> None:
    ctx = make_ctx()
    written, skipped = mod.mart(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.MART_TABLE}: no staged table"]
    assert ctx.tables.list_tables() == []


def test_fetch_stage_mart_end_to_end() -> None:
    ctx = make_ctx({mod.url(i): PAYLOADS[i] for i in mod.INDICATORS})
    mod.fetch(ctx, [], [])
    written, skipped = mod.stage(ctx, [], [])
    assert written == [mod.staged_table(i) for i in mod.INDICATORS]
    assert skipped == []
    staged = ctx.tables.read_table("staged/wdi_health/sh_xpd_chex_pc_cd")
    assert len(staged) == 4 and staged[0]["indicator"] == "SH.XPD.CHEX.PC.CD"

    written, skipped = mod.mart(ctx, [], [])
    assert written == [mod.MART_TABLE] and skipped == []
    mart = ctx.tables.read_table(mod.MART_TABLE)
    assert len(mart) == 4
    assert {r["source"] for r in mart} == {"worldbank_wdi"}
    assert mart[1]["chex_gdp_pct"] == 12.08108234
