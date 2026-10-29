"""OECD Remuneration of health professionals (DF_REMUN): classical tests.

The fixture is the real CSV header plus 4 rows (COL general practitioners 2019 x 3 sexes as
factor of average wage; JPN hospital nurses 2020 with OBS_STATUS=E).
"""

from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import oecd_remun as mod
from theme_essential_work_wages.pipeline import THEME

FIXTURE = (Path(__file__).parent / "fixtures" / "oecd_remun.csv").read_bytes()
HEADER = FIXTURE.splitlines()[0]
JPN_ROW = FIXTURE.splitlines()[4]


def make_ctx(responses: dict[str, bytes]) -> Context:
    return Context(
        fetcher=FakeFetcher(responses), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def test_constants() -> None:
    assert mod.SOURCE == "oecd_health_remun"
    assert mod.URL.startswith(
        "https://sdmx.oecd.org/public/rest/data/OECD.ELS.HD,DSD_HEALTH_REAC_EMP@DF_REMUN,/all"
    )
    assert "format=csvfilewithlabels" in mod.URL
    assert "startPeriod=2010" in mod.URL
    assert mod.RAW_NAME == "remuneration.csv"
    assert FIXTURE.startswith(mod.MAGIC)


# ---------------------------------------------------------------- parse (pure)


def test_parse_rows_columns_and_values() -> None:
    rows = mod.parse(FIXTURE)
    assert len(rows) == 4
    assert list(rows[0]) == [
        "iso3",
        "year",
        "measure",
        "unit",
        "health_prof",
        "health_prof_label",
        "worker_status",
        "sex",
        "price_base",
        "value",
        "obs_status",
    ]
    jpn = next(r for r in rows if r["iso3"] == "JPN")
    assert jpn == {
        "iso3": "JPN",
        "year": 2020,
        "measure": "AI",
        "unit": "FCTR_WG_A_SAL_A",
        "health_prof": "RINF",
        "health_prof_label": "Hospital nurses",
        "worker_status": "ICSE93_1",
        "sex": "_T",
        "price_base": "V",
        "value": 1.04,
        "obs_status": "E",
    }
    col = {r["sex"]: r["value"] for r in rows if r["iso3"] == "COL"}
    assert col == {"_T": 1.48, "M": 1.53, "F": 1.43}
    assert next(r for r in rows if r["sex"] == "_T" and r["iso3"] == "COL")["obs_status"] == ""


def test_parse_is_sorted_by_key_and_deterministic() -> None:
    rows = mod.parse(FIXTURE)
    keys = [mod.key_of(r) for r in rows]
    assert keys == sorted(keys)
    assert rows == mod.parse(FIXTURE)


def test_parse_drops_empty_values() -> None:
    blank = JPN_ROW.replace(b",2020,,1.04,", b",2020,,,")
    rows = mod.parse(b"\n".join([HEADER, blank]))
    assert rows == []


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (b"REF_AREA,TIME_PERIOD\nJPN,2020\n", "columns"),
        (HEADER + b"\n" + JPN_ROW.replace(b"DF_REMUN(1.1)", b"DF_OTHER(1.0)"), "STRUCTURE_ID"),
        (HEADER + b"\n" + JPN_ROW.replace(b",AI,", b",XX,"), "MEASURE"),
        (HEADER + b"\n" + JPN_ROW.replace(b",RINF,", b",DENT,"), "HEALTH_PROF"),
        (HEADER + b"\n" + JPN_ROW.replace(b",ICSE93_1,", b",ICSE93_9,"), "WORKER_STATUS"),
        (HEADER + b"\n" + JPN_ROW.replace(b",FCTR_WG_A_SAL_A,", b",PC,"), "UNIT_MEASURE"),
        (HEADER + b"\n" + JPN_ROW.replace(b",2020,", b",2020-Q1,"), "TIME_PERIOD"),
        (HEADER + b"\n" + JPN_ROW.replace(b",1.04,", b",n/a,"), "OBS_VALUE"),
        (HEADER + b"\n" + JPN_ROW + b"\n" + JPN_ROW, "duplicate"),
    ],
)
def test_parse_fails_closed(payload: bytes, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        mod.parse(payload)


# ---------------------------------------------------------------- mart (pure)


def test_build_mart_adds_source_sorts_and_rejects_duplicates() -> None:
    staged = mod.parse(FIXTURE)
    out = mod.build_mart(list(reversed(staged)))
    assert [r["iso3"] for r in out] == ["COL", "COL", "COL", "JPN"]
    assert list(out[0]) == [*staged[0], "source"]
    assert {r["source"] for r in out} == {mod.SOURCE}
    with pytest.raises(ValueError, match="duplicate"):
        mod.build_mart([*staged, dict(staged[0])])


# ---------------------------------------------------------------- stages (state)


def test_fetch_puts_raw_with_manifest_and_rejects_non_csv() -> None:
    ctx = make_ctx({mod.URL: FIXTURE})
    written, skipped = mod.fetch(ctx, [], [])
    assert written == [f"{THEME}/{mod.SOURCE}/{mod.RAW_NAME}"]
    assert skipped == []
    rec = ctx.raw.records()[0]
    assert (rec.url, rec.license, rec.theme) == (mod.URL, mod.LICENSE, THEME)

    ctx = make_ctx({mod.URL: b"<html>"})
    written, skipped = mod.fetch(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.RAW_NAME}: non-CSV payload"]
    assert ctx.raw.records() == []

    ctx = make_ctx({})
    written, skipped = mod.fetch(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.RAW_NAME}: no fake response for {mod.URL}"]


def test_stage_and_mart_flow_and_missing_inputs() -> None:
    ctx = make_ctx({})
    assert mod.stage(ctx, [], []) == ([], [f"{mod.RAW_NAME}: no raw"])
    assert mod.mart(ctx, [], []) == ([], [f"{mod.STAGED_TABLE}: no staged table"])

    ctx = make_ctx({mod.URL: FIXTURE})
    mod.fetch(ctx, [], [])
    assert mod.stage(ctx, [], []) == ([mod.STAGED_TABLE], [])
    assert mod.mart(ctx, [], []) == ([mod.MART_TABLE], [])
    rows = ctx.tables.read_table(mod.MART_TABLE)
    assert len(rows) == 4
    assert rows[-1]["iso3"] == "JPN"
    assert rows[-1]["source"] == mod.SOURCE


def test_stage_reports_bad_payload_instead_of_raising() -> None:
    ctx = make_ctx({})
    ctx.raw.put(
        theme=THEME,
        source=mod.SOURCE,
        name=mod.RAW_NAME,
        url=mod.URL,
        license=mod.LICENSE,
        payload=HEADER + b"\n" + JPN_ROW.replace(b",AI,", b",XX,"),
    )
    written, skipped = mod.stage(ctx, [], [])
    assert written == []
    assert len(skipped) == 1 and skipped[0].startswith(f"{mod.RAW_NAME}: ")
    assert ctx.tables.list_tables() == []
