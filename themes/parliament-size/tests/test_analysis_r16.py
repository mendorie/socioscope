import math

import pytest

from theme_parliament_size.analysis.a20261029_r16_government_size import (
    critical_rho,
    direction_h15c,
    judge_h15a,
    judge_h15b,
    judge_h15d,
    log_residuals,
    log_slope,
    p_value,
    window_mean,
)


def test_window_mean_uses_inclusive_window_and_none_when_empty() -> None:
    rows = [
        {"year": 2018, "value": 10.0},
        {"year": 2019, "value": 40.0},
        {"year": 2023, "value": 44.0},
    ]
    assert window_mean(rows) == pytest.approx(42.0)
    assert window_mean(rows, (2019, 2019)) == 40.0
    assert window_mean(rows, (2024, 2025)) is None


def test_log_residuals_are_zero_on_an_exact_cube_root_law() -> None:
    pops = {"A": 1e6, "B": 8e6, "C": 27e6, "D": 64e6}
    seats = {k: 2.0 * p ** (1 / 3) for k, p in pops.items()}
    assert log_slope(seats, pops) == pytest.approx(1 / 3)
    assert all(abs(v) < 1e-9 for v in log_residuals(seats, pops).values())
    seats["D"] *= 2.0  # D だけ法則の 2 倍 → D の残差が最大、残差の和は 0
    res = log_residuals(seats, pops)
    assert max(res, key=lambda k: res[k]) == "D" and res["D"] > 0
    assert sum(res.values()) == pytest.approx(0.0, abs=1e-9)
    assert log_residuals({"A": 1.0}, pops) == {}


def test_judgements_follow_the_pre_registered_cutoffs() -> None:
    assert judge_h15a(0.3) == "整合" and judge_h15a(0.29) == "不支持"
    assert judge_h15b(0.19) == "整合" and judge_h15b(-0.25) == "中間"
    assert judge_h15b(0.3) == "不支持" and judge_h15b(math.nan) == "判定不能"
    assert judge_h15d(-0.29) == "整合" and judge_h15d(0.31) == "不支持"
    assert direction_h15c(0.1).startswith("判定対象外")
    assert direction_h15c(0.4).startswith("正") and direction_h15c(-0.4).startswith("負")


def test_p_value_and_critical_rho_for_n_38() -> None:
    # n = 38 の 5% 境界はおよそ 0.32。境界の ρ では p ≈ 0.05
    crit = critical_rho(38)
    assert crit == pytest.approx(0.32, abs=0.01)
    assert p_value(crit, 38) == pytest.approx(0.05, abs=1e-6)
    assert math.isnan(p_value(math.nan, 38))
