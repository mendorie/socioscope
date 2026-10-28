"""R10: 官僚が多い国ほど議員は少ないか（H2e、ユーザー提起）。

事後追加の仮説 H2e（design/themes/parliament-size.md「事後追加（2026-10-28 夜）」、
結果の計算前に固定）:
  人口当たりの公務就業者（ILOSTAT EMP_TEMP_SEX_ECO_NB、ISIC Rev.4 大分類 O「公務・防衛・社会保障」、
  最新年）と 人口当たり下院議員数（IPU）の Spearman ρ ≤ −0.3 なら整合、|ρ| < 0.2 なら不支持、
  その間は中間。補助（探索的）: 公的部門就業者（INS_SECTOR_PUB）でも同じ相関、議員 1 人当たりの
  公務就業者数での日本の順位、米国を除いた ρ。ISIC O は警察・軍人・自治体職員を含む。

決定的スクリプト。入力は data/marts/{ilo_emp_public_admin, ilo_emp_public_sector,
ipu_parliaments}.parquet。
純粋ヘルパは tests/test_analysis_r10.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row
from theme_parliament_size.analysis.a20261027_r3_cost import rank_of
from theme_parliament_size.analysis.a20261027_r5_roles import judge_h2a, spearman

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
MAX_YEAR = 2025


# ---- pure helpers -------------------------------------------------------------------------------


def latest_value(
    rows: Sequence[Mapping[str, object]], max_year: int = MAX_YEAR
) -> tuple[int, float] | None:
    """[{year, value_thousands}] → max_year 以下で最新の (年, 値)。無ければ None。"""
    cands = [
        (int(str(r["year"])), float(str(r["value_thousands"])))
        for r in rows
        if int(str(r["year"])) <= max_year
    ]
    return max(cands) if cands else None


def per_thousand(value_thousands: float, population_thousands: float) -> float:
    """千人単位の就業者 ÷ 千人単位の人口 × 1000 = 人口 1,000 人当たりの人数。"""
    return 1000.0 * value_thousands / population_thousands


# ---- figure --------------------------------------------------------------------------------------


def fig_scatter(
    xs: Mapping[str, float],
    ys: Mapping[str, float],
    title: str,
    ylabel: str,
    path: Path,
    n_note: str,
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
    ax.set_xscale("log")
    ax.set_xlabel("人口 100 万人当たり下院議員数（対数軸）", fontsize=8, color=INK)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    note = f"出典: ILOSTAT（CC BY 4.0）、IPU Parline（CC BY-NC-SA 4.0）。{n_note}。横軸は対数"
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
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    eco = pl.read_parquet(marts / "ilo_emp_public_admin.parquet")
    ins = pl.read_parquet(marts / "ilo_emp_public_sector.parquet")
    lower = ipu.filter(pl.col("oecd_member") & (pl.col("chamber_type") == "lower"))
    names = {str(r["iso3"]): str(r["country"]) for r in lower.iter_rows(named=True)}
    per_m = {
        str(r["iso3"]): float(r["statutory_seats"]) / (float(r["population_thousands"]) / 1000)
        for r in lower.iter_rows(named=True)
    }
    pop_k = {str(r["iso3"]): float(r["population_thousands"]) for r in lower.iter_rows(named=True)}
    seats = {str(r["iso3"]): float(r["statutory_seats"]) for r in lower.iter_rows(named=True)}

    def latest_by_country(df: pl.DataFrame, metric: str) -> dict[str, tuple[int, float]]:
        out: dict[str, tuple[int, float]] = {}
        for iso3, grp in df.filter(pl.col("metric") == metric).group_by("iso3"):
            v = latest_value(list(grp.iter_rows(named=True)))
            if v is not None and str(iso3[0]) in per_m:
                out[str(iso3[0])] = v
        return out

    admin = latest_by_country(eco, "emp_public_admin")
    total = latest_by_country(eco, "emp_total")
    public = latest_by_country(ins, "emp_public_sector")
    admin_pt = {k: per_thousand(v[1], pop_k[k]) for k, v in admin.items()}
    admin_share = {k: 100.0 * v[1] / total[k][1] for k, v in admin.items() if k in total}
    public_pt = {k: per_thousand(v[1], pop_k[k]) for k, v in public.items()}
    per_member = {k: 1000.0 * v[1] / seats[k] for k, v in admin.items()}

    print("# R10 官僚が多い国ほど議員は少ないか（H2e）（2026-10-28）")
    print("\n事後追加の仮説（設計書 2026-10-28 夜 節）。順位相関の記述のみ。因果の主張はない。")
    print("\n## 表 1: 人口当たりの公務就業者（ISIC O）と人口当たり議員数（OECD、議員数の少ない順）")
    print(
        md_row(
            [
                "国",
                "下院 /100 万人",
                "公務就業者（千人）",
                "年",
                "人口 1,000 人当たり",
                "就業者に占める %",
                "議員 1 人当たり公務就業者",
                "公的部門 /1,000 人",
            ]
        )
    )
    print("|" + "---|" * 8)
    for k in sorted(per_m, key=lambda k: per_m[k]):
        mark = "**" if k == JP else ""
        a = admin.get(k)
        print(
            md_row(
                [
                    f"{mark}{names[k]}{mark}",
                    f"{per_m[k]:.2f}",
                    f"{a[1]:,.0f}" if a else "–",
                    a[0] if a else "–",
                    f"{admin_pt[k]:.1f}" if k in admin_pt else "–",
                    f"{admin_share[k]:.1f}" if k in admin_share else "–",
                    f"{per_member[k]:,.0f}" if k in per_member else "–",
                    f"{public_pt[k]:.1f}" if k in public_pt else "–",
                ]
            )
        )
    keys = sorted(k for k in admin_pt if k in per_m)
    rho = spearman([per_m[k] for k in keys], [admin_pt[k] for k in keys])
    no_us = [k for k in keys if k != "USA"]
    rho_no_us = spearman([per_m[k] for k in no_us], [admin_pt[k] for k in no_us])
    ks = sorted(k for k in admin_share if k in per_m)
    rho_share = spearman([per_m[k] for k in ks], [admin_share[k] for k in ks])
    kp = sorted(k for k in public_pt if k in per_m)
    rho_pub = spearman([per_m[k] for k in kp], [public_pt[k] for k in kp])
    med = sorted(admin_pt.values())[len(admin_pt) // 2]
    med_pm = sorted(per_member.values())[len(per_member) // 2]
    print(
        f"\n- Spearman ρ（人口当たり議員数 × 人口 1,000 人当たり公務就業者）= {rho:.2f}"
        f"（n = {len(keys)}）。日本 {admin_pt[JP]:.1f} 人/1,000 人（{admin[JP][0]} 年）は "
        f"{len(admin_pt)} か国中 少ない方から {rank_of(admin_pt, JP)} 位（中央値 {med:.1f}）"
    )
    print(f"- **H2e 判定: {judge_h2a(rho)}**（ρ ≤ −0.3 で整合、|ρ| < 0.2 で不支持）")
    print(
        f"- 探索的: 米国を除く ρ = {rho_no_us:.2f}（n = {len(no_us)}）。"
        f"就業者に占める公務の比率で ρ = {rho_share:.2f}（n = {len(ks)}）。"
        f"公的部門就業者（教育・医療を含む）で ρ = {rho_pub:.2f}（n = {len(kp)}）"
    )
    print(
        f"- 探索的: 議員 1 人当たりの公務就業者は日本 {per_member[JP]:,.0f} 人で "
        f"{len(per_member)} か国中 多い方から {len(per_member) + 1 - rank_of(per_member, JP)} 位"
        f"（中央値 {med_pm:,.0f}）"
    )
    # 規模効果の確認: 人口当たり議員数も人口当たり公務就業者も、人口の大きい国ほど低いか
    rho_pm_pop = spearman([pop_k[k] for k in keys], [per_m[k] for k in keys])
    rho_adm_pop = spearman([pop_k[k] for k in keys], [admin_pt[k] for k in keys])
    print(
        f"- 規模効果（事後）: 人口 × 人口当たり議員数 ρ = {rho_pm_pop:.2f}、"
        f"人口 × 人口当たり公務就業者 ρ = {rho_adm_pop:.2f}（n = {len(keys)}）"
    )
    fig_scatter(
        per_m,
        admin_pt,
        "官僚が多い国ほど議員は少ないか（OECD 下院、ISIC O 公務・防衛・社会保障）",
        "人口 1,000 人当たりの公務就業者",
        args.fig_dir / "r10_bureaucracy.png",
        f"n = {len(keys)}、就業者は各国の最新年",
    )
    print(f"\n図: {args.fig_dir}/r10_bureaucracy.png")


if __name__ == "__main__":
    main()
