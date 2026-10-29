import pytest

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages.pipeline import (
    PANEL_COLUMNS,
    PANEL_TABLE,
    THEME,
    build_panel,
)
from theme_essential_work_wages.wiring import PIPELINE


def make_ctx() -> Context:
    return Context(fetcher=FakeFetcher({}), raw=InMemoryRawStore(), tables=InMemoryTableStore())


def test_pipeline_is_registered_with_all_three_stages() -> None:
    assert PIPELINE.slug == THEME == "essential-work-wages"
    assert set(PIPELINE.stages) == {Stage.FETCH, Stage.STAGE, Stage.MART}


def test_theme_is_discoverable_through_the_entry_point() -> None:
    from socioscope_core.cli import discover_themes

    assert discover_themes()["essential-work-wages"] is PIPELINE


def test_fetch_and_stage_touch_nothing_while_no_source_is_wired() -> None:
    ctx = make_ctx()
    for st in (Stage.FETCH, Stage.STAGE):
        result = PIPELINE.run(st, ctx)
        assert result.written == ()
        assert result.skipped == ()
        assert result.notes == (f"{THEME}: no source wired yet",)
    assert ctx.raw.records() == []
    assert ctx.tables.list_tables() == []


def test_mart_writes_an_empty_panel_from_empty_input() -> None:
    ctx = make_ctx()
    result = PIPELINE.run(Stage.MART, ctx)
    assert result.written == (PANEL_TABLE,)
    assert ctx.tables.read_table(PANEL_TABLE) == []


def test_build_panel_keeps_only_panel_columns_and_sorts_by_key() -> None:
    rows: list[dict[str, object]] = [
        {
            "iso3": "JPN",
            "year": 2024,
            "occupation": "福祉施設介護員",
            "classification": "jp_bsws2020",
            "metric": "wage_median",
            "value": 251.4,
            "source": "estat_bsws",
            "extra": "dropped",
        },
        {
            "iso3": "JPN",
            "year": 2023,
            "occupation": "福祉施設介護員",
            "classification": "jp_bsws2020",
            "metric": "wage_median",
            "value": 247.2,
            "source": "estat_bsws",
        },
    ]
    out = build_panel(rows)
    assert [tuple(r) for r in out] == [PANEL_COLUMNS, PANEL_COLUMNS]
    assert [r["year"] for r in out] == [2023, 2024]


def test_build_panel_rejects_duplicate_keys() -> None:
    row: dict[str, object] = {
        "iso3": "USA",
        "year": 2024,
        "occupation": "15-1252",
        "classification": "us_soc2018",
        "metric": "wage_median",
        "value": 133080.0,
        "source": "bls_oews",
    }
    with pytest.raises(ValueError, match="duplicate panel key"):
        build_panel([row, dict(row)])
