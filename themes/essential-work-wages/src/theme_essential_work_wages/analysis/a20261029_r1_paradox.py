"""R1: 逆説は存在するか、必要性でなく免許・ジェンダー・随伴特性が賃金を分けるか。

対象仮説: H1・H1b・H2・H5・H0。

事前登録（design/themes/essential-work-wages.md、2026-10-29）:
  H1  : E=1 の雇用者数で重み付けした賃金中央値 ÷ 全職業の中央値 ≤ 0.90、かつ下位 4 分の 1 での
        過大代表 ≥ 1.5 倍。日本・米国（英国は未着手）で成立すれば整合。
  H1b : 2019→2024/25 で E=1 の賃金比が 2 pt 以上改善したか（記述）。
  H2  : E=1 の中で L=1 と L=0 の 学歴年数を統制した対数賃金差 ≥ 0.20 で整合、< 0.10 で不支持。
  H5  : E=1 の中で 女性比率 ≥ 70% vs ≤ 30% の統制後対数賃金差 ≤ −0.15 で整合、> −0.05 で不支持。
  H5b : 女性比率 +10pt の係数が E=1 と E=0 で同程度（差 < 0.02）か。
  H0  : log(賃金比) を E に回帰した係数 ≤ −0.10（逆説の再現）、L・P・T・F・学歴を入れると
        |β_E| < 0.05 で整合、≤ −0.10 のままなら不支持。

事後の具体化（結果を見る前に固定、2026-10-29 夜）:
  - 日本の賃金は 賃金構造基本統計調査 職種別の「所定内給与額」（月額、職種平均。中央値は
    公表されない）、一般労働者・企業規模計・男女計。「全職業の中央値」は職種平均の雇用者数加重中央値。
  - 米国は ACS 1 年推計の職業別 中央値年収（フルタイム通年）。
    E = cisa_sector × (teleworkable < 0.5)、teleworkable 欠損は cisa_sector のみで判定。
  - F（女性比率）は日本は同じ表の女性労働者数 ÷ 男女計（一般労働者のみ）、
    米国は ACS の女性就業者数 ÷ 総数。
  - 2020 年以降の「不詳」と、米国の Total 行は除く。頑健性: boundary=1 を除く、
    L の境界（低障壁の免許）を L=0 に。

決定的スクリプト。入力は data/marts/{bsws_occupation_wages, acs_occupation_earnings,
us_occupation_teleworkable}.parquet と package 内の定義表。図は reports/figures/r1_*.png。
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

from theme_essential_work_wages.analysis.common import (
    FIGURES,
    GRID,
    INK,
    MARTS,
    MUTED,
    PKG_DIR,
    SERIES,
    describe,
    group_ratio,
    load_flags,
    md_table,
    verdict,
    wls,
)

LOG = logging.getLogger("r1")
JP_LATEST = 2025
US_LATEST = 2024


# ---- data assembly (thin I/O wrappers around pure joins) --------------------------------------


def jp_frame(bsws: pl.DataFrame, year: int) -> pl.DataFrame:
    """One row per occupation for a year: wage (所定内給与, 千円), workers, female share, flags."""
    cls = "jp_bsws2020" if year >= 2020 else "jp_bsws2009"
    base = bsws.filter((pl.col("year") == year) & (pl.col("size_class") == "all"))
    t = base.filter(pl.col("sex") == "T").select(
        "occupation",
        pl.col("scheduled_wage_thousand_yen").alias("wage"),
        pl.col("annual_bonus_thousand_yen").alias("bonus"),
        pl.col("workers").cast(pl.Float64),
        "age",
        "tenure_years",
        "scheduled_hours",
    )
    f = base.filter(pl.col("sex") == "F").select(
        "occupation", pl.col("workers").cast(pl.Float64).alias("workers_f")
    )
    d = t.join(f, on="occupation", how="left").with_columns(
        (pl.col("workers_f") / pl.col("workers")).alias("female_share"),
        (pl.col("wage") * 12 + pl.col("bonus")).alias("annual_total"),
    )
    flags = load_flags(cls).select(
        "occupation",
        "essential",
        "licensed",
        "admin_price",
        "third_party",
        "boundary",
        "education_years",
        "group",
    )
    d = d.join(flags, on="occupation", how="left")
    missing = d.filter(pl.col("essential").is_null())["occupation"].to_list()
    if missing:
        msg = f"{year}: occupations without flags: {missing}"
        raise ValueError(msg)
    d = d.filter(pl.col("essential") >= 0)  # drop 不詳 (coded -1)
    return d.with_columns(pl.lit(year).alias("year"), pl.lit(cls).alias("classification"))


def us_frame(acs: pl.DataFrame, tele: pl.DataFrame, year: int) -> pl.DataFrame:
    base = acs.filter((pl.col("year") == year) & (pl.col("occupation_code") != "0000")).select(
        "occupation_code",
        "occupation",
        pl.col("earnings_median").alias("wage"),
        pl.col("workers").cast(pl.Float64),
        pl.col("workers_female").cast(pl.Float64).alias("workers_f"),
    )
    flags = load_flags("us_census_occ2018").select(
        "occupation_code",
        "cisa_sector",
        "licensed",
        "admin_price",
        "third_party",
        "boundary",
        "education_years",
        "group",
    )
    d = base.join(flags, on="occupation_code", how="left").join(
        tele.select("occupation_code", "teleworkable"), on="occupation_code", how="left"
    )
    missing = d.filter(pl.col("cisa_sector").is_null())["occupation"].to_list()
    if missing:
        msg = f"{year}: occupations without flags: {missing}"
        raise ValueError(msg)
    return d.with_columns(
        (pl.col("workers_f") / pl.col("workers")).alias("female_share"),
        pl.when(pl.col("teleworkable").is_null())
        .then(pl.col("cisa_sector"))
        .otherwise(((pl.col("cisa_sector") == 1) & (pl.col("teleworkable") < 0.5)).cast(pl.Int64))
        .alias("essential"),
        pl.lit(year).alias("year"),
        pl.lit("us_census_occ2018").alias("classification"),
    )


def with_derived(d: pl.DataFrame) -> pl.DataFrame:
    """log wage, log wage ratio to the employment-weighted median, strict L."""
    med = float(
        pl.Series(d["wage"]).to_list()[0]
        if d.height == 1
        else _wmed(d["wage"].to_list(), d["workers"].to_list())
    )
    return d.with_columns(
        (pl.col("wage").log() - math.log(med)).alias("log_ratio"),
        pl.col("wage").log().alias("log_wage"),
        ((pl.col("licensed") == 1) & (pl.col("boundary") == 0))
        .cast(pl.Int64)
        .alias("licensed_strict"),
        (pl.col("female_share") * 10).alias("female_share_10"),
    )


def _wmed(values: list[float], weights: list[float]) -> float:
    from theme_essential_work_wages.analysis.common import weighted_median

    return weighted_median(values, weights)


def add_census_female_share(d: pl.DataFrame, census: pl.DataFrame) -> pl.DataFrame:
    """女性比率の頑健性: 国勢調査 2020 職業（小分類）× 性の全就業者ベース。名称が一致する職種は
    そのまま、残りは jp_bsws2020_census_map.csv の対応で小分類を合算。対応が無い職種は None。"""
    import csv
    import re
    import unicodedata

    def norm(x: str) -> str:
        return unicodedata.normalize("NFKC", re.sub(r"[\s（）()・，,、]", "", x))

    minors = {
        norm(str(r["occupation"])): (float(r["workers_total"]), float(r["workers_female"]))
        for r in census.filter(pl.col("level") == "minor").iter_rows(named=True)
        if r["workers_total"] is not None and r["workers_female"] is not None
    }
    with (PKG_DIR / "jp_bsws2020_census_map.csv").open(encoding="utf-8", newline="") as f:
        cmap = {
            r["bsws_occupation"]: r["census_minor_occupations"].split(";")
            for r in csv.DictReader(f)
        }
    shares: list[float | None] = []
    n_direct = n_mapped = 0
    for occ in d["occupation"].to_list():
        key = norm(str(occ))
        if key in minors:
            t, fm = minors[key]
            n_direct += 1
        elif occ in cmap:
            parts = [minors[norm(m)] for m in cmap[occ] if norm(m) in minors]
            if not parts:  # 小分類が秘匿（None）のみの場合は欠損にする
                shares.append(None)
                continue
            t, fm = sum(x[0] for x in parts), sum(x[1] for x in parts)
            n_mapped += 1
        else:
            shares.append(None)
            continue
        shares.append(fm / t if t > 0 else None)
    LOG.info(
        "census female share: direct %d, mapped %d, missing %d",
        n_direct,
        n_mapped,
        len(shares) - n_direct - n_mapped,
    )
    return d.with_columns(pl.Series("female_share_census", shares, dtype=pl.Float64))


# ---- hypothesis blocks -----------------------------------------------------------------------


def h1_block(label: str, d: pl.DataFrame, wage: str = "wage") -> dict[str, float]:
    r = group_ratio(d, "essential", wage, "workers")
    r_nb = group_ratio(d.filter(pl.col("boundary") == 0), "essential", wage, "workers")
    print(f"\n### H1 {label}")
    print(
        md_table(
            ["指標", "全職業", "境界を除く"],
            [
                ["E=1 の賃金中央値 ÷ 全体（基準 ≤ 0.90）", r["median_ratio"], r_nb["median_ratio"]],
                ["E=1 の中央値", r["median_group"], r_nb["median_group"]],
                ["全体の中央値", r["median_all"], r_nb["median_all"]],
                ["全体の P25", r["p25_all"], r_nb["p25_all"]],
                ["E=1 の雇用者シェア（全体）", r["share_all"], r_nb["share_all"]],
                [
                    "E=1 の雇用者シェア（下位 4 分の 1）",
                    r["share_bottom_quartile"],
                    r_nb["share_bottom_quartile"],
                ],
                ["過大代表（基準 ≥ 1.5）", r["overrepresentation"], r_nb["overrepresentation"]],
                [
                    "職業数 E=1 / 全体",
                    f"{r['n_occupations']} / {r['n_all']}",
                    f"{r_nb['n_occupations']} / {r_nb['n_all']}",
                ],
            ],
        )
    )
    v1 = "満たす" if r["median_ratio"] <= 0.90 else "満たさない"
    v2 = "満たす" if r["overrepresentation"] >= 1.5 else "満たさない"
    print(f"判定: 賃金比 {v1}、過大代表 {v2} → {'整合' if v1 == v2 == '満たす' else '不支持'}")
    return r


def h2_block(label: str, d: pl.DataFrame) -> dict[str, float]:
    e = d.filter(pl.col("essential") == 1)
    out: dict[str, float] = {}
    print(f"\n### H2 {label}（E=1 の中で免許の有無）")
    rows = []
    for lcol, name in (
        ("licensed", "L（境界込み）"),
        ("licensed_strict", "L（低障壁の免許を除く）"),
    ):
        l1 = e.filter(pl.col(lcol) == 1)
        l0 = e.filter(pl.col(lcol) == 0)
        m1 = _wmed(l1["wage"].to_list(), l1["workers"].to_list())
        m0 = _wmed(l0["wage"].to_list(), l0["workers"].to_list())
        all_med = math.exp(-float(d["log_ratio"][0]) + math.log(float(d["wage"][0])))
        reg = wls(e, "log_wage", [lcol, "education_years"], "workers")
        raw = wls(e, "log_wage", [lcol], "workers")
        out[lcol] = reg[lcol][0]
        rows.append(
            [
                name,
                l1.height,
                l0.height,
                m1 / all_med,
                m0 / all_med,
                raw[lcol][0],
                describe(reg, lcol),
                reg["education_years"][0],
                verdict(reg[lcol][0], 0.20, 0.10, higher_is_ok=True),
            ]
        )
    print(
        md_table(
            [
                "定義",
                "L=1 職業数",
                "L=0 職業数",
                "L=1 中央値÷全体",
                "L=0 中央値÷全体",
                "粗差（log）",
                "学歴統制後の差（log）",
                "学歴 1 年の係数",
                "判定（≥0.20 整合 / <0.10 不支持）",
            ],
            rows,
        )
    )
    return out


def h5_block(
    label: str, d: pl.DataFrame, controls: list[str], fcol: str = "female_share"
) -> dict[str, float]:
    d = d.filter(pl.col(fcol).is_not_null()).with_columns((pl.col(fcol) * 10).alias("_f10"))
    e = d.filter(pl.col("essential") == 1)
    hi = e.filter(pl.col(fcol) >= 0.7)
    lo = e.filter(pl.col(fcol) <= 0.3)
    print(f"\n### H5 {label}（E=1 の中で女性比率）")
    out: dict[str, float] = {}
    if hi.height >= 3 and lo.height >= 3:
        mh = _wmed(hi["wage"].to_list(), hi["workers"].to_list())
        ml = _wmed(lo["wage"].to_list(), lo["workers"].to_list())
        print(
            f"女性 ≥70% の職業 {hi.height}（中央値 {mh:,.1f}）、"
            f"≤30% の職業 {lo.height}（中央値 {ml:,.1f}）、比 {mh / ml:.3f}"
        )
        hl = e.filter((pl.col(fcol) >= 0.7) | (pl.col(fcol) <= 0.3)).with_columns(
            (pl.col(fcol) >= 0.7).cast(pl.Int64).alias("fem_dom")
        )
        reg = wls(hl, "log_wage", ["fem_dom", *controls], "workers")
        out["fem_dom"] = reg["fem_dom"][0]
        print(
            f"統制（{', '.join(controls)}）後の差（log）: {describe(reg, 'fem_dom')} → "
            f"{verdict(reg['fem_dom'][0], -0.15, -0.05, higher_is_ok=False)}"
        )
    else:
        print(f"層が薄い（≥70%: {hi.height}、≤30%: {lo.height}）ので判定不能")
    # H5b: slope on female share in E=1 vs E=0
    rows = []
    for flag, name in ((1, "E=1"), (0, "E=0")):
        sub = d.filter(pl.col("essential") == flag)
        reg = wls(sub, "log_wage", ["_f10", *controls], "workers")
        out[f"slope_E{flag}"] = reg["_f10"][0]
        rows.append([name, sub.height, describe(reg, "_f10")])
    diff = out["slope_E1"] - out["slope_E0"]
    print(md_table(["群", "職業数", "女性比率 +10pt の係数（log 賃金、統制後）"], rows))
    print(
        f"H5b: 係数の差 E=1 − E=0 = {diff:+.3f} → "
        + (
            "同程度（差 < 0.02）"
            if abs(diff) < 0.02
            else ("E=1 で強い" if diff < 0 else "E=0 で強い")
        )
    )
    return out


def _zone(coef: float) -> str:
    if abs(coef) < 0.05:
        return "整合域"
    if coef <= -0.10:
        return "不支持域"
    return "中間帯"


def h0_block(label: str, d: pl.DataFrame, controls: list[str]) -> dict[str, float]:
    print(f"\n### H0 {label}（統合回帰、log 賃金比、雇用者数加重、HC1）")
    has_hours = "scheduled_hours" in controls
    specs = {
        "E のみ": ["essential"],
        "E + L + F + 学歴" + ("+時間+勤続" if has_hours else ""): [
            "essential",
            "licensed",
            "female_share",
            *controls,
        ],
        "+ P": ["essential", "licensed", "admin_price", "female_share", *controls],
        "+ T": ["essential", "licensed", "third_party", "female_share", *controls],
        "+ P + T": [
            "essential",
            "licensed",
            "admin_price",
            "third_party",
            "female_share",
            *controls,
        ],
        "+ P + T（境界を除く）": [
            "essential",
            "licensed",
            "admin_price",
            "third_party",
            "female_share",
            *controls,
        ],
    }
    rows: list[list[object]] = []
    out: dict[str, float] = {}
    for name, xs in specs.items():
        data = d.filter(pl.col("boundary") == 0) if "境界" in name else d
        p_eq_t = (
            "admin_price" in xs
            and "third_party" in xs
            and data.filter(pl.col("admin_price") != pl.col("third_party")).height == 0
        )
        reg = wls(data, "log_ratio", xs, "workers")
        out[name] = reg["essential"][0]
        cells: list[object] = [name, int(reg["_n"][0]), f"{reg['_n'][1]:.2f}"]
        for v in ("essential", "licensed", "admin_price", "third_party", "female_share"):
            if v in reg:
                cells.append(
                    describe(reg, v)
                    + (
                        "（P=T で識別不能）"
                        if p_eq_t and v in ("admin_price", "third_party")
                        else ""
                    )
                )
            else:
                cells.append("–")
        cells.append(_zone(reg["essential"][0]))
        rows.append(cells)
    print(md_table(["仕様", "n", "R²", "β_E", "β_L", "β_P", "β_T", "β_F", "β_E の帯"], rows))
    # sensitivity: unweighted and HC3 for the +P+T spec
    xs_full = specs["+ P + T"]
    unw = wls(d.with_columns(pl.lit(1.0).alias("_one")), "log_ratio", xs_full, "_one")
    hc3 = wls(d, "log_ratio", xs_full, "workers", cov_type="HC3")
    print(
        f"感度（+ P + T 仕様）: 重みなし β_E {describe(unw, 'essential')}"
        f"（{_zone(unw['essential'][0])}）、"
        f"HC3 β_E {describe(hc3, 'essential')}"
    )
    raw = out["E のみ"]
    zones = {k: _zone(v) for k, v in out.items() if k != "E のみ"}
    v_raw = "再現" if raw <= -0.10 else "逆説が弱い"
    n_ok = sum(z == "整合域" for z in zones.values())
    n_bad = sum(z == "不支持域" for z in zones.values())
    print(
        f"判定: E 単独 {raw:+.3f}（{v_raw}）。統制後の 5 仕様の帯: 整合域 {n_ok}、中間帯 "
        f"{len(zones) - n_ok - n_bad}、不支持域 {n_bad}。+ P + T {out['+ P + T']:+.3f}。"
        "→ 判定不能（点推定は仕様により整合域〜不支持域にまたがり、区間は両域にかかる。"
        "事前登録に ±0.05 と −0.10 の間の帯の扱いは無い）"
    )
    return out


def np_corr(d: pl.DataFrame) -> str:
    import numpy as np

    a = d["female_share"].to_numpy().astype(float)
    b = d["female_share_census"].to_numpy().astype(float)
    return f"{float(np.corrcoef(a, b)[0, 1]):.3f}（n={len(a)}）"


# ---- figures ---------------------------------------------------------------------------------


def fig_strip(jp: pl.DataFrame, us: pl.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharey=False)
    order = ["essential_low", "control1b", "control1", "control2", "control3", "reference"]
    labels = {
        "essential_low": "必要・免許なし",
        "control1b": "必要・免許・公定価格",
        "control1": "必要・免許",
        "control2": "資格なし高報酬群",
        "control3": "免許・非エッセンシャル",
        "reference": "その他（参照）",
    }
    for ax, (name, d) in zip(
        axes,
        (("日本 2025（所定内給与、千円/月）", jp), ("米国 2024（中央値年収、千ドル）", us)),
        strict=True,
    ):
        for i, g in enumerate(order):
            sub = d.filter(pl.col("group") == g)
            y = sub["wage"].to_numpy() / (1.0 if name.startswith("日本") else 1000.0)
            w = sub["workers"].to_numpy()
            s = 8 + 60 * (w / w.max()) if len(w) else []
            jitter = ((i * 3) % 7 - 3) / 40  # 決定的なずらし（hash は実行ごとに変わる）
            ax.scatter(
                [i + jitter] * len(y),
                y,
                s=s,
                color=SERIES[i % len(SERIES)],
                alpha=0.6,
                edgecolor="none",
            )
            if len(y):
                med = _wmed(list(sub["wage"].to_list()), list(sub["workers"].to_list())) / (
                    1.0 if name.startswith("日本") else 1000.0
                )
                ax.hlines(med, i - 0.3, i + 0.3, color=INK, linewidth=2)
        allmed = _wmed(d["wage"].to_list(), d["workers"].to_list()) / (
            1.0 if name.startswith("日本") else 1000.0
        )
        ax.axhline(allmed, color=MUTED, linestyle="--", linewidth=1)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels([labels[g] for g in order], rotation=25, ha="right", fontsize=9)
        ax.set_title(name, color=INK, fontsize=11)
        ax.grid(axis="y", color=GRID)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.suptitle(
        "職業別賃金の分布（点の大きさ＝雇用者数、横棒＝群の加重中央値、破線＝全体の加重中央値）",
        color=INK,
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig_timeseries(rows: list[tuple[str, int, float]], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, label in enumerate(sorted({r[0] for r in rows})):
        pts = sorted((y, v) for lbl, y, v in rows if lbl == label)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=SERIES[i], label=label)
    ax.axhline(0.9, color=MUTED, linestyle="--", linewidth=1)
    ax.set_ylabel("E=1 の賃金中央値 ÷ 全体", color=INK)
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(
        "H1b: エッセンシャル職の相対賃金の推移（破線 = 基準 0.90）", color=INK, fontsize=11
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---- main -------------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marts", type=Path, default=MARTS)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    plt.rcParams["font.family"] = ["IPAGothic", "IPAexGothic", "Noto Sans CJK JP", "DejaVu Sans"]

    bsws = pl.read_parquet(args.marts / "bsws_occupation_wages.parquet")
    acs = pl.read_parquet(args.marts / "acs_occupation_earnings.parquet")
    tele = pl.read_parquet(args.marts / "us_occupation_teleworkable.parquet")
    census = pl.read_parquet(args.marts / "jp_census2020_occupation_sex.parquet")

    jp = with_derived(jp_frame(bsws, JP_LATEST))
    us = with_derived(us_frame(acs, tele, US_LATEST))
    print("# R1 エッセンシャルワークの逆説: H1・H1b・H2・H5・H0（日本 2025・米国 2024）")
    print(
        f"日本: 職種 {jp.height}（E=1 {jp.filter(pl.col('essential') == 1).height}）、"
        f"雇用者 {jp['workers'].sum():,.0f} 人（一般労働者）"
    )
    print(
        f"米国: 職業 {us.height}（E=1 {us.filter(pl.col('essential') == 1).height}）、"
        f"就業者 {us['workers'].sum():,.0f} 人（フルタイム通年）"
    )
    print(
        "米国の E: cisa_sector=1 かつ teleworkable<0.5 ＝ "
        f"{us.filter((pl.col('cisa_sector') == 1) & (pl.col('teleworkable') < 0.5)).height}、"
        "cisa_sector=1 だが在宅可能で除外 = "
        f"{us.filter((pl.col('cisa_sector') == 1) & (pl.col('teleworkable') >= 0.5)).height}、"
        "teleworkable 欠損で cisa のみ = "
        f"{us.filter(pl.col('teleworkable').is_null() & (pl.col('cisa_sector') == 1)).height}"
    )
    excluded = us.filter((pl.col("cisa_sector") == 1) & (pl.col("teleworkable") >= 0.5)).sort(
        "workers", descending=True
    )
    print("在宅可能で E から外れた主な職業: " + ", ".join(excluded["occupation"].head(8).to_list()))

    # H1
    h1_jp = h1_block("日本 2025", jp)
    h1_block("日本 2025（年収＝所定内×12＋賞与）", jp, "annual_total")
    h1_us = h1_block("米国 2024", us)
    both = (
        h1_jp["median_ratio"] <= 0.90
        and h1_jp["overrepresentation"] >= 1.5
        and h1_us["median_ratio"] <= 0.90
        and h1_us["overrepresentation"] >= 1.5
    )
    print(f"\n**H1 総合判定（日本・米国）: {'整合' if both else '不支持または部分的'}**")

    # H1b time series
    ts: list[tuple[str, int, float]] = []
    for y in range(2009, 2020):
        ts.append(
            (
                "日本（旧分類 129 職種）",
                y,
                group_ratio(with_derived(jp_frame(bsws, y)), "essential", "wage", "workers")[
                    "median_ratio"
                ],
            )
        )
    for y in range(2020, JP_LATEST + 1):
        ts.append(
            (
                "日本（新分類 145 職種）",
                y,
                group_ratio(with_derived(jp_frame(bsws, y)), "essential", "wage", "workers")[
                    "median_ratio"
                ],
            )
        )
    for y in (2021, 2022, 2023, 2024):
        ts.append(
            (
                "米国（ACS 565 職業）",
                y,
                group_ratio(with_derived(us_frame(acs, tele, y)), "essential", "wage", "workers")[
                    "median_ratio"
                ],
            )
        )
    print("\n### H1b 相対賃金の推移")
    print(md_table(["系列", "年", "E=1 中央値 ÷ 全体"], [[a, b, c] for a, b, c in ts]))
    jp_old = {y: v for lbl, y, v in ts if "旧" in lbl}
    jp_new = {y: v for lbl, y, v in ts if "新" in lbl}
    us_ts = {y: v for lbl, y, v in ts if "米国" in lbl}
    print(
        f"日本 旧分類 2009→2019: {jp_old[2009]:.3f}→{jp_old[2019]:.3f}"
        f"（{100 * (jp_old[2019] - jp_old[2009]):+.1f} pt）、"
        f"新分類 2020→{JP_LATEST}: {jp_new[2020]:.3f}→{jp_new[JP_LATEST]:.3f}"
        f"（{100 * (jp_new[JP_LATEST] - jp_new[2020]):+.1f} pt）、"
        f"米国 2021→2024: {us_ts[2021]:.3f}→{us_ts[2024]:.3f}"
        f"（{100 * (us_ts[2024] - us_ts[2021]):+.1f} pt）"
    )
    print(
        "判定（改善 ≥ 2 pt で「可視化後に改善」）: "
        + ", ".join(
            f"{k}: {'改善' if v >= 0.02 else '改善なし'}"
            for k, v in (
                ("日本 2020→" + str(JP_LATEST), jp_new[JP_LATEST] - jp_new[2020]),
                ("米国 2021→2024", us_ts[2024] - us_ts[2021]),
            )
        )
    )

    # H2
    h2_jp = h2_block("日本 2025", jp)
    h2_us = h2_block("米国 2024", us)
    ok_jp = h2_jp["licensed"] >= 0.20
    ok_us = h2_us["licensed"] >= 0.20
    print(
        f"\n**H2 総合判定（事前規則: 2 か国中 2 か国で学歴統制後の差 ≥ 0.20）: "
        f"{'整合' if ok_jp and ok_us else '整合基準を満たさない'}**"
        f"（日本 {h2_jp['licensed']:+.3f}、米国 {h2_us['licensed']:+.3f}。国別は上表）"
    )
    # H5
    h5_block("日本 2025", jp, ["education_years", "scheduled_hours", "tenure_years"])
    h5_block("米国 2024", us, ["education_years"])
    jp_c = add_census_female_share(jp, census)
    h5_block(
        "日本 2025（頑健性: 女性比率 = 国勢調査 2020 の全就業者ベース）",
        jp_c,
        ["education_years", "scheduled_hours", "tenure_years"],
        fcol="female_share_census",
    )
    both_f = jp_c.filter(pl.col("female_share_census").is_not_null())
    print(f"女性比率の相関（一般労働者ベース vs 国勢調査）: r = {np_corr(both_f)}")
    # H0
    h0_block("日本 2025", jp, ["education_years", "scheduled_hours", "tenure_years"])
    h0_block("米国 2024", us, ["education_years"])

    # group table for the report
    print("\n### 群別の加重中央値（賃金比）")
    rows = []
    for g in ("essential_low", "control1b", "control1", "control2", "control3", "reference"):
        cells: list[object] = [g]
        for d in (jp, us):
            sub = d.filter(pl.col("group") == g)
            allmed = _wmed(d["wage"].to_list(), d["workers"].to_list())
            cells += [
                sub.height,
                _wmed(sub["wage"].to_list(), sub["workers"].to_list()) / allmed
                if sub.height
                else math.nan,
            ]
        rows.append(cells)
    print(
        md_table(["群", "日本 職種数", "日本 中央値÷全体", "米国 職業数", "米国 中央値÷全体"], rows)
    )

    args.figures.mkdir(parents=True, exist_ok=True)
    fig_strip(jp, us, args.figures / "r1_h1_groups.png")
    fig_timeseries(ts, args.figures / "r1_h1b_timeseries.png")
    print("\nfigures: r1_h1_groups.png, r1_h1b_timeseries.png")


if __name__ == "__main__":
    main()
