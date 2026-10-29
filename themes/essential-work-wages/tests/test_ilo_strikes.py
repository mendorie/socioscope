"""ILOSTAT 産業別 労働争議（STR_*_ECO_*_A）: fetch → stage → mart の状態検証と純粋変換のテスト。"""

from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import ilo_strikes as mod
from theme_essential_work_wages.pipeline import THEME

FIXTURE = Path(__file__).parent / "fixtures" / "ilo_str_tstr_eco_nb_sample.json"


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


# ---- 定数・契約


def test_module_exposes_the_source_contract() -> None:
    assert mod.SOURCE == "ilo_strikes"
    assert "CC BY 4.0" in mod.LICENSE
    assert mod.MAGIC == b"["
    assert set(mod.INDICATORS) == {
        "strikes_n",
        "days_not_worked",
        "workers_involved_thousands",
        "days_not_worked_per_1000_workers",
    }
    url = mod.url("strikes_n")
    assert url.startswith("https://rplumber.ilo.org/data/indicator/?id=STR_TSTR_ECO_NB_A")
    assert "timefrom=2010" in url and "format=.json" in url
    assert "ref_area" not in url  # 全世界を 1 リクエストで取る
    assert mod.raw_name("strikes_n") == "str_tstr_eco_nb_a.json"


# ---- parse（純粋変換）


def test_parse_keeps_isic4_sections_and_total_only_and_drops_records_without_value() -> None:
    rows = mod.parse(FIXTURE.read_bytes(), "strikes_n")
    assert [(r["iso3"], r["year"], r["classif1"]) for r in rows] == [
        ("JPN", 2023, "ECO_ISIC4_H"),
        ("JPN", 2023, "ECO_ISIC4_Q"),
        ("JPN", 2023, "ECO_ISIC4_TOTAL"),
    ]
    q = rows[1]
    assert q == {
        "iso3": "JPN",
        "year": 2023,
        "classif1": "ECO_ISIC4_Q",
        "industry": "Q",
        "metric": "strikes_n",
        "value": 28.0,
        "note": "T17:170",
    }
    assert rows[2]["industry"] == "TOTAL"


def test_parse_is_deterministic_regardless_of_input_order() -> None:
    import json

    doc = json.loads(FIXTURE.read_bytes())
    a = mod.parse(json.dumps(doc).encode(), "strikes_n")
    b = mod.parse(json.dumps(list(reversed(doc))).encode(), "strikes_n")
    assert a == b


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b'{"a": 1}',
        b'[{"ref_area": "JPN", "time": "2023", "obs_value": 1}]',  # classif1 missing
        b'[{"ref_area": "JPN", "classif1": "ECO_ISIC4_Q", "obs_value": 1}]',  # time missing
        b"[1, 2]",
    ],
)
def test_parse_fails_closed_on_malformed_payload(payload: bytes) -> None:
    with pytest.raises(ValueError, match="ilo_strikes"):
        mod.parse(payload, "strikes_n")


def test_parse_rejects_unknown_metric() -> None:
    with pytest.raises(ValueError, match="metric"):
        mod.parse(FIXTURE.read_bytes(), "wages")


# ---- build_mart（純粋変換）


def test_build_mart_adds_source_sorts_and_rejects_duplicate_keys() -> None:
    staged = mod.parse(FIXTURE.read_bytes(), "strikes_n")
    out = mod.build_mart(list(reversed(staged)))
    assert [r["classif1"] for r in out] == ["ECO_ISIC4_H", "ECO_ISIC4_Q", "ECO_ISIC4_TOTAL"]
    assert all(r["source"] == "ilostat" for r in out)
    assert tuple(out[0]) == (
        "iso3",
        "year",
        "classif1",
        "industry",
        "metric",
        "value",
        "note",
        "source",
    )
    with pytest.raises(ValueError, match="duplicate"):
        mod.build_mart([*staged, dict(staged[0])])


# ---- fetch / stage / mart（状態検証）


def test_fetch_writes_one_raw_per_indicator_and_skips_failures_and_non_json() -> None:
    payload = FIXTURE.read_bytes()
    ctx = make_ctx(
        {
            mod.url("strikes_n"): payload,
            mod.url("days_not_worked"): b"<html>maintenance</html>",
            # workers_involved_thousands: no response -> FetchError
            mod.url("days_not_worked_per_1000_workers"): payload,
        }
    )
    written, skipped = mod.fetch(ctx, [], [])
    assert written == [
        f"{THEME}/ilo_strikes/str_tstr_eco_nb_a.json",
        f"{THEME}/ilo_strikes/str_days_eco_rt_a.json",
    ]
    assert skipped == [
        "str_days_eco_nb_a.json: non-JSON payload",
        "str_work_eco_nb_a.json: no fake response for " + mod.url("workers_involved_thousands"),
    ]
    recs = ctx.raw.records()
    assert [r.name for r in recs] == ["str_tstr_eco_nb_a.json", "str_days_eco_rt_a.json"]
    assert all(r.license == mod.LICENSE and r.theme == THEME for r in recs)
    assert ctx.fetcher.requested == [mod.url(m) for m in mod.INDICATORS]


def test_stage_without_raw_skips_and_writes_nothing() -> None:
    ctx = make_ctx()
    written, skipped = mod.stage(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.raw_name(m)}: no raw" for m in mod.INDICATORS]
    assert ctx.tables.list_tables() == []


def test_mart_without_staged_skips() -> None:
    ctx = make_ctx()
    written, skipped = mod.mart(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.MART_TABLE}: no staged table"]
    assert ctx.tables.list_tables() == []


def test_fetch_stage_mart_end_to_end() -> None:
    payload = FIXTURE.read_bytes()
    ctx = make_ctx({mod.url(m): payload for m in mod.INDICATORS})
    mod.fetch(ctx, [], [])
    written, skipped = mod.stage(ctx, [], [])
    assert written == [f"staged/ilo_strikes/{mod.INDICATORS[m].lower()}" for m in mod.INDICATORS]
    assert skipped == []
    staged = ctx.tables.read_table("staged/ilo_strikes/str_tstr_eco_nb_a")
    assert len(staged) == 3 and staged[0]["metric"] == "strikes_n"

    written, skipped = mod.mart(ctx, [], [])
    assert written == [mod.MART_TABLE] and skipped == []
    mart = ctx.tables.read_table(mod.MART_TABLE)
    assert len(mart) == 3 * len(mod.INDICATORS)
    assert {r["metric"] for r in mart} == set(mod.INDICATORS)
    assert {r["source"] for r in mart} == {"ilostat"}
