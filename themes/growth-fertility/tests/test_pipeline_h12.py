"""pipeline.py H12 blocks: 報告書グラフデータ CSV (12 figures -> ``marts/jp_marriage_attitudes``)
and NHK 日本人の意識 Q49 (1 JSON -> ``marts/jp_norms_nhk``). State tests with the in-memory fakes;
T06-01★ rides on the H9-JP loop and is covered by ``test_pipeline.py`` / ``test_ipss_h12.py``."""

from pathlib import Path

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_growth_fertility import ipss, nhk, pipeline
from theme_growth_fertility.wiring import PIPELINE

FIXTURES = Path(__file__).parent / "fixtures"
NHK_JSON = (FIXTURES / "nhk_q49.json").read_bytes()


def make_ctx(responses: dict[str, bytes]) -> Context:
    return Context(
        fetcher=FakeFetcher(responses), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def graph_responses() -> dict[str, bytes]:
    return {
        ipss.graph_url(f): (FIXTURES / f"ipss_graph_{f}.csv").read_bytes() for f in ipss.GRAPH_FILES
    }


# ---- H12-JP ----------------------------------------------------------------------------------


def test_fetch_h12_jp_stores_the_twelve_graph_csvs_under_ipss_with_pdl_license() -> None:
    ctx = make_ctx(graph_responses())
    result = PIPELINE.run(Stage.FETCH, ctx)
    expected = tuple(f"growth-fertility/ipss/{ipss.graph_raw_name(f)}" for f in ipss.GRAPH_FILES)
    assert tuple(w for w in result.written if "houkokuFigure" in w) == expected
    recs = [r for r in ctx.raw.records() if r.name.startswith("houkokuFigure")]
    assert len(recs) == len(ipss.GRAPH_FILES)
    assert all("PDL" in r.license and r.source == "ipss" for r in recs)
    assert {r.url for r in recs} == {ipss.graph_url(f) for f in ipss.GRAPH_FILES}
    assert not any(s.startswith("houkokuFigure") for s in result.skipped)
    result = PIPELINE.run(Stage.FETCH, make_ctx({}))
    assert sum(s.startswith("houkokuFigure") for s in result.skipped) == len(ipss.GRAPH_FILES)


def test_stage_h12_jp_writes_one_staged_table_per_figure_and_skips_bad_layouts() -> None:
    ctx = make_ctx(graph_responses())
    PIPELINE.run(Stage.FETCH, ctx)
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert pipeline.H12_JP_TABLES["1_1_1"] == "staged/ipss/graph_1_1_1"
    assert pipeline.H12_JP_TABLES["12_1_2"] == "staged/ipss/graph_12_1_2"
    assert tuple(w for w in result.written if "/graph_" in w) == tuple(
        pipeline.H12_JP_TABLES.values()
    )
    rows = ctx.tables.read_table("staged/ipss/graph_1_1_1")
    assert len(rows) == 12 and all(r["source"] == "ipss_jnfs16_graph" for r in rows)
    assert rows[0]["survey_year"] == 1982 and rows[0]["share_pct"] == 95.9
    assert not any(s.startswith("houkokuFigure") for s in result.skipped)
    # one figure with the wrong header is skipped, the others are still staged
    responses = graph_responses()
    responses[ipss.graph_url("1_1_1")] = responses[ipss.graph_url("1_1_2")]
    ctx = make_ctx(responses)
    PIPELINE.run(Stage.FETCH, ctx)
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert "staged/ipss/graph_1_1_1" not in result.written
    assert "staged/ipss/graph_1_1_2" in result.written
    assert any(
        s.startswith("houkokuFigure1_1_1.csv: layout not recognised (") for s in result.skipped
    )
    result = PIPELINE.run(Stage.STAGE, make_ctx({}))
    assert sum(s.startswith("houkokuFigure") and "raw missing" in s for s in result.skipped) == len(
        ipss.GRAPH_FILES
    )


def test_mart_h12_jp_combines_the_staged_figures_into_jp_marriage_attitudes() -> None:
    ctx = make_ctx(graph_responses())
    PIPELINE.run(Stage.FETCH, ctx)
    PIPELINE.run(Stage.STAGE, ctx)
    result = PIPELINE.run(Stage.MART, ctx)
    assert pipeline.H12_JP_MART == "marts/jp_marriage_attitudes"
    assert pipeline.H12_JP_MART in result.written
    mart = ctx.tables.read_table(pipeline.H12_JP_MART)
    assert len(mart) == 12 * len(ipss.GRAPH_FILES)
    assert mart[0]["figure"] == "1_1_1" and mart[-1]["figure"] == "12_1_2"
    keys = [tuple(r[c] for c in ipss.ATTITUDES_KEY) for r in mart]
    assert len(set(keys)) == len(keys)
    # only the staged figures are combined; nothing staged -> skipped
    responses = graph_responses()
    del responses[ipss.graph_url("5_2_2")]
    ctx = make_ctx(responses)
    PIPELINE.run(Stage.FETCH, ctx)
    PIPELINE.run(Stage.STAGE, ctx)
    result = PIPELINE.run(Stage.MART, ctx)
    mart = ctx.tables.read_table(pipeline.H12_JP_MART)
    assert len(mart) == 12 * (len(ipss.GRAPH_FILES) - 1)
    assert any(
        s.startswith("staged/ipss/graph_5_2_2: staged table missing") for s in result.skipped
    )
    result = PIPELINE.run(Stage.MART, make_ctx({}))
    assert pipeline.H12_JP_MART not in result.written
    assert any(s.startswith("marts/jp_marriage_attitudes: no staged") for s in result.skipped)


# ---- H12-NHK ---------------------------------------------------------------------------------


def test_fetch_h12_nhk_stores_the_json_with_the_non_commercial_license() -> None:
    ctx = make_ctx({nhk.URL: NHK_JSON})
    result = PIPELINE.run(Stage.FETCH, ctx)
    assert "growth-fertility/nhk_nihonjin_ishiki/q49.json" in result.written
    recs = [r for r in ctx.raw.records() if r.source == nhk.SOURCE]
    assert len(recs) == 1 and recs[0].url == nhk.URL and recs[0].license == nhk.LICENSE
    assert ctx.raw.get(theme="growth-fertility", source=nhk.SOURCE, name="q49.json") == NHK_JSON
    result = PIPELINE.run(Stage.FETCH, make_ctx({}))
    assert any(s.startswith("q49.json: ") for s in result.skipped)


def test_stage_and_mart_h12_nhk_write_the_staged_table_and_jp_norms_nhk() -> None:
    ctx = make_ctx({nhk.URL: NHK_JSON})
    PIPELINE.run(Stage.FETCH, ctx)
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert pipeline.NHK_TABLE == "staged/nhk/q49"
    assert pipeline.NHK_TABLE in result.written
    staged = ctx.tables.read_table(pipeline.NHK_TABLE)
    assert len(staged) == 40 and all(r["source"] == "nhk_nihonjin_ishiki" for r in staged)
    result = PIPELINE.run(Stage.MART, ctx)
    assert pipeline.NHK_MART == "marts/jp_norms_nhk"
    assert pipeline.NHK_MART in result.written
    mart = ctx.tables.read_table(pipeline.NHK_MART)
    assert len(mart) == 40
    assert mart[0]["year"] == 1993 and mart[0]["answer_code"] == "01" and mart[0]["group"] == "all"
    assert mart[0]["ratio_pct"] == 45.0
    # bad payload -> skipped with a reason, nothing written
    ctx = make_ctx({nhk.URL: b'{"q50": []}'})
    PIPELINE.run(Stage.FETCH, ctx)
    result = PIPELINE.run(Stage.STAGE, ctx)
    assert pipeline.NHK_TABLE not in result.written
    assert any(s.startswith("q49.json: layout not recognised (") for s in result.skipped)
    result = PIPELINE.run(Stage.STAGE, make_ctx({}))
    assert any(s.startswith("q49.json: raw missing") for s in result.skipped)
    result = PIPELINE.run(Stage.MART, make_ctx({}))
    assert pipeline.NHK_MART not in result.written
    assert any(s.startswith("staged/nhk/q49: staged table missing") for s in result.skipped)
