import pytest

from theme_public_debt.analysis.a20261103_r1_debt_history import Decomposition
from theme_public_debt.analysis.a20261103_r3_mechanism_2010s import (
    base_window,
    build_obs,
    change,
    decompose,
    effective_rate,
    h7_flags,
    h9_hit,
    interest_to_revenue,
    judge_h7,
    judge_h8,
    judge_h9,
    judge_h10,
    last_at_or_before,
    nominal_growth,
    nominal_growth_series,
    period_mean,
    rate_exposure,
    rate_series,
    rg_breakeven,
    rg_share_of_decline,
    shift_rate,
    split_rg,
    window_max,
)


def _synthetic(
    d0: float, rs: list[float], gs: list[float], pbs: list[float], y0: int = 2010
) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float]]:
    """恒等式で sfa = 0 になるように作った債務経路（% 単位）。interest_t = r_t·d_{t−1}/100。"""
    d = {y0: d0}
    interest: dict[int, float] = {}
    g: dict[int, float] = {}
    pb: dict[int, float] = {}
    for i, (r, gg, p) in enumerate(zip(rs, gs, pbs, strict=True), start=1):
        y = y0 + i
        interest[y] = r * d[y - 1] / 100
        g[y] = gg
        pb[y] = p
        d[y] = d[y - 1] * (1 + r / 100) / (1 + gg / 100) - p
    return d, interest, g, pb


# ---- 名目成長率・実効金利 ----------------------------------------------------------------


def test_nominal_growth_compounds_real_growth_and_cpi() -> None:
    assert nominal_growth(2.0, 3.0) == pytest.approx(5.06)
    assert nominal_growth(0.0, 0.0) == 0.0
    assert nominal_growth(-5.0, 2.0) == pytest.approx(-3.1)
    assert nominal_growth_series({2020: 1.0, 2021: 2.0}, {2021: 1.0}) == {2021: pytest.approx(3.02)}


def test_effective_rate_divides_by_previous_debt() -> None:
    assert effective_rate(2.0, 100.0) == pytest.approx(2.0)
    assert effective_rate(-1.0, 50.0) == pytest.approx(-2.0)  # 純利子受取は負の金利
    assert effective_rate(1.0, 0.0) is None


def test_build_obs_uses_previous_year_debt_for_r() -> None:
    obs = build_obs(
        {2010: 100.0, 2011: 110.0}, {2011: 3.0}, {2011: 4.0}, {2011: -1.0}, [2010, 2011]
    )
    assert obs[0].r is None  # 2009 年の債務が無い
    assert obs[1].r == pytest.approx(3.0)
    assert (obs[1].g, obs[1].pb, obs[1].d) == (4.0, -1.0, 110.0)


def test_rate_series_skips_years_without_previous_debt() -> None:
    assert rate_series({2010: 50.0}, {2010: 1.0, 2011: 1.0}) == {2011: pytest.approx(2.0)}


# ---- 分解 ---------------------------------------------------------------------------------------


def test_decompose_reproduces_delta_with_zero_sfa_on_synthetic_path() -> None:
    d, i, g, pb = _synthetic(
        80.0, [2.0, 1.5, 1.0, 0.5], [3.0, 4.0, 8.0, 6.0], [-3.0, -2.0, -1.0, 0.5]
    )
    dec = decompose(d, i, g, pb, 2010, 2014)
    assert dec.sfa == pytest.approx(0.0, abs=1e-9)
    assert dec.gap == 0.0
    assert dec.n_complete == 4
    assert dec.delta == pytest.approx(d[2014] - d[2010])
    assert dec.rg + dec.pb == pytest.approx(dec.delta)
    assert dec.pb == pytest.approx(3.0 + 2.0 + 1.0 - 0.5)  # pb 項 = −Σpb（赤字で正）
    assert dec.rg < 0  # r < g の年だけなので債務を減らす向き


def test_decompose_identity_closes_with_residual_and_missing_years() -> None:
    d = {2019: 100.0, 2020: 120.0, 2021: 118.0, 2022: 115.0, 2023: 111.0}
    i = {2020: 2.0, 2021: 1.8, 2023: 2.5}  # 2022 年の利払いが欠損
    g = {2020: -4.0, 2021: 6.0, 2022: 9.0, 2023: 5.0}
    pb = {2020: -8.0, 2021: -4.0, 2022: -2.0, 2023: -1.0}
    dec = decompose(d, i, g, pb, 2019, 2023)
    assert dec.delta == pytest.approx(11.0)
    assert dec.delta == pytest.approx(dec.rg + dec.pb + dec.sfa + dec.gap)
    assert dec.gap == pytest.approx(115.0 - 118.0)  # 2022 年の Δd は分解できない
    assert dec.n_complete == 3
    # (r−g) 項の手計算: r_t = i_t / d_{t−1} × 100 なので
    # (r − g)/(100 + g)·d₋₁ = (100·i − g·d₋₁)/(100 + g)
    rg_2020 = (100 * 2.0 - (-4.0) * 100.0) / (100 - 4.0)
    rg_2021 = (100 * 1.8 - 6.0 * 120.0) / (100 + 6.0)
    rg_2023 = (100 * 2.5 - 5.0 * 115.0) / (100 + 5.0)
    assert dec.rg == pytest.approx(rg_2020 + rg_2021 + rg_2023)
    assert dec.pb == pytest.approx(8.0 + 4.0 + 1.0)


def test_decompose_requires_debt_at_both_endpoints() -> None:
    with pytest.raises(ValueError, match="endpoint"):
        decompose({2010: 50.0}, {}, {}, {}, 2010, 2012)


def test_split_rg_parts_sum_to_rg_term() -> None:
    d, i, _, pb = _synthetic(90.0, [2.0, 1.0, 3.0], [5.06, 8.15, 1.0], [-2.0, 1.0, -1.0])
    rgdp = {2011: 2.0, 2012: 3.0, 2013: -1.0}
    cpi = {2011: 3.0, 2012: 5.0, 2013: 2.0}
    g = nominal_growth_series(rgdp, cpi)
    dec = decompose(d, i, g, pb, 2010, 2013)
    parts = split_rg(d, i, rgdp, cpi, 2010, 2013)
    assert sum(parts) == pytest.approx(dec.rg)
    assert parts[0] > 0  # 利子は債務を増やす向き
    assert parts[2] < 0  # インフレは減らす向き


def test_period_mean_uses_available_years() -> None:
    assert period_mean({2010: 1.0, 2012: 3.0, 2020: 9.0}, 2010, 2019) == pytest.approx(2.0)
    assert period_mean({}, 2010, 2019) is None


# ---- H7 / H8 ------------------------------------------------------------------------------------


def _dec(delta: float, rg: float, pb: float) -> Decomposition:
    """1 年の分解で (r−g) 項・pb 項・Δd を指定値にする。

    利払い 0、g を逆算: g = −100·rg/(100 + rg)。
    """
    d, i, p = {2010: 100.0, 2011: 100.0 + delta}, {2011: 0.0}, {2011: -pb}
    dec = decompose(d, i, {2011: -100 * rg / (100 + rg)}, p, 2010, 2011)
    assert dec.rg == pytest.approx(rg) and dec.pb == pytest.approx(pb)
    return dec


def test_h7_flags_requires_deficit_that_offsets_rg() -> None:
    assert h7_flags(_dec(10.0, -10.0, 20.0)) == (True, True)
    assert h7_flags(_dec(0.0, -10.0, 10.0)) == (True, True)  # 等号は満たす
    assert h7_flags(_dec(-5.0, -10.0, 5.0)) == (True, False)  # 赤字が小さい
    assert h7_flags(_dec(-20.0, -10.0, -10.0)) == (True, False)  # 黒字
    assert h7_flags(_dec(15.0, 5.0, 10.0)) == (False, False)  # rg > 0


def test_judge_h7_follows_the_registered_thresholds() -> None:
    assert judge_h7(12, 10) == "整合"
    assert judge_h7(18, 18) == "整合"
    assert judge_h7(12, 9) == "中間"
    assert judge_h7(15, 6) == "中間"
    assert judge_h7(11, 11) == "不支持"


def test_rg_share_of_decline_only_for_declining_countries() -> None:
    assert rg_share_of_decline(_dec(-10.0, -6.0, 2.0)) == pytest.approx(0.6)
    assert rg_share_of_decline(_dec(-10.0, 4.0, -14.0)) == pytest.approx(-0.4)
    assert rg_share_of_decline(_dec(5.0, -6.0, 11.0)) is None


def test_judge_h8_needs_all_three_for_consistent() -> None:
    assert judge_h8(12, 0.5, 12) == "整合"
    assert judge_h8(16, 1.86, 13) == "整合"
    assert judge_h8(12, 0.49, 12) == "中間"
    assert judge_h8(12, 0.8, 11) == "中間"
    assert judge_h8(12, None, 12) == "中間"
    assert judge_h8(11, 0.9, 18) == "不支持"
    assert judge_h8(6, 2.34, 14) == "不支持"


# ---- H9 -----------------------------------------------------------------------------------------


def test_change_falls_back_to_last_year_at_or_before_end() -> None:
    s = {2008: 80.0, 2017: 85.0}
    assert last_at_or_before(s, 2019) == 2017
    assert change(s, 2008, 2019) == (2017, pytest.approx(5.0))
    assert change({2009: 1.0}, 2008, 2019) is None
    assert change({2008: 1.0}, 2008, 2019) is None  # 終点が起点と同じ


def test_h9_hit_and_judgement() -> None:
    assert h9_hit(10.0, -3.0) is True
    assert h9_hit(10.0, 4.99) is True
    assert h9_hit(10.0, 5.0) is False  # 5 pt ちょうどは「上昇 5 pt 未満」ではない
    assert h9_hit(0.0, -10.0) is False  # 公的が上昇していない
    assert judge_h9(12) == "整合"
    assert judge_h9(11) == "中間"
    assert judge_h9(10) == "中間"
    assert judge_h9(9) == "不支持"


# ---- H10 ----------------------------------------------------------------------------------------


def test_interest_to_revenue_in_percent() -> None:
    r = interest_to_revenue({2024: 1.0, 2025: -0.5, 2026: 1.0}, {2024: 40.0, 2025: 50.0, 2026: 0.0})
    assert r == {2024: pytest.approx(2.5), 2025: pytest.approx(-1.0)}


def test_base_window_handles_usa_and_late_starters() -> None:
    assert base_window("JPN", {1990: 1.0, 2024: 1.0}) == (1990, 1999)
    assert base_window("DEU", {1991: 1.0}) == (1991, 1999)
    assert base_window("IRL", {1995: 1.0}) == (1995, 1999)
    assert base_window("USA", {2001: 1.0}) == (2001, 2004)
    assert base_window("XXX", {2001: 1.0}) is None
    assert base_window("XXX", {}) is None


def test_window_max_takes_the_earliest_tie() -> None:
    s = {1990: 3.0, 1995: 5.0, 1997: 5.0, 2000: 9.0}
    assert window_max(s, (1990, 1999)) == (1995, 5.0)
    assert window_max(s, (2001, 2004)) is None


def test_judge_h10_threshold_is_twelve() -> None:
    assert judge_h10(12) == "整合"
    assert judge_h10(14) == "整合"
    assert judge_h10(11) == "不支持"


# ---- r の過小評価への感度 ----------------------------------------------------------------


def test_rg_breakeven_is_the_uniform_rate_shift_that_zeroes_the_rg_term() -> None:
    d, i, g, pb = _synthetic(80.0, [1.0, 1.0, 1.0], [4.0, 5.0, 3.0], [-2.0, -2.0, -2.0])
    dec = decompose(d, i, g, pb, 2010, 2013)
    exp = rate_exposure(d, i, g, pb, 2010, 2013)
    assert exp == pytest.approx(sum(d[t - 1] / (100 + g[t]) for t in (2011, 2012, 2013)))
    x = rg_breakeven(dec, exp)
    assert x is not None and x > 0
    # r を毎年 x pp 上げた入力で分解し直すと (r−g) 項は 0 になる
    i2 = {t: i[t] + x * d[t - 1] / 100 for t in i}
    assert decompose(d, i2, g, pb, 2010, 2013).rg == pytest.approx(0.0, abs=1e-9)
    assert rg_breakeven(dec, 0.0) is None


def test_shift_rate_keeps_identity_and_moves_residual() -> None:
    d, i, g, pb = _synthetic(80.0, [1.0, 1.0], [4.0, 5.0], [-2.0, -2.0])
    dec = decompose(d, i, g, pb, 2010, 2012)
    exp = rate_exposure(d, i, g, pb, 2010, 2012)
    sh = shift_rate(dec, 0.5, exp)
    assert sh.rg == pytest.approx(dec.rg + 0.5 * exp)
    assert sh.pb == dec.pb and sh.delta == dec.delta
    assert sh.delta == pytest.approx(sh.rg + sh.pb + sh.sfa + sh.gap)
