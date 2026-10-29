import math

import polars as pl
import pytest

from theme_essential_work_wages.analysis.common import (
    group_ratio,
    load_flags,
    verdict,
    weighted_median,
    weighted_quantile,
    wls,
)


def test_weighted_median_follows_cumulative_weight() -> None:
    assert weighted_median([1, 2, 3], [1, 1, 1]) == 2
    assert weighted_median([1, 2, 3], [1, 1, 10]) == 3
    assert weighted_median([5, 1], [1, 100]) == 1


def test_weighted_quantile_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="no observations"):
        weighted_quantile([], [], 0.5)
    with pytest.raises(ValueError, match="length"):
        weighted_quantile([1, 2], [1], 0.5)
    with pytest.raises(ValueError, match="negative"):
        weighted_quantile([1, 2], [1, -1], 0.5)
    with pytest.raises(ValueError, match="q outside"):
        weighted_quantile([1, 2], [1, 1], 1.5)


def test_group_ratio_median_and_bottom_quartile_overrepresentation() -> None:
    df = pl.DataFrame(
        {
            "wage": [100.0, 200.0, 300.0, 400.0],
            "workers": [10.0, 10.0, 10.0, 10.0],
            "essential": [1, 1, 0, 0],
        }
    )
    r = group_ratio(df, "essential", "wage", "workers")
    assert r["median_all"] == 200.0 and r["median_group"] == 100.0
    assert r["median_ratio"] == pytest.approx(0.5)
    assert r["p25_all"] == 100.0
    assert r["share_all"] == pytest.approx(0.5)
    assert r["share_bottom_quartile"] == pytest.approx(1.0)
    assert r["overrepresentation"] == pytest.approx(2.0)


def test_group_ratio_requires_flagged_rows() -> None:
    df = pl.DataFrame({"wage": [1.0], "workers": [1.0], "essential": [0]})
    with pytest.raises(ValueError, match="essential"):
        group_ratio(df, "essential", "wage", "workers")


def test_wls_recovers_a_known_slope() -> None:
    xs = [float(i) for i in range(20)]
    df = pl.DataFrame({"y": [2.0 + 0.5 * x for x in xs], "x": xs, "w": [1.0] * 20})
    out = wls(df, "y", ["x"], "w")
    assert out["x"][0] == pytest.approx(0.5, abs=1e-9)
    assert out["const"][0] == pytest.approx(2.0, abs=1e-9)
    assert out["_n"][0] == 20


def test_verdict_three_way() -> None:
    assert verdict(0.25, 0.20, 0.10, higher_is_ok=True) == "整合"
    assert verdict(0.15, 0.20, 0.10, higher_is_ok=True) == "中間"
    assert verdict(0.05, 0.20, 0.10, higher_is_ok=True) == "不支持"
    assert verdict(-0.2, -0.15, -0.05, higher_is_ok=False) == "整合"
    assert verdict(-0.1, -0.15, -0.05, higher_is_ok=False) == "中間"
    assert verdict(0.0, -0.15, -0.05, higher_is_ok=False) == "不支持"


def test_committed_flag_tables_load_with_integer_flags() -> None:
    jp = load_flags("jp_bsws2020")
    assert jp.height == 145
    assert set(jp["essential"].unique().to_list()) <= {-1, 0, 1}
    assert jp.filter(pl.col("occupation") == "医師")["licensed"][0] == 1
    us = load_flags("us_census_occ2018")
    assert us.height == 565
    assert us["occupation_code"].n_unique() == 565
    old = load_flags("jp_bsws2009")
    assert old.height == 129
    assert math.isfinite(float(old["education_years"].mean()))
