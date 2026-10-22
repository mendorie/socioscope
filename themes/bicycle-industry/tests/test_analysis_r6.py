import math

import pytest

from theme_bicycle_industry.analysis.a20261022_r6_participation import (
    OLD,
    YOUNG,
    age_centroid,
    group_mean,
    judge_h11a,
    judge_h11b,
)


def test_group_mean_requires_all_classes() -> None:
    rates = {"20_24": 10.0, "25_29": 8.0, "30_39": 12.0}
    assert group_mean(rates, YOUNG) == 10.0
    assert math.isnan(group_mean(rates, OLD))


def test_judge_h11a_four_quadrants() -> None:
    assert judge_h11a(-1.0, 0.0) == "整合（高齢化・非補充）"
    assert judge_h11a(-1.0, -1.0) == "全年齢の減少（高齢化ではない）"
    assert judge_h11a(1.0, -1.0) == "不支持（若返り）"
    assert judge_h11a(1.0, 1.0) == "不支持（全年齢の増加）"
    assert judge_h11a(math.nan, 1.0) == "判定不能"


def test_age_centroid_is_a_rate_and_width_weighted_mean_of_midpoints() -> None:
    flat = {
        a: 10.0
        for a in (
            "10_14",
            "15_19",
            "20_24",
            "25_29",
            "30_39",
            "40_49",
            "50_59",
            "60_64",
            "65_69",
            "70_plus",
        )
    }
    # equal rates → centroid = width-weighted mean of midpoints over 10–84
    assert age_centroid(flat) == pytest.approx(
        (
            12 * 5
            + 17 * 5
            + 22 * 5
            + 27 * 5
            + 34.5 * 10
            + 44.5 * 10
            + 54.5 * 10
            + 62 * 5
            + 67 * 5
            + 77 * 15
        )
        / 75
    )
    only_young = {"20_24": 10.0}
    assert age_centroid(only_young) == 22.0
    assert math.isnan(age_centroid({}))
    assert (
        judge_h11b(0.5) == "整合（重心が上がった）"
        and judge_h11b(-0.5) == "不支持（重心が下がった）"
    )
    assert judge_h11b(math.nan) == "判定不能"
