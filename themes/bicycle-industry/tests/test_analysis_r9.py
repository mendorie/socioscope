import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r9_auto_moto import (
    change,
    high_band_units,
    judge_deepest,
    judge_same_shape,
)


def test_judges() -> None:
    same = {"a": (0.0, -0.1), "b": (-0.2, -0.3), "c": (0.05, 0.05)}
    assert judge_same_shape(same) == "整合"
    assert judge_same_shape({**same, "b": (-0.3, -0.2)}) == "不支持"
    assert judge_same_shape({**same, "b": (math.nan, -0.2)}) == "判定不能"
    assert judge_deepest({"自動車": -0.01, "二輪": -0.1, "自転車": -0.2}) == "整合"
    assert judge_deepest({"自動車": -0.3, "二輪": -0.1, "自転車": -0.2}) == "不支持"
    assert judge_deepest({"自動車": math.nan, "自転車": -0.2}) == "判定不能"
    assert judge_deepest({"自動車": -0.1}, target="自転車") == "判定不能"


def test_change_and_high_bands() -> None:
    assert change({2022: 100.0, 2025: 121.0}, 2022, 2025) == pytest.approx(0.21)
    assert math.isnan(change({2022: 0.0, 2025: 1.0}, 2022, 2025))
    bands = {
        (2025, b): 1.0
        for b in (
            "ge_2000",
            "1000_1999",
            "900_999",
            "800_899",
            "700_799",
            "600_699",
            "500_599",
            "400_499",
        )
    }
    assert high_band_units(bands, 2025) == 7.0
    assert math.isnan(high_band_units(bands, 2024))
