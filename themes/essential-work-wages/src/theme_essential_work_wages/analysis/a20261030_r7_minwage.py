"""R7: 女性化の切り分け（H7c）と最低賃金への連動（H11〜H11c）。

日本、事後追加 第 2 弾。

結果を計算する前に設計書に固定した判定基準
（design/themes/essential-work-wages.md「事後追加の仮説（第 2 弾）」）:
  H7c : 結果 {男女計, 男性, 女性} × 差分幅 {1 年, 3 年} の 6 通りの β。
        3 年差分の男性 β が 1 年差分の 50% 以上残り、かつ女性 β の区間上限 < 0 なら
        「評価の低下と整合」。縮む／区間が 0 をまたげば「標本の入れ替わりと区別できない」。
  H11 : Kaitz 比（時間当たり所定内給与 ÷ 最低賃金）が分類の始点で < 1.3 の職種を
        「近傍」。Δlog 時間当たり賃金 = 年 FE + δ·(近傍 × Δlog 最低賃金)。
        δ ≥ 0.5 かつ下限 > 0 で整合、δ ≤ 0.2 または区間が 0 をまたげば不支持。
  H11b: E=1 の労働者のうち近傍職種の割合 ÷ E=0 の割合 ≥ 2 なら
        「最低賃金の近くに集まっている」。
  H11c: 介護職の Kaitz 比の推移（記述）。

入力: data/marts/bsws_occupation_wages.parquet、定義表、jp_minimum_wage.csv。
図: reports/figures/r7_minwage.png。決定的。
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl

from theme_essential_work_wages.analysis.a20261030_r3_admin_price import TREAT_NEW, TREAT_OLD
from theme_essential_work_wages.analysis.a20261030_r5_mechanisms import fe_regression, jp_panel
from theme_essential_work_wages.analysis.common import (
    FIGURES,
    GRID,
    INK,
    MARTS,
    MUTED,
    PKG_DIR,
    SERIES,
    md_table,
)

LOG = logging.getLogger("r7")
KAITZ_NEAR = 1.3


def load_minwage() -> dict[int, float]:
    with (PKG_DIR / "jp_minimum_wage.csv").open(encoding="utf-8", newline="") as f:
        return {
            int(r["fiscal_year"]): float(r["national_weighted_avg_yen"]) for r in csv.DictReader(f)
        }


def with_female_wage(bsws: pl.DataFrame, d: pl.DataFrame) -> pl.DataFrame:
    fw = bsws.filter((pl.col("sex") == "F") & (pl.col("size_class") == "all")).select(
        "year", "occupation", pl.col("scheduled_wage_thousand_yen").alias("wage_f")
    )
    return d.join(fw, on=["year", "occupation"], how="left").with_columns(
        (pl.col("wage_f").log() - pl.col("med").log()).alias("rel_female")
    )


def k_difference(d: pl.DataFrame, cols: list[str], k: int) -> pl.DataFrame:
    prev = d.select(
        "occupation",
        "classification",
        (pl.col("year") + k).alias("year"),
        *[pl.col(c).alias(f"{c}_prev") for c in cols],
    )
    out = d.join(prev, on=["occupation", "classification", "year"], how="inner")
    return out.with_columns([(pl.col(c) - pl.col(f"{c}_prev")).alias(f"d_{c}") for c in cols])


def h7c_block(d: pl.DataFrame) -> None:
    print(
        "\n### H7c: 女性化の切り分け"
        "（結果 × 差分幅、年齢・勤続の差分を統制、年 FE、職種クラスタ、加重）"
    )
    base = d.filter(pl.col("rel_male").is_not_null() & pl.col("rel_female").is_not_null())
    cols = ["rel", "rel_male", "rel_female", "female_share", "age", "tenure_years"]
    rows: list[list[object]] = []
    est: dict[tuple[str, int], tuple[float, float]] = {}
    for k in (1, 3):
        fd = k_difference(base, cols, k)
        for label, y in (("男女計", "d_rel"), ("男性", "d_rel_male"), ("女性", "d_rel_female")):
            reg = fe_regression(
                fd, y, ["d_female_share", "d_age", "d_tenure_years"], "workers", "occupation"
            )
            c, se, lo, hi = reg["d_female_share"]
            est[(label, k)] = (c, hi)
            rows.append(
                [
                    f"{k} 年差分",
                    label,
                    int(reg["_n"][0]),
                    f"{c:+.3f} (SE {se:.3f}, {lo:+.3f}〜{hi:+.3f})",
                ]
            )
    print(md_table(["差分幅", "結果（相対賃金）", "n", "β（Δ女性比率）"], rows))
    m1, m3 = est[("男性", 1)][0], est[("男性", 3)][0]
    f3_hi = est[("女性", 3)][1]
    keep = m3 / m1 if m1 != 0 else math.nan
    v = (
        "評価の低下と整合"
        if (keep >= 0.5 and f3_hi < 0 and est[("男性", 3)][1] < 0)
        else "標本の入れ替わりと区別できない"
    )
    print(
        f"**H7c 判定: {v}**（男性 β 1 年 {m1:+.3f} → 3 年 {m3:+.3f}、残存率 {keep:.2f}。"
        f"女性 3 年差分の区間上限 {f3_hi:+.3f}）"
    )


def kaitz_panel(d: pl.DataFrame, mw: dict[int, float]) -> pl.DataFrame:
    """Kaitz 比と、調査年に効いている最低賃金の前年比（log）。系列の無い年は None。"""
    x = d.filter(pl.col("scheduled_hours").is_not_null() & (pl.col("scheduled_hours") > 0))
    years = x["year"].to_list()
    x = x.with_columns(
        (pl.col("wage") * 1000.0 / pl.col("scheduled_hours")).alias("hourly"),
        pl.Series("minwage", [mw[int(y) - 1] for y in years]),
        pl.Series(
            "d_log_mw",
            [
                math.log(mw[int(y) - 1]) - math.log(mw[int(y) - 2]) if (int(y) - 2) in mw else None
                for y in years
            ],
            dtype=pl.Float64,
        ),
    ).with_columns(
        (pl.col("hourly") / pl.col("minwage")).alias("kaitz"),
        pl.col("hourly").log().alias("log_hourly"),
    )
    start = x.filter(
        ((pl.col("classification") == "jp_bsws2009") & (pl.col("year") == 2009))
        | ((pl.col("classification") == "jp_bsws2020") & (pl.col("year") == 2020))
    ).select(
        "occupation",
        "classification",
        (pl.col("kaitz") < KAITZ_NEAR).cast(pl.Int64).alias("near"),
        pl.col("kaitz").alias("kaitz_start"),
    )
    return x.join(start, on=["occupation", "classification"], how="inner")


def h11_block(d: pl.DataFrame, mw: dict[int, float]) -> pl.DataFrame:
    kp = kaitz_panel(d, mw)
    print(
        "\n### H11: 最低賃金への連動"
        "（Kaitz 比 = 時間当たり所定内給与 ÷ 最低賃金、近傍 = 始点で < 1.3）"
    )
    for cls, y0 in (("jp_bsws2009", 2009), ("jp_bsws2020", 2020)):
        s = kp.filter((pl.col("classification") == cls) & (pl.col("year") == y0))
        near = s.filter(pl.col("near") == 1)
        near_share = float(near["workers"].sum()) / float(s["workers"].sum())
        print(
            f"{cls} {y0} 年: 近傍職種 {near.height}/{s.height}（労働者 {near_share:.2f}）。例: "
            + "、".join(
                f"{r['occupation']} {r['kaitz']:.2f}"
                for r in near.sort("kaitz").head(8).iter_rows(named=True)
            )
        )
    fd = k_difference(kp, ["log_hourly"], 1).with_columns(
        (pl.col("near") * pl.col("d_log_mw")).alias("near_x_dmw")
    )
    rows: list[list[object]] = []
    main = None
    for name, sub, w in (
        ("主（加重）", fd, "workers"),
        ("重みなし", fd.with_columns(pl.lit(1.0).alias("one")), "one"),
        ("旧分類のみ", fd.filter(pl.col("classification") == "jp_bsws2009"), "workers"),
        ("新分類のみ", fd.filter(pl.col("classification") == "jp_bsws2020"), "workers"),
        (
            "近傍 < 1.2 で定義",
            fd.with_columns(
                ((pl.col("kaitz_start") < 1.2).cast(pl.Int64) * pl.col("d_log_mw")).alias(
                    "near_x_dmw"
                )
            ),
            "workers",
        ),
        (
            "近傍 < 1.5 で定義",
            fd.with_columns(
                ((pl.col("kaitz_start") < 1.5).cast(pl.Int64) * pl.col("d_log_mw")).alias(
                    "near_x_dmw"
                )
            ),
            "workers",
        ),
    ):
        reg = fe_regression(sub, "d_log_hourly", ["near_x_dmw"], w, "occupation")
        c, se, lo, hi = reg["near_x_dmw"]
        if name.startswith("主"):
            main = (c, lo, hi)
        rows.append([name, int(reg["_n"][0]), f"{c:+.3f} (SE {se:.3f}, {lo:+.3f}〜{hi:+.3f})"])
    print(md_table(["仕様", "n", "δ（近傍 × Δlog 最低賃金）"], rows))
    assert main is not None
    c, lo, hi = main
    v = "整合" if (c >= 0.5 and lo > 0) else ("不支持" if (c <= 0.2 or lo <= 0) else "中間")
    print(
        f"**H11 判定: {v}**（δ = {c:+.3f}。"
        f"近傍職種は最低賃金の上昇率 1% につき非近傍より {c:+.2f}% 余計に上がる）"
    )
    # descriptive: cumulative growth near vs far vs min wage
    for cls, y0, y1 in (("jp_bsws2009", 2009, 2019), ("jp_bsws2020", 2020, 2025)):
        a = kp.filter((pl.col("classification") == cls) & (pl.col("year") == y0)).select(
            "occupation", pl.col("log_hourly").alias("l0"), "workers", "near"
        )
        b = kp.filter((pl.col("classification") == cls) & (pl.col("year") == y1)).select(
            "occupation", pl.col("log_hourly").alias("l1")
        )
        ab = a.join(b, on="occupation")
        parts = []
        for flag, lab in ((1, "近傍"), (0, "非近傍")):
            s = ab.filter(pl.col("near") == flag)
            wt = s["workers"].to_numpy()
            g = float((wt * (s["l1"] - s["l0"]).to_numpy()).sum() / wt.sum())
            parts.append(f"{lab} {100 * g:+.1f}%（{s.height} 職種）")
        mwg = 100 * (math.log(mw[y1 - 1]) - math.log(mw[y0 - 1]))
        print(
            f"{y0}→{y1} の時間当たり賃金の累積変化（加重平均）: "
            + "、".join(parts)
            + f"、最低賃金 {mwg:+.1f}%"
        )
    # H11b
    for cls, y0 in (("jp_bsws2009", 2009), ("jp_bsws2020", 2020)):
        s = kp.filter((pl.col("classification") == cls) & (pl.col("year") == y0))
        sh = {}
        for flag in (1, 0):
            e = s.filter(pl.col("essential") == flag)
            sh[flag] = float(e.filter(pl.col("near") == 1)["workers"].sum()) / float(
                e["workers"].sum()
            )
        ratio = sh[1] / sh[0] if sh[0] > 0 else math.nan
        verdict = "整合（≥ 2）" if ratio >= 2 else "不支持"
        print(
            f"H11b（{y0} 年）: E=1 の労働者のうち近傍職種 {sh[1]:.2f}、E=0 {sh[0]:.2f}、"
            f"比 {ratio:.2f} → {verdict}"
        )
    # H11c
    care = kp.filter(pl.col("occupation").is_in([TREAT_OLD, TREAT_NEW])).sort("year")
    print(
        "H11c 介護職の Kaitz 比: "
        + ", ".join(f"{int(r['year'])} {r['kaitz']:.2f}" for r in care.iter_rows(named=True))
    )
    return kp


def fig(kp: pl.DataFrame, path: Path) -> None:
    fig_, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    s = kp.filter((pl.col("classification") == "jp_bsws2020") & (pl.col("year") == 2025))
    for flag, c, lab in ((1, SERIES[0], "E=1"), (0, MUTED, "E=0")):
        x = s.filter(pl.col("essential") == flag)
        ax.scatter(
            x["kaitz"], x["workers"] / 1e4, s=12, color=c, alpha=0.7, edgecolor="none", label=lab
        )
    ax.axvline(KAITZ_NEAR, color=INK, linestyle="--", linewidth=1)
    ax.set_xscale("log")
    ax.set_xlabel("Kaitz 比（時間当たり所定内給与 ÷ 最低賃金、対数）、2025 年", color=INK)
    ax.set_ylabel("労働者数（万人）", color=INK)
    ax.set_title("H11b: 職種の最低賃金からの距離と労働者数", color=INK, fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    ax.grid(color=GRID)
    ax = axes[1]
    for occ, c, lab in (
        (TREAT_OLD, SERIES[0], "介護（旧）"),
        (TREAT_NEW, SERIES[0], "介護（新）"),
        ("警備員", SERIES[1], "警備員"),
        ("ビル清掃員", SERIES[2], "ビル清掃員（旧）"),
        ("ビル・建物清掃員", SERIES[2], "ビル・建物清掃員（新）"),
        ("看護師", SERIES[3], "看護師"),
    ):
        x = kp.filter(pl.col("occupation") == occ).sort("year")
        if x.height:
            ax.plot(x["year"], x["kaitz"], marker="o", color=c, label=lab, linewidth=1.2)
    ax.axhline(KAITZ_NEAR, color=INK, linestyle="--", linewidth=1)
    ax.set_ylabel("Kaitz 比", color=INK)
    ax.set_title("H11c: Kaitz 比の推移（破線 = 近傍の閾値 1.3）", color=INK, fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    ax.grid(color=GRID)
    for a_ in axes:
        a_.set_axisbelow(True)
        for sp in ("top", "right"):
            a_.spines[sp].set_visible(False)
    fig_.tight_layout()
    fig_.savefig(path, dpi=150)
    plt.close(fig_)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marts", type=Path, default=MARTS)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    plt.rcParams["font.family"] = ["IPAGothic", "IPAexGothic", "Noto Sans CJK JP", "DejaVu Sans"]
    bsws = pl.read_parquet(args.marts / "bsws_occupation_wages.parquet")
    d = with_female_wage(bsws, jp_panel(bsws))
    mw = load_minwage()
    print("# R7 女性化の切り分け（H7c）と最低賃金への連動（H11）。日本、事後追加 第 2 弾")
    h7c_block(d)
    kp = h11_block(d, mw)
    args.figures.mkdir(parents=True, exist_ok=True)
    fig(kp, args.figures / "r7_minwage.png")
    print("\nfigures: r7_minwage.png")


if __name__ == "__main__":
    main()
