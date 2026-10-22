import pytest

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_bicycle_industry.pipeline import PANEL_COLUMNS, PANEL_TABLE, build_panel
from theme_bicycle_industry.wiring import PIPELINE


def make_ctx() -> Context:
    return Context(fetcher=FakeFetcher({}), raw=InMemoryRawStore(), tables=InMemoryTableStore())


def test_pipeline_is_registered_with_all_three_stages() -> None:
    assert PIPELINE.slug == "bicycle-industry"
    assert set(PIPELINE.stages) == {Stage.FETCH, Stage.STAGE, Stage.MART}


def test_fetch_and_stage_touch_nothing_while_no_source_is_wired() -> None:
    ctx = make_ctx()
    for stage in (Stage.FETCH, Stage.STAGE):
        result = PIPELINE.run(stage, ctx)
        assert result.written == () and result.skipped == ()
        assert any("no sources registered" in n for n in result.notes)
    assert ctx.raw.records() == [] and ctx.tables.list_tables() == []


def test_mart_writes_an_empty_panel_table() -> None:
    ctx = make_ctx()
    result = PIPELINE.run(Stage.MART, ctx)
    assert result.written == (PANEL_TABLE,)
    assert ctx.tables.read_table(PANEL_TABLE) == []


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
