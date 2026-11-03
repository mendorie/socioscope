import math

import polars as pl
import pytest

from theme_public_debt.analysis.a20261103_r1_debt_history import (
    YearObs,
    cross_median,
    decade_mean,
    decade_rise,
    decline_start,
    decompose_debt_change,
    impute_primary,
    in_war,
    judge_h1,
    judge_h2,
    judge_h2b,
    judge_h3,
    judge_h3_design,
    judge_h3b,
    judge_h4a,
    judge_h4b,
    judge_h6a,
    load_panel,
    max_year,
    max_year_through,
    peak_decade,
    period_rate,
    prewar_max,
    rg_dominates,
    share_below,
    window_gaps,
)

# ---- H1 / H2 -------------------------------------------------------------------------------------


def test_in_war_covers_both_world_war_intervals() -> None:
    assert in_war(1914) and in_war(1918) and in_war(1939) and in_war(1945)
    assert not in_war(1913) and not in_war(1919) and not in_war(1946)


def test_prewar_max_returns_year_and_value_within_1870_1950() -> None:
    s = {1869: 999.0, 1900: 50.0, 1918: 120.0, 1944: 200.0, 1951: 300.0}
    assert prewar_max(s) == (1944, 200.0)
    assert prewar_max({1960: 10.0}) is None


def test_judge_h1_uses_one_third_and_half_of_18() -> None:
    assert judge_h1(0) == "整合"
    assert judge_h1(5) == "整合"
    assert judge_h1(6) == "中間"
    assert judge_h1(9) == "中間"
    assert judge_h1(10) == "不支持"


def test_decline_start_uses_1945_or_first_year_up_to_1950() -> None:
    assert decline_start({1945: 100.0, 1946: 90.0}) == 1945
    assert decline_start({1946: 56.0, 1947: 50.0}) == 1946
    assert decline_start({1950: 20.0}) == 1950
    assert decline_start({1951: 20.0}) is None


def test_judge_h2_uses_two_thirds_and_half_of_18() -> None:
    assert judge_h2(12) == "整合"
    assert judge_h2(11) == "中間"
    assert judge_h2(9) == "中間"
    assert judge_h2(8) == "不支持"


# ---- H2b: debt dynamics -----------------------------------------------------------------------


def _synthetic(d0: float, rs: list[float], gs: list[float], pbs: list[float]) -> list[YearObs]:
    """Debt path generated exactly by the identity with sfa = 0 (values in %)."""
    out = [YearObs(2000, d0, None, None, None)]
    d = d0
    for i, (r, g, pb) in enumerate(zip(rs, gs, pbs, strict=True), start=1):
        d = d * (1 + r / 100) / (1 + g / 100) - pb
        out.append(YearObs(2000 + i, d, r, g, pb))
    return out


def test_decomposition_reproduces_delta_d_when_sfa_is_zero() -> None:
    obs = _synthetic(100.0, [5.0, 4.0, 3.0], [10.0, 8.0, 6.0], [1.0, -2.0, 0.5])
    dec = decompose_debt_change(obs, 2000, 2003)
    assert dec.delta == pytest.approx(obs[-1].d - 100.0)  # type: ignore[operator]
    assert dec.sfa == pytest.approx(0.0, abs=1e-9)
    assert dec.gap == 0.0
    assert dec.rg + dec.pb == pytest.approx(dec.delta)
    assert dec.pb == pytest.approx(-(1.0 - 2.0 + 0.5))
    assert (dec.n_years, dec.n_complete) == (3, 3)


def test_decomposition_single_year_known_numbers() -> None:
    # d-1 = 100, r = 5, g = 10: (r-g)/(1+g)·d-1 = -0.05/1.1·100 = -4.5454...; pb = 2 -> -2
    obs = [YearObs(2000, 100.0, None, None, None), YearObs(2001, 90.0, 5.0, 10.0, 2.0)]
    dec = decompose_debt_change(obs, 2000, 2001)
    assert dec.rg == pytest.approx(-100 * 0.05 / 1.1)
    assert dec.pb == pytest.approx(-2.0)
    assert dec.sfa == pytest.approx(-10.0 + 100 * 0.05 / 1.1 + 2.0)


def test_decomposition_identity_closes_with_missing_years() -> None:
    obs = [
        YearObs(2000, 50.0, None, None, None),
        YearObs(2001, 48.0, 4.0, 6.0, 1.0),
        YearObs(2002, None, 4.0, 6.0, 1.0),  # debt missing -> 2002 and 2003 not decomposable
        YearObs(2003, 40.0, 4.0, 6.0, 1.0),
        YearObs(2004, 39.0, 3.0, None, 1.0),  # growth missing
        YearObs(2005, 35.0, 3.0, 5.0, 0.0),
    ]
    dec = decompose_debt_change(obs, 2000, 2005)
    assert dec.delta == pytest.approx(-15.0)
    assert dec.rg + dec.pb + dec.sfa + dec.gap == pytest.approx(dec.delta)
    assert (dec.n_years, dec.n_complete) == (5, 2)
    # complete years 2001 (48-50 = -2) and 2005 (35-39 = -4): gap = -15 - (-6) = -9
    assert dec.gap == pytest.approx(-9.0)


def test_decomposition_requires_endpoints() -> None:
    obs = [YearObs(2000, None, None, None, None), YearObs(2001, 1.0, 1.0, 1.0, 1.0)]
    with pytest.raises(ValueError, match="endpoint"):
        decompose_debt_change(obs, 2000, 2001)


def test_impute_primary_adds_back_interest_on_previous_debt() -> None:
    obs = [YearObs(2000, 100.0, None, None, None), YearObs(2001, 95.0, 5.0, 10.0, -1.0)]
    out = impute_primary(obs)
    assert out[0].pb is None
    assert out[1].pb == pytest.approx(-1.0 + 5.0 / 110.0 * 100.0)
    # with the imputed pb the r-g term and the pb term no longer double-count interest
    dec = decompose_debt_change(out, 2000, 2001)
    assert dec.rg + dec.pb + dec.sfa == pytest.approx(-5.0)


def test_judge_h2b_majority_of_18() -> None:
    assert judge_h2b(10) == "整合"
    assert judge_h2b(9) == "中間"
    assert judge_h2b(8) == "不支持"


# ---- H3 / H3b -----------------------------------------------------------------------------------


def test_cross_median_per_year_ignores_missing_countries() -> None:
    panel = {"A": {2000: 1.0, 2001: 10.0}, "B": {2000: 3.0}, "C": {2000: 1e11, 2001: 20.0}}
    assert cross_median(panel) == {2000: 3.0, 2001: 15.0}


def test_decade_mean_and_rise() -> None:
    s = {y: float(y - 1950) for y in range(1950, 1971)}
    assert decade_mean(s, 1950) == pytest.approx(4.5)
    assert decade_rise(s, 1950) == pytest.approx(10.0)
    assert decade_rise(s, 1960, end=1969) == pytest.approx(9.0)
    assert decade_rise({1950: 1.0}, 1950) is None
    assert decade_mean({}, 1950) is None


def test_peak_decade_skips_missing() -> None:
    assert peak_decade({1950: 1.0, 1960: None, 1970: 3.0, 1980: 2.0}) == 1970
    assert peak_decade({1950: None}) is None


def test_judge_h3_requires_the_preregistered_order() -> None:
    assert judge_h3(1970, 1980, 1990) == "整合"
    assert judge_h3(1970, 1990, 2000) == "整合"
    assert judge_h3(1970, 1980, 2000) == "整合"
    assert judge_h3(1970, 1990, 1990) == "不支持"  # not ordered
    assert judge_h3(1970, 2000, 2000) == "不支持"
    assert judge_h3(1980, 1990, 2000) == "不支持"
    assert judge_h3(1970, 1980, None) == "判定不能"


def test_max_year_takes_first_maximum() -> None:
    assert max_year({1900: 1.0, 2019: 5.0, 2020: 4.0}) == 2019
    assert max_year({1900: 5.0, 2019: 5.0}) == 1900
    assert max_year({}) is None


def test_judge_h3b_two_thirds_and_half() -> None:
    assert judge_h3b(12) == "整合"
    assert judge_h3b(9) == "中間"
    assert judge_h3b(8) == "不支持"


# ---- H4 / H6 -------------------------------------------------------------------------------------


def test_share_below_counts_strictly_below() -> None:
    assert share_below([0.5, 1.0, 2.0, -1.0], 1.0) == pytest.approx(0.5)
    assert math.isnan(share_below([], 1.0))


def test_judge_h4() -> None:
    assert judge_h4a(0.009, 0.51) == "整合"
    assert judge_h4a(0.01, 0.9) == "不支持"
    assert judge_h4a(0.0, 0.5) == "不支持"
    assert judge_h4b(0.40, 0.50) == "整合"
    assert judge_h4b(0.39, 0.50) == "不支持"


def test_judge_h6a() -> None:
    assert judge_h6a(254.0, {"ITA": 155.0, "GRC": 200.0}, 204.0) == "整合"
    assert judge_h6a(254.0, {"ITA": 260.0}, 204.0) == "不支持"
    assert judge_h6a(190.0, {"ITA": 150.0}, 204.0) == "不支持"


# ---- loader --------------------------------------------------------------------------------------


def test_load_panel_nests_unit_metric_country_year() -> None:
    mart = pl.DataFrame(
        {
            "iso3": ["JPN", "JPN", "USA"],
            "year": [2019, 2020, 2020],
            "unit": ["general_gov_gross", "general_gov_gross", "macro"],
            "metric": ["debt_gdp", "debt_gdp", "ltrate"],
            "value": [234.9, 253.9, 0.9],
            "source": ["jst"] * 3,
        }
    )
    p = load_panel(mart)
    assert p["general_gov_gross.debt_gdp"] == {"JPN": {2019: 234.9, 2020: 253.9}}
    assert p["macro.ltrate"] == {"USA": {2020: 0.9}}


def test_load_panel_keeps_only_the_requested_source() -> None:
    mart = pl.DataFrame(
        {
            "iso3": ["JPN", "JPN"],
            "year": [2020, 2020],
            "unit": ["general_gov_gross", "general_gov_gross"],
            "metric": ["debt_gdp", "debt_gdp"],
            "value": [253.9, 258.7],
            "source": ["jst", "imf_gdd"],
        }
    )
    assert load_panel(mart, source="jst") == {"general_gov_gross.debt_gdp": {"JPN": {2020: 253.9}}}
    with pytest.raises(ValueError, match="duplicate"):
        load_panel(mart)


# ---- review round 1: design-text operationalisations ---------------------------------------------


def _dec(rg: float, pb: float) -> object:
    from theme_public_debt.analysis.a20261103_r1_debt_history import Decomposition

    return Decomposition(1945, 1975, 100.0, 50.0, -50.0, rg, pb, -50.0 - rg - pb, 0.0, 30, 30)


def test_rg_dominates_signed_vs_absolute() -> None:
    # rg = -20 (reduces debt), pb = +40 (deficit, raises debt): signed -> rg contributes more to
    # the decline; absolute -> |pb| is larger
    d = _dec(-20.0, 40.0)
    assert rg_dominates(d, signed=True)  # type: ignore[arg-type]
    assert not rg_dominates(d, signed=False)  # type: ignore[arg-type]
    d2 = _dec(-10.0, -30.0)  # surplus reduced debt more than growth/inflation
    assert not rg_dominates(d2, signed=True)  # type: ignore[arg-type]
    assert not rg_dominates(d2, signed=False)  # type: ignore[arg-type]


def test_period_rate_is_change_per_year() -> None:
    s = {1980: 10.0, 1995: 40.0}
    assert period_rate(s, 1980, 1995) == pytest.approx(2.0)
    assert period_rate(s, 1980, 2000) is None


def test_judge_h3_design_periods() -> None:
    assert judge_h3_design(1970, 1980, 1995) == "整合"
    assert judge_h3_design(1970, 1995, 1995) == "不支持"
    assert judge_h3_design(1980, 1980, 1995) == "不支持"
    assert judge_h3_design(1970, 1980, None) == "判定不能"


def test_max_year_through_end_year() -> None:
    s = {2000: 1.0, 2018: 5.0, 2019: 4.0, 2020: 9.0}
    assert max_year_through(s, 2019) == 2018  # 2020 is ignored
    assert max_year_through(s, 2020) == 2020
    assert max_year_through({1990: 1.0}, 2019) == 1990


def test_window_gaps_lists_missing_years() -> None:
    s = {y: 1.0 for y in range(1870, 1951) if y not in (1945, 1946)}
    assert window_gaps(s) == [1945, 1946]
    assert window_gaps({y: 1.0 for y in range(1875, 1951)}) == [1870, 1871, 1872, 1873, 1874]
