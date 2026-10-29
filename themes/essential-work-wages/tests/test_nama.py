"""Eurostat national accounts by industry (nama_10_a64 / nama_10_a64_e): classical tests.

Fixtures are the live JSON-stat responses (2026-10-29) cut to geo {EU27_2020, DE, EL} x
time {2018, 2022} x nace_r2 {TOTAL, B-E, C, C10-C12, K, K64, L68A, M_N}, re-indexed. They keep
one flagged cell (DE L68A 2022 value added, status ``p``), employment ``0.0`` for L68A in
EU27/EL and *missing* employment for DE L68A (per-person must be None in both cases).
"""

import json
from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import nama as mod
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
VA_FIXTURE = (FIXTURES / "nama_10_a64_sample.json").read_bytes()
EMP_FIXTURE = (FIXTURES / "nama_10_a64_e_sample.json").read_bytes()
VA, EMP = mod.DATASETS


def make_ctx(responses: dict[str, bytes]) -> Context:
    return Context(
        fetcher=FakeFetcher(responses), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def responses() -> dict[str, bytes]:
    return {VA.url: VA_FIXTURE, EMP.url: EMP_FIXTURE}


def mutate(payload: bytes, **changes: object) -> bytes:
    doc = json.loads(payload)
    doc.update(changes)
    return json.dumps(doc).encode()


# ---------------------------------------------------------------- constants / requests


def test_constants_and_urls() -> None:
    assert mod.SOURCE == "eurostat_nama"
    assert mod.MAGIC == b"{"
    assert [d.name for d in mod.DATASETS] == ["nama_10_a64", "nama_10_a64_e"]
    assert VA.raw_name == "nama_10_a64_b1g_2015_2023.json"
    assert EMP.raw_name == "nama_10_a64_e_emp_2015_2023.json"
    assert VA.staged_table == "staged/nama/nama_10_a64"
    assert EMP.staged_table == "staged/nama/nama_10_a64_e"
    assert VA.url.startswith(f"{mod.BASE}/nama_10_a64?format=JSON&lang=EN")
    assert "&na_item=B1G" in VA.url and "&unit=CP_MEUR" in VA.url
    assert "&na_item=EMP_DC&na_item=SAL_DC" in EMP.url and "&unit=THS_PER" in EMP.url
    for d in mod.DATASETS:
        assert all(f"&time={y}" in d.url for y in range(2015, 2024))
        assert "&time=2014" not in d.url and "&time=2024" not in d.url
    assert VA_FIXTURE.startswith(mod.MAGIC)
    assert mod.MART_TABLE == "marts/nama_industry_value_added_employment"


# ---------------------------------------------------------------- parse (pure)


def test_parse_value_added_rows() -> None:
    rows = mod.parse(VA_FIXTURE, VA)
    assert len(rows) == 48
    assert (
        list(rows[0])
        == list(mod.STAGED_COLUMNS)
        == [
            "geo",
            "year",
            "nace_r2",
            "nace_r2_label",
            "na_item",
            "unit",
            "value",
            "flags",
        ]
    )
    de_c = next(r for r in rows if (r["geo"], r["year"], r["nace_r2"]) == ("DE", 2022, "C"))
    assert de_c == {
        "geo": "DE",
        "year": 2022,
        "nace_r2": "C",
        "nace_r2_label": "Manufacturing",
        "na_item": "B1G",
        "unit": "CP_MEUR",
        "value": 731784.0,
        "flags": None,
    }
    flagged = [r for r in rows if r["flags"]]
    assert [(r["geo"], r["year"], r["nace_r2"], r["flags"]) for r in flagged] == [
        ("DE", 2022, "L68A", "p")
    ]
    assert {r["year"] for r in rows} == {2018, 2022}


def test_parse_employment_rows_keep_both_na_items_and_skip_missing_cells() -> None:
    rows = mod.parse(EMP_FIXTURE, EMP)
    assert len(rows) == 92  # 96 cells, DE L68A x 2 years x 2 items missing
    assert {r["na_item"] for r in rows} == {"EMP_DC", "SAL_DC"}
    assert {r["unit"] for r in rows} == {"THS_PER"}
    assert not [r for r in rows if r["geo"] == "DE" and r["nace_r2"] == "L68A"]
    el = {
        r["na_item"]: r["value"]
        for r in rows
        if (r["geo"], r["year"], r["nace_r2"]) == ("EL", 2022, "C")
    }
    assert el == {"EMP_DC": 403.8, "SAL_DC": 338.0}
    zero = next(
        r for r in rows if (r["geo"], r["nace_r2"], r["na_item"]) == ("EL", "L68A", "EMP_DC")
    )
    assert zero["value"] == 0.0


def test_parse_is_sorted_and_deterministic() -> None:
    rows = mod.parse(EMP_FIXTURE, EMP)
    keys = [mod.staged_key(r) for r in rows]
    assert keys == sorted(keys)
    assert rows == mod.parse(EMP_FIXTURE, EMP)


def _swap_dims(payload: bytes) -> bytes:
    doc = json.loads(payload)
    doc["id"] = [d if d != "nace_r2" else "nace_r1" for d in doc["id"]]
    doc["dimension"]["nace_r1"] = doc["dimension"].pop("nace_r2")
    return json.dumps(doc).encode()


def _with_na_item(payload: bytes, code: str) -> bytes:
    doc = json.loads(payload)
    cat = doc["dimension"]["na_item"]["category"]
    cat["index"] = {code: 0}
    cat["label"] = {code: code}
    return json.dumps(doc).encode()


def _with_time(payload: bytes, years: list[str]) -> bytes:
    doc = json.loads(payload)
    cat = doc["dimension"]["time"]["category"]
    cat["index"] = {y: i for i, y in enumerate(years)}
    cat["label"] = {y: y for y in years}
    return json.dumps(doc).encode()


@pytest.mark.parametrize(
    ("payload", "spec", "match"),
    [
        (b"<html>", VA, "not JSON"),
        (b"[]", VA, "not a JSON object"),
        (b'{"error": {"status": 400}}', VA, "API error"),
        (mutate(VA_FIXTURE, **{"class": "collection"}), VA, "class"),
        (_swap_dims(VA_FIXTURE), VA, "dimensions"),
        (mutate(VA_FIXTURE, size=[1, 1, 8, 1, 3, 3]), VA, "size mismatch"),
        (_with_na_item(VA_FIXTURE, "D1"), VA, "na_item"),
        (_with_na_item(EMP_FIXTURE, "EMP_DC"), EMP, "size mismatch"),  # size 2, one code
        (_with_time(VA_FIXTURE, ["2018", "2024"]), VA, "time"),
    ],
)
def test_parse_fails_closed(payload: bytes, spec: mod.Dataset, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        mod.parse(payload, spec)


def test_parse_rejects_unit_and_dataset_mixups() -> None:
    with pytest.raises(ValueError, match="unit"):
        mod.parse(VA_FIXTURE, EMP)  # value-added payload parsed with the employment spec
    with pytest.raises(ValueError, match="unit"):
        mod.parse(EMP_FIXTURE, VA)


# ---------------------------------------------------------------- nace_section / mart (pure)


@pytest.mark.parametrize(
    ("code", "section"),
    [
        ("A", "A"),
        ("C", "C"),
        ("C10-C12", "C"),
        ("C22_C23", "C"),
        ("L68A", "L"),
        ("U99", "U"),
        ("TOTAL", None),
        ("B-E", None),
        ("G-I", None),
        ("M_N", None),
        ("O-Q", None),
        ("R-U", None),
    ],
)
def test_nace_section(code: str, section: str | None) -> None:
    assert mod.nace_section(code) == section


def test_build_mart_wide_rows() -> None:
    staged = [*mod.parse(VA_FIXTURE, VA), *mod.parse(EMP_FIXTURE, EMP)]
    out = mod.build_mart(staged)
    assert len(out) == 48  # 3 geo x 2 years x 8 nace
    assert (
        list(out[0])
        == list(mod.MART_COLUMNS)
        == [
            "iso3",
            "geo",
            "year",
            "nace_r2",
            "nace_r2_label",
            "nace_section",
            "value_added_meur",
            "employment_ths",
            "employees_ths",
            "value_added_per_person_keur",
            "flags",
            "source",
        ]
    )
    by = {(r["geo"], r["year"], r["nace_r2"]): r for r in out}
    de_c = by["DE", 2022, "C"]
    assert de_c["iso3"] == "DEU"
    assert de_c["nace_section"] == "C"
    assert de_c["nace_r2_label"] == "Manufacturing"
    assert (de_c["value_added_meur"], de_c["employment_ths"], de_c["employees_ths"]) == (
        731784.0,
        7486.0,
        7262.0,
    )
    assert de_c["value_added_per_person_keur"] == pytest.approx(731784.0 / 7486.0)  # 97.75
    assert de_c["flags"] is None
    assert de_c["source"] == "eurostat_nama"
    assert by["EL", 2018, "K64"]["iso3"] == "GRC"
    assert by["EU27_2020", 2018, "TOTAL"]["iso3"] is None
    assert by["EU27_2020", 2018, "TOTAL"]["nace_section"] is None
    assert by["DE", 2018, "M_N"]["nace_section"] is None


def test_build_mart_missing_and_zero_employment() -> None:
    staged = [*mod.parse(VA_FIXTURE, VA), *mod.parse(EMP_FIXTURE, EMP)]
    by = {(r["geo"], r["year"], r["nace_r2"]): r for r in mod.build_mart(staged)}
    de = by["DE", 2022, "L68A"]  # value added present (flag p), employment missing
    assert de["value_added_meur"] == 162798.0
    assert de["employment_ths"] is None and de["employees_ths"] is None
    assert de["value_added_per_person_keur"] is None
    assert de["flags"] == "p"
    el = by["EL", 2022, "L68A"]  # employment 0.0 -> no division
    assert el["employment_ths"] == 0.0
    assert el["value_added_per_person_keur"] is None


def test_build_mart_employment_only_rows_keep_none_value_added() -> None:
    out = mod.build_mart(mod.parse(EMP_FIXTURE, EMP))
    assert len(out) == 46  # DE L68A x 2 years absent entirely
    assert {r["value_added_meur"] for r in out} == {None}
    assert {r["value_added_per_person_keur"] for r in out} == {None}
    assert all(r["employment_ths"] is not None for r in out)


def test_build_mart_sorted_and_fails_on_duplicates_or_unknown_items() -> None:
    staged = [*mod.parse(VA_FIXTURE, VA), *mod.parse(EMP_FIXTURE, EMP)]
    out = mod.build_mart(list(reversed(staged)))
    keys = [(r["geo"], r["year"], r["nace_r2"]) for r in out]
    assert keys == sorted(keys)
    assert out == mod.build_mart(staged)
    with pytest.raises(ValueError, match="duplicate"):
        mod.build_mart([*staged, dict(staged[0])])
    with pytest.raises(ValueError, match="na_item"):
        mod.build_mart([{**staged[0], "na_item": "D1"}])


def test_build_mart_flags_merge_from_any_item() -> None:
    staged = mod.parse(VA_FIXTURE, VA)
    va = next(r for r in staged if (r["geo"], r["year"], r["nace_r2"]) == ("DE", 2022, "C"))
    emp = {**va, "na_item": "EMP_DC", "unit": "THS_PER", "value": 10.0, "flags": "e"}
    (row,) = mod.build_mart([va, emp])
    assert row["flags"] == "e"


# ---------------------------------------------------------------- stages (state)


def test_fetch_puts_raw_with_manifest_and_rejects_non_json() -> None:
    ctx = make_ctx(responses())
    written, skipped = mod.fetch(ctx, [], [])
    assert written == [f"{THEME}/{mod.SOURCE}/{d.raw_name}" for d in mod.DATASETS]
    assert skipped == []
    recs = ctx.raw.records()
    assert [(r.url, r.license, r.theme) for r in recs] == [
        (d.url, mod.LICENSE, THEME) for d in mod.DATASETS
    ]

    ctx = make_ctx({VA.url: b"<html>", EMP.url: EMP_FIXTURE})
    written, skipped = mod.fetch(ctx, [], [])
    assert written == [f"{THEME}/{mod.SOURCE}/{EMP.raw_name}"]
    assert skipped == [f"{VA.raw_name}: non-JSON payload"]

    ctx = make_ctx({})
    written, skipped = mod.fetch(ctx, [], [])
    assert written == []
    assert skipped == [f"{d.raw_name}: no fake response for {d.url}" for d in mod.DATASETS]
    assert ctx.raw.records() == []


def test_stage_and_mart_flow_and_missing_inputs() -> None:
    ctx = make_ctx({})
    assert mod.stage(ctx, [], []) == ([], [f"{d.raw_name}: no raw" for d in mod.DATASETS])
    assert mod.mart(ctx, [], []) == (
        [],
        [f"{d.staged_table}: no staged table" for d in mod.DATASETS],
    )

    ctx = make_ctx(responses())
    mod.fetch(ctx, [], [])
    assert mod.stage(ctx, [], []) == ([d.staged_table for d in mod.DATASETS], [])
    assert len(ctx.tables.read_table(VA.staged_table)) == 48
    assert len(ctx.tables.read_table(EMP.staged_table)) == 92
    assert mod.mart(ctx, [], []) == ([mod.MART_TABLE], [])
    rows = ctx.tables.read_table(mod.MART_TABLE)
    assert len(rows) == 48
    assert rows[0]["geo"] == "DE" and rows[0]["year"] == 2018
    assert {r["source"] for r in rows} == {mod.SOURCE}


def test_mart_runs_with_only_one_staged_table() -> None:
    ctx = make_ctx({VA.url: VA_FIXTURE})
    mod.fetch(ctx, [], [])
    mod.stage(ctx, [], [])
    written, skipped = mod.mart(ctx, [], [])
    assert written == [mod.MART_TABLE]
    assert skipped == [f"{EMP.staged_table}: no staged table"]
    rows = ctx.tables.read_table(mod.MART_TABLE)
    assert len(rows) == 48 and {r["employment_ths"] for r in rows} == {None}


def test_stage_reports_bad_payload_instead_of_raising() -> None:
    ctx = make_ctx({})
    ctx.raw.put(
        theme=THEME,
        source=mod.SOURCE,
        name=VA.raw_name,
        url=VA.url,
        license=mod.LICENSE,
        payload=_swap_dims(VA_FIXTURE),
    )
    written, skipped = mod.stage(ctx, [], [])
    assert written == []
    assert skipped[0].startswith(f"{VA.raw_name}: ") and "dimensions" in skipped[0]
    assert skipped[1] == f"{EMP.raw_name}: no raw"
    assert ctx.tables.list_tables() == []
