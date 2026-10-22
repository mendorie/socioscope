"""R4: 特需の先食い（H7）と原産国別の貿易分解（H8）。コロナ前・特需・特需後の 3 局面を分けて扱う。

事前登録（design/themes/bicycle-industry.md、2026-10-22）:
  H7: 2015–19 の線形トレンドを外挿し、E = Σ_{2020–21}(実績 − トレンド)、F = Σ_{2022–24}(同)、
      R = −F/E。E > 0 かつ 0.8 ≤ R ≤ 1.5 → 先食いで説明できる（整合）。R > 2 → 不支持
      （構造的縮小を含む）。1.5 < R ≤ 2 → 中間。E ≤ 0 → 判定不能。
      水準 L = 特需後（2023–24、あれば 2025）の実績平均 ÷ 同期間のトレンド平均。
      L ≥ 0.9 戻っている、L < 0.8 新しい常態、間は中間。
      頑健性: トレンド期間 2012–19・2017–19、対数線形、F を 2023–24 に。
      日本の国内販売（生産動態統計）は 2017 年からしか無いのでトレンドは 2017–19
      （事前登録からの逸脱、明記）。
  H8: (a) 台湾産完成車の輸入単価（USD/台）の 2022→2024 変化率、5 か国の中央値 ≤ −10% で整合、
      ≥ 0 で不支持。
      (b) 部品（8714）輸入の中国シェア（金額）の 2019→2024 変化、5 か国の中央値 ≥ +5pt で整合、
      ≤ 0 で不支持。
      局面: コロナ前（2015–19 平均）と特需後（2023–24 平均）の比較を並べる。

決定的スクリプト。入力は data/marts/{meti_production, bicycle_trade, bicycle_trade_by_origin,
shimano_segments}.parquet。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/\\
        a20261022_r4_pullforward_origin.py [--data-dir data] [--fig-dir …]

純粋ヘルパ（linear_trend, pullforward, judge_h7, level_ratio, judge_level, median, judge_h8a,
judge_h8b）は tests/test_analysis_r4.py で検証する。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from theme_bicycle_industry.analysis.a20261022_r1_volume_price import (
    INK,
    MUTED,
    SERIES,
    _direct_labels,
    _style,
    meti_annual,
    trade_annual,
)

THEME_DIR = Path(__file__).resolve().parents[3]
PRE = (2015, 2019)
BOOM = (2020, 2021)
BUST = (2022, 2024)
POST = (2023, 2025)
ORIGIN_COUNTRIES: tuple[str, ...] = ("JPN", "USA", "DEU", "NLD", "GBR")


# ---- pure helpers -------------------------------------------------------------------------------


def linear_trend(
    series: Mapping[int, float], start: int, end: int, log: bool = False
) -> dict[int, float] | None:
    """start–end の点に最小二乗直線（log=True なら対数線形）を当て、start–2025 の予測値を返す。
    点が 3 つ未満なら None。"""
    xs = [y for y in range(start, end + 1) if y in series]
    if len(xs) < 3:
        return None
    ys = [math.log(series[y]) if log else series[y] for y in xs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    intercept = my - slope * mx
    out = {}
    for y in range(start, 2026):
        v = intercept + slope * y
        out[y] = math.exp(v) if log else v
    return out


@dataclass(frozen=True)
class PullForward:
    excess: float  # E
    deficit: float  # F (negative when actual is below trend)
    ratio: float  # R = -F / E
    n_boom: int
    n_bust: int


def pullforward(
    series: Mapping[int, float],
    trend: Mapping[int, float],
    boom: tuple[int, int] = BOOM,
    bust: tuple[int, int] = BUST,
) -> PullForward:
    b = [series[y] - trend[y] for y in range(boom[0], boom[1] + 1) if y in series and y in trend]
    d = [series[y] - trend[y] for y in range(bust[0], bust[1] + 1) if y in series and y in trend]
    e, f = sum(b), sum(d)
    ratio = (-f / e) if (b and d and e > 0) else math.nan
    return PullForward(e, f, ratio, len(b), len(d))


def judge_h7(pf: PullForward) -> str:
    if pf.n_boom == 0 or pf.n_bust == 0 or pf.excess <= 0:
        return "判定不能（特需なし）"
    if 0.8 <= pf.ratio <= 1.5:
        return "整合（先食い）"
    if pf.ratio > 2:
        return "不支持（構造的縮小）"
    if pf.ratio < 0.8:
        return "不足小（事後区分: R < 0.8）"
    return "中間"


def level_ratio(
    series: Mapping[int, float], trend: Mapping[int, float], post: tuple[int, int] = POST
) -> float:
    ys = [y for y in range(post[0], post[1] + 1) if y in series and y in trend]
    if not ys:
        return math.nan
    return (sum(series[y] for y in ys) / len(ys)) / (sum(trend[y] for y in ys) / len(ys))


def judge_level(level: float) -> str:
    if math.isnan(level):
        return "判定不能"
    if level >= 0.9:
        return "戻っている"
    if level < 0.8:
        return "新しい常態（下方）"
    return "中間"


def median(values: Sequence[float]) -> float:
    xs = sorted(v for v in values if not math.isnan(v))
    if not xs:
        return math.nan
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def judge_h8a(median_change: float) -> str:
    if math.isnan(median_change):
        return "判定不能"
    if median_change <= -0.10:
        return "整合"
    if median_change >= 0:
        return "不支持"
    return "中間"


def judge_h8b(median_pt: float) -> str:
    if math.isnan(median_pt):
        return "判定不能"
    if median_pt >= 5:
        return "整合"
    if median_pt <= 0:
        return "不支持"
    return "中間"


def pct(a: float, b: float) -> float:
    return math.nan if a == 0 or math.isnan(a) or math.isnan(b) else b / a - 1


def avg(series: Mapping[int, float], span: tuple[int, int]) -> float:
    xs = [
        series[y] for y in range(span[0], span[1] + 1) if y in series and not math.isnan(series[y])
    ]
    return sum(xs) / len(xs) if xs else math.nan


# ---- data ----------------------------------------------------------------------------------------


def origin_series(o: pl.DataFrame, iso3: str, hs: str, partner: str, col: str) -> dict[int, float]:
    sub = o.filter((pl.col("iso3") == iso3) & (pl.col("hs") == hs) & (pl.col("partner") == partner))
    return {int(r["year"]): float(r[col]) for r in sub.iter_rows(named=True) if r[col] is not None}


def unit_value(o: pl.DataFrame, iso3: str, partner: str) -> dict[int, float]:
    q = origin_series(o, iso3, "8712", partner, "qty")
    v = origin_series(o, iso3, "8712", partner, "value_usd")
    return {y: v[y] / q[y] for y in q if y in v and q[y] > 0}


def share(o: pl.DataFrame, iso3: str, hs: str, partner: str, col: str) -> dict[int, float]:
    p = origin_series(o, iso3, hs, partner, col)
    w = origin_series(o, iso3, hs, "WLD", col)
    return {y: p[y] / w[y] * 100 for y in p if y in w and w[y] > 0}


# ---- figures -------------------------------------------------------------------------------------


def fig_trend(
    series: Mapping[int, float],
    trend: Mapping[int, float],
    path: Path,
    title: str,
    ylabel: str,
    source: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = sorted(series)
    ax.plot(xs, [series[x] for x in xs], color=SERIES[0], linewidth=2, marker="o", markersize=3.5)
    tx = [y for y in sorted(trend) if y >= min(xs)]
    ax.plot(tx, [trend[y] for y in tx], color=MUTED, linewidth=1.2, linestyle="--")
    for y in xs:
        if y in trend and y >= 2020:
            ax.fill_between(
                [y - 0.2, y + 0.2],
                trend[y],
                series[y],
                color=SERIES[1] if series[y] < trend[y] else SERIES[2],
                alpha=0.5,
                linewidth=0,
            )
    ax.axvspan(2019.5, 2022.5, color="#f2f2f2", zorder=0)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    _style(ax)
    fig.text(
        0.01,
        0.01,
        f"出典: {source}。破線は 2015–19（日本国内販売は 2017–19）の線形トレンド、"
        "網掛けは特需期 2020–22",
        fontsize=7,
        color=MUTED,
        ha="left",
        va="bottom",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_lines(
    data: Mapping[str, Mapping[int, float]],
    path: Path,
    title: str,
    ylabel: str,
    source: str,
    gap: float,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ends: list[tuple[float, float, str]] = []
    for (name, s), color in zip(data.items(), SERIES, strict=False):
        xs = sorted(s)
        if not xs:
            continue
        ax.plot(
            xs, [s[x] for x in xs], color=color, linewidth=2, marker="o", markersize=3.5, label=name
        )
        ends.append((s[xs[-1]], xs[-1], name))
    if gap > 0:
        _direct_labels(ax, ends, gap=gap)
    else:
        ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=5)
    ax.axvspan(2019.5, 2022.5, color="#f2f2f2", zorder=0)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=18 if gap <= 0 else 6)
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
    meti = pl.read_parquet(args.data_dir / "marts" / "meti_production.parquet")
    trade = pl.read_parquet(args.data_dir / "marts" / "bicycle_trade.parquet")
    origin = pl.read_parquet(args.data_dir / "marts" / "bicycle_trade_by_origin.parquet")
    sh = pl.read_parquet(args.data_dir / "marts" / "shimano_segments.parquet")

    import logging

    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]

    print("# R4 特需の先食い（H7）と原産国別分解（H8）（2026-10-22）")
    print(
        f"meti_production {meti.height}, bicycle_trade {trade.height}, "
        f"bicycle_trade_by_origin {origin.height}, shimano_segments {sh.height} rows"
    )

    # ---- H7
    jp_sales: dict[int, float] = {}
    for p in ("bicycle_light", "bicycle_e_assist", "bicycle_other"):
        for y, v in meti_annual(meti, p, "sales_qty").items():
            jp_sales[y] = jp_sales.get(y, 0.0) + v
    shimano = {
        int(r["fy"]): float(r["value_mn_jpy"])
        for r in sh.filter(
            (pl.col("key") == "bicycle_components") & (pl.col("metric") == "sales")
        ).iter_rows(named=True)
    }
    six: dict[int, float] = {}
    for iso in ("JPN", "USA", "DEU", "NLD", "GBR", "ITA"):
        s = trade_annual(trade, iso, "import", "8712", "qty")
        for y in range(2015, 2025):
            if y in s:
                six[y] = six.get(y, 0.0) + s[y]
            else:
                six[y] = math.nan
    six = {y: v for y, v in six.items() if not math.isnan(v)}
    h7: dict[str, tuple[dict[int, float], tuple[int, int]]] = {
        "日本 国内販売（生産動態統計、完成車 3 区分、トレンド 2017–19）": (jp_sales, (2017, 2019)),
        "日本 輸入 8712": (trade_annual(trade, "JPN", "import", "8712", "qty"), PRE),
        "米国 輸入 8712": (trade_annual(trade, "USA", "import", "8712", "qty"), PRE),
        "ドイツ 輸入 8712": (trade_annual(trade, "DEU", "import", "8712", "qty"), PRE),
        "英国 輸入 8712": (trade_annual(trade, "GBR", "import", "8712", "qty"), PRE),
        "オランダ 輸入 8712": (trade_annual(trade, "NLD", "import", "8712", "qty"), PRE),
        "6 か国 輸入 8712 合計": (six, PRE),
        "シマノ 自転車部品売上（百万円）": (shimano, PRE),
        "日本 電動アシスト 販売（トレンド 2017–19）": (
            meti_annual(meti, "bicycle_e_assist", "sales_qty"),
            (2017, 2019),
        ),
        "日本 軽快車 販売（トレンド 2017–19）": (
            meti_annual(meti, "bicycle_light", "sales_qty"),
            (2017, 2019),
        ),
        "日本 その他 販売（トレンド 2017–19）": (
            meti_annual(meti, "bicycle_other", "sales_qty"),
            (2017, 2019),
        ),
    }
    print(
        "\n## H7 主判定: 2020–21 の累積超過 E と 2022–24 の累積不足 F、R = −F/E（0.8–1.5 整合、>2 不支持）、"  # noqa: E501
        "特需後の水準 L（2023–25 の実績平均 ÷ トレンド平均。貿易系列は 2023–24。≥0.9 戻り、<0.8 新常態）。"  # noqa: E501
        "注: 特需期は 2020–22 と定義するが、E は事前登録どおり 2020–21、F は 2022–24 で、2022 年は F 側に入る。"  # noqa: E501
        "「不足小」は事後区分（R < 0.8）"
    )
    print("| 系列 | E（2020–21） | F（2022–24） | R | 判定 | L | 水準 | 2024 実績／トレンド |")
    print("|---|---|---|---|---|---|---|---|")
    trends: dict[str, dict[int, float]] = {}
    for name, (s, span) in h7.items():
        tr = linear_trend(s, *span)
        if tr is None:
            print(f"| {name} | – | – | – | 判定不能（点不足） | – | – | – |")
            continue
        trends[name] = tr
        pf = pullforward(s, tr)
        lv = level_ratio(s, tr)
        r24 = s[2024] / tr[2024] if 2024 in s else math.nan
        print(
            f"| {name} | {pf.excess:+,.0f} | {pf.deficit:+,.0f} | {pf.ratio:.2f} | {judge_h7(pf)} | {lv:.2f} | {judge_level(lv)} | {r24:.2f} |"  # noqa: E501
        )

    print("\n### H7 頑健性")
    print(
        "| 系列 | トレンド 2012–19 R / L | トレンド 2017–19 R / L | 対数線形 R / L "
        "| F を 2023–24 に R |"
    )
    print("|---|---|---|---|---|")
    for name, (s, span) in h7.items():
        cells = []
        for start, end, log in ((2012, 2019, False), (2017, 2019, False), (span[0], span[1], True)):
            tr = linear_trend(s, start, end, log=log)
            if tr is None:
                cells.append("–")
                continue
            pf = pullforward(s, tr)
            cells.append(f"{pf.ratio:.2f} / {level_ratio(s, tr):.2f}")
        tr0 = linear_trend(s, *span)
        if tr0 is None:
            cells.append("–")
        else:
            cells.append(f"{pullforward(s, tr0, bust=(2023, 2024)).ratio:.2f}")
        print(f"| {name} | " + " | ".join(cells) + " |")

    print("\n### 3 局面の水準（コロナ前 2015–19 平均 = 100。日本国内販売は 2017–19）")
    print("| 系列 | 特需 2020–22 | 特需後 2023–25 |")
    print("|---|---|---|")
    for name, (s, span) in h7.items():
        base = avg(s, span)
        print(
            f"| {name} | {avg(s, (2020, 2022)) / base * 100:.0f} | {avg(s, (2023, 2025)) / base * 100:.0f} |"  # noqa: E501
        )

    for key, name in (
        ("jp", "日本 国内販売（生産動態統計、完成車 3 区分、トレンド 2017–19）"),
        ("six", "6 か国 輸入 8712 合計"),
        ("shimano", "シマノ 自転車部品売上（百万円）"),
    ):
        s, _ = h7[name]
        scale = 1e4 if key != "shimano" else 1e2
        fig_trend(
            {y: v / scale for y, v in s.items() if y >= 2012},
            {y: v / scale for y, v in trends[name].items()},
            fig_dir / f"r4_h7_trend_{key}.png",
            f"{name.split('（')[0]}: 実績とコロナ前トレンド",
            "万台" if key != "shimano" else "億円",
            {
                "jp": "経産省 生産動態統計（販売数量）",
                "six": "UN Comtrade（HS 8712 輸入台数、日米独蘭英伊）",
                "shimano": "シマノ 有価証券報告書（EDINET）",
            }[key],
        )

    # ---- H8
    print(
        "\n## H8 (a) 主判定: 台湾産完成車（8712）の輸入単価 USD/台、2022→2024"
        "（5 か国の中央値 ≤ −10% 整合、≥ 0 不支持）"
    )
    print(
        "| 輸入国 | 2015–19 平均 | 2022 | 2023 | 2024 | 2022→2024 | 特需後（2023–24）／コロナ前 | 中国産 2024 | 台湾／中国 2024 |"  # noqa: E501
    )
    print("|---|---|---|---|---|---|---|---|---|")
    changes_a: list[float] = []
    uv_twn: dict[str, dict[int, float]] = {}
    for iso in ORIGIN_COUNTRIES:
        t = unit_value(origin, iso, "TWN")
        c = unit_value(origin, iso, "CHN")
        uv_twn[iso] = t
        ch = pct(t.get(2022, math.nan), t.get(2024, math.nan))
        changes_a.append(ch)
        pre_ = avg(t, PRE)
        post_ = avg(t, (2023, 2024))
        print(
            f"| {iso} | {pre_:,.0f} | {t.get(2022, math.nan):,.0f} | {t.get(2023, math.nan):,.0f} | {t.get(2024, math.nan):,.0f} "  # noqa: E501
            f"| {ch:+.1%} | {post_ / pre_:.2f} | {c.get(2024, math.nan):,.0f} | {t.get(2024, math.nan) / c.get(2024, math.nan):.1f} |"  # noqa: E501
        )
    med_a = median(changes_a)
    print(f"- 中央値 {med_a:+.1%} → **{judge_h8a(med_a)}**")
    post_pre = [avg(uv_twn[iso], (2023, 2024)) / avg(uv_twn[iso], PRE) for iso in ORIGIN_COUNTRIES]
    print(f"- 特需後／コロナ前 の中央値 {median(post_pre):.2f}（1 未満なら特需後の方が安い）")

    print(
        "\n## H8 (b) 主判定: 部品（8714）輸入の中国シェア（金額 %）、2019→2024"
        "（5 か国の中央値 ≥ +5pt 整合、≤ 0 不支持）"
    )
    print(
        "| 輸入国 | 2015 | 2015–19 平均 | 2019 | 2022 | 2024 | 2019→2024 pt | 特需後 − コロナ前 pt | 台湾 2024 |"  # noqa: E501
    )
    print("|---|---|---|---|---|---|---|---|---|")
    changes_b: list[float] = []
    post_pre_b: list[float] = []
    chn_share: dict[str, dict[int, float]] = {}
    for iso in ORIGIN_COUNTRIES:
        s_c = share(origin, iso, "8714", "CHN", "value_usd")
        s_t = share(origin, iso, "8714", "TWN", "value_usd")
        chn_share[iso] = s_c
        d = s_c.get(2024, math.nan) - s_c.get(2019, math.nan)
        changes_b.append(d)
        pp = avg(s_c, (2023, 2024)) - avg(s_c, PRE)
        post_pre_b.append(pp)
        print(
            f"| {iso} | {s_c.get(2015, math.nan):.1f} | {avg(s_c, PRE):.1f} | {s_c.get(2019, math.nan):.1f} | {s_c.get(2022, math.nan):.1f} | {s_c.get(2024, math.nan):.1f} "  # noqa: E501
            f"| {d:+.2f} | {pp:+.2f} | {s_t.get(2024, math.nan):.1f} |"
        )
    med_b = median(changes_b)
    print(f"- 中央値 {med_b:+.2f}pt → **{judge_h8b(med_b)}**（基準 ≥ +5pt。小数 2 桁で判定）")
    print(f"- 特需後 − コロナ前 の中央値 {median(post_pre_b):+.2f}pt")

    print("\n## H8 (c) 記述: 完成車（8712）の台湾産シェア（台数 %／金額 %）")
    print(
        "| 輸入国 | 台数 2015–19 | 台数 2022 | 台数 2024 | 金額 2015–19 | 金額 2022 | 金額 2024 | 中国産 台数 2024 | 中国産 金額 2024 |"  # noqa: E501
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for iso in ORIGIN_COUNTRIES:
        sq = share(origin, iso, "8712", "TWN", "qty")
        sv = share(origin, iso, "8712", "TWN", "value_usd")
        cq = share(origin, iso, "8712", "CHN", "qty")
        cv = share(origin, iso, "8712", "CHN", "value_usd")
        print(
            f"| {iso} | {avg(sq, PRE):.1f} | {sq.get(2022, math.nan):.1f} | {sq.get(2024, math.nan):.1f} "  # noqa: E501
            f"| {avg(sv, PRE):.1f} | {sv.get(2022, math.nan):.1f} | {sv.get(2024, math.nan):.1f} "
            f"| {cq.get(2024, math.nan):.1f} | {cv.get(2024, math.nan):.1f} |"
        )

    fig_lines(
        {iso: uv_twn[iso] for iso in ORIGIN_COUNTRIES},
        fig_dir / "r4_h8_taiwan_unit_value.png",
        "台湾産完成自転車の輸入単価（USD/台、輸入国別）",
        "USD/台",
        "UN Comtrade（HS 8712 輸入、相手国 台湾 490、金額 ÷ 台数）",
        gap=0.0,
    )
    fig_lines(
        {iso: chn_share[iso] for iso in ORIGIN_COUNTRIES},
        fig_dir / "r4_h8_china_parts_share.png",
        "部品（HS 8714）輸入に占める中国のシェア（金額 %、輸入国別）",
        "%",
        "UN Comtrade（HS 8714 輸入、相手国 中国 156 ÷ 世界計）",
        gap=0.0,
    )
    print("\n図:", ", ".join(p.name for p in sorted(fig_dir.glob("r4_*.png"))))


if __name__ == "__main__":
    main()
