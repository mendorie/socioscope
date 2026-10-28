"""R16（番外編）: 議会の大きさは「小さな政府／大きな政府」と関係するか（H15a〜d、ユーザー提起）。

事後追加の仮説（design/themes/parliament-size.md「事後追加（2026-10-29 深夜、番外編 R16）」、
結果の計算前に固定）:
  政府の大きさ = 一般政府支出 ÷ GDP（OECD Government at a Glance 2025、S13、2019〜2023 年平均）。
  議会の大きさ = (i) 人口 100 万人当たり下院定数、(ii) 立方根補正比 seats / population^(1/3)。
  H15a: (i) × 支出比 の Spearman ρ ≥ +0.3 で整合、|ρ| < 0.3 で不支持。
  H15b: (ii) × 支出比 の |ρ| < 0.2 で整合（規模の効果）、|ρ| ≥ 0.3 で不支持、間は中間。
  H15c: H15b 不支持のときのみ、残る関係の向きを記述。
  H15d: 議員 1 人当たり議会職員 × 支出比 の |ρ| < 0.3 で整合。
  頑健性: 2019 年単独、log 回帰残差による補正、連邦制／単一制、人口 1,000 万人以上／未満、
  米国除外、政府収入比、人口当たり公務就業者（R10）。

決定的スクリプト。入力は data/marts/{oecd_gov_finance, ipu_parliaments,
ilo_emp_public_admin}.parquet と src/theme_parliament_size/federal_states.csv。
純粋ヘルパは tests/test_analysis_r16.py で検証する。
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r1_ratio import cube_ratio, per_million
from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row
from theme_parliament_size.analysis.a20261027_r3_cost import rank_of
from theme_parliament_size.analysis.a20261027_r5_roles import spearman, staff_per_member
from theme_parliament_size.analysis.a20261028_r10_bureaucracy import latest_value, per_thousand

THEME_DIR = Path(__file__).resolve().parents[3]
FEDERAL_CSV = THEME_DIR / "src" / "theme_parliament_size" / "federal_states.csv"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
WINDOW = (2019, 2023)


# ---- pure helpers -------------------------------------------------------------------------------


def window_mean(
    rows: Sequence[Mapping[str, object]], years: tuple[int, int] = WINDOW
) -> float | None:
    """[{year, value}] → years（両端含む）の平均。窓内に 1 年も無ければ None。"""
    vals = [float(str(r["value"])) for r in rows if years[0] <= int(str(r["year"])) <= years[1]]
    return sum(vals) / len(vals) if vals else None


def log_residuals(seats: Mapping[str, float], pops: Mapping[str, float]) -> dict[str, float]:
    """log(定数) を log(人口) に OLS 回帰した残差（立方根の係数 1/3 を仮定しない補正）。"""
    keys = sorted(k for k in seats if k in pops)
    if len(keys) < 3:
        return {}
    xs = [math.log(pops[k]) for k in keys]
    ys = [math.log(seats[k]) for k in keys]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    a = my - b * mx
    return {k: y - (a + b * x) for k, x, y in zip(keys, xs, ys, strict=True)}


def log_slope(seats: Mapping[str, float], pops: Mapping[str, float]) -> float:
    keys = sorted(k for k in seats if k in pops)
    xs = [math.log(pops[k]) for k in keys]
    ys = [math.log(seats[k]) for k in keys]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx


def judge_h15a(rho: float) -> str:
    if math.isnan(rho):
        return "判定不能"
    return "整合" if rho >= 0.3 else "不支持"


def judge_h15b(rho: float) -> str:
    if math.isnan(rho):
        return "判定不能"
    if abs(rho) < 0.2:
        return "整合"
    if abs(rho) >= 0.3:
        return "不支持"
    return "中間"


def judge_h15d(rho: float) -> str:
    if math.isnan(rho):
        return "判定不能"
    return "整合" if abs(rho) < 0.3 else "不支持"


def direction_h15c(rho: float) -> str:
    if math.isnan(rho) or abs(rho) < 0.3:
        return "判定対象外（H15b が不支持ではない）"
    return "正（大きな政府ほど議会も大きい）" if rho > 0 else "負（行政が大きいと議会は小さい）"


def p_value(rho: float, n: int) -> float:
    """Spearman ρ の t 近似による両側 p 値。"""
    from scipy import stats

    if math.isnan(rho) or n < 3 or abs(rho) >= 1:
        return math.nan
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    return float(2 * stats.t.sf(abs(t), n - 2))


def critical_rho(n: int, alpha: float = 0.05) -> float:
    """両側 alpha で有意になる |ρ| の境界（t 近似）。"""
    from scipy import stats

    t = float(stats.t.ppf(1 - alpha / 2, n - 2))
    return t / math.sqrt(n - 2 + t * t)


def rho_of(xs: Mapping[str, float], ys: Mapping[str, float], keys: Sequence[str]) -> float:
    ks = [k for k in keys if k in xs and k in ys]
    return spearman([xs[k] for k in ks], [ys[k] for k in ks])


# ---- figure --------------------------------------------------------------------------------------


def fig_scatter(
    xs: Mapping[str, float],
    ys: Mapping[str, float],
    title: str,
    xlabel: str,
    path: Path,
    note: str,
    logx: bool,
) -> None:
    import matplotlib.pyplot as plt

    keys = sorted(k for k in xs if k in ys)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.scatter(
        [xs[k] for k in keys],
        [ys[k] for k in keys],
        s=22,
        color=[SERIES[1] if k == JP else "#7f9cc4" for k in keys],
    )
    for k in keys:
        ax.annotate(
            k, (xs[k], ys[k]), fontsize=6.5, color=INK, xytext=(3, 2), textcoords="offset points"
        )
    if logx:
        ax.set_xscale("log")
    ax.set_xlabel(xlabel, fontsize=8, color=INK)
    ax.set_ylabel("一般政府支出 ÷ GDP（%、2019〜2023 年平均）", fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    fig.text(
        0.01,
        0.005,
        f"出典: OECD Government at a Glance 2025、IPU Parline（CC BY-NC-SA 4.0）。{note}",
        fontsize=7,
        color=MUTED,
    )
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
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    gov = pl.read_parquet(marts / "oecd_gov_finance.parquet")
    eco = pl.read_parquet(marts / "ilo_emp_public_admin.parquet")
    oecd = ipu.filter(pl.col("oecd_member"))
    lower = oecd.filter(pl.col("chamber_type") == "lower")
    names = {str(r["iso3"]): str(r["country"]) for r in lower.iter_rows(named=True)}
    seats = {str(r["iso3"]): float(r["statutory_seats"]) for r in lower.iter_rows(named=True)}
    pop_k = {str(r["iso3"]): float(r["population_thousands"]) for r in lower.iter_rows(named=True)}
    per_m = {k: per_million(seats[k], pop_k[k]) for k in seats}
    cube = {k: cube_ratio(seats[k], pop_k[k]) for k in seats}
    resid = log_residuals(seats, {k: v * 1000 for k, v in pop_k.items()})
    staff: dict[str, float] = {}
    for iso3, grp in oecd.group_by("iso3"):
        s = staff_per_member(list(grp.iter_rows(named=True)))
        if s is not None:
            staff[str(iso3[0])] = s[0]
    with FEDERAL_CSV.open(encoding="utf-8") as f:
        federal = {r["iso3"] for r in csv.DictReader(f) if r["federal"] == "1"}

    def series(metric: str) -> dict[str, list[dict[str, object]]]:
        out: dict[str, list[dict[str, object]]] = {}
        for r in gov.filter(pl.col("metric") == metric).iter_rows(named=True):
            out.setdefault(str(r["iso3"]), []).append(r)
        return out

    ge_rows, gr_rows = series("gov_expenditure_pct_gdp"), series("gov_revenue_pct_gdp")
    ge = {k: v for k in seats if (v := window_mean(ge_rows.get(k, []))) is not None}
    ge19 = {k: v for k in seats if (v := window_mean(ge_rows.get(k, []), (2019, 2019))) is not None}
    gr = {k: v for k in seats if (v := window_mean(gr_rows.get(k, []))) is not None}
    admin: dict[str, float] = {}
    for iso3, grp in eco.filter(pl.col("metric") == "emp_public_admin").group_by("iso3"):
        lv = latest_value(list(grp.iter_rows(named=True)))
        if lv is not None and str(iso3[0]) in pop_k:
            admin[str(iso3[0])] = per_thousand(lv[1], pop_k[str(iso3[0])])

    keys = sorted(k for k in seats if k in ge)
    n = len(keys)
    print(
        "# R16（番外編）議会の大きさは「小さな政府／大きな政府」と関係するか"
        "（H15a〜d）（2026-10-29）"
    )
    print("\n事後追加の仮説（設計書 2026-10-29 深夜 節）。順位相関の記述のみ。因果の主張はない。")
    print("\n## 表 1: 政府の大きさと議会の大きさ（OECD 下院、政府支出比の高い順）")
    print(
        md_row(
            [
                "国",
                "支出 ÷ GDP %（19–23 平均）",
                "収入 ÷ GDP %",
                "下院 /100 万人",
                "立方根補正比",
                "log 残差",
                "職員 ÷ 議員",
                "公務 /1,000 人",
                "連邦",
            ]
        )
    )
    print("|" + "---|" * 9)
    for k in sorted(keys, key=lambda k: -ge[k]):
        mark = "**" if k == JP else ""
        print(
            md_row(
                [
                    f"{mark}{names[k]}{mark}",
                    f"{ge[k]:.1f}",
                    f"{gr[k]:.1f}" if k in gr else "–",
                    f"{per_m[k]:.2f}",
                    f"{cube[k]:.2f}",
                    f"{resid[k]:+.2f}" if k in resid else "–",
                    f"{staff[k]:.1f}" if k in staff else "–",
                    f"{admin[k]:.1f}" if k in admin else "–",
                    "連邦" if k in federal else "",
                ]
            )
        )
    crit = critical_rho(n)
    rho_a = rho_of(per_m, ge, keys)
    rho_b = rho_of(cube, ge, keys)
    rho_r = rho_of(resid, ge, keys)
    rho_d = rho_of(staff, ge, keys)
    n_d = len([k for k in keys if k in staff])
    med = sorted(ge.values())[n // 2]
    print(
        f"\n- 日本の一般政府支出比は {ge[JP]:.1f}%（2019〜2023 年平均）で {n} か国中 高い方から "
        f"{n + 1 - rank_of(ge, JP)} 位（中央値 {med:.1f}%）。2019 年単独では {ge19[JP]:.1f}%"
    )
    print("\n## 判定")
    print(
        f"- **H15a**: 人口当たり議員数 × 支出比 ρ = {rho_a:+.2f}"
        f"（n = {n}、p = {p_value(rho_a, n):.3f}）"
        f" → **{judge_h15a(rho_a)}**（ρ ≥ +0.3 で整合）"
    )
    print(
        f"- **H15b**: 立方根補正比 × 支出比 ρ = {rho_b:+.2f}（p = {p_value(rho_b, n):.3f}）"
        f" → **{judge_h15b(rho_b)}**（|ρ| < 0.2 で整合、≥ 0.3 で不支持）"
    )
    print(
        f"- **H15c**: 向き = {direction_h15c(rho_b)}。"
        f"log 回帰残差で補正しても ρ = {rho_r:+.2f}（p = {p_value(rho_r, n):.3f}）"
    )
    print(
        f"- **H15d**: 職員 ÷ 議員 × 支出比 ρ = {rho_d:+.2f}"
        f"（n = {n_d}、p = {p_value(rho_d, n_d):.3f}）"
        f" → **{judge_h15d(rho_d)}**（|ρ| < 0.3 で整合）"
    )
    print(f"- 参考: n = {n} で両側 5% 有意になる |ρ| の境界は {crit:.2f}")
    slope = log_slope(seats, {k: v * 1000 for k, v in pop_k.items()})
    print("\n## 頑健性")
    print(md_row(["仕様", "n", "素の比率 ρ", "立方根補正 ρ", "log 残差 ρ"]))
    print("|" + "---|" * 5)

    def row(label: str, ks: Sequence[str], y: Mapping[str, float]) -> None:
        print(
            md_row(
                [
                    label,
                    len([k for k in ks if k in y]),
                    f"{rho_of(per_m, y, ks):+.2f}",
                    f"{rho_of(cube, y, ks):+.2f}",
                    f"{rho_of(resid, y, ks):+.2f}",
                ]
            )
        )

    row("本体（支出比 2019〜2023 平均）", keys, ge)
    row("2019 年単独", keys, ge19)
    row("政府収入比（2019〜2023 平均）", keys, gr)
    row("米国を除く", [k for k in keys if k != "USA"], ge)
    row("連邦制のみ", [k for k in keys if k in federal], ge)
    row("単一制のみ", [k for k in keys if k not in federal], ge)
    row("人口 1,000 万人以上", [k for k in keys if pop_k[k] >= 10_000], ge)
    row("人口 1,000 万人未満", [k for k in keys if pop_k[k] < 10_000], ge)
    row("人口当たり公務就業者（R10、従属変数を置換）", keys, admin)
    rho_pop_ge = rho_of(pop_k, ge, keys)
    print(
        f"\n- log(定数) の log(人口) への回帰の傾き = {slope:.2f}（立方根法則なら 0.33）。"
        f"人口 × 支出比 ρ = {rho_pop_ge:+.2f}（小国ほど政府が大きいか）"
    )
    fig_scatter(
        per_m,
        ge,
        "人口当たり議員数と政府の大きさ（OECD 下院）",
        "人口 100 万人当たり下院定数（対数軸）",
        args.fig_dir / "r16_raw_vs_spending.png",
        f"n = {n}。横軸は対数",
        True,
    )
    fig_scatter(
        cube,
        ge,
        "立方根補正した議会の大きさと政府の大きさ（OECD 下院）",
        "下院定数 ÷ 人口の立方根（1.0 = 立方根法則どおり）",
        args.fig_dir / "r16_cube_vs_spending.png",
        f"n = {n}",
        False,
    )
    print(f"\n図: {args.fig_dir}/r16_raw_vs_spending.png, r16_cube_vs_spending.png")


if __name__ == "__main__":
    main()
