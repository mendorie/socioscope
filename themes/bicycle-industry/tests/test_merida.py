import json
from pathlib import Path

import pytest

from theme_bicycle_industry import merida

FIXTURES = Path(__file__).parent / "fixtures"
FY2023 = json.loads((FIXTURES / "merida_fy2023_pages.json").read_text())
FY2025 = json.loads((FIXTURES / "merida_fy2025_pages.json").read_text())


def test_urls_and_names() -> None:
    assert merida.url(2023).startswith("https://merida-cdn.m-c-g.net/") and merida.url(
        2023
    ).endswith("112q4.pdf?p1")
    assert merida.raw_name(2025) == "merida_consolidated_fy2025_q4.pdf"
    assert "merida-bikes.com" in merida.INVESTOR_PAGE


def test_parse_fy2023_reads_current_and_prior_year() -> None:
    rows = {(r["fy"], r["metric"]): r["value_ntd_k"] for r in merida.parse_pages(FY2023, 2023).rows}
    assert rows[(2023, "revenue")] == 27_261_117 and rows[(2022, "revenue")] == 37_003_082
    assert (
        rows[(2023, "equity_method_share")] == -684_938
        and rows[(2022, "equity_method_share")] == 623_962
    )
    assert (
        rows[(2023, "sbc_carrying_amount")] == 18_653_865
        and rows[(2022, "sbc_carrying_amount")] == 18_650_181
    )
    assert (
        rows[(2023, "sbc_group_sales")] == 13_012_660
        and rows[(2022, "sbc_group_sales")] == 25_310_245
    )
    assert all(
        r["doc_fy"] == 2023 and r["source"] == "merida_ir"
        for r in merida.parse_pages(FY2023, 2023).rows
    )


def test_parse_fy2025_handles_renumbered_income_line_and_positive_share() -> None:
    rows = {(r["fy"], r["metric"]): r["value_ntd_k"] for r in merida.parse_pages(FY2025, 2025).rows}
    assert (
        rows[(2025, "equity_method_share")] == 92_064
        and rows[(2024, "equity_method_share")] == -4_064_696
    )
    assert rows[(2025, "sbc_carrying_amount")] == 15_970_171
    assert rows[(2025, "associates_carrying_total")] == 16_260_388
    assert (
        rows[(2025, "sbc_group_sales")] == 14_581_368
        and rows[(2024, "sbc_group_sales")] == 12_442_585
    )


def test_parse_fails_closed() -> None:
    with pytest.raises(ValueError, match="not look like a Merida"):
        merida.parse_pages(["<html>"], 2023)
    with pytest.raises(ValueError, match="items not found"):
        merida.parse_pages(["美利達工業股份有限公司 及子公司 合併資產負債表"], 2023)
    with pytest.raises(ValueError, match="no document"):
        merida.parse_pages(FY2023, 2019)
    with pytest.raises(ValueError, match="not a readable PDF"):
        merida.parse(b"<html>", 2023)


def test_build_mart_prefers_own_year_and_records_restatement() -> None:
    staged = merida.parse_pages(FY2023, 2023).rows + merida.parse_pages(FY2025, 2025).rows
    bumped = [dict(r) for r in staged]
    for r in bumped:
        if r["fy"] == 2024 and r["metric"] == "revenue":
            r["value_ntd_k"] = 1  # pretend FY2025 filing restates FY2024
    own2024 = {
        "fy": 2024,
        "doc_fy": 2024,
        "metric": "revenue",
        "value_ntd_k": 29_633_132,
        "source": merida.SOURCE,
    }
    mart = {(r["fy"], r["metric"]): r for r in merida.build_mart([*bumped, own2024])}
    assert (
        mart[(2024, "revenue")]["value_ntd_k"] == 29_633_132
        and mart[(2024, "revenue")]["restated_next_year"] == 1
    )
    assert (
        mart[(2022, "revenue")]["doc_fy"] == 2023
        and mart[(2022, "revenue")]["restated_next_year"] is None
    )
    assert sorted(mart) == sorted(set(mart)) and all(
        r["company"] == "Merida" for r in mart.values()
    )
