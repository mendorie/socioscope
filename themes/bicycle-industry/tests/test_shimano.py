import json
from pathlib import Path

import pytest

from theme_bicycle_industry import shimano

FIXTURES = Path(__file__).parent / "fixtures"
OLD = json.loads((FIXTURES / "shimano_S1004EF8_pages.json").read_text())  # FY2014, 和暦
NEW = json.loads((FIXTURES / "shimano_S100XQSE_pages.json").read_text())  # FY2025


def test_urls_and_names() -> None:
    assert (
        shimano.url(2024)
        == "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100VGFP.pdf"
    )
    assert shimano.raw_name(2024) == "shimano_yuho_fy2024_S100VGFP.pdf"
    assert len(shimano.DOCS) == 12 and min(shimano.DOCS) == 2014 and max(shimano.DOCS) == 2025


def test_old_format_filing_yields_both_years_segments_and_regions() -> None:
    parsed = shimano.parse_pages(OLD, fy=2014)
    rows = parsed.rows
    assert {r["fy"] for r in rows} == {2013, 2014}
    bike = {
        r["fy"]: r["value_mn_jpy"]
        for r in rows
        if r["key"] == "bicycle_components" and r["metric"] == "sales"
    }
    assert bike == {2013: 217263, 2014: 273955}
    profit = {
        r["fy"]: r["value_mn_jpy"]
        for r in rows
        if r["key"] == "bicycle_components" and r["metric"] == "profit"
    }
    assert profit == {2013: 39505, 2014: 62033}
    eu = {r["fy"]: r["value_mn_jpy"] for r in rows if r["key"] == "europe"}
    assert eu == {2013: 93357, 2014: 121584}
    jp2013 = next(r for r in rows if r["key"] == "japan" and r["fy"] == 2013)
    assert (
        jp2013["value_mn_jpy"] == 31545
        and jp2013["docid"] == "S1004EF8"
        and jp2013["doc_fy"] == 2014
    )
    # regions sum to the reported total
    for fy in (2013, 2014):
        parts = sum(
            r["value_mn_jpy"]
            for r in rows
            if r["table"] == "region" and r["key"] != "total" and r["fy"] == fy
        )
        total = next(r["value_mn_jpy"] for r in rows if r["key"] == "total" and r["fy"] == fy)
        assert abs(parts - total) <= 5  # 百万円単位の丸め
    assert parsed.skipped == []


def test_new_format_filing_handles_western_years_and_negative_segment_profit() -> None:
    rows = shimano.parse_pages(NEW, fy=2025).rows
    assert {r["fy"] for r in rows} == {2024, 2025}
    bike = {
        r["fy"]: r["value_mn_jpy"]
        for r in rows
        if r["key"] == "bicycle_components" and r["metric"] == "sales"
    }
    assert bike == {2024: 345553, 2025: 354972}
    other = {
        r["fy"]: r["value_mn_jpy"] for r in rows if r["key"] == "other" and r["metric"] == "profit"
    }
    assert other[2024] == -1  # 「△ 1」
    assert len(rows) == 24


def test_parse_pages_fails_closed() -> None:
    with pytest.raises(ValueError, match="not look like a Shimano"):
        shimano.parse_pages(["<html>403</html>"], fy=2024)
    with pytest.raises(ValueError, match="table not found"):
        shimano.parse_pages(
            ["シマノ 有価証券報告書 当連結会計年度（自 2024年１月１日 至 2024年12月31日）"], fy=2024
        )
    with pytest.raises(ValueError, match="no docID"):
        shimano.parse_pages(NEW, fy=2010)
    with pytest.raises(ValueError, match="not a readable PDF"):
        shimano.parse(b"<html>", fy=2024)


def test_build_mart_prefers_own_year_and_records_restatements() -> None:
    staged = shimano.parse_pages(OLD, fy=2014).rows + shimano.parse_pages(NEW, fy=2025).rows
    # pretend the FY2024 bicycle sales were restated in the FY2025 filing
    for r in staged:
        if r["fy"] == 2024 and r["key"] == "bicycle_components" and r["metric"] == "sales":
            r["value_mn_jpy"] = 345000
    own2024 = {
        "fy": 2024,
        "doc_fy": 2024,
        "docid": "S100VGFP",
        "table": "segment",
        "key": "bicycle_components",
        "metric": "sales",
        "value_mn_jpy": 345553,
        "source": shimano.SOURCE,
    }
    mart = shimano.build_mart([*staged, own2024])
    row = next(
        r
        for r in mart
        if r["fy"] == 2024 and r["key"] == "bicycle_components" and r["metric"] == "sales"
    )
    assert (
        row["value_mn_jpy"] == 345553
        and row["restated_next_year"] == 345000
        and row["docid"] == "S100VGFP"
    )
    # FY2013 only exists as a prior-year comparative → taken from the FY2014 filing
    row2013 = next(r for r in mart if r["fy"] == 2013 and r["key"] == "europe")
    assert row2013["docid"] == "S1004EF8" and row2013["restated_next_year"] is None
    keys = [tuple(r[c] for c in shimano.MART_KEY) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert all(r["iso3"] == "JPN" and r["company"] == "Shimano" for r in mart)
