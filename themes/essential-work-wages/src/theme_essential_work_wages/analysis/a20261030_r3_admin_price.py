"""R3: 公定価格は人手不足の価格シグナルを遮断するか（H3・H3b、日本）。

事前登録（design/themes/essential-work-wages.md、2026-10-29）:
  H3  : 職業別有効求人倍率と職業別賃金の年次変化率を回帰すると、P=1 の職業（介護・保育・看護）の
        残差は負で、13 年のうち 9 年以上で回帰線より下（≈ 69%）なら整合、5 年以下なら不支持。
        介護職の有効求人倍率は全職業の上位 10% に入り続けている。
  H3b : 介護職員処遇改善の改定（事前登録は 5 回: 2009-10 交付金、2012-04 加算、
        2019-10 特定加算、2022-10 ベースアップ加算、2024-06 一本化。
        2015-04 拡充・2017-04 加算 I は事後追加）の前後で、
        介護職の所定内給与の
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
from typing import TypedDict, cast

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
# 事前登録の 5 改定（設計書 H3b）を「翌調査年」（6 月分賃金）に対応させたもの。
# 2022-10 は 2023 年調査、2024-06-01 施行は 2024 年調査
# （同月。効果が出るには早いので 2025 年も併記）
EVENTS_PRE = {
    2010: "2009-10 交付金",
    2012: "2012-04 加算",
    2020: "2019-10 特定加算",
    2023: "2022-10 ベースアップ加算",
    2024: "2024-06 一本化",
}
# 事後の代替対応: 2022-02 の補助金（月 9,000 円）が 2022 年 6 月調査に入るとみなす
EVENTS_PRE_ALT = {
    2010: "2009-10 交付金",
    2012: "2012-04 加算",
    2020: "2019-10 特定加算",
    2022: "2022-02 補助金",
    2024: "2024-06 一本化",
}
# 事後追加（2015-04 拡充、2017-04 加算 I を加えた 7 回。設計には無い）
EVENTS_ALL = {**EVENTS_PRE_ALT, 2015: "2015-04 拡充", 2017: "2017-04 加算 I"}
EVENT_YEARS = EVENTS_ALL  # 表示用のタグ
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


class H3bResult(TypedDict):
    hits: int
    n_events: int
    event_median: float
    event_values: list[float]
    non_event_median: float
    non_event_values: list[float]
    skipped: list[str]
    verdict: str


def h3b_judge(ds: pl.DataFrame, events: dict[int, str], col: str = "rel_change") -> H3bResult:
    """事前登録の規則: 改定の翌調査年の相対上昇 ≥ 2% が 4 回以上 かつ
    非改定年の中央値が ±1% 以内 → 整合。
    「改定年と非改定年で差が無い」（事後の操作化: 中央値の差 < 0.5 pt）→ 不支持。それ以外 → 中間。
    2019→2020 は分類改定をまたぐので改定年の計数から除き、別に示す。"""
    ev: list[float] = []
    non: list[float] = []
    hits = 0
    skipped: list[str] = []
    for row in ds.iter_rows(named=True):
        y, rc = int(row["year"]), row[col]
        if rc is None:
            continue
        if y in events:
            if y == 2020:
                skipped.append(f"2020（{100 * rc:+.1f}%、分類改定をまたぐため除外）")
                continue
            ev.append(float(rc))
            hits += int(rc >= 0.02)
        else:
            non.append(float(rc))
    ev_med = float(np.median(ev)) if ev else math.nan
    non_med = float(np.median(non)) if non else math.nan
    n_ev = len(ev)
    if hits >= 4 and abs(non_med) <= 0.01:
        v = "整合"
    elif abs(ev_med - non_med) < 0.005:
        v = "不支持（改定年と非改定年で差が無い）"
    else:
        v = "中間（改定年の上昇は 2% 未満だが非改定年より大きい）" if ev_med > non_med else "中間"
    return {
        "hits": hits,
        "n_events": n_ev,
        "event_median": ev_med,
        "event_values": ev,
        "non_event_median": non_med,
        "non_event_values": non,
        "skipped": skipped,
        "verdict": v,
    }


def event_study(
    ds: pl.DataFrame, events: dict[int, str], col: str = "rel_change"
) -> list[tuple[int, float, int]]:
    """改定年 k=0 の前後 2 年の相対変化の平均（事前登録のイベントスタディ図用）。"""
    by_year = {int(r["year"]): r[col] for r in ds.iter_rows(named=True) if r[col] is not None}
    out = []
    for k in range(-2, 3):
        vals = [by_year[y + k] for y in events if (y + k) in by_year and (y + k) != 2020]
        out.append((k, float(np.mean(vals)) if vals else math.nan, len(vals)))
    return out


def did_series_controls(
    bsws: pl.DataFrame, new: tuple[str, ...], old: tuple[str, ...]
) -> pl.DataFrame:
    """対照職業を差し替えた did_series（頑健性: 賃金水準が介護に最も近い 2 職業）。"""
    b = bsws.filter((pl.col("sex") == "T") & (pl.col("size_class") == "all"))
    rows = []
    for year in sorted(b["year"].unique().to_list()):
        treat = TREAT_NEW if year >= 2020 else TREAT_OLD
        ctrls = new if year >= 2020 else old
        sub = b.filter(pl.col("year") == year)
        t = sub.filter(pl.col("occupation") == treat)
        c = sub.filter(pl.col("occupation").is_in(list(ctrls)))
        w = c["workers"].cast(pl.Float64).to_numpy()
        rows.append(
            {
                "year": year,
                "gap": math.log(float(t["scheduled_wage_thousand_yen"][0]))
                - math.log(
                    float((w * c["scheduled_wage_thousand_yen"].to_numpy()).sum() / w.sum())
                ),
            }
        )
    d = pl.DataFrame(rows).sort("year")
    return d.with_columns((pl.col("gap") - pl.col("gap").shift(1)).alias("rel_change"))


def regression_variants(d: pl.DataFrame) -> list[tuple[str, float, float]]:
    """b の感度: 年固定効果 + HC1（主）、年固定効果 + 区分クラスタ、
    固定効果なし + クラスタ、重みなし。"""
    years = sorted(d["year"].unique().to_list())
    x_fe = [d["log_ratio"].to_numpy()] + [
        (d["year"] == y).cast(pl.Float64).to_numpy() for y in years[1:]
    ]
    x_nofe = [d["log_ratio"].to_numpy()]
    groups = d["key"].rank("dense").to_numpy()
    y = d["dlog_wage"].to_numpy()
    w = d["workers"].to_numpy()
    out = []
    for name, cols, weights, kw in (
        ("年 FE・HC1（主）", x_fe, w, {"cov_type": "HC1"}),
        ("年 FE・区分クラスタ", x_fe, w, {"cov_type": "cluster", "cov_kwds": {"groups": groups}}),
        (
            "FE なし・区分クラスタ",
            x_nofe,
            w,
            {"cov_type": "cluster", "cov_kwds": {"groups": groups}},
        ),
        (
            "年 FE・重みなし・クラスタ",
            x_fe,
            np.ones_like(w),
            {"cov_type": "cluster", "cov_kwds": {"groups": groups}},
        ),
    ):
        x = sm.add_constant(np.column_stack(cols), has_constant="add")
        res = sm.WLS(y, x, weights=weights).fit(**kw)
        out.append((name, float(res.params[1]), float(res.bse[1])))
    return out


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
    print("\n### H3: 傾き b の感度")
    print(
        md_table(
            ["仕様", "b", "SE"],
            [[n, f"{bb:+.4f}", f"{ss:.4f}"] for n, bb, ss in regression_variants(d)],
        )
    )
    print(
        "\n### H3: 区分の間で、人手不足と賃金変化に関係があるか。"
        "Δlog(所定内給与) = 年固定効果 + b·log(有効求人倍率)（労働者数加重、HC1）: "
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
    for row in ds.iter_rows(named=True):
        y = int(row["year"])
        rc = row["rel_change"]
        if rc is None:
            rows.append(
                [y, row["treated_wage"], row["control_wage"], f"{row['gap']:+.3f}", "–", "–", ""]
            )
            continue
        tag = EVENT_YEARS.get(y, "")
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
    print("\n#### H3b の判定（事前登録の規則。改定年 = 改定の翌調査年）")
    rows = []
    results = {}
    for name, events in (
        ("事前登録 5 回（2022-10 → 2023 年調査）", EVENTS_PRE),
        ("事前登録 5 回・代替対応（2022-02 補助金 → 2022 年調査）", EVENTS_PRE_ALT),
        ("事後追加 7 回（2015・2017 を加える）", EVENTS_ALL),
    ):
        j = h3b_judge(ds, events)
        results[name] = j
        rows.append(
            [
                name,
                f"{j['hits']}/{j['n_events']}",
                f"{100 * j['event_median']:+.2f}%",
                " ".join(f"{100 * x:+.1f}" for x in j["event_values"]),
                f"{100 * j['non_event_median']:+.2f}%",
                j["verdict"],
            ]
        )
    print(
        md_table(
            [
                "改定の数え方",
                "翌年 ≥ +2% の回数",
                "改定年の中央値",
                "改定年の値（%）",
                "非改定年の中央値",
                "判定",
            ],
            rows,
        )
    )
    j0 = results["事前登録 5 回（2022-10 → 2023 年調査）"]
    print(
        f"除外: {'; '.join(j0['skipped'])}。非改定年の値（%）: "
        + " ".join(f"{100 * x:+.1f}" for x in j0["non_event_values"])
    )
    print(f"**H3b 判定（事前登録 5 回）: {j0['verdict']}**")
    jc = h3b_judge(ds, EVENTS_PRE, col="rel_change_cash")
    print(
        f"きまって支給する現金給与で: 翌年 ≥ +2% {jc['hits']}/{jc['n_events']}、"
        f"改定年の中央値 {100 * jc['event_median']:+.2f}%、"
        f"非改定年 {100 * jc['non_event_median']:+.2f}% → {jc['verdict']}"
    )
    # event study (pre-registered figure)
    print("\n#### イベントスタディ（改定年 k=0 の前後 2 年、相対変化の平均、2020 を除く）")
    for name, events in (("事前登録 5 回", EVENTS_PRE), ("事後追加 7 回", EVENTS_ALL)):
        es = event_study(ds, events)
        print(name + ": " + ", ".join(f"k={k:+d} {100 * m:+.2f}% (n={n})" for k, m, n in es))
    # robustness: controls closest in wage level to care in 2009
    # (pre-registered: 最低賃金比率の近い対照)
    b2009 = bsws.filter(
        (pl.col("year") == 2009) & (pl.col("sex") == "T") & (pl.col("size_class") == "all")
    )
    care0 = float(b2009.filter(pl.col("occupation") == TREAT_OLD)["scheduled_wage_thousand_yen"][0])
    dist = sorted(
        (
            abs(
                float(b2009.filter(pl.col("occupation") == o)["scheduled_wage_thousand_yen"][0])
                - care0
            ),
            i,
        )
        for i, o in enumerate(CONTROLS_OLD)
    )
    pick = [dist[0][1], dist[1][1]]
    ctrl_old2 = tuple(CONTROLS_OLD[i] for i in pick)
    ctrl_new2 = tuple(CONTROLS_NEW[i] for i in pick)
    ds2 = did_series_controls(bsws, ctrl_new2, ctrl_old2)
    j2 = h3b_judge(ds2, EVENTS_PRE)
    ctrl_old2_label = "・".join(ctrl_old2)
    ctrl_new2_label = "・".join(ctrl_new2)
    print(
        f"\n#### 頑健性: 2009 年の所定内給与が介護（{care0:.0f} 千円）に最も近い 2 職業を対照に"
        f"（{ctrl_old2_label} → {ctrl_new2_label}）"
    )
    gap2_2009 = float(ds2.filter(pl.col("year") == 2009)["gap"][0])
    gap2_2019 = float(ds2.filter(pl.col("year") == 2019)["gap"][0])
    gap2_2025 = float(ds2.filter(pl.col("year") == 2025)["gap"][0])
    print(
        f"翌年 ≥ +2% {j2['hits']}/{j2['n_events']}、"
        f"改定年の中央値 {100 * j2['event_median']:+.2f}%、"
        f"非改定年 {100 * j2['non_event_median']:+.2f}% → {j2['verdict']}。"
        f" gap: 2009 {gap2_2009:+.3f} → 2019 {gap2_2019:+.3f} → 2025 {gap2_2025:+.3f}"
    )
    print(
        "最低賃金近傍比率の職業別データは無いため、賃金水準の近さで代替した（事後の具体化）。"
        "並行トレンドの事前期間は無い（改定が 2009 年から連続）ため検証できない。"
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
