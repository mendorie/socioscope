import math

import pytest

from theme_parliament_size.analysis.a20261027_r4_history import (
    SEATS_CSV,
    judge_h6_cross,
    judge_h6_jp,
    load_seats,
    pearson,
    per_million,
    seats_in_year,
)


def test_seats_history_csv_covers_1890_to_2017_and_both_chambers() -> None:
    h = load_seats()
    assert SEATS_CSV.exists()
    assert seats_in_year(h, "lower", 1890) == 300
    assert seats_in_year(h, "lower", 1889) is None
    assert seats_in_year(h, "lower", 1946) == 468
    assert seats_in_year(h, "lower", 1999) == 500
    assert seats_in_year(h, "lower", 2000) == 480
    assert seats_in_year(h, "lower", 2016) == 475
    assert seats_in_year(h, "lower", 2026) == 465
    assert seats_in_year(h, "upper", 2026) == 248
    assert all(r["source"] for r in h)


def test_judges_and_pearson() -> None:
    assert judge_h6_jp(0.6) == "整合" and judge_h6_jp(0.61) == "不支持"
    assert judge_h6_cross(0.29) == "整合" and judge_h6_cross(-0.3) == "不支持"
    assert judge_h6_cross(math.nan) == "判定不能"
    assert pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert math.isnan(pearson([1, 2], [1, 2]))
    assert math.isnan(pearson([1, 1, 1], [1, 2, 3]))
    assert per_million(465, 124_371) == pytest.approx(3.7388, abs=1e-3)
