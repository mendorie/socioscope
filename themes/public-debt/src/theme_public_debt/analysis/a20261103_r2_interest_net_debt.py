"""R2: 純利払い・純債務・総負債の世界拡張（H5・H6(a)(b)、補助: H3b の GDD 拡張）。

事前登録（design/themes/public-debt.md、2026-11-03）。閾値は設計書のまま:
  H5   : JST 18 か国で、純利払い対 GDP 比が 2019 年に起点年（1990 年。データの始まる国は
         米 2001・独 1991・愛 1995・蘭 1995）の半分以下の国が過半（≥10）、かつ 2024 年に 2019 年
         より上がった国が過半（≥10）。両方満たせば整合、前半のみなら中間、前半を満たさなければ不支持。
         起点が 0 以下（純利子受取の国）は「半分以下」が定義できないので「満たさない」に数える。
  H6(a): 日本の一般政府総債務（JST 2020 年、IMF WEO 2024 年）が両方で 18 か国の最高で、かつ
         JST の日本 1944 年（204%）を上回れば整合。
  H6(b): 純債務（IMF FM、2024 年）での日本の順位（大きい方から）が総債務（IMF WEO、2024 年）の順位
         より下がれば整合。下がらなければ不支持（首位のままなら「定義を変えても首位」）。
         市中保有（中銀保有控除）はデータ未採用のため対象外。
  補助 : GDD で 一般政府総債務（GG_DEBT_GDP）＋ 民間非金融債務（PVD_LS）の 1950 年以降の最大年が
         2008 年以降の国の割合（両方ある国・年のみ）。H3b の母集団拡張の参考値で、判定はしない。

純利払い（interest_gdp）は IMF Fiscal Monitor の 基礎的財政収支 − 総合収支（いずれも FM の値、
丸めなし）で、利払い − 利子受取（純利払い）の対 GDP 比。グロスの利払いではない。
「前半を満たさなければ不支持」は設計書に無い補完ルール（report の逸脱 7）。

決定的スクリプト（乱数なし）。入力は data/marts/public_debt_panel.parquet。純粋ヘルパは
tests/test_analysis_r2.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
import statistics
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

THEME_DIR = Path(__file__).resolve().parents[3]
SRC_FM = "IMF Fiscal Monitor（DataMapper、2026-11-03 取得）"
SRC_WEO = "IMF World Economic Outlook 2026 年 10 月版（DataMapper、2026-11-03 取得）"
SRC_GDD = "IMF Global Debt Database 2025 年 9 月版（DataMapper、2026-11-03 取得）"
SRC_JST = "Jordà–Schularick–Taylor Macrohistory Database R6（CC BY-NC-SA 4.0）"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"

JST18: tuple[str, ...] = (
    "AUS", "BEL", "CAN", "CHE", "DEU", "DNK", "ESP", "FIN", "FRA",
    "GBR", "IRL", "ITA", "JPN", "NLD", "NOR", "PRT", "SWE", "USA",
)  # fmt: skip
NAMES: dict[str, str] = {
    "AUS": "豪",
    "BEL": "ベルギー",
    "CAN": "加",
    "CHE": "スイス",
    "DEU": "独",
    "DNK": "デンマーク",
    "ESP": "スペイン",
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
H5_START = 1990
MAJORITY_18 = 10
PEAK_1944 = 1944
GDD_START = 1950
GDD_CUTOFF = 2008
ESTIMATE_YEAR = 2025  # WEO/FM の 2025 年は一部推計

Series = dict[int, float]

# ---- pure helpers: H5 -------------------------------------------------------------------------


def base_year(years: Iterable[int], start: int = H5_START) -> int | None:
    """start 以降で最初に値のある年（H5 の起点）。無ければ None。"""
    ys = [y for y in years if y >= start]
    return min(ys) if ys else None


def halved(base: float, later: float) -> bool | None:
    """later が base の半分以下か。base ≤ 0（純利子受取）は比が定義できないので None。"""
    if base <= 0:
        return None
    return later <= base / 2


def judge_h5(n_halved: int, n_rose: int, threshold: int = MAJORITY_18) -> str:
    """前半（2019 ≤ 起点 / 2）と後半（2024 > 2019）が両方 ≥ threshold なら整合、前半のみ中間。"""
    if n_halved < threshold:
        return "不支持"
    if n_rose < threshold:
        return "中間"
    return "整合"


def h5_counts(
    s: Mapping[str, Mapping[int, float]],
    mid: int = 2019,
    late: int = 2024,
    start: int = H5_START,
    fixed_base: int | None = None,
) -> tuple[int, int, int]:
    """(半分以下の国数, late > mid の国数, 起点が 0 以下で前半を判定できない国数)。

    fixed_base を与えると全ての国でその年を起点にする（無い国は前半を満たさない扱い）。
    """
    n_half = n_rose = n_undef = 0
    for vals in s.values():
        b = fixed_base if fixed_base is not None else base_year(vals, start)
        if b is not None and b in vals and mid in vals:
            h = halved(vals[b], vals[mid])
            if h is None:
                n_undef += 1
            elif h:
                n_half += 1
        if mid in vals and late in vals and vals[late] > vals[mid]:
            n_rose += 1
    return n_half, n_rose, n_undef


# ---- pure helpers: H6 -------------------------------------------------------------------------


def rank_desc(values: Mapping[str, float], iso3: str) -> int:
    """大きい方から数えた順位（1 始まり。厳密に大きい国の数 + 1。同値は同順位）。"""
    v = values[iso3]
    return 1 + sum(1 for k, x in values.items() if k != iso3 and x > v)


def judge_h6a(rank_jst: int, rank_weo: int, jp_jst: float, jp_weo: float, peak: float) -> str:
    """JST・WEO の両方で首位、かつ両方の値が 1944 年のピークを上回れば整合。"""
    ok = rank_jst == 1 and rank_weo == 1 and jp_jst > peak and jp_weo > peak
    return "整合" if ok else "不支持"


def judge_h6b(rank_gross: int, rank_net: int) -> str:
    """純債務の順位が総債務の順位より下がれば（数字が大きくなれば）整合。"""
    return "整合" if rank_net > rank_gross else "不支持"


def judge_h6(
    rank_jst: int,
    rank_weo: int,
    jp_jst: float,
    jp_weo: float,
    peak: float,
    rank_net: int,
) -> tuple[str, str]:
    """(H6(a), H6(b))。H6(b) の総債務順位は WEO の順位を使う。"""
    return judge_h6a(rank_jst, rank_weo, jp_jst, jp_weo, peak), judge_h6b(rank_weo, rank_net)


# ---- pure helpers: GDD ------------------------------------------------------------------------


def total_debt(gov: Mapping[int, float], priv: Mapping[int, float]) -> Series:
    """両方に値がある年だけの 公的 + 民間。"""
    return {y: gov[y] + priv[y] for y in sorted(set(gov) & set(priv))}


def peak_year(s: Mapping[int, float], start: int = GDD_START) -> int | None:
    """start 以降の最大値の年。同値は最も早い年（「2008 年以降」を多めに数えない側）。"""
    best: tuple[int, float] | None = None
    for y in sorted(s):
        if y < start:
            continue
        if best is None or s[y] > best[1]:
            best = (y, s[y])
    return None if best is None else best[0]


def share_peak_after(peaks: Mapping[str, int], cutoff: int = GDD_CUTOFF) -> tuple[int, int]:
    """(最大年が cutoff 以降の国数, 国数)。"""
    return sum(1 for y in peaks.values() if y >= cutoff), len(peaks)


# ---- loader -----------------------------------------------------------------------------------


def series(
    mart: pl.DataFrame,
    source: str,
    unit: str,
    metric: str,
    countries: Sequence[str] | None = None,
) -> dict[str, Series]:
    """long 形式 mart から iso3 → {year: value}。null は落とす。キー重複は ValueError。"""
    f = mart.filter(
        (pl.col("source") == source)
        & (pl.col("unit") == unit)
        & (pl.col("metric") == metric)
        & pl.col("value").is_not_null()
    )
    if countries is not None:
        f = f.filter(pl.col("iso3").is_in(list(countries)))
    out: dict[str, Series] = {}
    for iso, year, value in f.select("iso3", "year", "value").sort("iso3", "year").iter_rows():
        s = out.setdefault(str(iso), {})
        if int(year) in s:
            msg = f"duplicate {source}/{unit}/{metric} {iso} {year}"
            raise ValueError(msg)
        s[int(year)] = float(value)
    return out


def at(s: Mapping[str, Mapping[int, float]], year: int) -> dict[str, float]:
    return {k: v[year] for k, v in s.items() if year in v}


# ---- figures ----------------------------------------------------------------------------------


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


def fig_interest_small_multiples(s: Mapping[str, Series], path: Path) -> None:
    import matplotlib.pyplot as plt

    order = sorted(s, key=lambda k: -s[k].get(2019, 0.0))
    fig, axes = plt.subplots(3, 6, figsize=(12.0, 6.6), sharex=True, sharey=True)
    for ax, iso in zip(axes.flat, order, strict=True):
        v = s[iso]
        ys = sorted(y for y in v if y < ESTIMATE_YEAR)
        col = SERIES[1] if iso == JP else SERIES[0]
        ax.plot(ys, [v[y] for y in ys], color=col, linewidth=1.2)
        if ESTIMATE_YEAR in v and ESTIMATE_YEAR - 1 in v:
            ax.plot(
                [ESTIMATE_YEAR - 1, ESTIMATE_YEAR],
                [v[ESTIMATE_YEAR - 1], v[ESTIMATE_YEAR]],
                color=col,
                linewidth=1.2,
                linestyle=":",
            )
        for y, mk in ((2019, "o"), (2024, "s")):
            if y in v:
                ax.scatter([y], [v[y]], color=INK, s=10, marker=mk, zorder=3)
        ax.axhline(0, color=MUTED, linewidth=0.6)
        b = base_year(v)
        ax.set_title(f"{NAMES[iso]}（{iso}、起点 {b}）", fontsize=8, color=INK, loc="left")
        _style(ax)
    for ax in axes[:, 0]:
        ax.set_ylabel("純利払い（対 GDP %）", fontsize=7, color=INK)
    fig.suptitle(
        "一般政府の純利払い（利払い − 利子受取）対 GDP 比 1990–2025"
        "（JST 18 か国、2019 年の大きい順）",
        fontsize=10,
        color=INK,
        x=0.01,
        ha="left",
    )
    _footer(
        fig,
        f"出典: {SRC_FM}。基礎的財政収支 − 総合収支（いずれも FM）で導出、グロスの利払いではない。"
        "\n"
        "● 2019 年、■ 2024 年、点線 = 2025 年（一部推計）。縦軸は全国共通。n = 18 か国",
    )
    fig.tight_layout(rect=(0, 0.025, 1, 0.96))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_interest_dots(s: Mapping[str, Series], path: Path) -> None:
    import matplotlib.pyplot as plt

    order = sorted(s, key=lambda k: s[k].get(2019, 0.0))
    fig, ax = plt.subplots(figsize=(7.4, 6.6))
    marks = (
        ("起点（1990 年。米 2001・独 1991・愛蘭 1995）", None, SERIES[6], "D"),
        ("2007 年", 2007, MUTED, "|"),
        ("2019 年", 2019, SERIES[0], "o"),
        ("2024 年", 2024, SERIES[1], "s"),
    )
    for label, year, col, mk in marks:
        xs, ys = [], []
        for i, iso in enumerate(order):
            v = s[iso]
            y = base_year(v) if year is None else year
            if y is not None and y in v:
                xs.append(v[y])
                ys.append(i)
        ax.scatter(xs, ys, color=col, marker=mk, s=22, label=label, zorder=3)
    ax.axvline(0, color=MUTED, linewidth=0.6)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{NAMES[k]}（{k}）" for k in order], fontsize=7)
    ax.set_xlabel("純利払い（対 GDP %、負 = 純利子受取）", fontsize=8, color=INK)
    ax.set_title(
        "純利払いの対 GDP 比: 起点・2007・2019・2024 年", fontsize=10, color=INK, loc="left"
    )
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    _style(ax, "x")
    _footer(fig, f"出典: {SRC_FM}。基礎的財政収支 − 総合収支（いずれも FM）。n = 18 か国")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_gross_net(gross: Mapping[str, float], net: Mapping[str, float], path: Path) -> None:
    import matplotlib.pyplot as plt

    order = sorted(gross, key=lambda k: gross[k])
    fig, ax = plt.subplots(figsize=(7.4, 6.4))
    for i, iso in enumerate(order):
        if iso in net:
            ax.plot([net[iso], gross[iso]], [i, i], color=GRID, linewidth=2.0, zorder=1)
    ax.scatter(
        [gross[k] for k in order],
        range(len(order)),
        color=SERIES[0],
        s=24,
        label="総債務（WEO）",
        zorder=3,
    )
    ax.scatter(
        [net[k] for k in order if k in net],
        [i for i, k in enumerate(order) if k in net],
        color=SERIES[1],
        marker="s",
        s=22,
        label="純債務（Fiscal Monitor）",
        zorder=3,
    )
    ax.axvline(0, color=MUTED, linewidth=0.6)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([f"{NAMES[k]}（{k}）" for k in order], fontsize=7)
    ax.set_xlabel("一般政府債務（対 GDP %）", fontsize=8, color=INK)
    ax.set_title(
        "一般政府の総債務と純債務（2024 年、上から総債務の大きい順）",
        fontsize=10,
        color=INK,
        loc="left",
    )
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    _style(ax, "x")
    _footer(
        fig,
        f"出典: {SRC_WEO}（総債務）、\n{SRC_FM}（純債務）。"
        "線の長さ = 総 − 純（政府の金融資産）。n = 18 か国",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_gdd_peaks(peaks: Mapping[str, int], path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    years = sorted(set(peaks.values()))
    others = [sum(1 for k, y in peaks.items() if y == yy and k not in JST18) for yy in years]
    jst = [sum(1 for k, y in peaks.items() if y == yy and k in JST18) for yy in years]
    ax.bar(years, others, color=SERIES[0], label="JST 18 か国以外")
    ax.bar(years, jst, bottom=others, color=SERIES[1], label="JST 18 か国")
    ax.axvline(GDD_CUTOFF - 0.5, color=INK, linewidth=0.8, linestyle="--")
    ax.text(GDD_CUTOFF - 0.3, max(o + j for o, j in zip(others, jst, strict=True)), " 2008 年")
    ax.set_xlabel("公的（一般政府）＋ 民間非金融 債務の対 GDP 比が最大の年", fontsize=8, color=INK)
    ax.set_ylabel("国の数", fontsize=8, color=INK)
    k, n = share_peak_after(peaks)
    ax.set_title(
        f"総負債の最大年（GDD、1950–2024）: 2008 年以降は {k} / {n} か国",
        fontsize=10,
        color=INK,
        loc="left",
    )
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    _style(ax)
    _footer(
        fig,
        f"出典: {SRC_GDD}。GG_DEBT_GDP ＋ PVD_LS（貸出＋債券）。\n"
        f"両方ある国・年のみ、始まりの年は国により 1950–2011。同値は早い年。n = {n} か国",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- report printing --------------------------------------------------------------------------


def _f(v: float | None, nd: int = 2) -> str:
    return "–" if v is None else f"{v:.{nd}f}"


def _row(cells: Sequence[object]) -> None:
    print("| " + " | ".join(str(c) for c in cells) + " |")


def _yn(b: bool | None) -> str:
    return "定義不能" if b is None else ("○" if b else "×")


def _print_h5(s: Mapping[str, Series]) -> tuple[str, int, int]:
    n_half, n_rose, n_undef = h5_counts(s)
    h5 = judge_h5(n_half, n_rose)
    print("\n## H5: 純利払い（利払い − 利子受取）対 GDP 比（IMF FM）")
    print(f"- 2019 ≤ 起点 / 2 の国: {n_half} / 18（起点が 0 以下で定義できない国 {n_undef}）")
    print(f"- 2024 > 2019 の国: {n_rose} / 18")
    print(f"- **H5 判定: {h5}**")
    print("\n| 国 | 起点年 | 起点 | 2007 | 2019 | 2024 | 2025（推計） | 2019 / 起点 "
          "| 2019 ≤ 起点/2 | 2024 > 2019 | 2025 > 2019 |")  # fmt: skip
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for iso in sorted(s, key=lambda k: -s[k][2019]):
        v = s[iso]
        b = base_year(v)
        assert b is not None
        h = halved(v[b], v[2019])
        ratio = v[2019] / v[b] if v[b] > 0 else None
        _row(
            [
                f"{NAMES[iso]}（{iso}）",
                b,
                _f(v[b]),
                _f(v.get(2007)),
                _f(v[2019]),
                _f(v.get(2024)),
                _f(v.get(ESTIMATE_YEAR)),
                _f(ratio),
                _yn(h),
                _yn(v[2024] > v[2019]),
                _yn(v[ESTIMATE_YEAR] > v[2019]),
            ]
        )
    med = {y: statistics.median(at(s, y).values()) for y in (2007, 2019, 2022, 2023, 2024, 2025)}
    print("\n- 18 か国中央値: " + "、".join(f"{y} 年 {_f(m)}" for y, m in med.items()))
    v24 = at(s, 2024)
    low = 1 + sum(1 for x in v24.values() if x < v24[JP])
    print(f"- 日本 2024 年 {_f(v24[JP], 3)}%: 18 か国で小さい方から {low} 番目")
    small = sorted(k for k in s if 0 < s[k][2024] - s[k][2019] < 0.05)
    print("- 2024 > 2019 のうち上昇幅 0.05 pt 未満の国: " + (", ".join(small) or "なし"))
    d = [s[k][2024] - s[k][2019] for k in sorted(s)]
    print(f"- 2024 − 2019 の変化（pt）: 中央値 {_f(statistics.median(d))}、"
          f"最小 {_f(min(d))}、最大 {_f(max(d))}")  # fmt: skip

    print("\n### H5 頑健性（判定の閾値 ≥ 10 は固定）")
    print("| 仕様 | 前半（半分以下） | 後半（上昇） | 判定 |")
    print("|---|---|---|---|")
    _row(["主仕様（起点 1990 等、2019 vs 2024）", f"{n_half} / 18", f"{n_rose} / 18", h5])
    pos = {k: v for k, v in s.items() if v[base_year(v) or 0] > 0}
    a, b_, _ = h5_counts(pos)
    _row([f"起点が負の国を母数から除外（n = {len(pos)}、探索的・事後）", f"{a} / {len(pos)}",
          f"{b_} / {len(pos)}",
          f"{judge_h5(a, b_)}（閾値 10。過半 {len(pos) // 2 + 1} でも "
          f"{judge_h5(a, b_, len(pos) // 2 + 1)}）"])  # fmt: skip
    for late in (2023, ESTIMATE_YEAR):
        a, b_, _ = h5_counts(s, late=late)
        _row([f"後半を 2019 vs {late}（探索的・事後）", f"{a} / 18", f"{b_} / 18", judge_h5(a, b_)])
    a, b_, _ = h5_counts(s, fixed_base=2001)
    _row(["起点を全国 2001 年に統一（探索的・事後）", f"{a} / 18", f"{b_} / 18", judge_h5(a, b_)])
    a, b_, _ = h5_counts(s, mid=2021, late=2024)
    _row(["中間年を 2021 年（探索的・事後）", f"{a} / 18", f"{b_} / 18",
          judge_h5(a, b_)])  # fmt: skip
    return h5, n_half, n_rose


def _print_h6(
    jst: Mapping[str, Series], weo: Mapping[str, Series], net: Mapping[str, Series]
) -> tuple[str, str]:
    jp_peak = jst[JP][PEAK_1944]
    first_above = min(y for y, v in jst[JP].items() if y > PEAK_1944 and v > jp_peak)
    j20, w24, n24 = at(jst, 2020), at(weo, 2024), at(net, 2024)
    r_j, r_w, r_n = rank_desc(j20, JP), rank_desc(w24, JP), rank_desc(n24, JP)
    h6a, h6b = judge_h6(r_j, r_w, j20[JP], w24[JP], jp_peak, r_n)
    print("\n## H6: 日本の総債務・純債務の順位")
    print(f"- JST 日本 1944 年 {_f(jp_peak, 1)}%（1945 年は欠損）。JST で初めて上回った年 "
          f"{first_above}（{_f(jst[JP][first_above], 1)}%）")  # fmt: skip
    print(f"- H6(a): JST 2020 年 {_f(j20[JP], 1)}%（{r_j} 位 / {len(j20)}）、"
          f"WEO 2024 年 {_f(w24[JP], 1)}%（{r_w} 位 / {len(w24)}） → **判定: {h6a}**")  # fmt: skip
    print(f"- H6(b): 総債務 WEO 2024 {r_w} 位、純債務 FM 2024 {r_n} 位 → **判定: {h6b}**")
    print("\n| 総債務順位 | 国 | 総債務 WEO 2024 | 純債務 FM 2024 | 純債務順位 | 総 − 純 "
          "| JST 2020 総債務（順位） |")  # fmt: skip
    print("|---|---|---|---|---|---|---|")
    for iso in sorted(w24, key=lambda k: -w24[k]):
        g, n = w24[iso], n24.get(iso)
        _row(
            [
                rank_desc(w24, iso),
                f"{NAMES[iso]}（{iso}）",
                _f(g, 1),
                _f(n, 1),
                rank_desc(n24, iso) if n is not None else "–",
                _f(None if n is None else g - n, 1),
                f"{_f(j20.get(iso), 1)}（{rank_desc(j20, iso)}）" if iso in j20 else "–",
            ]
        )
    print("\n### H6(b) 頑健性（年を変える、探索的・事後）")
    print("| 年 | 日本 総債務 WEO（順位） | 日本 純債務 FM（順位） | 日本以外の純債務最大 | 判定 |")
    print("|---|---|---|---|---|")
    for y in (2007, 2019, 2024, ESTIMATE_YEAR):
        wg, nn = at(weo, y), at(net, y)
        if JP not in wg or JP not in nn:
            continue
        second = max((k for k in nn if k != JP), key=lambda k: nn[k])
        _row([y, f"{_f(wg[JP], 1)}（{rank_desc(wg, JP)} / {len(wg)}）",
              f"{_f(nn[JP], 1)}（{rank_desc(nn, JP)} / {len(nn)}）",
              f"{NAMES[second]} {_f(nn[second], 1)}",
              judge_h6b(rank_desc(wg, JP), rank_desc(nn, JP))])  # fmt: skip
    return h6a, h6b


def _print_gdd(gov: Mapping[str, Series], priv: Mapping[str, Series]) -> dict[str, int]:
    tot = {k: total_debt(gov[k], priv[k]) for k in sorted(set(gov) & set(priv))}
    tot = {k: v for k, v in tot.items() if any(y >= GDD_START for y in v)}
    peaks = {k: y for k, v in tot.items() if (y := peak_year(v)) is not None}
    k, n = share_peak_after(peaks)
    print("\n## 補助（H3b の母集団拡張、判定なし）: GDD 公的（一般政府）＋ 民間の最大年")
    print(f"- 一般政府 {len(gov)} か国、民間 {len(priv)} か国、両方ある国 {n}")
    print(f"- 最大年が {GDD_CUTOFF} 年以降: **{k} / {n}（{100 * k / n:.0f}%）**")
    starts = {c: min(v) for c, v in tot.items()}
    for lim in (1995, 1980, 1970):
        sub = {c: y for c, y in peaks.items() if starts[c] <= lim}
        a, m = share_peak_after(sub)
        print(f"- 頑健性（探索的・事後）: 系列が {lim} 年以前から始まる国に限ると {a} / {m}"
              f"（{100 * a / m:.0f}%）")  # fmt: skip
    no_covid = {
        c: y
        for c, v in tot.items()
        if (y := peak_year({yy: x for yy, x in v.items() if yy not in (2020, 2021)})) is not None
    }
    a, m = share_peak_after(no_covid)
    pct = 100 * a / m
    print(f"- 頑健性（探索的・事後）: 2020・2021 年を除いて最大年を取ると {a} / {m}（{pct:.0f}%）")
    latest = sum(1 for c, y in peaks.items() if y == max(tot[c]))
    print(f"- 参考: 最大年がその国の最新年（多くは 2024）である国 {latest} / {n}")
    late = sorted(c for c, y in peaks.items() if y >= GDD_CUTOFF)
    early = sorted(c for c, y in peaks.items() if y < GDD_CUTOFF)
    print(f"- 2008 年以降が最大（{len(late)}）: " + ", ".join(f"{c} {peaks[c]}" for c in late))
    print(f"- 2008 年より前が最大（{len(early)}）: " + ", ".join(f"{c} {peaks[c]}" for c in early))
    jst_in = sorted(c for c in peaks if c in JST18)
    print(f"- JST 18 か国のうち GDD で両方ある国 {len(jst_in)}: "
          + ", ".join(f"{c} {peaks[c]}（始 {starts[c]}）" for c in jst_in))  # fmt: skip
    n1920 = sum(1 for c in jst_in if peaks[c] in (2019, 2020))
    print(f"- 同 18 か国で GDD の最大年が 2019・2020 年: {n1920} / {len(jst_in)}")
    return peaks


# ---- main -------------------------------------------------------------------------------------


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
    interest = series(mart, "imf_fm", "general_gov_gross", "interest_gdp", JST18)
    weo = series(mart, "imf_weo", "general_gov_gross", "debt_gdp", JST18)
    net = series(mart, "imf_fm", "general_gov_net", "debt_gdp", JST18)
    jst = series(mart, "jst", "general_gov_gross", "debt_gdp", JST18)
    gdd_gov = series(mart, "imf_gdd", "general_gov_gross", "debt_gdp")
    gdd_priv = series(mart, "imf_gdd", "private_nonfin", "debt_gdp")
    for name, s in (("interest", interest), ("weo", weo), ("net", net), ("jst", jst)):
        if len(s) != len(JST18):
            msg = f"{name}: expected {len(JST18)} countries, got {sorted(s)}"
            raise ValueError(msg)

    print("# R2 純利払い・純債務・総負債の世界拡張（H5・H6・H3b 補助）（2026-11-03）")
    print(f"- mart: public_debt_panel {mart.height} 行")
    for label, s in (
        ("FM 純利払い", interest),
        ("WEO 総債務", weo),
        ("FM 純債務", net),
        ("JST 総債務", jst),
        ("GDD 一般政府", gdd_gov),
        ("GDD 民間", gdd_priv),
    ):
        n_obs = sum(len(v) for v in s.values())
        y0 = min(min(v) for v in s.values())
        y1 = max(max(v) for v in s.values())
        print(f"- {label}: {len(s)} か国、{n_obs} 国・年、{y0}–{y1}")
    starts = {k: base_year(v) for k, v in interest.items()}
    print("- H5 起点が 1990 年でない国: "
          + ", ".join(f"{k} {y}" for k, y in sorted(starts.items()) if y != H5_START))  # fmt: skip

    h5, _, _ = _print_h5(interest)
    h6a, h6b = _print_h6(jst, weo, net)
    peaks = _print_gdd(gdd_gov, gdd_priv)

    print(f"\n## まとめ: H5 {h5}、H6(a) {h6a}、H6(b) {h6b}")

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    fig_interest_small_multiples(interest, args.fig_dir / "r2_net_interest_small_multiples.png")
    fig_interest_dots(interest, args.fig_dir / "r2_net_interest_dots.png")
    fig_gross_net(at(weo, 2024), at(net, 2024), args.fig_dir / "r2_gross_vs_net_2024.png")
    fig_gdd_peaks(peaks, args.fig_dir / "r2_gdd_total_debt_peak_year.png")
    print(
        f"\n図: {args.fig_dir}/r2_net_interest_small_multiples.png, r2_net_interest_dots.png, "
        "r2_gross_vs_net_2024.png, r2_gdd_total_debt_peak_year.png"
    )


if __name__ == "__main__":
    main()
