"""R6: 保健支出の公的シェアが高い国ほど看護師の相対賃金が低いか
（H3c、設計の未着手分。事後追加節で再登録）。

判定（設計書 H3c）: OECD 内で Spearman ρ ≤ −0.3 なら整合、|ρ| < 0.2 なら不支持。
粗い対照で弱い証拠。
事後の具体化（結果を見る前に固定）: 公的シェアは World Bank WDI `SH.XPD.GHED.CH.ZS`
（国内一般政府保健支出 ÷ 経常保健支出、%。OECD SHA の「政府・強制保険」とは定義が違い、
強制保険は含まれない国がある）。看護師の相対賃金は OECD `DF_REMUN` の病院看護師
（被用者、男女計）の報酬 ÷ 平均賃金。各国の最新年（2019 年以降）どうしを対応させる。
補助: 1 人当たり経常保健支出（US ドル）・対 GDP 比との ρ、OECD 以外を含めた全体。

入力: data/marts/{oecd_health_remuneration, wdi_health_expenditure}.parquet。
図: reports/figures/r6_h3c.png。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
from scipy.stats import spearmanr

from theme_essential_work_wages.analysis.a20261030_r4_strikes import OECD
from theme_essential_work_wages.analysis.common import FIGURES, GRID, INK, MARTS, SERIES, md_table

LOG = logging.getLogger("r6")


def latest_nurse_ratio(remun: pl.DataFrame) -> pl.DataFrame:
    n = remun.filter(
        (pl.col("health_prof") == "RINF")
        & (pl.col("unit") == "FCTR_WG_A_SAL_A")
        & (pl.col("worker_status") == "ICSE93_1")
        & (pl.col("sex") == "_T")
        & (pl.col("year") >= 2019)
    ).sort("year")
    return n.group_by("iso3").agg(
        pl.col("year").last().alias("year_nurse"), pl.col("value").last().alias("nurse_ratio")
    )


def latest_wdi(wdi: pl.DataFrame) -> pl.DataFrame:
    w = wdi.filter((pl.col("year") >= 2019) & pl.col("gov_share_pct").is_not_null()).sort("year")
    return w.group_by("iso3").agg(
        pl.col("year").last().alias("year_wdi"),
        pl.col("gov_share_pct").last(),
        pl.col("chex_gdp_pct").last(),
        pl.col("chex_pc_usd").last(),
    )


def rho(d: pl.DataFrame, x: str, y: str) -> tuple[float, int]:
    s = d.filter(pl.col(x).is_not_null() & pl.col(y).is_not_null())
    if s.height < 5:
        return float("nan"), s.height
    r, _ = spearmanr(s[x].to_numpy(), s[y].to_numpy())
    return float(r), s.height


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marts", type=Path, default=MARTS)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    plt.rcParams["font.family"] = ["IPAGothic", "IPAexGothic", "Noto Sans CJK JP", "DejaVu Sans"]
    remun = pl.read_parquet(args.marts / "oecd_health_remuneration.parquet")
    wdi = pl.read_parquet(args.marts / "wdi_health_expenditure.parquet")
    d = latest_nurse_ratio(remun).join(latest_wdi(wdi), on="iso3", how="inner").sort("iso3")
    oecd = d.filter(pl.col("iso3").is_in(sorted(OECD)))
    print("# R6 H3c: 保健支出の公的シェアと病院看護師の相対賃金（最新年、2019 年以降）")
    rows = [
        [
            r["iso3"],
            int(r["year_nurse"]),
            f"{r['nurse_ratio']:.2f}",
            int(r["year_wdi"]),
            f"{r['gov_share_pct']:.1f}",
            f"{r['chex_gdp_pct']:.1f}",
            f"{r['chex_pc_usd']:,.0f}",
        ]
        for r in oecd.sort("gov_share_pct", descending=True).iter_rows(named=True)
    ]
    print(
        md_table(
            [
                "国",
                "年（看護師）",
                "看護師 ÷ 平均賃金",
                "年（WDI）",
                "政府支出シェア %",
                "保健支出 %GDP",
                "1 人当たり USD",
            ],
            rows,
        )
    )
    r_main, n_main = rho(oecd, "gov_share_pct", "nurse_ratio")
    v = "整合" if r_main <= -0.3 else ("不支持" if abs(r_main) < 0.2 else "中間")
    print(f"\n**H3c 判定（OECD {n_main} か国、Spearman ρ）: ρ = {r_main:+.3f} → {v}**")
    for x, label in (("chex_gdp_pct", "保健支出 %GDP"), ("chex_pc_usd", "1 人当たり保健支出 USD")):
        r_, n_ = rho(oecd, x, "nurse_ratio")
        print(f"補助: {label} × 看護師比 ρ = {r_:+.3f}（n={n_}）")
    r_all, n_all = rho(d, "gov_share_pct", "nurse_ratio")
    print(f"補助: OECD 以外を含む全体 ρ = {r_all:+.3f}（n={n_all}）")
    jp = oecd.filter(pl.col("iso3") == "JPN")
    if jp.height:
        jp_ratio = float(jp["nurse_ratio"][0])
        jp_share = float(jp["gov_share_pct"][0])
        print(f"日本: 看護師比 {jp_ratio:.2f}、政府シェア {jp_share:.1f}%")
    print(
        "注: WDI の政府シェアは社会保険を「政府」に含めるかが国で違う"
        "（日本・ドイツ・フランスの強制保険は含まれる）。粗い対照であり、弱い証拠。"
    )

    args.figures.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(
        oecd["gov_share_pct"],
        oecd["nurse_ratio"],
        s=30,
        color=SERIES[0],
        alpha=0.7,
        edgecolor="none",
    )
    for r in oecd.iter_rows(named=True):
        ax.annotate(
            r["iso3"],
            (r["gov_share_pct"], r["nurse_ratio"]),
            fontsize=7,
            color=INK,
            xytext=(3, 2),
            textcoords="offset points",
        )
    ax.set_xlabel("国内一般政府保健支出 ÷ 経常保健支出（%、WDI）", color=INK)
    ax.set_ylabel("病院看護師の報酬 ÷ 平均賃金（OECD）", color=INK)
    ax.set_title(f"H3c: OECD {n_main} か国、Spearman ρ = {r_main:+.2f}", color=INK, fontsize=10)
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(args.figures / "r6_h3c.png", dpi=150)
    plt.close(fig)
    print("\nfigures: r6_h3c.png")


if __name__ == "__main__":
    main()
