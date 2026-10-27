"""R1: 人口当たり国会議員数の国際比較（H1・H1b・H1c）。

事前登録（design/themes/parliament-size.md、2026-10-27）:
  H1  : 日本の人口 100 万人当たり議員数は、下院のみ・両院合計の両方で OECD 38 か国の少ない方から
        5 位以内なら整合。どちらかが 10 位以下なら不支持。
  H1b : 下院定数 ÷ 人口の立方根（立方根法則）の順位が 13〜26 位（中央 3 分の 1）なら整合。
  H1c : 1 割減（衆院 420）・比例 45 減（420）・比例 31 減（434）のいずれでも H1 と H1b の判定が
        変わらなければ整合。

決定的スクリプト。入力は data/marts/ipu_parliaments.parquet（IPU Parline、CC BY-NC-SA 4.0）。
議員数は定数（statutory_members_number の最新値）、人口は Parline の population_in_thousands
（最新年、ほぼ 2023）。上院が非公選の国（英・加 など）は両院合計の表に注記する。

純粋ヘルパ（per_million, cube_ratio, rank_of, judge_h1, judge_h1b, judge_h1c, with_reduction）は
tests/test_analysis_r1.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import polars as pl

THEME_DIR = Path(__file__).resolve().parents[3]
_SRC = "IPU Parline（data.ipu.org、2026-10-27 取得、CC BY-NC-SA 4.0）"
SOURCE_NOTE = _SRC + "。定数ベース、人口は Parline 収録値"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
PEERS = ("USA", "DEU", "GBR", "FRA", "ITA", "KOR", "MEX", "TUR", "ESP", "CAN", "AUS", "POL")

# 削減案（2026-10-27 時点の報道。衆院定数のみ変わり、参院 248 は不変）
SCENARIOS: dict[str, int] = {
    "現行（465）": 465,
    "1 割減（420）": 420,
    "比例 45 減（420）": 420,
    "比例 31 減（434）": 434,
}


@dataclass(frozen=True)
class Country:
    iso3: str
    name: str
    lower_seats: float
    total_seats: float
    population_thousands: float
    upper_designation: str = ""  # "" when unicameral


# ---- pure helpers -------------------------------------------------------------------------------


def per_million(seats: float, population_thousands: float) -> float:
    return seats / (population_thousands / 1000.0)


def cube_ratio(seats: float, population_thousands: float) -> float:
    """定数 ÷ 人口の立方根（Taagepera の立方根法則。1.0 が法則どおり）。"""
    return float(seats / (population_thousands * 1000.0) ** (1.0 / 3.0))


def rank_of(values: Mapping[str, float], iso3: str) -> int:
    """小さい方から数えた順位（1 始まり。同値は先に来る方を優先しない: 厳密に小さい数 + 1）。"""
    v = values[iso3]
    return 1 + sum(1 for k, x in values.items() if k != iso3 and x < v)


def judge_h1(rank_lower: int, rank_total: int) -> str:
    if rank_lower <= 5 and rank_total <= 5:
        return "整合"
    if rank_lower >= 10 or rank_total >= 10:
        return "不支持"
    return "中間"


def judge_h1b(rank_cube: int, n: int = 38) -> str:
    lo, hi = (n // 3) + 1, 2 * (n // 3) + 2  # 38 -> 13..26
    return "整合" if lo <= rank_cube <= hi else "不支持"


def judge_h1c(base: tuple[str, str], after: Sequence[tuple[str, str]]) -> str:
    """削減後も (H1, H1b) の判定が全シナリオで変わらなければ整合。"""
    return "整合" if all(a == base for a in after) else "不支持"


def with_reduction(countries: Sequence[Country], iso3: str, lower_seats: int) -> list[Country]:
    out: list[Country] = []
    for c in countries:
        if c.iso3 == iso3:
            upper = c.total_seats - c.lower_seats
            out.append(replace(c, lower_seats=lower_seats, total_seats=lower_seats + upper))
        else:
            out.append(c)
    return out


def metrics(countries: Sequence[Country]) -> dict[str, dict[str, float]]:
    return {
        "per_m_lower": {
            c.iso3: per_million(c.lower_seats, c.population_thousands) for c in countries
        },
        "per_m_total": {
            c.iso3: per_million(c.total_seats, c.population_thousands) for c in countries
        },
        "cube": {c.iso3: cube_ratio(c.lower_seats, c.population_thousands) for c in countries},
    }


def judgements(countries: Sequence[Country], iso3: str = JP) -> tuple[str, str, dict[str, int]]:
    m = metrics(countries)
    ranks = {k: rank_of(v, iso3) for k, v in m.items()}
    return (
        judge_h1(ranks["per_m_lower"], ranks["per_m_total"]),
        judge_h1b(ranks["cube"], len(countries)),
        ranks,
    )


# ---- loader --------------------------------------------------------------------------------------


def load_countries(mart: pl.DataFrame) -> list[Country]:
    """OECD 加盟国の下院・両院合計の定数と人口。下院の無い国・人口欠損は ValueError。"""
    o = mart.filter(pl.col("oecd_member"))
    out: list[Country] = []
    for iso3, grp in sorted(o.group_by("iso3"), key=lambda kv: str(kv[0][0])):
        lower = grp.filter(pl.col("chamber_type") == "lower")
        upper = grp.filter(pl.col("chamber_type") == "upper")
        if lower.height != 1 or upper.height > 1:
            msg = f"{iso3}: expected one lower and at most one upper chamber"
            raise ValueError(msg)
        seats = grp["statutory_seats"].to_list()
        pop = lower["population_thousands"][0]
        if any(s is None for s in seats) or pop is None:
            msg = f"{iso3}: statutory seats or population missing"
            raise ValueError(msg)
        out.append(
            Country(
                iso3=str(iso3[0]),
                name=str(lower["country"][0]),
                lower_seats=float(lower["statutory_seats"][0]),
                total_seats=float(sum(seats)),
                population_thousands=float(pop),
                upper_designation=str(upper["designation_mode"][0]) if upper.height else "",
            )
        )
    return out


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_bars(countries: Sequence[Country], key: str, title: str, path: Path) -> None:
    import matplotlib.pyplot as plt

    m = metrics(countries)[key]
    order = sorted(m, key=lambda k: m[k])
    names = {c.iso3: c.name for c in countries}
    fig, ax = plt.subplots(figsize=(7.2, 8.2))
    colors = [SERIES[1] if k == JP else (SERIES[0] if k in PEERS else "#b8c6d9") for k in order]
    ax.barh([names[k] for k in order], [m[k] for k in order], color=colors)
    for i, k in enumerate(order):
        ax.text(m[k], i, f" {m[k]:.1f}", va="center", fontsize=7, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_xlabel("人口 100 万人当たり議員数（人）", fontsize=8, color=INK)
    ax.invert_yaxis()
    _style(ax)
    fig.text(0.01, 0.005, f"出典: {SOURCE_NOTE}。n = {len(countries)}", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_cube(countries: Sequence[Country], path: Path) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    pops = np.array([c.population_thousands * 1000 for c in countries])
    seats = np.array([c.lower_seats for c in countries])
    xs = np.logspace(np.log10(pops.min() * 0.8), np.log10(pops.max() * 1.3), 50)
    ax.plot(
        xs,
        xs ** (1 / 3),
        color=MUTED,
        linewidth=1,
        linestyle="--",
        label="立方根法則（定数 = 人口^(1/3)）",
    )
    for c, p, s in zip(countries, pops, seats, strict=True):
        col = SERIES[1] if c.iso3 == JP else (SERIES[0] if c.iso3 in PEERS else "#9bb0c9")
        ax.scatter(p, s, color=col, s=28 if c.iso3 == JP else 16, zorder=3)
        if c.iso3 == JP or c.iso3 in PEERS:
            ax.annotate(
                c.iso3, (p, s), xytext=(4, 2), textcoords="offset points", fontsize=7, color=INK
            )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("人口（人、対数軸）", fontsize=8, color=INK)
    ax.set_ylabel("下院の定数（対数軸）", fontsize=8, color=INK)
    ax.set_title(
        "下院定数と人口（OECD 38 か国）: 日本は立方根法則の線のほぼ上にある",
        fontsize=10,
        color=INK,
        loc="left",
    )
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    fig.text(0.01, 0.005, f"出典: {SOURCE_NOTE}。n = {len(countries)}", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = [
        "Hiragino Sans",
        "Noto Sans CJK JP",
        "IPAPGothic",
        "IPAGothic",
        "sans-serif",
    ]
    mart = pl.read_parquet(args.data_dir / "marts" / "ipu_parliaments.parquet")
    countries = load_countries(mart)
    n = len(countries)
    jp = next(c for c in countries if c.iso3 == JP)
    m = metrics(countries)
    h1, h1b, ranks = judgements(countries)

    print("# R1 人口当たり国会議員数の国際比較（H1・H1b・H1c）（2026-10-27）")
    n_oecd_ch = mart.filter(pl.col("oecd_member")).height
    print(f"- mart: ipu_parliaments {mart.height} 行（うち OECD 加盟国の議院 {n_oecd_ch}、国 {n}）")
    pop_txt = f"{jp.population_thousands:,.0f} 千人"
    print(f"- 日本: 下院 {jp.lower_seats:.0f}、両院 {jp.total_seats:.0f}、人口 {pop_txt}")
    pm_l, pm_t, cube = m["per_m_lower"][JP], m["per_m_total"][JP], m["cube"][JP]
    r_l, r_t, r_c = ranks["per_m_lower"], ranks["per_m_total"], ranks["cube"]
    print(f"- 100 万人当たり: 下院 {pm_l:.2f} 人（{r_l} 位 / {n}）、両院 {pm_t:.2f} 人（{r_t} 位）")
    root = (jp.population_thousands * 1000) ** (1 / 3)
    print(
        f"- 立方根比: {cube:.3f}（{r_c} 位 / {n}、法則どおりなら 1.0。人口の立方根 = {root:.0f}）"
    )
    print(f"- **H1 判定: {h1}**、**H1b 判定: {h1b}**")

    print("\n## 表 1: OECD 38 か国の人口 100 万人当たり議員数（少ない順）")
    print(
        "| 順位 | 国 | 下院定数 | 両院定数 | 人口（千人） | 下院 /100 万人 | 両院 /100 万人 "
        "| 立方根比 | 上院の選出 |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for i, iso in enumerate(sorted(m["per_m_lower"], key=lambda k: m["per_m_lower"][k]), start=1):
        c = next(x for x in countries if x.iso3 == iso)
        mark = "**" if iso == JP else ""
        cells = [
            str(i),
            f"{mark}{c.name}{mark}",
            f"{c.lower_seats:.0f}",
            f"{c.total_seats:.0f}",
            f"{c.population_thousands:,.0f}",
            f"{m['per_m_lower'][iso]:.2f}",
            f"{m['per_m_total'][iso]:.2f}",
            f"{m['cube'][iso]:.2f}",
            c.upper_designation or "一院制",
        ]
        print("| " + " | ".join(cells) + " |")

    print("\n## 表 2: 人口規模の近い国との比較（人口 4,000 万人以上）")
    print("| 国 | 人口（千人） | 下院定数 | 下院 /100 万人 | 立方根比 |")
    print("|---|---|---|---|---|")
    for c in sorted(
        (c for c in countries if c.population_thousands >= 40_000),
        key=lambda c: -c.population_thousands,
    ):
        cells = [
            c.name,
            f"{c.population_thousands:,.0f}",
            f"{c.lower_seats:.0f}",
            f"{m['per_m_lower'][c.iso3]:.2f}",
            f"{m['cube'][c.iso3]:.2f}",
        ]
        print("| " + " | ".join(cells) + " |")

    print("\n## 表 3: H1c 削減シナリオ後の日本の順位")
    print(
        "| シナリオ | 衆院定数 | 下院 /100 万人（順位） | 両院 /100 万人（順位） "
        "| 立方根比（順位） | H1 | H1b |"
    )
    print("|---|---|---|---|---|---|---|")
    after: list[tuple[str, str]] = []
    for label, seats in SCENARIOS.items():
        cs = with_reduction(countries, JP, seats)
        mm = metrics(cs)
        a1, a1b, rr = judgements(cs)
        if label != "現行（465）":
            after.append((a1, a1b))
        cells = [
            label,
            str(seats),
            f"{mm['per_m_lower'][JP]:.2f}（{rr['per_m_lower']} 位）",
            f"{mm['per_m_total'][JP]:.2f}（{rr['per_m_total']} 位）",
            f"{mm['cube'][JP]:.3f}（{rr['cube']} 位）",
            a1,
            a1b,
        ]
        print("| " + " | ".join(cells) + " |")
    h1c = judge_h1c((h1, h1b), after)
    note = "（削減後も H1・H1b の判定は変わらない）" if h1c == "整合" else ""
    print(f"\n- **H1c 判定: {h1c}**{note}")

    print("\n## 頑健性: 現員ベース・G7 のみ・人口 1,000 万人以上")
    cur = mart.filter(pl.col("oecd_member"))
    cur_lower = {
        str(r["iso3"]): per_million(float(r["current_members"]), float(r["population_thousands"]))
        for r in cur.filter(pl.col("chamber_type") == "lower").iter_rows(named=True)
    }
    r_cur = rank_of(cur_lower, JP)
    print(
        f"- 現員ベースの下院 /100 万人: 日本 {cur_lower[JP]:.2f}（{r_cur} 位 / {len(cur_lower)}）"
    )
    g7 = [c for c in countries if c.iso3 in ("USA", "JPN", "DEU", "GBR", "FRA", "ITA", "CAN")]
    _, _, r_g7 = judgements(g7)
    print(
        f"- G7 のみ（n = {len(g7)}）: 下院 /100 万人 {r_g7['per_m_lower']} 位、"
        f"両院 {r_g7['per_m_total']} 位、立方根比 {r_g7['cube']} 位"
    )
    big = [c for c in countries if c.population_thousands >= 10_000]
    b1, _, rb = judgements(big)
    b1b = judge_h1b(rb["cube"], len(big))
    lo, hi = len(big) // 3 + 1, 2 * (len(big) // 3) + 2
    print(
        f"- 人口 1,000 万人以上（n = {len(big)}）: 下院 {rb['per_m_lower']} 位、"
        f"両院 {rb['per_m_total']} 位、立方根比 {rb['cube']} 位 → H1 {b1}、H1b {b1b}"
        f"（区間は n に合わせ {lo}〜{hi} 位）"
    )
    elected_total = {
        c.iso3: per_million(
            c.lower_seats
            + (c.total_seats - c.lower_seats)
            * (1 if c.upper_designation == "directly_elected" else 0),
            c.population_thousands,
        )
        for c in countries
    }
    r_el = rank_of(elected_total, JP)
    el_txt = f"{elected_total[JP]:.2f}（{r_el} 位 / {n}）"
    print(f"- 両院合計を『直接公選の議席のみ』にした場合: 日本 {el_txt}")

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    fig_bars(
        countries,
        "per_m_lower",
        "人口 100 万人当たりの下院議員数（OECD 38 か国、定数ベース）",
        args.fig_dir / "r1_per_million_lower.png",
    )
    fig_bars(
        countries,
        "per_m_total",
        "人口 100 万人当たりの両院合計議員数（OECD 38 か国、定数ベース）",
        args.fig_dir / "r1_per_million_total.png",
    )
    fig_cube(countries, args.fig_dir / "r1_cube_root.png")
    print(
        f"\n図: {args.fig_dir}/r1_per_million_lower.png, r1_per_million_total.png, r1_cube_root.png"
    )


if __name__ == "__main__":
    main()
