"""R1: 先進 18 か国の負債の歴史 1870–2020（H1・H2・H2b・H3・H3b・H4・H6(a)）。

事前登録（design/themes/public-debt.md、2026-11-03）。閾値は設計書のまま:
  H1  : 2020 年の政府債務比率 ≥ その国の 1870〜1950 年の最大値 の国数が 18 の 1/3 未満（≤5）なら
        整合、過半（≥10）なら不支持、間は中間。2019 年で副判定。
  H2  : 1945 → 1975 年に 30 pt 以上低下した国が 2/3 以上（≥12）なら整合、半数未満（≤8）なら不支持。
        1945 年が欠損の国は 1946〜1950 年の最初の利用可能年を起点にする。
  H2b : 起点〜1975 年の Δd を (r−g) 項・pb 項・残差に分解し、(r−g) 項の方が低下への寄与が大きい
        （符号付き: rg < pb）国が過半（≥10）なら整合、半数未満（≤8）なら不支持。絶対値比較
        |rg| > |pb| は旧仕様として併記。r = 長期金利（代理）、g = 名目 GDP 成長率、
        pb = 総合財政収支（代理、利払い込み）。
  H3  : 設計書の区切りで、(i) インフレ 10 年平均の最大が 1970s、(ii) 18 か国中央値の政府債務の
        年当たり上昇が 1970–80 / 1980–95 / 1995–2008 のうち 1980–95 で最大、(iii) 家計債務が
        1995–2008 で最大なら整合。2008– は (iv)（中銀、データなし）。10 年グリッドは補助。
  H3b : 総負債（公的 + 民間非金融）の 1870〜2019 年の最大が 2019 年（2019 欠損国は最終観測年）
        である国が 2/3 以上（≥12）なら整合、半数未満（≤8）なら不支持。2020 年・2008 年以降も併記。
  H4  : (a) 長期金利 < 1% の国・年が 1870–2008 年に 1% 未満、かつ 2012–2020 年に過半なら整合。
        (b) r − g < 0 の国・年の割合が 1945–1980 年 ≥ 2010–2020 年 × 0.8 なら整合。
  H6a : 日本の 2020 年の債務比率が 18 か国の最高で、かつ同国 1944 年（204%）を上回れば整合。

決定的スクリプト（乱数なし）。入力は data/marts/public_debt_panel.parquet（JST Macrohistory R6、
CC BY-NC-SA 4.0）。純粋ヘルパは tests/test_analysis_r1.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
import math
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

THEME_DIR = Path(__file__).resolve().parents[3]
SOURCE_NOTE = "Jordà–Schularick–Taylor Macrohistory Database R6（2026-11-03 取得、CC BY-NC-SA 4.0）"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
WAR_SHADE = "#efe7da"
JP = "JPN"

WARS: tuple[tuple[int, int], ...] = ((1914, 1918), (1939, 1945))
DECADES: tuple[int, ...] = (1950, 1960, 1970, 1980, 1990, 2000, 2010)

DEBT = "general_gov_gross.debt_gdp"
FB = "general_gov_gross.fiscal_balance_gdp"
HH = "households.debt_gdp"
NFC = "nfc.debt_gdp"
PRIV = "private_nonfin.debt_gdp"
TOTAL = "total_nonfin.debt_gdp"
LT = "macro.ltrate"
ST = "macro.stir"
G = "macro.ngdp_growth"
INFL = "macro.cpi_inflation"

Series = dict[int, float]
Panel = dict[str, dict[str, Series]]

# ---- pure helpers: periods / thresholds ----------------------------------------------------------


def in_war(year: int) -> bool:
    return any(a <= year <= b for a, b in WARS)


def _judge_low(n_hit: int, n: int) -> str:
    """少数（1/3 未満）なら整合、過半なら不支持、間は中間。"""
    if 3 * n_hit < n:
        return "整合"
    if 2 * n_hit > n:
        return "不支持"
    return "中間"


def _judge_two_thirds(n_hit: int, n: int) -> str:
    """2/3 以上なら整合、半数未満なら不支持、間は中間。"""
    if 3 * n_hit >= 2 * n:
        return "整合"
    if 2 * n_hit < n:
        return "不支持"
    return "中間"


def _judge_majority(n_hit: int, n: int) -> str:
    """過半なら整合、半数未満なら不支持、ちょうど半数は中間。"""
    if 2 * n_hit > n:
        return "整合"
    if 2 * n_hit < n:
        return "不支持"
    return "中間"


# ---- H1 / H2 -------------------------------------------------------------------------------------


def prewar_max(s: Mapping[int, float], lo: int = 1870, hi: int = 1950) -> tuple[int, float] | None:
    """lo〜hi 年の最大値（年, 値）。同値は早い年。"""
    window = [(y, v) for y, v in sorted(s.items()) if lo <= y <= hi]
    if not window:
        return None
    best = window[0]
    for y, v in window[1:]:
        if v > best[1]:
            best = (y, v)
    return best


def window_gaps(s: Mapping[int, float], lo: int = 1870, hi: int = 1950) -> list[int]:
    """lo〜hi 年のうち値が無い年（H1 の最大値が下限にすぎない国を示す）。"""
    return [y for y in range(lo, hi + 1) if y not in s]


def judge_h1(n_at_or_above: int, n: int = 18) -> str:
    return _judge_low(n_at_or_above, n)


def decline_start(s: Mapping[int, float], base: int = 1945, latest: int = 1950) -> int | None:
    """H2 の起点: base 年、欠損なら latest 年までの最初の利用可能年。"""
    for y in range(base, latest + 1):
        if y in s:
            return y
    return None


def judge_h2(n_declined: int, n: int = 18) -> str:
    return _judge_two_thirds(n_declined, n)


# ---- H2b: debt dynamics --------------------------------------------------------------------------


@dataclass(frozen=True)
class YearObs:
    """1 国 1 年。d: 債務比率（% GDP）、r: 名目金利（%）、g: 名目成長率（%）、

    pb: 財政収支（% GDP）。
    """

    year: int
    d: float | None
    r: float | None
    g: float | None
    pb: float | None


@dataclass(frozen=True)
class Decomposition:
    """Δd = Σ(r−g)項 + Σpb項 + Σsfa + gap（gap: 入力が欠けて分解できない年の Δd の合計）。"""

    start: int
    end: int
    d_start: float
    d_end: float
    delta: float
    rg: float
    pb: float
    sfa: float
    gap: float
    n_years: int
    n_complete: int


def decompose_debt_change(obs: Sequence[YearObs], start: int, end: int) -> Decomposition:
    """債務動態の恒等式 Δd_t = (r_t − g_t)/(1 + g_t)·d_{t−1} − pb_t + sfa_t を積み上げる。

    t = start+1..end。値はすべて % 単位（(r − g)/(1 + g) = (r − g)/(100 + g)）。
    d_{t−1}, d_t, r_t, g_t, pb_t が揃う年だけ分解し、揃わない年の Δd は gap に入れる。
    端点の d が無ければ ValueError。恒等式は delta = rg + pb + sfa + gap で必ず閉じる。
    """
    by_year = {o.year: o for o in obs}
    o0, o1 = by_year.get(start), by_year.get(end)
    if o0 is None or o1 is None or o0.d is None or o1.d is None:
        msg = f"decompose: debt endpoint missing ({start} or {end})"
        raise ValueError(msg)
    rg = pb = sfa = explained = 0.0
    n_complete = 0
    for t in range(start + 1, end + 1):
        cur, prev = by_year.get(t), by_year.get(t - 1)
        if cur is None or prev is None:
            continue
        if cur.d is None or prev.d is None or cur.r is None or cur.g is None or cur.pb is None:
            continue
        dd = cur.d - prev.d
        rg_t = (cur.r - cur.g) / (100.0 + cur.g) * prev.d
        pb_t = -cur.pb
        rg += rg_t
        pb += pb_t
        sfa += dd - rg_t - pb_t
        explained += dd
        n_complete += 1
    delta = o1.d - o0.d
    return Decomposition(
        start=start,
        end=end,
        d_start=o0.d,
        d_end=o1.d,
        delta=delta,
        rg=rg,
        pb=pb,
        sfa=sfa,
        gap=delta - explained,
        n_years=end - start,
        n_complete=n_complete,
    )


def impute_primary(obs: Sequence[YearObs]) -> list[YearObs]:
    """総合収支 → 基礎的収支の近似: pb ≈ 総合収支 + r/(1 + g)·d_{t−1}（r は長期金利の代理）。"""
    by_year = {o.year: o for o in obs}
    out: list[YearObs] = []
    for o in obs:
        prev = by_year.get(o.year - 1)
        pb: float | None = None
        if (
            o.pb is not None
            and o.r is not None
            and o.g is not None
            and prev is not None
            and prev.d is not None
        ):
            pb = o.pb + o.r / (100.0 + o.g) * prev.d
        out.append(YearObs(o.year, o.d, o.r, o.g, pb))
    return out


def rg_dominates(dec: Decomposition, signed: bool = True) -> bool:
    """(r−g) 項が pb 項より「大きい」か。

    signed=True（主、設計書「低下のうち (r−g) 項が基礎的財政収支項より大きい」）: 債務を減らす
    寄与（負の値）が大きい方、すなわち rg < pb。signed=False（旧主仕様）: |rg| > |pb|。
    """
    return dec.rg < dec.pb if signed else abs(dec.rg) > abs(dec.pb)


def judge_h2b(n_rg_dominant: int, n: int = 18) -> str:
    return _judge_majority(n_rg_dominant, n)


# ---- H3 / H3b ------------------------------------------------------------------------------------


def cross_median(panel: Mapping[str, Mapping[int, float]]) -> Series:
    """年ごとの国間中央値（その年に値のある国だけ）。"""
    years = sorted({y for s in panel.values() for y in s})
    return {y: statistics.median([s[y] for s in panel.values() if y in s]) for y in years}


def decade_mean(s: Mapping[int, float], d0: int) -> float | None:
    vals = [s[y] for y in range(d0, d0 + 10) if y in s]
    return sum(vals) / len(vals) if vals else None


def decade_rise(s: Mapping[int, float], d0: int, end: int | None = None) -> float | None:
    """d0 年 → d0+10 年（end 指定時は end 年）の変化幅。端点が欠ければ None。"""
    e = d0 + 10 if end is None else end
    if d0 not in s or e not in s:
        return None
    return s[e] - s[d0]


def peak_decade(values: Mapping[int, float | None]) -> int | None:
    best: tuple[int, float] | None = None
    for k in sorted(values):
        v = values[k]
        if v is None:
            continue
        if best is None or v > best[1]:
            best = (k, v)
    return None if best is None else best[0]


def judge_h3(infl: int | None, debt: int | None, hh: int | None) -> str:
    if infl is None or debt is None or hh is None:
        return "判定不能"
    ok = infl == 1970 and debt in (1980, 1990) and hh in (1990, 2000) and infl < debt < hh
    return "整合" if ok else "不支持"


# 設計書 H3 の区切り（(i) 1970s、(ii) 1980–1995、(iii) 1995–2008。2008– は (iv) で対象外）
DESIGN_PERIODS: tuple[tuple[int, int], ...] = ((1970, 1980), (1980, 1995), (1995, 2008))


def period_rate(s: Mapping[int, float], a: int, b: int) -> float | None:
    """a 年 → b 年の変化を年数で割った年当たり変化（pt/年）。端点が欠ければ None。"""
    if a not in s or b not in s:
        return None
    return (s[b] - s[a]) / (b - a)


def judge_h3_design(infl: int | None, debt: int | None, hh: int | None) -> str:
    """設計書の区切りでの判定。infl はインフレ 10 年平均が最大の 10 年、debt / hh は
    DESIGN_PERIODS のうち年当たり上昇が最大の期間の開始年。"""
    if infl is None or debt is None or hh is None:
        return "判定不能"
    return "整合" if (infl, debt, hh) == (1970, 1980, 1995) else "不支持"


def max_year(s: Mapping[int, float]) -> int | None:
    best: tuple[int, float] | None = None
    for y in sorted(s):
        if best is None or s[y] > best[1]:
            best = (y, s[y])
    return None if best is None else best[0]


def max_year_through(s: Mapping[int, float], end: int) -> int | None:
    """end 年以前に限った最大の年。"""
    return max_year({y: v for y, v in s.items() if y <= end})


def judge_h3b(n_latest_max: int, n: int = 18) -> str:
    return _judge_two_thirds(n_latest_max, n)


# ---- H4 / H6 -------------------------------------------------------------------------------------


def share_below(values: Sequence[float], threshold: float) -> float:
    if not values:
        return math.nan
    return sum(1 for v in values if v < threshold) / len(values)


def judge_h4a(share_hist: float, share_recent: float) -> str:
    return "整合" if share_hist < 0.01 and share_recent > 0.5 else "不支持"


def judge_h4b(share_postwar: float, share_recent: float) -> str:
    return "整合" if share_postwar >= 0.8 * share_recent else "不支持"


def judge_h6a(jp_latest: float, others_latest: Mapping[str, float], jp_1944: float) -> str:
    top = all(jp_latest > v for v in others_latest.values())
    return "整合" if top and jp_latest > jp_1944 else "不支持"


# ---- loader --------------------------------------------------------------------------------------


def load_panel(mart: pl.DataFrame, source: str | None = None) -> Panel:
    """long mart → {"unit.metric": {iso3: {year: value}}}。source 指定時はその出典の行だけ。

    (unit, metric, iso3, year) が重複したら ValueError（出典を混ぜて黙って上書きしない）。
    """
    if source is not None:
        mart = mart.filter(pl.col("source") == source)
    out: Panel = {}
    for r in mart.select("iso3", "year", "unit", "metric", "value").iter_rows():
        iso, year, unit, metric, value = r
        s = out.setdefault(f"{unit}.{metric}", {}).setdefault(str(iso), {})
        if int(year) in s:
            msg = f"load_panel: duplicate {unit}.{metric} {iso} {year}; pass source="
            raise ValueError(msg)
        s[int(year)] = float(value)
    return out


def _s(p: Panel, key: str, iso: str) -> Series:
    return p.get(key, {}).get(iso, {})


def year_obs(p: Panel, iso: str, years: Iterable[int], r_key: str = LT) -> list[YearObs]:
    d, r, g, fb = _s(p, DEBT, iso), _s(p, r_key, iso), _s(p, G, iso), _s(p, FB, iso)
    return [YearObs(y, d.get(y), r.get(y), g.get(y), fb.get(y)) for y in years]


def pooled(p: Panel, key: str, lo: int, hi: int) -> list[float]:
    return [v for s in p.get(key, {}).values() for y, v in s.items() if lo <= y <= hi]


def pooled_r_minus_g(p: Panel, lo: int, hi: int, r_key: str = LT) -> list[float]:
    out: list[float] = []
    for iso, r in p.get(r_key, {}).items():
        g = _s(p, G, iso)
        out.extend(r[y] - g[y] for y in sorted(r) if lo <= y <= hi and y in g)
    return out


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


def fig_small_multiples(p: Panel, names: Mapping[str, str], path: Path) -> None:
    import matplotlib.pyplot as plt

    isos = sorted(p[DEBT])
    fig, axes = plt.subplots(3, 6, figsize=(12.5, 6.6), sharex=True, sharey=True)
    for ax, iso in zip(axes.flat, isos, strict=True):
        for a, b in WARS:
            ax.axvspan(a - 0.5, b + 0.5, color=WAR_SHADE, linewidth=0)
        s = p[DEBT][iso]
        ys = sorted(s)
        col = SERIES[1] if iso == JP else SERIES[0]
        # break the line at missing years
        seg_x: list[int] = []
        seg_y: list[float] = []
        for y in ys:
            if seg_x and y != seg_x[-1] + 1:
                ax.plot(seg_x, seg_y, color=col, linewidth=1.6 if iso == JP else 1.0)
                seg_x, seg_y = [], []
            seg_x.append(y)
            seg_y.append(s[y])
        ax.plot(seg_x, seg_y, color=col, linewidth=1.6 if iso == JP else 1.0)
        pk = prewar_max(s)
        if pk is not None:
            ax.axhline(pk[1], color=MUTED, linewidth=0.6, linestyle=":")
        ax.set_title(f"{names.get(iso, iso)}（{iso}）", fontsize=8, color=INK, loc="left")
        _style(ax)
    for ax in axes[:, 0]:
        ax.set_ylabel("政府債務 / GDP（%）", fontsize=7, color=INK)
    fig.suptitle(
        "政府債務の対 GDP 比 1870–2020（18 か国）。網掛け = 両大戦（1914–18, 1939–45）、"
        "点線 = 1870–1950 年の最大値、橙 = 日本",
        fontsize=9.5,
        color=INK,
        x=0.01,
        ha="left",
    )
    _footer(fig, f"出典: {SOURCE_NOTE}（debtgdp × 100）。n = 18 か国、欠損年は線を切る。")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h3(med: Mapping[str, Series], counts: Panel, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    spans = (*DESIGN_PERIODS, (2008, 2020))
    names = ("(i) インフレ", "(ii) 公的債務", "(iii) 家計", "(iv) 中銀・公的")
    for k, ((a0, b0), nm) in enumerate(zip(spans, names, strict=True)):
        ax.axvspan(a0, b0, color="#f0f0f0" if k % 2 == 0 else "#fafafa", linewidth=0)
        ax.text((a0 + b0) / 2, 88, nm, ha="center", va="top", fontsize=7, color=MUTED)
    labels = {DEBT: "政府債務", HH: "家計債務", NFC: "企業債務"}
    for i, key in enumerate((DEBT, HH, NFC)):
        s = {y: v for y, v in med[key].items() if 1950 <= y <= 2020}
        ys = sorted(s)
        ax.plot(ys, [s[y] for y in ys], color=SERIES[i], linewidth=1.5, label=labels[key])
    ax.set_ylabel("対 GDP 比（%、18 か国中央値）", fontsize=8, color=INK)
    ax.set_xlim(1949, 2021)
    _style(ax)
    ax2 = ax.twinx()
    s = {y: v for y, v in med[INFL].items() if 1950 <= y <= 2020}
    ys = sorted(s)
    ax2.plot(ys, [s[y] for y in ys], color=SERIES[3], linewidth=1.3, label="CPI インフレ率（右軸）")
    ax2.set_ylabel("CPI インフレ率（% 前年比、18 か国中央値）", fontsize=8, color=SERIES[3])
    ax2.tick_params(colors=SERIES[3], labelsize=7)
    ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.5, frameon=False, loc="center left")
    ax.set_title(
        "シュトレークの「先送り手段」の順序（H3）: 18 か国中央値 1950–2020",
        fontsize=10,
        color=INK,
        loc="left",
    )
    n_hh = len(counts[HH])
    n_hh_1950 = sum(1 for s in counts[HH].values() if 1950 in s)
    _footer(
        fig,
        f"出典: {SOURCE_NOTE}。家計・企業債務は銀行貸出（thh・tbus）。\n"
        f"各年の中央値はその年に値のある国のみ（家計: 1950 年 {n_hh_1950} か国、"
        f"1990 年以降 {n_hh} か国）。"
        "網掛けは設計書 H3 の区切り（1970–80 / 1980–95 / 1995–2008 / 2008–）。n = 18 か国。",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h4(
    lt_groups: Sequence[tuple[str, list[float]]],
    rg_groups: Sequence[tuple[str, list[float]]],
    path: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.6))
    specs = (
        (axes[0], lt_groups, 1.0, "名目長期金利（% 年率）", "名目長期金利", "< 1%"),
        (axes[1], rg_groups, 0.0, "r − g（%pt、r = 長期金利、g = 名目成長率）", "r − g", "< 0"),
    )
    for ax, groups, thr, ylabel, title, lab in specs:
        data = [g for _, g in groups]
        ax.boxplot(
            data,
            tick_labels=[f"{name}\nn={len(g)}" for name, g in groups],
            showfliers=False,
            widths=0.55,
            medianprops={"color": SERIES[1]},
            boxprops={"color": SERIES[0]},
            whiskerprops={"color": SERIES[0]},
            capprops={"color": SERIES[0]},
        )
        ax.axhline(thr, color=MUTED, linewidth=0.8, linestyle="--")
        lo, hi = ax.get_ylim()
        for i, g in enumerate(data, start=1):
            ax.text(
                i,
                hi,
                f"{lab}: {100 * share_below(g, thr):.0f}%",
                ha="center",
                va="top",
                fontsize=7,
                color=INK,
            )
        ax.set_ylim(lo, hi + (hi - lo) * 0.06)
        ax.set_ylabel(ylabel, fontsize=8, color=INK)
        ax.set_title(f"{title}（国・年の分布、期間別）", fontsize=9.5, color=INK, loc="left")
        _style(ax)
    _footer(
        fig,
        f"出典: {SOURCE_NOTE}。18 か国の国・年をプール。箱 = 四分位、ひげ = 1.5×IQR、"
        "外れ値（ハイパーインフレ年など）は非表示。上の % は閾値未満の国・年の割合。",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_h2b(decs: Sequence[tuple[str, Mapping[str, Decomposition], int]], path: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(2, 1, figsize=(11.0, 8.0))
    comps = (
        ("(r−g) 項（成長・インフレ・金利）", SERIES[0]),
        ("財政収支項（−総合収支、代理）", SERIES[2]),
        ("残差（sfa + 欠損年）", "#b5b5b5"),
    )
    for ax, (title, dmap, start0) in zip(axes, decs, strict=True):
        isos = sorted(dmap)
        x = np.arange(len(isos))
        vals = np.array(
            [[dmap[i].rg, dmap[i].pb, dmap[i].sfa + dmap[i].gap] for i in isos], dtype=float
        )
        pos_bottom = np.zeros(len(isos))
        neg_bottom = np.zeros(len(isos))
        for k, (lab, col) in enumerate(comps):
            v = vals[:, k]
            bottom = np.where(v >= 0, pos_bottom, neg_bottom)
            ax.bar(x, v, bottom=bottom, color=col, width=0.7, label=lab)
            pos_bottom = pos_bottom + np.where(v >= 0, v, 0)
            neg_bottom = neg_bottom + np.where(v < 0, v, 0)
        ax.scatter(
            x, [dmap[i].delta for i in isos], color=INK, marker="D", s=18, zorder=3, label="Δd"
        )
        ax.axhline(0, color=MUTED, linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(
            [f"{i}\n{dmap[i].start}" if dmap[i].start != start0 else i for i in isos],
            fontsize=7,
        )
        ax.set_ylabel("債務比率の変化への寄与（%pt）", fontsize=8, color=INK)
        ax.set_title(title, fontsize=9.5, color=INK, loc="left")
        _style(ax)
        ax.legend(fontsize=7, frameon=False, ncol=4, loc="lower right", bbox_to_anchor=(1.0, 1.0))
    _footer(
        fig,
        f"出典: {SOURCE_NOTE}。Δd = (r−g)/(1+g)·d₋₁ − pb + sfa を年ごとに積み上げ。"
        "r = 長期金利（代理）、pb = 総合財政収支（利払い込みの代理）。"
        "国名下の年 = 起点が期首と異なる国の起点。",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- main ----------------------------------------------------------------------------------------

NAMES = {
    "AUS": "豪",
    "BEL": "ベルギー",
    "CAN": "加",
    "CHE": "スイス",
    "DEU": "独",
    "DNK": "デンマーク",
    "ESP": "西",
    "FIN": "フィンランド",
    "FRA": "仏",
    "GBR": "英",
    "IRL": "アイルランド",
    "ITA": "伊",
    "JPN": "日本",
    "NLD": "蘭",
    "NOR": "ノルウェー",
    "PRT": "ポルトガル",
    "SWE": "スウェーデン",
    "USA": "米",
}


def _f(v: float | None, nd: int = 1) -> str:
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def _row(cells: Sequence[object]) -> None:
    print("| " + " | ".join(str(c) for c in cells) + " |")


def _period_label(year: int) -> str:
    if in_war(year):
        return "戦時"
    if 1946 <= year <= 1950:
        return "戦後直後"
    return "平時"


def _years_txt(ys: Sequence[int]) -> str:
    """連続年を a–b にまとめる。"""
    out: list[str] = []
    i = 0
    while i < len(ys):
        j = i
        while j + 1 < len(ys) and ys[j + 1] == ys[j] + 1:
            j += 1
        out.append(str(ys[i]) if i == j else f"{ys[i]}–{ys[j]}")
        i = j + 1
    return "、".join(out)


def _decade_label(d: int | None) -> str:
    return "–" if d is None else f"{d}s"


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
    p = load_panel(mart, source="jst")
    mart_jst = mart.filter(pl.col("source") == "jst")
    isos = sorted(p[DEBT])
    n = len(isos)

    print("# R1 先進 18 か国の負債の歴史（2026-11-03）")
    srcs = ", ".join(sorted(str(x) for x in mart["source"].unique().to_list()))
    print(f"- mart: public_debt_panel {mart.height} 行（source: {srcs}）")
    yr = f"{int(mart_jst['year'].min())}–{int(mart_jst['year'].max())}"  # type: ignore[arg-type]
    print(f"- 本レポートは source = jst の {mart_jst.height} 行のみ使用（国 {n}、{yr}）")

    # ---- データ表 ----
    print("\n## データ: 系列ごとの国・年の数")
    _row(["unit.metric", "国・年", "国", "最初の年", "最後の年", "2020 年の国数"])
    _row(["---"] * 6)
    for key in (DEBT, FB, HH, NFC, PRIV, TOTAL, LT, ST, G, INFL):
        d = p.get(key, {})
        ys = [y for s in d.values() for y in s]
        n2020 = sum(1 for s in d.values() if 2020 in s)
        _row([key, len(ys), len(d), min(ys), max(ys), n2020])
    first_hh = {iso: min(s) for iso, s in p[HH].items()}
    print(
        "- 家計債務の最初の年: "
        + "、".join(f"{k} {v}" for k, v in sorted(first_hh.items(), key=lambda kv: kv[1]))
    )
    infl_all = pooled(p, INFL, 1870, 2020)
    big = sorted((v for v in infl_all if v > 100), reverse=True)
    print(f"- インフレ率 > 100% の国・年: {len(big)}（最大 {big[0]:.3g}%）" if big else "")

    # ---- H1 ----
    print("\n## H1: 2020 年の債務比率 vs 1870–1950 年の最大値")
    _row(
        [
            "国",
            "1870–1950 最大（年）",
            "区間",
            "1945",
            "1975",
            "2007",
            "2019",
            "2020",
            "2020 ≥ 最大",
            "2019 ≥ 最大",
        ]
    )
    _row(["---"] * 10)
    n20 = n19 = 0
    above20: list[str] = []
    above19: list[str] = []
    n_peak_war = 0
    for iso in isos:
        s = p[DEBT][iso]
        pk = prewar_max(s)
        assert pk is not None
        a20 = s.get(2020) is not None and s[2020] >= pk[1]
        a19 = s.get(2019) is not None and s[2019] >= pk[1]
        n20 += a20
        n19 += a19
        n_peak_war += in_war(pk[0])
        if a20:
            above20.append(iso)
        if a19:
            above19.append(iso)
        _row(
            [
                f"{NAMES[iso]}（{iso}）",
                f"{pk[1]:.1f}（{pk[0]}）",
                _period_label(pk[0]),
                _f(s.get(1945)),
                _f(s.get(1975)),
                _f(s.get(2007)),
                _f(s.get(2019)),
                _f(s.get(2020)),
                "○" if a20 else "",
                "○" if a19 else "",
            ]
        )
    print(f"- 1870–1950 の最大が戦時（1914–18, 1939–45）の年である国: {n_peak_war} / {n}")
    war_gaps = []
    for iso in isos:
        miss = [y for a, b in WARS for y in range(a, b + 1) if y not in p[DEBT][iso]]
        if miss:
            war_gaps.append(f"{iso} {len(miss)} 年（{min(miss)}–{max(miss)} のうち）")
    print(f"- 戦時の年に債務比率が欠損している国: {', '.join(war_gaps) or 'なし'}")
    print(f"- 2020 ≥ 最大: {n20} / {n}（{', '.join(above20)}）→ **H1 判定: {judge_h1(n20, n)}**")
    print(f"- 副判定 2019 ≥ 最大: {n19} / {n}（{', '.join(above19)}）→ {judge_h1(n19, n)}")
    gaps_hit = [
        f"{iso}（{_years_txt(window_gaps(p[DEBT][iso]))}）"
        for iso in above20
        if window_gaps(p[DEBT][iso])
    ]
    print(
        "- ○ のうち 1870–1950 の窓に欠損がある国（欠損年の方が高ければ ○ が外れうる → "
        f"{n20} は上限）: {', '.join(gaps_hit) or 'なし'}"
    )
    # 探索的: 平時（両大戦を除く）1870–1950 の最大
    n20p = 0
    for iso in isos:
        s = {y: v for y, v in p[DEBT][iso].items() if not in_war(y)}
        pk = prewar_max(s)
        if pk is not None and p[DEBT][iso].get(2020, -1.0) >= pk[1]:
            n20p += 1
    print(f"- 探索的: 両大戦の年を除いた 1870–1950 の最大と比べると 2020 ≥ 最大は {n20p} / {n}")

    # ---- H2 ----
    print("\n## H2: 1945 → 1975 年の低下幅")
    _row(["国", "起点年", "起点の値", "1975", "変化（pt）", "30pt 以上低下"])
    _row(["---"] * 6)
    n_decl = 0
    starts: dict[str, int] = {}
    for iso in isos:
        s = p[DEBT][iso]
        st = decline_start(s)
        assert st is not None
        starts[iso] = st
        ch = s[1975] - s[st]
        hit = ch <= -30.0
        n_decl += hit
        note = "" if st == 1945 else "（注: 1945 欠損）"
        _row(
            [
                f"{NAMES[iso]}（{iso}）",
                f"{st}{note}",
                _f(s[st]),
                _f(s[1975]),
                f"{ch:+.1f}",
                "○" if hit else "",
            ]
        )
    print(f"- 30pt 以上低下: {n_decl} / {n} → **H2 判定: {judge_h2(n_decl, n)}**")
    low_start = [iso for iso in isos if p[DEBT][iso][starts[iso]] < 30.0]
    print(f"- 起点の値が 30% 未満で 30pt 低下が起こりえない国: {', '.join(low_start) or 'なし'}")
    n_elig = n - len(low_start)
    print(f"- 探索的: それらを除くと {n_decl} / {n_elig}")
    n_half = sum(1 for iso in isos if p[DEBT][iso][1975] <= 0.5 * p[DEBT][iso][starts[iso]])
    print(f"- 探索的: 1975 年に起点の半分以下になった国 {n_half} / {n}")
    n_peak75 = 0
    for iso in isos:
        s = p[DEBT][iso]
        pk = prewar_max(s, 1940, 1950)
        if pk is not None and s[1975] - pk[1] <= -30.0:
            n_peak75 += 1
    print(f"- 探索的: 起点を 1940–1950 年の最大値にすると 30pt 以上低下 {n_peak75} / {n}")
    obs45 = [iso for iso in isos if 1945 in p[DEBT][iso]]
    n45 = sum(1 for iso in obs45 if p[DEBT][iso][1975] - p[DEBT][iso][1945] <= -30.0)
    print(
        f"- 頑健性（設計書どおり 1945 年を観測できる国だけ）: {n45} / {len(obs45)}"
        f"（閾値 2/3 以上で整合、判定: {judge_h2(n45, len(obs45))}）"
    )

    # ---- H2b ----
    print("\n## H2b: 債務動態の分解（主仕様: pb = 総合財政収支、r = 長期金利）")
    periods = (("1945–1975", None, 1975), ("1980–2007", 1980, 2007))
    all_decs: dict[str, dict[str, dict[str, Decomposition]]] = {"main": {}, "imputed": {}}
    for label, st0, en in periods:
        for variant in ("main", "imputed"):
            dm: dict[str, Decomposition] = {}
            for iso in isos:
                st = starts[iso] if st0 is None else decline_start(p[DEBT][iso], st0, st0 + 5)
                assert st is not None
                obs = year_obs(p, iso, range(st, en + 1))
                if variant == "imputed":
                    obs = impute_primary(obs)
                dm[iso] = decompose_debt_change(obs, st, en)
            all_decs[variant][label] = dm
    for variant, vlabel in (
        ("main", "主仕様（pb = 総合収支）"),
        ("imputed", "頑健性（pb = 総合収支 + r/(1+g)·d₋₁ で利払いを足し戻した近似）"),
    ):
        for label, _, _ in periods:
            dm = all_decs[variant][label]
            print(f"\n### {label} — {vlabel}")
            _row(
                [
                    "国",
                    "起点",
                    "d 起点",
                    "d 終点",
                    "Δd",
                    "(r−g) 項",
                    "pb 項",
                    "sfa",
                    "欠損年の Δd",
                    "分解できた年",
                    "rg < pb（符号付き、主）",
                    "|r−g| > |pb|（絶対値）",
                ]
            )
            _row(["---"] * 12)
            n_dom = n_abs = 0
            for iso in isos:
                dc = dm[iso]
                dom = rg_dominates(dc, signed=True)
                dab = rg_dominates(dc, signed=False)
                n_dom += dom
                n_abs += dab
                _row(
                    [
                        f"{NAMES[iso]}（{iso}）",
                        dc.start,
                        _f(dc.d_start),
                        _f(dc.d_end),
                        f"{dc.delta:+.1f}",
                        f"{dc.rg:+.1f}",
                        f"{dc.pb:+.1f}",
                        f"{dc.sfa:+.1f}",
                        f"{dc.gap:+.1f}",
                        f"{dc.n_complete}/{dc.n_years}",
                        "○" if dom else "",
                        "○" if dab else "",
                    ]
                )
                assert abs(dc.rg + dc.pb + dc.sfa + dc.gap - dc.delta) < 1e-9
            j = judge_h2b(n_dom, n)
            tag = "**H2b 判定" if (variant == "main" and label == "1945–1975") else "（参考）判定"
            end = "**" if tag.startswith("**") else ""
            print(f"- 符号付き（低下への寄与 rg < pb）: {n_dom} / {n} → {tag}: {j}{end}")
            print(f"- 絶対値（|rg| > |pb|、旧主仕様）: {n_abs} / {n} → {judge_h2b(n_abs, n)}")
            big_res = [
                f"{iso}（sfa {dm[iso].sfa:+.0f}、欠損 {dm[iso].gap:+.0f}）"
                for iso in isos
                if abs(dm[iso].sfa + dm[iso].gap) > max(abs(dm[iso].rg), abs(dm[iso].pb))
            ]
            print(f"- 残差（sfa + 欠損年）が両項より大きい国: {', '.join(big_res) or 'なし'}")
            med_rg = statistics.median(dm[i].rg for i in isos)
            med_pb = statistics.median(dm[i].pb for i in isos)
            med_d = statistics.median(dm[i].delta for i in isos)
            print(f"- 中央値: Δd {med_d:+.1f}、(r−g) 項 {med_rg:+.1f}、pb 項 {med_pb:+.1f}")
    # 探索的: r = 短期金利
    dm_st: dict[str, Decomposition] = {}
    for iso in isos:
        st = starts[iso]
        dm_st[iso] = decompose_debt_change(year_obs(p, iso, range(st, 1976), r_key=ST), st, 1975)
    n_dom_st = sum(1 for i in isos if rg_dominates(dm_st[i], signed=True))
    n_abs_st = sum(1 for i in isos if rg_dominates(dm_st[i], signed=False))
    print(
        f"\n- 探索的: r = 短期金利で 1945–1975 を分解すると 符号付き {n_dom_st} / {n}、"
        f"絶対値 {n_abs_st} / {n}"
    )

    # ---- H3 ----
    print("\n## H3: 先送り手段の順序（主: 設計書の区切り 1970s / 1980–95 / 1995–2008）")
    med = {k: cross_median(p[k]) for k in (INFL, DEBT, HH, NFC)}
    infl_dm = {d0: decade_mean(med[INFL], d0) for d0 in DECADES}
    pi = peak_decade(infl_dm)
    _row(["時期", "インフレ率 平均（%）", "政府債務 変化（pt/年）", "家計債務 変化（pt/年）"])
    _row(["---"] * 4)
    for a0, b0 in (*DESIGN_PERIODS, (2008, 2020)):
        im = [med[INFL][y] for y in range(a0, b0) if y in med[INFL]]
        tag = "（(iv) の領分、比較対象外）" if a0 == 2008 else ""
        _row(
            [
                f"{a0}–{b0}{tag}",
                _f(sum(im) / len(im)),
                _f(period_rate(med[DEBT], a0, b0), 2),
                _f(period_rate(med[HH], a0, b0), 2),
            ]
        )
    pdp = peak_decade({a0: period_rate(med[DEBT], a0, b0) for a0, b0 in DESIGN_PERIODS})
    php = peak_decade({a0: period_rate(med[HH], a0, b0) for a0, b0 in DESIGN_PERIODS})
    j3 = judge_h3_design(pi, pdp, php)
    print(
        f"- (i) インフレ 10 年平均の最大: {_decade_label(pi)}、(ii) 政府債務の年当たり上昇が最大の"
        f"期間: {pdp}–、(iii) 家計: {php}– → **H3 判定: {j3}**"
    )
    print(
        "- (iv)（2008 年以降の中銀資産）はデータなしで対象外。2008–2020 の政府債務上昇"
        f" {_f(period_rate(med[DEBT], 2008, 2020), 2)} pt/年は (ii) の比較に入れない"
    )
    print("\n### H3 国ごと（設計書の区切り）")
    _row(["国", "インフレ最大", "政府債務上昇最大", "家計上昇最大", "判定"])
    _row(["---"] * 5)
    n_ok = n_det = infl_1970 = 0
    for iso in isos:
        ci = peak_decade({d0: decade_mean(_s(p, INFL, iso), d0) for d0 in DECADES})
        cd = peak_decade({a0: period_rate(_s(p, DEBT, iso), a0, b0) for a0, b0 in DESIGN_PERIODS})
        chh = peak_decade({a0: period_rate(_s(p, HH, iso), a0, b0) for a0, b0 in DESIGN_PERIODS})
        jj = judge_h3_design(ci, cd, chh)
        n_det += jj != "判定不能"
        n_ok += jj == "整合"
        infl_1970 += ci == 1970
        nh = sum(1 for a0, b0 in DESIGN_PERIODS if period_rate(_s(p, HH, iso), a0, b0) is not None)
        _row(
            [
                f"{NAMES[iso]}（{iso}）",
                _decade_label(ci),
                "–" if cd is None else f"{cd}–",
                "–" if chh is None else f"{chh}–（{nh} 期間）",
                jj,
            ]
        )
    print(
        f"- 国ごとの一致率: {n_ok} / {n_det}（判定可能な国）。インフレ最大が 1970s の国: "
        f"{infl_1970} / {n}"
    )

    print("\n### 補助（逸脱した読み方）: 10 年グリッドでのピーク")
    debt_dr = {d0: decade_rise(med[DEBT], d0) for d0 in DECADES}
    hh_dr = {d0: decade_rise(med[HH], d0) for d0 in DECADES}
    nfc_dr = {d0: decade_rise(med[NFC], d0) for d0 in DECADES}
    _row(
        [
            "10 年",
            "インフレ率 10 年平均（%）",
            "政府債務 上昇幅（pt）",
            "家計債務 上昇幅",
            "企業債務 上昇幅（参考）",
        ]
    )
    _row(["---"] * 5)
    for d0 in DECADES:
        end = "2020" if d0 == 2010 else str(d0 + 10)
        _row(
            [
                f"{d0}s（{d0}→{end}）",
                _f(infl_dm[d0]),
                _f(debt_dr[d0]),
                _f(hh_dr[d0]),
                _f(nfc_dr[d0]),
            ]
        )
    pd_, ph = peak_decade(debt_dr), peak_decade(hh_dr)
    print(
        f"- 10 年グリッド: インフレ {_decade_label(pi)}、政府債務 {_decade_label(pd_)}、"
        f"家計 {_decade_label(ph)}（企業 {_decade_label(peak_decade(nfc_dr))}）→ "
        f"{judge_h3(pi, pd_, ph)}"
    )
    debt_dr19 = dict(debt_dr)
    debt_dr19[2010] = decade_rise(med[DEBT], 2010, end=2019)
    hh_dr19 = dict(hh_dr)
    hh_dr19[2010] = decade_rise(med[HH], 2010, end=2019)
    pd19, ph19 = peak_decade(debt_dr19), peak_decade(hh_dr19)
    print(
        f"- 10 年グリッドで 2010s を 2010→2019 に: 政府債務 {_decade_label(pd19)}、"
        f"家計 {_decade_label(ph19)} → {judge_h3(pi, pd19, ph19)}"
    )

    def med_of(key: str, d0: int, mean: bool = False) -> float | None:
        vals = [
            v
            for s in p[key].values()
            if (v := (decade_mean(s, d0) if mean else decade_rise(s, d0))) is not None
        ]
        return statistics.median(vals) if vals else None

    infl_c = {d0: med_of(INFL, d0, mean=True) for d0 in DECADES}
    debt_c = {d0: med_of(DEBT, d0) for d0 in DECADES}
    hh_c = {d0: med_of(HH, d0) for d0 in DECADES}
    pic, pdc, phc = peak_decade(infl_c), peak_decade(debt_c), peak_decade(hh_c)
    print(
        "- 10 年グリッドで国ごとの変化幅の中央値: "
        f"インフレ {_decade_label(pic)}、政府債務 {_decade_label(pdc)}、家計 {_decade_label(phc)}"
        f" → {judge_h3(pic, pdc, phc)}"
    )
    n_ok_g = 0
    for iso in isos:
        ci = peak_decade({d0: decade_mean(_s(p, INFL, iso), d0) for d0 in DECADES})
        cd = peak_decade({d0: decade_rise(_s(p, DEBT, iso), d0) for d0 in DECADES})
        chh = peak_decade({d0: decade_rise(_s(p, HH, iso), d0) for d0 in DECADES})
        n_ok_g += judge_h3(ci, cd, chh) == "整合"
    print(f"- 10 年グリッドでの国ごとの一致: {n_ok_g} / {n}")

    # 設計書区切りの頑健性: 国ごとの年当たり変化の中央値
    def med_rate(key: str, a0: int, b0: int) -> float | None:
        vals = [v for s in p[key].values() if (v := period_rate(s, a0, b0)) is not None]
        return statistics.median(vals) if vals else None

    pdr = peak_decade({a0: med_rate(DEBT, a0, b0) for a0, b0 in DESIGN_PERIODS})
    phr = peak_decade({a0: med_rate(HH, a0, b0) for a0, b0 in DESIGN_PERIODS})
    print(
        f"- 頑健性（設計書の区切り、国ごとの年当たり変化の中央値）: 政府債務 {pdr}–、家計 {phr}– → "
        f"{judge_h3_design(pi, pdr, phr)}"
    )

    # ---- H3b ----
    print("\n## H3b: 総負債（公的 + 民間非金融）の最大年")
    _row(
        [
            "国",
            "データ期間",
            "全期間の最大年",
            "最大値",
            "2019",
            "2020",
            "〜2019 の最大が 2019（主）",
            "最大が 2020",
            "最大が 2008 以降",
        ]
    )
    _row(["---"] * 9)
    n19b = n20b = n_2008 = 0
    not_latest_2008: list[str] = []
    for iso in isos:
        s = p[TOTAL][iso]
        my = max_year(s)
        assert my is not None
        end19 = 2019 if 2019 in s else max(y for y in s if y <= 2019)
        hit19 = max_year_through(s, end19) == end19
        hit20 = my == 2020
        post = my >= 2008
        n19b += hit19
        n20b += hit20
        n_2008 += post
        if post and my not in (2019, 2020):
            not_latest_2008.append(f"{iso} {my}")
        _row(
            [
                f"{NAMES[iso]}（{iso}）",
                f"{min(s)}–{max(s)}（{len(s)} 年）",
                my,
                _f(s[my]),
                _f(s.get(2019)),
                _f(s.get(2020)),
                ("○" if hit19 else "") + ("" if end19 == 2019 else f"（{end19} で判定）"),
                "○" if hit20 else "",
                "○" if post else "",
            ]
        )
    print(
        f"- 主（設計書の主年 2019。2019 欠損国は最終観測年）: {n19b} / {n} → "
        f"**H3b 判定: {judge_h3b(n19b, n)}**"
    )
    print(f"- 「最新年」= 2020 と読む: {n20b} / {n} → {judge_h3b(n20b, n)}")
    print(f"- 最大が 2008 以降（逸脱した広い読み方）: {n_2008} / {n} → {judge_h3b(n_2008, n)}")
    print(f"- 2008 以降だが 2019/2020 でない国: {', '.join(not_latest_2008) or 'なし'}")
    g20 = p[G]
    shrink = sorted(iso for iso in isos if g20.get(iso, {}).get(2020, 0.0) < 0)
    print(
        f"- 2020 年に名目 GDP が縮小した国（分母が縮む）: {len(shrink)} / {n}"
        f"（{', '.join(shrink)}）"
    )
    n_pub_latest = sum(1 for iso in isos if max_year(p[DEBT][iso]) in (2019, 2020))
    n_priv_latest = sum(1 for iso in isos if max_year(p[PRIV][iso]) in (2019, 2020))
    print(
        f"- 参考: 公的債務単独で最大が 2019/2020 の国 {n_pub_latest} / {n}、"
        f"民間非金融単独で {n_priv_latest} / {n}"
    )

    # ---- H4 ----
    print("\n## H4: 利子率")
    lt_hist = pooled(p, LT, 1870, 2008)
    lt_rec = pooled(p, LT, 2012, 2020)
    s_hist, s_rec = share_below(lt_hist, 1.0), share_below(lt_rec, 1.0)
    j4a = judge_h4a(s_hist, s_rec)
    print(
        f"- (a) 長期金利 < 1%: 1870–2008 {100 * s_hist:.2f}%（{sum(v < 1 for v in lt_hist)} / "
        f"{len(lt_hist)} 国・年）、2012–2020 {100 * s_rec:.1f}%（{sum(v < 1 for v in lt_rec)} / "
        f"{len(lt_rec)}）→ **H4(a) 判定: {j4a}**"
    )
    hist_cases = sorted(
        (iso, y, v)
        for iso, s in p[LT].items()
        for y, v in s.items()
        if 1870 <= y <= 2008 and v < 1.0
    )
    print(f"  - 1870–2008 の 1% 未満: {', '.join(f'{i} {y}（{v:.2f}）' for i, y, v in hist_cases)}")
    first_below = {
        iso: min((y for y, v in s.items() if v < 1.0), default=None) for iso, s in p[LT].items()
    }
    print(
        "  - 各国で初めて 1% 未満になった年: "
        + "、".join(f"{k} {v}" for k, v in sorted(first_below.items()) if v is not None)
    )
    never = sorted(k for k, v in first_below.items() if v is None)
    print(f"  - 2020 年まで一度も 1% 未満にならなかった国: {', '.join(never) or 'なし'}")
    for a0, b0 in ((2012, 2019), (2015, 2020), (2019, 2020)):
        v = pooled(p, LT, a0, b0)
        print(f"  - 探索的: {a0}–{b0} の 1% 未満 {100 * share_below(v, 1.0):.1f}%（n={len(v)}）")
    rg45 = pooled_r_minus_g(p, 1945, 1980)
    rg10 = pooled_r_minus_g(p, 2010, 2020)
    s45, s10 = share_below(rg45, 0.0), share_below(rg10, 0.0)
    j4b = judge_h4b(s45, s10)
    print(
        f"- (b) r − g < 0: 1945–1980 {100 * s45:.1f}%（n={len(rg45)}）、2010–2020 "
        f"{100 * s10:.1f}%（n={len(rg10)}）、比 {s45 / s10:.2f} → **H4(b) 判定: {j4b}**"
    )
    print(
        f"  - 中央値: 1945–1980 {statistics.median(rg45):+.2f}pt、2010–2020 "
        f"{statistics.median(rg10):+.2f}pt"
    )
    rg10_19 = pooled_r_minus_g(p, 2010, 2019)
    rg46 = pooled_r_minus_g(p, 1946, 1980)
    print(
        f"  - 頑健性: 2010–2019（コロナ年除く）{100 * share_below(rg10_19, 0):.1f}%、"
        f"1946–1980（終戦年除く）{100 * share_below(rg46, 0):.1f}%"
    )
    rg45s = pooled_r_minus_g(p, 1945, 1980, r_key=ST)
    rg10s = pooled_r_minus_g(p, 2010, 2020, r_key=ST)
    print(
        f"  - 探索的: r = 短期金利なら 1945–1980 {100 * share_below(rg45s, 0):.1f}%、"
        f"2010–2020 {100 * share_below(rg10s, 0):.1f}%"
    )
    lt_periods = [
        ("1870–1913", 1870, 1913),
        ("1914–1945", 1914, 1945),
        ("1946–1980", 1946, 1980),
        ("1981–2008", 1981, 2008),
        ("2012–2020", 2012, 2020),
    ]
    rg_periods = [
        ("1870–1913", 1870, 1913),
        ("1914–1944", 1914, 1944),
        ("1945–1980", 1945, 1980),
        ("1981–2009", 1981, 2009),
        ("2010–2020", 2010, 2020),
    ]
    lt_groups = [(nm, pooled(p, LT, a, b)) for nm, a, b in lt_periods]
    rg_groups = [(nm, pooled_r_minus_g(p, a, b)) for nm, a, b in rg_periods]
    _row(["期間（長期金利）", "国・年", "中央値（%）", "< 1% の割合"])
    _row(["---"] * 4)
    for nm, g in lt_groups:
        _row([nm, len(g), _f(statistics.median(g), 2), f"{100 * share_below(g, 1.0):.1f}%"])
    _row(["期間（r − g）", "国・年", "中央値（pt）", "< 0 の割合"])
    _row(["---"] * 4)
    for nm, g in rg_groups:
        _row([nm, len(g), _f(statistics.median(g), 2), f"{100 * share_below(g, 0.0):.1f}%"])

    # ---- H6(a) ----
    print("\n## H6(a): 日本")
    d2020 = {iso: p[DEBT][iso][2020] for iso in isos if 2020 in p[DEBT][iso]}
    jp20, jp44 = d2020[JP], p[DEBT][JP][1944]
    others = {k: v for k, v in d2020.items() if k != JP}
    j6 = judge_h6a(jp20, others, jp44)
    top3 = sorted(d2020.items(), key=lambda kv: -kv[1])[:4]
    print(
        f"- 日本 2020 {jp20:.1f}%（1944 {jp44:.1f}%）。2020 年の上位: "
        + "、".join(f"{k} {v:.1f}" for k, v in top3)
        + f" → **H6(a) 判定: {j6}**"
    )
    jp = p[DEBT][JP]
    print(
        "- 日本の推移: "
        + "、".join(
            f"{y} {jp[y]:.0f}"
            for y in (
                1875,
                1905,
                1920,
                1935,
                1944,
                1946,
                1950,
                1965,
                1975,
                1990,
                2000,
                2007,
                2019,
                2020,
            )
            if y in jp
        )
    )
    jp_tot = p[TOTAL][JP]
    jmy = max_year(jp_tot)
    assert jmy is not None
    print(
        f"- 日本の総負債（公的 + 民間）最大 {jmy} 年 {jp_tot[jmy]:.0f}%、"
        f"最終観測 {max(jp_tot)} 年 {jp_tot[max(jp_tot)]:.0f}%（2020 年は民間が欠損）"
    )
    jlt = p[LT][JP]
    print(
        "- 日本の長期金利: "
        + "、".join(
            f"{y} {jlt[y]:.2f}" for y in (1990, 1997, 1998, 2003, 2012, 2016, 2020) if y in jlt
        )
    )

    # ---- figures ----
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    fig_small_multiples(p, NAMES, args.fig_dir / "r1_debt_small_multiples.png")
    fig_h3(med, p, args.fig_dir / "r1_h3_medians.png")
    fig_h4(lt_groups, rg_groups, args.fig_dir / "r1_h4_rates_boxplot.png")
    fig_h2b(
        [
            (
                "1945–1975（起点が 1945 年欠損の国は 1946–1950 年）: 債務比率の変化の分解",
                all_decs["main"]["1945–1975"],
                1945,
            ),
            ("1980–2007: 債務比率の変化の分解", all_decs["main"]["1980–2007"], 1980),
        ],
        args.fig_dir / "r1_h2b_decomposition.png",
    )
    print(
        "\n図: r1_debt_small_multiples.png, r1_h3_medians.png, r1_h4_rates_boxplot.png, "
        "r1_h2b_decomposition.png"
    )


if __name__ == "__main__":
    main()
