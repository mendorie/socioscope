"""R9: 各国の定数は 1990 年以降どう変わり、人口変化と関係があるか（H6b、H6 の深掘り）。

事後追加の仮説 H6b（design/themes/parliament-size.md「事後追加（2026-10-28 夕）」、
結果の計算前に固定）:
  ParlGov 2024（選挙ごとの総議席 seats_total）で OECD 32 か国の下院定数の変更を 1990 年以降の
  選挙ごとに拾い、変更率と直前 10 年の人口変化率（WDI SP.POP.TOTL）の相関を取る。|r| < 0.3 なら
  「定数は人口に連動していない」で整合。副次: 直前 10 年で人口が減っていた選挙で定数を減らした
  例の数。
  事後の具体化: ParlGov の日本 2021 年（176 = 比例のみ）は手入力表（465）で置き換え、ドイツは
  超過議席で実員が変わるため法定 598（1990–2021）・630（2025）に置き換える。

決定的スクリプト。入力は data/marts/{parlgov_elections, wdi_population, ipu_parliaments}.parquet と
src/theme_parliament_size/jp_seats_history.csv。純粋ヘルパは tests/test_analysis_r9.py で検証する。
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row
from theme_parliament_size.analysis.a20261027_r5_roles import spearman

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
START_YEAR = 1990
LOOKBACK = 10  # 直前 10 年の人口変化
JP_SEATS_CSV = THEME_DIR / "src" / "theme_parliament_size" / "jp_seats_history.csv"
# ドイツ連邦議会の法定定数（超過議席・調整議席を除く）。2023 年改正で 630 に固定（2025 年選挙から）
DEU_STATUTORY: tuple[tuple[int, int], ...] = ((1990, 656), (2002, 598), (2025, 630))


# ---- pure helpers -------------------------------------------------------------------------------


def statutory_at(table: Sequence[tuple[int, int]], year: int) -> int | None:
    """(施行年, 定数) の表から、year 時点で有効な定数。表の最初の年より前なら None。"""
    val: int | None = None
    for y, s in sorted(table):
        if y <= year:
            val = s
    return val


def jp_lower_house(rows: Sequence[Mapping[str, object]]) -> list[tuple[int, int]]:
    """jp_seats_history.csv（chamber, effective_year, seats, …）→ 衆院の (施行年, 定数)。"""
    out = [
        (int(str(r["effective_year"])), int(str(r["seats"])))
        for r in rows
        if str(r.get("chamber")) == "lower"
    ]
    return sorted(out)


def changes(
    elections: Sequence[tuple[int, str, int]],
) -> list[dict[str, object]]:
    """[(year, date, seats)] → 前回選挙から定数が変わった選挙。

    {year, date, before, after, change_pct} のリスト。"""
    out: list[dict[str, object]] = []
    prev: tuple[int, str, int] | None = None
    for e in sorted(elections, key=lambda x: x[1]):
        if prev is not None and e[2] != prev[2] and e[0] >= START_YEAR:
            out.append(
                {
                    "year": e[0],
                    "date": e[1],
                    "before": prev[2],
                    "after": e[2],
                    "change_pct": 100.0 * (e[2] - prev[2]) / prev[2],
                }
            )
        prev = e
    return out


def pop_change(pop: Mapping[int, float], year: int, lookback: int = LOOKBACK) -> float | None:
    a, b = pop.get(year - lookback), pop.get(year)
    if a is None or b is None or a <= 0:
        return None
    return 100.0 * (b - a) / a


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


def judge_h6b(r: float) -> str:
    if math.isnan(r):
        return "判定不能"
    return "整合" if abs(r) < 0.3 else "不支持"


# ---- figure --------------------------------------------------------------------------------------


def fig_scatter(points: Sequence[tuple[str, float, float]], path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    for iso, x, y in points:
        ax.scatter([x], [y], s=24, color=SERIES[1] if iso == "JPN" else "#7f9cc4")
        ax.annotate(iso, (x, y), fontsize=6.5, color=INK, xytext=(3, 2), textcoords="offset points")
    ax.axhline(0, color=INK, linewidth=0.6)
    ax.axvline(0, color=MUTED, linewidth=0.6, linestyle=":")
    ax.set_xlabel("直前 10 年の人口変化率（%、WDI）", fontsize=8, color=INK)
    ax.set_ylabel("下院定数の変更率（%、前回選挙比）", fontsize=8, color=INK)
    ax.set_title(
        "定数を変えた選挙（OECD、1990 年以降）と直前 10 年の人口変化", fontsize=10, loc="left"
    )
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    note = (
        "出典: ParlGov 2024（Harvard Dataverse、CC0）、World Bank WDI SP.POP.TOTL（CC BY 4.0）。"
        "日本は手入力表、ドイツは法定定数で置換"
    )
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
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    marts = args.data_dir / "marts"
    pg = pl.read_parquet(marts / "parlgov_elections.parquet")
    popdf = pl.read_parquet(marts / "wdi_population.parquet")
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    oecd = sorted(set(ipu.filter(pl.col("oecd_member"))["iso3"].to_list()))
    names = {str(r["iso3"]): str(r["country"]) for r in ipu.iter_rows(named=True)}
    with JP_SEATS_CSV.open(encoding="utf-8") as f:
        jp_table = jp_lower_house(list(csv.DictReader(f)))

    pop: dict[str, dict[int, float]] = {}
    for r in popdf.iter_rows(named=True):
        pop.setdefault(str(r["iso3"]), {})[int(r["year"])] = float(r["population"])

    print("# R9 各国の定数は 1990 年以降どう変わり、人口と関係があるか（H6b）（2026-10-28）")
    print("\n事後追加の仮説（設計書 2026-10-28 夕 節）。記述と相関のみ。因果の主張はない。")
    print("\n## 表 1: 1990 年以降に下院定数を変えた選挙（OECD、ParlGov に収録の 32 か国）")
    print(
        md_row(
            ["国", "選挙", "定数（前 → 後）", "変更率 %", "直前 10 年の人口変化率 %", "人口減少中"]
        )
    )
    print("|---|---|---|---|---|---|")
    points: list[tuple[str, float, float]] = []
    n_countries = 0
    n_changed = 0
    n_decline_cut = 0
    n_decline = 0
    missing = [c for c in oecd if c not in set(pg["iso3"].to_list())]
    for iso in oecd:
        sub = pg.filter(pl.col("iso3") == iso).sort("election_date")
        if sub.height == 0:
            continue
        n_countries += 1
        elections: list[tuple[int, str, int]] = []
        for r in sub.iter_rows(named=True):
            year, date, seats = int(r["year"]), str(r["election_date"]), int(r["seats_total"])
            if iso == "JPN":
                s = statutory_at(jp_table, year)
                seats = s if s is not None else seats
            elif iso == "DEU":
                s = statutory_at(DEU_STATUTORY, year)
                seats = s if s is not None else seats
            elections.append((year, date, seats))
        ch = changes(elections)
        if ch:
            n_changed += 1
        for c in ch:
            pc = pop_change(pop.get(iso, {}), int(str(c["year"])))
            declining = pc is not None and pc < 0
            if declining:
                n_decline += 1
                if float(str(c["change_pct"])) < 0:
                    n_decline_cut += 1
            if pc is not None:
                points.append((iso, pc, float(str(c["change_pct"]))))
            print(
                md_row(
                    [
                        f"{names.get(iso, iso)}（{iso}）",
                        str(c["date"])[:4],
                        f"{c['before']} → {c['after']}",
                        f"{float(str(c['change_pct'])):+.1f}",
                        f"{pc:+.1f}" if pc is not None else "–",
                        "はい" if declining else "いいえ",
                    ]
                )
            )
    r_all = pearson([p[1] for p in points], [p[2] for p in points])
    cuts = [p for p in points if p[2] < 0]
    print(
        f"\n- 対象 {n_countries} か国（ParlGov に無い OECD 国: {'、'.join(missing)}）、"
        f"1990 年以降に定数を変えた国 {n_changed}、変更回数 {len(points)}"
        f"（増 {len(points) - len(cuts)}・減 {len(cuts)}）"
    )
    print(f"- 変更率 × 直前 10 年の人口変化率の相関 r = {r_all:.2f}（n = {len(points)}）")
    print(
        f"- 直前 10 年で人口が減っていた変更 {n_decline} 回のうち定数を減らしたのは "
        f"{n_decline_cut} 回"
    )
    print(f"- **H6b 判定: {judge_h6b(r_all)}**（|r| < 0.3 で整合）")
    # 頑健性: 制度転換級の大変更（|変更率| ≥ 20%）を除く、順位相関、2005 年以降（R4 と同じ窓）
    small = [p for p in points if abs(p[2]) < 20.0]
    r_small = pearson([p[1] for p in small], [p[2] for p in small])
    rho = spearman([p[1] for p in points], [p[2] for p in points])
    big = sorted((p[0], p[2]) for p in points if abs(p[2]) >= 20.0)
    print("\n## 頑健性")
    print(
        f"- |変更率| ≥ 20% の制度転換級の変更（{len(big)} 回: "
        + "、".join(f"{iso} {v:+.0f}%" for iso, v in big)
        + f"）を除くと r = {r_small:.2f}（n = {len(small)}）"
    )
    print(f"- Spearman ρ（全 {len(points)} 回）= {rho:.2f}")
    fig_scatter(points, args.fig_dir / "r9_seat_changes_population.png")
    print(f"\n図: {args.fig_dir}/r9_seat_changes_population.png")


if __name__ == "__main__":
    main()
