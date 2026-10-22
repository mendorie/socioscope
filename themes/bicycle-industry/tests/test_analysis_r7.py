import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r7_specialized import change, judge_h14a, judge_h14b


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
