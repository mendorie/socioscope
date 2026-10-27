import pytest

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_parliament_size.pipeline import PANEL_COLUMNS, PANEL_TABLE, THEME, build_panel
from theme_parliament_size.wiring import PIPELINE


def make_ctx() -> Context:
    return Context(fetcher=FakeFetcher({}), raw=InMemoryRawStore(), tables=InMemoryTableStore())


def test_pipeline_is_registered_with_all_three_stages() -> None:
    assert PIPELINE.slug == THEME == "parliament-size"
    assert set(PIPELINE.stages) == {Stage.FETCH, Stage.STAGE, Stage.MART}


def test_theme_is_discoverable_through_the_entry_point() -> None:
    from socioscope_core.cli import discover_themes

    assert discover_themes()["parliament-size"] is PIPELINE


@pytest.mark.parametrize("stage", [Stage.FETCH, Stage.STAGE, Stage.MART])
def test_stages_without_a_source_write_nothing_and_say_why(stage: Stage) -> None:
    ctx = make_ctx()
    result = PIPELINE.run(stage, ctx)

    assert result.stage == stage
    assert result.written == () and result.skipped == ()
    assert any("no data source adopted" in n for n in result.notes)
    assert ctx.raw.records() == [] and ctx.tables.list_tables() == []
    assert PANEL_TABLE not in ctx.tables.list_tables()


def test_build_panel_sorts_by_key_and_keeps_only_panel_columns() -> None:
    rows: list[dict[str, object]] = [
        {
            "iso3": "JPN",
            "year": 2024,
            "unit": "lower_house",
            "metric": "seats",
            "value": 465,
            "source": "ipu",
            "extra": "dropped",
        },
        {
            "iso3": "DEU",
            "year": 2025,
            "unit": "lower_house",
            "metric": "seats",
            "value": 630,
            "source": "ipu",
        },
    ]
    out = build_panel(rows)

    assert [tuple(r) for r in out] == [PANEL_COLUMNS, PANEL_COLUMNS]
    assert [r["iso3"] for r in out] == ["DEU", "JPN"]


def test_build_panel_rejects_duplicate_keys() -> None:
    row: dict[str, object] = {
        "iso3": "JPN",
        "year": 2024,
        "unit": "lower_house",
        "metric": "seats",
        "value": 465,
        "source": "ipu",
    }
    with pytest.raises(ValueError, match="duplicate panel key"):
        build_panel([row, dict(row, value=466)])
