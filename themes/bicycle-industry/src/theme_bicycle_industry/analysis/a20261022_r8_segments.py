"""R8: 日本のセグメント分離（H2）— 電動アシスト車 vs スポーツ車の台数と単価。

事前登録（design/themes/bicycle-industry.md、H2。変数の具体化は 2026-10-22 の事後記録を参照）:
  H2: 電動アシスト車の台数はコロナ後も減らず単価は上がる一方、スポーツ車は台数・単価ともに下がる。
      判定: 2022 → 2025 の台数変化率が 電動アシスト ≥ 0 かつ スポーツ < −10% なら整合。
      どちらかを満たさなければ不支持。
      電動アシスト = 生産動態統計の電動アシスト車（国内生産）。スポーツ車 = 主判定「その他
      （スポーツ車・外装変速機付軽快車、輸入）」、副判定「マウンテンバイク（MTB・クロスバイク、輸入）」。
      単価 = 金額 ÷ 台数（記述）。局面: 特需期 2021–2022、特需後 2023–2025。
  補助（記述）: POS 販売統計（2024-07–2025-12、小売・税込）の車種別 台数・金額・平均単価、
      2025 年 7–9 月・10–12 月の前年同期比。

決定的スクリプト。入力は data/marts/{jp_bicycle_by_type, jp_pos_sales}.parquet。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/\\
        a20261022_r8_segments.py [--data-dir data] [--fig-dir …]

純粋ヘルパ（change, judge_h2, quarter_sum）は tests/test_analysis_r8.py で検証する。
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
)

THEME_DIR = Path(__file__).resolve().parents[3]
BOOM, POST = 2022, 2025
LABELS: dict[tuple[str, str], str] = {
    ("eassist", "production"): "電動アシスト車（国内生産）",
    ("other_sports_geared", "import"): "スポーツ車・外装変速機付軽快車（輸入）",
    ("mtb_cross", "import"): "MTB・クロスバイク（輸入）",
    ("light", "import"): "軽快車（輸入）",
    ("kids", "import"): "子供車（輸入）",
    ("mini", "import"): "ミニサイクル（輸入）",
}


# ---- pure helpers -------------------------------------------------------------------------------


def change(series: Mapping[int, float], a: int, b: int) -> float:
    if a not in series or b not in series or series[a] == 0:
        return math.nan
    return series[b] / series[a] - 1


def judge_h2(eassist_change: float, sports_change: float) -> str:
    """電動 ≥ 0 かつ スポーツ < −10% で整合。どちらかを欠けば不支持。欠損は判定不能。"""
    if math.isnan(eassist_change) or math.isnan(sports_change):
        return "判定不能"
    return "整合" if eassist_change >= 0 and sports_change < -0.10 else "不支持"


def quarter_sum(monthly: Mapping[str, float], year: int, months: Sequence[int]) -> float:
    keys = [f"{year}-{m:02d}" for m in months]
    if any(k not in monthly for k in keys):
        return math.nan
    return sum(monthly[k] for k in keys)


def series(m: pl.DataFrame, category: str, flow: str, col: str) -> dict[int, float]:
    sub = m.filter((pl.col("category") == category) & (pl.col("flow") == flow))
    return {int(r["year"]): float(r[col]) for r in sub.iter_rows(named=True)}


# ---- figures -------------------------------------------------------------------------------------


def fig_index(
    data: Mapping[str, Mapping[int, float]], path: Path, title: str, ylabel: str, source: str
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ends: list[tuple[float, str]] = []
    for (name, s), color in zip(data.items(), SERIES, strict=False):
        xs = sorted(s)
        base = s[BOOM]
        ys = [s[x] / base * 100 for x in xs]
        ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=3.5, label=name)
        ends.append((ys[-1], name))
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.axvspan(2020.5, 2022.5, color="#f2f2f2", zorder=0, label="特需期 2021–22（灰色帯）")
    ax.set_xticks(sorted(next(iter(data.values()))))
    ax.legend(fontsize=7.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=44)
    _style(ax)
    fig.text(0.01, 0.01, f"出典: {source}", fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
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
    m = pl.read_parquet(args.data_dir / "marts" / "jp_bicycle_by_type.parquet")
    pos = pl.read_parquet(args.data_dir / "marts" / "jp_pos_sales.parquet")
    src = (
        "JBPI 国内向自転車生産輸入統計（経産省 生産動態統計・財務省 貿易統計の合算、jbpi_domestic）"
    )

    qty = {k: series(m, k[0], k[1], "qty") for k in LABELS}
    price = {k: series(m, k[0], k[1], "unit_price_jpy") for k in LABELS}
    value = {k: series(m, k[0], k[1], "value_k_jpy") for k in LABELS}
    ea, sp, mtb = (
        ("eassist", "production"),
        ("other_sports_geared", "import"),
        ("mtb_cross", "import"),
    )
    years = sorted(qty[ea])

    print("# R8 日本のセグメント分離（H2）（2026-10-22）")
    print(
        f"- mart: marts/jp_bicycle_by_type（{m.height} 行、{years[0]}–{years[-1]}）、"
        f"marts/jp_pos_sales（{pos.height} 行）"
    )
    print("\n## 表: 車種別 台数（台）と単価（円 = 金額 ÷ 台数）")
    print(
        "| 車種 | "
        + " | ".join(f"{y} 台数" for y in years)
        + " | "
        + " | ".join(f"{y} 単価" for y in years)
        + " |"
    )
    print("|---|" + "---|" * (2 * len(years)))
    for k, name in LABELS.items():
        q, p_ = qty[k], price[k]
        print(
            f"| {name} | "
            + " | ".join(f"{q[y]:,.0f}" for y in years)
            + " | "
            + " | ".join(f"{p_[y]:,.0f}" for y in years)
            + " |"
        )

    print(f"\n## H2 主判定: {BOOM} → {POST} の台数変化率")
    ce, cs, cm = (
        change(qty[ea], BOOM, POST),
        change(qty[sp], BOOM, POST),
        change(qty[mtb], BOOM, POST),
    )
    print(f"- 電動アシスト車（国内生産）: {ce:+.1%}（基準 ≥ 0）")
    print(f"- スポーツ車・外装変速機付軽快車（輸入、主）: {cs:+.1%}（基準 < −10%）")
    print(f"- MTB・クロスバイク（輸入、副）: {cm:+.1%}")
    print(
        f"- 判定（主: 電動 ≥ 0 かつ スポーツ < −10%）: **{judge_h2(ce, cs)}**、"
        f"副（MTB・クロス）: **{judge_h2(ce, cm)}**"
    )
    print(
        f"- 電動アシスト車の台数は {BOOM} → {POST} で {ce:+.1%} と基準 0 をわずかに下回る。"
        f"金額では {change(value[ea], BOOM, POST):+.1%}、"
        f"単価 {change(price[ea], BOOM, POST):+.1%}。"
    )
    print("\n### 単価（記述）: 2022 → 2025")
    for k, name in LABELS.items():
        print(
            f"- {name}: {price[k][BOOM]:,.0f} → {price[k][POST]:,.0f} 円"
            f"（{change(price[k], BOOM, POST):+.1%}）、"
            f"台数 {change(qty[k], BOOM, POST):+.1%}"
        )
    print(
        "- 台数と単価の向き: 電動アシスト（台数 僅減・単価 上昇）、スポーツ車・外装変速機付軽快車"
        "（台数 減・単価 減）、MTB・クロス（台数 大幅減・単価 僅減）。"
    )

    print("\n## 頑健性")
    for a, b in ((2021, 2025), (2023, 2025), (2022, 2024)):
        e_, s_, m_ = change(qty[ea], a, b), change(qty[sp], a, b), change(qty[mtb], a, b)
        print(
            f"- 期間 {a} → {b}: 電動 {e_:+.1%}、スポーツ(主) {s_:+.1%}、MTB {m_:+.1%}"
            f" → 主 {judge_h2(e_, s_)}、副 {judge_h2(e_, m_)}"
        )
    ev, sv = change(value[ea], BOOM, POST), change(value[sp], BOOM, POST)
    print(
        f"- 台数ではなく金額で（探索的・判定外）: 電動 {ev:+.1%}、スポーツ(主) {sv:+.1%}"
        f" → （{judge_h2(ev, sv)}）"
    )
    print(
        "- スポーツ車を 主＋副 の合算で: "
        f"{change({y: qty[sp][y] + qty[mtb][y] for y in years}, BOOM, POST):+.1%}"
    )

    # ---- POS 補助
    def monthly(cat: str, col: str) -> dict[str, float]:
        sub = pos.filter(pl.col("category") == cat)
        return {str(r["period"]): float(r[col]) for r in sub.iter_rows(named=True)}

    cats = {
        "light": "軽快車",
        "sports": "スポーツ車",
        "infant": "幼児車",
        "kids": "子ども車",
        "eassist": "電動アシスト自転車",
        "other": "その他自転車",
        "total": "合計",
    }
    print("\n## 補助: POS 販売統計（小売、税込、2024-07 開始。カバー率約 42%、家電量販を含まない）")
    print("### 2025 年暦年: 車種別 台数・金額・平均単価・構成比")
    print("| 車種 | 台数 | 金額 百万円 | 平均単価 円 | 台数構成比 | 金額構成比 |")
    print("|---|---|---|---|---|---|")
    tot_q = sum(v for k, v in monthly("total", "qty").items() if k.startswith("2025"))
    tot_v = sum(v for k, v in monthly("total", "value_jpy").items() if k.startswith("2025"))
    for cat, name in cats.items():
        yq = sum(v for k, v in monthly(cat, "qty").items() if k.startswith("2025"))
        yv = sum(v for k, v in monthly(cat, "value_jpy").items() if k.startswith("2025"))
        print(
            f"| {name} | {yq:,.0f} | {yv / 1e6:,.0f} | {yv / yq:,.0f} "
            f"| {yq / tot_q:.1%} | {yv / tot_v:.1%} |"
        )
    print("\n### 2025 年 7–9 月・10–12 月の前年同期比（台数／金額／平均単価）")
    print(
        "| 車種 | 7–9 月 台数 | 7–9 月 金額 | 7–9 月 単価 "
        "| 10–12 月 台数 | 10–12 月 金額 | 10–12 月 単価 |"
    )
    print("|---|---|---|---|---|---|---|")
    for cat, name in cats.items():
        cells = []
        for months in ((7, 8, 9), (10, 11, 12)):
            q0, q1 = (
                quarter_sum(monthly(cat, "qty"), 2024, months),
                quarter_sum(monthly(cat, "qty"), 2025, months),
            )
            v0, v1 = (
                quarter_sum(monthly(cat, "value_jpy"), 2024, months),
                quarter_sum(monthly(cat, "value_jpy"), 2025, months),
            )
            cells += [
                f"{q1 / q0 - 1:+.1%}",
                f"{v1 / v0 - 1:+.1%}",
                f"{(v1 / q1) / (v0 / q0) - 1:+.1%}",
            ]
        print(f"| {name} | " + " | ".join(cells) + " |")

    fig_index(
        {LABELS[k]: qty[k] for k in LABELS},
        args.fig_dir / "r8_qty_index.png",
        "国内向け台数（生産＋輸入）: 2022 = 100",
        "台数指数（2022 = 100）",
        src,
    )
    fig_index(
        {LABELS[k]: price[k] for k in LABELS},
        args.fig_dir / "r8_price_index.png",
        "単価（金額 ÷ 台数）: 2022 = 100",
        "単価指数（2022 = 100）",
        src,
    )
    print(f"\nfigures: {args.fig_dir / 'r8_qty_index.png'}, {args.fig_dir / 'r8_price_index.png'}")


if __name__ == "__main__":
    main()
