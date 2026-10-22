import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r4_pullforward_origin import (
    PullForward,
    judge_h7,
    judge_h8a,
    judge_h8b,
    judge_level,
    level_ratio,
    linear_trend,
    median,
    pullforward,
)


def test_linear_trend_extrapolates_a_straight_line_and_needs_three_points() -> None:
    s = {2015: 10.0, 2016: 12.0, 2017: 14.0, 2018: 16.0, 2019: 18.0}
    tr = linear_trend(s, 2015, 2019)
    assert tr is not None and tr[2019] == pytest.approx(18.0) and tr[2024] == pytest.approx(28.0)
    assert linear_trend({2018: 1.0, 2019: 2.0}, 2015, 2019) is None
    lg = linear_trend(
        {2015: 100.0, 2016: 110.0, 2017: 121.0, 2018: 133.1, 2019: 146.41}, 2015, 2019, log=True
    )
    assert lg is not None and lg[2020] == pytest.approx(161.05, rel=1e-3)


def test_pullforward_sums_excess_and_deficit_and_ratio() -> None:
    trend = {y: 100.0 for y in range(2015, 2026)}
    s = {2020: 120.0, 2021: 130.0, 2022: 90.0, 2023: 80.0, 2024: 80.0}
    pf = pullforward(s, trend)
    assert pf.excess == 50.0 and pf.deficit == -50.0 and pf.ratio == pytest.approx(1.0)
    assert judge_h7(pf) == "整合（先食い）"
    assert judge_h7(PullForward(50.0, -150.0, 3.0, 2, 3)) == "不支持（構造的縮小）"
    assert judge_h7(PullForward(50.0, -90.0, 1.8, 2, 3)) == "中間"
    assert judge_h7(PullForward(50.0, -20.0, 0.4, 2, 3)) == "不足小（事後区分: R < 0.8）"
    assert judge_h7(PullForward(-10.0, -20.0, math.nan, 2, 3)) == "判定不能（特需なし）"
    assert judge_h7(PullForward(50.0, 0.0, math.nan, 2, 0)) == "判定不能（特需なし）"


def test_level_ratio_and_judgement() -> None:
    trend = {y: 100.0 for y in range(2015, 2026)}
    assert level_ratio({2023: 90.0, 2024: 70.0}, trend) == pytest.approx(0.8)
    assert math.isnan(level_ratio({2019: 1.0}, trend))
    assert judge_level(0.95) == "戻っている" and judge_level(0.79) == "新しい常態（下方）"
    assert judge_level(0.85) == "中間" and judge_level(math.nan) == "判定不能"


def test_median_and_h8_judgements() -> None:
    assert median([3.0, 1.0, 2.0]) == 2.0 and median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert math.isnan(median([math.nan]))
    assert judge_h8a(-0.10) == "整合" and judge_h8a(0.0) == "不支持" and judge_h8a(-0.05) == "中間"
    assert judge_h8b(5.0) == "整合" and judge_h8b(0.0) == "不支持" and judge_h8b(2.0) == "中間"
