import polars as pl
import pytest

from theme_public_debt.analysis.a20261103_r2_interest_net_debt import (
    at,
    base_year,
    h5_counts,
    halved,
    judge_h5,
    judge_h6,
    judge_h6a,
    judge_h6b,
    peak_year,
    rank_desc,
    series,
    share_peak_after,
    total_debt,
)


def test_base_year_is_first_year_from_1990() -> None:
    assert base_year([1985, 1990, 1991]) == 1990
    assert base_year([2001, 2002]) == 2001  # 米国は 2001 年から
    assert base_year([1980, 1989]) is None
    assert base_year([]) is None


def test_halved_is_undefined_for_non_positive_base() -> None:
    assert halved(1.2, 0.6) is True  # ちょうど半分は「半分以下」
    assert halved(1.19, 0.62) is False  # 日本 1990 → 2019 に近い数値例
    assert halved(-1.85, 0.11) is None  # 純利子受取の国
    assert halved(0.0, -0.1) is None


def test_judge_h5_follows_the_preregistered_thresholds() -> None:
    assert judge_h5(10, 10) == "整合"
    assert judge_h5(11, 6) == "中間"
    assert judge_h5(9, 18) == "不支持"
    assert judge_h5(9, 9) == "不支持"
    assert judge_h5(2, 2, threshold=2) == "整合"


def test_h5_counts_counts_halving_rise_and_undefined() -> None:
    s = {
        "A": {1990: 4.0, 2019: 1.0, 2024: 2.0},  # 半分以下、上昇
        "B": {1990: 2.0, 2019: 1.5, 2024: 1.0},  # どちらも満たさない
        "C": {1990: -1.0, 2019: 0.5, 2024: 0.6},  # 前半は定義不能、上昇
        "D": {2001: 3.0, 2019: 1.5, 2024: 1.5},  # 起点 2001、半分ちょうど、横ばいは上昇ではない
    }
    assert h5_counts(s) == (2, 2, 1)
    assert h5_counts(s, late=2019) == (2, 0, 1)
    # 全国 2001 年起点: 2001 年の無い国は前半を満たさない
    assert h5_counts(s, fixed_base=2001) == (1, 2, 0)


def test_rank_desc_counts_strictly_larger_values() -> None:
    v = {"JPN": 213.6, "ITA": 134.7, "USA": 122.3}
    assert rank_desc(v, "JPN") == 1
    assert rank_desc(v, "USA") == 3
    assert rank_desc({"A": 1.0, "B": 1.0}, "B") == 1  # 同値は同順位


def test_judge_h6a_needs_top_in_both_sources_and_above_1944() -> None:
    assert judge_h6a(1, 1, 253.9, 213.6, 204.0) == "整合"
    assert judge_h6a(1, 2, 253.9, 213.6, 204.0) == "不支持"
    assert judge_h6a(1, 1, 253.9, 200.0, 204.0) == "不支持"


def test_judge_h6b_requires_the_net_rank_to_drop() -> None:
    assert judge_h6b(1, 2) == "整合"
    assert judge_h6b(1, 1) == "不支持"
    assert judge_h6b(3, 2) == "不支持"
    assert judge_h6(1, 1, 253.9, 213.6, 204.0, 1) == ("整合", "不支持")
    assert judge_h6(1, 1, 253.9, 213.6, 204.0, 3) == ("整合", "整合")


def test_total_debt_uses_only_years_with_both_series() -> None:
    assert total_debt({1990: 50.0, 1991: 60.0}, {1991: 100.0, 1992: 90.0}) == {1991: 160.0}


def test_peak_year_ignores_pre_start_and_takes_the_earliest_tie() -> None:
    assert peak_year({1940: 500.0, 1950: 100.0, 2020: 300.0}) == 2020
    assert peak_year({2009: 200.0, 2020: 200.0}) == 2009
    assert peak_year({1940: 1.0}) is None
    assert peak_year({}) is None


def test_share_peak_after_counts_cutoff_inclusive() -> None:
    assert share_peak_after({"A": 2008, "B": 2007, "C": 2020}) == (2, 3)
    assert share_peak_after({}) == (0, 0)


def _mart() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "iso3": ["JPN", "JPN", "ITA", "XXX", "JPN"],
            "year": [2019, 2024, 2024, 2024, 2024],
            "unit": ["general_gov_gross"] * 4 + ["general_gov_net"],
            "metric": ["interest_gdp"] * 4 + ["debt_gdp"],
            "value": [0.62, 0.16, 3.66, None, 141.1],
            "source": ["imf_fm"] * 5,
        },
        schema_overrides={"value": pl.Float64},
    )


def test_series_filters_source_unit_metric_and_countries() -> None:
    s = series(_mart(), "imf_fm", "general_gov_gross", "interest_gdp", ["JPN", "ITA", "XXX"])
    assert s == {"ITA": {2024: 3.66}, "JPN": {2019: 0.62, 2024: 0.16}}  # null は落ちる
    assert at(s, 2019) == {"JPN": 0.62}


def test_series_fails_closed_on_duplicate_keys() -> None:
    dup = pl.concat([_mart(), _mart().head(1)])
    with pytest.raises(ValueError, match="duplicate"):
        series(dup, "imf_fm", "general_gov_gross", "interest_gdp")
