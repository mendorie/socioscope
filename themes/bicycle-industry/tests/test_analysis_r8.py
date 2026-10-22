import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r8_segments import change, judge_h2, quarter_sum


def test_change_and_judge_h2() -> None:
    assert change({2022: 100.0, 2025: 80.0}, 2022, 2025) == pytest.approx(-0.2)
    assert math.isnan(change({2022: 0.0, 2025: 1.0}, 2022, 2025))
    assert judge_h2(0.0, -0.11) == "整合"
    assert judge_h2(-0.01, -0.5) == "不支持"  # 電動が減れば不支持（僅差でも）
    assert judge_h2(0.05, -0.10) == "不支持"  # −10% ちょうどは不支持
    assert judge_h2(math.nan, -0.5) == "判定不能"


def test_quarter_sum_requires_all_months() -> None:
    s = {"2025-07": 1.0, "2025-08": 2.0, "2025-09": 3.0, "2025-10": 4.0}
    assert quarter_sum(s, 2025, (7, 8, 9)) == 6.0
    assert math.isnan(quarter_sum(s, 2025, (10, 11, 12)))
