"""R2: 部品のブルウィップ（H3）と価格の二極化（H4）— 事前登録した判定を行う。

事前登録（design/themes/bicycle-industry.md、2026-10-22）:
  H3: シマノ 自転車部品売上の 2022→2023 の落ち幅（%）は、同期間の世界完成車需要の代理
      （主要国輸入台数）
      の落ち幅の 1.5 倍以上。判定: 比 ≥ 1.5 で整合。ついで 2024–25 に完成車が横ばい・部品が増収なら
      「在庫消化の終了」と記述。
      需要の代理 = Comtrade HS 8712 輸入台数の合計（JPN USA DEU NLD GBR ITA の 6 か国。
      FRA は台数欠損、CHN・TWN は輸出国なので除く）。補助: 国別の比、金額 USD ベース。
      EU 販売台数は未取得（ZIV 等）。
  H4: CPI 自転車Ａ（低価格）の 2022→2025 の上昇率 − 自転車Ｂ（高価格）の上昇率 ≥ 5pt で整合。
      年平均指数（2025=100）。補助: 12 月値、2019→2025、HICP（R1 参照）。

決定的スクリプト。入力は data/marts/{shimano_segments,bicycle_trade,jp_cpi_vehicles}.parquet のみ。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/\\
        a20261022_r2_bullwhip_price.py [--data-dir data] [--fig-dir …]

純粋ヘルパ（pct_change, bullwhip_ratio, judge_h3, judge_h4）は tests/test_analysis_r2.py で
検証する。
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
    _direct_labels,
    _style,
)

THEME_DIR = Path(__file__).resolve().parents[3]
DEMAND_REPORTERS: tuple[str, ...] = ("JPN", "USA", "DEU", "NLD", "GBR", "ITA")
H3_FROM, H3_TO = 2022, 2023
H4_FROM, H4_TO = 2022, 2025


# ---- pure helpers -------------------------------------------------------------------------------


def pct_change(series: Mapping[int, float], a: int, b: int) -> float:
    """a → b の変化率（負なら減少）。欠けていれば nan。"""
    x, y = series.get(a), series.get(b)
    if x is None or y is None or x == 0:
        return math.nan
    return y / x - 1.0


def bullwhip_ratio(parts_change: float, demand_change: float) -> float:
    """部品の落ち幅 ÷ 需要の落ち幅（どちらも減少のとき）。需要が減っていなければ nan。"""
    if math.isnan(parts_change) or math.isnan(demand_change) or demand_change >= 0:
        return math.nan
    return (-parts_change) / (-demand_change)


def judge_h3(ratio: float) -> str:
    if math.isnan(ratio):
        return "判定不能"
    return "整合" if ratio >= 1.5 else "不支持"


def judge_h4(gap_pt: float) -> str:
    if math.isnan(gap_pt):
        return "判定不能"
    return "整合" if gap_pt >= 5.0 else "不支持"


# ---- data ----------------------------------------------------------------------------------------


def shimano_series(m: pl.DataFrame, key: str, metric: str) -> dict[int, float]:
    sub = m.filter((pl.col("key") == key) & (pl.col("metric") == metric))
    return {int(r["fy"]): float(r["value_mn_jpy"]) for r in sub.iter_rows(named=True)}


def trade_series(t: pl.DataFrame, iso3: str, col: str) -> dict[int, float]:
    sub = t.filter(
        (pl.col("iso3") == iso3)
        & (pl.col("flow") == "import")
        & (pl.col("hs") == "8712")
        & pl.col(col).is_not_null()
    )
    return {int(r["year"]): float(r[col]) for r in sub.iter_rows(named=True)}


def demand_aggregate(t: pl.DataFrame, col: str, years: Sequence[int]) -> dict[int, float]:
    """6 か国の合計。どの年も 6 か国全部そろう年だけ返す。"""
    per = {iso: trade_series(t, iso, col) for iso in DEMAND_REPORTERS}
    out: dict[int, float] = {}
    for y in years:
        if all(y in s for s in per.values()):
            out[y] = sum(s[y] for s in per.values())
    return out


def cpi_annual(c: pl.DataFrame, item: str) -> dict[int, float]:
    sub = c.filter((pl.col("item") == item) & (pl.col("freq") == "annual"))
    return {int(r["year"]): float(r["value"]) for r in sub.iter_rows(named=True)}


def cpi_december(c: pl.DataFrame, item: str) -> dict[int, float]:
    sub = c.filter(
        (pl.col("item") == item) & (pl.col("freq") == "monthly") & (pl.col("month") == 12)
    )
    return {int(r["year"]): float(r["value"]) for r in sub.iter_rows(named=True)}


# ---- figures -------------------------------------------------------------------------------------


def fig_lines(
    series: Mapping[str, Mapping[int, float]],
    path: Path,
    title: str,
    ylabel: str,
    source: str,
    base_year: int | None = None,
    gap: float = 6.0,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ends: list[tuple[float, float, str]] = []
    for (name, s), color in zip(series.items(), SERIES, strict=False):
        xs = sorted(s)
        if base_year is not None:
            if base_year not in s:
                continue
            ys = [s[x] / s[base_year] * 100 for x in xs]
        else:
            ys = [s[x] for x in xs]
        ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=3.5)
        ends.append((ys[-1], xs[-1], name))
    _direct_labels(ax, ends, gap=gap)
    if base_year is not None:
        ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.axvspan(2020, 2021, color="#f2f2f2", zorder=0)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    _style(ax)
    fig.text(0.01, 0.01, f"出典: {source}", fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    fig_dir: Path = args.fig_dir
    sh = pl.read_parquet(args.data_dir / "marts" / "shimano_segments.parquet")
    tr = pl.read_parquet(args.data_dir / "marts" / "bicycle_trade.parquet")
    cp = pl.read_parquet(args.data_dir / "marts" / "jp_cpi_vehicles.parquet")

    import logging

    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]

    print("# R2 部品のブルウィップ（H3）と価格の二極化（H4）（2026-10-22）")
    print(
        f"shimano_segments {sh.height} rows, bicycle_trade {tr.height}, jp_cpi_vehicles {cp.height}"
    )

    # ---- H3
    bike = shimano_series(sh, "bicycle_components", "sales")
    bike_profit = shimano_series(sh, "bicycle_components", "profit")
    qty = demand_aggregate(tr, "qty", range(2010, 2025))
    usd = demand_aggregate(tr, "value_usd", range(2010, 2025))
    p_parts = pct_change(bike, H3_FROM, H3_TO)
    p_qty = pct_change(qty, H3_FROM, H3_TO)
    p_usd = pct_change(usd, H3_FROM, H3_TO)
    ratio = bullwhip_ratio(p_parts, p_qty)
    print(
        f"\n## H3 主判定: シマノ 自転車部品売上 {H3_FROM}→{H3_TO} vs 6 か国 8712 輸入台数"
        "（判定: 比 ≥ 1.5）"
    )
    print(
        f"- シマノ 自転車部品売上（百万円）: {bike[H3_FROM]:,.0f} → {bike[H3_TO]:,.0f}"
        f"（{p_parts:+.1%}）"
    )
    print(
        f"- 6 か国 輸入台数（{', '.join(DEMAND_REPORTERS)}）: {qty[H3_FROM]:,.0f} → "
        f"{qty[H3_TO]:,.0f}（{p_qty:+.1%}）"
    )
    print(f"- 比 = {ratio:.2f} → **{judge_h3(ratio)}**")
    print("\n補助")
    r_usd = bullwhip_ratio(p_parts, p_usd)
    print(f"- 6 か国 輸入金額 USD: {p_usd:+.1%}、比 {r_usd:.2f}（{judge_h3(r_usd)}）")
    print("- 国別（8712 輸入台数の 2022→2023 と 比）:")
    for iso in DEMAND_REPORTERS:
        s = trade_series(tr, iso, "qty")
        pc = pct_change(s, H3_FROM, H3_TO)
        print(f"  - {iso}: {pc:+.1%}, 比 {bullwhip_ratio(p_parts, pc):.2f}")
    p21 = pct_change(bike, 2021, 2023)
    p24, q24 = pct_change(bike, 2022, 2024), pct_change(qty, 2022, 2024)
    q21 = pct_change(qty, 2021, 2023)
    print(
        f"- 2021→2023（ピーク 1 年前から）: 部品 {p21:+.1%}, 需要 {q21:+.1%}, "
        f"比 {bullwhip_ratio(p21, q21):.2f}"
    )
    print(f"- 2022→2024: 部品 {p24:+.1%}, 需要 {q24:+.1%}, 比 {bullwhip_ratio(p24, q24):.2f}")
    print(
        f"- 回復局面: 部品 2023→2024 {pct_change(bike, 2023, 2024):+.1%}, "
        f"2024→2025 {pct_change(bike, 2024, 2025):+.1%}; "
        f"需要 2023→2024 {pct_change(qty, 2023, 2024):+.1%}（2025 は未取得）"
    )
    print(
        f"- セグメント利益（百万円）: 2022 {bike_profit[2022]:,.0f} "
        f"→ 2023 {bike_profit[2023]:,.0f} "
        f"（{pct_change(bike_profit, 2022, 2023):+.1%}）→ 2025 {bike_profit[2025]:,.0f}"
    )
    print("\n| 年 | 部品売上 百万円 | 6 か国 輸入台数 | 6 か国 輸入 USD mn |")
    print("|---|---|---|---|")
    for y in range(2013, 2026):
        print(
            f"| {y} | {bike.get(y, float('nan')):,.0f} | {qty.get(y, float('nan')):,.0f} "
            f"| {usd.get(y, float('nan')) / 1e6:,.0f} |"
        )
    fig_lines(
        {
            "シマノ 自転車部品売上（円）": bike,
            "6 か国 完成車輸入台数": {y: v for y, v in qty.items() if y >= 2013},
            "6 か国 完成車輸入金額（USD）": {y: v for y, v in usd.items() if y >= 2013},
        },
        fig_dir / "r2_h3_shimano_vs_imports.png",
        "部品供給（シマノ）と完成車需要（6 か国の輸入）（2019 = 100）",
        "指数（2019 = 100）",
        "シマノ 有価証券報告書（EDINET、自転車部品 外部顧客売上高）、"
        "UN Comtrade（HS 8712 輸入、JPN USA DEU NLD GBR ITA 合計）",
        base_year=2019,
    )

    # ---- H4
    a = cpi_annual(cp, "bicycle_a")
    b = cpi_annual(cp, "bicycle_b")
    ga, gb = pct_change(a, H4_FROM, H4_TO), pct_change(b, H4_FROM, H4_TO)
    gap = (ga - gb) * 100
    print(
        f"\n## H4 主判定: CPI 自転車Ａ − 自転車Ｂ の {H4_FROM}→{H4_TO} 上昇率差"
        "（年平均、判定: ≥ 5pt）"
    )
    print(f"- 自転車Ａ（低価格）: {a[H4_FROM]:.1f} → {a[H4_TO]:.1f}（{ga:+.1%}）")
    print(f"- 自転車Ｂ（高価格）: {b[H4_FROM]:.1f} → {b[H4_TO]:.1f}（{gb:+.1%}）")
    print(f"- 差 = {gap:+.1f}pt → **{judge_h4(gap)}**")
    print("\n補助")
    ad, bd = cpi_december(cp, "bicycle_a"), cpi_december(cp, "bicycle_b")
    gd = (pct_change(ad, H4_FROM, H4_TO) - pct_change(bd, H4_FROM, H4_TO)) * 100
    print(
        f"- 12 月値: Ａ {pct_change(ad, H4_FROM, H4_TO):+.1%}, "
        f"Ｂ {pct_change(bd, H4_FROM, H4_TO):+.1%}, 差 {gd:+.1f}pt"
    )
    g19 = (pct_change(a, 2019, H4_TO) - pct_change(b, 2019, H4_TO)) * 100
    print(
        f"- 2019→2025（年平均）: Ａ {pct_change(a, 2019, H4_TO):+.1%}, "
        f"Ｂ {pct_change(b, 2019, H4_TO):+.1%}, 差 {g19:+.1f}pt"
    )
    g1522 = (pct_change(a, 2015, 2022) - pct_change(b, 2015, 2022)) * 100
    print(
        f"- 2015→2022（コロナ前〜インフレ初期）: Ａ {pct_change(a, 2015, 2022):+.1%}, "
        f"Ｂ {pct_change(b, 2015, 2022):+.1%}, 差 {g1522:+.1f}pt"
    )
    cars = {
        k: cpi_annual(cp, k)
        for k in ("car_kei", "car_small", "car_standard_a", "car_standard_b", "all_items")
    }
    print(
        "- 対比（年平均 2022→2025）: "
        + ", ".join(f"{k} {pct_change(s, H4_FROM, H4_TO):+.1%}" for k, s in cars.items())
    )
    print(
        "\n| 年 | 自転車Ａ | 自転車Ｂ | 自転車（類） | 軽乗用車 "
        "| 普通乗用車Ａ | 普通乗用車Ｂ | 総合 |"
    )
    print("|---|---|---|---|---|---|---|---|")
    cls = cpi_annual(cp, "bicycles")
    for y in range(2015, 2026):
        print(
            f"| {y} | {a[y]:.1f} | {b[y]:.1f} | {cls[y]:.1f} | {cars['car_kei'][y]:.1f} "
            f"| {cars['car_standard_a'][y]:.1f} | {cars['car_standard_b'][y]:.1f} "
            f"| {cars['all_items'][y]:.1f} |"
        )
    fig_lines(
        {
            "自転車Ａ（低価格）": {y: v for y, v in a.items() if y >= 2015},
            "自転車Ｂ（高価格）": {y: v for y, v in b.items() if y >= 2015},
            "軽乗用車": {y: v for y, v in cars["car_kei"].items() if y >= 2015},
            "普通乗用車Ａ": {y: v for y, v in cars["car_standard_a"].items() if y >= 2015},
            "普通乗用車Ｂ": {y: v for y, v in cars["car_standard_b"].items() if y >= 2015},
            "総合": {y: v for y, v in cars["all_items"].items() if y >= 2015},
        },
        fig_dir / "r2_h4_cpi_bicycle_ab.png",
        "日本 CPI: 自転車Ａ／Ｂ と乗用車（年平均、2019 = 100）",
        "指数（2019 = 100）",
        "総務省 消費者物価指数 2025 年基準 品目別（全国、年平均）",
        base_year=2019,
        gap=3.5,
    )
    print("\n図:", ", ".join(p.name for p in sorted(fig_dir.glob("r2_*.png"))))


if __name__ == "__main__":
    main()
