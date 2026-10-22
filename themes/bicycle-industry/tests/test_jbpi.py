import json
from pathlib import Path

import pytest

from theme_bicycle_industry import jbpi

FIXTURES = Path(__file__).parent / "fixtures"
DOM = json.loads((FIXTURES / "jbpi_domestic_pages.json").read_text())
POS = json.loads((FIXTURES / "jbpi_pos_pages.json").read_text())


def test_urls_are_percent_encoded() -> None:
    assert "%E5%9B%BD%E5%86%85%E5%90%91" in jbpi.domestic_url(2025)  # 国内向
    assert jbpi.domestic_raw_name(2025) == "jbpi_domestic_2023_2025_dec.pdf"
    assert jbpi.pos_url(2025).startswith("https://jbpi.or.jp/wp-content/uploads/2026/04/POS")


def test_domestic_rows_by_order_and_years() -> None:
    rows = jbpi.parse_domestic_pages(DOM["2025"], 2025).rows
    assert len(rows) == 30 and {r["year"] for r in rows} == {2023, 2024, 2025}
    v = {(r["year"], r["category"], r["flow"]): (r["qty"], r["value_k_jpy"]) for r in rows}
    assert v[(2025, "eassist", "production")] == (585_074, 63_410_283)
    assert v[(2025, "other_sports_geared", "import")] == (1_732_111, 33_629_026)
    assert v[(2025, "mtb_cross", "import")] == (51_365, 1_073_077)
    assert v[(2023, "light", "production")] == (84_950, 1_164_566)
    assert v[(2023, "light", "import")] == (1_065_294, 15_851_864)
    assert v[(2025, "other", "production")] == (46_059, 1_122_669)


def test_domestic_fails_closed() -> None:
    with pytest.raises(ValueError, match="year header"):
        jbpi.parse_domestic_pages(DOM["2025"], 2024)
    with pytest.raises(ValueError, match="not look like"):
        jbpi.parse_domestic_pages(["<html>"], 2025)
    broken = [DOM["2025"][0].replace("電動アシスト車 577,729", "電動アシスト車 1")]
    with pytest.raises(ValueError, match="production total"):
        jbpi.parse_domestic_pages(broken, 2025)
    with pytest.raises(ValueError, match="no document"):
        jbpi.parse_domestic_pages(DOM["2025"], 2019)


def test_domestic_mart_prefers_newer_edition_and_prices() -> None:
    staged = (
        jbpi.parse_domestic_pages(DOM["2024"], 2024).rows
        + jbpi.parse_domestic_pages(DOM["2025"], 2025).rows
    )
    bumped = [dict(r) for r in staged]
    for r in bumped:
        if r["edition"] == 2024 and r["year"] == 2024 and r["category"] == "mini":
            r["qty"] = 1  # pretend the older edition differed
    mart = {(r["year"], r["category"], r["flow"]): r for r in jbpi.build_domestic_mart(bumped)}
    assert len(mart) == 40  # 2022–2025 × 10
    m = mart[(2024, "mini", "import")]
    assert m["edition"] == 2025 and m["qty"] == 346_637 and m["restated_from"] == 1
    assert mart[(2025, "eassist", "production")]["restated_from"] is None
    assert mart[(2025, "eassist", "production")]["unit_price_jpy"] == pytest.approx(108_380, abs=1)


def test_pos_rows_and_sum_check() -> None:
    rows = jbpi.parse_pos_pages(POS["2025"], 2025).rows
    periods = sorted({r["period"] for r in rows})
    assert periods[0] == "2024-07" and periods[-1] == "2025-12" and len(periods) == 18
    v = {(r["period"], r["category"]): (r["qty"], r["value_jpy"]) for r in rows}
    assert v[("2025-01", "sports")] == (22_285, 1_158_931_425)
    assert v[("2025-01", "light")] == (58_879, 1_897_493_533)
    assert v[("2024-07", "total")] == (169_623, 7_784_035_881)  # 金額は 1 円の端数差を許す
    mart = jbpi.build_pos_mart(rows)
    sp = next(r for r in mart if r["period"] == "2025-01" and r["category"] == "sports")
    assert sp["avg_price_jpy"] == pytest.approx(52_005, abs=1)
    with pytest.raises(ValueError, match="sum != total"):
        jbpi.parse_pos_pages(
            [
                POS["2025"][0].replace(
                    "22,285 1,897,493,533 58,879 1月", "22,285 1,897,493,533 58,878 1月"
                )
            ],
            2025,
        )
    with pytest.raises(ValueError, match="table not found"):
        jbpi.parse_pos_pages(["POS販売統計時系列表\n2019年\n"], 2025)
