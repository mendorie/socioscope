import json
from collections.abc import Callable

import pytest

from socioscope_core.core.pipeline import Context, Stage
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_parliament_size import ipu
from theme_parliament_size.pipeline import (
    IPU_CHAMBERS_TABLE,
    IPU_COUNTRIES_TABLE,
    IPU_MART,
    PANEL_COLUMNS,
    PANEL_TABLE,
    THEME,
    build_panel,
)
from theme_parliament_size.wiring import PIPELINE

PageBuilder = Callable[[str, list[dict[str, object]], bool], bytes]


def make_ctx(
    responses: dict[str, bytes] | None = None,
    sources: frozenset[str] | None = frozenset({ipu.SOURCE}),
) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=sources,
    )


def test_pipeline_is_registered_with_all_three_stages() -> None:
    assert PIPELINE.slug == THEME == "parliament-size"
    assert set(PIPELINE.stages) == {Stage.FETCH, Stage.STAGE, Stage.MART}


def test_theme_is_discoverable_through_the_entry_point() -> None:
    from socioscope_core.cli import discover_themes

    assert discover_themes()["parliament-size"] is PIPELINE


def test_fetch_follows_next_links_and_stores_each_page_with_the_license(
    chambers_page: bytes, countries_page: bytes, jp_lc: dict[str, object], make_page: PageBuilder
) -> None:
    responses = {
        ipu.url("chambers", 1): make_page("chambers", [jp_lc], True),
        ipu.url("chambers", 2): chambers_page,
        ipu.url("countries", 1): countries_page,
    }
    ctx = make_ctx(responses)
    result = PIPELINE.run(Stage.FETCH, ctx)

    assert result.written == (
        f"{THEME}/{ipu.SOURCE}/chambers_p1.json",
        f"{THEME}/{ipu.SOURCE}/chambers_p2.json",
        f"{THEME}/{ipu.SOURCE}/countries_p1.json",
    )
    assert result.skipped == ()
    recs = ctx.raw.records()
    assert [r.url for r in recs] == [
        ipu.url("chambers", 1),
        ipu.url("chambers", 2),
        ipu.url("countries", 1),
    ]
    assert all("CC BY-NC-SA 4.0" in r.license for r in recs)


def test_fetch_rejects_html_and_reports_unreachable_pages_without_touching_raw() -> None:
    ctx = make_ctx({ipu.url("chambers", 1): b"<!DOCTYPE html><html>403</html>"})
    result = PIPELINE.run(Stage.FETCH, ctx)

    assert result.written == ()
    assert result.skipped[0] == "chambers_p1.json: non-JSON payload"
    assert result.skipped[1].startswith("countries_p1.json: ")
    assert ctx.raw.records() == []


def test_fetch_honours_the_source_filter() -> None:
    ctx = Context(
        fetcher=FakeFetcher({}),
        raw=InMemoryRawStore(),
        tables=InMemoryTableStore(),
        sources=frozenset({"something_else"}),
    )
    result = PIPELINE.run(Stage.FETCH, ctx)
    assert result.written == () and result.skipped == ()


def test_stage_without_raw_writes_nothing_and_says_why() -> None:
    ctx = make_ctx()
    result = PIPELINE.run(Stage.STAGE, ctx)

    assert result.written == ()
    assert result.skipped == (
        "chambers_p1.json: raw missing (run fetch)",
        "countries_p1.json: raw missing (run fetch)",
    )
    assert ctx.tables.list_tables() == []


def test_stage_and_mart_end_to_end_from_fetched_pages(
    chambers_page: bytes, countries_page: bytes
) -> None:
    ctx = make_ctx({ipu.url("chambers", 1): chambers_page, ipu.url("countries", 1): countries_page})
    PIPELINE.run(Stage.FETCH, ctx)
    staged = PIPELINE.run(Stage.STAGE, ctx)
    assert staged.written == (IPU_CHAMBERS_TABLE, IPU_COUNTRIES_TABLE) and staged.skipped == ()
    assert {r["entity_id"] for r in ctx.tables.read_table(IPU_CHAMBERS_TABLE)} == {
        "JP-LC01",
        "JP-UC01",
    }

    marted = PIPELINE.run(Stage.MART, ctx)
    assert marted.written == (IPU_MART,) and marted.skipped == ()
    rows = ctx.tables.read_table(IPU_MART)
    assert [(r["iso3"], r["chamber_type"], r["statutory_seats"]) for r in rows] == [
        ("JPN", "lower", 465.0),
        ("JPN", "upper", 248.0),
    ]
    assert PANEL_TABLE not in ctx.tables.list_tables()


def test_stage_rejects_an_unreadable_page_without_writing_the_table(countries_page: bytes) -> None:
    ctx = make_ctx()
    bad = json.dumps({"data": [{"type": "Country", "id": "JP", "attributes": {}}]}).encode()
    ctx.raw.put(
        theme=THEME, source=ipu.SOURCE, name="chambers_p1.json", url="u", license="l", payload=bad
    )
    ctx.raw.put(
        theme=THEME,
        source=ipu.SOURCE,
        name="countries_p1.json",
        url="u",
        license="l",
        payload=countries_page,
    )
    result = PIPELINE.run(Stage.STAGE, ctx)

    assert result.written == (IPU_COUNTRIES_TABLE,)
    assert result.skipped == ("chambers_p1.json: chambers page 1: item is not of type Chamber",)


def test_mart_without_staged_tables_writes_nothing_and_says_why() -> None:
    ctx = make_ctx()
    result = PIPELINE.run(Stage.MART, ctx)
    assert result.written == ()
    assert result.skipped == (
        f"{IPU_MART}: staged missing ({IPU_CHAMBERS_TABLE}, {IPU_COUNTRIES_TABLE}; run stage)",
    )


def test_mart_reports_a_chamber_without_its_country_instead_of_writing(
    chambers_page: bytes, make_page: PageBuilder, make_country: Callable[..., dict[str, object]]
) -> None:
    ctx = make_ctx()
    ctx.tables.write_table(IPU_CHAMBERS_TABLE, ipu.parse(chambers_page, "chambers", 1))
    other = make_page("countries", [make_country("DE", "DEU", "Germany", 84000, 699, True)], False)
    ctx.tables.write_table(IPU_COUNTRIES_TABLE, ipu.parse(other, "countries", 1))
    result = PIPELINE.run(Stage.MART, ctx)
    assert result.written == ()
    assert result.skipped == (f"{IPU_MART}: chamber JP-LC01: country JP not in countries pages",)


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


def test_worldbank_gdp_is_wired_as_a_single_document_source() -> None:
    import json

    from theme_parliament_size import worldbank
    from theme_parliament_size.pipeline import WDI

    point = {
        "indicator": {"id": "NY.GDP.MKTP.CN", "value": "GDP (current LCU)"},
        "country": {"id": "JP", "value": "Japan"},
        "countryiso3code": "JPN",
        "date": "2024",
        "value": 634226000000000.0,
    }
    body = json.dumps([{"page": 1, "pages": 1, "total": 1}, [point]]).encode()
    ctx = make_ctx({worldbank.URL: body}, sources=frozenset({worldbank.SOURCE}))
    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert fetched.written == (f"{THEME}/{worldbank.SOURCE}/{worldbank.RAW_NAME}",)
    assert "CC BY 4.0" in ctx.raw.records()[0].license
    PIPELINE.run(Stage.STAGE, ctx)
    marted = PIPELINE.run(Stage.MART, ctx)
    assert marted.written == (WDI.mart,) and WDI.mart == "marts/wdi_gdp_lcu"
    assert ctx.tables.read_table(WDI.mart) == [
        {
            "iso3": "JPN",
            "year": 2024,
            "country": "Japan",
            "gdp_lcu": 634226000000000.0,
            "source": worldbank.SOURCE,
        }
    ]


def test_ukbills_and_fran_are_wired_end_to_end() -> None:
    import io
    import json
    import zipfile

    from theme_parliament_size import fran, ukbills
    from theme_parliament_size.pipeline import FRAN_MART, UKBILLS_MART

    def bill(bid: int, t: int, act: bool) -> dict[str, object]:
        stage = (
            {"stageId": 11, "stageSittings": [{"date": "2024-05-24T00:00:00"}]}
            if act
            else {"stageId": 7, "stageSittings": []}
        )
        return {
            "billId": bid,
            "shortTitle": "x",
            "billTypeId": t,
            "isAct": act,
            "currentStage": stage,
        }

    p1 = json.dumps({"items": [bill(1, 1, True)], "totalResults": 150}).encode()
    p2 = json.dumps({"items": [bill(2, 7, False)], "totalResults": 150}).encode()

    def fr_zip(uid: str) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(
                f"json/dossierParlementaire/{uid}.json",
                json.dumps(
                    {
                        "dossierParlementaire": {
                            "uid": uid,
                            "procedureParlementaire": {"libelle": "Proposition de loi ordinaire"},
                            "actesLegislatifs": {
                                "acteLegislatif": [
                                    {"codeActe": "AN1-DEPOT", "texteAssocie": "PIONANR5L17B0001"},
                                    {"codeActe": "PROM-PUB", "dateActe": "2026-04-21T00:00:00"},
                                ]
                            },
                        }
                    }
                ),
            )
        return buf.getvalue()

    responses = {
        ukbills.url(1): p1,
        ukbills.url(2): p2,
        fran.url(16): fr_zip("A"),
        fran.url(17): fr_zip("B"),
    }
    ctx = make_ctx(responses, sources=frozenset({ukbills.SOURCE, fran.SOURCE}))
    fetched = PIPELINE.run(Stage.FETCH, ctx)
    assert len(fetched.written) == 4 and fetched.skipped == ()
    PIPELINE.run(Stage.STAGE, ctx)
    marted = PIPELINE.run(Stage.MART, ctx)
    assert marted.written == (UKBILLS_MART, FRAN_MART)
    assert [r["bill_id"] for r in ctx.tables.read_table(UKBILLS_MART)] == [1]
    fr_rows = ctx.tables.read_table(FRAN_MART)
    assert [(r["uid"], r["legislature"], r["origin"]) for r in fr_rows] == [
        ("A", 16, "member"),
        ("B", 17, "member"),
    ]
