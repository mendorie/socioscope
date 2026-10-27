import math

import pytest

from theme_parliament_size.analysis.a20261027_r5_roles import (
    judge_h2a,
    ranks,
    spearman,
    staff_per_member,
)


def test_ranks_with_ties_and_spearman() -> None:
    assert ranks([10.0, 20.0, 20.0, 5.0]) == [2.0, 3.5, 3.5, 1.0]
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    assert math.isnan(spearman([1, 2], [1, 2]))
    assert math.isnan(spearman([1, 1, 1], [1, 2, 3]))


def test_judge_h2a() -> None:
    assert judge_h2a(-0.3) == "整合"
    assert judge_h2a(-0.25) == "中間"
    assert judge_h2a(0.1) == "不支持"
    assert judge_h2a(math.nan) == "判定不能"


def test_staff_per_member_handles_both_single_and_combined_reports() -> None:
    both = [
        {"statutory_seats": 465.0, "permanent_staff": 1814.0, "staff_combined_parl": False},
        {"statutory_seats": 248.0, "permanent_staff": 1360.0, "staff_combined_parl": False},
    ]
    assert staff_per_member(both) == (pytest.approx((1814 + 1360) / 713), "両院合計")
    one = [{"statutory_seats": 300.0, "permanent_staff": 900.0, "staff_combined_parl": False}]
    assert staff_per_member(one) == (3.0, "一院")
    combined = [
        {"statutory_seats": 400.0, "permanent_staff": 1000.0, "staff_combined_parl": True},
        {"statutory_seats": 100.0, "permanent_staff": None, "staff_combined_parl": None},
    ]
    assert staff_per_member(combined) == (2.0, "両院合計（1 議院の申告）")
    partial = [
        {"statutory_seats": 400.0, "permanent_staff": 1000.0, "staff_combined_parl": False},
        {"statutory_seats": 100.0, "permanent_staff": None, "staff_combined_parl": None},
    ]
    assert staff_per_member(partial) == (2.5, "1 議院のみ")
    assert staff_per_member([{"statutory_seats": 1.0, "permanent_staff": None}]) is None
