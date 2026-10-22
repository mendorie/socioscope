import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r2_bullwhip_price import (
    bullwhip_ratio,
    judge_h3,
    judge_h4,
    pct_change,
)


def test_pct_change_and_missing() -> None:
    assert pct_change({2022: 200.0, 2023: 150.0}, 2022, 2023) == -0.25
    assert math.isnan(pct_change({2022: 200.0}, 2022, 2023))
    assert math.isnan(pct_change({2022: 0.0, 2023: 1.0}, 2022, 2023))


def test_bullwhip_ratio_only_when_demand_falls() -> None:
    assert bullwhip_ratio(-0.30, -0.20) == pytest.approx(1.5)
    assert math.isnan(bullwhip_ratio(-0.30, 0.05))
    assert math.isnan(bullwhip_ratio(math.nan, -0.2))


def test_judges_follow_preregistered_thresholds() -> None:
    assert (
        judge_h3(1.5) == "整合" and judge_h3(1.49) == "不支持" and judge_h3(math.nan) == "判定不能"
    )
    assert (
        judge_h4(5.0) == "整合" and judge_h4(4.9) == "不支持" and judge_h4(math.nan) == "判定不能"
    )
