import pytest

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import (
    allocate,
    block_populations,
    disparity,
    gallagher_chamber,
    group_reduction,
    judge_h3,
    judge_h3b,
    judge_h4,
    judge_h4b,
    national_shares,
    party_totals,
)
from theme_parliament_size.soumu import BLOCKS

BV = {
    "北海道": {"甲": 600.0, "乙": 300.0, "丙": 100.0},
    "四国": {"甲": 500.0, "乙": 400.0, "丙": 100.0},
}


def test_allocate_and_totals_per_block() -> None:
    seats = {"北海道": 8, "四国": 6}
    d = allocate(BV, seats, "dhondt")
    assert sum(d["北海道"].values()) == 8 and sum(d["四国"].values()) == 6
    assert party_totals(d) == {"甲": 9, "乙": 5, "丙": 0}  # 北海道は 100 票の同点を先の党（甲）に
    m = allocate(BV, seats, "msl")
    assert sum(party_totals(m).values()) == 14
    with pytest.raises(ValueError, match="unknown method"):
        allocate(BV, seats, "x")


def test_national_shares_sum_to_100() -> None:
    s = national_shares(BV)
    assert s["甲"] == pytest.approx(55.0) and sum(s.values()) == pytest.approx(100.0)


def test_group_reduction_splits_small_and_large_parties() -> None:
    shares = {"甲": 55.0, "乙": 35.0, "丙": 10.0, "丁": 0.5}
    base = {"甲": 10, "乙": 6, "丙": 3, "丁": 1}
    after = {"甲": 8, "乙": 5, "丙": 1, "丁": 0}
    rs, rl, d = group_reduction(base, after, shares)
    # 小政党 = 得票率 10% 未満 → 丁 のみ（丙は 10.0 で大政党側）: 1 → 0 = 100%
    assert rs == pytest.approx(100.0)
    assert rl == pytest.approx(100.0 * (19 - 14) / 19)
    assert d == pytest.approx(rs - rl)
    assert group_reduction({"甲": 1}, {"甲": 1}, {"甲": 5.0}) == (0.0, 0.0, 0.0)


def test_judges() -> None:
    assert judge_h3([5.0, 6.0]) == "整合"
    assert judge_h3([5.0, -1.0]) == "不支持"
    assert judge_h3([5.0, 3.0]) == "中間"
    assert judge_h3b([4.9, 0.0]) == "整合" and judge_h3b([5.0, 0.0]) == "不支持"
    assert judge_h4(1.0, 1.1, [2.0, 3.0]) == "整合"
    assert judge_h4(1.0, 1.05, [2.0, 3.0]) == "不支持"
    assert judge_h4(1.0, 1.2, [1.0]) == "中間"
    assert judge_h4b(2.01) == "整合" and judge_h4b(2.0) == "不支持"


def test_gallagher_chamber_mixes_smd_and_pr_seats() -> None:
    shares = {"甲": 60.0, "乙": 40.0}
    assert gallagher_chamber(shares, {"甲": 6.0, "乙": 4.0}, {"甲": 6, "乙": 4}) == pytest.approx(
        0.0
    )
    assert gallagher_chamber(shares, {"甲": 10.0}, {"甲": 10}) == pytest.approx(40.0)


def test_disparity_and_block_populations() -> None:
    ratio, hi, lo = disparity({"A": 1000.0, "B": 300.0}, {"A": 2, "B": 1})
    assert (ratio, hi, lo) == (pytest.approx(500 / 300), "A", "B")
    prefs = [
        {"pref": "北海道", "population_japanese": 5.0},
        {"pref": "青森県", "population_japanese": 1.0},
        {"pref": "岩手県", "population_japanese": 1.5},
    ]
    pops = block_populations(prefs, {"北海道": "北海道", "青森県": "東北", "岩手県": "東北"})
    assert pops["北海道"] == 5.0 and pops["東北"] == 2.5
    assert set(pops) == set(BLOCKS)
