"""R2: 資格なしの高報酬はレントへの近さで決まるか（H6、対照群 2）。

事前登録（design/themes/essential-work-wages.md、2026-10-29）と事後の具体化（同「事後記録」、
結果を見る前に固定）:
  H6  : 同じ職業で、金融・保険（K）、情報通信（J）、専門・科学・技術（M）の賃金 ÷ 職業全体 ≥ 1.30、
        かつ 産業 × 職業セルの賃金比と産業の 1 人当たり付加価値の Spearman ρ ≥ 0.5 なら整合。
        プレミアムが 1.10 未満なら不支持（高報酬は職業の技能に帰属する）。
        データ: Eurostat SES 2018・2022（ISCO-08 大分類 × NACE 大分類、平均時給、男女計）と
        Eurostat 国民経済計算（NACE 大分類の 1 人当たり付加価値）。国別に判定し、
        整合した国の割合で報告。
        対象職業は ISCO 大分類 OC2（専門職。ICT・金融アナリスト・経営コンサルタントを含む）と
        OC3（準専門職。証券ディーラー等を含む）。SES は 1 桁 ISCO しか無いので、2 桁（25・24・33）で
        設計した判定を 1 桁で代替する（事後の具体化、2026-10-30 未明）。
  H6b : p90/p10 は平均しか無いため代替できない。代わりに「同じ職業の産業間のばらつき
        （最大 ÷ 最小、B〜S の大分類）」を OC2 と OC5（サービス・販売）・OC9（単純労務）で比べ、
        探索的に報告する（判定はしない）。
  H6 日本: 職業 × 産業が無いため、賃金構造基本統計調査の 職種 × 企業規模
        （1,000 人以上 ÷ 10〜99 人）の「規模プレミアム」を、資格なし高報酬群（control2）と
        エッセンシャル低賃金群（essential_low）で
        比べる。判定基準は H6 と同じ 1.30 を control2 に、essential_low は記述（事後の具体化）。

決定的スクリプト。入力は data/marts/{ses_occupation_industry_earnings, ses_occupation_earnings,
nama_industry_value_added_employment, bsws_occupation_wages}.parquet。
図は reports/figures/r2_*.png。
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl
from scipy.stats import spearmanr

from theme_essential_work_wages.analysis.common import (
    FIGURES,
    GRID,
    INK,
    MARTS,
    MUTED,
    SERIES,
    as_float,
    load_flags,
    md_table,
    weighted_median,
)

LOG = logging.getLogger("r2")
RENT_SECTIONS = ("K", "J", "M")
SECTIONS = tuple("BCDEFGHIJKLMNOPQRS")
TARGET = ("OC2", "OC3")
COMPARE = ("OC5", "OC9")
OCC_LABEL = {
    "OC1": "管理職",
    "OC2": "専門職",
    "OC3": "準専門職",
    "OC4": "事務",
    "OC5": "サービス・販売",
    "OC6": "農林漁業",
    "OC7": "技能工",
    "OC8": "設備・機械運転",
    "OC9": "単純労務",
}


# ---- pure helpers ---------------------------------------------------------------------------


def premium_table(ses: pl.DataFrame, geo: str, year: int, isco: str) -> dict[str, float]:
    """{nace_section: hourly earnings ÷ same-occupation earnings in B-S} for one country-year."""
    d = ses.filter(
        (pl.col("geo") == geo)
        & (pl.col("year") == year)
        & (pl.col("isco08") == isco)
        & (pl.col("sex") == "T")
        & pl.col("hourly_earnings_eur").is_not_null()
    )
    base_row = d.filter(pl.col("nace_r2") == "B-S")
    if base_row.height != 1:
        return {}
    base = float(base_row["hourly_earnings_eur"][0])
    out: dict[str, float] = {}
    for r in d.iter_rows(named=True):
        if r["nace_r2"] in SECTIONS:
            out[str(r["nace_r2"])] = float(r["hourly_earnings_eur"]) / base
    return out


def spearman_excluding(
    prem: dict[str, float], va: dict[str, float], drop: tuple[str, ...]
) -> float:
    pairs = [(prem[s], va[s]) for s in SECTIONS if s in prem and s in va and s not in drop]
    return spearman(pairs)


def value_added_by_section(nama: pl.DataFrame, geo: str, year: int) -> dict[str, float]:
    d = nama.filter(
        (pl.col("geo") == geo)
        & (pl.col("year") == year)
        & pl.col("nace_r2").is_in(list(SECTIONS))
        & pl.col("value_added_per_person_keur").is_not_null()
    )
    return {
        str(r["nace_r2"]): float(r["value_added_per_person_keur"]) for r in d.iter_rows(named=True)
    }


def spearman(pairs: list[tuple[float, float]]) -> float:
    if len(pairs) < 5:
        return math.nan
    rho, _ = spearmanr([p[0] for p in pairs], [p[1] for p in pairs])
    return float(rho)


def judge_country(prem: dict[str, float], va: dict[str, float]) -> dict[str, float | str]:
    rent = [prem[s] for s in RENT_SECTIONS if s in prem]
    rent_prem = min(rent) if rent else math.nan  # 3 産業すべてで ≥ 1.30 を要求（最小値で判定）
    rent_max = max(rent) if rent else math.nan
    pairs = [(prem[s], va[s]) for s in SECTIONS if s in prem and s in va]
    rho = spearman(pairs)
    if math.isnan(rent_prem) or math.isnan(rho):
        v = "判定不能"
    elif rent_prem >= 1.30 and rho >= 0.5:
        v = "整合"
    elif rent_max < 1.10:
        v = "不支持"
    else:
        v = "中間"
    return {
        "premium_min_KJM": rent_prem,
        "premium_max_KJM": rent_max,
        "rho_ex_L": spearman_excluding(prem, va, ("L",)),
        "rho_ex_LO": spearman_excluding(prem, va, ("L", "O")),
        "premium_K": prem.get("K", math.nan),
        "premium_J": prem.get("J", math.nan),
        "premium_M": prem.get("M", math.nan),
        "rho": rho,
        "n_sections": len(pairs),
        "verdict": v,
    }


def dispersion(prem: dict[str, float]) -> float:
    vals = [v for k, v in prem.items() if k != "O"]  # 公務は国で有無が違うので除く
    return max(vals) / min(vals) if len(vals) >= 5 else math.nan


# ---- main -----------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marts", type=Path, default=MARTS)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    plt.rcParams["font.family"] = ["IPAGothic", "IPAexGothic", "Noto Sans CJK JP", "DejaVu Sans"]

    ses = pl.read_parquet(args.marts / "ses_occupation_industry_earnings.parquet")
    nama = pl.read_parquet(args.marts / "nama_industry_value_added_employment.parquet")
    bsws = pl.read_parquet(args.marts / "bsws_occupation_wages.parquet")

    print("# R2 資格なしの高報酬はレントへの近さで決まるか（H6）")
    geos = sorted(
        ses.filter(pl.col("hourly_earnings_eur").is_not_null() & pl.col("iso3").is_not_null())
        .select("geo", "year")
        .unique()
        .iter_rows()
    )
    print(f"SES の国 × 年: {len(geos)}（{', '.join(f'{g}{y % 100}' for g, y in geos)}）")

    results: list[dict[str, object]] = []
    for isco in TARGET:
        for geo, year in geos:
            prem = premium_table(ses, geo, year, isco)
            va = value_added_by_section(nama, geo, year)
            if not prem:
                continue
            j = judge_country(prem, va)
            results.append(
                {"isco": isco, "geo": geo, "year": year, **j, "dispersion": dispersion(prem)}
            )
    res = pl.DataFrame(results)

    for isco in TARGET:
        sub = res.filter(pl.col("isco") == isco).sort("year", "geo")
        print(f"\n### H6 {isco}（{OCC_LABEL[isco]}）: 国 × 年ごとの判定")
        rows = [
            [
                f"{r['geo']} {r['year']}",
                r["premium_K"],
                r["premium_J"],
                r["premium_M"],
                r["rho"],
                int(r["n_sections"]),
                r["verdict"],
            ]
            for r in sub.iter_rows(named=True)
        ]
        print(
            md_table(
                [
                    "国 年",
                    "K 金融÷全体",
                    "J 情報通信÷全体",
                    "M 専門技術÷全体",
                    "ρ（産業プレミアム × 1 人当たり付加価値）",
                    "産業数",
                    "判定",
                ],
                rows,
            )
        )
        n = sub.height
        counts = sub.group_by("verdict").len().sort("verdict")
        summary = ", ".join(f"{r['verdict']} {r['len']}" for r in counts.iter_rows(named=True))
        med_k = as_float(sub["premium_K"].median())
        med_j = as_float(sub["premium_J"].median())
        med_m = as_float(sub["premium_M"].median())
        med_rho = as_float(sub["rho"].drop_nans().median())
        med_rho_l = as_float(sub["rho_ex_L"].drop_nans().median())
        med_rho_lo = as_float(sub["rho_ex_LO"].drop_nans().median())
        print(
            f"集計: n={n}、{summary}。"
            f"プレミアムの中央値 K {med_k:.3f} / J {med_j:.3f} / M {med_m:.3f}、"
            f"ρ の中央値 {med_rho:.3f}（不動産 L を除くと {med_rho_l:.3f}、"
            f"L と公務 O を除くと {med_rho_lo:.3f}）、"
            f"ρ ≥ 0.5 の割合 {as_float((sub['rho'] >= 0.5).mean()):.2f}、"
            f"K・J・M すべて ≥ 1.30 の割合 "
            f"{as_float((sub['premium_min_KJM'] >= 1.30).mean()):.2f}、"
            f"少なくとも 1 つ ≥ 1.30 の割合 {as_float((sub['premium_max_KJM'] >= 1.30).mean()):.2f}"
        )

    # H6b exploratory: cross-industry dispersion by occupation group
    print("\n### H6b（探索）: 同じ職業大分類の産業間ばらつき（最大 ÷ 最小、公務 O を除く）")
    rows = []
    for isco in ("OC1", "OC2", "OC3", "OC4", "OC5", "OC7", "OC8", "OC9"):
        vals = [dispersion(premium_table(ses, g, y, isco)) for g, y in geos]
        vals = [v for v in vals if not math.isnan(v)]
        if vals:
            vals.sort()
            rows.append(
                [f"{isco} {OCC_LABEL[isco]}", len(vals), vals[len(vals) // 2], vals[0], vals[-1]]
            )
    print(md_table(["職業大分類", "国×年", "中央値", "最小", "最大"], rows))

    # Japan: size premium
    print(
        "\n### H6 日本: 職種 × 企業規模のプレミアム"
        "（1,000 人以上 ÷ 10〜99 人、所定内給与、2025 年、男女計）"
    )
    flags = load_flags("jp_bsws2020").select("occupation", "group", "essential", "licensed")
    b = bsws.filter((pl.col("year") == 2025) & (pl.col("sex") == "T"))
    big = b.filter(pl.col("size_class") == "1000+").select(
        "occupation",
        pl.col("scheduled_wage_thousand_yen").alias("w_big"),
        pl.col("workers").alias("n_big"),
    )
    small = b.filter(pl.col("size_class") == "10-99").select(
        "occupation",
        pl.col("scheduled_wage_thousand_yen").alias("w_small"),
        pl.col("workers").alias("n_small"),
    )
    allsz = b.filter(pl.col("size_class") == "all").select(
        "occupation", pl.col("workers").alias("n_all")
    )
    jp = (
        big.join(small, on="occupation")
        .join(allsz, on="occupation")
        .join(flags, on="occupation", how="left")
        .with_columns((pl.col("w_big") / pl.col("w_small")).alias("size_premium"))
        .filter(pl.col("size_premium").is_not_null() & (pl.col("essential") >= 0))
    )
    rows = []
    for g in ("control2", "essential_low", "control1", "control1b", "control3", "reference"):
        sub = jp.filter(pl.col("group") == g)
        med = weighted_median(
            sub["size_premium"].to_list(), sub["n_all"].cast(pl.Float64).to_list()
        )
        rows.append(
            [
                g,
                sub.height,
                med,
                as_float(sub["size_premium"].min()),
                as_float(sub["size_premium"].max()),
            ]
        )
    print(md_table(["群", "職種数", "規模プレミアム（加重中央値）", "最小", "最大"], rows))
    c2 = jp.filter(pl.col("group") == "control2").sort("size_premium", descending=True)
    print(
        "資格なし高報酬群の内訳: "
        + "; ".join(f"{r['occupation']} {r['size_premium']:.2f}" for r in c2.iter_rows(named=True))
    )
    el = jp.filter(pl.col("group") == "essential_low").sort("size_premium", descending=True)
    print(
        "エッセンシャル低賃金群の上位・下位: "
        + "; ".join(
            f"{r['occupation']} {r['size_premium']:.2f}"
            for r in list(el.iter_rows(named=True))[:3] + list(el.iter_rows(named=True))[-3:]
        )
    )
    c2_med = weighted_median(c2["size_premium"].to_list(), c2["n_all"].cast(pl.Float64).to_list())
    el_med = weighted_median(el["size_premium"].to_list(), el["n_all"].cast(pl.Float64).to_list())
    print(
        "探索的（H6 の事前登録変数ではない。1.30 を目安に読む）: "
        f"control2 の加重中央値 {c2_med:.3f}"
        + (
            "（≥ 1.30）"
            if c2_med >= 1.30
            else ("（< 1.10）" if c2_med < 1.10 else "（1.10〜1.30）")
        )
        + f"、essential_low は {el_med:.3f}"
    )

    # figure: premium by section for OC2, DE/NL/PL/ES 2022 and ρ scatter
    args.figures.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    show = [g for g in ("DE", "NL", "ES", "PL", "CZ", "NO") if (g, 2022) in geos]
    for i, g in enumerate(show):
        prem = premium_table(ses, g, 2022, "OC2")
        xs = [s for s in SECTIONS if s in prem]
        ax.plot(
            xs,
            [prem[s] for s in xs],
            marker="o",
            color=SERIES[i % len(SERIES)],
            label=g,
            linewidth=1.2,
        )
    ax.axhline(1.0, color=MUTED, linestyle="--", linewidth=1)
    ax.axhline(1.3, color=MUTED, linestyle=":", linewidth=1)
    ax.set_title("専門職（ISCO 2）の時給 ÷ 専門職全体、産業別（SES 2022）", color=INK, fontsize=10)
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, ncol=3)
    ax = axes[1]
    pts_x: list[float] = []
    pts_y: list[float] = []
    all_x: list[float] = []
    all_y: list[float] = []
    for g, y in geos:
        prem = premium_table(ses, g, y, "OC2")
        va = value_added_by_section(nama, g, y)
        tot = nama.filter(
            (pl.col("geo") == g) & (pl.col("year") == y) & (pl.col("nace_r2") == "TOTAL")
        )
        if tot.height != 1 or tot["value_added_per_person_keur"][0] is None:
            continue
        base = float(tot["value_added_per_person_keur"][0])
        for s in SECTIONS:
            if s in prem and s in va:
                all_x.append(va[s] / base)
                all_y.append(prem[s])
                if s != "L":  # 不動産は帰属家賃で付加価値が極端（図と主結果は除く、含めた値も報告）
                    pts_x.append(va[s] / base)
                    pts_y.append(prem[s])
    ax.scatter(pts_x, pts_y, s=10, color=SERIES[0], alpha=0.5, edgecolor="none")
    ax.set_xscale("log")
    ax.set_xlabel("産業の 1 人当たり付加価値 ÷ 全産業（対数）", color=INK)
    ax.set_ylabel("専門職の時給 ÷ 専門職全体", color=INK)
    rho_all = spearman(list(zip(pts_x, pts_y, strict=True)))
    ax.set_title(
        f"全国 × 年 × 産業のプール（不動産を除く）: Spearman ρ = {rho_all:.2f}",
        color=INK,
        fontsize=10,
    )
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    for a in axes:
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(args.figures / "r2_h6_industry_premium.png", dpi=150)
    plt.close(fig)
    rho_incl = spearman(list(zip(all_x, all_y, strict=True)))
    print(
        f"\nプール全体の ρ（OC2）: 不動産を除く {rho_all:.3f}（{len(pts_x)} セル）、"
        f"不動産を含む {rho_incl:.3f}（{len(all_x)} セル）"
    )
    print(
        "図 1 左の 6 か国は、2022 年に値があり人口の大きい順に"
        "西欧 2（DE NL）・南欧 1（ES）・中東欧 2（PL CZ）・北欧 1（NO）を選んだ"
    )
    print("figures: r2_h6_industry_premium.png")


if __name__ == "__main__":
    main()
