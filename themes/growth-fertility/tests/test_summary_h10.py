"""H10 記事用図（s20261018_h10_summary）の純粋ヘルパのテスト。"""

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h10_family_formation as h10
from theme_growth_fertility.analysis import s20261018_h10_summary as s


def _rows() -> pl.DataFrame:
    data = [
        (2012, "regular", "total", 100.0),
        (2012, "regular", "never_married", 40.0),
        (2022, "regular", "total", 80.0),
        (2022, "regular", "never_married", 36.0),
        (2007, "regular", "total", 50.0),
    ]
    return pl.DataFrame(
        [
            {
                "survey_year": y,
                "sex": "male",
                "age_class": "30-34",
                "employment": e,
                "marital": m,
                "persons": p,
            }
            for y, e, m, p in data
        ]
    )


def test_rate_series_sorted_and_skips_incomplete_years() -> None:
    out = s.rate_series(_rows(), "male", "30-34", "regular")
    assert out == [(2012, pytest.approx(40.0)), (2022, pytest.approx(45.0))]
    assert s.rate_series(_rows(), "male", "30-34", "nonregular") == []


def test_coef_items_flags_predicted_sign() -> None:
    fit = h10.Fit({"a": (1.0, 0.1, 0.5, 1.5), "b": (-1.0, 0.1, -1.5, -0.5)}, 10, 5, (1,))
    items = s.coef_items(fit, ["a", "b", "c"], {"a": 1, "b": 1, "c": 1})
    assert [(x, ok) for x, _, ok in items] == [("a", True), ("b", False), ("c", False)]
    assert items[2][1] is None
    assert [ok for _, _, ok in s.coef_items(None, ["a"], {"a": 1})] == [False]


def test_pt_label() -> None:
    assert s.pt(5.03) == "+5.0 ポイント"
    assert s.pt(-0.85) == "-0.8 ポイント"
