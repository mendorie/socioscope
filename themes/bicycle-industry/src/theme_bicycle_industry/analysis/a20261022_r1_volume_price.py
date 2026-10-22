"""R1: 量と価格 — コロナ前後の自転車（日本・欧米）を自動車・二輪と並べる。H1 と H4(国際側) の記述。

事前登録: design/themes/bicycle-industry.md（2026-10-22）。
  H1 判定: 2024–25 平均 / 2017–19 平均 >= 0.95 で整合、< 0.85 で不支持（完成車台数）。
           日本は 生産動態統計の販売数量（完成車 3 区分の合計）と 8712 輸入台数、
           欧米は 8712 輸入台数。
           2025 がない系列は 2024 のみ。
  H4 国際側（記述のみ、判定は CPI 自転車 A/B を取得後）: HICP 自転車 vs 自動車 の 2022→2025 変化。
  H3 の代理（記述のみ）: 部品輸出（8714、台湾・日本）の 2022→2024 の落ち幅と
           完成車輸入（8712、米独日英）の落ち幅。
  H6 の国内側（記述のみ）: 生産動態統計の 実用層（電動アシスト／軽／原付）と
           趣味層（その他自転車／普通乗用車／>250ml）。

決定的スクリプト。入力は data/marts/{meti_production,bicycle_trade,price_indices}.parquet のみ。
乱数・現在時刻なし。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/\
        a20261022_r1_volume_price.py
        [--data-dir data] [--fig-dir themes/bicycle-industry/reports/figures]

純粋ヘルパ（ratio_pre_post, judge_h1, rebase, drop_ratio）は tests/test_analysis_r1.py で検証する。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

THEME_DIR = Path(__file__).resolve().parents[3]
PRE_YEARS = (2017, 2018, 2019)
POST_YEARS = (2024, 2025)

# validated default categorical palette (dataviz skill, fixed order, never cycled)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e5e5e5"


# ---- pure helpers -------------------------------------------------------------------------------


def ratio_pre_post(
    by_year: Mapping[int, float], pre: Sequence[int] = PRE_YEARS, post: Sequence[int] = POST_YEARS
) -> tuple[float, int, int]:
    """(post 平均 / pre 平均, n_pre, n_post)。欠けている年は外す。pre か post が空なら nan。"""
    pre_v = [by_year[y] for y in pre if y in by_year and by_year[y] is not None]
    post_v = [by_year[y] for y in post if y in by_year and by_year[y] is not None]
    if not pre_v or not post_v:
        return math.nan, len(pre_v), len(post_v)
    return (sum(post_v) / len(post_v)) / (sum(pre_v) / len(pre_v)), len(pre_v), len(post_v)


def judge_h1(ratio: float) -> str:
    """事前判定: >= 0.95 整合 / < 0.85 不支持 / 間は 判定なし（中間）。nan は 判定不能。"""
    if math.isnan(ratio):
        return "判定不能"
    if ratio >= 0.95:
        return "整合"
    if ratio < 0.85:
        return "不支持"
    return "中間"


def rebase(by_period: Mapping[str, float], base_period: str) -> dict[str, float]:
    """base_period = 100 に再基準化。base が無ければ空。"""
    base = by_period.get(base_period)
    if base is None or base == 0:
        return {}
    return {p: v / base * 100.0 for p, v in by_period.items() if v is not None}


def drop_ratio(series: Mapping[int, float], peak_year: int, trough_year: int) -> float:
    """peak → trough の変化率（負なら減少）。欠けていれば nan。"""
    a, b = series.get(peak_year), series.get(trough_year)
    if a is None or b is None or a == 0:
        return math.nan
    return b / a - 1.0


# ---- data ----------------------------------------------------------------------------------------


def load(data_dir: Path) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    meti = pl.read_parquet(data_dir / "marts" / "meti_production.parquet")
    trade = pl.read_parquet(data_dir / "marts" / "bicycle_trade.parquet")
    prices = pl.read_parquet(data_dir / "marts" / "price_indices.parquet")
    return meti, trade, prices


def meti_annual(meti: pl.DataFrame, product: str, measure: str) -> dict[int, float]:
    """暦年系列: 2017–2023 は年報の暦年列（cy）、2024– は月次 12 本の年計（cy_from_months）。"""
    sub = meti.filter(
        (pl.col("product") == product)
        & (pl.col("measure") == measure)
        & pl.col("period_type").is_in(["cy", "cy_from_months"])
        & pl.col("value").is_not_null()
    )
    out: dict[int, float] = {}
    for r in sub.sort("year", "period_type").iter_rows(named=True):
        # prefer the published calendar-year figure when both exist
        if r["period_type"] == "cy" or int(r["year"]) not in out:
            out[int(r["year"])] = float(r["value"])
    return out


def trade_annual(trade: pl.DataFrame, iso3: str, flow: str, hs: str, col: str) -> dict[int, float]:
    sub = trade.filter(
        (pl.col("iso3") == iso3)
        & (pl.col("flow") == flow)
        & (pl.col("hs") == hs)
        & pl.col(col).is_not_null()
    )
    return {int(r["year"]): float(r[col]) for r in sub.iter_rows(named=True)}


def price_series(prices: pl.DataFrame, geo: str, series: str) -> dict[str, float]:
    sub = prices.filter((pl.col("geo") == geo) & (pl.col("series") == series))
    return {str(r["period"]): float(r["value"]) for r in sub.iter_rows(named=True)}


def december(by_period: Mapping[str, float]) -> dict[int, float]:
    return {int(p[:4]): v for p, v in by_period.items() if p.endswith("-12")}


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def _direct_labels(ax: Any, ends: list[tuple[float, float, str]], gap: float) -> None:
    """右端ラベルを上下にずらして重ならないようにし、線の終点からずれた分は細い引き出し線で結ぶ。"""
    ends.sort()
    last_y = -1e9
    for y_end, x_end, name in ends:
        y_lab = max(y_end, last_y + gap)
        last_y = y_lab
        if abs(y_lab - y_end) > gap / 4:
            ax.plot([x_end, x_end], [y_end, y_lab], color=MUTED, linewidth=0.5, zorder=1)
        ax.annotate(
            name, (x_end, y_lab), xytext=(4, 0), textcoords="offset points", fontsize=8, color=INK
        )


def fig_indexed_lines(
    series: Mapping[str, Mapping[int, float]],
    path: Path,
    title: str,
    ylabel: str,
    source: str,
    base_years: Sequence[int] = PRE_YEARS,
) -> None:
    """各系列を 2017–19 平均 = 100 に再基準化して重ねる（1 軸、固定色、直接ラベル）。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ends: list[tuple[float, float, str]] = []
    for (name, s), color in zip(series.items(), SERIES, strict=False):
        base = [s[y] for y in base_years if y in s]
        if not base:
            continue
        b = sum(base) / len(base)
        xs = sorted(s)
        ys = [s[x] / b * 100 for x in xs]
        ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=3.5)
        ends.append((ys[-1], xs[-1], name))
    _direct_labels(ax, ends, gap=6.5)
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


def fig_price_lines(
    series: Mapping[str, Mapping[str, float]],
    path: Path,
    title: str,
    base_period: str,
    source: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ends: list[tuple[float, float, str]] = []
    for (name, s), color in zip(series.items(), SERIES, strict=False):
        rb = rebase(s, base_period)
        if not rb:
            continue
        xs = sorted(rb)
        idx = [int(p[:4]) + (int(p[5:]) - 1) / 12 for p in xs]
        ax.plot(idx, [rb[p] for p in xs], color=color, linewidth=1.8)
        ends.append((rb[xs[-1]], idx[-1], name))
    _direct_labels(ax, ends, gap=2.0)
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.set_ylabel(f"指数（{base_period} = 100、月次）", fontsize=8, color=INK)
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
    meti, trade, prices = load(args.data_dir)
    fig_dir: Path = args.fig_dir

    import logging

    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]

    print("# R1 量と価格（2026-10-22）")
    print(
        f"meti_production {meti.height} rows, bicycle_trade {trade.height}, "
        f"price_indices {prices.height}"
    )

    # ---- H1: 完成車台数 pre/post
    print("\n## H1 完成車台数: 2024–25 平均 / 2017–19 平均（判定: >=0.95 整合, <0.85 不支持）")
    jp_sales = {
        y: sum(v)
        for y, v in _sum_products(
            meti, ["bicycle_light", "bicycle_e_assist", "bicycle_other"], "sales_qty"
        ).items()
    }
    h1_series: dict[str, dict[int, float]] = {
        "日本 国内販売（生産動態統計、完成車 3 区分）": jp_sales,
        "日本 輸入 8712": trade_annual(trade, "JPN", "import", "8712", "qty"),
        "米国 輸入 8712": trade_annual(trade, "USA", "import", "8712", "qty"),
        "ドイツ 輸入 8712": trade_annual(trade, "DEU", "import", "8712", "qty"),
        "英国 輸入 8712": trade_annual(trade, "GBR", "import", "8712", "qty"),
        "オランダ 輸入 8712": trade_annual(trade, "NLD", "import", "8712", "qty"),
    }
    print("| 系列 | 2017–19 平均 | 2024–25 平均 | 比 | n_pre/n_post | 判定 |")
    print("|---|---|---|---|---|---|")
    for name, s in h1_series.items():
        ratio, npre, npost = ratio_pre_post(s)
        pre = [s[y] for y in PRE_YEARS if y in s]
        post = [s[y] for y in POST_YEARS if y in s]
        pre_m = sum(pre) / len(pre) if pre else math.nan
        post_m = sum(post) / len(post) if post else math.nan
        print(
            f"| {name} | {pre_m:,.0f} | {post_m:,.0f} | {ratio:.2f} | {npre}/{npost} "
            f"| {judge_h1(ratio)} |"
        )
    fig_indexed_lines(
        h1_series,
        fig_dir / "r1_h1_complete_bikes_indexed.png",
        "完成自転車の台数（2017–19 平均 = 100）: 日本の国内販売・主要国の輸入",
        "指数（2017–19 平均 = 100）",
        "経産省 生産動態統計（販売数量、受入を含む、台）、UN Comtrade（HS 8712 輸入、台）",
    )

    # ---- H1 補助: 日本 セグメント別（H2 の前置き）
    print("\n## 日本 国内販売台数 セグメント別（生産動態統計、受入を含む販売数量）")
    seg = {
        "電動アシスト車": meti_annual(meti, "bicycle_e_assist", "sales_qty"),
        "軽快車": meti_annual(meti, "bicycle_light", "sales_qty"),
        "その他（スポーツ車等を含む）": meti_annual(meti, "bicycle_other", "sales_qty"),
    }
    _print_table(seg, range(2017, 2026))
    for name, s in seg.items():
        ratio, _, _ = ratio_pre_post(s)
        print(f"- {name}: 2024–25/2017–19 = {ratio:.2f}")
    unit_price = {}
    for name, key in (
        ("電動アシスト車", "bicycle_e_assist"),
        ("軽快車", "bicycle_light"),
        ("その他", "bicycle_other"),
    ):
        q = meti_annual(meti, key, "sales_qty")
        v = meti_annual(meti, key, "sales_value")
        unit_price[name] = {y: v[y] * 1000 / q[y] for y in q if y in v and q[y]}
    print("\n販売単価（販売金額 ÷ 販売数量、円）")
    _print_table(unit_price, range(2017, 2026), fmt="{:,.0f}")
    fig_indexed_lines(
        {**seg, **{f"単価 {k}": v for k, v in unit_price.items()}},
        fig_dir / "r1_jp_segments_indexed.png",
        "日本 国内販売: セグメント別の台数と単価（2017–19 平均 = 100）",
        "指数（2017–19 平均 = 100）",
        "経産省 生産動態統計 機械統計（販売数量 台、販売金額 千円 ÷ 販売数量 = 単価）",
    )

    # ---- H3 代理: 部品輸出 vs 完成車輸入 の落ち幅
    print(
        "\n## H3 の代理（探索的）: 部品輸出（8714 USD）と完成車輸入（8712 台）の変化率。"
        "事前登録の期間は 2022→2023（主）、2022→2024・2021→2024 は補助"
    )
    parts = {
        "台湾 部品輸出": trade_annual(trade, "TWN", "export", "8714", "value_usd"),
        "日本 部品輸出": trade_annual(trade, "JPN", "export", "8714", "value_usd"),
        "中国 部品輸出": trade_annual(trade, "CHN", "export", "8714", "value_usd"),
    }
    bikes = {
        "米国 完成車輸入": trade_annual(trade, "USA", "import", "8712", "qty"),
        "ドイツ 完成車輸入": trade_annual(trade, "DEU", "import", "8712", "qty"),
        "日本 完成車輸入": trade_annual(trade, "JPN", "import", "8712", "qty"),
        "英国 完成車輸入": trade_annual(trade, "GBR", "import", "8712", "qty"),
    }
    for name, s in {**parts, **bikes}.items():
        print(
            f"- {name}: 2022→2023 {drop_ratio(s, 2022, 2023):+.1%}, "
            f"2022→2024 {drop_ratio(s, 2022, 2024):+.1%}, "
            f"2021→2024 {drop_ratio(s, 2021, 2024):+.1%}"
        )
    fig_indexed_lines(
        {**parts, **bikes},
        fig_dir / "r1_parts_vs_bikes_indexed.png",
        "部品輸出（USD）と完成車輸入（台）（2017–19 平均 = 100）",
        "指数（2017–19 平均 = 100）",
        "UN Comtrade（HS 8714 輸出 FOB USD、HS 8712 輸入 台、相手国 世界計）",
    )

    # ---- H4 国際側: HICP 自転車 vs 自動車 vs 二輪、BLS
    print("\n## H4 国際側: 12 月値の変化率（HICP 2015=100、BLS 1982-84=100。基準は比に影響しない）")
    px = {
        "EU27 自転車": price_series(prices, "EU27_2020", "bicycles"),
        "EU27 自動車": price_series(prices, "EU27_2020", "cars"),
        "EU27 二輪": price_series(prices, "EU27_2020", "motorcycles"),
        "ドイツ 自転車": price_series(prices, "DE", "bicycles"),
        "米国 スポーツ用車両（自転車含む）": price_series(
            prices, "US", "sports_vehicles_incl_bicycles"
        ),
        "米国 新車": price_series(prices, "US", "new_vehicles"),
    }
    for name, ps in px.items():
        d = december(ps)
        print(
            f"- {name}: 2019→2022 {drop_ratio(d, 2019, 2022):+.1%}, "
            f"2022→2025 {drop_ratio(d, 2022, 2025):+.1%}"
        )
    fig_price_lines(
        px,
        fig_dir / "r1_price_indices.png",
        "価格指数: 自転車 vs 自動車 vs 二輪（2019-12 = 100）",
        "2019-12",
        "Eurostat HICP prc_hicp_midx CP0711/0712/0713（2015=100）、"
        "US BLS CPI-U SERC01/SETA01（1982-84=100）",
    )

    # ---- H6 国内側: 実用層 vs 趣味層（生産動態統計 販売数量）
    print(
        "\n## H6 国内側（探索的: 事前登録の区分は 輸入車 500 万円超／小型二輪／スポーツ車、"
        "期間は 2022→2025。ここでは生産動態統計で取れる区分と 2024–25/2017–19 も並べる）"
    )
    h6 = {
        "自転車 実用: 電動アシスト": meti_annual(meti, "bicycle_e_assist", "sales_qty"),
        "自転車 趣味寄り: その他": meti_annual(meti, "bicycle_other", "sales_qty"),
        "自動車 実用: 軽": meti_annual(meti, "car_kei", "sales_qty"),
        "自動車 趣味寄り: 普通（>2000ml）": meti_annual(meti, "car_standard", "sales_qty"),
        "二輪 実用: 原付一種（≤50ml）": meti_annual(meti, "moto_le50", "sales_qty"),
        "二輪 趣味: >250ml": meti_annual(meti, "moto_gt250", "sales_qty"),
    }
    for name, s in h6.items():
        ratio, _, _ = ratio_pre_post(s)
        print(f"- {name}: 2022→2025 {drop_ratio(s, 2022, 2025):+.1%}, 2024–25/2017–19 {ratio:.2f}")
    fig_indexed_lines(
        h6,
        fig_dir / "r1_h6_utility_vs_hobby_indexed.png",
        "三産業の実用層と趣味層（国内製造事業所の販売台数、2017–19 平均 = 100）",
        "指数（2017–19 平均 = 100）",
        "経産省 生産動態統計 機械統計（販売数量、台。輸入車は調査対象事業所の受入分のみ）",
    )
    # ---- 頑健性（事前リスト: 2024 のみ / pre 2015–19 / 生産数量）
    print("\n## 頑健性")
    r24 = jp_sales[2024] / (sum(jp_sales[y] for y in PRE_YEARS) / 3)
    print(
        f"- 日本 国内販売 2024 のみ / 2017–19: {r24:.2f}"
        f"（2024 {jp_sales[2024]:,.0f}, 2025 {jp_sales[2025]:,.0f}）"
    )
    for name, s in h1_series.items():
        if "輸入" in name:
            ratio, npre, _ = ratio_pre_post(s, pre=(2015, 2016, 2017, 2018, 2019))
            print(f"- {name} pre 2015–19（n_pre={npre}）: {ratio:.2f}")
    jp_prod = {
        y: sum(v)
        for y, v in _sum_products(
            meti, ["bicycle_light", "bicycle_e_assist", "bicycle_other"], "production_qty"
        ).items()
    }
    ratio, _, _ = ratio_pre_post(jp_prod)
    pre_m = sum(jp_prod[y] for y in PRE_YEARS) / 3
    post_m = sum(jp_prod[y] for y in POST_YEARS) / 2
    print(f"- 日本 国内生産数量（完成車 3 区分）: {pre_m:,.0f} → {post_m:,.0f}、比 {ratio:.2f}")
    print("\n図:", ", ".join(p.name for p in sorted(fig_dir.glob("r1_*.png"))))


def _sum_products(
    meti: pl.DataFrame, products: Sequence[str], measure: str
) -> dict[int, list[float]]:
    out: dict[int, list[float]] = {}
    for p in products:
        for y, v in meti_annual(meti, p, measure).items():
            out.setdefault(y, []).append(v)
    return {y: v for y, v in out.items() if len(v) == len(products)}


def _print_table(
    series: Mapping[str, Mapping[int, float]], years: Sequence[int], fmt: str = "{:,.0f}"
) -> None:
    ys = [y for y in years if any(y in s for s in series.values())]
    print("| 系列 | " + " | ".join(str(y) for y in ys) + " |")
    print("|---|" + "---|" * len(ys))
    for name, s in series.items():
        print(f"| {name} | " + " | ".join(fmt.format(s[y]) if y in s else "–" for y in ys) + " |")


if __name__ == "__main__":
    main()
