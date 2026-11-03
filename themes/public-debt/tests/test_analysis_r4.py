import math

import pytest

from theme_public_debt.analysis.a20261103_r1_debt_history import Decomposition
from theme_public_debt.analysis.a20261103_r3_mechanism_2010s import split_rg
from theme_public_debt.analysis.a20261103_r4_japan_inflation_holders import (
    RgSplit,
    Shares,
    add_splits,
    boj_holdings_gdp,
    chain,
    compound,
    decompose_jst,
    decompose_multi_year,
    judge_h11,
    judge_h12,
    judge_h13,
    level_growth,
    market_held,
    primary_from_overall,
    r_minus_g,
    shares_of_decline,
    split_multi_year,
    split_rg_jst,
    unexplained,
)


def _path(
    d0: float, rs: list[float], gs: list[float], pbs: list[float], y0: int = 1946
) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float]]:
    """sfa = 0 になるように作った債務経路（% 単位）。r は金利（%）で与える（JST 流）。"""
    d = {y0: d0}
    r: dict[int, float] = {}
    g: dict[int, float] = {}
    pb: dict[int, float] = {}
    for i, (rr, gg, p) in enumerate(zip(rs, gs, pbs, strict=True), start=1):
        y = y0 + i
        r[y], g[y], pb[y] = rr, gg, p
        d[y] = d[y - 1] * (1 + rr / 100) / (1 + gg / 100) - p
    return d, r, g, pb


# ---- 累積・水準 ---------------------------------------------------------------------------------


def test_compound_and_level_growth() -> None:
    assert compound([10.0, 10.0]) == pytest.approx(21.0)
    assert compound([]) == 0.0
    assert level_growth(2.0, 3.0) == pytest.approx(50.0)
    assert level_growth(0.5, 3.0) == pytest.approx(500.0)


# ---- 年ごとの分解と内訳 ------------------------------------------------------------------------


def test_decompose_jst_reproduces_delta_with_zero_sfa() -> None:
    d, r, g, pb = _path(56.0, [3.7, 5.5, 5.5], [176.0, 99.0, 30.0], [0.6, 1.7, 1.7])
    dec = decompose_jst(d, r, g, pb, 1946, 1949)
    assert dec.sfa == pytest.approx(0.0, abs=1e-9)
    assert dec.gap == 0.0
    assert dec.delta == pytest.approx(d[1949] - 56.0)
    assert dec.pb == pytest.approx(-(0.6 + 1.7 + 1.7))  # 黒字なので負（債務を減らす向き）


def test_split_rg_jst_adds_up_and_puts_missing_cpi_into_unsplit() -> None:
    d, r, g, pb = _path(56.0, [3.7, 5.5, 5.5], [176.0, 99.0, 30.0], [0.6, 1.7, 1.7])
    cpi = {1947: 125.0, 1949: 32.0}  # 1948 年の CPI が欠損
    dec = decompose_jst(d, r, g, pb, 1946, 1949)
    sp = split_rg_jst(d, r, g, pb, cpi, 1946, 1949)
    assert sp.total == pytest.approx(dec.rg)
    grow_1948 = -99.0 / 199.0 * d[1947]
    assert sp.unsplit == pytest.approx(grow_1948)
    assert sp.interest > 0
    assert sp.inflation < 0


def test_split_rg_jst_skips_years_that_decompose_skips() -> None:
    d, r, g, pb = _path(56.0, [3.7, 5.5], [176.0, 99.0], [0.6, 1.7])
    del pb[1948]  # 総合収支が欠ければ分解しない年
    dec = decompose_jst(d, r, g, pb, 1946, 1948)
    sp = split_rg_jst(d, r, g, pb, {1947: 125.0, 1948: 76.0}, 1946, 1948)
    assert dec.n_complete == 1
    assert sp.total == pytest.approx(dec.rg)


def test_split_rg_jst_matches_r3_split_rg_on_converted_inputs() -> None:
    d, r, g, pb = _path(80.0, [2.0, 4.0, 3.0], [8.0, 12.0, 5.0], [-1.0, 0.5, 2.0], y0=1950)
    cpi = {1951: 5.0, 1952: 9.0, 1953: -1.0}
    interest = {y: r[y] * d[y - 1] / 100 for y in r}
    rgdp = {y: ((1 + g[y] / 100) / (1 + cpi[y] / 100) - 1) * 100 for y in g}
    mine = split_rg_jst(d, r, g, pb, cpi, 1950, 1953)
    theirs = split_rg(d, interest, rgdp, cpi, 1950, 1953)
    assert (mine.interest, mine.real, mine.inflation) == pytest.approx(theirs)


def test_split_puts_everything_into_inflation_when_real_growth_is_zero() -> None:
    d, r, g, pb = _path(100.0, [0.0], [10.0], [0.0], y0=1950)
    sp = split_rg_jst(d, r, g, pb, {1951: 10.0}, 1950, 1951)
    assert sp.real == pytest.approx(0.0, abs=1e-12)
    assert sp.inflation == pytest.approx(-10.0 / 110.0 * 100.0)


# ---- 1945 年欠損の扱い --------------------------------------------------------------------------


def test_decompose_multi_year_closes_and_matches_two_annual_steps_when_sfa_is_zero() -> None:
    # 2 年を 1 ステップにまとめても、pb = 0 なら累積の r・g で Δd を再現する
    d, r, g, pb = _path(200.0, [3.0, 4.0], [50.0, 300.0], [0.0, 0.0], y0=1944)
    r_cum, g_cum = compound([r[1945], r[1946]]), compound([g[1945], g[1946]])
    dec = decompose_multi_year(1944, 1946, d[1944], d[1946], r_cum, g_cum, 0.0)
    assert dec.sfa == pytest.approx(0.0, abs=1e-9)
    assert dec.delta == pytest.approx(dec.rg + dec.pb + dec.sfa + dec.gap)
    assert dec.n_years == 2 and dec.n_complete == 1


def test_split_multi_year_sums_to_rg_term() -> None:
    dec = decompose_multi_year(1944, 1946, 204.0, 56.0, 7.5, 555.2, 1.5)
    sp = split_multi_year(204.0, 7.5, 555.2, 1951.3)
    assert sp.total == pytest.approx(dec.rg)
    # CPI が名目 GDP より大きく上がった（実質マイナス）ので、インフレ寄与は成長部分全体より大きい
    assert sp.inflation < sp.total
    assert sp.real > 0


def test_unexplained_puts_delta_into_gap_and_chain_adds_up() -> None:
    a = unexplained(1944, 1946, 204.0, 56.0)
    assert (a.rg, a.pb, a.sfa, a.gap) == (0.0, 0.0, 0.0, pytest.approx(-148.0))
    d, r, g, pb = _path(56.0, [3.7, 5.5], [176.0, 99.0], [0.6, 1.7])
    b = decompose_jst(d, r, g, pb, 1946, 1948)
    c = chain([a, b])
    assert (c.start, c.end, c.d_start, c.d_end) == (1944, 1948, 204.0, d[1948])
    assert c.delta == pytest.approx(c.rg + c.pb + c.sfa + c.gap)
    assert c.gap == pytest.approx(-148.0)


def test_chain_rejects_non_contiguous_pieces() -> None:
    a = unexplained(1944, 1946, 204.0, 56.0)
    b = unexplained(1947, 1950, 27.5, 14.0)
    with pytest.raises(ValueError, match="contiguous"):
        chain([a, b])
    with pytest.raises(ValueError, match="empty"):
        chain([])


def test_add_splits() -> None:
    s = add_splits([RgSplit(1.0, -2.0, -3.0, 0.0), RgSplit(0.5, 1.0, -1.0, -0.5)])
    assert (s.interest, s.real, s.inflation, s.unsplit) == (1.5, -1.0, -4.0, -0.5)
    assert s.total == pytest.approx(-4.0)


def test_primary_from_overall_adds_back_interest() -> None:
    pb = primary_from_overall({1946: 100.0}, {1947: 5.0}, {1947: 25.0}, {1947: -2.0, 1948: 1.0})
    assert pb == {1947: pytest.approx(-2.0 + 5.0 / 125.0 * 100.0)}


# ---- 割合と判定 --------------------------------------------------------------------------------


def _dec(delta: float, rg: float, pb: float, sfa: float, gap: float = 0.0) -> Decomposition:
    return Decomposition(1944, 1955, 200.0, 200.0 + delta, delta, rg, pb, sfa, gap, 11, 9)


def test_shares_of_decline_sum_to_one_and_sign_convention() -> None:
    dec = _dec(-100.0, -70.0, -10.0, 0.0, -20.0)
    sp = RgSplit(interest=10.0, real=-20.0, inflation=-60.0, unsplit=0.0)
    sh = shares_of_decline(dec, sp)
    assert sh is not None
    assert sh.inflation == pytest.approx(0.6)
    assert sh.interest == pytest.approx(-0.1)  # 利子は債務を増やす向き
    assert sh.residual == pytest.approx(0.2)
    assert sh.unexplained == pytest.approx(0.2)  # gap（未分解区間）
    assert sh.sfa == pytest.approx(0.0)  # 測った sfa
    total = sh.inflation + sh.real + sh.interest + sh.unsplit + sh.balance + sh.residual
    assert total == pytest.approx(1.0)
    assert shares_of_decline(_dec(5.0, 1.0, 1.0, 3.0), RgSplit(1.0, 0.0, 0.0, 0.0)) is None


def test_shares_of_decline_rejects_inconsistent_split() -> None:
    with pytest.raises(ValueError, match="add up"):
        shares_of_decline(_dec(-10.0, -5.0, 0.0, -5.0), RgSplit(0.0, 0.0, -1.0, 0.0))


def _sh(infl: float, real: float, bal: float, resid: float, gap_part: float = 0.0) -> Shares:
    """resid = 未分解区間 gap_part + 測った sfa。"""
    return Shares(infl, real, 1.0 - infl - real - bal - resid, 0.0, bal, gap_part, resid - gap_part)


def test_shares_split_residual_into_unexplained_interval_and_measured_sfa() -> None:
    # 1944→46 を分解しない構成: Δd −191.7 のうち gap −148.0、測った sfa +32.6
    dec = _dec(-191.7, -58.6, -17.7, 32.6, -148.0)
    sp = RgSplit(interest=7.2, real=-18.5, inflation=-47.3, unsplit=0.0)
    sh = shares_of_decline(dec, sp)
    assert sh is not None
    assert sh.unexplained == pytest.approx(148.0 / 191.7)
    assert sh.sfa == pytest.approx(-32.6 / 191.7)
    assert sh.residual == pytest.approx(sh.unexplained + sh.sfa)
    assert judge_h11(sh) == "中間"


def test_judge_h11_follows_the_registered_rules_and_order() -> None:
    assert judge_h11(_sh(0.5, 0.2, 0.1, 0.2)) == "整合"  # 等号は整合
    assert judge_h11(_sh(1.70, -0.45, 0.10, -0.30)) == "整合"
    assert judge_h11(_sh(0.25, 0.10, 0.09, 0.60, 0.77)) == "中間"  # 残差（gap + sfa）≥ 1/2
    assert judge_h11(_sh(0.2, 0.1, 0.1, 0.5)) == "中間"  # 等号
    assert judge_h11(_sh(0.6, 0.0, 0.0, 0.6)) == "整合"  # 両方なら整合を先に見る（補完）
    assert judge_h11(_sh(0.2, 0.3, 0.1, 0.3)) == "不支持"  # 実質成長が大きい
    assert judge_h11(_sh(0.2, 0.1, 0.35, 0.3)) == "不支持"  # 総合収支項が大きい
    assert judge_h11(_sh(0.4, 0.1, 0.1, 0.3)) == "中間"  # どれでもない（補完）


def test_r_minus_g_and_judge_h12() -> None:
    assert r_minus_g({2020: 1.0, 2021: 0.5}, {2021: 3.0}) == {2021: pytest.approx(-2.5)}
    base = {y: -1.0 for y in range(2011, 2020)}
    ok = {**base, **{y: -3.0 for y in range(2021, 2026)}}
    j, all_neg, m_rec, m_base = judge_h12(ok)
    assert (j, all_neg) == ("整合", True)
    assert m_rec == pytest.approx(3.0) and m_base == pytest.approx(1.0)
    # 1 年でも r − g ≥ 0 なら不支持
    assert judge_h12({**ok, 2023: 0.0})[0] == "不支持"
    # 年が欠けても不支持
    missing = {k: v for k, v in ok.items() if k != 2025}
    assert judge_h12(missing)[0] == "不支持"
    # 平均 (g − r) が広がらなければ不支持（等しい場合も）
    assert judge_h12({**base, **{y: -1.0 for y in range(2021, 2026)}})[0] == "不支持"
    assert judge_h12(missing, recent=(2021, 2024))[0] == "整合"


def test_market_held_and_boj_ratio() -> None:
    assert market_held(204.8, 46.7) == pytest.approx(204.8 * 0.533)
    assert market_held(100.0, 0.0) == 100.0
    assert boj_holdings_gdp(4_700_401.0, 6_634_400.0) == pytest.approx(70.85, abs=0.01)


def test_judge_h13_requires_first_place() -> None:
    assert judge_h13({"JPN": 140.0, "ITA": 137.1, "USA": 124.4}) == "整合"
    assert judge_h13({"JPN": 137.1, "ITA": 137.1}) == "整合"  # 同値は首位に含む
    assert judge_h13({"JPN": 109.2, "ITA": 137.1, "USA": 124.4}) == "不支持"


def test_split_ignores_zero_nominal_growth_year() -> None:
    d, r, g, pb = _path(100.0, [2.0], [0.0], [0.0], y0=1950)
    sp = split_rg_jst(d, r, g, pb, {1951: 3.0}, 1950, 1951)
    assert sp.real == 0.0 and sp.inflation == 0.0
    assert sp.unsplit == pytest.approx(0.0)
    assert sp.interest == pytest.approx(2.0)
    assert not math.isnan(sp.total)
