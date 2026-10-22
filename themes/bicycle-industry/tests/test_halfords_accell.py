import json
from pathlib import Path

import pytest

from theme_bicycle_industry import accell, halfords

FIXTURES = Path(__file__).parent / "fixtures"
HAL = json.loads((FIXTURES / "halfords_pages.json").read_text())
ACC = json.loads((FIXTURES / "accell_pages.json").read_text())


def _vals(rows: list[dict[str, object]]) -> dict[str, object]:
    return {str(r["metric"]): r["value"] for r in rows}


def test_halfords_urls() -> None:
    assert halfords.url(2015).startswith("https://www.halfordscompany.com/media/")
    assert halfords.raw_name(2026) == "halfords_prelims_fy2026.pdf"


def test_halfords_mix_layouts_and_week53() -> None:
    v15 = _vals(halfords.parse_pages(HAL["2015"], 2015).rows)  # 53 週: 52 週列、'Cycling 34.4 32.8'
    assert v15 == {"retail_revenue": 857.9, "cycling_mix": 34.4, "cycling_revenue": 295.1}
    v17 = _vals(halfords.parse_pages(HAL["2017"], 2017).rows)  # 'Cycling 38.0 34.3 +5.1'
    assert v17["cycling_mix"] == 38.0 and v17["cycling_revenue"] == pytest.approx(356.6)
    v20 = _vals(halfords.parse_pages(HAL["2020"], 2020).rows)  # 53 週、'Cycling +2.3 41.6 39.6'
    assert v20["retail_revenue"] == 950.6 and v20["cycling_mix"] == 41.6
    v22 = _vals(halfords.parse_pages(HAL["2022"], 2022).rows)  # 'Cycling +18.0 40.6 53.9 41.6'
    assert v22["cycling_mix"] == 40.6 and v22["retail_revenue"] == 1001.6
    v23 = _vals(
        halfords.parse_pages(HAL["2023"], 2023).rows
    )  # LFL 2 列 '-10.9% +1.3% 38.0 40.6 41.6'
    assert v23["cycling_mix"] == 38.0
    assert all(
        r["derived"] == (r["metric"] == "cycling_revenue")
        for r in halfords.parse_pages(HAL["2023"], 2023).rows
    )


def test_halfords_disclosed_cycling_from_fy2025() -> None:
    rows = halfords.parse_pages(HAL["2026"], 2026).rows
    v = _vals(rows)
    assert v == {"retail_revenue": 1039.3, "cycling_revenue": 378.9}  # 52 週列、開示 £m
    assert all(r["derived"] is False for r in rows)


def test_halfords_fails_closed() -> None:
    with pytest.raises(ValueError, match="not look like"):
        halfords.parse_pages(["<html>"], 2020)
    with pytest.raises(ValueError, match="Cycling mix line not found"):
        halfords.parse_pages(["Halfords\nRetail 950.6 977.2 -2.7%\n"], 2019)
    with pytest.raises(ValueError, match="no document"):
        halfords.parse_pages(HAL["2020"], 2014)
    with pytest.raises(ValueError, match="not a readable PDF"):
        halfords.parse(b"nope", 2020)


def test_halfords_build_mart_sorted_unique() -> None:
    staged = (
        halfords.parse_pages(HAL["2020"], 2020).rows + halfords.parse_pages(HAL["2026"], 2026).rows
    )
    mart = halfords.build_mart(staged)
    assert [r["fy"] for r in mart] == [2020, 2020, 2020, 2026, 2026]
    assert all(r["iso3"] == "GBR" for r in mart)
    with pytest.raises(ValueError, match="duplicate"):
        halfords.build_mart(staged + staged[:1])


def test_accell_tables_and_restatement() -> None:
    assert accell.url(2021).startswith("https://web.archive.org/web/20240104114552id_/https://")
    r17 = accell.parse_pages(ACC["2017"], 2017).rows
    assert {r["year"]: r["value_eur_m"] for r in r17}[2010] == 577.2 and len(r17) == 8
    r21 = accell.parse_pages(ACC["2021"], 2021).rows
    assert [r["value_eur_m"] for r in r21] == [1069.0, 1094.0, 1111.0, 1296.0, 1377.0]
    mart = {r["year"]: r for r in accell.build_mart(r17 + r21)}
    assert (
        len(mart) == 12
        and mart[2017]["value_eur_m"] == 1068.5
        and mart[2017]["restated_later"] == 1069.0
    )
    assert mart[2021]["restated_later"] is None and mart[2021]["iso3"] == "NLD"
    with pytest.raises(ValueError, match="table not found"):
        accell.parse_pages(["Accell Group"], 2017)
    with pytest.raises(ValueError, match="no document"):
        accell.parse_pages(ACC["2017"], 2019)
