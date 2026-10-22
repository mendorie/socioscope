from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_bicycle_industry import meti
from theme_bicycle_industry.pipeline import (
    METI_MART,
    METI_TABLE,
    PANEL_COLUMNS,
    PANEL_TABLE,
    THEME,
    build_panel,
)
from theme_bicycle_industry.wiring import PIPELINE

FIXTURES = Path(__file__).parent / "fixtures"
F2025 = (FIXTURES / "meti_h2daa2025k_sample.xlsx").read_bytes()
F2021 = (FIXTURES / "meti_h2daa2021k_sample.xlsx").read_bytes()
HTML_BLOCK = b"<!DOCTYPE html><html><body>403</body></html>"


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def test_pipeline_is_registered_with_all_three_stages() -> None:
    assert PIPELINE.slug == "bicycle-industry"
    assert set(PIPELINE.stages) == {Stage.FETCH, Stage.STAGE, Stage.MART}


def test_fetch_stores_each_available_annual_xlsx_with_license_and_reports_the_rest() -> None:
    ctx = make_ctx({meti.annual_url(2025): F2025, meti.annual_url(2024): HTML_BLOCK})
    result = PIPELINE.run(Stage.FETCH, ctx)

    assert result.written == (f"{THEME}/meti_seidou/h2daa2025k.xlsx",)
    assert "h2daa2024k.xlsx: non-xlsx payload (blocked or moved?)" in result.skipped
    assert sum("no fake response" in s for s in result.skipped) == len(meti.YEARS) - 2
    recs = ctx.raw.records()
    assert [r.name for r in recs] == ["h2daa2025k.xlsx"]
    assert "政府標準利用規約" in recs[0].license and recs[0].url == meti.annual_url(2025)


def test_fetch_honours_the_source_filter() -> None:
    ctx = Context(
        fetcher=FakeFetcher({meti.annual_url(2025): F2025}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({"something_else"}),
    )
    result = PIPELINE.run(Stage.FETCH, ctx)
    assert result.written == () and ctx.raw.records() == []


def test_stage_without_raw_writes_nothing_and_says_why() -> None:
    ctx = make_ctx()
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert result.written == ()
    assert all("raw missing (run fetch)" in s for s in result.skipped)
    assert len(result.skipped) == len(meti.YEARS)
    assert ctx.tables.list_tables() == []


def test_stage_parses_every_fetched_year_into_one_long_table() -> None:
    ctx = make_ctx()
    for year, payload in ((2021, F2021), (2025, F2025)):
        ctx.raw.put(
            theme=THEME,
            source=meti.SOURCE,
            name=meti.raw_name(year),
            url=meti.annual_url(year),
            license=meti.LICENSE,
            payload=payload,
        )
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert result.written == (METI_TABLE,)
    rows = ctx.tables.read_table(METI_TABLE)
    assert {r["report_year"] for r in rows} == {2021, 2025}
    assert {r["industry"] for r in rows} == {"bicycle", "motor_vehicle"}
    assert any("unmapped product" in s for s in result.skipped)


def test_stage_rejects_an_unrecognised_layout_without_writing() -> None:
    ctx = make_ctx()
    ctx.raw.put(
        theme=THEME,
        source=meti.SOURCE,
        name=meti.raw_name(2025),
        url=meti.annual_url(2025),
        license=meti.LICENSE,
        payload=HTML_BLOCK,
    )
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert result.written == ()
    assert any("layout not recognised" in s for s in result.skipped)
    assert ctx.tables.list_tables() == []


def test_mart_builds_meti_production_and_no_empty_panel() -> None:
    ctx = make_ctx()
    ctx.tables.write_table(METI_TABLE, meti.parse(F2025, report_year=2025).rows)
    result = PIPELINE.run(Stage.MART, ctx)
    assert result.written == (METI_MART,)
    mart = ctx.tables.read_table(METI_MART)
    assert mart and all(r["iso3"] == "JPN" for r in mart)
    assert any(r["period_type"] == "cy_from_months" for r in mart)
    # a zero-row panel is never written (DuckDB cannot read a column-less Parquet)
    assert PANEL_TABLE not in ctx.tables.list_tables()


def test_mart_without_staged_meti_writes_nothing_and_says_why() -> None:
    ctx = make_ctx()
    result = PIPELINE.run(Stage.MART, ctx)
    assert result.written == ()
    assert f"{METI_TABLE}: staged table missing (run stage)" in result.skipped


def test_build_panel_sorts_by_key_and_keeps_only_panel_columns() -> None:
    rows: list[dict[str, object]] = [
        {
            "iso3": "JPN",
            "year": 2024,
            "product": "e_assist",
            "metric": "units",
            "value": 2.0,
            "source": "s",
            "extra": "dropped",
        },
        {
            "iso3": "JPN",
            "year": 2023,
            "product": "e_assist",
            "metric": "units",
            "value": 1.0,
            "source": "s",
        },
    ]
    out = build_panel(rows)
    assert [r["year"] for r in out] == [2023, 2024]
    assert all(tuple(r) == PANEL_COLUMNS for r in out)


def test_build_panel_rejects_duplicate_keys() -> None:
    row: dict[str, object] = {
        "iso3": "JPN",
        "year": 2024,
        "product": "e_assist",
        "metric": "units",
        "value": 1.0,
        "source": "s",
    }
    with pytest.raises(ValueError, match="duplicate panel key"):
        build_panel([row, dict(row)])
