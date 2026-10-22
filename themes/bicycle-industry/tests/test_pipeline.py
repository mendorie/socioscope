from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_bicycle_industry import (
    census,
    comtrade,
    cpi,
    merida,
    meti,
    prices,
    shakai,
    shimano,
    tw_mops,
)
from theme_bicycle_industry.pipeline import (
    BLS_TABLE,
    CENSUS_MART,
    CENSUS_TABLE,
    COMTRADE_MART,
    COMTRADE_TABLE,
    COMTRADE_TAIWAN_MART,
    COMTRADE_TAIWAN_TABLE,
    CPI_MART,
    CPI_TABLE,
    HICP_TABLE,
    MERIDA_MART,
    MERIDA_TABLE,
    METI_MART,
    METI_TABLE,
    MOPS_MART,
    MOPS_TABLE,
    PANEL_COLUMNS,
    PANEL_TABLE,
    PRICES_MART,
    SHAKAI_MART,
    SHAKAI_TABLE,
    SHIMANO_TABLE,
    THEME,
    build_panel,
)
from theme_bicycle_industry.wiring import PIPELINE

FIXTURES = Path(__file__).parent / "fixtures"
F2025 = (FIXTURES / "meti_h2daa2025k_sample.xlsx").read_bytes()
F2021 = (FIXTURES / "meti_h2daa2021k_sample.xlsx").read_bytes()
HTML_BLOCK = b"<!DOCTYPE html><html><body>403</body></html>"
COMTRADE = (FIXTURES / "comtrade_2023_sample.json").read_bytes()
HICP = (FIXTURES / "hicp_midx_sample.json").read_bytes()
BLS = (FIXTURES / "bls_serc01_sample.json").read_bytes()


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
    assert (
        sum("no fake response" in s and "h2daa" in s for s in result.skipped) == len(meti.YEARS) - 2
    )
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
    n_bls = len(prices.BLS_SERIES) * len(prices.BLS_RANGES)
    n_other = 1 + n_bls + len(shimano.DOCS) + len(cpi.FILES) + 1 + len(comtrade.ORIGIN_YEARS) + 1
    n_other += len(comtrade.TAIWAN_YEARS) + 1  # taiwan exports + 'mops: raw missing'
    n_other += len(merida.DOCS)
    assert len(result.skipped) == len(meti.YEARS) + len(comtrade.YEARS) + n_other
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
    for table in (
        METI_TABLE,
        COMTRADE_TABLE,
        HICP_TABLE,
        BLS_TABLE,
        SHIMANO_TABLE,
        CPI_TABLE,
        CENSUS_TABLE,
        SHAKAI_TABLE,
        COMTRADE_TAIWAN_TABLE,
        MOPS_TABLE,
        MERIDA_TABLE,
    ):
        assert f"{table}: staged table missing (run stage)" in result.skipped


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


# ---- Comtrade + price indices


def test_comtrade_and_prices_fetch_stage_mart_end_to_end() -> None:
    responses = {comtrade.url(2023): COMTRADE, prices.hicp_url(): HICP}
    responses[prices.bls_url("CUUR0000SERC01", 2016, 2025)] = BLS
    ctx = Context(
        fetcher=FakeFetcher(responses),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({comtrade.SOURCE, prices.HICP_SOURCE, prices.BLS_SOURCE}),
    )
    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert set(fetched.written) == {
        f"{THEME}/un_comtrade/comtrade_2023.json",
        f"{THEME}/eurostat_hicp/{prices.HICP_RAW_NAME}",
        f"{THEME}/bls_cpi/bls_CUUR0000SERC01_2016_2025.json",
    }
    licenses = {r.source: r.license for r in ctx.raw.records()}
    assert "UN Comtrade" in licenses["un_comtrade"] and "Eurostat" in licenses["eurostat_hicp"]
    assert "パブリックドメイン" in licenses["bls_cpi"]

    staged = PIPELINE.run(Stage.STAGE, ctx)
    assert set(staged.written) == {COMTRADE_TABLE, HICP_TABLE, BLS_TABLE}
    assert any("comtrade_2010.json: raw missing" in s for s in staged.skipped)
    assert all("h2daa" not in s for s in staged.skipped)  # meti is filtered out by --only

    marted = PIPELINE.run(Stage.MART, ctx)
    assert set(marted.written) == {COMTRADE_MART, PRICES_MART}
    trade = ctx.tables.read_table(COMTRADE_MART)
    assert {r["iso3"] for r in trade} == {"JPN", "DEU", "TWN"} and all(
        r["year"] == 2023 for r in trade
    )
    px = ctx.tables.read_table(PRICES_MART)
    assert {r["source"] for r in px} == {"eurostat_hicp", "bls_cpi"}


def test_comtrade_fetch_rejects_non_json_without_touching_raw() -> None:
    ctx = Context(
        fetcher=FakeFetcher({comtrade.url(2023): HTML_BLOCK}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({comtrade.SOURCE}),
    )
    result = PIPELINE.run(Stage.FETCH, ctx)
    assert result.written == () and ctx.raw.records() == []
    assert "comtrade_2023.json: non-JSON payload" in result.skipped


# ---- Shimano


def test_shimano_fetch_rejects_non_pdf_and_stage_reports_unreadable_raw() -> None:
    ctx = Context(
        fetcher=FakeFetcher({shimano.url(2024): HTML_BLOCK}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({shimano.SOURCE}),
    )
    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert fetched.written == () and ctx.raw.records() == []
    assert "shimano_yuho_fy2024_S100VGFP.pdf: non-PDF payload" in fetched.skipped
    assert sum("no fake response" in s for s in fetched.skipped) == len(shimano.DOCS) - 1

    ctx.raw.put(
        theme=THEME,
        source=shimano.SOURCE,
        name=shimano.raw_name(2024),
        url=shimano.url(2024),
        license=shimano.LICENSE,
        payload=HTML_BLOCK,
    )
    staged = PIPELINE.run(Stage.STAGE, ctx)
    assert staged.written == ()
    assert any("S100VGFP.pdf: layout not recognised" in s for s in staged.skipped)


# ---- CPI


def test_cpi_fetch_stage_mart_end_to_end_and_html_rejected() -> None:
    annual = (FIXTURES / "cpi_zni2025a.csv").read_bytes()
    ctx = Context(
        fetcher=FakeFetcher({cpi.url("annual"): annual, cpi.url("monthly"): HTML_BLOCK}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({cpi.SOURCE}),
    )
    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert fetched.written == (f"{THEME}/estat_cpi/cpi_2025base_annual.csv",)
    assert (
        "cpi_2025base_monthly.csv: HTML payload (wrong statInfId or fileKind?)" in fetched.skipped
    )
    assert "政府標準利用規約" in ctx.raw.records()[0].license
    staged = PIPELINE.run(Stage.STAGE, ctx)
    assert staged.written == (CPI_TABLE,)
    assert "cpi_2025base_monthly.csv: raw missing (run fetch)" in staged.skipped
    marted = PIPELINE.run(Stage.MART, ctx)
    assert CPI_MART in marted.written
    mart = ctx.tables.read_table(CPI_MART)
    assert {r["freq"] for r in mart} == {"annual"} and {r["iso3"] for r in mart} == {"JPN"}


# ---- census


def test_census_fetch_stage_mart_end_to_end() -> None:
    xlsx = (FIXTURES / "census_f1_001_sample.xlsx").read_bytes()
    ctx = Context(
        fetcher=FakeFetcher({census.URL: xlsx}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({census.SOURCE}),
    )
    assert PIPELINE.run(Stage.FETCH, ctx).written == (f"{THEME}/estat_census/{census.RAW_NAME}",)
    assert PIPELINE.run(Stage.STAGE, ctx).written == (CENSUS_TABLE,)
    assert CENSUS_MART in PIPELINE.run(Stage.MART, ctx).written
    mart = ctx.tables.read_table(CENSUS_MART)
    bike = {
        r["year"]: r["value"]
        for r in mart
        if r["industry"] == "bicycle_retail" and r["metric"] == "establishments"
    }
    assert bike[2021] == 9552.0


# ---- 社会生活基本調査


def test_shakai_fetch_stage_mart_end_to_end() -> None:
    xlsx = (FIXTURES / "shakai_jikei2_sample.xlsx").read_bytes()
    ctx = Context(
        fetcher=FakeFetcher({shakai.URL: xlsx}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({shakai.SOURCE}),
    )
    assert PIPELINE.run(Stage.FETCH, ctx).written == (f"{THEME}/estat_shakai/{shakai.RAW_NAME}",)
    assert PIPELINE.run(Stage.STAGE, ctx).written == (SHAKAI_TABLE,)
    assert SHAKAI_MART in PIPELINE.run(Stage.MART, ctx).written
    mart = ctx.tables.read_table(SHAKAI_MART)
    cyc = {
        r["year"]: r["rate_pct"]
        for r in mart
        if r["sport"] == "サイクリング" and r["sex"] == "total" and r["age"] == "total"
    }
    assert cyc[2021] == 8.2


# ---- Taiwan exports + MOPS


def test_mops_fetch_stage_mart_end_to_end_with_json_post() -> None:
    ok = (FIXTURES / "mops_9921_2019_06.json").read_bytes()
    empty = (FIXTURES / "mops_9921_2013_06_empty.json").read_bytes()
    responses = {
        FakeFetcher.post_key(tw_mops.URL, tw_mops.body("9921", 2019, 6)): ok,
        FakeFetcher.post_key(tw_mops.URL, tw_mops.body("9921", 2014, 1)): empty,
    }
    ctx = Context(
        fetcher=FakeFetcher(responses),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({tw_mops.SOURCE}),
    )
    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert set(fetched.written) == {
        f"{THEME}/tw_mops/mops_9921_2019_06.json",
        f"{THEME}/tw_mops/mops_9921_2014_01.json",
    }
    assert sum("no fake response" in s for s in fetched.skipped) == len(tw_mops.requests()) - 2
    staged = PIPELINE.run(Stage.STAGE, ctx)
    assert staged.written == (MOPS_TABLE,)
    assert any("1 company-months without data" in s for s in staged.skipped)
    assert MOPS_MART in PIPELINE.run(Stage.MART, ctx).written
    mart = ctx.tables.read_table(MOPS_MART)
    assert (
        len(mart) == 1 and mart[0]["period"] == "2019-06" and mart[0]["revenue_ntd_k"] == 4881737.0
    )


def test_taiwan_exports_stage_and_mart_add_other_destinations() -> None:
    import json

    doc = json.loads((FIXTURES / "comtrade_2023_sample.json").read_bytes())
    base = next(x for x in doc["data"] if x["reporterCode"] == 392 and x["cmdCode"] == "8712")
    rows = []
    for partner, qty, val in (
        (392, 63461.0, 51.2e6),
        (842, 457488.0, 458.8e6),
        (276, 50000.0, 60e6),
        (528, 90000.0, 140e6),
        (826, 70000.0, 80e6),
        (0, 1356048.0, 1390e6),
    ):
        rows.append(
            {
                **base,
                "reporterCode": 490,
                "flowCode": "X",
                "partnerCode": partner,
                "qty": qty,
                "primaryValue": val,
            }
        )
    payload = json.dumps({"data": rows}).encode()
    ctx = Context(
        fetcher=FakeFetcher({comtrade.taiwan_url(2023): payload}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({"un_comtrade_taiwan"}),
    )
    assert PIPELINE.run(Stage.FETCH, ctx).written == (
        f"{THEME}/un_comtrade_taiwan/comtrade_taiwan_exports_2023.json",
    )
    assert PIPELINE.run(Stage.STAGE, ctx).written == (COMTRADE_TAIWAN_TABLE,)
    assert COMTRADE_TAIWAN_MART in PIPELINE.run(Stage.MART, ctx).written
    mart = {r["partner"]: r for r in ctx.tables.read_table(COMTRADE_TAIWAN_MART)}
    assert set(mart) == {"JPN", "USA", "DEU", "NLD", "GBR", "WLD", "OTH"}
    assert mart["OTH"]["qty"] == pytest.approx(1356048.0 - (63461 + 457488 + 50000 + 90000 + 70000))
    assert mart["JPN"]["iso3"] == "TWN" and mart["JPN"]["flow"] == "export"


# ---- Merida


def test_merida_fetch_rejects_non_pdf_and_stage_reports_unreadable_raw() -> None:
    ctx = Context(
        fetcher=FakeFetcher({merida.url(2023): HTML_BLOCK}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({merida.SOURCE}),
    )
    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert (
        fetched.written == ()
        and "merida_consolidated_fy2023_q4.pdf: non-PDF payload" in fetched.skipped
    )
    ctx.raw.put(
        theme=THEME,
        source=merida.SOURCE,
        name=merida.raw_name(2023),
        url=merida.url(2023),
        license=merida.LICENSE,
        payload=HTML_BLOCK,
    )
    staged = PIPELINE.run(Stage.STAGE, ctx)
    assert staged.written == () and any("layout not recognised" in s for s in staged.skipped)
    assert (
        f"{MERIDA_TABLE}: staged table missing (run stage)" in PIPELINE.run(Stage.MART, ctx).skipped
    )
    assert MERIDA_MART not in PIPELINE.run(Stage.MART, ctx).written
