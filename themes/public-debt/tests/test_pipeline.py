import io

import pytest

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_public_debt import imf, jst
from theme_public_debt.pipeline import PANEL_COLUMNS, PANEL_TABLE, THEME, build_panel
from theme_public_debt.wiring import PIPELINE

from .test_jst import HEADER, _many_countries, _row


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def jst_xlsx(rows: list[list[object]]) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Data"
    ws.append(HEADER)
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_pipeline_is_registered_with_all_three_stages() -> None:
    assert PIPELINE.slug == THEME == "public-debt"
    assert set(PIPELINE.stages) == {Stage.FETCH, Stage.STAGE, Stage.MART}


def test_theme_is_discoverable_through_the_entry_point() -> None:
    from socioscope_core.cli import discover_themes

    assert discover_themes()["public-debt"] is PIPELINE


def test_fetch_stores_jst_xlsx_with_provenance() -> None:
    payload = jst_xlsx(_many_countries())
    ctx = make_ctx({jst.URL: payload})

    result = PIPELINE.run(Stage.FETCH, ctx)

    assert result.written == ("public-debt/jst/JSTdatasetR6.xlsx",)
    imf_urls = tuple(imf.url(c) for c in imf.INDICATORS)
    assert sum(n.endswith(imf_urls) for n in result.skipped) == len(imf.INDICATORS)
    assert any(n.startswith("eo_interest") for n in result.skipped)
    assert any(n.startswith("holdings01.pdf") for n in result.skipped)
    (rec,) = ctx.raw.records()
    assert rec.url == jst.URL and "CC BY-NC-SA" in rec.license and rec.theme == THEME
    assert ctx.raw.get(theme=THEME, source=jst.SOURCE, name=jst.RAW_NAME) == payload


def test_fetch_skips_when_source_unreachable_or_not_xlsx() -> None:
    ctx = make_ctx()
    assert PIPELINE.run(Stage.FETCH, ctx).skipped[0].startswith("JSTdatasetR6.xlsx: no fake")
    assert ctx.raw.records() == []

    ctx = make_ctx({jst.URL: b"<html>blocked</html>"})
    assert PIPELINE.run(Stage.FETCH, ctx).skipped[0] == "JSTdatasetR6.xlsx: non-xlsx payload"
    assert ctx.raw.records() == []


def imf_json(code: str, values: dict[str, dict[str, float]]) -> bytes:
    import json

    return json.dumps({"values": {code: values}, "api": {"version": "1"}}).encode()


def test_imf_fetch_stage_mart_are_independent_per_indicator() -> None:
    responses = {
        imf.url("GGXWDG_NGDP"): imf_json("GGXWDG_NGDP", {"JPN": {"2019": 236.1, "2030": 1.0}}),
        imf.url("GGXWDN_G01_GDP_PT"): imf_json("GGXWDN_G01_GDP_PT", {"JPN": {"2019": 150.0}}),
        imf.url("GG_DEBT_GDP"): b"<html>blocked</html>",
    }
    ctx = make_ctx(responses)

    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert "public-debt/imf/GGXWDG_NGDP.json" in fetched.written
    assert "GG_DEBT_GDP.json: non-JSON payload" in fetched.skipped
    assert len(ctx.raw.records()) == 2

    staged = PIPELINE.run(Stage.STAGE, ctx)
    assert imf.STAGED_TABLE in staged.written
    assert any(s.startswith("CG_DEBT_GDP.json: raw missing") for s in staged.skipped)

    marted = PIPELINE.run(Stage.MART, ctx)
    assert marted.written == (imf.MART_TABLE, PANEL_TABLE)
    panel = ctx.tables.read_table(PANEL_TABLE)
    got = {(r["unit"], r["metric"], r["source"]): r["value"] for r in panel}
    assert got[("general_gov_gross", "debt_gdp", "imf_weo")] == 236.1
    assert got[("general_gov_net", "debt_gdp", "imf_fm")] == 150.0
    assert all(r["year"] == 2019 for r in panel)


@pytest.mark.parametrize("stage", [Stage.STAGE, Stage.MART])
def test_stage_and_mart_without_raw_write_nothing_and_say_why(stage: Stage) -> None:
    ctx = make_ctx()
    result = PIPELINE.run(stage, ctx)

    assert result.stage == stage and result.written == ()
    assert any("missing" in n for n in result.skipped)
    assert ctx.tables.list_tables() == []


def test_fetch_stage_mart_end_to_end_builds_the_panel() -> None:
    rows = [*_many_countries(), _row("JPN", 1990), _row("JPN", 1991, debtgdp=0.6, gdp=1050.0)]
    ctx = make_ctx({jst.URL: jst_xlsx(rows)})

    PIPELINE.run(Stage.FETCH, ctx)
    staged = PIPELINE.run(Stage.STAGE, ctx)
    marted = PIPELINE.run(Stage.MART, ctx)

    assert staged.written == (jst.STAGED_TABLE,)
    assert marted.written == (jst.MART_TABLE, PANEL_TABLE)  # imf/oecd skipped (no raw)
    panel = ctx.tables.read_table(PANEL_TABLE)
    assert [tuple(r) for r in panel[:1]] == [PANEL_COLUMNS]
    jp = {(r["year"], r["unit"], r["metric"]): r["value"] for r in panel if r["iso3"] == "JPN"}
    assert jp[(1991, "general_gov_gross", "debt_gdp")] == pytest.approx(60.0)
    assert jp[(1991, "macro", "ngdp_growth")] == pytest.approx(5.0)
    assert all(r["source"] == "jst" for r in panel)


def test_stage_reports_a_broken_raw_instead_of_writing() -> None:
    ctx = make_ctx({jst.URL: b"PK not really a workbook"})
    PIPELINE.run(Stage.FETCH, ctx)
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert result.written == () and "not a readable xlsx" in result.skipped[0]


def test_build_panel_sorts_by_key_and_keeps_only_panel_columns() -> None:
    rows: list[dict[str, object]] = [
        {
            "iso3": "JPN",
            "year": 2020,
            "unit": "general_gov_gross",
            "metric": "debt_gdp",
            "value": 258.7,
            "source": "jst",
            "extra": "dropped",
        },
        {
            "iso3": "DEU",
            "year": 2020,
            "unit": "general_gov_gross",
            "metric": "debt_gdp",
            "value": 68.7,
            "source": "jst",
        },
    ]
    out = build_panel(rows)

    assert [tuple(r) for r in out] == [PANEL_COLUMNS, PANEL_COLUMNS]
    assert [r["iso3"] for r in out] == ["DEU", "JPN"]


def test_build_panel_keeps_different_debt_definitions_as_separate_rows() -> None:
    gross: dict[str, object] = {
        "iso3": "JPN",
        "year": 2020,
        "unit": "general_gov_gross",
        "metric": "debt_gdp",
        "value": 258.7,
        "source": "imf_gdd",
    }
    net = dict(gross, unit="general_gov_net", value=162.0)
    out = build_panel([gross, net])

    assert [(r["unit"], r["value"]) for r in out] == [
        ("general_gov_gross", 258.7),
        ("general_gov_net", 162.0),
    ]


def test_build_panel_rejects_duplicate_keys() -> None:
    row: dict[str, object] = {
        "iso3": "JPN",
        "year": 2020,
        "unit": "general_gov_gross",
        "metric": "debt_gdp",
        "value": 258.7,
        "source": "jst",
    }
    with pytest.raises(ValueError, match="duplicate panel key"):
        build_panel([row, dict(row, value=259.0)])
