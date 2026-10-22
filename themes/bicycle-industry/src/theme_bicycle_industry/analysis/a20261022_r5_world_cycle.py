"""R5: 世界のスポーツ車サイクル（H9・H10）— 台湾の完成車輸出と、部品 → 完成車 の在庫サイクルの位相。

事前登録（design/themes/bicycle-industry.md、2026-10-22）:
  H9: 台湾の完成車輸出台数（HS 8712、世界計）は特需後（2023–24 平均）にコロナ前（2015–19 平均）を
      下回り、金額（USD）では上回る。判定: 台数比 < 0.9 かつ 金額比 > 1.1 で整合。
      台数比 ≥ 0.9 または
      金額比 ≤ 1.0 で不支持。間は中間。仕向地別と e-bike（871160）も並べる。
  H10: 月次（MOPS、2014–2026）: KMC（部品）と Giant・Merida（完成車）の 12 か月後方移動平均の
       ピーク月とピークからの最大落ち幅。判定: ピーク月 KMC ≤ Giant かつ KMC ≤ Merida、かつ
       最大落ち幅 KMC > Giant・Merida の平均 なら整合。片方だけなら中間、両方逆なら不支持。
       年次: シマノ（自転車部品）・KMC・Giant・Merida の年次売上でピーク年と 2019 年比（記述）。
       Fox Factory は SEC の連絡先付き UA が無いためスキップ（事前登録どおり）。

決定的スクリプト。入力は data/marts/{taiwan_bicycle_exports, tw_bicycle_monthly_revenue,
shimano_segments}.parquet。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/\\
        a20261022_r5_world_cycle.py [--data-dir data] [--fig-dir …]

純粋ヘルパ（ratio, judge_h9, trailing_mean, peak_and_drawdown, judge_h10）は
tests/test_analysis_r5.py で検証する。
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
    _style,
)

THEME_DIR = Path(__file__).resolve().parents[3]
PRE = (2015, 2019)
POST = (2023, 2024)


# ---- pure helpers -------------------------------------------------------------------------------


def avg(series: Mapping[int, float], span: tuple[int, int]) -> float:
    xs = [series[y] for y in range(span[0], span[1] + 1) if y in series]
    return sum(xs) / len(xs) if xs else math.nan


def ratio(
    series: Mapping[int, float], post: tuple[int, int] = POST, pre: tuple[int, int] = PRE
) -> float:
    a, b = avg(series, pre), avg(series, post)
    return math.nan if math.isnan(a) or math.isnan(b) or a == 0 else b / a


def judge_h9(qty_ratio: float, value_ratio: float) -> str:
    if math.isnan(qty_ratio) or math.isnan(value_ratio):
        return "判定不能"
    if qty_ratio < 0.9 and value_ratio > 1.1:
        return "整合（少なく・高く）"
    if qty_ratio >= 0.9 or value_ratio <= 1.0:
        return "不支持"
    return "中間"


def trailing_mean(series: Mapping[str, float], window: int = 12) -> dict[str, float]:
    """期間キー（YYYY-MM）順に、直近 window 本の平均（window 本そろう月だけ）。"""
    keys = sorted(series)
    out: dict[str, float] = {}
    for i in range(window - 1, len(keys)):
        win = keys[i - window + 1 : i + 1]
        out[keys[i]] = sum(series[k] for k in win) / window
    return out


@dataclass(frozen=True)
class PeakDrawdown:
    peak_period: str
    peak_value: float
    trough_period: str
    trough_value: float
    drawdown: float  # (trough − peak) / peak, 負


def peak_and_drawdown(series: Mapping[str, float], start: str = "2019-01") -> PeakDrawdown:
    """start 以降の最大値（ピーク）と、その後の最小値（谷）。"""
    keys = [k for k in sorted(series) if k >= start]
    if not keys:
        return PeakDrawdown("", math.nan, "", math.nan, math.nan)
    peak = max(keys, key=lambda k: series[k])
    after = [k for k in keys if k >= peak]
    trough = min(after, key=lambda k: series[k])
    return PeakDrawdown(
        peak, series[peak], trough, series[trough], series[trough] / series[peak] - 1
    )


def judge_h10(parts: PeakDrawdown, bikes: Sequence[PeakDrawdown]) -> str:
    """部品のピーク月が完成車の各ピーク月以前、かつ 部品の落ち幅（絶対値）> 完成車平均 で整合。"""
    if not parts.peak_period or any(not b.peak_period for b in bikes):
        return "判定不能"
    phase_ok = all(parts.peak_period <= b.peak_period for b in bikes)
    depth_ok = -parts.drawdown > sum(-b.drawdown for b in bikes) / len(bikes)
    if phase_ok and depth_ok:
        return "整合"
    if phase_ok or depth_ok:
        return "中間"
    return "不支持"


# ---- data ----------------------------------------------------------------------------------------


def taiwan_series(t: pl.DataFrame, hs: str, partner: str, col: str) -> dict[int, float]:
    sub = t.filter((pl.col("hs") == hs) & (pl.col("partner") == partner))
    return {int(r["year"]): float(r[col]) for r in sub.iter_rows(named=True) if r[col] is not None}


def monthly(m: pl.DataFrame, company: str) -> dict[str, float]:
    sub = m.filter((pl.col("company") == company) & pl.col("revenue_ntd_k").is_not_null())
    return {str(r["period"]): float(r["revenue_ntd_k"]) for r in sub.iter_rows(named=True)}


def annual_from_monthly(series: Mapping[str, float]) -> dict[int, float]:
    out: dict[int, list[float]] = {}
    for k, v in series.items():
        out.setdefault(int(k[:4]), []).append(v)
    return {y: sum(v) for y, v in out.items() if len(v) == 12}


# ---- figures -------------------------------------------------------------------------------------


def fig_monthly(
    data: Mapping[str, Mapping[str, float]], path: Path, title: str, source: str
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (name, s), color in zip(data.items(), SERIES, strict=False):
        keys = sorted(s)
        base = s.get("2019-12")
        if base is None or base == 0:
            continue
        xs = [int(k[:4]) + (int(k[5:]) - 1) / 12 for k in keys]
        ax.plot(xs, [s[k] / base * 100 for k in keys], color=color, linewidth=1.8, label=name)
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.axvspan(2020, 2023, color="#f2f2f2", zorder=0)
    ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4)
    ax.set_ylabel("12 か月移動平均（2019-12 = 100）", fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=18)
    _style(ax)
    fig.text(0.01, 0.01, f"出典: {source}", fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_annual(
    data: Mapping[str, Mapping[int, float]], path: Path, title: str, ylabel: str, source: str
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (name, s), color in zip(data.items(), SERIES, strict=False):
        xs = sorted(s)
        base = s.get(2019)
        if not xs or base is None or base == 0:
            continue
        ax.plot(
            xs,
            [s[x] / base * 100 for x in xs],
            color=color,
            linewidth=2,
            marker="o",
            markersize=3.5,
            label=name,
        )
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.axvspan(2019.5, 2022.5, color="#f2f2f2", zorder=0)
    ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=18)
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
    tw = pl.read_parquet(args.data_dir / "marts" / "taiwan_bicycle_exports.parquet")
    mo = pl.read_parquet(args.data_dir / "marts" / "tw_bicycle_monthly_revenue.parquet")
    sh = pl.read_parquet(args.data_dir / "marts" / "shimano_segments.parquet")

    import logging

    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]

    print("# R5 世界のスポーツ車サイクル（H9・H10）（2026-10-22）")
    print(
        f"taiwan_bicycle_exports {tw.height}, tw_bicycle_monthly_revenue {mo.height}, shimano_segments {sh.height} rows"  # noqa: E501
    )

    # ---- H9
    q = taiwan_series(tw, "8712", "WLD", "qty")
    v = taiwan_series(tw, "8712", "WLD", "value_usd")
    rq, rv = ratio(q), ratio(v)
    print("\n## H9 主判定: 台湾の完成車輸出（8712、世界計）特需後（2023–24）／コロナ前（2015–19）")
    print(f"- 台数: {avg(q, PRE):,.0f} → {avg(q, POST):,.0f}（比 {rq:.2f}）")
    print(f"- 金額 USD: {avg(v, PRE) / 1e6:,.0f} → {avg(v, POST) / 1e6:,.0f} 百万（比 {rv:.2f}）")
    print(f"- 単価 USD/台: {avg(v, PRE) / avg(q, PRE):,.0f} → {avg(v, POST) / avg(q, POST):,.0f}")
    print(f"- 判定（台数 < 0.9 かつ 金額 > 1.1 で整合）: **{judge_h9(rq, rv)}**")
    print("\n| 年 | 台数 | 金額 USD mn | 単価 USD | e-bike 871160 台数 | e-bike 金額 USD mn |")
    print("|---|---|---|---|---|---|")
    eq = taiwan_series(tw, "871160", "WLD", "qty")
    ev = taiwan_series(tw, "871160", "WLD", "value_usd")
    for y in sorted(q):
        print(
            f"| {y} | {q[y]:,.0f} | {v[y] / 1e6:,.0f} | {v[y] / q[y]:,.0f} "
            f"| {eq.get(y, float('nan')):,.0f} | {ev.get(y, float('nan')) / 1e6:,.0f} |"
        )
    print("\n### 仕向地別（8712 台数、特需後／コロナ前 と 2024／2015）")
    print(
        "| 仕向地 | 2015 | 2019 | 2022 | 2024 | 特需後／コロナ前 台数 | 同 金額 | 2024／2015 台数 |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for p in ("USA", "DEU", "NLD", "GBR", "JPN", "OTH", "WLD"):
        pq = taiwan_series(tw, "8712", p, "qty")
        pv = taiwan_series(tw, "8712", p, "value_usd")
        print(
            f"| {p} | {pq.get(2015, float('nan')):,.0f} | {pq.get(2019, float('nan')):,.0f} | {pq.get(2022, float('nan')):,.0f} "  # noqa: E501
            f"| {pq.get(2024, float('nan')):,.0f} | {ratio(pq):.2f} | {ratio(pv):.2f} | {pq.get(2024, float('nan')) / pq.get(2015, float('nan')):.2f} |"  # noqa: E501
        )
    print("\n### e-bike（871160）世界計: 特需後／コロナ前（2017–19 平均。2015–16 は細分なし）")
    print(
        f"- 台数 {avg(eq, (2017, 2019)):,.0f} → {avg(eq, POST):,.0f}（比 {ratio(eq, pre=(2017, 2019)):.2f}）、金額 比 {ratio(ev, pre=(2017, 2019)):.2f}"  # noqa: E501
    )
    print(
        "- 2015 → 2024 の 8712 台数: "
        + f"{q[2024] / q[2015]:.2f} 倍（コロナ前から減り続けている: 2015→2019 {q[2019] / q[2015]:.2f}）"  # noqa: E501
    )

    # ---- H10 monthly
    print("\n## H10 主判定: 月次売上の 12 か月移動平均、ピーク月と最大落ち幅（2019-01 以降）")
    series12 = {c: trailing_mean(monthly(mo, c)) for c in ("kmc", "giant", "merida", "ideal_bike")}
    pdd = {c: peak_and_drawdown(s) for c, s in series12.items()}
    print(
        "| 企業 | 役割 | ピーク月 | 谷の月 | 最大落ち幅 | 直近月 | 直近／ピーク | 直近／2019-12 |"
    )
    print("|---|---|---|---|---|---|---|---|")
    roles = {
        "kmc": "部品（チェーン）",
        "giant": "完成車",
        "merida": "完成車",
        "ideal_bike": "完成車 OEM（補助）",
    }
    for c, d in pdd.items():
        s = series12[c]
        last = max(s) if s else ""
        print(
            f"| {c} | {roles[c]} | {d.peak_period} | {d.trough_period} | {d.drawdown:+.1%} | {last} "  # noqa: E501
            f"| {s[last] / d.peak_value:.2f} | {s[last] / s.get('2019-12', float('nan')):.2f} |"
        )
    verdict = judge_h10(pdd["kmc"], [pdd["giant"], pdd["merida"]])
    print(
        f"- 判定（KMC のピーク ≤ Giant・Merida のピーク、かつ KMC の落ち幅 > 両社平均）: **{verdict}**"  # noqa: E501
    )
    print("\n### 補助: 12 か月移動平均を使わない単月のピーク（季節性を含む）")
    for c in ("kmc", "giant", "merida"):
        d = peak_and_drawdown(monthly(mo, c))
        print(f"- {c}: ピーク {d.peak_period}、谷 {d.trough_period}、落ち幅 {d.drawdown:+.1%}")

    # ---- H10 annual
    print("\n## 頑健性")
    print(
        f"- H9 コロナ前を 2017–19 に: 台数比 {ratio(q, pre=(2017, 2019)):.2f}, 金額比 {ratio(v, pre=(2017, 2019)):.2f}; "  # noqa: E501
        f"特需後を 2024 年のみに: 台数比 {ratio(q, post=(2024, 2024)):.2f}, 金額比 {ratio(v, post=(2024, 2024)):.2f}"  # noqa: E501
    )
    for w in (6, 3):
        pd6 = {
            c: peak_and_drawdown(trailing_mean(monthly(mo, c), w))
            for c in ("kmc", "giant", "merida")
        }
        print(
            f"- H10 移動平均 {w} か月: "
            + ", ".join(
                f"{c} ピーク {d.peak_period} 落ち幅 {d.drawdown:+.1%}" for c, d in pd6.items()
            )
            + f" → {judge_h10(pd6['kmc'], [pd6['giant'], pd6['merida']])}"
        )
    pd20 = {
        c: peak_and_drawdown(trailing_mean(monthly(mo, c)), start="2020-01")
        for c in ("kmc", "giant", "merida")
    }
    print(
        "- H10 起点 2020-01: "
        + ", ".join(f"{c} ピーク {d.peak_period} 落ち幅 {d.drawdown:+.1%}" for c, d in pd20.items())
        + f" → {judge_h10(pd20['kmc'], [pd20['giant'], pd20['merida']])}"
    )
    for c in ("kmc", "giant", "merida"):
        s12 = series12[c]
        b19 = s12["2019-12"]
        y25 = max(v_ for k, v_ in s12.items() if k.startswith("2025"))
        print(
            f"- {c}: ピーク／2019-12 {pdd[c].peak_value / b19:.2f}, 谷／2019-12 {pdd[c].trough_value / b19:.2f}, 2025 年中の最大／2019-12 {y25 / b19:.2f}"  # noqa: E501
        )

    print("\n## 年次（2019 = 100）: 部品 vs 完成車 のピーク年と 2019 年比")
    annual = {c: annual_from_monthly(monthly(mo, c)) for c in ("kmc", "giant", "merida")}
    shimano = {
        int(r["fy"]): float(r["value_mn_jpy"])
        for r in sh.filter(
            (pl.col("key") == "bicycle_components") & (pl.col("metric") == "sales")
        ).iter_rows(named=True)
    }
    annual["shimano"] = shimano
    print("| 企業 | 2019 | ピーク年 | ピーク／2019 | 2023／2019 | 2024／2019 | 2025／2019 |")
    print("|---|---|---|---|---|---|---|")
    for c, a_ in annual.items():
        if 2019 not in a_:
            continue
        pk = max((y for y in a_ if y >= 2019), key=lambda y: a_[y])
        print(
            f"| {c} | {a_[2019]:,.0f} | {pk} | {a_[pk] / a_[2019]:.2f} | {a_.get(2023, float('nan')) / a_[2019]:.2f} "  # noqa: E501
            f"| {a_.get(2024, float('nan')) / a_[2019]:.2f} | {a_.get(2025, float('nan')) / a_[2019]:.2f} |"  # noqa: E501
        )

    fig_monthly(
        {"KMC（部品）": series12["kmc"], "Giant": series12["giant"], "Merida": series12["merida"]},
        fig_dir / "r5_h10_monthly_revenue.png",
        "台湾 3 社の月次売上（12 か月移動平均、2019-12 = 100。網掛けは特需期 2020–22）",
        "台湾 MOPS 月次営業収入（NT$ 千）",
    )
    fig_annual(
        {
            "台湾 8712 輸出 台数": q,
            "台湾 8712 輸出 金額 USD": v,
            "台湾 871160 輸出 台数": {y: x for y, x in eq.items() if y >= 2017},
        },
        fig_dir / "r5_h9_taiwan_exports.png",
        "台湾の完成車・e-bike 輸出（2019 = 100。網掛けは特需期 2020–22）",
        "指数（2019 = 100）",
        "UN Comtrade（reporter 490 = Other Asia, nes、世界計）",
    )
    fig_annual(
        {
            "シマノ 自転車部品（円）": shimano,
            "KMC（NT$）": annual["kmc"],
            "Giant（NT$）": annual["giant"],
            "Merida（NT$）": annual["merida"],
        },
        fig_dir / "r5_h10_annual_revenue.png",
        "部品と完成車の年次売上（2019 = 100。網掛けは特需期 2020–22）",
        "指数（2019 = 100）",
        "シマノ 有価証券報告書（EDINET）、台湾 MOPS 月次営業収入の年計",
    )
    print("\n図:", ", ".join(p.name for p in sorted(fig_dir.glob("r5_*.png"))))


if __name__ == "__main__":
    main()
