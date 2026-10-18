"""H11 記事用図（s20261018_h11_summary）の純粋ヘルパのテスト。"""

import polars as pl
import pytest

from theme_growth_fertility.analysis import s20261018_h11_summary as s


def test_parts_pct_sum_to_total() -> None:
    mar, cou, tot = s.parts_pct(-0.27, -0.31)
    assert mar == pytest.approx(-31.0)
    assert cou == pytest.approx(4.0)
    assert mar + cou == pytest.approx(tot)


def test_tfr_series_needs_all_35_ages() -> None:
    full = {a: 0.04 for a in range(15, 50)}
    gap = {a: 0.04 for a in range(15, 49)}
    out = s.tfr_series({2000: full, 2001: gap, 2002: full}, 2000, 2002)
    assert [y for y, _ in out] == [2000, 2002]
    assert out[0][1] == pytest.approx(35 * 0.04)


def test_share_series_filters_women_married_and_years() -> None:
    df = pl.DataFrame(
        {
            "year": [1960, 1970, 2020, 2020, 2020],
            "metric": ["married_share"] * 3 + ["never_married_share", "married_share"],
            "sex": ["F", "F", "F", "F", "M"],
            "age_class": ["25-29"] * 5,
            "value": [70.0, 80.3, 32.3, 66.0, 20.0],
        }
    )
    assert s.share_series(df, "25-29", 1970, 2020) == [(1970, 80.3), (2020, 32.3)]
