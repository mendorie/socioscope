from theme_parliament_size.analysis.a20261029_r15_small_parties import (
    entries,
    judge_h14a,
    judge_h14b,
)


def test_entries_detects_first_wins_with_up_to_three_pr_seats_and_growth() -> None:
    pr = {
        "甲": {45: 3, 46: 14},  # 第 45 回に既にいる → 初当選と判定できず除外
        "乙": {49: 3, 50: 9, 51: 1},  # 初当選 49、次回 9 → 成長
        "丙": {50: 2, 51: 0},  # 初当選 50、次回 0、次々回は未観測
        "丁": {48: 8},  # 4 議席以上で入ったので対象外
        "戊": {51: 1},  # 初当選 51、以後未観測
    }
    total = {
        "甲": {45: 5, 46: 18},
        "乙": {49: 3, 50: 9, 51: 1},
        "丙": {50: 2},
        "丁": {48: 8},
        "戊": {51: 1},
    }
    out = entries(pr, total)
    assert [(r["party"], r["entry"], r["grown"], r["observed"]) for r in out] == [
        ("乙", 49, True, True),
        ("丙", 50, False, True),
        ("戊", 51, False, False),
    ]
    assert judge_h14a(1, 3) == "整合" and judge_h14a(1, 4) == "中間"
    assert judge_h14a(0, 3) == "不支持" and judge_h14a(0, 0) == "判定不能"


def test_judge_h14b_counts_thresholds_of_three_percent_or_more() -> None:
    rows = [
        {"legal_threshold_pct": "5"},
        {"legal_threshold_pct": "3"},
        {"legal_threshold_pct": "0"},
    ]
    assert judge_h14b(rows) == ("整合", 2, 3)
    assert judge_h14b(rows[1:]) == ("不支持", 1, 2)
