"""R3: 小売構造（H5）— 自転車小売業は集約したのか、小規模店は淘汰されたのか。

事前登録（design/themes/bicycle-industry.md、2026-10-22）:
  H5 (a): 経済センサス 2016→2021 で 事業所数の変化率 < 販売額の変化率
          （事業所は減るが販売額はそれほど減らない）で整合。
  H5 (b): 個人経営の事業所数の減少率 > 法人 で整合。
  注意: 2021 年の販売額は個人経営を含まない（表の注 7）→ (a) は法人の販売額に近い比較。
  頑健性で「法人の事業所数 vs 販売額」と「2012→2021」「2007→2021」「1994→2021」を並べ、
  小売業計・自動車・二輪・機械器具と比べる。

決定的スクリプト。入力は data/marts/jp_retail_census.parquet のみ。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/a20261022_r3_retail.py
        [--data-dir data] [--fig-dir …]

純粋ヘルパ（change, judge_h5a, judge_h5b）は tests/test_analysis_r3.py で検証する。
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
FROM, TO = 2016, 2021
INDUSTRY_JA: dict[str, str] = {
    "bicycle_retail": "自転車小売業",
    "retail_total": "小売業計",
    "auto_retail": "自動車小売業",
    "motorcycle_retail": "二輪自動車小売業",
    "machinery_retail_other": "機械器具小売業（自動車・自転車を除く）",
}


def change(series: Mapping[int, float | None], a: int, b: int) -> float:
    x, y = series.get(a), series.get(b)
    if x is None or y is None or x == 0:
        return math.nan
    return y / x - 1.0


def judge_h5a(est_change: float, sales_change: float) -> str:
    """(a) 事業所数の変化率 < 販売額の変化率 で整合。"""
    if math.isnan(est_change) or math.isnan(sales_change):
        return "判定不能"
    return "整合" if est_change < sales_change else "不支持"


def judge_h5b(indiv_change: float, corp_change: float) -> str:
    """(b) 個人の減少率 > 法人の減少率（= 個人の変化率 < 法人の変化率）で整合。"""
    if math.isnan(indiv_change) or math.isnan(corp_change):
        return "判定不能"
    return "整合" if indiv_change < corp_change else "不支持"


def _div(a: float | None, b: float | None) -> float:
    return math.nan if a is None or b is None or b == 0 else a / b


def _f(v: float | None) -> str:
    return "–" if v is None else f"{v:,.0f}"


def _pct(v: float) -> str:
    return "–" if math.isnan(v) else f"{v:+.1%}"


def breakeven_individual_share(
    sales_from: float, sales_to_corp: float, corp_from: float, corp_to: float
) -> float:
    """(a) を法人同士で比べたとき整合になる、2016 年の個人経営販売額の総販売額に対する最小シェア。

    2016 年の法人販売額 = sales_from − S_i（S_i: 個人の販売額、本表では不明）。法人の販売額変化率が
    法人の事業所数変化率を上回る条件
    sales_to_corp / (sales_from − S_i) − 1 > corp_to / corp_from − 1
    を S_i について解く。"""
    needed_corp_from = sales_to_corp / (corp_to / corp_from)
    return max(0.0, (sales_from - needed_corp_from) / sales_from)


def series(m: pl.DataFrame, industry: str, metric: str) -> dict[int, float | None]:
    sub = m.filter((pl.col("industry") == industry) & (pl.col("metric") == metric))
    return {int(r["year"]): r["value"] for r in sub.iter_rows(named=True)}


def fig_lines(
    data: Mapping[str, Mapping[int, float | None]],
    path: Path,
    title: str,
    ylabel: str,
    source: str,
    base_year: int,
    gap: float = 8.0,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ends: list[tuple[float, float, str]] = []
    for (name, s), color in zip(data.items(), SERIES, strict=False):
        pts = [(y, v) for y, v in sorted(s.items()) if v is not None]
        base = s.get(base_year)
        if not pts or base is None:
            continue
        xs = [y for y, _ in pts]
        ys = [v / base * 100 for _, v in pts]
        ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=3.5)
        ends.append((ys[-1], xs[-1], name))
    _direct_labels(ax, ends, gap=gap)
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    _style(ax)
    fig.text(0.01, 0.01, f"出典: {source}", fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    fig_dir: Path = args.fig_dir
    m = pl.read_parquet(args.data_dir / "marts" / "jp_retail_census.parquet")

    import logging

    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]

    print("# R3 小売構造（H5）（2026-10-22）")
    print(f"jp_retail_census {m.height} rows")
    src = (
        "経済センサス-活動調査（令和 3 年）卸売業・小売業 産業編 第 1 表（全国）。"
        "2021 年の販売額は法人のみ"
    )

    est = series(m, "bicycle_retail", "establishments")
    corp = series(m, "bicycle_retail", "establishments_corporate")
    indiv = series(m, "bicycle_retail", "establishments_individual")
    sales = series(m, "bicycle_retail", "annual_sales_mn_jpy")
    persons = series(m, "bicycle_retail", "persons_engaged")
    e, s_, i_, c_ = (change(x, FROM, TO) for x in (est, sales, indiv, corp))
    print(f"\n## H5 主判定（{FROM}→{TO}、自転車小売業）")
    print(
        f"- (a) 事業所数 {_f(est[FROM])} → {_f(est[TO])}（{e:+.1%}） vs "
        f"販売額 {_f(sales[FROM])} → {_f(sales[TO])} 百万円（{s_:+.1%}） → **{judge_h5a(e, s_)}**"
    )
    print(
        f"- (b) 個人 {_f(indiv[FROM])} → {_f(indiv[TO])}（{i_:+.1%}） vs "
        f"法人 {_f(corp[FROM])} → {_f(corp[TO])}（{c_:+.1%}） → **{judge_h5b(i_, c_)}**"
    )
    print(f"- 従業者数 {_f(persons[FROM])} → {_f(persons[TO])}（{change(persons, FROM, TO):+.1%}）")
    per_corp = {y: _div(sales.get(y), corp.get(y)) for y in (FROM, TO)}
    print(
        f"- 法人 1 事業所当たり販売額（百万円）: {FROM} ≤ {per_corp[FROM]:,.1f}"
        "（上限。分子に個人の販売額を含む）, "
        f"{TO} = {per_corp[TO]:,.1f}"
    )

    print("\n## 頑健性")
    share = breakeven_individual_share(
        sales[FROM] or 0, sales[TO] or 0, corp[FROM] or 0, corp[TO] or 0
    )
    print(
        f"- (a) 法人同士の比較: 2016 の法人販売額は本表に無く上限 {_f(sales[FROM])} のみ"
        "分かる。"
        f"法人の販売額変化率 ≥ {s_:+.1%}（下限）vs 法人の事業所数 {c_:+.1%} → "
        "**判定不能（定義差）**。"
        f"2016 の個人経営の販売額が総販売額の {share:.1%}"
        f"（{share * (sales[FROM] or 0):,.0f} 百万円、"
        f"個人 1 店当たり {share * (sales[FROM] or 0) / (indiv[FROM] or 1) * 100:,.0f} 万円/年）"
        "を超えれば整合"
    )
    for a, b in ((2012, 2021), (2007, 2021), (1994, 2021)):
        print(
            f"- {a}→{b}: 事業所 {_pct(change(est, a, b))}, 販売額 {_pct(change(sales, a, b))}"
            f"（{b} は法人のみ）, 個人 {_pct(change(indiv, a, b))}, "
            f"法人 {_pct(change(corp, a, b))} → "
            f"(a) {judge_h5a(change(est, a, b), change(sales, a, b))}（定義差込み）, "
            f"(b) {judge_h5b(change(indiv, a, b), change(corp, a, b))}"
        )

    print(f"\n## 対比: 他業種の {FROM}→{TO}（販売額の {TO} は法人のみ。(a) は定義差込み）")
    print("| 業種 | 事業所数 | 個人 | 法人 | 販売額（2021 は法人のみ） | (a) 定義差込み | (b) |")
    print("|---|---|---|---|---|---|---|")
    for ind, ja in INDUSTRY_JA.items():
        ce = change(series(m, ind, "establishments"), FROM, TO)
        ci = change(series(m, ind, "establishments_individual"), FROM, TO)
        cc = change(series(m, ind, "establishments_corporate"), FROM, TO)
        cs = change(series(m, ind, "annual_sales_mn_jpy"), FROM, TO)
        print(
            f"| {ja} | {_pct(ce)} | {_pct(ci)} | {_pct(cc)} | {_pct(cs)} "
            f"| {judge_h5a(ce, cs)} | {judge_h5b(ci, cc)} |"
        )

    print("\n## 自転車小売業の時系列")
    print("| 年 | 事業所数 | 法人 | 個人 | 従業者数 | 販売額 百万円 |")
    print("|---|---|---|---|---|---|")
    for y in sorted(est):
        print(
            f"| {y} | {_f(est[y])} | {_f(corp[y])} | {_f(indiv[y])} | {_f(persons[y])} "
            f"| {_f(sales[y])} |"
        )

    fig_lines(
        {
            "事業所数（合計）": est,
            "事業所数（法人）": corp,
            "事業所数（個人）": indiv,
            "従業者数": persons,
            "年間商品販売額（2021 は法人のみ）": sales,
        },
        fig_dir / "r3_h5_bicycle_retail.png",
        "自転車小売業の事業所・従業者・販売額（2016 = 100）",
        "指数（2016 = 100）",
        src,
        base_year=2016,
        gap=12.0,
    )
    fig_lines(
        {
            ja: series(m, ind, "establishments_individual")
            for ind, ja in INDUSTRY_JA.items()
            if ind != "motorcycle_retail"
        },
        fig_dir / "r3_h5_individual_establishments.png",
        "個人経営の事業所数: 自転車小売業と他業種（2016 = 100）",
        "指数（2016 = 100）",
        "経済センサス-活動調査（令和 3 年）卸売業・小売業 産業編 第 1 表（全国）",
        base_year=2016,
    )
    print("\n図:", ", ".join(p.name for p in sorted(fig_dir.glob("r3_*.png"))))


if __name__ == "__main__":
    main()
