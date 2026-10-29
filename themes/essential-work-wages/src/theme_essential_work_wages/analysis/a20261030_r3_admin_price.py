"""R3: 公定価格は人手不足の価格シグナルを遮断するか（H3・H3b、日本）。

事前登録（design/themes/essential-work-wages.md、2026-10-29）:
  H3  : 職業別有効求人倍率と職業別賃金の年次変化率を回帰すると、P=1 の職業（介護・保育・看護）の
        残差は負で、13 年のうち 9 年以上で回帰線より下（≈ 69%）なら整合、5 年以下なら不支持。
        介護職の有効求人倍率は全職業の上位 10% に入り続けている。
  H3b : 介護職員処遇改善の改定（2009-10 交付金、2012-04 加算、2015-04 拡充、2017-04 加算 I、
        2019-10 特定加算、2022-02/10 補助金→加算、2024-06 一本化）の前後で、介護職の所定内給与の
        変化を対照職業（販売店員・警備員・ビル清掃員・調理）と差分の差分で比べる。
        改定の翌調査年の相対上昇 ≥ 2% が 5 回中 4 回以上、かつ改定の無い年の相対変化の中央値が
        ±1% 以内なら整合。改定年と非改定年で差が無ければ不支持。非改定年にも上がっていれば中間。

事後の具体化（結果を見る前に固定、2026-10-30）:
  - 単位は職業安定業務統計の職業中分類（`jp_jobs_category_map.csv` の 45 区分）。各区分の賃金は、
    区分に属する賃金構造基本統計調査の職種の 所定内給与額（企業規模計・男女計）の労働者数加重平均。
    求人倍率は「パート除く常用」の暦年平均（原数値、季節調整なし）。
  - 求人統計は 2020-04〜2022-03 が公開されていないため、使える年は 2013〜2019・2022〜2025
    （2012・2020 は月数不足、2021 は欠落）。賃金変化率は賃金構造基本統計調査の t−1→t で、
    2020 年の分類改定をまたぐ 2019→2020 は使わない。H3 の判定は「使える年の 69% 以上」
    （11 年なら 8 年以上）で回帰線より下、5 年以下（45% 以下）で不支持、と事前基準を
    比例で読み替える。
  - 回帰: Δlog(賃金)_t = a_t + b·log(求人倍率)_t + ε（年固定効果、区分の労働者数で加重）。
    P=1 区分（care_service, nurses, social_welfare_prof）の残差を年ごとに見る。
  - 改定が「翌調査年」に効く対応: 2009-10→2010、2012-04→2012、2015-04→2015、2017-04→2017、
    2019-10→2020、2022-02/10→2022、2024-06→2024（賃金構造基本統計調査は 6 月分の所定内給与）。
    2019→2020 は職種名が 福祉施設介護員 → 介護職員（医療・福祉施設等）、対照も旧→新に変わるので
    注記付きで使う。処置群は 介護職員（医療・福祉施設等）／福祉施設介護員、対照は 4 職業の
    労働者数加重平均。「相対変化」= Δlog(介護) − Δlog(対照)。

決定的スクリプト。入力は data/marts/{bsws_occupation_wages, jobs_occupation_annual}.parquet と
package 内の jp_jobs_category_map.csv・jp_care_policy_events.csv。図は reports/figures/r3_*.png。
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from pathlib import Path
from typing import cast

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
import statsmodels.api as sm

from theme_essential_work_wages.analysis.common import (
    FIGURES,
    GRID,
    INK,
    MARTS,
    MUTED,
    PKG_DIR,
    SERIES,
    as_float,
    md_table,
)

LOG = logging.getLogger("r3")
ADMIN_KEYS = ("care_service", "nurses", "social_welfare_prof")
TREAT_NEW = "介護職員（医療・福祉施設等）"
TREAT_OLD = "福祉施設介護員"
CONTROLS_NEW = ("販売店員", "警備員", "ビル・建物清掃員", "飲食物調理従事者")
CONTROLS_OLD = ("販売店員(百貨店店員を除く。)", "警備員", "ビル清掃員", "調理士")
EVENT_YEARS = {
    2010: "2009-10 交付金",
    2012: "2012-04 加算",
    2015: "2015-04 拡充",
    2017: "2017-04 加算 I",
    2020: "2019-10 特定加算",
    2022: "2022-02/10 補助金→加算",
    2024: "2024-06 一本化",
}
JOB_YEARS = (2013, 2014, 2015, 2016, 2017, 2018, 2019, 2022, 2023, 2024, 2025)


# ---- pure helpers ---------------------------------------------------------------------------


def load_map() -> list[dict[str, object]]:
    with (PKG_DIR / "jp_jobs_category_map.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        out.append(
            {
                "key": r["key"],
                "name_mhlw2011": r["name_mhlw2011"],
                "name_jsoc2009": r["name_jsoc2009"],
                "admin_price": int(r["admin_price"]),
                "bsws2020": [x for x in r["bsws2020"].split(";") if x],
                "bsws2009": [x for x in r["bsws2009"].split(";") if x],
            }
        )
    return out


def category_wages(bsws: pl.DataFrame, cmap: list[dict[str, object]]) -> pl.DataFrame:
    """(key, year) -> workers-weighted mean scheduled wage of member occupations, workers."""
    b = bsws.filter((pl.col("sex") == "T") & (pl.col("size_class") == "all")).select(
        "year", "occupation", "scheduled_wage_thousand_yen", "workers"
    )
    rows = []
    for m in cmap:
        for year in sorted(b["year"].unique().to_list()):
            members = cast("list[str]", m["bsws2020"] if year >= 2020 else m["bsws2009"])
            if not members:
                continue
            sub = b.filter((pl.col("year") == year) & pl.col("occupation").is_in(list(members)))
            sub = sub.filter(
                pl.col("scheduled_wage_thousand_yen").is_not_null() & (pl.col("workers") > 0)
            )
            if sub.height == 0:
                continue
            w = sub["workers"].cast(pl.Float64).to_numpy()
            x = sub["scheduled_wage_thousand_yen"].to_numpy()
            rows.append(
                {
                    "key": m["key"],
                    "year": year,
                    "wage": float((w * x).sum() / w.sum()),
                    "workers": float(w.sum()),
                    "n_members": sub.height,
                    "admin_price": m["admin_price"],
                }
            )
    return pl.DataFrame(rows)


def category_ratios(jobs: pl.DataFrame, cmap: list[dict[str, object]]) -> pl.DataFrame:
    j = jobs.filter(pl.col("employment_type") == "regular_excl_parttime")
    rows = []
    for m in cmap:
        for cls, name in (("jp_mhlw2011", m["name_mhlw2011"]), ("jp_jsoc2009", m["name_jsoc2009"])):
            sub = j.filter((pl.col("classification") == cls) & (pl.col("occupation") == name))
            for r in sub.iter_rows(named=True):
                rows.append(
                    {
                        "key": m["key"],
                        "year": int(r["year"]),
                        "ratio": float(r["openings_to_seekers_mean"]),
                        "n_months": int(r["n_months"]),
                    }
                )
    return pl.DataFrame(rows)


def panel(cw: pl.DataFrame, cr: pl.DataFrame) -> pl.DataFrame:
    """Δlog wage (t-1→t, same classification) joined with log ratio_t."""
    w = cw.sort("key", "year")
    prev = w.select("key", (pl.col("year") + 1).alias("year"), pl.col("wage").alias("wage_prev"))
    d = w.join(prev, on=["key", "year"], how="inner").with_columns(
        (pl.col("wage").log() - pl.col("wage_prev").log()).alias("dlog_wage")
    )
    d = d.filter(pl.col("year") != 2020)  # classification break 2019→2020
    d = d.join(cr.select("key", "year", "ratio", "n_months"), on=["key", "year"], how="inner")
    d = d.filter(pl.col("year").is_in(list(JOB_YEARS)) & (pl.col("ratio") > 0))
    return d.with_columns(pl.col("ratio").log().alias("log_ratio"))


def residuals_with_year_fe(d: pl.DataFrame) -> tuple[pl.DataFrame, float, float]:
    years = sorted(d["year"].unique().to_list())
    x_cols = [d["log_ratio"].to_numpy()]
    for y in years[1:]:
        x_cols.append((d["year"] == y).cast(pl.Float64).to_numpy())
    x = sm.add_constant(np.column_stack(x_cols), has_constant="add")
    res = sm.WLS(d["dlog_wage"].to_numpy(), x, weights=d["workers"].to_numpy()).fit(cov_type="HC1")
    b, se = float(res.params[1]), float(res.bse[1])
    return d.with_columns(pl.Series("resid", np.asarray(res.resid))), b, se


def did_series(bsws: pl.DataFrame) -> pl.DataFrame:
    """year -> treated wage, control wage (weighted), with old/new names across the 2020 break."""
    b = bsws.filter((pl.col("sex") == "T") & (pl.col("size_class") == "all"))
    rows = []
    for year in sorted(b["year"].unique().to_list()):
        treat = TREAT_NEW if year >= 2020 else TREAT_OLD
        ctrls = CONTROLS_NEW if year >= 2020 else CONTROLS_OLD
        sub = b.filter(pl.col("year") == year)
        t = sub.filter(pl.col("occupation") == treat)
        c = sub.filter(pl.col("occupation").is_in(list(ctrls)))
        if t.height != 1 or c.height != len(ctrls):
            msg = f"{year}: treated {t.height}, controls {c.height}"
            raise ValueError(msg)
        w = c["workers"].cast(pl.Float64).to_numpy()
        rows.append(
            {
                "year": year,
                "treated_wage": float(t["scheduled_wage_thousand_yen"][0]),
                "treated_cash": float(t["monthly_cash_thousand_yen"][0]),
                "control_wage": float(
                    (w * c["scheduled_wage_thousand_yen"].to_numpy()).sum() / w.sum()
                ),
                "control_cash": float(
                    (w * c["monthly_cash_thousand_yen"].to_numpy()).sum() / w.sum()
                ),
                "treated_workers": float(t["workers"][0]),
            }
        )
    d = pl.DataFrame(rows).sort("year")
    return d.with_columns(
        (pl.col("treated_wage").log() - pl.col("control_wage").log()).alias("gap"),
        (pl.col("treated_cash").log() - pl.col("control_cash").log()).alias("gap_cash"),
    ).with_columns(
        (pl.col("gap") - pl.col("gap").shift(1)).alias("rel_change"),
        (pl.col("gap_cash") - pl.col("gap_cash").shift(1)).alias("rel_change_cash"),
    )


# ---- main -----------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marts", type=Path, default=MARTS)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    plt.rcParams["font.family"] = ["IPAGothic", "IPAexGothic", "Noto Sans CJK JP", "DejaVu Sans"]

    bsws = pl.read_parquet(args.marts / "bsws_occupation_wages.parquet")
    jobs = pl.read_parquet(args.marts / "jobs_occupation_annual.parquet")
    cmap = load_map()
    cw = category_wages(bsws, cmap)
    cr = category_ratios(jobs, cmap)
    d = panel(cw, cr)
    print("# R3 公定価格は人手不足の価格シグナルを遮断するか（H3・H3b、日本）")
    print(
        f"区分 {cw['key'].n_unique()}、パネル行 {d.height}"
        f"（年 {sorted(d['year'].unique().to_list())}）"
    )

    # ---- H3: rank of care in shortage
    print("\n### H3 前段: 介護の有効求人倍率の順位（パート除く常用、暦年平均）")
    rows: list[list[object]] = []
    top_decile_years = 0
    for y in JOB_YEARS:
        sub = cr.filter((pl.col("year") == y) & (pl.col("n_months") >= 9)).sort(
            "ratio", descending=True
        )
        n = sub.height
        rank = next(
            (i + 1 for i, r in enumerate(sub.iter_rows(named=True)) if r["key"] == "care_service"),
            None,
        )
        care = sub.filter(pl.col("key") == "care_service")["ratio"]
        allr = cr.filter((pl.col("year") == y) & (pl.col("key") == "nurses"))["ratio"]
        in_top = rank is not None and rank <= math.ceil(n / 10)
        top_decile_years += int(in_top)
        rows.append(
            [
                y,
                n,
                rank,
                f"{care[0]:.2f}" if care.len() else "–",
                f"{allr[0]:.2f}" if allr.len() else "–",
                "上位 10%" if in_top else "",
            ]
        )
    print(md_table(["年", "区分数", "介護の順位", "介護 倍率", "看護 倍率", ""], rows))
    print(f"介護が上位 10% に入った年: {top_decile_years} / {len(JOB_YEARS)}")

    # ---- H3: regression and residuals
    dr, b, se = residuals_with_year_fe(d)
    print(
        "\n### H3: Δlog(所定内給与) = 年固定効果 + b·log(有効求人倍率)（労働者数加重、HC1）: "
        f"b = {b:+.4f} (SE {se:.4f})"
    )
    rows = []
    neg_years = {k: 0 for k in ADMIN_KEYS}
    n_years = {k: 0 for k in ADMIN_KEYS}
    for y in sorted(dr["year"].unique().to_list()):
        cells: list[object] = [y]
        for k in ADMIN_KEYS:
            r = dr.filter((pl.col("year") == y) & (pl.col("key") == k))
            if r.height:
                rv = float(r["resid"][0])
                n_years[k] += 1
                neg_years[k] += int(rv < 0)
                cells.append(f"{rv:+.3f}")
            else:
                cells.append("–")
        rows.append(cells)
    print(md_table(["年", "介護 残差", "看護 残差", "社会福祉専門職（保育士等） 残差"], rows))
    verdicts = []
    for k in ADMIN_KEYS:
        n, neg = n_years[k], neg_years[k]
        share = neg / n if n else math.nan
        v = "整合" if share >= 9 / 13 else ("不支持" if share <= 5 / 13 else "中間")
        verdicts.append(f"{k}: 負の年 {neg}/{n}（{share:.2f}）→ {v}")
    print("判定（負の年の割合 ≥ 0.69 整合 / ≤ 0.38 不支持）: " + "; ".join(verdicts))
    pooled = dr.filter(pl.col("key").is_in(list(ADMIN_KEYS)))
    pooled_mean = as_float(pooled["resid"].mean())
    pooled_neg = as_float((pooled["resid"] < 0).mean())
    other_mean = as_float(dr.filter(~pl.col("key").is_in(list(ADMIN_KEYS)))["resid"].mean())
    print(
        f"P=1 区分のプール残差: 平均 {pooled_mean:+.4f}、負の割合 {pooled_neg:.2f}"
        f"（n={pooled.height}）。"
        f"P=0 区分: 平均 {other_mean:+.4f}"
    )
    # level view: ratio vs cumulative wage growth 2013->2019 and 2022->2025
    print("\n### H3 補助: 期間内の累積賃金変化と平均求人倍率（区分別）")
    rows = []
    for key in sorted(cw["key"].unique().to_list()):
        cells = [key]
        for lo, hi in ((2013, 2019), (2022, 2025)):
            w0 = cw.filter((pl.col("key") == key) & (pl.col("year") == lo))["wage"]
            w1 = cw.filter((pl.col("key") == key) & (pl.col("year") == hi))["wage"]
            rr = cr.filter(
                (pl.col("key") == key) & (pl.col("year") >= lo) & (pl.col("year") <= hi)
            )["ratio"]
            cells += [
                f"{100 * (math.log(w1[0]) - math.log(w0[0])):+.1f}%"
                if w0.len() and w1.len()
                else "–",
                f"{as_float(rr.mean()):.2f}" if rr.len() else "–",
            ]
        rows.append(cells)
    print(md_table(["区分", "Δ 2013→2019", "倍率 2013–19", "Δ 2022→2025", "倍率 2022–25"], rows))

    # ---- H3b DID
    ds = did_series(bsws)
    print("\n### H3b: 介護職 vs 対照 4 職業（所定内給与、log 差分の差分）")
    rows = []
    event_hits = 0
    non_event: list[float] = []
    for row in ds.iter_rows(named=True):
        y = int(row["year"])
        rc = row["rel_change"]
        if rc is None:
            rows.append(
                [y, row["treated_wage"], row["control_wage"], f"{row['gap']:+.3f}", "–", "–", ""]
            )
            continue
        tag = EVENT_YEARS.get(y, "")
        if tag:
            event_hits += int(rc >= 0.02)
        else:
            non_event.append(rc)
        rows.append(
            [
                y,
                row["treated_wage"],
                row["control_wage"],
                f"{row['gap']:+.3f}",
                f"{100 * rc:+.2f}%",
                f"{100 * row['rel_change_cash']:+.2f}%",
                tag + ("（分類改定をまたぐ）" if y == 2020 else ""),
            ]
        )
    print(
        md_table(
            [
                "年",
                "介護 所定内",
                "対照 所定内",
                "gap（log）",
                "相対変化 所定内",
                "相対変化 きまって支給",
                "改定",
            ],
            rows,
        )
    )
    non_event_med = float(np.median(non_event)) if non_event else math.nan
    n_events = len(EVENT_YEARS)
    v = (
        "整合"
        if event_hits >= 4 and abs(non_event_med) <= 0.01
        else (
            "中間（改定年も非改定年も上がっている）"
            if event_hits >= 4
            else ("不支持" if event_hits <= 2 else "中間")
        )
    )
    print(
        f"判定: 改定の翌調査年に相対上昇 ≥ 2% だった回数 {event_hits}/{n_events}（基準 4 以上）、"
        f"非改定年の相対変化の中央値 {100 * non_event_med:+.2f}%（基準 ±1%）→ {v}"
    )
    gap0, gap1 = (
        float(ds.filter(pl.col("year") == 2009)["gap"][0]),
        float(ds.filter(pl.col("year") == 2025)["gap"][0]),
    )
    gap19 = float(ds.filter(pl.col("year") == 2019)["gap"][0])
    print(f"介護職の対照比（log gap）: 2009 {gap0:+.3f} → 2019 {gap19:+.3f} → 2025 {gap1:+.3f}")

    # ---- figures
    args.figures.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    other = dr.filter(~pl.col("key").is_in(list(ADMIN_KEYS)))
    ax.scatter(
        other["log_ratio"],
        other["dlog_wage"] * 100,
        s=np.sqrt(other["workers"].to_numpy()) / 40,
        color=MUTED,
        alpha=0.5,
        edgecolor="none",
        label="その他の区分",
    )
    for i, k in enumerate(ADMIN_KEYS):
        sub = dr.filter(pl.col("key") == k)
        ax.scatter(
            sub["log_ratio"],
            sub["dlog_wage"] * 100,
            s=np.sqrt(sub["workers"].to_numpy()) / 40,
            color=SERIES[i],
            alpha=0.9,
            edgecolor="none",
            label={
                "care_service": "介護",
                "nurses": "看護",
                "social_welfare_prof": "社会福祉専門職",
            }[k],
        )
    ax.set_xlabel("log 有効求人倍率（暦年平均）", color=INK)
    ax.set_ylabel("所定内給与の前年比（%）", color=INK)
    ax.set_title(f"H3: 人手不足と賃金変化（区分 × 年、b = {b:+.3f}）", color=INK, fontsize=10)
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8)
    ax = axes[1]
    ax.plot(ds["year"], ds["gap"] * 100, marker="o", color=SERIES[0])
    for y in EVENT_YEARS:
        ax.axvline(y - 0.5, color=SERIES[1], linestyle=":", linewidth=1)
    ax.axvline(2019.5, color=MUTED, linestyle="--", linewidth=1)
    ax.set_ylabel("log(介護 ÷ 対照) × 100", color=INK)
    ax.set_title(
        "H3b: 介護職の所定内給与の対照比（点線 = 処遇改善の改定、破線 = 分類改定）",
        color=INK,
        fontsize=10,
    )
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    for a in axes:
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(args.figures / "r3_h3_shortage_wage.png", dpi=150)
    plt.close(fig)
    print("\nfigures: r3_h3_shortage_wage.png")


if __name__ == "__main__":
    main()
