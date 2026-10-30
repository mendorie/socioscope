"""R5: 経路を絞る事後追加の仮説 H7・H8・H9・H10（日本。設計書「事後追加の仮説（2026-10-30）」）。

結果を計算する前に設計書に固定した判定基準:
  H7  : 職種 × 年パネル（分類をまたがない）で、職種 FE・年 FE つきの
        Δ相対賃金 = β·Δ女性比率（＋Δ年齢・Δ勤続）。
        β ≤ −0.10 かつ 95% 上限 < 0 で整合、β ≥ 0 または
        （区間がゼロをまたぎ点推定 > −0.05）で不支持、間は中間。
        H7b: E=1 と E=0 で β を併記（差 < 0.05 なら「ケア特有でない」）。
        米国 ACS 4 年は参考値。
  H8  : 全職種で log 賃金 ~ 学歴・時間・勤続・女性比率 + L_capped + L_open。
        L_capped ≥ 0.20 かつ L_open < 0.10 で整合、L_open ≥ 0.20 で不支持、
        両方 < 0.10 で「免許は学歴で説明し尽くされる」。
  H9  : 介護 vs 対照の gap（2009→2019）のうち、年齢・勤続の構成効果を除いた
        残差の改善が ≥ 5.5 pt で整合、< 2 pt で不支持。
        (b) 年ごとの Δgap × Δlog 最低賃金 は記述。
  H10 : 区分 FE・年 FE つきの Δlog 賃金 = b·Δlog 求人倍率。
        b ≥ 0.02 かつ区間下限 > 0 で「変化には反応する」、|b| < 0.01 で反応しない、
        間は中間。

入力: data/marts/{bsws_occupation_wages, acs_occupation_earnings,
jobs_occupation_annual}.parquet と package 内の定義表・jp_jobs_category_map.csv・
jp_minimum_wage.csv。図: reports/figures/r5_*.png。決定的。
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
import numpy as np
import polars as pl
import statsmodels.api as sm

from theme_essential_work_wages.analysis.a20261030_r3_admin_price import (
    CONTROLS_NEW,
    CONTROLS_OLD,
    JOB_YEARS,
    TREAT_NEW,
    TREAT_OLD,
    category_ratios,
    category_wages,
    load_map,
)
from theme_essential_work_wages.analysis.common import (
    FIGURES,
    GRID,
    INK,
    MARTS,
    MUTED,
    PKG_DIR,
    SERIES,
    describe,
    load_flags,
    md_table,
    weighted_median,
    wls,
)

LOG = logging.getLogger("r5")


# ---- panel construction -----------------------------------------------------------------------


def jp_panel(bsws: pl.DataFrame) -> pl.DataFrame:
    """職種 × 年: 相対賃金（log 賃金 − その年の加重中央値の log）、女性比率、年齢、勤続、
    E、分類。"""
    base = bsws.filter(pl.col("size_class") == "all")
    t = base.filter(pl.col("sex") == "T").select(
        "year",
        "occupation",
        "classification",
        pl.col("scheduled_wage_thousand_yen").alias("wage"),
        pl.col("workers").cast(pl.Float64),
        "age",
        "tenure_years",
        "scheduled_hours",
    )
    f = base.filter(pl.col("sex") == "F").select(
        "year", "occupation", pl.col("workers").cast(pl.Float64).alias("wf")
    )
    m = base.filter(pl.col("sex") == "M").select(
        "year", "occupation", pl.col("scheduled_wage_thousand_yen").alias("wage_m")
    )
    d = (
        t.join(f, on=["year", "occupation"], how="left")
        .join(m, on=["year", "occupation"], how="left")
        .with_columns((pl.col("wf") / pl.col("workers")).alias("female_share"))
    )
    flags = pl.concat(
        [
            load_flags(c).select(
                "occupation",
                "classification",
                "essential",
                "licensed",
                "boundary",
                "education_years",
                "capacity_capped",
            )
            for c in ("jp_bsws2009", "jp_bsws2020")
        ]
    )
    d = d.join(flags, on=["occupation", "classification"], how="left").filter(
        pl.col("essential") >= 0
    )
    meds = []
    for y in sorted(d["year"].unique().to_list()):
        sub = d.filter(pl.col("year") == y)
        meds.append(
            {"year": y, "med": weighted_median(sub["wage"].to_list(), sub["workers"].to_list())}
        )
    d = d.join(pl.DataFrame(meds), on="year").with_columns(
        (pl.col("wage").log() - pl.col("med").log()).alias("rel"),
        (pl.col("wage_m").log() - pl.col("med").log()).alias("rel_male"),
        pl.col("wage").log().alias("log_wage"),
    )
    return d.filter(pl.col("female_share").is_not_null() & pl.col("wage").is_not_null())


def first_difference(d: pl.DataFrame, cols: list[str], key: str = "occupation") -> pl.DataFrame:
    """同じ分類の中で t−1 → t の差分（分類をまたがない）。"""
    prev = d.select(
        key,
        "classification",
        (pl.col("year") + 1).alias("year"),
        *[pl.col(c).alias(f"{c}_prev") for c in cols],
    )
    out = d.join(prev, on=[key, "classification", "year"], how="inner")
    return out.with_columns([(pl.col(c) - pl.col(f"{c}_prev")).alias(f"d_{c}") for c in cols])


def fe_regression(
    d: pl.DataFrame, y: str, xs: list[str], weight: str, group: str
) -> dict[str, tuple[float, float, float, float]]:
    """年 FE（ダミー）を入れた WLS。群クラスタ SE。差分に年 FE を入れれば職種 FE も吸収される。"""
    years = sorted(d["year"].unique().to_list())
    cols = [d[x].to_numpy().astype(float) for x in xs]
    cols += [(d["year"] == yv).cast(pl.Float64).to_numpy() for yv in years[1:]]
    x = sm.add_constant(np.column_stack(cols), has_constant="add")
    groups = d[group].rank("dense").to_numpy()
    res = sm.WLS(d[y].to_numpy().astype(float), x, weights=d[weight].to_numpy().astype(float)).fit(
        cov_type="cluster", cov_kwds={"groups": groups}
    )
    ci = np.asarray(res.conf_int())
    out = {
        n: (
            float(res.params[i + 1]),
            float(res.bse[i + 1]),
            float(ci[i + 1, 0]),
            float(ci[i + 1, 1]),
        )
        for i, n in enumerate(xs)
    }
    out["_n"] = (float(d.height), float(res.rsquared), math.nan, math.nan)
    return out


# ---- H7 --------------------------------------------------------------------------------------


def h7_verdict(coef: float, hi: float) -> str:
    if coef <= -0.10 and hi < 0:
        return "整合"
    if coef >= 0 or (hi >= 0 and coef > -0.05):
        return "不支持"
    return "中間"


def h7_block(d: pl.DataFrame) -> None:
    fd = first_difference(
        d.filter(pl.col("rel_male").is_not_null()),
        ["rel", "rel_male", "female_share", "age", "tenure_years"],
    )
    print(
        "\n### H7: 職種内の女性比率の変化と相対賃金の変化"
        "（日本、職種 FE・年 FE、職種クラスタ SE、労働者数加重）"
    )
    n_old = fd.filter(pl.col("classification") == "jp_bsws2009").height
    n_new = fd.filter(pl.col("classification") == "jp_bsws2020").height
    print(
        f"パネル: 職種 × 年の差分 {fd.height} 行"
        f"（旧分類 2010〜2019: {n_old}、新分類 2021〜2025: {n_new}）"
    )
    rows: list[list[object]] = []
    main = None
    for name, sub, xs in (
        ("全職種・女性比率のみ", fd, ["d_female_share"]),
        ("全職種・年齢・勤続を統制（主）", fd, ["d_female_share", "d_age", "d_tenure_years"]),
        ("E=1", fd.filter(pl.col("essential") == 1), ["d_female_share", "d_age", "d_tenure_years"]),
        ("E=0", fd.filter(pl.col("essential") == 0), ["d_female_share", "d_age", "d_tenure_years"]),
        (
            "旧分類のみ 2010〜2019",
            fd.filter(pl.col("classification") == "jp_bsws2009"),
            ["d_female_share", "d_age", "d_tenure_years"],
        ),
        (
            "新分類のみ 2021〜2025",
            fd.filter(pl.col("classification") == "jp_bsws2020"),
            ["d_female_share", "d_age", "d_tenure_years"],
        ),
        (
            "全職種・重みなし",
            fd.with_columns(pl.lit(1.0).alias("one")),
            ["d_female_share", "d_age", "d_tenure_years"],
        ),
        (
            "男性の賃金を結果に（職種内の性別構成の効果を除く）",
            fd,
            ["d_female_share", "d_age", "d_tenure_years"],
        ),
    ):
        w = "one" if name.endswith("重みなし") else "workers"
        yv = "d_rel_male" if name.startswith("男性") else "d_rel"
        reg = fe_regression(sub, yv, xs, w, "occupation")
        c, se, lo, hi = reg["d_female_share"]
        rows.append(
            [
                name,
                int(reg["_n"][0]),
                f"{c:+.3f} (SE {se:.3f}, {lo:+.3f}〜{hi:+.3f})",
                h7_verdict(c, hi),
            ]
        )
        if name.startswith("全職種・年齢・勤続を統制"):
            main = (c, hi)
        if name == "E=1":
            e1 = c
        if name == "E=0":
            e0 = c
    print(
        md_table(
            ["仕様", "n", "β（Δ女性比率、log 相対賃金）", "判定（≤−0.10 & 上限<0 整合）"], rows
        )
    )
    assert main is not None
    per_10pt = 100 * main[0] / 10
    print(
        f"**H7 判定（主仕様）: {h7_verdict(*main)}**"
        f"（β = {main[0]:+.3f}。+10 pt の女性化で相対賃金 {per_10pt:+.2f}%）"
    )
    if abs(e1 - e0) < 0.05:
        h7b = "ケア特有でない（差 < 0.05）"
    else:
        h7b = "E=1 で強い" if e1 < e0 else "E=0 で強い"
    print(f"H7b: E=1 {e1:+.3f} vs E=0 {e0:+.3f}、差 {e1 - e0:+.3f} → {h7b}")
    # 長期差分（分類内の始点→終点）
    print("\n長期差分（職種ごとの始点→終点、相対賃金の変化 vs 女性比率の変化）:")
    for cls, y0, y1 in (("jp_bsws2009", 2009, 2019), ("jp_bsws2020", 2020, 2025)):
        a = d.filter((pl.col("classification") == cls) & (pl.col("year") == y0)).select(
            "occupation", pl.col("rel").alias("r0"), pl.col("female_share").alias("f0"), "workers"
        )
        b = d.filter((pl.col("classification") == cls) & (pl.col("year") == y1)).select(
            "occupation", pl.col("rel").alias("r1"), pl.col("female_share").alias("f1")
        )
        ab = a.join(b, on="occupation").with_columns(
            (pl.col("r1") - pl.col("r0")).alias("dr"), (pl.col("f1") - pl.col("f0")).alias("df")
        )
        reg = wls(ab, "dr", ["df"], "workers")
        print(f"  {cls} {y0}→{y1}: n={ab.height}、β = {describe(reg, 'df')}")


# ---- H8 --------------------------------------------------------------------------------------


def h8_block(d: pl.DataFrame) -> None:
    print(
        "\n### H8: 免許の中身（養成定員の制限あり vs なし）、日本 2025 年、全職種"
        "（労働者数加重、HC1）"
    )
    x = d.filter(pl.col("year") == 2025).with_columns(
        ((pl.col("licensed") == 1) & (pl.col("capacity_capped") == 1))
        .cast(pl.Int64)
        .alias("l_capped"),
        ((pl.col("licensed") == 1) & (pl.col("capacity_capped") == 0))
        .cast(pl.Int64)
        .alias("l_open"),
    )
    rows: list[list[object]] = []
    res = {}
    for name, sub in (
        ("全職種", x),
        ("E=1 のみ", x.filter(pl.col("essential") == 1)),
        ("境界を除く", x.filter(pl.col("boundary") == 0)),
    ):
        reg = wls(
            sub,
            "log_wage",
            [
                "l_capped",
                "l_open",
                "education_years",
                "scheduled_hours",
                "tenure_years",
                "female_share",
            ],
            "workers",
        )
        res[name] = reg
        n_capped = sub.filter(pl.col("l_capped") == 1).height
        n_open = sub.filter(pl.col("l_open") == 1).height
        rows.append(
            [
                name,
                int(reg["_n"][0]),
                f"{n_capped} / {n_open}",
                describe(reg, "l_capped"),
                describe(reg, "l_open"),
                f"{reg['education_years'][0]:.3f}",
            ]
        )
    print(
        md_table(
            [
                "仕様",
                "n",
                "L_capped / L_open 職種数",
                "L_capped（log）",
                "L_open（log）",
                "学歴 1 年",
            ],
            rows,
        )
    )
    c_cap, c_open = res["全職種"]["l_capped"][0], res["全職種"]["l_open"][0]
    if c_cap >= 0.20 and c_open < 0.10:
        v = "整合（供給制限は定員制限の形でのみ賃金を分ける）"
    elif c_open >= 0.20:
        v = "不支持（免許一般が効く）"
    elif c_cap < 0.10 and c_open < 0.10:
        v = "免許は学歴で説明し尽くされる（H2 日本の不支持を補強）"
    else:
        v = "中間"
    print(f"**H8 判定（全職種）: {v}**（L_capped {c_cap:+.3f}、L_open {c_open:+.3f}）")
    capped = (
        x.filter(pl.col("l_capped") == 1)
        .select("occupation", "wage", "education_years")
        .sort("wage", descending=True)
    )
    print(
        "定員制限ありの職種: "
        + "; ".join(
            f"{r['occupation']} {r['wage']:.0f}（学歴 {r['education_years']} 年）"
            for r in capped.iter_rows(named=True)
        )
    )


# ---- H9 --------------------------------------------------------------------------------------


def h9_block(d: pl.DataFrame) -> None:
    print("\n### H9: 介護職の相対上昇（2009→2019）の源泉: 年齢・勤続の構成効果と最低賃金")
    old = d.filter(pl.col("classification") == "jp_bsws2009")
    # (a) 構成効果: 職種 FE + 年 FE + 年齢 + 勤続（レベル、加重）
    occs = sorted(old["occupation"].unique().to_list())
    years = sorted(old["year"].unique().to_list())
    cols = [old["age"].to_numpy().astype(float), old["tenure_years"].to_numpy().astype(float)]
    cols += [(old["year"] == y).cast(pl.Float64).to_numpy() for y in years[1:]]
    cols += [(old["occupation"] == o).cast(pl.Float64).to_numpy() for o in occs[1:]]
    xmat = sm.add_constant(np.column_stack(cols), has_constant="add")
    res = sm.WLS(old["log_wage"].to_numpy(), xmat, weights=old["workers"].to_numpy()).fit()
    b_age, b_ten = float(res.params[1]), float(res.params[2])
    print(
        f"log 賃金の職種 FE・年 FE 回帰（旧分類 2009〜2019、n={old.height}）: "
        f"年齢 1 歳 {b_age:+.4f}、勤続 1 年 {b_ten:+.4f}"
    )

    def comp(year: int, occs_: tuple[str, ...]) -> tuple[float, float, float]:
        sub = old.filter((pl.col("year") == year) & pl.col("occupation").is_in(list(occs_)))
        w = sub["workers"].to_numpy()
        return (
            float((w * sub["log_wage"].to_numpy()).sum() / w.sum()),
            float((w * sub["age"].to_numpy()).sum() / w.sum()),
            float((w * sub["tenure_years"].to_numpy()).sum() / w.sum()),
        )

    rows: list[list[object]] = []
    gaps = {}
    for y in (2009, 2019):
        lt, at, tt = comp(y, (TREAT_OLD,))
        lc, ac, tc = comp(y, CONTROLS_OLD)
        gap = lt - lc
        comp_pred = b_age * (at - ac) + b_ten * (tt - tc)
        gaps[y] = (gap, comp_pred, gap - comp_pred, at, tt, ac, tc)
        rows.append(
            [
                y,
                f"{at:.1f} / {tt:.1f}",
                f"{ac:.1f} / {tc:.1f}",
                f"{100 * gap:+.2f}",
                f"{100 * comp_pred:+.2f}",
                f"{100 * (gap - comp_pred):+.2f}",
            ]
        )
    print(
        md_table(
            [
                "年",
                "介護 年齢 / 勤続",
                "対照 年齢 / 勤続",
                "gap（log×100）",
                "構成が予測する gap",
                "構成調整後の gap",
            ],
            rows,
        )
    )
    raw_change = 100 * (gaps[2019][0] - gaps[2009][0])
    adj_change = 100 * (gaps[2019][2] - gaps[2009][2])
    comp_change = 100 * (gaps[2019][1] - gaps[2009][1])
    v = (
        "整合（構成では説明されない）"
        if adj_change >= 5.5
        else ("不支持（改善の大半は構成変化）" if adj_change < 2 else "中間")
    )
    print(
        f"gap の改善: 元 {raw_change:+.2f} pt、うち構成（年齢・勤続）が予測 {comp_change:+.2f} pt、"
        f"構成調整後 {adj_change:+.2f} pt → **H9 判定: {v}**"
    )
    # (b) minimum wage
    with (PKG_DIR / "jp_minimum_wage.csv").open(encoding="utf-8", newline="") as f:
        mw = {
            int(r["fiscal_year"]): float(r["national_weighted_avg_yen"]) for r in csv.DictReader(f)
        }
    ser = []
    for y in range(2011, 2020):  # 最低賃金の系列が 2009 年度からなので Δ は 2011 年から
        lt, _, _ = comp(y, (TREAT_OLD,))
        lc, _, _ = comp(y, CONTROLS_OLD)
        lt0, _, _ = comp(y - 1, (TREAT_OLD,))
        lc0, _, _ = comp(y - 1, CONTROLS_OLD)
        # 6 月調査なので前年 10 月発効の最低賃金（fiscal_year = y−1）が当年の水準
        ser.append(
            {
                "year": y,
                "d_gap": (lt - lc) - (lt0 - lc0),
                "d_mw": math.log(mw[y - 1]) - math.log(mw[y - 2]),
            }
        )
    sd = pl.DataFrame(ser)
    reg = wls(sd.with_columns(pl.lit(1.0).alias("one")), "d_gap", ["d_mw"], "one")
    rho = float(np.corrcoef(sd["d_gap"].to_numpy(), sd["d_mw"].to_numpy())[0, 1])
    mw_growth = 100 * math.log(901 / 713)
    print(
        f"(b) 年ごとの Δgap × Δlog 最低賃金（2011〜2019、n=9、記述）: "
        f"係数 {describe(reg, 'd_mw')}、相関 {rho:+.2f}。"
        f"最低賃金は 2009 年度 713 円 → 2019 年度 901 円（+{mw_growth:.1f}%）"
    )
    print(
        "  "
        + ", ".join(
            f"{r['year']}: Δgap {100 * r['d_gap']:+.1f} / Δmw {100 * r['d_mw']:+.1f}"
            for r in sd.iter_rows(named=True)
        )
    )
    # same for 2020-2025
    new = d.filter(pl.col("classification") == "jp_bsws2020")
    rows2: list[list[object]] = []
    for y in (2020, 2025):
        sub_t = new.filter((pl.col("year") == y) & (pl.col("occupation") == TREAT_NEW))
        sub_c = new.filter((pl.col("year") == y) & pl.col("occupation").is_in(list(CONTROLS_NEW)))
        w = sub_c["workers"].to_numpy()
        age_c = float((w * sub_c["age"].to_numpy()).sum() / w.sum())
        ten_c = float((w * sub_c["tenure_years"].to_numpy()).sum() / w.sum())
        rows2.append(
            [
                y,
                f"{float(sub_t['age'][0]):.1f} / {float(sub_t['tenure_years'][0]):.1f}",
                f"{age_c:.1f} / {ten_c:.1f}",
            ]
        )
    print(md_table(["年（新分類、参考）", "介護 年齢 / 勤続", "対照 年齢 / 勤続"], rows2))


# ---- H10 -------------------------------------------------------------------------------------


def h7_us_block(acs: pl.DataFrame) -> None:
    """設計 H7b の参考値: 米国 ACS 2021〜2024。

    職業 × 年の 1 年差分、年ダミー、職業クラスタ、就業者数加重。"""
    a = acs.filter(pl.col("occupation_code") != "0000").select(
        "year",
        pl.col("occupation_code").alias("occupation"),
        pl.lit("us_census_occ2018").alias("classification"),
        pl.col("earnings_median").alias("wage"),
        pl.col("workers").cast(pl.Float64),
        (pl.col("workers_female") / pl.col("workers")).alias("female_share"),
    )
    a = a.filter(pl.col("wage").is_not_null() & pl.col("female_share").is_not_null())
    meds = []
    for y in sorted(a["year"].unique().to_list()):
        sub = a.filter(pl.col("year") == y)
        meds.append(
            {"year": y, "med": weighted_median(sub["wage"].to_list(), sub["workers"].to_list())}
        )
    a = a.join(pl.DataFrame(meds), on="year").with_columns(
        (pl.col("wage").log() - pl.col("med").log()).alias("rel")
    )
    fd = first_difference(a, ["rel", "female_share"])
    reg = fe_regression(fd, "d_rel", ["d_female_share"], "workers", "occupation")
    c, se, lo, hi = reg["d_female_share"]
    print(
        f"\n参考（設計 H7b）: 米国 ACS 2021〜2024 の 1 年差分（n={fd.height}、年齢・勤続は無し）: "
        f"β = {c:+.3f} (SE {se:.3f}, {lo:+.3f}〜{hi:+.3f})。判定はしない（4 年、中央値年収）"
    )


def h10_block(bsws: pl.DataFrame, jobs: pl.DataFrame) -> None:
    print("\n### H10: 求人倍率の変化と賃金の変化（45 区分、区分 FE・年 FE、区分クラスタ SE、加重）")
    cmap = load_map()
    cw = category_wages(bsws, cmap)
    cr = category_ratios(jobs, cmap).filter(pl.col("n_months") >= 9)
    cls_of_year = {y: ("jp_bsws2009" if y < 2020 else "jp_bsws2020") for y in range(2009, 2026)}
    w = cw.join(cr.select("key", "year", "ratio"), on=["key", "year"], how="inner").with_columns(
        pl.col("wage").log().alias("lw"), pl.col("ratio").log().alias("lr")
    )
    w = w.with_columns(
        pl.Series("classification", [cls_of_year[int(y)] for y in w["year"].to_list()])
    )
    fd = first_difference(w, ["lw", "lr"], key="key").filter(pl.col("year").is_in(list(JOB_YEARS)))
    rows: list[list[object]] = []
    main = None
    for name, sub in (
        ("主（加重）", fd),
        ("重みなし", fd.with_columns(pl.lit(1.0).alias("one"))),
        ("1 年ラグ（Δlr_{t−1}）", None),
    ):
        if sub is None:
            lag = fd.select(
                "key", (pl.col("year") + 1).alias("year"), pl.col("d_lr").alias("d_lr_lag")
            )
            sub = fd.join(lag, on=["key", "year"], how="inner")
            reg = fe_regression(sub, "d_lw", ["d_lr_lag"], "workers", "key")
            c, se, lo, hi = reg["d_lr_lag"]
        else:
            reg = fe_regression(
                sub, "d_lw", ["d_lr"], "one" if name == "重みなし" else "workers", "key"
            )
            c, se, lo, hi = reg["d_lr"]
        if name.startswith("主"):
            main = (c, lo)
        rows.append([name, int(reg["_n"][0]), f"{c:+.4f} (SE {se:.4f}, {lo:+.4f}〜{hi:+.4f})"])
    print(md_table(["仕様", "n", "b（Δlog 求人倍率 → Δlog 賃金）"], rows))
    assert main is not None
    c, lo = main
    v = (
        "変化には反応する（R3 の解釈を修正）"
        if (c >= 0.02 and lo > 0)
        else ("反応しない（R3 と同じ）" if abs(c) < 0.01 else "中間")
    )
    print(f"**H10 判定: {v}**（b = {c:+.4f}）")


# ---- figure ----------------------------------------------------------------------------------


def fig(d: pl.DataFrame, path: Path) -> None:
    fig_, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    for i, (cls, y0, y1) in enumerate((("jp_bsws2009", 2009, 2019), ("jp_bsws2020", 2020, 2025))):
        a = d.filter((pl.col("classification") == cls) & (pl.col("year") == y0)).select(
            "occupation",
            pl.col("rel").alias("r0"),
            pl.col("female_share").alias("f0"),
            "workers",
            "essential",
        )
        b = d.filter((pl.col("classification") == cls) & (pl.col("year") == y1)).select(
            "occupation", pl.col("rel").alias("r1"), pl.col("female_share").alias("f1")
        )
        ab = a.join(b, on="occupation")
        ax.scatter(
            (ab["f1"] - ab["f0"]) * 100,
            (ab["r1"] - ab["r0"]) * 100,
            s=np.sqrt(ab["workers"].to_numpy()) / 25,
            color=SERIES[i],
            alpha=0.6,
            edgecolor="none",
            label=f"{y0}→{y1}（{'旧' if i == 0 else '新'}分類）",
        )
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_xlabel("女性比率の変化（pt）", color=INK)
    ax.set_ylabel("相対賃金の変化（log × 100）", color=INK)
    ax.set_title("H7: 職種内の女性化と相対賃金（点の大きさ = 労働者数）", color=INK, fontsize=10)
    ax.grid(color=GRID)
    ax.legend(frameon=False, fontsize=8)
    ax = axes[1]
    old = d.filter(pl.col("classification") == "jp_bsws2009")
    for occ, c, lab in (
        (TREAT_OLD, SERIES[0], "介護（福祉施設介護員）"),
        ("看護師", SERIES[1], "看護師"),
        ("保育士(保母・保父)", SERIES[2], "保育士"),
        ("警備員", SERIES[3], "警備員"),
        ("ビル清掃員", SERIES[4], "ビル清掃員"),
    ):
        s = old.filter(pl.col("occupation") == occ).sort("year")
        ax.plot(s["year"], s["age"], marker="o", color=c, label=lab, linewidth=1.2)
    ax.set_ylabel("平均年齢（歳）", color=INK)
    ax.set_title("H9: 平均年齢の推移（旧分類 2009〜2019）", color=INK, fontsize=10)
    ax.grid(color=GRID)
    ax.legend(frameon=False, fontsize=8)
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
    jobs = pl.read_parquet(args.marts / "jobs_occupation_annual.parquet")
    acs = pl.read_parquet(args.marts / "acs_occupation_earnings.parquet")
    print(
        "# R5 経路を絞る: H7 脱価値化・H8 定員制限・H9 介護の相対上昇の源泉・H10 変化どうし"
        "（日本、事後追加）"
    )
    d = jp_panel(bsws)
    h7_block(d)
    h7_us_block(acs)
    h8_block(d)
    h9_block(d)
    h10_block(bsws, jobs)
    args.figures.mkdir(parents=True, exist_ok=True)
    fig(d, args.figures / "r5_mechanisms.png")
    print("\nfigures: r5_mechanisms.png")


if __name__ == "__main__":
    main()
