"""H12 記事用図（s20261018_h12_summary）の純粋ヘルパのテスト。"""

import polars as pl

from theme_growth_fertility.analysis import s20261018_h12_summary as s


def test_ci_series_sorts_by_year() -> None:
    df = pl.DataFrame(
        {
            "survey_year": [2021, 1982],
            "share_pct": [84.3, 94.2],
            "ci_low": [82.7, 93.2],
            "ci_high": [85.9, 95.2],
        }
    )
    assert s.ci_series(df) == [(1982, 94.2, 93.2, 95.2), (2021, 84.3, 82.7, 85.9)]
