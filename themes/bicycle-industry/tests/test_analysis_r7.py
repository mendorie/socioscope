import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r7_specialized import (
    change,
    index_to,
    judge_h14a,
    judge_h14b,
    regime_means,
)


def test_judge_h14a_loss_or_under_threshold() -> None:
    assert judge_h14a({2022: 1000.0, 2023: -5.0, 2024: 200.0, 2025: 300.0}) == "整合"
    assert judge_h14a({2022: 1000.0, 2023: -5.0, 2024: 200.0, 2025: 301.0}) == "不支持"
    assert judge_h14a({2022: 1000.0, 2023: -5.0, 2024: 200.0, 2025: 301.0}, threshold=0.5) == "整合"
    assert judge_h14a({2022: -1.0, 2023: -5.0, 2024: 1.0, 2025: 1.0}) == "判定不能"
    assert judge_h14a({2022: 1000.0, 2023: 1.0}) == "判定不能"


def test_change_and_judge_h14b() -> None:
    s = {2022: 200.0, 2025: 100.0}
    assert change(s, 2022, 2025) == pytest.approx(-0.5)
    assert math.isnan(change(s, 2022, 2024)) and math.isnan(
        change({2022: 0.0, 2025: 1.0}, 2022, 2025)
    )
    assert judge_h14b(-0.5, -0.3) == "整合" and judge_h14b(-0.2, -0.3) == "不支持"
    assert judge_h14b(math.nan, -0.3) == "判定不能"


def test_index_and_regime_means() -> None:
    s = {2018: 80.0, 2019: 100.0, 2020: 110.0, 2021: 150.0, 2022: 120.0, 2023: 90.0}
    idx = index_to(s, 2019)
    assert idx[2021] == pytest.approx(150.0) and index_to(s, 2017) == {}
    rm = regime_means(idx)
    assert rm["コロナ前 FY2019–20"] == pytest.approx(105.0)
    assert rm["特需 FY2021–22"] == pytest.approx(135.0)
    assert rm["特需後 FY2023–26"] == pytest.approx(90.0)  # FY2024–26 欠損は平均から外す
    assert math.isnan(regime_means({}, {"x": (1, 2)})["x"])
