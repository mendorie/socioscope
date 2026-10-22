import math

from theme_bicycle_industry.analysis.a20261022_r1_volume_price import (
    drop_ratio,
    judge_h1,
    ratio_pre_post,
    rebase,
)


def test_ratio_pre_post_averages_available_years_only() -> None:
    s = {2017: 100.0, 2018: 110.0, 2019: 90.0, 2024: 80.0}  # no 2025
    ratio, npre, npost = ratio_pre_post(s)
    assert ratio == 0.8 and (npre, npost) == (3, 1)
    assert math.isnan(ratio_pre_post({2017: 1.0})[0])


def test_judge_h1_thresholds_are_the_preregistered_ones() -> None:
    assert judge_h1(0.95) == "整合"
    assert judge_h1(0.949) == "中間"
    assert judge_h1(0.85) == "中間"
    assert judge_h1(0.849) == "不支持"
    assert judge_h1(math.nan) == "判定不能"


def test_rebase_to_a_period_and_drop_ratio() -> None:
    assert rebase({"2019-12": 50.0, "2020-12": 60.0}, "2019-12") == {
        "2019-12": 100.0,
        "2020-12": 120.0,
    }
    assert rebase({"2019-12": 50.0}, "2018-12") == {}
    assert drop_ratio({2022: 200.0, 2024: 150.0}, 2022, 2024) == -0.25
    assert math.isnan(drop_ratio({2022: 200.0}, 2022, 2024))
