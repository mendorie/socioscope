"""R3: 2010 年代とインフレ期の債務動態・民間から国家へ・利払いの対歳入比（H7〜H10、事後追加）。

事後追加の仮説（design/themes/public-debt.md「事後追加（2026-11-03 夕、R3 …）」節）。R1・R2 の結果を
見た後に立てたもので、判定基準は追加データ（WEO 実質成長率・CPI、FM 歳入）を見る前に設計書で固定。
閾値は設計書のまま:
  H7 : 2010 → 2019 年の Δd を (r−g) 項・pb 項・残差に分解。(a) (r−g) 項 < 0 の国 ≥ 12、かつ
       (b) そのうち pb 項 > 0（基礎的赤字）で |pb 項| ≥ |(r−g) 項| の国 ≥ 10 → 整合。
       (a) を満たし (b) ≤ 9 → 中間。(a) ≤ 11 → 不支持。
  H8 : 2020 → 2024 年。(a) Δd < 0 の国 ≥ 12、(b) 下がった国の中央値で (r−g) 項の寄与 ≥
       低下幅の半分、(c) pb 項 > 0 の国 ≥ 12。3 つ全部で整合、(a) のみ（(a) を満たし
       3 つ全部ではない）→ 中間、(a) ≤ 11 → 不支持。副判定 2019 → 2024。
  H9 : JST 2008 → 2019（日本の民間は 2017 年まで）。公的債務比率が上昇し、かつ民間非金融債務比率の
       変化 < 5 pt の国 ≥ 12 → 整合、≤ 9 → 不支持、10〜11 → 中間（補完）。
  H10: 純利払い ÷ 歳入（%）。(a) 2024 年 ≤ その国の 1990 年代（1990–1999。米は 2001–2004、
       FM が後から始まる国は始点〜1999）の最大値 ÷ 2 の国 ≥ 12 → 整合、≤ 11 → 不支持（補完）。
       基準が 0 以下の国は「半分以下」が定義できないので満たさない側に数え、分母は 18 のまま
       （R2 と同じ規則）。
       (b) 日本の 2024 年の値と順位（記述）。(c) 2025 年（一部推計）で副判定。

債務動態の恒等式（R1 と同じ、値は % 単位）: Δd_t = (r_t − g_t)/(100 + g_t)·d_{t−1} − pb_t + sfa_t。
  d  : IMF WEO 一般政府総債務 / GDP
  r_t: 実効金利 = FM 純利払い_t / d_{t−1} × 100（純利払いなのでグロスより低い → (r−g) 項を
       債務削減側に過大評価する向き）
  g_t: 名目成長率 ≈ (1 + WEO 実質成長率)(1 + WEO CPI インフレ率) − 1（GDP デフレータではない。
       向き不定）
  pb : FM 基礎的財政収支 / GDP（黒字が正。pb 項 = −pb なので赤字なら正 = 債務を増やす向き）
因果は主張しない。「選択で相殺した」は会計上の分解の言い換え。

決定的スクリプト（乱数なし）。入力は data/marts/public_debt_panel.parquet。純粋ヘルパは
tests/test_analysis_r3.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
import math
import statistics
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import polars as pl

from theme_public_debt.analysis.a20261103_r1_debt_history import (
    Decomposition,
    YearObs,
    decompose_debt_change,
)
from theme_public_debt.analysis.a20261103_r2_interest_net_debt import (
    JST18,
    NAMES,
    halved,
    rank_desc,
    series,
)

THEME_DIR = Path(__file__).resolve().parents[3]
SRC_IMF = (
    "IMF World Economic Outlook 2026 年 10 月版（総債務・実質成長率・CPI）／ Fiscal Monitor"
    "（基礎的財政収支・純利払い・歳入）、DataMapper、2026-11-03 取得"
)
SRC_JST = "Jordà–Schularick–Taylor Macrohistory Database R6（CC BY-NC-SA 4.0、2026-11-03 取得）"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"

MAJORITY = 10  # 18 の過半
TWO_THIRDS = 12  # 18 の 2/3
H9_PRIV_LIMIT = 5.0  # 民間の上昇 < 5 pt
H10_LATE_START = {"USA": (2001, 2004)}  # 設計書: 米国は 2001–2004
H10_DECADE = (1990, 1999)
ESTIMATE_YEAR = 2025

Series = dict[int, float]

# ---- pure helpers: debt dynamics -----------------------------------------------------------------


def nominal_growth(rgdp: float, cpi: float) -> float:
    """名目成長率の近似（%）: (1 + 実質成長率)(1 + CPI インフレ率) − 1。"""
    return ((1.0 + rgdp / 100.0) * (1.0 + cpi / 100.0) - 1.0) * 100.0


def nominal_growth_series(rgdp: Mapping[int, float], cpi: Mapping[int, float]) -> Series:
    """両方ある年だけ名目成長率（%）を返す。"""
    return {y: nominal_growth(rgdp[y], cpi[y]) for y in sorted(rgdp) if y in cpi}


def effective_rate(interest: float, d_prev: float) -> float | None:
    """実効金利（%）= 純利払い_t（% GDP）÷ 債務_{t−1}（% GDP）× 100。d_prev ≤ 0 は定義しない。"""
    if d_prev <= 0:
        return None
    return interest / d_prev * 100.0


def build_obs(
    d: Mapping[int, float],
    interest: Mapping[int, float],
    g: Mapping[int, float],
    pb: Mapping[int, float],
    years: Iterable[int],
) -> list[YearObs]:
    """R1 の YearObs（d, r, g, pb）を作る。r_t は interest_t / d_{t−1}。入力が欠ければ None。"""
    out: list[YearObs] = []
    for y in years:
        r: float | None = None
        if y in interest and (y - 1) in d:
            r = effective_rate(interest[y], d[y - 1])
        out.append(YearObs(y, d.get(y), r, g.get(y), pb.get(y)))
    return out


def decompose(
    d: Mapping[int, float],
    interest: Mapping[int, float],
    g: Mapping[int, float],
    pb: Mapping[int, float],
    start: int,
    end: int,
) -> Decomposition:
    """start → end 年の Δd を (r−g) 項・pb 項（= −Σpb）・sfa・gap に分解（R1 の恒等式を積み上げ）。

    Δd = rg + pb + sfa + gap が必ず閉じる。gap は入力が欠けて分解できない年の Δd の合計。
    """
    return decompose_debt_change(build_obs(d, interest, g, pb, range(start, end + 1)), start, end)


def split_rg(
    d: Mapping[int, float],
    interest: Mapping[int, float],
    rgdp: Mapping[int, float],
    cpi: Mapping[int, float],
    start: int,
    end: int,
) -> tuple[float, float, float]:
    """(r−g) 項を 利子・実質成長・インフレ に分ける（探索的）。

    (r − g)/(100 + g)·d₋₁ = r/(100 + g)·d₋₁ − g/(100 + g)·d₋₁。後者を ln(1+γ) : ln(1+π) の比で
    実質成長と CPI インフレに配分する（g = 0 の年は 0）。全入力が揃う年だけ足す。
    """
    i_part = real_part = infl_part = 0.0
    for t in range(start + 1, end + 1):
        if not all(t in s for s in (interest, rgdp, cpi)) or t - 1 not in d or t not in d:
            continue
        if d[t - 1] <= 0:
            continue
        g = nominal_growth(rgdp[t], cpi[t])
        i_part += interest[t] * 100.0 / (100.0 + g)
        grow = -g / (100.0 + g) * d[t - 1]
        lg = math.log1p(g / 100.0)
        if lg == 0.0:
            continue
        w_real = math.log1p(rgdp[t] / 100.0) / lg
        real_part += grow * w_real
        infl_part += grow * (1.0 - w_real)
    return i_part, real_part, infl_part


def period_mean(s: Mapping[int, float], a: int, b: int) -> float | None:
    """a〜b 年（両端含む）の値のある年の平均。1 年も無ければ None。"""
    vals = [s[y] for y in range(a, b + 1) if y in s]
    return sum(vals) / len(vals) if vals else None


def rate_exposure(
    d: Mapping[int, float],
    interest: Mapping[int, float],
    g: Mapping[int, float],
    pb: Mapping[int, float],
    start: int,
    end: int,
) -> float:
    """Σ d_{t−1}/(100 + g_t)（decompose が分解する年だけ）。r を毎年 x pp 上乗せすると
    (r−g) 項は x × この値だけ増える。"""
    total = 0.0
    for t in range(start + 1, end + 1):
        if all(t in s for s in (d, interest, g, pb)) and (t - 1) in d and d[t - 1] > 0:
            total += d[t - 1] / (100.0 + g[t])
    return total


def rg_breakeven(dec: Decomposition, exposure: float) -> float | None:
    """(r−g) 項の符号が反転する r の一律上乗せ（年平均 pp）= −rg ÷ exposure。

    正なら「r がこれだけ高ければ (r−g) 項は 0」。純利払いによる r の過小評価への感度を見る。
    """
    if exposure <= 0:
        return None
    return -dec.rg / exposure


def shift_rate(dec: Decomposition, pp: float, exposure: float) -> Decomposition:
    """r を毎年 pp だけ上乗せした分解。(r−g) 項に pp × exposure を足し、sfa から同じだけ引く
    （Δd と pb 項は不変、恒等式は閉じたまま）。"""
    add = pp * exposure
    return replace(dec, rg=dec.rg + add, sfa=dec.sfa - add)


def rate_series(d: Mapping[int, float], interest: Mapping[int, float]) -> Series:
    """実効金利 r_t（%）の年系列。"""
    out: Series = {}
    for y in sorted(interest):
        if (y - 1) in d:
            r = effective_rate(interest[y], d[y - 1])
            if r is not None:
                out[y] = r
    return out


# ---- H7 / H8 -------------------------------------------------------------------------------------


def h7_flags(dec: Decomposition) -> tuple[bool, bool]:
    """(a) (r−g) 項 < 0。(b) (a) かつ pb 項 > 0（基礎的赤字）かつ |pb 項| ≥ |(r−g) 項|。"""
    a = dec.rg < 0
    b = a and dec.pb > 0 and abs(dec.pb) >= abs(dec.rg)
    return a, b


def judge_h7(n_rg_negative: int, n_offset: int) -> str:
    """(a) ≤ 11 → 不支持。(a) ≥ 12 かつ (b) ≥ 10 → 整合。(a) ≥ 12 かつ (b) ≤ 9 → 中間。"""
    if n_rg_negative < TWO_THIRDS:
        return "不支持"
    return "整合" if n_offset >= MAJORITY else "中間"


def rg_share_of_decline(dec: Decomposition) -> float | None:
    """債務比率が下がった国について (r−g) 項 ÷ Δd（低下幅のうち (r−g) 項が説明する割合）。

    Δd ≥ 0 なら None。(r−g) 項が正（債務を増やす向き）なら負の値になる。
    """
    if dec.delta >= 0:
        return None
    return dec.rg / dec.delta


def judge_h8(n_declined: int, median_share: float | None, n_pb_positive: int) -> str:
    """(a) ≤ 11 → 不支持。(a)(b)(c) 全部 → 整合。(a) を満たし全部ではない → 中間。"""
    if n_declined < TWO_THIRDS:
        return "不支持"
    b = median_share is not None and median_share >= 0.5
    c = n_pb_positive >= TWO_THIRDS
    return "整合" if b and c else "中間"


# ---- H9 ------------------------------------------------------------------------------------------


def last_at_or_before(s: Mapping[int, float], year: int) -> int | None:
    """year 以前で値のある最後の年。"""
    ys = [y for y in s if y <= year]
    return max(ys) if ys else None


def change(s: Mapping[int, float], start: int, end: int) -> tuple[int, float] | None:
    """start → end（end が無ければ end 以前の最終観測年）の変化（pt）と使った終点。"""
    e = last_at_or_before(s, end)
    if start not in s or e is None or e <= start:
        return None
    return e, s[e] - s[start]


def h9_hit(gov_change: float, priv_change: float, limit: float = H9_PRIV_LIMIT) -> bool:
    """公的債務比率が上昇し、かつ民間非金融債務比率の変化が limit 未満（低下を含む）。"""
    return gov_change > 0 and priv_change < limit


def judge_h9(n_hit: int) -> str:
    """≥ 12 整合、≤ 9 不支持、10〜11 は中間（設計書に無い間の扱い、補完）。"""
    if n_hit >= TWO_THIRDS:
        return "整合"
    if n_hit < MAJORITY:
        return "不支持"
    return "中間"


# ---- H10 -----------------------------------------------------------------------------------------


def interest_to_revenue(interest: Mapping[int, float], revenue: Mapping[int, float]) -> Series:
    """純利払い ÷ 歳入 × 100（%）。歳入 ≤ 0 の年は落とす。"""
    return {
        y: interest[y] / revenue[y] * 100.0
        for y in sorted(interest)
        if y in revenue and revenue[y] > 0
    }


def base_window(iso: str, s: Mapping[int, float]) -> tuple[int, int] | None:
    """H10 の基準期間。原則 1990–1999、米は 2001–2004、後から始まる国は始点〜1999。"""
    if iso in H10_LATE_START:
        return H10_LATE_START[iso]
    if not s:
        return None
    lo = max(H10_DECADE[0], min(s))
    return None if lo > H10_DECADE[1] else (lo, H10_DECADE[1])


def window_max(s: Mapping[int, float], window: tuple[int, int]) -> tuple[int, float] | None:
    """窓内の最大値（年, 値）。同値は早い年。"""
    best: tuple[int, float] | None = None
    for y in range(window[0], window[1] + 1):
        if y in s and (best is None or s[y] > best[1]):
            best = (y, s[y])
    return best


def judge_h10(n_halved: int) -> str:
    """≥ 12 整合、≤ 11 不支持（設計書は整合の条件のみ。満たさない場合を不支持とする補完）。"""
    return "整合" if n_halved >= TWO_THIRDS else "不支持"


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


def fig_decomposition(
    panels: Sequence[tuple[str, Mapping[str, Decomposition]]], order: Sequence[str], path: Path
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(len(panels), 1, figsize=(11.0, 3.4 * len(panels)), sharex=True)
    comps = (
        ("(r−g) 項（実効金利 − 名目成長）", SERIES[0]),
        ("pb 項（= −基礎的財政収支。正 = 赤字で債務増）", SERIES[1]),
        ("残差（sfa + 欠損年）", "#b5b5b5"),
    )
    x = np.arange(len(order))
    for ax, (title, dmap) in zip(axes, panels, strict=True):
        vals = np.array(
            [[dmap[i].rg, dmap[i].pb, dmap[i].sfa + dmap[i].gap] for i in order], dtype=float
        )
        pos_bottom = np.zeros(len(order))
        neg_bottom = np.zeros(len(order))
        for k, (lab, col) in enumerate(comps):
            v = vals[:, k]
            bottom = np.where(v >= 0, pos_bottom, neg_bottom)
            ax.bar(x, v, bottom=bottom, color=col, width=0.7, label=lab)
            pos_bottom = pos_bottom + np.where(v >= 0, v, 0)
            neg_bottom = neg_bottom + np.where(v < 0, v, 0)
        ax.scatter(
            x, [dmap[i].delta for i in order], color=INK, marker="D", s=18, zorder=3, label="Δd"
        )
        ax.axhline(0, color=MUTED, linewidth=0.8)
        ax.set_ylabel("債務比率の変化への寄与（%pt）", fontsize=8, color=INK)
        ax.set_title(title, fontsize=9.5, color=INK, loc="left")
        _style(ax)
        ax.legend(fontsize=7, frameon=False, ncol=4, loc="lower right", bbox_to_anchor=(1.0, 1.0))
    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels([f"{NAMES[i]}\n{i}" for i in order], fontsize=7)
    _footer(
        fig,
        f"出典: {SRC_IMF}。\nΔd = (r−g)/(1+g)·d₋₁ − pb + sfa を年ごとに積み上げ。"
        "r = 純利払い ÷ 前年総債務、g ≈ (1+実質成長率)(1+CPI)−1、"
        "pb = FM 基礎的財政収支。n = 18 か国。",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h9(rows: Sequence[tuple[str, float, float, int]], path: Path) -> None:
    """rows: (iso3, 民間の変化, 公的の変化, 民間の終点年)。"""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.6, 6.0))
    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    lo_x, hi_x = min([*xs, 0.0]) - 8, max([*xs, H9_PRIV_LIMIT]) + 8
    lo_y, hi_y = min([*ys, 0.0]) - 8, max(ys) + 8
    ax.axvspan(lo_x, H9_PRIV_LIMIT, ymin=(0 - lo_y) / (hi_y - lo_y), color="#eef4fb", linewidth=0)
    ax.axvline(H9_PRIV_LIMIT, color=MUTED, linewidth=0.8, linestyle="--")
    ax.axvline(0, color=MUTED, linewidth=0.6)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    for iso, xv, yv, e in rows:
        col = SERIES[1] if iso == JP else SERIES[0]
        ax.scatter([xv], [yv], color=col, s=26, zorder=3)
        lab = f"{NAMES[iso]}" + ("（民間 2008→2017）" if e != 2019 else "")
        ax.annotate(lab, (xv, yv), xytext=(4, 3), textcoords="offset points", fontsize=7, color=INK)
    ax.set_xlim(lo_x, hi_x)
    ax.set_ylim(lo_y, hi_y)
    ax.set_xlabel("民間非金融債務の対 GDP 比の変化 2008→2019（pt）", fontsize=8, color=INK)
    ax.set_ylabel("一般政府債務の対 GDP 比の変化 2008→2019（pt）", fontsize=8, color=INK)
    ax.set_title(
        "H9: 公的債務と民間債務の変化（JST 18 か国）。網掛け = 公的が上昇 かつ 民間 < +5 pt",
        fontsize=9,
        color=INK,
        loc="left",
    )
    _style(ax, grid_axis="both")
    _footer(
        fig,
        f"出典: {SRC_JST}。民間 = 銀行貸出（tloans）÷ GDP。日本の民間は 2017 年まで。"
        f"n = {len(rows)}。",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h10(
    ratio: Mapping[str, Series], bases: Mapping[str, tuple[int, float]], path: Path
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 6, figsize=(12.5, 6.6), sharex=True, sharey=True)
    for ax, iso in zip(axes.flat, JST18, strict=True):
        s = ratio.get(iso, {})
        ys = [y for y in sorted(s) if 1990 <= y <= ESTIMATE_YEAR]
        col = SERIES[1] if iso == JP else SERIES[0]
        ax.plot(
            [y for y in ys if y < ESTIMATE_YEAR],
            [s[y] for y in ys if y < ESTIMATE_YEAR],
            color=col,
            linewidth=1.6 if iso == JP else 1.1,
        )
        if ESTIMATE_YEAR in s and ESTIMATE_YEAR - 1 in s:
            ax.plot(
                [ESTIMATE_YEAR - 1, ESTIMATE_YEAR],
                [s[ESTIMATE_YEAR - 1], s[ESTIMATE_YEAR]],
                color=col,
                linewidth=1.1,
                linestyle=":",
            )
        if iso in bases:
            by, bv = bases[iso]
            ax.scatter([by], [bv], color=INK, s=10, zorder=3)
            if bv > 0:
                ax.axhline(bv / 2, color=MUTED, linewidth=0.7, linestyle="--")
        if 2024 in s:
            ax.scatter([2024], [s[2024]], color=SERIES[2], s=12, zorder=3)
        ax.axhline(0, color=MUTED, linewidth=0.5)
        ax.set_title(f"{NAMES[iso]}（{iso}）", fontsize=8, color=INK, loc="left")
        _style(ax)
    for ax in axes[:, 0]:
        ax.set_ylabel("純利払い ÷ 歳入（%）", fontsize=7, color=INK)
    fig.suptitle(
        "H10: 一般政府の純利払い ÷ 歳入 1990–2025（18 か国）。"
        "黒点 = 1990 年代（米 2001–04）の最大、破線 = その半分、"
        "緑点 = 2024 年、点線 = 2025 年（一部推計）",
        fontsize=9,
        color=INK,
        x=0.01,
        ha="left",
    )
    _footer(
        fig,
        "出典: IMF Fiscal Monitor（純利払い = 基礎的財政収支 − 総合収支、歳入 GGR_G01_GDP_PT）、"
        "DataMapper 2026-11-03 取得。負値 = 純利子受取。n = 18 か国。",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
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
    return "定義不能" if b is None else ("○" if b else "×")


@dataclass(frozen=True)
class Inputs:
    d: dict[str, Series]
    interest: dict[str, Series]
    pb: dict[str, Series]
    rgdp: dict[str, Series]
    cpi: dict[str, Series]
    g: dict[str, Series]
    revenue: dict[str, Series]


def _decs(
    inp: Inputs, start: int, end: int, g: Mapping[str, Series] | None = None
) -> dict[str, Decomposition]:
    gg = inp.g if g is None else g
    return {
        iso: decompose(
            inp.d.get(iso, {}), inp.interest.get(iso, {}), gg.get(iso, {}), inp.pb.get(iso, {}),
            start, end,
        )
        for iso in JST18
    }  # fmt: skip


def _check_identity(decs: Mapping[str, Decomposition]) -> None:
    for iso, dec in decs.items():
        assert abs(dec.delta - (dec.rg + dec.pb + dec.sfa + dec.gap)) < 1e-9, iso


def _h7_counts(decs: Mapping[str, Decomposition]) -> tuple[int, int]:
    fl = [h7_flags(dec) for dec in decs.values()]
    return sum(a for a, _ in fl), sum(b for _, b in fl)


def _h8_stats(decs: Mapping[str, Decomposition]) -> tuple[int, float | None, float | None, int]:
    """(低下国数, 低下国の rg / Δd の中央値, 中央値 rg ÷ 中央値 Δd（別読み）, pb 項 > 0 の国数)。"""
    down = [dec for dec in decs.values() if dec.delta < 0]
    shares = [s for s in (rg_share_of_decline(dec) for dec in down) if s is not None]
    med_share = statistics.median(shares) if shares else None
    alt = (
        statistics.median([d.rg for d in down]) / statistics.median([d.delta for d in down])
        if down
        else None
    )
    n_pb = sum(dec.pb > 0 for dec in decs.values())
    return len(down), med_share, alt, n_pb


def _print_decomp_table(
    inp: Inputs, decs: Mapping[str, Decomposition], a: int, b: int, h: str
) -> None:
    _row(
        [
            "国", "d 期首", "d 期末", "Δd", "(r−g) 項", "pb 項", "残差", "うち欠損年",
            "分解年", f"r 平均 {a}–{b}", f"g 平均 {a}–{b}", f"pb 平均 {a}–{b}",
            "(a) rg<0" if h == "H7" else "Δd<0", "(b) 相殺" if h == "H7" else "rg/Δd",
        ]
    )  # fmt: skip
    _row(["---"] * 14)
    order = sorted(JST18, key=lambda i: decs[i].delta, reverse=True)
    for iso in order:
        dec = decs[iso]
        r = period_mean(rate_series(inp.d.get(iso, {}), inp.interest.get(iso, {})), a, b)
        g = period_mean(inp.g.get(iso, {}), a, b)
        pbm = period_mean(inp.pb.get(iso, {}), a, b)
        if h == "H7":
            fa, fb = h7_flags(dec)
            c1, c2 = _yn(fa), _yn(fb)
        else:
            c1 = _yn(dec.delta < 0)
            sh = rg_share_of_decline(dec)
            c2 = "–" if sh is None else f"{sh:.2f}"
        name = f"**{NAMES[iso]}（{iso}）**" if iso == JP else f"{NAMES[iso]}（{iso}）"
        _row(
            [
                name, _u(dec.d_start), _u(dec.d_end), _f(dec.delta), _f(dec.rg), _f(dec.pb),
                _f(dec.sfa + dec.gap), _f(dec.gap), f"{dec.n_complete}/{dec.n_years}",
                _u(r, 2), _u(g, 2), _f(pbm, 2), c1, c2,
            ]
        )  # fmt: skip
    print("\n単位: d・Δd・各項は対 GDP 比 %（pt）。r・g は % 年率、pb は対 GDP %（黒字が正）。")


def _print_medians(decs: Mapping[str, Decomposition]) -> None:
    def med(f: Callable[[Decomposition], float]) -> float:
        return statistics.median([f(d) for d in decs.values()])

    print(
        f"- 18 か国中央値: Δd {med(lambda d: d.delta):+.1f}、(r−g) 項 {med(lambda d: d.rg):+.1f}、"
        f"pb 項 {med(lambda d: d.pb):+.1f}、残差 {med(lambda d: d.sfa + d.gap):+.1f}"
    )
    rg_neg = sum(d.rg < 0 for d in decs.values())
    pb_pos = sum(d.pb > 0 for d in decs.values())
    big_res = [i for i, d in decs.items() if abs(d.sfa + d.gap) > max(abs(d.rg), abs(d.pb))]
    print(f"- (r−g) 項 < 0: {rg_neg} / 18、pb 項 > 0（基礎的赤字の累積）: {pb_pos} / 18")
    print(
        f"- 残差が (r−g) 項と pb 項のどちらよりも大きい国: {len(big_res)}"
        + (f"（{'、'.join(NAMES[i] for i in big_res)}）" if big_res else "")
    )
    print("- 恒等式の検算: 全 18 か国で |Δd − (rg + pb + sfa + gap)| < 1e-9（assert 済み）")


def _print_split(inp: Inputs, a: int, b: int) -> None:
    print(
        f"\n探索的（事後）: (r−g) 項の内訳 {a}→{b}（利子 / 実質成長 / CPI インフレ、ln 比で配分）"
    )
    _row(["国", "利子", "実質成長", "インフレ", "計 = (r−g) 項"])
    _row(["---"] * 5)
    tot = [0.0, 0.0, 0.0]
    parts: dict[str, tuple[float, float, float]] = {}
    for iso in JST18:
        p = split_rg(
            inp.d.get(iso, {}), inp.interest.get(iso, {}), inp.rgdp.get(iso, {}),
            inp.cpi.get(iso, {}), a, b,
        )  # fmt: skip
        parts[iso] = p
        _row([NAMES[iso], _f(p[0]), _f(p[1]), _f(p[2]), _f(sum(p))])
    for k in range(3):
        tot[k] = statistics.median([parts[i][k] for i in JST18])
    print(f"- 中央値: 利子 {tot[0]:+.1f}、実質成長 {tot[1]:+.1f}、インフレ {tot[2]:+.1f}（pt）")


def _h7(inp: Inputs) -> tuple[dict[str, Decomposition], str]:
    print("\n## H7: 2010 → 2019 年の分解")
    decs = _decs(inp, 2010, 2019)
    _check_identity(decs)
    _print_decomp_table(inp, decs, 2011, 2019, "H7")
    n_a, n_b = _h7_counts(decs)
    j = judge_h7(n_a, n_b)
    a_list = [NAMES[i] for i in JST18 if h7_flags(decs[i])[0]]
    b_list = [NAMES[i] for i in JST18 if h7_flags(decs[i])[1]]
    print(f"- (a) (r−g) 項 < 0: {n_a} / 18（{'、'.join(a_list)}）。閾値 ≥ 12")
    print(
        f"- (b) そのうち pb 項 > 0 かつ |pb| ≥ |rg|: {n_b} / 18（{'、'.join(b_list)}）。閾値 ≥ 10"
    )
    a_not_b = [
        f"{NAMES[i]}（pb {decs[i].pb:+.1f} / rg {decs[i].rg:+.1f}）"
        for i in JST18
        if h7_flags(decs[i])[0] and not h7_flags(decs[i])[1]
    ]
    print(f"- (a) だが (b) でない国: {'、'.join(a_not_b) if a_not_b else 'なし'}")
    _print_medians(decs)
    print(f"- **H7 判定: {j}**")
    _print_rate_sensitivity(inp, decs)
    _print_split(inp, 2010, 2019)
    return decs, j


def _exposure(inp: Inputs, iso: str, a: int, b: int) -> float:
    return rate_exposure(
        inp.d.get(iso, {}), inp.interest.get(iso, {}), inp.g.get(iso, {}), inp.pb.get(iso, {}),
        a, b,
    )  # fmt: skip


def _print_rate_sensitivity(inp: Inputs, decs: Mapping[str, Decomposition]) -> None:
    print(
        "\n探索的（事後）: 純利払いによる r の過小評価への感度 2010→2019"
        "（(r−g) 項が 0 になる r の一律上乗せ、年平均 pp。小さい順）"
    )
    _row(["国", "(r−g) 項", "Σ d₋₁/(100+g)", "損益分岐 pp", "(a)", "(b)"])
    _row(["---"] * 6)
    exp = {i: _exposure(inp, i, 2010, 2019) for i in JST18}
    be = {i: rg_breakeven(decs[i], exp[i]) for i in JST18}

    def _key(i: str) -> float:
        v = be[i]
        return math.inf if v is None else v

    for iso in sorted(JST18, key=_key):
        fa, fb = h7_flags(decs[iso])
        _row([NAMES[iso], _f(decs[iso].rg), _u(exp[iso], 2), _f(be[iso], 2), _yn(fa), _yn(fb)])
    print("- r を全国・全年で一律に上乗せしたときの H7（探索的・事後。閾値は固定）")
    _row(["上乗せ pp", "(a)", "(b)", "判定"])
    _row(["---"] * 4)
    for pp in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
        shifted = {i: shift_rate(decs[i], pp, exp[i]) for i in JST18}
        n_a, n_b = _h7_counts(shifted)
        _row([f"{pp:.2f}", f"{n_a} / 18", f"{n_b} / 18", judge_h7(n_a, n_b)])


def _h8(inp: Inputs, start: int, label: str) -> tuple[dict[str, Decomposition], str]:
    print(f"\n## H8{label}: {start} → 2024 年の分解")
    decs = _decs(inp, start, 2024)
    _check_identity(decs)
    _print_decomp_table(inp, decs, start + 1, 2024, "H8")
    n_down, med_share, alt, n_pb = _h8_stats(decs)
    j = judge_h8(n_down, med_share, n_pb)
    down = [NAMES[i] for i in JST18 if decs[i].delta < 0]
    print(f"- (a) Δd < 0: {n_down} / 18（{'、'.join(down)}）。閾値 ≥ 12")
    print(
        f"- (b) 下がった国の (r−g) 項 ÷ Δd の中央値: {_u(med_share, 2)}（閾値 ≥ 0.50）。"
        f"別読み（中央値 rg ÷ 中央値 Δd）: {_u(alt, 2)}"
    )
    res_add = [(d.rg + d.sfa + d.gap) / d.delta for d in decs.values() if d.delta < 0]
    if res_add:
        print(
            "  - 探索的（事後）: 残差をすべて (r−g) 項に足した比の中央値: "
            f"{statistics.median(res_add):.2f}"
        )
        exp = {i: _exposure(inp, i, start, 2024) for i in JST18}
        for pp in (0.5, 1.0):
            sh = [
                rg_share_of_decline(shift_rate(decs[i], pp, exp[i]))
                for i in JST18
                if decs[i].delta < 0
            ]
            vals = [v for v in sh if v is not None]
            print(
                f"  - 探索的（事後）: r を一律 +{pp:.1f} pp 上乗せした比の中央値: "
                f"{statistics.median(vals):.2f}"
            )
    pbpos = [NAMES[i] for i in JST18 if decs[i].pb > 0]
    print(f"- (c) pb 項 > 0（基礎的赤字の累積）: {n_pb} / 18（{'、'.join(pbpos)}）。閾値 ≥ 12")
    _print_medians(decs)
    print(f"- **H8{label} 判定: {j}**")
    _print_split(inp, start, 2024)
    return decs, j


def _robust_decomp(inp: Inputs, g_jst: Mapping[str, Series]) -> None:
    print("\n## 頑健性（H7・H8、探索的・事後。判定の閾値は固定）")
    _row(["仮説", "仕様", "(a)", "(b)", "(c)", "判定"])
    _row(["---"] * 6)
    for a, b in ((2010, 2019), (2009, 2019), (2011, 2019), (2012, 2019)):
        decs = _decs(inp, a, b)
        _check_identity(decs)
        n_a, n_b = _h7_counts(decs)
        tag = "主" if (a, b) == (2010, 2019) else "探索的・事後"
        _row(["H7", f"{a}→{b}（{tag}）", f"{n_a} / 18", f"{n_b} / 18", "–", judge_h7(n_a, n_b)])
    decs = _decs(inp, 2010, 2019, g=g_jst)
    n_a, n_b = _h7_counts(decs)
    n_cov = sum(d.n_complete == d.n_years for d in decs.values())
    _row(
        [
            "H7",
            f"g = JST 名目 GDP 成長率（探索的・事後。全年分解できた国 {n_cov} / 18）",
            f"{n_a} / 18",
            f"{n_b} / 18",
            "–",
            judge_h7(n_a, n_b),
        ]
    )
    # (b) を |pb| ≥ |rg| 抜きで（pb 項 > 0 だけ）
    decs = _decs(inp, 2010, 2019)
    n_pbpos_in_a = sum(d.rg < 0 and d.pb > 0 for d in decs.values())
    n_a, _ = _h7_counts(decs)
    _row(
        [
            "H7",
            "(b) を「pb 項 > 0」だけにする（探索的・事後）",
            f"{n_a} / 18",
            f"{n_pbpos_in_a} / 18",
            "–",
            judge_h7(n_a, n_pbpos_in_a),
        ]
    )
    for a, b, tag in (
        (2020, 2024, "主"),
        (2019, 2024, "副判定（事前登録）"),
        (2021, 2024, "探索的・事後"),
        (2022, 2024, "探索的・事後"),
        (2020, 2025, "2025 年は一部推計、探索的・事後"),
        (2019, 2025, "2025 年は一部推計、探索的・事後"),
    ):
        decs = _decs(inp, a, b)
        _check_identity(decs)
        n_down, med_share, alt, n_pb = _h8_stats(decs)
        _row(
            [
                "H8",
                f"{a}→{b}（{tag}）",
                f"{n_down} / 18",
                f"{_u(med_share, 2)}（別読み {_u(alt, 2)}）",
                f"{n_pb} / 18",
                judge_h8(n_down, med_share, n_pb),
            ]
        )
    decs = _decs(inp, 2019, 2020, g=g_jst)
    n_cov = sum(d.n_complete == d.n_years for d in decs.values())
    print(
        "\n（参考: JST の g は 2020 年で終わるので H8 には使えない。"
        f"2019→2020 で分解できた国 {n_cov}）"
    )


def _h9(
    jst_gov: Mapping[str, Series], jst_priv: Mapping[str, Series]
) -> tuple[str, list[tuple[str, float, float, int]]]:
    print("\n## H9: JST 2008 → 2019 年の公的・民間債務比率の変化")
    _row(
        [
            "国",
            "公的 2008",
            "公的 終点",
            "公的 変化",
            "民間 2008",
            "民間 終点（年）",
            "民間 変化",
            "該当",
        ]
    )
    _row(["---"] * 8)
    rows: list[tuple[str, float, float, int]] = []
    n_hit = 0
    hits: list[str] = []
    for iso in JST18:
        gs, ps = jst_gov.get(iso, {}), jst_priv.get(iso, {})
        gc, pc = change(gs, 2008, 2019), change(ps, 2008, 2019)
        if gc is None or pc is None:
            _row([NAMES[iso], "–", "–", "–", "–", "–", "–", "データ不足"])
            continue
        hit = h9_hit(gc[1], pc[1])
        n_hit += hit
        if hit:
            hits.append(NAMES[iso])
        rows.append((iso, pc[1], gc[1], pc[0]))
        name = f"**{NAMES[iso]}（{iso}）**" if iso == JP else f"{NAMES[iso]}（{iso}）"
        _row(
            [
                name, _u(gs[2008]), f"{_u(gs[gc[0]])}（{gc[0]}）", _f(gc[1]), _u(ps[2008]),
                f"{_u(ps[pc[0]])}（{pc[0]}）", _f(pc[1]), _yn(hit),
            ]
        )  # fmt: skip
    j = judge_h9(n_hit)
    print(f"\n- 該当（公的が上昇 かつ 民間の変化 < +5 pt）: {n_hit} / 18（{'、'.join(hits)}）")
    gov_up = sum(r[2] > 0 for r in rows)
    priv_down = sum(r[1] < 0 for r in rows)
    print(f"- 公的が上昇: {gov_up} / 18、民間が低下: {priv_down} / 18")
    print(
        f"- 中央値: 公的 {statistics.median([r[2] for r in rows]):+.1f} pt、"
        f"民間 {statistics.median([r[1] for r in rows]):+.1f} pt"
    )
    print(f"- **H9 判定: {j}**")
    print("\n### H9 頑健性（探索的・事後。閾値は固定）")
    _row(["仕様", "該当", "判定"])
    _row(["---"] * 3)
    _row(["主: 2008→2019（日本の民間 2017）", f"{n_hit} / 18", j])
    for label, a, b, jp_end in (
        ("日本は公的も 2008→2017", 2008, 2019, 2017),
        ("2008→2020（コロナの年を含む）", 2008, 2020, None),
        ("2007→2019（危機前年を起点）", 2007, 2019, None),
        ("2009→2019", 2009, 2019, None),
    ):
        n = 0
        for iso in JST18:
            end_g = jp_end if (iso == JP and jp_end is not None) else b
            gc = change(jst_gov.get(iso, {}), a, end_g)
            pc = change(jst_priv.get(iso, {}), a, b)
            if gc is not None and pc is not None and h9_hit(gc[1], pc[1]):
                n += 1
        _row([f"{label}", f"{n} / 18", judge_h9(n)])
    return j, rows


def _h10(inp: Inputs) -> tuple[str, dict[str, Series], dict[str, tuple[int, float]]]:
    print("\n## H10: 純利払い ÷ 歳入（%）")
    ratio = {
        iso: interest_to_revenue(inp.interest.get(iso, {}), inp.revenue.get(iso, {}))
        for iso in JST18
    }
    _row(
        [
            "国", "基準期間", "基準最大（年）", "基準 ÷ 2", "2019", "2024", "2025（推計）",
            "2024 / 基準", "2024 ≤ 基準/2", "2025 ≤ 基準/2",
        ]
    )  # fmt: skip
    _row(["---"] * 10)
    bases: dict[str, tuple[int, float]] = {}
    n24 = n25 = 0
    undefined: list[str] = []
    hit24: list[str] = []
    for iso in sorted(JST18, key=lambda i: -ratio[i].get(2024, -math.inf)):
        s = ratio[iso]
        w = base_window(iso, s)
        bm = window_max(s, w) if w is not None else None
        if bm is not None:
            bases[iso] = bm
        h24 = halved(bm[1], s[2024]) if bm is not None and 2024 in s else None
        h25 = halved(bm[1], s[2025]) if bm is not None and 2025 in s else None
        if bm is not None and bm[1] <= 0:
            undefined.append(NAMES[iso])
        n24 += h24 is True
        n25 += h25 is True
        if h24:
            hit24.append(NAMES[iso])
        rat = s[2024] / bm[1] if bm is not None and bm[1] > 0 and 2024 in s else None
        name = f"**{NAMES[iso]}（{iso}）**" if iso == JP else f"{NAMES[iso]}（{iso}）"
        _row(
            [
                name, "–" if w is None else f"{w[0]}–{w[1]}",
                "–" if bm is None else f"{bm[1]:.1f}（{bm[0]}）",
                "–" if bm is None else f"{bm[1] / 2:.1f}", _u(s.get(2019)), _u(s.get(2024)),
                _u(s.get(2025)), _u(rat, 2), _yn(h24), _yn(h25),
            ]
        )  # fmt: skip
    j24, j25 = judge_h10(n24), judge_h10(n25)
    n_def = 18 - len(undefined)
    print("\n単位: %（純利払い ÷ 歳入 × 100）。負値 = 純利子受取。")
    print(f"- 基準が 0 以下で「半分以下」を定義できない国: {'、'.join(undefined) or 'なし'}")
    print(f"- (a) 2024 ≤ 基準最大 ÷ 2: {n24} / 18（{'、'.join(hit24)}）。閾値 ≥ 12")
    print(f"  - 定義できる国だけ: {n24} / {n_def}")
    print(f"- **H10(a) 判定: {j24}**")
    v24 = {i: ratio[i][2024] for i in JST18 if 2024 in ratio[i]}
    print(
        f"- (b) 日本 2024 年: {v24[JP]:.2f}%、大きい方から {rank_desc(v24, JP)} 位 / {len(v24)}。"
        f"日本の基準最大 {bases[JP][1]:.2f}%（{bases[JP][0]}）、"
        f"2019 年 {ratio[JP].get(2019, math.nan):.2f}%"
    )
    med24 = statistics.median(v24.values())
    v19 = [ratio[i][2019] for i in JST18 if 2019 in ratio[i]]
    vb = [b[1] for b in bases.values()]
    print(
        f"- 18 か国中央値: 基準最大 {statistics.median(vb):.2f}%、"
        f"2019 年 {statistics.median(v19):.2f}%、"
        f"2024 年 {med24:.2f}%"
    )
    print(
        f"- (c) 副判定 2025 年（一部推計）: {n25} / 18 → {j25}（定義できる国だけ {n25} / {n_def}）"
    )
    # 探索的
    print("\n### H10 頑健性（探索的・事後。閾値は固定）")
    _row(["仕様", "該当", "判定"])
    _row(["---"] * 3)
    _row(["主: 2024 年、基準 = 1990 年代の最大", f"{n24} / 18", j24])
    _row([f"基準が 0 以下の国を母数から除く（n = {n_def}）", f"{n24} / {n_def}", "–"])
    n_fn = sum(
        1
        for i in JST18
        if i not in ("FIN", "NOR") and i in bases and halved(bases[i][1], ratio[i][2024]) is True
    )
    _row(["FIN・NOR を母数から除く（n = 16）", f"{n_fn} / 16", "–"])
    neg24 = [NAMES[i] for i in JST18 if ratio[i].get(2024, 0.0) < 0]
    n_pos = sum(
        1
        for i in JST18
        if i in bases and ratio[i][2024] >= 0 and halved(bases[i][1], ratio[i][2024]) is True
    )
    _row(
        [
            f"2024 年が負（純利子受取: {'、'.join(neg24)}）の国も満たさない側に数える",
            f"{n_pos} / 18",
            judge_h10(n_pos),
        ]
    )
    _row(["副判定（事前登録）: 2025 年", f"{n25} / 18", j25])
    for label, yr in (("2023 年", 2023), ("2019 年（参考: 金利上昇前）", 2019)):
        n = sum(
            1
            for i in JST18
            if i in bases and yr in ratio[i] and halved(bases[i][1], ratio[i][yr]) is True
        )
        _row([label, f"{n} / 18", judge_h10(n)])
    n = 0
    for i in JST18:
        w = base_window(i, ratio[i])
        m = period_mean(ratio[i], *w) if w is not None else None
        if m is not None and 2024 in ratio[i] and halved(m, ratio[i][2024]) is True:
            n += 1
    _row(["基準 = 1990 年代の平均（最大でなく）", f"{n} / 18", judge_h10(n)])
    n = 0
    for i in JST18:
        bm = window_max(ratio[i], (2001, 2004))
        if bm is not None and 2024 in ratio[i] and halved(bm[1], ratio[i][2024]) is True:
            n += 1
    _row(["基準 = 全国 2001–2004 年の最大", f"{n} / 18", judge_h10(n)])
    return j24, ratio, bases


def _coverage(inp: Inputs, jst_gov: Mapping[str, Series], jst_priv: Mapping[str, Series]) -> None:
    print("\n## データ: 系列ごとの国・年の数（JST 18 か国）")
    _row(["系列", "国・年", "国", "最初の年", "最後の年", "始まりが遅い国"])
    _row(["---"] * 6)
    for label, d, lo in (
        ("WEO 総債務", inp.d, 1980),
        ("WEO 実質成長率", inp.rgdp, 1980),
        ("WEO CPI", inp.cpi, 1980),
        ("FM 基礎的財政収支", inp.pb, 1990),
        ("FM 純利払い", inp.interest, 1990),
        ("FM 歳入", inp.revenue, 1990),
        ("JST 公的債務", jst_gov, 1870),
        ("JST 民間非金融", jst_priv, 1870),
    ):
        ys = [y for s in d.values() for y in s]
        late = [f"{i} {min(s)}" for i, s in sorted(d.items()) if s and min(s) > lo]
        _row([label, len(ys), len(d), min(ys), max(ys), "、".join(late) or "–"])
    late_end = [f"{i} {max(s)}" for i, s in sorted(jst_priv.items()) if max(s) < 2019]
    print(f"- JST 民間非金融が 2019 年より前に終わる国: {'、'.join(late_end) or 'なし'}")


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
    rgdp = series(mart, "imf_weo", "macro", "rgdp_growth", JST18)
    cpi = series(mart, "imf_weo", "macro", "cpi_inflation", JST18)
    inp = Inputs(
        d=series(mart, "imf_weo", gg, "debt_gdp", JST18),
        interest=series(mart, "imf_fm", gg, "interest_gdp", JST18),
        pb=series(mart, "imf_fm", gg, "primary_balance_gdp", JST18),
        rgdp=rgdp,
        cpi=cpi,
        g={iso: nominal_growth_series(rgdp[iso], cpi.get(iso, {})) for iso in rgdp},
        revenue=series(mart, "imf_fm", gg, "revenue_gdp", JST18),
    )
    jst_gov = series(mart, "jst", gg, "debt_gdp", JST18)
    jst_priv = series(mart, "jst", "private_nonfin", "debt_gdp", JST18)
    g_jst = series(mart, "jst", "macro", "ngdp_growth", JST18)

    print("# R3 2010 年代の債務動態・インフレ期・民間から国家へ・利払いの対歳入比（2026-11-03）")
    print(f"- mart: public_debt_panel {mart.height} 行。JST 18 か国のみ使用")
    _coverage(inp, jst_gov, jst_priv)

    decs7, j7 = _h7(inp)
    decs8, j8 = _h8(inp, 2020, "")
    decs8b, j8b = _h8(inp, 2019, "（副判定）")
    _robust_decomp(inp, g_jst)
    j9, rows9 = _h9(jst_gov, jst_priv)
    j10, ratio, bases = _h10(inp)

    print("\n## 判定のまとめ")
    print(f"- H7: {j7} / H8: {j8}（副判定 2019→2024: {j8b}）/ H9: {j9} / H10(a): {j10}")

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    order = sorted(JST18, key=lambda i: decs7[i].delta, reverse=True)
    fig_decomposition(
        [
            ("H7: 2010 → 2019 年の債務比率の変化の分解", decs7),
            ("H8: 2020 → 2024 年の分解", decs8),
            ("H8 副判定: 2019 → 2024 年の分解", decs8b),
        ],
        order,
        args.fig_dir / "r3_decomposition_stacked.png",
    )
    fig_h9(rows9, args.fig_dir / "r3_h9_public_private_scatter.png")
    fig_h10(ratio, bases, args.fig_dir / "r3_h10_interest_revenue_small_multiples.png")
    print(
        "\n図: r3_decomposition_stacked.png, r3_h9_public_private_scatter.png, "
        "r3_h10_interest_revenue_small_multiples.png"
    )


if __name__ == "__main__":
    main()
