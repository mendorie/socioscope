import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r5_world_cycle import (
    PeakDrawdown,
    annual_from_monthly,
    judge_h9,
    judge_h10,
    peak_and_drawdown,
    ratio,
    trailing_mean,
)


def test_ratio_and_judge_h9() -> None:
    s = {2015: 100.0, 2016: 100.0, 2017: 100.0, 2018: 100.0, 2019: 100.0, 2023: 80.0, 2024: 60.0}
    assert ratio(s) == pytest.approx(0.7)
    assert math.isnan(ratio({2023: 1.0}))
    assert judge_h9(0.7, 1.2) == "整合（少なく・高く）"
    assert judge_h9(0.95, 1.2) == "不支持" and judge_h9(0.7, 0.9) == "不支持"
    assert judge_h9(0.7, 1.05) == "中間" and judge_h9(math.nan, 1.0) == "判定不能"


def test_trailing_mean_needs_full_window() -> None:
    s = {f"2020-{m:02d}": float(m) for m in range(1, 13)}
    s["2021-01"] = 13.0
    tm = trailing_mean(s)
    assert set(tm) == {"2020-12", "2021-01"}
    assert tm["2020-12"] == 6.5 and tm["2021-01"] == 7.5


def test_peak_and_drawdown_after_start() -> None:
    s = {
        "2018-06": 500.0,
        "2019-06": 100.0,
        "2021-06": 200.0,
        "2022-06": 180.0,
        "2023-06": 90.0,
        "2024-06": 120.0,
    }
    d = peak_and_drawdown(s)
    assert (
        d.peak_period == "2021-06"
        and d.trough_period == "2023-06"
        and d.drawdown == pytest.approx(-0.55)
    )
    assert math.isnan(peak_and_drawdown({"2018-01": 1.0}).drawdown)


def test_judge_h10_phase_and_depth() -> None:
    parts = PeakDrawdown("2022-03", 1.0, "2023-09", 0.5, -0.5)
    bike_a = PeakDrawdown("2022-06", 1.0, "2023-09", 0.7, -0.3)
    bike_b = PeakDrawdown("2022-03", 1.0, "2023-09", 0.8, -0.2)
    assert judge_h10(parts, [bike_a, bike_b]) == "整合"
    late = PeakDrawdown("2022-09", 1.0, "2023-09", 0.5, -0.5)
    assert judge_h10(late, [bike_a, bike_b]) == "中間"  # depth ok, phase not
    shallow = PeakDrawdown("2022-09", 1.0, "2023-09", 0.9, -0.1)
    assert judge_h10(shallow, [bike_a, bike_b]) == "不支持"
    assert judge_h10(PeakDrawdown("", math.nan, "", math.nan, math.nan), [bike_a]) == "判定不能"


def test_annual_from_monthly_requires_twelve_months() -> None:
    s = {f"2020-{m:02d}": 1.0 for m in range(1, 13)}
    s["2021-01"] = 5.0
    assert annual_from_monthly(s) == {2020: 12.0}
