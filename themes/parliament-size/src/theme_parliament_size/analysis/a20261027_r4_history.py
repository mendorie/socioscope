"""R4: 定数は人口に連動して変えられてきたか（H6）。

事前登録（design/themes/parliament-size.md、2026-10-27）:
  H6: 日本の 人口当たり衆院定数 の時系列が 1946 年比で 2020 年に 0.6 倍以下なら「人口に連動して
      いない」が整合。各国の定数変更幅と直近の人口変化率の相関が |r| < 0.3 なら整合。

日本: 定数は src/theme_parliament_size/jp_seats_history.csv（法令・衆議院 HP から手入力、
出典列あり）、
人口は e-Stat 人口推計 長期時系列（1920–2000、総人口）と IPU Parline の population_in_thousands
（2001 年以降。IPU は 2016–2020 年を欠くため、2020 年以前で最も近い年で判定し最新年も併記）。
各国: IPU Parline の statutory_members_number の記録（2005 年以降の変更しか持たない国が多い。
1 件しかない国は「変更なし」とみなす。日本は IPU の記録が誤っている（2005 年から 465）ため
手入力表で置き換える）。

決定的スクリプト。純粋ヘルパは tests/test_analysis_r4.py で検証する。
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

THEME_DIR = Path(__file__).resolve().parents[3]
SEATS_CSV = Path(__file__).resolve().parents[1] / "jp_seats_history.csv"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
BASE_YEAR, END_YEAR = 1946, 2020


# ---- pure helpers -------------------------------------------------------------------------------


def load_seats(path: Path = SEATS_CSV) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as f:
        return [
            {**row, "effective_year": int(row["effective_year"]), "seats": int(row["seats"])}
            for row in csv.DictReader(f)
        ]


def seats_in_year(history: Sequence[Mapping[str, object]], chamber: str, year: int) -> int | None:
    """year 時点で有効な定数（effective_year ≤ year の最新）。"""
    rows = [r for r in history if r["chamber"] == chamber and int(str(r["effective_year"])) <= year]
    if not rows:
        return None
    return int(str(max(rows, key=lambda r: int(str(r["effective_year"])))["seats"]))


def per_million(seats: float, population_thousands: float) -> float:
    return seats / (population_thousands / 1000.0)


def nearest_year_at_or_before(years: Sequence[int], target: int) -> int:
    cands = [y for y in years if y <= target]
    if not cands:
        msg = f"no year at or before {target}"
        raise ValueError(msg)
    return max(cands)


def judge_h6_jp(ratio_end_over_base: float) -> str:
    return "整合" if ratio_end_over_base <= 0.6 else "不支持"


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n < 3:
        return math.nan
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return math.nan
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / math.sqrt(sxx * syy)


def judge_h6_cross(r: float) -> str:
    if math.isnan(r):
        return "判定不能"
    return "整合" if abs(r) < 0.3 else "不支持"


def md_row(cells: Sequence[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_jp(years: Sequence[int], seats: Sequence[int], pop: Sequence[float], path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    ax.step(years, seats, where="post", color=SERIES[0], linewidth=1.6, label="衆院定数（左軸）")
    ax.set_ylabel("衆院定数", fontsize=8, color=INK)
    ax.set_ylim(0, 560)
    ax2 = ax.twinx()
    pm = [per_million(s, p) for s, p in zip(seats, pop, strict=True)]
    ax2.plot(years, pm, color=SERIES[1], linewidth=1.6, label="人口 100 万人当たり定数（右軸）")
    ax2.set_ylabel("人口 100 万人当たり定数（人）", fontsize=8, color=INK)
    ax2.set_ylim(0, 10)
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(colors=INK, labelsize=8)
    title = "衆院定数と人口当たり定数 1920–2023: 定数は 464〜512 で横ばい、人口比は半減"
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, frameon=False, loc="lower left")
    _style(ax)
    note = "出典: 定数は法令・衆議院 HP、人口は e-Stat 人口推計（1920–2000）と IPU Parline（2001–）"
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_cross(points: Mapping[str, tuple[float, float]], path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    for iso, (px, sy) in points.items():
        changed = sy != 0 or iso == JP
        col = SERIES[1] if iso == JP else (SERIES[0] if sy != 0 else "#9bb0c9")
        ax.scatter(px, sy, color=col, s=26 if changed else 14, zorder=3)
        if changed:
            ax.annotate(iso, (px, sy), xytext=(4, 2), textcoords="offset points", fontsize=7)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xlabel("人口変化率 2005 → 2023（%）", fontsize=8, color=INK)
    ax.set_ylabel("下院定数の変化率 2005 → 最新（%）", fontsize=8, color=INK)
    title = "OECD 38 か国: 定数の変更と人口の変化（IPU Parline、2005 年以降の記録）"
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    _style(ax)
    note = "出典: IPU Parline statutory_members_number・population_in_thousands。日本は法令表で補正"
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
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
    fonts = ["Hiragino Sans", "Noto Sans CJK JP", "IPAPGothic", "IPAGothic", "sans-serif"]
    matplotlib.rcParams["font.family"] = fonts
    marts = args.data_dir / "marts"
    staged = args.data_dir / "staged"
    longpop = pl.read_parquet(marts / "jp_population_longterm.parquet")
    country = pl.read_parquet(staged / "ipu" / "country_attributes.parquet")
    chamber = pl.read_parquet(staged / "ipu" / "chamber_attributes.parquet")
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    history = load_seats()

    # 日本の人口系列: 1920–2000 e-Stat、2001– IPU
    pop: dict[int, float] = {
        int(r["year"]): float(r["population_total_thousands"])
        for r in longpop.iter_rows(named=True)
    }
    jp_pop = country.filter(
        (pl.col("entity_id") == "JP") & (pl.col("attribute") == "population_in_thousands")
    )
    for r in jp_pop.iter_rows(named=True):
        y = int(str(r["date_from"])[:4])
        if y > 2000:
            pop[y] = float(r["value_num"])
    years = sorted(pop)
    seats = [seats_in_year(history, "lower", y) or 0 for y in years]
    n_ipu = len([y for y in years if y > 2000])

    print("# R4 定数は人口に連動して変えられてきたか（H6）（2026-10-27）")
    print(
        f"- 人口: e-Stat 長期時系列 {longpop.height} 年 ＋ IPU {n_ipu} 年。"
        f"定数: jp_seats_history.csv {len(history)} 行"
    )
    print("\n## 表 1: 衆院定数と人口当たり定数（定数が変わった年と節目）")
    print(md_row(["年", "衆院定数", "人口（千人）", "100 万人当たり定数", "1946 年比"]))
    print("|---|---|---|---|---|")
    base = per_million(seats_in_year(history, "lower", BASE_YEAR) or 0, pop[BASE_YEAR])
    end_year = nearest_year_at_or_before(years, END_YEAR)
    change_years = {
        int(str(r["effective_year"]))
        for r in history
        if r["chamber"] == "lower" and int(str(r["effective_year"])) >= 1920
    }
    marks = sorted(change_years | {1920, 1946, 1970, 1990, 2000, 2010, end_year, years[-1]})
    for y in marks:
        if y not in pop:
            continue
        s = seats_in_year(history, "lower", y) or 0
        pm = per_million(s, pop[y])
        print(md_row([y, s, f"{pop[y]:,.0f}", f"{pm:.2f}", f"{pm / base:.3f}"]))
    s_end = seats_in_year(history, "lower", end_year) or 0
    pm_end = per_million(s_end, pop[end_year])
    end_ratio = pm_end / base
    s_last = seats_in_year(history, "lower", years[-1]) or 0
    last_ratio = per_million(s_last, pop[years[-1]]) / base
    print(
        f"\n- 1946 年 {base:.2f} 人 → {end_year} 年 {pm_end:.2f} 人（{end_ratio:.3f} 倍）、"
        f"{years[-1]} 年 {last_ratio:.3f} 倍。定数は 1946 年 468 → {years[-1]} 年 {s_last} で"
        f"ほぼ不変、人口は {pop[BASE_YEAR] / 1000:,.1f} → {pop[years[-1]] / 1000:,.1f} 百万人"
    )
    print(f"- **H6（日本）判定: {judge_h6_jp(end_ratio)}**（基準 0.6 倍以下、判定年 {end_year}）")
    upper = [
        (int(str(r["effective_year"])), int(str(r["seats"])))
        for r in history
        if r["chamber"] == "upper"
    ]
    print(f"- 参考: 参院定数 {' → '.join(f'{s}（{y}）' for y, s in upper)}")

    # 各国
    o = ipu.filter(pl.col("oecd_member") & (pl.col("chamber_type") == "lower"))
    cc_of = {str(r["chamber_id"]): str(r["iso3"]) for r in o.iter_rows(named=True)}
    st = chamber.filter(
        (pl.col("attribute") == "statutory_members_number") & pl.col("entity_id").is_in(list(cc_of))
    )
    seat_change: dict[str, tuple[float, float, str, str]] = {}
    for cid, grp in st.group_by("entity_id"):
        g = grp.sort("seq")
        v0, v1 = float(g["value_num"][0]), float(g["value_num"][-1])
        y0, y1 = str(g["date_from"][0])[:4], str(g["date_from"][-1])[:4]
        seat_change[cc_of[str(cid[0])]] = (v0, v1, y0, y1)
    # IPU は日本を 2005 年から 465 としており誤り。法令表（480 → 475 → 465）で置換
    seat_change[JP] = (480.0, 465.0, "2005", "2017")
    pop_change: dict[str, float] = {}
    pop_rows = country.filter(pl.col("attribute") == "population_in_thousands")
    for cc, grp in pop_rows.group_by("entity_id"):
        series = {
            int(str(r["date_from"])[:4]): float(r["value_num"]) for r in grp.iter_rows(named=True)
        }
        if 2005 in series and 2023 in series:
            sub = o.filter(pl.col("chamber_id").str.starts_with(str(cc[0]) + "-"))
            if sub.height:
                pop_change[str(sub["iso3"][0])] = 100.0 * (series[2023] / series[2005] - 1)
    points = {
        iso: (pop_change[iso], 100.0 * (v1 / v0 - 1))
        for iso, (v0, v1, _, _) in seat_change.items()
        if iso in pop_change
    }
    r_all = pearson([p[0] for p in points.values()], [p[1] for p in points.values()])
    changed = {k: v for k, v in points.items() if v[1] != 0}
    r_changed = pearson([v[0] for v in changed.values()], [v[1] for v in changed.values()])
    print(
        "\n## 表 2: OECD 下院の定数変更（IPU の記録に変更がある国 ＋ 日本）と人口変化 2005 → 2023"
    )
    print(md_row(["国", "定数（最初の記録 → 最新）", "変更率 %", "人口変化率 %", "人口減少中か"]))
    print("|---|---|---|---|---|")
    for iso, (px, sy) in sorted(changed.items(), key=lambda kv: kv[1][1]):
        v0, v1, y0, y1 = seat_change[iso]
        cells = [iso, f"{v0:.0f}（{y0}）→ {v1:.0f}（{y1}）", f"{sy:+.1f}", f"{px:+.1f}"]
        print(md_row([*cells, "はい" if px < 0 else "いいえ"]))
    shrinking = sorted(iso for iso, (px, _) in points.items() if px < 0)
    shrink_changed = sorted(i for i in shrinking if i in changed)
    print(
        f"\n- 人口が 2005 → 2023 で減った OECD 国: {len(shrinking)}（{', '.join(shrinking)}）。"
        f"うち定数を変えた国: {', '.join(shrink_changed) or 'なし'}"
    )
    print(
        f"- 定数変更率と人口変化率の相関: 全 {len(points)} か国 r = {r_all:.2f}、"
        f"変更があった {len(changed)} か国 r = {r_changed:.2f}"
    )
    print(
        f"- **H6（各国）判定: {judge_h6_cross(r_all)}**（|r| < 0.3 で整合。ただし IPU の定数記録は "
        "2005 年以降で、1 件しか無い国を「変更なし」と扱う弱い証拠）"
    )

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    fig_jp(years, seats, [pop[y] for y in years], args.fig_dir / "r4_jp_seats_population.png")
    fig_cross(points, args.fig_dir / "r4_oecd_seat_vs_population.png")
    print(f"\n図: {args.fig_dir}/r4_jp_seats_population.png, r4_oecd_seat_vs_population.png")


if __name__ == "__main__":
    main()
