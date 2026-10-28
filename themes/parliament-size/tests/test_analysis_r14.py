from theme_parliament_size.analysis.a20261029_r14_pay_and_workload import (
    judge_h12,
    judge_h13,
    latest_local_salary,
    tercile_verdict,
)


def test_latest_local_salary_takes_the_newest_record() -> None:
    rows = [
        {"attribute": "basic_salary", "value_num": 100.0, "unit": "JPY", "date_from": "2020-01-01"},
        {"attribute": "basic_salary", "value_num": 120.0, "unit": "JPY", "date_from": "2025-01-01"},
        {"attribute": "basic_salary", "value_num": None, "unit": "JPY", "date_from": "2026-01-01"},
        {"attribute": "other", "value_num": 1.0, "unit": "", "date_from": "2026-01-01"},
    ]
    assert latest_local_salary(rows) == (120.0, "JPY", 2025)
    assert latest_local_salary([]) is None


def test_tercile_and_judges() -> None:
    assert tercile_verdict(1, 36) == "高い" and tercile_verdict(12, 36) == "高い"
    assert tercile_verdict(13, 36) == "中位" and tercile_verdict(24, 36) == "中位"
    assert tercile_verdict(25, 36) == "低い"
    assert judge_h12("高い", "高い") == "整合"
    assert judge_h12("低い", "低い") == "不支持"
    assert judge_h12("高い", "中位") == "中間"
    assert judge_h13(120.0, 50.0) == "整合" and judge_h13(90.0, 50.0) == "不支持"
    assert judge_h13(1.0, 0.0) == "不支持"
