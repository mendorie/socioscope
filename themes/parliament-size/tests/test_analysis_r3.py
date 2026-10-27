from pathlib import Path

import pytest

from theme_parliament_size.analysis.a20261027_r3_cost import (
    COSTS_CSV,
    judge_h5,
    judge_h5b,
    load_costs,
    per_member_cost,
    rank_of,
    saving_share,
    totals,
)


def test_costs_csv_is_complete_and_cited() -> None:
    assert Path(COSTS_CSV).exists()
    costs = load_costs()
    items = per_member_cost(costs)
    lo, hi = totals(items)
    assert lo < hi
    assert 50_000_000 < lo < 80_000_000  # 議員 1 人当たり 5,000〜8,000 万円の範囲
    assert items["調査研究広報滞在費"] == (12_000_000.0, 12_000_000.0)
    assert items["立法事務費"] == (7_800_000.0, 7_800_000.0)


def test_saving_share_and_judges() -> None:
    assert saving_share(60_000_000, 45, 1_315 * 1e8) == pytest.approx(2.0532, abs=1e-3)
    assert saving_share(60_000_000, 45, 115.2e12) == pytest.approx(0.002344, abs=1e-5)
    assert judge_h5(2.0, 0.002) == "整合"
    assert judge_h5(6.0, 0.002) == "中間"
    assert judge_h5(2.0, 0.06) == "不支持"
    assert (
        judge_h5b(9, 37) == "整合" and judge_h5b(19, 37) == "整合" and judge_h5b(20, 37) == "不支持"
    )
    assert rank_of({"A": 1.0, "B": 2.0, "JPN": 1.5}, "JPN") == 2
