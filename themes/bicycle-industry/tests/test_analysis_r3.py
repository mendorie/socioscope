import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r3_retail import (
    breakeven_individual_share,
    change,
    judge_h5a,
    judge_h5b,
)


def test_change_handles_missing_and_none() -> None:
    assert change({2016: 100.0, 2021: 90.0}, 2016, 2021) == pytest.approx(-0.1)
    assert math.isnan(change({2016: None, 2021: 90.0}, 2016, 2021))
    assert math.isnan(change({2016: 100.0}, 2016, 2021))


def test_h5_judgements() -> None:
    assert judge_h5a(-0.15, -0.04) == "整合"  # establishments fall faster than sales
    assert judge_h5a(-0.04, -0.15) == "不支持"
    assert judge_h5a(math.nan, -0.1) == "判定不能"
    assert judge_h5b(-0.19, -0.03) == "整合"  # individual shops fall faster
    assert judge_h5b(-0.03, -0.19) == "不支持"
    assert judge_h5b(-0.1, math.nan) == "判定不能"


def test_breakeven_share_solves_the_corporate_only_condition() -> None:
    # corporate sales 2021 = 231,252; corporate establishments 3,021 -> 2,924 (-3.2%).
    share = breakeven_individual_share(240079.0, 231252.0, 3021.0, 2924.0)
    assert 0.004 < share < 0.006
    # no individual sales needed when corporate sales already grew faster than establishments
    assert breakeven_individual_share(100.0, 110.0, 10.0, 10.0) == 0.0
