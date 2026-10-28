import pytest

from theme_parliament_size.analysis.a20261028_r10_bureaucracy import latest_value, per_thousand


def test_latest_value_respects_max_year() -> None:
    rows = [
        {"year": 2021, "value_thousands": 1.0},
        {"year": 2025, "value_thousands": 3.0},
        {"year": 2023, "value_thousands": 2.0},
        {"year": 2030, "value_thousands": 9.0},
    ]
    assert latest_value(rows) == (2025, 3.0)
    assert latest_value(rows, max_year=2022) == (2021, 1.0)
    assert latest_value([], max_year=2025) is None


def test_per_thousand() -> None:
    # 2,477 千人 ÷ 124,371 千人 × 1000 = 19.9 人/1,000 人
    assert per_thousand(2477.183, 124371.0) == pytest.approx(19.92, abs=0.01)
