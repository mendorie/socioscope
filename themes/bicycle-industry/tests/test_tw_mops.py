from pathlib import Path

import pytest

from theme_bicycle_industry import tw_mops

FIXTURES = Path(__file__).parent / "fixtures"
OK = (FIXTURES / "mops_9921_2019_06.json").read_bytes()
EMPTY = (FIXTURES / "mops_9921_2013_06_empty.json").read_bytes()


def test_body_uses_roc_year_and_custom_datatype() -> None:
    assert tw_mops.body("9921", 2019, 6) == {
        "companyId": "9921",
        "dataType": "2",
        "subsidiaryCompanyId": "",
        "year": "108",
        "month": "6",
    }
    assert tw_mops.raw_name("5306", 2024, 1) == "mops_5306_2024_01.json"
    assert len(tw_mops.requests()) == len(tw_mops.COMPANIES) * (2026 - 2014 + 1) * 12


def test_parse_reads_monthly_revenue_from_label_value_pairs() -> None:
    parsed = tw_mops.parse(OK, "9921", 2019, 6)
    assert len(parsed.rows) == 1 and parsed.skipped == []
    r = parsed.rows[0]
    assert r["company"] == "giant" and r["period"] == "2019-06"
    assert r["revenue_ntd_k"] == 4881737.0 and r["revenue_prev_year_ntd_k"] == 4858140.0
    assert r["ytd_ntd_k"] == 30679486.0 and r["source"] == "tw_mops"


def test_parse_returns_no_row_for_months_before_coverage() -> None:
    parsed = tw_mops.parse(EMPTY, "9921", 2013, 6)
    assert parsed.rows == [] and parsed.skipped and "9921 2013-06" in parsed.skipped[0]


def test_parse_fails_closed() -> None:
    with pytest.raises(ValueError, match="not JSON"):
        tw_mops.parse(b"<html>", "9921", 2019, 6)
    with pytest.raises(ValueError, match="does not match"):
        tw_mops.parse(OK, "9921", 2019, 7)  # yymm 10806 vs request 10807
    with pytest.raises(ValueError, match="unknown company"):
        tw_mops.parse(OK, "0000", 2019, 6)


def test_build_mart_sorts_and_rejects_duplicates() -> None:
    rows = tw_mops.parse(OK, "9921", 2019, 6).rows
    mart = tw_mops.build_mart(rows)
    assert mart[0]["iso3"] == "TWN"
    with pytest.raises(ValueError, match="duplicate mops key"):
        tw_mops.build_mart([*rows, dict(rows[0])])
