import pytest

from theme_parliament_size.analysis.a20261028_r6_pr_history import (
    district_uplift,
    effective_number,
    first_seats_over,
    judge_h4c,
    judge_robust,
    seat_shares,
    small_party_share,
)


def test_effective_number_and_seat_shares() -> None:
    assert effective_number({"甲": 50.0, "乙": 50.0}) == pytest.approx(2.0)
    assert effective_number({"甲": 100.0}) == pytest.approx(1.0)
    assert effective_number({}) == 0.0
    assert seat_shares({"甲": 3, "乙": 1}) == {"甲": 75.0, "乙": 25.0}
    assert seat_shares({"甲": 0}) == {}


def test_small_party_share_uses_the_10_percent_cut() -> None:
    assert small_party_share({"甲": 60.0, "乙": 10.0, "丙": 9.9, "丁": 0.1}) == pytest.approx(10.0)


def test_first_seats_over_walks_down_until_the_limit_is_crossed() -> None:
    pops = {"大": 1000.0, "中": 300.0, "小": 100.0}
    first, ratios = first_seats_over(pops, 14, 4, limit=2.0)  # 3 以下はアダムズの除数探索の範囲外
    assert sorted(ratios) == list(range(4, 15))
    assert first is not None and ratios[first] > 2.0
    assert first == max(n for n in ratios if ratios[n] > 2.0)  # 上から見て最初に超える定数
    none, _ = first_seats_over(pops, 14, 12, limit=100.0)
    assert none is None


def test_district_uplift_and_judges() -> None:
    assert district_uplift(1.999, 1.675) == pytest.approx(1.999 / 1.675)
    with pytest.raises(ValueError, match="positive"):
        district_uplift(1.0, 0.0)
    assert judge_h4c(2.01) == "整合" and judge_h4c(2.0) == "不支持"
    assert judge_robust(6, 7) == "頑健" and judge_robust(5, 7) == "選挙により変わる"
    assert judge_robust(5, 6) == "頑健" and judge_robust(1, 1) == "判定不能"
