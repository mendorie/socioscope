"""R4: 日本の戦後の債務消滅、2019〜25 年の r − g、市中保有、グロス利払い（H11〜H14、事後追加）。

事後追加の仮説（design/themes/public-debt.md「事後追加（2026-11-03 夜、R4 …）」節）。R1〜R3 の結果を
見た後に立て、判定基準は追加データ（OECD Economic Outlook のグロス利払い、財務省の国債保有者別
内訳）を見る前に設計書で固定。閾値は設計書のまま:
  H11: JST の日本 1944 → 1955 年の Δd（約 −192 pt）を (r−g) 項・総合収支項・残差に分け、
       (r−g) 項を利子・実質成長・インフレに分ける。インフレ寄与 ≥ 低下幅の 1/2 → 整合。
       実質成長寄与か総合収支項の方が（インフレ寄与より）大きい → 不支持。
       残差 ≥ 1/2 → 中間「分解できない（帳簿上の消滅）」。
       判定の順序（設計書に無い、補完）: 整合 → 中間（残差）→ 不支持 → どれでもなければ中間。
       1945 年が欠損なので 1944 → 1946 年の扱いを 2 通り出す:
         どちらも主としない（設計書の逸脱の記録、2026-11-03）。
         分解しない: 1944 → 1946 は未分解区間（帳簿上の消滅）、1946 → 1955 を年ごとに分解。
         2 年 1 ステップ: 1944 → 1946 を 2 年 1 ステップで分解（g は JST の名目 GDP 水準 1946/1944、
               r は長期金利 1945・1946 年の複利、総合収支は 1946 年の値 × 2、
               インフレは CPI 水準 1946/1944）。
       英国・米国 1946 → 1975 年の同じ分解を並べる（記述）。
  H12: IMF の日本。r_t = FM 純利払い_t ÷ WEO 総債務_{t−1} × 100、g_t = (1+実質成長)(1+CPI)−1。
       2021〜2025 の各年 r − g < 0、かつ 2021–25 平均 (g − r) > 2011–19 平均 (g − r) → 整合、
       どちらかが崩れれば不支持。副: OECD グロス利払いで r を作り直す（探索的）。
  H13: 市中保有 ≒ WEO 日本 2025 年総債務 ×（1 − 日銀保有比率 46.7%）。18 か国の WEO 2025 年総債務
       （他国は未修正）で首位 → 整合、首位でなければ不支持。2024 年でも併記。
  H14: OECD EO のグロス利払い ÷ GDP で H5 を再判定（R2 の judge_h5・h5_counts をそのまま使う）。

因果は主張しない。「インフレで消した」は会計上の分解であり、政策意図（金融抑圧）は文献の見立て。

決定的スクリプト（乱数なし）。入力は data/marts/public_debt_panel.parquet。H13 の探索的な
金額ベースの検算だけ data/staged/mof/jgb_holders.parquet と
data/staged/oecd/eo_interest.parquet（名目 GDP）を読む。
純粋ヘルパは tests/test_analysis_r4.py で検証する。
"""

from __future__ import annotations

import argparse
import itertools
import logging
import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from theme_public_debt.analysis.a20261103_r1_debt_history import (
    Decomposition,
    YearObs,
    decompose_debt_change,
)
from theme_public_debt.analysis.a20261103_r2_interest_net_debt import (
    H5_START,
    JST18,
    NAMES,
    at,
    base_year,
    h5_counts,
    halved,
    judge_h5,
    rank_desc,
    series,
)
from theme_public_debt.analysis.a20261103_r3_mechanism_2010s import (
    nominal_growth_series,
    period_mean,
    rate_series,
)

THEME_DIR = Path(__file__).resolve().parents[3]
SRC_JST = "Jordà–Schularick–Taylor Macrohistory Database R6（CC BY-NC-SA 4.0、2026-11-03 取得）"
SRC_IMF = (
    "IMF World Economic Outlook 2026 年 10 月版／Fiscal Monitor（DataMapper、2026-11-03 取得）"
)
SRC_OECD = "OECD (2026), OECD Economic Outlook 119（2026-11-03 取得）"
SRC_MOF = "財務省「国債等の保有者別内訳」令和 8 年 6 月末速報（日本銀行「資金循環統計」より作成）"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"

HALF = 0.5
H12_RECENT = (2021, 2025)
H12_BASE = (2011, 2019)
H13_YEAR = 2025  # 2026 年 6 月末の日銀比率に最も近い WEO の実績年（一部推計）
ESTIMATE_YEAR = 2025

Series = dict[int, float]

# ---- pure helpers: H11 decomposition -------------------------------------------------------------


@dataclass(frozen=True)
class RgSplit:
    """(r−g) 項の内訳（pt）。interest + real + inflation + unsplit = (r−g) 項。

    unsplit: 分解はできたが CPI が欠けて実質成長とインフレに分けられない年の成長部分。
    """

    interest: float
    real: float
    inflation: float
    unsplit: float

    @property
    def total(self) -> float:
        return self.interest + self.real + self.inflation + self.unsplit


def compound(rates_pct: Sequence[float]) -> float:
    """年率（%）の複利による累積変化率（%）。"""
    f = 1.0
    for r in rates_pct:
        f *= 1.0 + r / 100.0
    return (f - 1.0) * 100.0


def level_growth(lo: float, hi: float) -> float:
    """水準 lo → hi の変化率（%）。"""
    return (hi / lo - 1.0) * 100.0


def _split_growth(grow: float, g: float, infl: float) -> tuple[float, float]:
    """成長部分 −g/(100+g)·d₋₁ を ln(1+γ) : ln(1+π) で実質成長とインフレに配分。

    R3 の split_rg と同じ規則。

    γ は (1+g)/(1+π) − 1（実質成長）。ln(1+g) = 0 なら成長部分も 0 なので (0, 0)。
    """
    lg = math.log1p(g / 100.0)
    if lg == 0.0:
        return 0.0, 0.0
    w_infl = math.log1p(infl / 100.0) / lg
    return grow * (1.0 - w_infl), grow * w_infl


def year_obs_jst(
    d: Mapping[int, float],
    r: Mapping[int, float],
    g: Mapping[int, float],
    pb: Mapping[int, float],
    years: Sequence[int],
) -> list[YearObs]:
    """JST の系列から R1 の YearObs（r = 長期金利、g = 名目 GDP 成長率、pb = 総合収支）を作る。"""
    return [YearObs(y, d.get(y), r.get(y), g.get(y), pb.get(y)) for y in years]


def decompose_jst(
    d: Mapping[int, float],
    r: Mapping[int, float],
    g: Mapping[int, float],
    pb: Mapping[int, float],
    start: int,
    end: int,
) -> Decomposition:
    """start → end を年ごとに分解（R1 の decompose_debt_change）。欠けた年の Δd は gap。"""
    return decompose_debt_change(year_obs_jst(d, r, g, pb, range(start, end + 1)), start, end)


def split_rg_jst(
    d: Mapping[int, float],
    r: Mapping[int, float],
    g: Mapping[int, float],
    pb: Mapping[int, float],
    cpi: Mapping[int, float],
    start: int,
    end: int,
) -> RgSplit:
    """decompose_jst が分解する年と同じ年について (r−g) 項を 利子・実質成長・インフレ に分ける。

    利子 = r/(100+g)·d₋₁、成長 = −g/(100+g)·d₋₁。CPI が欠ける年の成長部分は unsplit に入れる
    ので、合計は必ず decompose_jst の (r−g) 項に一致する。
    """
    i_part = real = infl = unsplit = 0.0
    for t in range(start + 1, end + 1):
        if not all(t in s for s in (d, r, g, pb)) or (t - 1) not in d:
            continue
        dp = d[t - 1]
        i_part += r[t] / (100.0 + g[t]) * dp
        grow = -g[t] / (100.0 + g[t]) * dp
        if t not in cpi:
            unsplit += grow
            continue
        re, inf = _split_growth(grow, g[t], cpi[t])
        if re == 0.0 and inf == 0.0:
            unsplit += grow
        real += re
        infl += inf
    return RgSplit(i_part, real, infl, unsplit)


def primary_from_overall(
    d: Mapping[int, float],
    r: Mapping[int, float],
    g: Mapping[int, float],
    overall: Mapping[int, float],
) -> Series:
    """総合収支 → 基礎的収支の近似 pb ≈ 総合収支 + r/(100+g)·d₋₁（R1 の impute_primary と同式）。"""
    return {
        y: overall[y] + r[y] / (100.0 + g[y]) * d[y - 1]
        for y in sorted(overall)
        if y in r and y in g and (y - 1) in d
    }


def decompose_multi_year(
    start: int, end: int, d0: float, d1: float, r_cum: float, g_cum: float, pb_sum: float
) -> Decomposition:
    """start → end を 1 ステップで分解: Δd = (R − G)/(100 + G)·d₀ − Σpb + sfa。

    R・G は期間の累積（%）。"""
    rg = (r_cum - g_cum) / (100.0 + g_cum) * d0
    pb = -pb_sum
    delta = d1 - d0
    return Decomposition(
        start=start,
        end=end,
        d_start=d0,
        d_end=d1,
        delta=delta,
        rg=rg,
        pb=pb,
        sfa=delta - rg - pb,
        gap=0.0,
        n_years=end - start,
        n_complete=1,
    )


def split_multi_year(d0: float, r_cum: float, g_cum: float, infl_cum: float) -> RgSplit:
    """decompose_multi_year の (r−g) 項を同じ ln 比の規則で分ける。"""
    i_part = r_cum / (100.0 + g_cum) * d0
    grow = -g_cum / (100.0 + g_cum) * d0
    re, inf = _split_growth(grow, g_cum, infl_cum)
    unsplit = grow if (re == 0.0 and inf == 0.0) else 0.0
    return RgSplit(i_part, re, inf, unsplit)


def unexplained(start: int, end: int, d0: float, d1: float) -> Decomposition:
    """分解しない区間: Δd をすべて gap（帳簿上の消滅）に入れる。"""
    return Decomposition(start, end, d0, d1, d1 - d0, 0.0, 0.0, 0.0, d1 - d0, end - start, 0)


def chain(decs: Sequence[Decomposition]) -> Decomposition:
    """連続する区間の分解を足し合わせる（前の終点 = 次の始点でなければ ValueError）。"""
    if not decs:
        msg = "chain: empty"
        raise ValueError(msg)
    for a, b in itertools.pairwise(decs):
        if a.end != b.start or a.d_end != b.d_start:
            msg = f"chain: not contiguous ({a.end} -> {b.start})"
            raise ValueError(msg)
    return Decomposition(
        start=decs[0].start,
        end=decs[-1].end,
        d_start=decs[0].d_start,
        d_end=decs[-1].d_end,
        delta=sum(x.delta for x in decs),
        rg=sum(x.rg for x in decs),
        pb=sum(x.pb for x in decs),
        sfa=sum(x.sfa for x in decs),
        gap=sum(x.gap for x in decs),
        n_years=sum(x.n_years for x in decs),
        n_complete=sum(x.n_complete for x in decs),
    )


def add_splits(splits: Sequence[RgSplit]) -> RgSplit:
    return RgSplit(
        sum(s.interest for s in splits),
        sum(s.real for s in splits),
        sum(s.inflation for s in splits),
        sum(s.unsplit for s in splits),
    )


@dataclass(frozen=True)
class Shares:
    """低下幅 |Δd| に対する各寄与の割合。正 = 低下に寄与（債務を減らす向き）。和は 1。"""

    inflation: float
    real: float
    interest: float
    unsplit: float
    balance: float
    unexplained: float
    sfa: float

    @property
    def residual(self) -> float:
        """設計書の「残差」= 未分解区間（gap）+ 測った sfa。"""
        return self.unexplained + self.sfa


def shares_of_decline(dec: Decomposition, sp: RgSplit) -> Shares | None:
    """各寄与 ÷ Δd（Δd < 0 のときだけ）。残差は 未分解区間（gap）と 測った sfa に分けて持つ。"""
    if dec.delta >= 0:
        return None
    if abs(sp.total - dec.rg) > 1e-6:
        msg = "shares_of_decline: split does not add up to the (r−g) term"
        raise ValueError(msg)
    dd = dec.delta
    return Shares(
        inflation=sp.inflation / dd,
        real=sp.real / dd,
        interest=sp.interest / dd,
        unsplit=sp.unsplit / dd,
        balance=dec.pb / dd,
        unexplained=dec.gap / dd,
        sfa=dec.sfa / dd,
    )


def judge_h11(sh: Shares) -> str:
    """設計書の 3 条件。順序（補完）: インフレ ≥ 1/2 → 整合、残差 ≥ 1/2 → 中間、
    実質成長か総合収支項がインフレより大きい → 不支持、どれでもない → 中間。"""
    if sh.inflation >= HALF:
        return "整合"
    if sh.residual >= HALF:
        return "中間"
    if max(sh.real, sh.balance) > sh.inflation:
        return "不支持"
    return "中間"


# ---- pure helpers: H12 ---------------------------------------------------------------------------


def r_minus_g(r: Mapping[int, float], g: Mapping[int, float]) -> Series:
    """両方ある年の r − g（pp）。"""
    return {y: r[y] - g[y] for y in sorted(r) if y in g}


def judge_h12(
    rg: Mapping[int, float],
    recent: tuple[int, int] = H12_RECENT,
    base: tuple[int, int] = H12_BASE,
) -> tuple[str, bool, float | None, float | None]:
    """(判定, 各年 r−g<0, recent 平均 g−r, base 平均 g−r)。

    recent の年が 1 つでも欠ければ (a) は満たさない。"""
    years = range(recent[0], recent[1] + 1)
    all_neg = all(y in rg and rg[y] < 0 for y in years)
    gr = {y: -v for y, v in rg.items()}
    m_recent = period_mean(gr, *recent)
    m_base = period_mean(gr, *base)
    wider = m_recent is not None and m_base is not None and m_recent > m_base
    return ("整合" if all_neg and wider else "不支持"), all_neg, m_recent, m_base


# ---- pure helpers: H13 ---------------------------------------------------------------------------


def market_held(debt_gdp: float, boj_share_pct: float) -> float:
    """市中保有の近似 = 総債務 ×（1 − 日銀保有比率）。"""
    return debt_gdp * (1.0 - boj_share_pct / 100.0)


def boj_holdings_gdp(boj_amount: float, ngdp: float) -> float:
    """日銀の国債保有額 ÷ 名目 GDP × 100（同じ通貨単位で渡す）。"""
    return boj_amount / ngdp * 100.0


def judge_h13(values: Mapping[str, float], iso3: str = JP) -> str:
    """日本（市中保有）が 18 か国の中で首位（同値は首位に含む）なら整合、そうでなければ不支持。"""
    return "整合" if rank_desc(values, iso3) == 1 else "不支持"


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any, grid_axis: str = "y") -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=7)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def _footer(fig: Any, text: str) -> None:
    fig.text(0.01, 0.005, text, fontsize=6.5, color=MUTED)


def fig_h11_japan(debt: Mapping[int, float], cpi_level: Mapping[int, float], path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    ys = [y for y in range(1935, 1961)]
    segs: list[list[int]] = [[]]
    for y in ys:
        if y in debt:
            segs[-1].append(y)
        elif segs[-1]:
            segs.append([])
    for k, seg in enumerate(s for s in segs if s):
        ax.plot(
            seg,
            [debt[y] for y in seg],
            color=SERIES[0],
            linewidth=1.8,
            marker="o",
            markersize=3,
            label="一般政府債務 ÷ GDP（左軸、%）" if k == 0 else None,
        )
    ax.axvspan(1944.5, 1945.5, color="#efe7da", linewidth=0)
    ax.text(1945, max(debt.values()) * 0.6, "1945 年\n債務欠損", fontsize=7, color=INK, ha="center")
    for y in (1944, 1946, 1955):
        if y in debt:
            ax.annotate(
                f"{y}: {debt[y]:.1f}%",
                (y, debt[y]),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=7,
                color=INK,
            )
    ax.set_ylabel("一般政府債務の対 GDP 比（%）", fontsize=8, color=INK)
    ax.set_xlabel("年", fontsize=8, color=INK)
    _style(ax)
    ax2 = ax.twinx()
    cy = [y for y in ys if y in cpi_level]
    ax2.plot(
        cy,
        [cpi_level[y] for y in cy],
        color=SERIES[1],
        linewidth=1.4,
        linestyle="--",
        label="CPI 水準（右軸、1935 = 1、対数軸）",
    )
    ax2.set_yscale("log")
    ax2.set_ylabel("CPI（1935 年 = 1、対数軸）", fontsize=8, color=SERIES[1])
    ax2.tick_params(colors=SERIES[1], labelsize=7)
    for side in ("top",):
        ax2.spines[side].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="upper left")
    ax.set_title(
        "H11: 日本の一般政府債務比率と CPI 1935–1960（JST）", fontsize=9.5, color=INK, loc="left"
    )
    _footer(
        fig,
        f"出典: {SRC_JST}。debtgdp・cpi。n = 1 か国 × 26 年（債務は 1945 年欠損）。"
        "CPI は 1935 年 = 1 に基準化。",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h11_decomposition(rows: Sequence[tuple[str, Decomposition, RgSplit]], path: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    comps = (
        ("インフレ寄与（CPI）", SERIES[1]),
        ("実質成長寄与", SERIES[2]),
        ("利子（r = 長期金利）", SERIES[0]),
        ("総合収支項（−Σ 総合収支）", SERIES[3]),
        ("測った sfa（残差）", "#b5b5b5"),
        ("未分解区間 1944→46（残差、1945 年欠損）", "#e3e3e3"),
    )
    vals = np.array(
        [
            [sp.inflation, sp.real + sp.unsplit, sp.interest, dec.pb, dec.sfa, dec.gap]
            for _, dec, sp in rows
        ],
        dtype=float,
    )
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    x = np.arange(len(rows))
    pos_b = np.zeros(len(rows))
    neg_b = np.zeros(len(rows))
    for k, (lab, col) in enumerate(comps):
        v = vals[:, k]
        bottom = np.where(v >= 0, pos_b, neg_b)
        hatch = "////" if k == len(comps) - 1 else None
        ax.bar(x, v, bottom=bottom, color=col, width=0.62, label=lab, hatch=hatch,
               edgecolor=MUTED if hatch else None, linewidth=0.0)  # fmt: skip
        pos_b = pos_b + np.where(v >= 0, v, 0)
        neg_b = neg_b + np.where(v < 0, v, 0)
    ax.scatter(
        x, [dec.delta for _, dec, _ in rows], color=INK, marker="D", s=22, zorder=3, label="Δd"
    )
    for xi, (_, dec, _) in zip(x, rows, strict=True):
        ax.annotate(
            f"Δd {dec.delta:+.1f}",
            (xi, dec.delta),
            xytext=(8, -3),
            textcoords="offset points",
            fontsize=7,
            color=INK,
        )
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for lab, _, _ in rows], fontsize=7.5)
    ax.set_ylabel("債務比率の変化への寄与（%pt）", fontsize=8, color=INK)
    ax.set_title(
        "H11: 債務比率の低下の会計分解（日本 1944→1955 の 2 仕様、英・米 1946→1975）",
        fontsize=9.5,
        color=INK,
        loc="left",
    )
    _style(ax)
    ax.legend(fontsize=7, frameon=False, ncol=3, loc="lower left")
    _footer(
        fig,
        f"出典: {SRC_JST}。Δd = (r−g)/(1+g)·d₋₁ − 総合収支 + sfa を年ごとに積み上げ。"
        "r = 長期金利（代理）、g = 名目 GDP 成長率、成長部分は ln(1+実質):ln(1+CPI) で配分。\n"
        "ハッチ = 1944→46 の未分解区間（1945 年欠損）。どちらの扱いも主としない。"
        "n = 3 か国。",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h12(
    r: Mapping[int, float], g: Mapping[int, float], r_gross: Mapping[int, float], path: Path
) -> None:
    import matplotlib.pyplot as plt

    ys = [y for y in range(2011, 2026) if y in r and y in g]
    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    ax.axvspan(2019.5, 2020.5, color="#f4f4f4", linewidth=0)
    ax.plot(ys, [g[y] for y in ys], color=SERIES[2], linewidth=1.6, marker="o", markersize=3,
            label="名目成長率 g（≈ (1+実質)(1+CPI)−1）")  # fmt: skip
    ax.plot(ys, [r[y] for y in ys], color=SERIES[0], linewidth=1.6, marker="o", markersize=3,
            label="実効金利 r（FM 純利払い ÷ 前年総債務）")  # fmt: skip
    yg = [y for y in ys if y in r_gross]
    ax.plot(yg, [r_gross[y] for y in yg], color=SERIES[0], linewidth=1.1, linestyle="--",
            label="参考: r（OECD グロス利払い ÷ 前年 WEO 総債務、探索的）")  # fmt: skip
    ax.bar(ys, [r[y] - g[y] for y in ys], color=SERIES[1], alpha=0.55, width=0.6,
           label="r − g（純利払いベース）")  # fmt: skip
    ax.axhline(0, color=MUTED, linewidth=0.8)
    for a, b, lab in ((2011, 2019, "2011–19"), (2021, 2025, "2021–25")):
        ax.axvspan(a - 0.5, b + 0.5, ymin=0.97, ymax=1.0, color=MUTED, alpha=0.4, linewidth=0)
        ax.text((a + b) / 2, ax.get_ylim()[1], lab, fontsize=7, color=INK, ha="center", va="top")
    ax.set_xlabel("年（2025 年は一部推計）", fontsize=8, color=INK)
    ax.set_ylabel("% / pp", fontsize=8, color=INK)
    ax.set_title("H12: 日本の実効金利 r と名目成長率 g 2011–2025", fontsize=9.5, color=INK,
                 loc="left")  # fmt: skip
    _style(ax)
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    _footer(fig, f"出典: {SRC_IMF}、{SRC_OECD}。n = 1 か国 × 15 年。")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h13(
    debt: Mapping[str, float],
    boj_share: float,
    year: int,
    path: Path,
    amount_based: float | None = None,
) -> None:
    import matplotlib.pyplot as plt

    order = sorted(debt, key=lambda i: debt[i])
    jp_mkt = market_held(debt[JP], boj_share)
    fig, ax = plt.subplots(figsize=(8.6, 6.4))
    for k, iso in enumerate(order):
        if iso == JP:
            ax.barh(
                k, jp_mkt, color=SERIES[1], height=0.65, label="日本: 市中保有（登録した比率法）"
            )
            ax.barh(k, debt[iso] - jp_mkt, left=jp_mkt, color="#f3c7ae", height=0.65,
                    label=f"日本: 日銀保有分（総債務 × {boj_share:.1f}%）")  # fmt: skip
            ax.text(debt[iso] + 2, k, f"{debt[iso]:.1f}（市中 {jp_mkt:.1f}）", va="center",
                    fontsize=7, color=INK)  # fmt: skip
        else:
            ax.barh(k, debt[iso], color=SERIES[0], height=0.65,
                    label="他国: 総債務（中銀保有は未控除）" if k == 0 else None)  # fmt: skip
            ax.text(debt[iso] + 2, k, f"{debt[iso]:.1f}", va="center", fontsize=7, color=INK)
    ax.axvline(jp_mkt, color=SERIES[1], linewidth=0.8, linestyle=":")
    top = max((i for i in debt if i != JP), key=lambda i: debt[i])
    ax.axvline(debt[top], color=SERIES[0], linewidth=0.8, linestyle="--",
               label=f"他国の最大（{NAMES[top]} {debt[top]:.1f}）")  # fmt: skip
    if amount_based is not None:
        ax.scatter([amount_based], [order.index(JP)], marker="D", color=INK, s=30, zorder=4,
                   label=f"日本: 金額法の市中保有 {amount_based:.1f}（探索的）")  # fmt: skip
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{NAMES[i]}（{i}）" for i in order], fontsize=7.5)
    ax.set_xlabel(f"一般政府総債務の対 GDP 比 {year} 年（%）", fontsize=8, color=INK)
    ax.set_title(
        f"H13: {year} 年の一般政府総債務（18 か国）と、日本の日銀保有分を除いた近似",
        fontsize=9.5,
        color=INK,
        loc="left",
    )
    _style(ax, grid_axis="x")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, fontsize=7, frameon=False, loc="lower right")
    _footer(
        fig,
        f"出典: {SRC_IMF}（{year} 年は一部推計）、\n{SRC_MOF}。日銀比率は国債（国庫短期証券を除く、"
        "財投債を含む）に対する比率で、\n総債務全体に掛けた近似。"
        "他国の中銀保有は未控除。n = 18 か国。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h14(gross: Mapping[str, Series], net_fm: Mapping[str, Series], path: Path) -> None:
    import matplotlib.pyplot as plt

    order = sorted(JST18, key=lambda i: gross[i].get(2024, math.nan))
    fig, ax = plt.subplots(figsize=(8.8, 6.6))
    marks = ((1990, "o", SERIES[0], "グロス 1990"), (2019, "s", SERIES[2], "グロス 2019"),
             (2024, "D", SERIES[1], "グロス 2024"))  # fmt: skip
    for k, iso in enumerate(order):
        vals = [gross[iso][y] for y, *_ in marks if y in gross[iso]]
        ax.plot([min(vals), max(vals)], [k, k], color=GRID, linewidth=2.0, zorder=1)
    for y, mk, col, lab in marks:
        ax.scatter([gross[i].get(y, math.nan) for i in order], range(len(order)), marker=mk,
                   color=col, s=24, zorder=3, label=lab)  # fmt: skip
    ax.scatter([net_fm.get(i, {}).get(2024, math.nan) for i in order], range(len(order)),
               marker="x", color=INK, s=20, zorder=3,
               label="参考: 純利払い 2024（IMF FM、R2 の H5）")  # fmt: skip
    ax.axvline(0, color=MUTED, linewidth=0.8)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{NAMES[i]}（{i}）" for i in order], fontsize=7.5)
    ax.set_xlabel("一般政府の利払い ÷ 名目 GDP（%）", fontsize=8, color=INK)
    ax.set_title("H14: グロス利払い 1990・2019・2024 年（OECD EO、18 か国）", fontsize=9.5,
                 color=INK, loc="left")  # fmt: skip
    _style(ax, grid_axis="x")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    _footer(
        fig,
        f"出典: {SRC_OECD}（GGINTP ÷ GDP）、"
        "IMF Fiscal Monitor（純利払い = 基礎的収支 − 総合収支）。\n"
        "n = 18 か国（独の起点は 1991 年なので 1990 年の点が無い）。"
        "並びは 2024 年のグロス利払いの小さい順。",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- report printing -----------------------------------------------------------------------------


def _f(v: float | None, nd: int = 1) -> str:
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:+.{nd}f}"


def _u(v: float | None, nd: int = 1) -> str:
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def _row(cells: Sequence[object]) -> None:
    print("| " + " | ".join(str(c) for c in cells) + " |")


def _yn(b: bool | None) -> str:
    return "–" if b is None else ("○" if b else "×")


@dataclass(frozen=True)
class Jst:
    d: dict[str, Series]
    r: dict[str, Series]
    g: dict[str, Series]
    pb: dict[str, Series]
    cpi: dict[str, Series]

    def get(self, iso: str) -> tuple[Series, Series, Series, Series, Series]:
        return (
            self.d.get(iso, {}),
            self.r.get(iso, {}),
            self.g.get(iso, {}),
            self.pb.get(iso, {}),
            self.cpi.get(iso, {}),
        )


def _decomp_and_split(j: Jst, iso: str, a: int, b: int) -> tuple[Decomposition, RgSplit]:
    d, r, g, pb, cpi = j.get(iso)
    dec = decompose_jst(d, r, g, pb, a, b)
    sp = split_rg_jst(d, r, g, pb, cpi, a, b)
    assert abs(dec.delta - (dec.rg + dec.pb + dec.sfa + dec.gap)) < 1e-9, iso
    assert abs(sp.total - dec.rg) < 1e-9, iso
    return dec, sp


def _print_dec_row(label: str, dec: Decomposition, sp: RgSplit) -> None:
    _row(
        [
            label, f"{dec.start}→{dec.end}", _u(dec.d_start), _u(dec.d_end), _f(dec.delta),
            _f(sp.inflation), _f(sp.real), _f(sp.unsplit), _f(sp.interest), _f(dec.rg),
            _f(dec.pb), _f(dec.sfa), _f(dec.gap), f"{dec.n_complete}/{dec.n_years}",
        ]
    )  # fmt: skip


def _print_share_row(label: str, sh: Shares | None, judge: str) -> None:
    if sh is None:
        _row([label, "–", "–", "–", "–", "–", "–", "–", "–", "Δd ≥ 0"])
        return
    _row(
        [
            label, _u(sh.inflation, 2), _u(sh.real, 2), _u(sh.interest, 2), _u(sh.unsplit, 2),
            _u(sh.balance, 2), _u(sh.unexplained, 2) if abs(sh.unexplained) > 1e-9 else "–",
            _u(sh.sfa, 2), _u(sh.residual, 2), judge,
        ]
    )  # fmt: skip


@dataclass(frozen=True)
class H11Result:
    main: tuple[Decomposition, RgSplit]
    alt: tuple[Decomposition, RgSplit]
    main_judge: str
    alt_judge: str
    gbr: tuple[Decomposition, RgSplit]
    usa: tuple[Decomposition, RgSplit]


def _h11(j: Jst, gdp_level: Mapping[int, float], cpi_level: Mapping[int, float]) -> H11Result:
    print("\n## H11: 日本 1944 → 1955 年の債務比率低下の分解（JST）")
    d, r, g, pb, cpi = j.get(JP)
    print("\n### 入力（日本、JST）")
    _row(["年", "d（%）", "r = 長期金利", "g = 名目 GDP 成長率", "CPI 上昇率", "総合収支 / GDP"])
    _row(["---"] * 6)
    for y in range(1943, 1956):
        _row([y, _u(d.get(y)), _u(r.get(y), 2), _u(g.get(y)), _u(cpi.get(y)), _f(pb.get(y), 2)])
    print("- 1945 年は債務比率・名目 GDP が欠損。1946 年の名目 GDP 成長率も欠損（前年が無い）。")

    # 1944 → 1946 の 2 通り
    g2 = level_growth(gdp_level[1944], gdp_level[1946])
    pi2 = level_growth(cpi_level[1944], cpi_level[1946])
    r2 = compound([r[1945], r[1946]])
    pb2 = 2.0 * pb[1946]
    real2 = ((1 + g2 / 100) / (1 + pi2 / 100) - 1) * 100
    print("\n### 1944 → 1946 年（1945 年欠損）の扱い")
    print(
        f"- 代替（2 年 1 ステップ）の入力: 名目 GDP 水準比 1946/1944 → G = {g2:.1f}%、"
        f"CPI 水準比 → Π = {pi2:.1f}%、実質 (1+G)/(1+Π)−1 = {real2:.1f}%、"
        f"長期金利 1945・1946 年の複利 R = {r2:.2f}%、総合収支 1946 年 {pb[1946]:+.2f}% × 2 = "
        f"{pb2:+.2f}%（1945 年は欠損）"
    )
    step_main = unexplained(1944, 1946, d[1944], d[1946])
    step_alt = decompose_multi_year(1944, 1946, d[1944], d[1946], r2, g2, pb2)
    sp_alt_step = split_multi_year(d[1944], r2, g2, pi2)
    zero = RgSplit(0.0, 0.0, 0.0, 0.0)
    post_dec, post_sp = _decomp_and_split(j, JP, 1946, 1955)
    main = (chain([step_main, post_dec]), add_splits([zero, post_sp]))
    alt = (chain([step_alt, post_dec]), add_splits([sp_alt_step, post_sp]))
    for dec, sp in (main, alt):
        assert abs(dec.delta - (dec.rg + dec.pb + dec.sfa + dec.gap)) < 1e-9
        assert abs(sp.total - dec.rg) < 1e-9

    print("\n### 分解（pt。負 = 債務比率を下げる向き）")
    _row(
        [
            "仕様", "区間", "d 期首", "d 期末", "Δd", "インフレ", "実質成長", "未配分",
            "利子", "(r−g) 項 計", "総合収支項", "sfa", "分解しない区間", "分解年",
        ]
    )  # fmt: skip
    _row(["---"] * 14)
    _print_dec_row("分解しない: 1944→46", step_main, zero)
    _print_dec_row("2 年 1 ステップ: 1944→46", step_alt, sp_alt_step)
    _print_dec_row("共通: 1946→55 を年ごと", post_dec, post_sp)
    _print_dec_row("**分解しない: 1944→55 計**", *main)
    _print_dec_row("**2 年 1 ステップ: 1944→55 計**", *alt)

    sh_main = shares_of_decline(*main)
    sh_alt = shares_of_decline(*alt)
    sh_post = shares_of_decline(post_dec, post_sp)
    assert sh_main is not None and sh_alt is not None
    jm, ja = judge_h11(sh_main), judge_h11(sh_alt)
    jp_post = "–" if sh_post is None else judge_h11(sh_post)
    print("\n### 低下幅に対する割合（正 = 低下に寄与。和 = 1）")
    _row(["1944→46 年の扱い", "インフレ", "実質成長", "利子", "未配分", "総合収支項",
          "未分解区間（1944→46）", "測った sfa", "残差 計", "判定"])  # fmt: skip
    _row(["---"] * 10)
    _print_share_row("分解しない: 1944→1955", sh_main, jm)
    _print_share_row("2 年 1 ステップ: 1944→1955", sh_alt, ja)
    _print_share_row("参考: 1946→1955 だけ（探索的・事後）", sh_post, jp_post)
    print(
        f"\n- 分解しない: インフレ {sh_main.inflation:.2f}（閾値 0.50）、"
        f"残差 {sh_main.residual:.2f}（閾値 0.50。うち未分解区間 {sh_main.unexplained:.2f}、"
        f"測った sfa {sh_main.sfa:.2f}） → {jm}"
    )
    print(
        f"- 2 年 1 ステップ: インフレ {sh_alt.inflation:.2f}、残差 {sh_alt.residual:.2f}"
        f"（測った sfa のみ） → {ja}"
    )
    print(
        f"- **H11 判定: 1944→46 年の扱いに依存（分解しない: {jm}／2 年 1 ステップ: {ja}）。**"
        "どちらを主にするかの規則は設計書に無かった（設計書の逸脱の記録、2026-11-03）"
    )

    grow_alt = (alt[1].real + alt[1].inflation + alt[1].unsplit) / alt[0].delta
    grow_main = (main[1].real + main[1].inflation + main[1].unsplit) / main[0].delta
    print(
        f"- 探索的・事後: 成長部分全体（名目 GDP の膨張 = 実質成長 + インフレ）の割合は "
        f"分解しない {grow_main:.2f}・"
        "2 年 1 ステップ "
        f"{grow_alt:.2f}。この値は CPI・デフレータのずれによる"
        "実質とインフレの配分に依存しない"
    )

    # 1946 → 1955 の年別
    print("\n### 1946 → 1955 年の年別（日本）")
    _row(["年", "Δd", "インフレ", "実質成長", "利子", "総合収支項", "sfa"])
    _row(["---"] * 7)
    for t in range(1947, 1956):
        dt, st = _decomp_and_split(j, JP, t - 1, t)
        _row([t, _f(dt.delta), _f(st.inflation), _f(st.real + st.unsplit), _f(st.interest),
              _f(dt.pb), _f(dt.sfa + dt.gap)])  # fmt: skip

    # 英・米（記述）
    print("\n### 英国・米国 1946 → 1975 年（記述）")
    _row(
        [
            "国", "区間", "d 期首", "d 期末", "Δd", "インフレ", "実質成長", "未配分",
            "利子", "(r−g) 項 計", "総合収支項", "sfa", "欠損年", "分解年",
        ]
    )  # fmt: skip
    _row(["---"] * 14)
    gbr = _decomp_and_split(j, "GBR", 1946, 1975)
    usa = _decomp_and_split(j, "USA", 1946, 1975)
    _print_dec_row("英（GBR）", *gbr)
    _print_dec_row("米（USA）", *usa)
    _row(
        [
            "国",
            "インフレ",
            "実質成長",
            "利子",
            "未配分",
            "総合収支項",
            "未分解区間",
            "測った sfa",
            "残差 計",
            "（H11 の規則を当てた場合）",
        ]
    )
    _row(["---"] * 10)
    for lab, (dec, sp) in (("英 1946→1975", gbr), ("米 1946→1975", usa)):
        sh = shares_of_decline(dec, sp)
        _print_share_row(lab, sh, "–" if sh is None else judge_h11(sh))
    print("- 英・米は記述（判定しない）。最右列は H11 の規則を機械的に当てた参考。")

    # 探索的: 総合収支を基礎的収支に近似（R1 の impute_primary と同じ式）
    print("\n### 探索的・事後: 総合収支 → 基礎的収支の近似（pb ≈ 総合収支 + r/(1+g)·d₋₁）")
    _row(["国・区間", "Δd", "(r−g) 項", "pb 項", "残差", "インフレ割合", "残差割合", "判定"])
    _row(["---"] * 8)
    for iso, a, b in ((JP, 1946, 1955), ("GBR", 1946, 1975), ("USA", 1946, 1975)):
        d_, r_, g_, pb_, cpi_ = j.get(iso)
        pb_prim = primary_from_overall(d_, r_, g_, pb_)
        dec = decompose_jst(d_, r_, g_, pb_prim, a, b)
        sp = split_rg_jst(d_, r_, g_, pb_prim, cpi_, a, b)
        sh = shares_of_decline(dec, sp)
        _row([f"{NAMES[iso]} {a}→{b}", _f(dec.delta), _f(dec.rg), _f(dec.pb),
              _f(dec.sfa + dec.gap), _u(None if sh is None else sh.inflation, 2),
              _u(None if sh is None else sh.residual, 2),
              "–" if sh is None else judge_h11(sh)])  # fmt: skip
    pb_jp = primary_from_overall(d, r, g, pb)
    # 日本 1944→1955（1944→46 を分解しない扱い）
    if pb_jp:
        dec_p = chain([step_main, decompose_jst(d, r, g, pb_jp, 1946, 1955)])
        sp_p = add_splits([zero, split_rg_jst(d, r, g, pb_jp, cpi, 1946, 1955)])
        sh_p = shares_of_decline(dec_p, sp_p)
        assert sh_p is not None
        print(
            f"- 日本 1944→1955（1944→46 分解しない）に当てると: インフレ {sh_p.inflation:.2f}、"
            f"残差 {sh_p.residual:.2f} → {judge_h11(sh_p)}"
        )

    # 探索的: 1944→1946 の 2 ステップで総合収支を 1946 年 1 回だけにする / 0 にする
    print("\n### 探索的・事後: 2 年 1 ステップの 1944→46 の総合収支の置き方")
    _row(["総合収支の置き方", "インフレ割合", "残差割合", "判定"])
    _row(["---"] * 4)
    for lab, pbx in (("1946 年 × 2（既定）", pb2), ("1946 年 × 1", pb[1946]), ("0", 0.0)):
        stp = decompose_multi_year(1944, 1946, d[1944], d[1946], r2, g2, pbx)
        sh = shares_of_decline(chain([stp, post_dec]), add_splits([sp_alt_step, post_sp]))
        assert sh is not None
        _row([lab, _u(sh.inflation, 2), _u(sh.residual, 2), judge_h11(sh)])
    return H11Result(main, alt, jm, ja, gbr, usa)


def _h12(
    d: Mapping[int, float],
    interest: Mapping[int, float],
    g: Mapping[int, float],
    gross: Mapping[int, float],
) -> tuple[str, Series, Series]:
    print("\n## H12: 日本の r − g 2011–2025（IMF）")
    r = rate_series(d, interest)
    r_g = rate_series(d, gross)
    rg = r_minus_g(r, g)
    rg_g = r_minus_g(r_g, g)
    _row(["年", "d_{t−1}（WEO）", "純利払い / GDP（FM）", "r", "g", "r − g", "r − g < 0",
          "参考: グロス利払い / GDP（OECD）", "参考: r（グロス）",
          "参考: r − g（グロス）"])  # fmt: skip
    _row(["---"] * 10)
    for y in range(2011, 2026):
        mark = "（推計）" if y == ESTIMATE_YEAR else ""
        _row([f"{y}{mark}", _u(d.get(y - 1)), _u(interest.get(y), 2), _u(r.get(y), 2),
              _u(g.get(y), 2), _f(rg.get(y), 2), _yn(rg[y] < 0) if y in rg else "–",
              _u(gross.get(y), 2), _u(r_g.get(y), 2), _f(rg_g.get(y), 2)])  # fmt: skip
    j, all_neg, m_rec, m_base = judge_h12(rg)
    print(
        f"\n- (a) 2021〜2025 の各年 r − g < 0: {_yn(all_neg)}"
        f"（{sum(1 for y in range(2021, 2026) if rg.get(y, 0.0) < 0)} / 5 年）"
    )
    print(
        f"- (b) 平均 (g − r): 2021–25 年 {_u(m_rec, 2)} pp、2011–19 年 {_u(m_base, 2)} pp → "
        f"{_yn(m_rec is not None and m_base is not None and m_rec > m_base)}"
    )
    print(f"- **H12 判定: {j}**")
    print("\n### H12 頑健性（探索的・事後。閾値は固定）")
    _row(["仕様", "(a) 各年 r−g<0", "2021–25 平均 g−r", "2011–19 平均 g−r", "判定"])
    _row(["---"] * 5)
    _row(["主: FM 純利払い、2021–25", _yn(all_neg), _u(m_rec, 2), _u(m_base, 2), j])
    for lab, s, rec in (
        ("2025 年（一部推計）を除く 2021–24", rg, (2021, 2024)),
        ("OECD グロス利払い ÷ 前年 WEO 総債務（副、探索的）", rg_g, H12_RECENT),
        ("OECD グロス、2021–24", rg_g, (2021, 2024)),
    ):
        jj, an, mr, mb = judge_h12(s, recent=rec)
        _row([lab, _yn(an), _u(mr, 2), _u(mb, 2), jj])
    # 年平均の内訳
    m_r = (period_mean(r, *H12_BASE), period_mean(r, *H12_RECENT))
    m_g = (period_mean(g, *H12_BASE), period_mean(g, *H12_RECENT))
    print(
        f"- 平均 r: 2011–19 年 {_u(m_r[0], 2)}%、2021–25 年 {_u(m_r[1], 2)}%。"
        f"平均 g: {_u(m_g[0], 2)}% → {_u(m_g[1], 2)}%"
    )
    return j, r, r_g


def _h13(
    weo: Mapping[str, Series], boj_share: float, boj_amount_oku: float | None,
    jgb_total_oku: float | None, ngdp_jpn: Mapping[int, float],
) -> tuple[str, str]:  # fmt: skip
    print("\n## H13: 日銀保有を除いた市中保有（日本のみ修正）")
    print(f"- 日銀保有比率 s = {boj_share:.1f}%（{SRC_MOF}。国債＝国庫短期証券を除き財投債を含む）")
    out: dict[int, str] = {}
    for y in (H13_YEAR, 2024):
        v = at(weo, y)
        jp_m = market_held(v[JP], boj_share)
        adj = {**v, JP: jp_m}
        j = judge_h13(adj)
        out[y] = j
        tag = "登録した比率法、一部推計" if y == H13_YEAR else "併記"
        print(f"\n### {y} 年（{tag}）")
        print(
            f"- 日本: 総債務 {v[JP]:.1f}% × (1 − {boj_share / 100:.3f}) = 市中保有 {jp_m:.1f}%"
            f"（控除 {v[JP] - jp_m:.1f} pt）"
        )
        _row(["順位", "国", "値（%）", "備考"])
        _row(["---"] * 4)
        for k, iso in enumerate(sorted(adj, key=lambda i: -adj[i]), start=1):
            note = "市中保有（近似）" if iso == JP else "総債務（未修正）"
            name = f"**{NAMES[iso]}（{iso}）**" if iso == JP else f"{NAMES[iso]}（{iso}）"
            if k <= 8 or iso == JP:
                _row([k, name, _u(adj[iso]), note])
        print(f"- 日本の順位: {rank_desc(adj, JP)} / {len(adj)}。**H13 判定（{y} 年）: {j}**")
        top = max((i for i in v if i != JP), key=lambda i: v[i])
        need = 1 - v[top] / v[JP]
        print(
            f"- 日本が首位になる日銀比率の上限（他国未修正のまま）: {need * 100:.1f}%"
            f"（{NAMES[top]} {v[top]:.1f}% を上回る条件）"
        )
    # 探索的: 金額ベース
    print("\n### 探索的・事後: 金額ベースの検算（staged の保有額と OECD の名目 GDP）")
    if boj_amount_oku is not None and jgb_total_oku is not None and H13_YEAR in ngdp_jpn:
        ngdp_oku = ngdp_jpn[H13_YEAR] / 1e8
        boj_gdp = boj_holdings_gdp(boj_amount_oku, ngdp_oku)
        jgb_gdp = boj_holdings_gdp(jgb_total_oku, ngdp_oku)
        v = at(weo, H13_YEAR)
        approx_cut = v[JP] - market_held(v[JP], boj_share)
        alt_m = v[JP] - boj_gdp
        adj = {**v, JP: alt_m}
        top = max((i for i in v if i != JP), key=lambda i: v[i])
        need_gdp = boj_amount_oku / ((v[JP] - v[top]) / 100) / ngdp_oku - 1
        print(
            f"- 日銀の国債保有額 {boj_amount_oku / 1e4:,.1f} 兆円（2026 年 6 月末）÷ 名目 GDP "
            f"{ngdp_oku / 1e4:,.1f} 兆円（OECD、{H13_YEAR} 年）= {boj_gdp:.1f}%。"
            f"国債（T-Bill 除く）全体は {jgb_total_oku / 1e4:,.1f} 兆円 = {jgb_gdp:.1f}%、"
            f"WEO の総債務 {v[JP]:.1f}% との差 {v[JP] - jgb_gdp:.1f} pt は国債以外"
            "（国庫短期証券・地方債・借入金など）と定義差"
        )
        print(
            f"- 比率の近似で差し引いた日銀保有分 {approx_cut:.1f} pt に対し、金額ベースでは "
            f"{boj_gdp:.1f} pt。近似は {approx_cut - boj_gdp:.1f} pt 多く差し引いている"
            "（国債以外の債務にも s を掛けているため）。"
        )
        print(
            f"- 金額ベースの市中保有 {alt_m:.1f}% → 順位 {rank_desc(adj, JP)} / 18"
            f"（{NAMES[top]} {v[top]:.1f}%）→ 規則を当てると {judge_h13(adj)}。"
            f"名目 GDP が {need_gdp * 100:.1f}% 大きければ首位になる"
            "（保有時点と GDP の年のずれへの感度）。"
        )
    else:
        print("- staged の保有額または OECD の名目 GDP が無いので省略")
    return out[H13_YEAR], out[2024]


def _h14(
    gross: Mapping[str, Series], received: Mapping[str, Series], net_oecd: Mapping[str, Series],
    net_fm: Mapping[str, Series],
) -> tuple[str, int, int, int]:  # fmt: skip
    print("\n## H14: OECD グロス利払いで H5 を再判定")
    n_half, n_rose, n_undef = h5_counts(gross)
    j = judge_h5(n_half, n_rose)
    late = {i: base_year(s) for i, s in gross.items() if base_year(s) != H5_START}
    print(
        "- 起点年: 原則 1990 年（R2 と同じ規則: 1990 年以降で最初に値のある年）。1990 年に無い国: "
        + ("、".join(f"{NAMES[i]} {y}" for i, y in sorted(late.items())) or "なし")
    )
    _row(["国", "起点年", "起点", "2007", "2019", "2024", "2025（推計）", "2019 / 起点",
          "2019 ≤ 起点/2", "2024 > 2019", "参考: FM 純 2019", "参考: FM 純 2024"])  # fmt: skip
    _row(["---"] * 12)
    for iso in sorted(JST18, key=lambda i: -gross[i][2024]):
        s = gross[iso]
        b = base_year(s)
        assert b is not None
        h = halved(s[b], s[2019])
        nf = net_fm.get(iso, {})
        name = f"**{NAMES[iso]}（{iso}）**" if iso == JP else f"{NAMES[iso]}（{iso}）"
        _row([name, b, _u(s[b], 2), _u(s.get(2007), 2), _u(s[2019], 2), _u(s[2024], 2),
              _u(s.get(2025), 2), _u(s[2019] / s[b], 2) if s[b] > 0 else "–",
              "定義不能" if h is None else _yn(h),
              _yn(s[2024] > s[2019]), _u(nf.get(2019), 2), _u(nf.get(2024), 2)])  # fmt: skip
    print(f"\n- 前半（2019 ≤ 起点 / 2）: {n_half} / 18（定義不能 {n_undef}）。閾値 ≥ 10")
    print(f"- 後半（2024 > 2019）: {n_rose} / 18。閾値 ≥ 10")
    print(f"- **H14 判定: {j}**")
    fh, fr, _ = h5_counts(net_fm)
    print(
        f"- 比較: R2 の H5（IMF FM 純利払い）: 前半 {fh} / 18、後半 {fr} / 18 → {judge_h5(fh, fr)}"
    )
    med = {
        y: statistics.median(at(gross, y).values()) for y in (1990, 2007, 2019, 2022, 2024, 2025)
    }
    print(
        "- グロス利払いの 18 か国中央値: " + "、".join(f"{y} 年 {v:.2f}%" for y, v in med.items())
    )
    print("\n### H14 頑健性（探索的・事後。閾値 ≥ 10 は固定）")
    _row(["仕様", "前半", "後半", "判定"])
    _row(["---"] * 4)
    _row(
        [
            "主: OECD グロス、起点 1990（独 1991）/ 2019 / 2024",
            f"{n_half} / 18",
            f"{n_rose} / 18",
            j,
        ]
    )
    a, b, _ = h5_counts(gross, late=ESTIMATE_YEAR)
    _row(["OECD グロス、後半 2019 vs 2025（推計）", f"{a} / 18", f"{b} / 18", judge_h5(a, b)])
    a, b, _ = h5_counts(gross, late=2023)
    _row(["OECD グロス、後半 2019 vs 2023", f"{a} / 18", f"{b} / 18", judge_h5(a, b)])
    a, b, _ = h5_counts(gross, mid=2021)
    _row(["OECD グロス、中間年 2021", f"{a} / 18", f"{b} / 18", judge_h5(a, b)])
    a, b, _ = h5_counts(gross, fixed_base=2001)
    _row(["OECD グロス、起点 2001", f"{a} / 18", f"{b} / 18", judge_h5(a, b)])
    a, b, u = h5_counts(net_oecd)
    _row([f"OECD 純利払い（定義不能 {u}）", f"{a} / 18", f"{b} / 18", judge_h5(a, b)])
    _row(["参考: IMF FM 純利払い（R2 の H5 主判定）", f"{fh} / 18", f"{fr} / 18", judge_h5(fh, fr)])

    print("\n### グロスと純の差（利子受取）2024 年")
    _row(
        [
            "国",
            "グロス（OECD）",
            "受取（OECD）",
            "純（OECD）",
            "純（IMF FM）",
            "グロス − 純（OECD）",
        ]
    )
    _row(["---"] * 6)
    for iso in sorted(JST18, key=lambda i: -(gross[i][2024] - net_oecd[i][2024])):
        _row([f"**{NAMES[iso]}**" if iso == JP else NAMES[iso], _u(gross[iso][2024], 2),
              _u(received[iso][2024], 2), _f(net_oecd[iso][2024], 2),
              _f(net_fm.get(iso, {}).get(2024), 2),
              _u(gross[iso][2024] - net_oecd[iso][2024], 2)])  # fmt: skip
    gap = {i: gross[i][2024] - net_oecd[i][2024] for i in JST18}
    neg = [NAMES[i] for i in JST18 if net_oecd[i][2024] < 0]
    print(
        f"- 日本 2024 年: グロス {gross[JP][2024]:.2f}%、受取 {received[JP][2024]:.2f}%、"
        f"純 {net_oecd[JP][2024]:+.2f}%（OECD）。IMF FM の純利払い {net_fm[JP][2024]:+.2f}%。"
        f"グロス − 純 = {gap[JP]:.2f} pt（大きい方から {rank_desc(gap, JP)} 位 / 18）"
    )
    print(f"- OECD で 2024 年の純利払いが負の国: {'、'.join(neg) or 'なし'}")
    jp_yrs = [y for y in sorted(net_oecd[JP]) if net_oecd[JP][y] < 0]
    print(f"- 日本で OECD 純利払いが負の年: {jp_yrs}")
    print(
        f"- 日本のグロス利払い: 1990 年 {gross[JP][1990]:.2f}%、2019 年 {gross[JP][2019]:.2f}%、"
        f"2024 年 {gross[JP][2024]:.2f}%、2025 年 {gross[JP].get(2025, math.nan):.2f}%"
    )
    return j, n_half, n_rose, n_undef


def _coverage(mart: pl.DataFrame) -> None:
    print("\n## データ: 使用系列の国・年の数（JST 18 か国）")
    _row(["source", "unit", "metric", "国・年", "国", "最初の年", "最後の年"])
    _row(["---"] * 7)
    used = (
        ("jst", "general_gov_gross", "debt_gdp"),
        ("jst", "general_gov_gross", "fiscal_balance_gdp"),
        ("jst", "macro", "ltrate"),
        ("jst", "macro", "ngdp_growth"),
        ("jst", "macro", "cpi_inflation"),
        ("imf_weo", "general_gov_gross", "debt_gdp"),
        ("imf_weo", "macro", "rgdp_growth"),
        ("imf_weo", "macro", "cpi_inflation"),
        ("imf_fm", "general_gov_gross", "interest_gdp"),
        ("oecd_eo", "general_gov_gross", "gross_interest_gdp"),
        ("oecd_eo", "general_gov_gross", "interest_received_gdp"),
        ("oecd_eo", "general_gov_gross", "net_interest_gdp"),
        ("mof_holdings", "jgb_holders", "share_boj"),
    )
    for src, unit, metric in used:
        s = series(mart, src, unit, metric, JST18)
        ys = [y for v in s.values() for y in v]
        _row([src, unit, metric, len(ys), len(s), min(ys), max(ys)])


def _read_staged(data_dir: Path) -> tuple[float | None, float | None, Series]:
    """H13 の探索的検算用: 日銀保有額・国債合計（億円）と日本の名目 GDP（円）。"""
    boj = total = None
    p = data_dir / "staged" / "mof" / "jgb_holders.parquet"
    if p.exists():
        h = pl.read_parquet(p).filter(pl.col("instrument") == "jgb")
        total = float(h["amount_oku_yen"].sum())
        b = h.filter(pl.col("holder") == "日本銀行")["amount_oku_yen"]
        boj = float(b[0]) if b.len() == 1 else None
    ngdp: Series = {}
    q = data_dir / "staged" / "oecd" / "eo_interest.parquet"
    if q.exists():
        o = pl.read_parquet(q).filter((pl.col("iso3") == JP) & (pl.col("metric") == "ngdp_lcu"))
        ngdp = {int(y): float(v) for y, v in o.select("year", "value").iter_rows()}
    return boj, total, ngdp


def _jst_levels(data_dir: Path, iso: str) -> tuple[Series, Series]:
    """1944 → 1946 年の代替仕様用: JST の名目 GDP・CPI の水準（staged）。"""
    s = pl.read_parquet(data_dir / "staged" / "jst" / "macrohistory.parquet").filter(
        pl.col("iso3") == iso
    )
    gdp = {int(y): float(v) for y, v in s.select("year", "gdp").iter_rows() if v is not None}
    cpi = {int(y): float(v) for y, v in s.select("year", "cpi").iter_rows() if v is not None}
    return gdp, cpi


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    import matplotlib

    matplotlib.use("Agg")
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = [
        "Hiragino Sans",
        "Noto Sans CJK JP",
        "IPAPGothic",
        "IPAGothic",
        "sans-serif",
    ]
    mart = pl.read_parquet(args.data_dir / "marts" / "public_debt_panel.parquet")
    gg = "general_gov_gross"
    jst = Jst(
        d=series(mart, "jst", gg, "debt_gdp", JST18),
        r=series(mart, "jst", "macro", "ltrate", JST18),
        g=series(mart, "jst", "macro", "ngdp_growth", JST18),
        pb=series(mart, "jst", gg, "fiscal_balance_gdp", JST18),
        cpi=series(mart, "jst", "macro", "cpi_inflation", JST18),
    )
    weo = series(mart, "imf_weo", gg, "debt_gdp", JST18)
    rgdp = series(mart, "imf_weo", "macro", "rgdp_growth", JST18)
    cpi_w = series(mart, "imf_weo", "macro", "cpi_inflation", JST18)
    net_fm = series(mart, "imf_fm", gg, "interest_gdp", JST18)
    gross = series(mart, "oecd_eo", gg, "gross_interest_gdp", JST18)
    received = series(mart, "oecd_eo", gg, "interest_received_gdp", JST18)
    net_oecd = series(mart, "oecd_eo", gg, "net_interest_gdp", JST18)
    boj_share = series(mart, "mof_holdings", "jgb_holders", "share_boj")[JP][2026]
    gdp_lv, cpi_lv = _jst_levels(args.data_dir, JP)
    boj_amt, jgb_total, ngdp_jpn = _read_staged(args.data_dir)

    print("# R4 日本の戦後の債務消滅・r − g・市中保有・グロス利払い（2026-11-03）")
    print(f"- mart: public_debt_panel {mart.height} 行。JST 18 か国のみ使用")
    _coverage(mart)

    h11 = _h11(jst, gdp_lv, cpi_lv)
    g_jp = nominal_growth_series(rgdp[JP], cpi_w[JP])
    j12, r12, r12g = _h12(weo[JP], net_fm[JP], g_jp, gross[JP])
    j13, j13b = _h13(weo, boj_share, boj_amt, jgb_total, ngdp_jpn)
    j14, *_ = _h14(gross, received, net_oecd, net_fm)

    print("\n## 判定のまとめ")
    print(
        f"- H11: 1944→46 年の扱いに依存（分解しない: {h11.main_judge}／2 年 1 ステップ: "
        f"{h11.alt_judge}）/ H12: {j12} / "
        f"H13: {j13}（2024 年 {j13b}）/ H14: {j14}"
    )

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    base = cpi_lv[1935]
    fig_h11_japan(
        {y: v for y, v in jst.d[JP].items() if 1935 <= y <= 1960},
        {y: v / base for y, v in cpi_lv.items() if 1935 <= y <= 1960},
        args.fig_dir / "r4_h11_japan_debt_cpi.png",
    )
    fig_h11_decomposition(
        [
            ("日本 1944→1955\n1944→46 を分解しない", *h11.main),
            ("日本 1944→1955\n1944→46 を 2 年 1 ステップ", *h11.alt),
            ("英 1946→1975", *h11.gbr),
            ("米 1946→1975", *h11.usa),
        ],
        args.fig_dir / "r4_h11_decomposition.png",
    )
    fig_h12(r12, g_jp, r12g, args.fig_dir / "r4_h12_japan_r_g.png")
    amt_m = None
    if boj_amt is not None and H13_YEAR in ngdp_jpn:
        amt_m = weo[JP][H13_YEAR] - boj_holdings_gdp(boj_amt, ngdp_jpn[H13_YEAR] / 1e8)
    fig_h13(
        at(weo, H13_YEAR),
        boj_share,
        H13_YEAR,
        args.fig_dir / "r4_h13_market_held.png",
        amount_based=amt_m,
    )
    fig_h14(gross, net_fm, args.fig_dir / "r4_h14_gross_interest_dots.png")
    print(
        "\n図: r4_h11_japan_debt_cpi.png, r4_h11_decomposition.png, r4_h12_japan_r_g.png, "
        "r4_h13_market_held.png, r4_h14_gross_interest_dots.png"
    )


if __name__ == "__main__":
    main()
