"""Eurostat SES (earn_ses22_47 / earn_ses22_14 / earn_ses18_47 / earn_ses18_14): classical tests.

Fixtures are hand-cut JSON-stat 2.0 documents with the dimension order of the live API
(2026-10-29): 2 geo x 2 isco08 x 2 nace_r2 x 2 sex, one cell missing and one flagged.
"""

import json
from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import ses
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
S22_47 = (FIXTURES / "ses_earn_ses22_47.json").read_bytes()
S22_14 = (FIXTURES / "ses_earn_ses22_14.json").read_bytes()
S18_47 = (FIXTURES / "ses_earn_ses18_47.json").read_bytes()


def ds(name: str) -> ses.Dataset:
    return next(d for d in ses.DATASETS if d.name == name)


def make_ctx(responses: dict[str, bytes]) -> Context:
    return Context(
        fetcher=FakeFetcher(responses), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


# ---------------------------------------------------------------- requests


def test_four_datasets_one_request_each_with_fixed_filters() -> None:
    assert [d.name for d in ses.DATASETS] == [
        "earn_ses22_47",
        "earn_ses22_14",
        "earn_ses18_47",
        "earn_ses18_14",
    ]
    url = ds("earn_ses22_47").url
    assert url.startswith(f"{ses.BASE}/earn_ses22_47?format=JSON&lang=EN")
    for part in ("&unit=EUR", "&sizeclas=TOTAL", "&indic_se=ERN", "&sex=T", "&sex=M", "&sex=F"):
        assert part in url
    assert "&age=" not in url
    assert "&age=TOTAL" in ds("earn_ses18_14").url
    assert ds("earn_ses22_47").raw_name == "ses22_47.json"
    assert ds("earn_ses18_14").raw_name == "ses18_14.json"
    assert len({d.url for d in ses.DATASETS}) == 4


# ---------------------------------------------------------------- parse (pure)


def test_parse_expands_cells_with_labels_and_drops_missing_cells() -> None:
    rows = ses.parse(S22_47, ds("earn_ses22_47"))
    assert len(rows) == 15  # 16 cells, one absent from `value`
    assert list(rows[0]) == [
        "geo",
        "year",
        "isco08",
        "isco08_label",
        "nace_r2",
        "nace_r2_label",
        "sex",
        "hourly_earnings_eur",
        "flags",
    ]
    by_key = {(r["geo"], r["isco08"], r["nace_r2"], r["sex"]): r for r in rows}
    assert by_key[("DE", "OC2", "B-S_X_O", "T")]["hourly_earnings_eur"] == 31.21
    assert by_key[("EU27_2020", "OC5", "Q", "T")]["hourly_earnings_eur"] == 14.1
    assert ("EU27_2020", "OC5", "Q", "F") not in by_key
    assert by_key[("DE", "OC5", "Q", "T")]["flags"] == "u"
    assert by_key[("DE", "OC2", "B-S_X_O", "T")]["flags"] is None
    r = by_key[("DE", "OC5", "Q", "F")]
    assert r["year"] == 2022
    assert r["isco08_label"] == "Service and sales workers"
    assert r["nace_r2_label"] == "Human health and social work activities"
    assert r["hourly_earnings_eur"] == 16.1


def test_parse_is_sorted_and_deterministic() -> None:
    rows = ses.parse(S22_47, ds("earn_ses22_47"))
    keys = [(r["geo"], r["year"], r["isco08"], r["nace_r2"], r["sex"]) for r in rows]
    assert keys == sorted(keys)
    assert rows == ses.parse(S22_47, ds("earn_ses22_47"))


def test_parse_handles_2018_dimension_order_by_name() -> None:
    rows = ses.parse(S18_47, ds("earn_ses18_47"))
    assert [(r["geo"], r["year"], r["isco08"], r["nace_r2"], r["sex"]) for r in rows] == [
        ("UK", 2018, "OC2", "Q", "T"),
        ("UK", 2018, "OC5", "Q", "T"),
    ]


def test_parse_occupation_total_dataset_fills_nace_from_dataset_scope() -> None:
    rows = ses.parse(S22_14, ds("earn_ses22_14"))
    assert len(rows) == 7
    assert {r["nace_r2"] for r in rows} == {"B-S_X_O"}
    assert {r["nace_r2_label"] for r in rows} == {ses.NACE_B_S_X_O_LABEL}
    by_key = {(r["geo"], r["isco08"], r["sex"]): r["hourly_earnings_eur"] for r in rows}
    assert by_key[("DE", "TOTAL", "T")] == 24.5
    assert by_key[("EU27_2020", "OC5", "T")] == 13.45
    assert ("EU27_2020", "OC5", "F") not in by_key


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda d: d["id"].__setitem__(3, "isco88"), "dimension"),
        (lambda d: d["dimension"]["unit"]["category"]["index"].update({"PPS": 1}), "unit"),
        (lambda d: d["dimension"]["indic_se"]["category"]["index"].update({"OPAY": 1}), "indic_se"),
        (lambda d: d["dimension"]["sizeclas"]["category"]["index"].update({"GE10": 1}), "sizeclas"),
        (lambda d: d.__setitem__("class", "collection"), "class"),
        (lambda d: d["size"].__setitem__(1, 3), "size"),
    ],
)
def test_parse_fails_closed_on_unexpected_shape(mutate, match) -> None:  # type: ignore[no-untyped-def]
    doc = json.loads(S22_47)
    mutate(doc)
    with pytest.raises(ValueError, match=match):
        ses.parse(json.dumps(doc).encode(), ds("earn_ses22_47"))


def test_parse_rejects_error_documents_and_non_json() -> None:
    with pytest.raises(ValueError, match="error"):
        ses.parse(b'{"error": [{"status": 400, "label": "bad"}]}', ds("earn_ses22_47"))
    with pytest.raises(ValueError, match="JSON"):
        ses.parse(b"<html>", ds("earn_ses22_47"))


def test_parse_rejects_dataset_mismatch_between_payload_and_spec() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        ses.parse(S22_14, ds("earn_ses22_47"))


# ---------------------------------------------------------------- iso3


def test_geo_mapping_covers_eu27_efta_uk_candidates_and_leaves_aggregates_none() -> None:
    assert ses.iso3_of("EL") == "GRC"
    assert ses.iso3_of("UK") == "GBR"
    assert ses.iso3_of("CH") == "CHE"
    assert ses.iso3_of("RS") == "SRB"
    assert ses.iso3_of("EU27_2020") is None
    assert ses.iso3_of("EA20") is None
    assert len(ses.GEO_TO_ISO3) == 37  # EU27 + IS/NO/CH/LI/UK + BA/MK/AL/RS/TR


# ---------------------------------------------------------------- marts (pure)


def test_build_industry_mart_concatenates_years_sorts_and_adds_iso3_and_source() -> None:
    staged = [
        *ses.parse(S22_47, ds("earn_ses22_47")),
        *ses.parse(S18_47, ds("earn_ses18_47")),
    ]
    out = ses.build_industry_mart(staged)
    assert len(out) == 17
    assert list(out[0]) == [
        "iso3",
        "geo",
        "year",
        "isco08",
        "isco08_label",
        "nace_r2",
        "nace_r2_label",
        "sex",
        "hourly_earnings_eur",
        "flags",
        "source",
    ]
    assert {r["source"] for r in out} == {"eurostat_ses"}
    de = [r for r in out if r["geo"] == "DE"]
    assert {r["iso3"] for r in de} == {"DEU"}
    assert {r["iso3"] for r in out if r["geo"] == "EU27_2020"} == {None}
    assert [r["iso3"] for r in out if r["year"] == 2018] == ["GBR", "GBR"]
    keys = [(r["geo"], r["year"], r["isco08"], r["nace_r2"], r["sex"]) for r in out]
    assert keys == sorted(keys)


def test_build_industry_mart_rejects_duplicate_keys() -> None:
    staged = ses.parse(S22_47, ds("earn_ses22_47"))
    with pytest.raises(ValueError, match="duplicate"):
        ses.build_industry_mart([*staged, dict(staged[0])])


def test_build_occupation_mart_keeps_nace_scope_column() -> None:
    out = ses.build_occupation_mart(ses.parse(S22_14, ds("earn_ses22_14")))
    assert len(out) == 7
    assert list(out[0]) == [
        "iso3",
        "geo",
        "year",
        "isco08",
        "isco08_label",
        "nace_r2",
        "sex",
        "hourly_earnings_eur",
        "flags",
        "source",
    ]
    assert {r["nace_r2"] for r in out} == {"B-S_X_O"}
    keys = [(r["geo"], r["year"], r["isco08"], r["sex"]) for r in out]
    assert keys == sorted(keys)
    with pytest.raises(ValueError, match="duplicate"):
        ses.build_occupation_mart([*out, dict(out[0])])


# ---------------------------------------------------------------- stages (state)


def test_fetch_writes_each_dataset_with_manifest_and_skips_failures_and_non_json() -> None:
    ctx = make_ctx(
        {
            ds("earn_ses22_47").url: S22_47,
            ds("earn_ses22_14").url: S22_14,
            ds("earn_ses18_47").url: b"<html>maintenance</html>",
        }
    )
    written, skipped = ses.fetch(ctx, [], [])
    assert written == [
        f"{THEME}/eurostat_ses/ses22_47.json",
        f"{THEME}/eurostat_ses/ses22_14.json",
    ]
    assert skipped == [
        "ses18_47.json: non-JSON payload",
        f"ses18_14.json: no fake response for {ds('earn_ses18_14').url}",
    ]
    recs = ctx.raw.records()
    assert [r.name for r in recs] == ["ses22_47.json", "ses22_14.json"]
    assert recs[0].url == ds("earn_ses22_47").url
    assert recs[0].license == ses.LICENSE
    assert recs[0].theme == THEME
    assert ctx.raw.get(theme=THEME, source=ses.SOURCE, name="ses18_47.json") is None


def test_stage_writes_one_table_per_raw_and_reports_missing_raws() -> None:
    ctx = make_ctx({})
    ctx.raw.put(
        theme=THEME,
        source=ses.SOURCE,
        name="ses22_47.json",
        url=ds("earn_ses22_47").url,
        license=ses.LICENSE,
        payload=S22_47,
    )
    written, skipped = ses.stage(ctx, [], [])
    assert written == ["staged/ses/earn_ses22_47"]
    assert skipped == [
        "ses22_14.json: no raw",
        "ses18_47.json: no raw",
        "ses18_14.json: no raw",
    ]
    assert len(ctx.tables.read_table("staged/ses/earn_ses22_47")) == 15


def test_stage_reports_a_bad_payload_instead_of_raising() -> None:
    ctx = make_ctx({})
    ctx.raw.put(
        theme=THEME,
        source=ses.SOURCE,
        name="ses22_47.json",
        url=ds("earn_ses22_47").url,
        license=ses.LICENSE,
        payload=S22_14,  # wrong dataset shape
    )
    written, skipped = ses.stage(ctx, [], [])
    assert written == []
    assert len(skipped) == 4
    assert skipped[0].startswith("ses22_47.json: ")
    assert ctx.tables.list_tables() == []


def test_mart_builds_both_tables_from_available_staged_tables() -> None:
    ctx = make_ctx({})
    ctx.tables.write_table("staged/ses/earn_ses22_47", ses.parse(S22_47, ds("earn_ses22_47")))
    ctx.tables.write_table("staged/ses/earn_ses18_47", ses.parse(S18_47, ds("earn_ses18_47")))
    ctx.tables.write_table("staged/ses/earn_ses22_14", ses.parse(S22_14, ds("earn_ses22_14")))
    written, skipped = ses.mart(ctx, [], [])
    assert written == [ses.INDUSTRY_MART, ses.OCCUPATION_MART]
    assert skipped == ["staged/ses/earn_ses18_14: no staged table"]
    assert len(ctx.tables.read_table(ses.INDUSTRY_MART)) == 17
    assert len(ctx.tables.read_table(ses.OCCUPATION_MART)) == 7


def test_mart_writes_nothing_when_no_staged_table_exists() -> None:
    ctx = make_ctx({})
    written, skipped = ses.mart(ctx, [], [])
    assert written == []
    assert len(skipped) == 4
    assert ctx.tables.list_tables() == []


def test_full_flow_fetch_stage_mart() -> None:
    ctx = make_ctx({d.url: p for d, p in zip(ses.DATASETS, (S22_47, S22_14, S18_47), strict=False)})
    ses.fetch(ctx, [], [])
    ses.stage(ctx, [], [])
    written, _ = ses.mart(ctx, [], [])
    assert written == [ses.INDUSTRY_MART, ses.OCCUPATION_MART]
    gbr = [r for r in ctx.tables.read_table(ses.INDUSTRY_MART) if r["iso3"] == "GBR"]
    assert [r["hourly_earnings_eur"] for r in gbr] == [25.4, 12.3]
