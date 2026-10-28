import pytest

from theme_parliament_size.analysis.a20261029_r11_alternatives import (
    _msl_threshold,
    committee_load,
    extra_staff,
    judge_h8,
    percentile,
)
from theme_parliament_size.analysis.a20261029_r12_future_disparity import judge_h11, pref_ratio
from theme_parliament_size.analysis.a20261029_r13_after_cuts import (
    judge_h7,
    mean_in,
    pct_change,
    yearly_from_ipu,
)


def test_r11_helpers() -> None:
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == pytest.approx(2.5)
    assert percentile([1.0, 2.0, 3.0, 4.0], 2 / 3) == pytest.approx(3.0)
    assert extra_staff(4.45, 5.0, 713) == 392 and extra_staff(4.45, 3.0, 713) == 0
    assert committee_load(575, 465) == pytest.approx(575 / 465)
    assert judge_h8(1.2, [-0.1, 0.0]) == "整合"
    assert judge_h8(1.2, [0.5]) == "中間"
    assert judge_h8(0.3, [0.0]) == "不支持"
    # 修正サンラグの参入閾値: 甲 60, 乙 40 で 2 議席（甲 1・乙 1）。
    # 新党は乙の 1 議席目の商（40/1.4）を超える票 × 1.4 が要る
    thr = _msl_threshold({"甲": 60.0, "乙": 40.0}, 2)
    assert thr == pytest.approx(100 * 40 / (100 + 40))


def test_r12_helpers() -> None:
    ratio, hi, lo, n2 = pref_ratio({"大": 1000.0, "小": 100.0}, 6)
    assert hi == "大" and lo == "小" and n2 == 1 and ratio > 1
    assert judge_h11(2.01) == "整合" and judge_h11(2.0) == "不支持"


def test_r13_helpers() -> None:
    s = {2019: 10.0, 2020: 20.0, 2021: 30.0, 2023: 15.0}
    assert mean_in(s, (2019, 2021)) == pytest.approx(20.0)
    assert mean_in(s, (2030, 2031)) is None
    assert pct_change(20.0, 15.0) == pytest.approx(-25.0)
    assert pct_change(None, 1.0) is None and pct_change(0.0, 1.0) is None
    assert judge_h7(-12.0, -15.0) == "整合"
    assert judge_h7(5.0, 2.0) == "不支持"
    assert judge_h7(-12.0, 2.0) == "中間"
    assert judge_h7(None, -15.0) == "判定不能"
    rows = [
        {"attribute": "num_days_parl_plen", "value_num": 100.0, "date_from": "2019-01-01"},
        {"attribute": "num_days_parl_plen", "value_num": 110.0, "date_from": "2019-06-01"},
        {"attribute": "other", "value_num": 1.0, "date_from": "2019-01-01"},
        {"attribute": "num_days_parl_plen", "value_num": None, "date_from": "2020-01-01"},
    ]
    assert yearly_from_ipu(rows, "num_days_parl_plen") == {2019: 110.0}
