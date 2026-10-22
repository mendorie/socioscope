"""R9: 三産業の対比（H6）— 実用層と趣味層の分化は自転車・自動車・二輪で同形か。

事前登録（design/themes/bicycle-industry.md、H6。変数の具体化は 2026-10-22 の事後記録）:
  前段: 2022 → 2025 の台数変化率を 実用層 と 趣味層 で並べ、三産業とも 実用層 ≥ 趣味層 なら
    「同形」。自動車: 実用 = 軽四輪 新車販売（全軽自協）、趣味 = 輸入乗用車 500 万円以上（JAIA）。
    二輪: 実用 = 原付一種（生産動態統計 販売）、趣味 = 小型二輪 251cc〜 新車販売（全軽自協）。
    自転車: 実用 = 電動アシスト車（JBPI 国内生産）、趣味 = スポーツ車・外装変速機付軽快車
    （JBPI 輸入）。
  後段: 2021 → 2024 の産業全体の変化率が自転車で最小（下落率が最大）なら整合。
    自動車 = 登録車（自販連）＋ 軽四輪、二輪 = 軽二輪＋小型二輪（全軽自協）＋ 原付一・二種
    （生産動態統計）、自転車 = JBPI 国内向 合計。
  記述: 軽比率（軽 ÷ (登録車＋軽)）、輸入車の 500 万円以上比率、長期推移。

決定的スクリプト。入力は data/marts/{jp_kei_moto_sales, jp_registered_car_sales,
jp_import_car_price_bands, jp_bicycle_by_type, meti_production}.parquet。

純粋ヘルパ（change, judge_same_shape, judge_deepest, high_band_units）は
tests/test_analysis_r9.py で検証する。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_bicycle_industry.analysis.a20261022_r1_volume_price import (
    INK,
    MUTED,
    SERIES,
    _style,
    meti_annual,
)

THEME_DIR = Path(__file__).resolve().parents[3]
BOOM, POST = 2022, 2025
DEEP_A, DEEP_B = 2021, 2024
HIGH_BANDS = ("ge_2000", "1000_1999", "900_999", "800_899", "700_799", "600_699", "500_599")


# ---- pure helpers -------------------------------------------------------------------------------


def change(series: Mapping[int, float], a: int, b: int) -> float:
    if a not in series or b not in series or series[a] == 0:
        return math.nan
    return series[b] / series[a] - 1


def judge_same_shape(pairs: Mapping[str, tuple[float, float]]) -> str:
    """各産業の (実用層, 趣味層) の変化率。全産業で 実用 ≥ 趣味 なら整合、1 つでも逆なら不支持。"""
    if any(math.isnan(u) or math.isnan(h) for u, h in pairs.values()):
        return "判定不能"
    return "整合" if all(u >= h for u, h in pairs.values()) else "不支持"


def judge_deepest(changes: Mapping[str, float], target: str = "自転車") -> str:
    """産業全体の変化率が target で最小（最も負）なら整合。"""
    if any(math.isnan(v) for v in changes.values()) or target not in changes:
        return "判定不能"
    return "整合" if changes[target] == min(changes.values()) else "不支持"


def high_band_units(bands: Mapping[tuple[int, str], float], year: int) -> float:
    vals = [bands.get((year, b)) for b in HIGH_BANDS]
    if any(v is None for v in vals):
        return math.nan
    return sum(v for v in vals if v is not None)


# ---- loaders -------------------------------------------------------------------------------------


def seg(m: pl.DataFrame, segment: str) -> dict[int, float]:
    sub = m.filter(pl.col("segment") == segment)
    return {int(r["year"]): float(r["units"]) for r in sub.iter_rows(named=True)}


def jbpi_series(m: pl.DataFrame, category: str, flow: str) -> dict[int, float]:
    sub = m.filter((pl.col("category") == category) & (pl.col("flow") == flow))
    return {int(r["year"]): float(r["qty"]) for r in sub.iter_rows(named=True)}


# ---- figure --------------------------------------------------------------------------------------


def fig_pairs(
    data: Mapping[str, tuple[int, Mapping[str, Mapping[int, float]]]], path: Path, source: str
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharey=False)
    for ax, (industry, (base, pair)) in zip(axes, data.items(), strict=True):
        for (name, s), color in zip(pair.items(), SERIES, strict=False):
            xs = [x for x in sorted(s) if x >= base]
            b = s.get(base)
            if not b:
                continue
            ys = [s[x] / b * 100 for x in xs]
            ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=3, label=name)
            ax.annotate(
                f"{ys[-1]:.0f}",
                (xs[-1], ys[-1]),
                textcoords="offset points",
                xytext=(4, -3),
                fontsize=7.5,
                color=INK,
            )
        ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
        ax.axvspan(2020.5, 2022.5, color="#f2f2f2", zorder=0, label="特需期 2021–22")
        ax.set_title(industry, fontsize=9.5, color=INK, loc="left")
        ax.legend(fontsize=7, frameon=False, loc="lower left" if base == 2021 else "upper left")
        ax.set_ylabel(f"{base} = 100", fontsize=8, color=INK)
        _style(ax)
    fig.text(0.01, 0.01, f"出典: {source}", fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    import logging

    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]
    marts = args.data_dir / "marts"
    kei = pl.read_parquet(marts / "jp_kei_moto_sales.parquet")
    reg = pl.read_parquet(marts / "jp_registered_car_sales.parquet")
    imp = pl.read_parquet(marts / "jp_import_car_price_bands.parquet")
    jb = pl.read_parquet(marts / "jp_bicycle_by_type.parquet")
    meti = pl.read_parquet(marts / "meti_production.parquet")

    kei4 = seg(kei, "kei4_total")
    moto250 = seg(kei, "moto_126_250")
    moto_gt = seg(kei, "moto_gt250")
    reg_total = seg(reg, "registered_total")
    bands = {(int(r["year"]), str(r["band"])): float(r["units"]) for r in imp.iter_rows(named=True)}
    imp_total = {y: v for (y, b), v in bands.items() if b == "total"}
    imp_high = {y: high_band_units(bands, y) for y in imp_total}
    gentsuki1 = meti_annual(meti, "moto_le50", "sales_qty")
    gentsuki2 = meti_annual(meti, "moto_51_125", "sales_qty")
    eassist = jbpi_series(jb, "eassist", "production")
    sports = jbpi_series(jb, "other_sports_geared", "import")
    bike_total = {
        y: jbpi_series(jb, "total", "production")[y]
        + sum(
            jbpi_series(jb, c, "import")[y]
            for c in ("light", "mtb_cross", "mini", "infant", "kids", "other_sports_geared")
        )
        for y in jbpi_series(jb, "total", "production")
    }
    auto_total = {y: reg_total[y] + kei4[y] for y in reg_total if y in kei4}
    moto_total = {
        y: moto250[y] + moto_gt[y] + gentsuki1[y] + gentsuki2[y]
        for y in moto_gt
        if y in gentsuki1 and y in gentsuki2
    }

    print("# R9 三産業の対比（H6）（2026-10-22）")
    print(
        f"- mart: jp_kei_moto_sales {kei.height} 行、jp_registered_car_sales {reg.height} 行、"
        f"jp_import_car_price_bands {imp.height} 行、jp_bicycle_by_type {jb.height} 行、"
        "meti_production（原付）"
    )
    print(f"\n## H6 前段: {BOOM} → {POST} の台数変化率（実用層 vs 趣味層）")
    pairs = {
        "自動車": (change(kei4, BOOM, POST), change(imp_high, BOOM, POST)),
        "二輪": (change(gentsuki1, BOOM, POST), change(moto_gt, BOOM, POST)),
        "自転車": (change(eassist, BOOM, POST), change(sports, BOOM, POST)),
    }
    labels = {
        "自動車": ("軽四輪 新車販売", "輸入乗用車 500 万円以上"),
        "二輪": ("原付一種（生産動態統計 販売）", "小型二輪 251cc〜 新車販売"),
        "自転車": ("電動アシスト車（国内生産）", "スポーツ車・外装変速機付軽快車（輸入）"),
    }
    print("| 産業 | 実用層 | 変化率 | 趣味層 | 変化率 | 実用 ≥ 趣味 |")
    print("|---|---|---|---|---|---|")
    for ind, (u, h) in pairs.items():
        ok = "はい" if u >= h else "いいえ"
        print(f"| {ind} | {labels[ind][0]} | {u:+.1%} | {labels[ind][1]} | {h:+.1%} | {ok} |")
    print(f"- 判定（三産業とも 実用 ≥ 趣味 で同形）: **{judge_same_shape(pairs)}**")

    print(f"\n## H6 後段: {DEEP_A} → {DEEP_B} の産業全体の変化率（自転車が最小なら整合）")
    deep = {
        "自動車": change(auto_total, DEEP_A, DEEP_B),
        "二輪": change(moto_total, DEEP_A, DEEP_B),
        "自転車": change(bike_total, DEEP_A, DEEP_B),
    }
    for ind, v in deep.items():
        print(f"- {ind}: {v:+.1%}")
    print(f"- 判定: **{judge_deepest(deep)}**")

    print("\n## 記述: 各系列の水準（台）")
    years = [2015, 2019, 2021, 2022, 2023, 2024, 2025]
    series = {
        "軽四輪 新車販売": kei4,
        "登録車 新車登録": reg_total,
        "輸入乗用車 計": imp_total,
        "輸入乗用車 500 万円以上": imp_high,
        "原付一種（販売）": gentsuki1,
        "原付二種（販売）": gentsuki2,
        "軽二輪 126–250cc": moto250,
        "小型二輪 251cc〜": moto_gt,
        "電動アシスト車": eassist,
        "スポーツ車・外装変速機付軽快車": sports,
        "自転車 国内向 合計": bike_total,
    }
    print("| 系列 | " + " | ".join(str(y) for y in years) + " |")
    print("|---|" + "---|" * len(years))
    for name, s in series.items():
        print(f"| {name} | " + " | ".join(f"{s[y]:,.0f}" if y in s else "–" for y in years) + " |")
    print("\n### 比率（記述）")
    for y in (2015, 2019, 2022, 2025):
        hi = imp_high[y] / imp_total[y]
        if y in reg_total:
            tot = kei4[y] + reg_total[y]
            print(
                f"- {y}: 軽比率 {kei4[y] / tot:.1%}、輸入乗用車の 500 万円以上比率 {hi:.1%}、"
                f"輸入乗用車 ÷ (登録車＋軽) {imp_total[y] / tot:.1%}"
            )
        else:
            print(f"- {y}: 輸入乗用車の 500 万円以上比率 {hi:.1%}（登録車の年計は 2021 年から）")
    print(
        "- 2015 → 2025（2015 = 100）: "
        + "、".join(
            f"{n} {s[2025] / s[2015] * 100:.0f}"
            for n, s in series.items()
            if 2015 in s and 2025 in s
        )
    )

    print("\n## 頑健性")
    for a, b in ((2021, 2025), (2023, 2025), (2019, 2025)):
        p2 = {
            "自動車": (change(kei4, a, b), change(imp_high, a, b)),
            "二輪": (change(gentsuki1, a, b), change(moto_gt, a, b)),
            "自転車": (change(eassist, a, b), change(sports, a, b)),
        }

        def pct(v: float) -> str:
            return "–" if math.isnan(v) else f"{v:+.1%}"

        txt = "、".join(f"{k} {pct(u)} vs {pct(h)}" for k, (u, h) in p2.items())
        print(f"- 前段 期間 {a} → {b}: {txt} → {judge_same_shape(p2)}")
    alt = {
        "自動車": (
            change(kei4, BOOM, POST),
            change(
                {y: bands[(y, "ge_2000")] + bands[(y, "1000_1999")] for y in imp_total}, BOOM, POST
            ),
        ),
        "二輪": (change(gentsuki1, BOOM, POST), change(moto_gt, BOOM, POST)),
        "自転車": (change(eassist, BOOM, POST), change(sports, BOOM, POST)),
    }
    a0, a1 = alt["自動車"]
    ja = judge_same_shape(alt)
    print(f"- 前段 趣味層を輸入車 1,000 万円以上に: 自動車 {a0:+.1%} vs {a1:+.1%} → {ja}")
    alt2 = dict(pairs)
    alt2["自転車"] = (
        change(eassist, BOOM, POST),
        change(jbpi_series(jb, "mtb_cross", "import"), BOOM, POST),
    )
    b0, b1 = alt2["自転車"]
    print(
        f"- 前段 自転車の趣味層を MTB・クロスに: {b0:+.1%} vs {b1:+.1%} → {judge_same_shape(alt2)}"
    )
    alt3 = dict(pairs)
    alt3["二輪"] = (change(gentsuki2, BOOM, POST), change(moto_gt, BOOM, POST))
    c0, c1 = alt3["二輪"]
    print(f"- 前段 二輪の実用層を原付二種に: {c0:+.1%} vs {c1:+.1%} → {judge_same_shape(alt3)}")
    for a, b in ((2022, 2025), (2021, 2025), (2019, 2024)):
        d2 = {
            "自動車": change(auto_total, a, b),
            "二輪": change(moto_total, a, b),
            "自転車": change(bike_total, a, b),
        }
        if any(math.isnan(v) for v in d2.values()):
            print(f"- 後段 期間 {a} → {b}: 判定不能（登録車の年計が 2021 年から）")
            continue
        print(
            f"- 後段 期間 {a} → {b}: "
            + "、".join(f"{k} {v:+.1%}" for k, v in d2.items())
            + f" → {judge_deepest(d2)}"
        )
    moto_alt = {y: moto250[y] + moto_gt[y] for y in moto_gt}
    d3 = {
        "自動車": deep["自動車"],
        "二輪（軽二輪＋小型二輪のみ）": change(moto_alt, DEEP_A, DEEP_B),
        "自転車": deep["自転車"],
    }
    m_alt = d3["二輪（軽二輪＋小型二輪のみ）"]
    print(f"- 後段 二輪を協会統計のみ（原付を除く）に: 二輪 {m_alt:+.1%} → {judge_deepest(d3)}")

    fig_pairs(
        {
            "自動車（2015 = 100）": (2015, {"軽四輪": kei4, "輸入車 500 万円以上": imp_high}),
            "二輪（2019 = 100）": (2019, {"原付一種": gentsuki1, "小型二輪 251cc〜": moto_gt}),
            "自転車（2021 = 100）": (
                2021,
                {"電動アシスト": eassist, "スポーツ車・外装変速機付軽快車": sports},
            ),
        },
        args.fig_dir / "r9_pairs.png",
        "全軽自協・JAIA・経産省 生産動態統計・JBPI",
    )
    print(f"\nfigures: {args.fig_dir / 'r9_pairs.png'}")


if __name__ == "__main__":
    main()
