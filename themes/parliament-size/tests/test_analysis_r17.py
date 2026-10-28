import math

import pytest

from theme_parliament_size.analysis.a20261030_r17_system_oversight_trust import (
    judge_h16a_i,
    judge_h16a_ii,
    judge_h16b,
    judge_h16c,
    latest,
    median,
    spend_per_member,
)


def test_median_and_latest() -> None:
    assert median([3.0, 1.0, 2.0]) == 2.0
    assert median([4.0, 1.0, 2.0, 3.0]) == 2.5
    assert math.isnan(median([]))
    rows = [{"year": 2021, "value": 19.3}, {"year": 2023, "value": 25.0}]
    assert latest(rows) == (2023, 25.0)
    assert latest([]) is None


def test_spend_per_member_scales_per_capita_spending_by_population_over_seats() -> None:
    # 1 人当たり 17,000 USD × 1 億 2,437 万人 ÷ 465 ≈ 45.5 億 USD/議員
    assert spend_per_member(17_000.0, 124_371.0, 465.0) == pytest.approx(4.547e9, rel=1e-3)


def test_judgements_follow_the_pre_registered_cutoffs() -> None:
    assert judge_h16a_i(3.0) == "再現" and judge_h16a_i(2.9) == "再現せず"
    assert judge_h16a_ii(0.19) == "整合" and judge_h16a_ii(0.3) == "不支持"
    assert judge_h16a_ii(0.25) == "中間" and judge_h16a_ii(-0.4) == "中間"
    assert judge_h16b(5) == "整合" and judge_h16b(6) == "不支持"
    assert judge_h16c(0.1).startswith("整合（無関係")
    assert judge_h16c(-0.3).startswith("整合（小さい")
    assert judge_h16c(0.3).startswith("逆") and judge_h16c(0.25) == "中間"
    assert judge_h16c(math.nan) == "判定不能"
