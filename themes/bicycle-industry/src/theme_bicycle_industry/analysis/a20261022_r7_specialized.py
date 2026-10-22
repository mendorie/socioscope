"""R7: Specialized の特需後（H14）— Merida の持分法開示と SBC 集団向け売上で読む。

事前登録（design/themes/bicycle-industry.md、2026-10-22）:
  H14: Specialized（非上場、Merida が 35% を持分法）の利益は特需後に赤字、または特需期の 3 割以下。
    (a) Merida が認識した持分法損益（損益表 7370/7770、関連企業全体）が FY2023–2025 の各年で
        損失、または FY2022 の利益の 30% 以下なら整合。1 年でも 30% を超える利益なら不支持。
    (b) 記述: Merida の SBC 集団向け売上の FY2022 → FY2025 変化率と、Merida 全体の売上変化率。
        SBC 向けの落ち幅が全体より大きければ「Specialized の在庫調整が Merida を直撃」と整合。
    局面: 特需期 = FY2022 のみ（FY2021 以前は取得不可）、特需後 = FY2023–2025。

決定的スクリプト。入力は data/marts/merida_specialized.parquet（NT$ 千）。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/\\
        a20261022_r7_specialized.py [--data-dir data] [--fig-dir …]

純粋ヘルパ（judge_h14a, change, judge_h14b）は tests/test_analysis_r7.py で検証する。
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
BOOM_FY = 2022
POST_FYS = (2023, 2024, 2025)
THRESHOLD = 0.3


# ---- pure helpers -------------------------------------------------------------------------------


def judge_h14a(
    share: Mapping[int, float],
    boom_fy: int = BOOM_FY,
    post: Sequence[int] = POST_FYS,
    threshold: float = THRESHOLD,
) -> str:
    """各特需後年が 損失 または 特需期利益 × threshold 以下 なら整合。1 年でも超えれば不支持。"""
    if boom_fy not in share or any(fy not in share for fy in post):
        return "判定不能"
    boom = share[boom_fy]
    if boom <= 0:
        return "判定不能"
    for fy in post:
        if share[fy] > boom * threshold:
            return "不支持"
    return "整合"


def change(series: Mapping[int, float], a: int, b: int) -> float:
    if a not in series or b not in series or series[a] == 0:
        return math.nan
    return series[b] / series[a] - 1


def judge_h14b(sbc_change: float, total_change: float) -> str:
    """SBC 向けの落ち幅が全体より大きい（より負）なら整合、そうでなければ不支持。"""
    if math.isnan(sbc_change) or math.isnan(total_change):
        return "判定不能"
    return "整合" if sbc_change < total_change else "不支持"


def by_fy(m: pl.DataFrame, metric: str) -> dict[int, float]:
    sub = m.filter(pl.col("metric") == metric)
    return {int(r["fy"]): float(r["value_ntd_k"]) for r in sub.iter_rows(named=True)}


# ---- figures -------------------------------------------------------------------------------------


def fig_share(share: Mapping[int, float], path: Path, source: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    fys = sorted(share)
    vals = [share[fy] / 1e6 for fy in fys]
    colors = [SERIES[0] if v >= 0 else SERIES[1] for v in vals]
    ax.bar(fys, vals, color=colors, width=0.6)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    for fy, v in zip(fys, vals, strict=True):
        ax.annotate(
            f"{v:+.2f}",
            (fy, v),
            textcoords="offset points",
            xytext=(0, 4 if v >= 0 else -10),
            ha="center",
            fontsize=8,
            color=INK,
        )
    ax.axvspan(BOOM_FY - 0.5, BOOM_FY + 0.5, color="#f2f2f2", zorder=0)
    ax.margins(y=0.15)
    ax.set_xticks(fys)
    ax.set_ylabel("Merida が認識した持分法損益（NT$ 十億）", fontsize=8, color=INK)
    ax.set_title(
        "持分法による関連企業損益（SBC を含む）: 特需期 FY2022 → 特需後 FY2023–25",
        fontsize=10,
        color=INK,
        loc="left",
    )
    _style(ax)
    fig.text(0.01, 0.01, f"出典: {source}", fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_index(data: Mapping[str, Mapping[int, float]], path: Path, source: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for (name, s), color in zip(data.items(), SERIES, strict=False):
        fys = sorted(s)
        base = s[BOOM_FY]
        ys = [s[fy] / base * 100 for fy in fys]
        ax.plot(fys, ys, color=color, linewidth=2, marker="o", markersize=3.5, label=name)
        ax.annotate(
            f"{ys[-1]:.0f}",
            (fys[-1], ys[-1]),
            textcoords="offset points",
            xytext=(6, -3),
            fontsize=8,
            color=INK,
        )
    ax.axhline(100, color=MUTED, linewidth=0.8, linestyle="--")
    ax.set_xticks(sorted(next(iter(data.values()))))
    ax.set_xlim(BOOM_FY - 0.3, POST_FYS[-1] + 0.6)
    ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    ax.set_ylabel("FY2022 = 100", fontsize=8, color=INK)
    ax.set_title(
        "Merida の売上: 全体 vs SBC 集団向け、SBC 帳簿価額",
        fontsize=10,
        color=INK,
        loc="left",
        pad=18,
    )
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
    m = pl.read_parquet(args.data_dir / "marts" / "merida_specialized.parquet")
    share = by_fy(m, "equity_method_share")
    rev = by_fy(m, "revenue")
    sbc_sales = by_fy(m, "sbc_group_sales")
    carry = by_fy(m, "sbc_carrying_amount")
    assoc = by_fy(m, "associates_carrying_total")
    others = {fy: assoc[fy] - carry[fy] for fy in assoc}
    src = "Merida Industry 連結財務報告 FY2023–2025 Q4（merida_ir）"

    print("# R7 Specialized の特需後（H14）（2026-10-22）")
    print(f"- mart: marts/merida_specialized（{m.height} 行、NT$ 千、FY{min(rev)}–{max(rev)}）")
    print("\n## 表: Merida の開示値（NT$ 百万）")
    print(
        "| FY | 売上（全体） | SBC 集団向け売上 | SBC 向け比率 "
        "| 持分法損益（関連企業） | SBC 帳簿価額 |"
    )
    print("|---|---|---|---|---|---|")
    for fy in sorted(rev):
        print(
            f"| {fy} | {rev[fy] / 1e3:,.0f} | {sbc_sales[fy] / 1e3:,.0f} | "
            f"{sbc_sales[fy] / rev[fy]:.1%} | {share[fy] / 1e3:+,.0f} | {carry[fy] / 1e3:,.0f} |"
        )

    print("\n## H14 (a) 主判定: 持分法損益 FY2023–25 vs FY2022 の 30%")
    boom = share[BOOM_FY]
    print(
        f"- FY{BOOM_FY}（特需期）: {boom / 1e3:+,.0f} 百万 → "
        f"30% 閾値 {boom * THRESHOLD / 1e3:+,.0f} 百万"
    )
    for fy in POST_FYS:
        v = share[fy]
        state = "損失" if v <= 0 else f"利益、FY2022 比 {v / boom:.1%}"
        print(f"- FY{fy}: {v / 1e3:+,.0f} 百万（{state}）")
    print(f"- 判定: **{judge_h14a(share)}**")
    print(f"- FY2024 の損失は FY2022 の利益の {-share[2024] / boom:.1f} 倍。")
    print(
        "\n### 事前登録からの逸脱: 判定に使った行は SBC 単独ではなく関連企業全体（SBC 以外の比重）"
    )
    print(
        "| FY | 関連企業 帳簿価額 合計 | うち SBC | SBC 比率 | SBC 以外 | SBC 以外の前年差 "
        "| 判定が覆るのに要する SBC 以外の損失 | 同 ÷ SBC 以外の帳簿価額 |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for fy in sorted(assoc):
        diff = f"{(others[fy] - others[fy - 1]) / 1e3:+,.0f}" if fy - 1 in others else "–"
        if fy in POST_FYS:
            need = (
                share[fy] - boom * THRESHOLD
            )  # SBC 以外の損益がこれより小さい（負に大きい）と SBC 単独が閾値超え
            flip = (
                f"{need / 1e3:,.0f} 百万 の損失"
                if need < 0
                else "不可能（合計が閾値以下でも SBC 単独は上回りうる）"
            )
            flip = f"{-need / 1e3:,.0f} 百万 以上の損失" if need < 0 else "（既に閾値超え）"
            ratio = f"{-need / others[fy]:.0%}" if need < 0 else "–"
        else:
            flip, ratio = "–", "–"
        print(
            f"| {fy} | {assoc[fy] / 1e3:,.0f} | {carry[fy] / 1e3:,.0f} "
            f"| {carry[fy] / assoc[fy]:.1%} "
            f"| {others[fy] / 1e3:,.0f} | {diff} | {flip} | {ratio} |"
        )
    print(
        "- SBC 以外の関連企業（欧州販社など 6 社）の帳簿価額は合計の 2% 未満。持分法で認識する"
        "損失は帳簿価額（長期持分を含む）が上限（IAS 28）なので、FY2023・2024（帳簿価額の数倍の"
        "損失が必要）は覆らない。FY2025 は SBC 以外が期末帳簿価額の 3 割超（期首比では約 4 割）の"
        "損失を出していれば覆りうるが、"
        "同年の SBC 以外の帳簿価額は増えている（配当・為替を含む粗い目安）。"
    )
    print(
        "- 注: 損益表の行は SBC を含む関連企業全体の持分。FY2024 の損失と同年の帳簿価額の減少"
        f"（{(carry[2024] - carry[2023]) / 1e3:+,.0f} 百万）を併記。"
        "抽出した本文に SBC に関する減損の注記は見つからなかった（語の検索）が、"
        "SBC 側の一時要因は分からない。"
    )

    print("\n## H14 (b) 記述: SBC 集団向け売上 vs 全体売上の変化（FY2022 → FY2025）")
    sc, tc = change(sbc_sales, BOOM_FY, 2025), change(rev, BOOM_FY, 2025)
    print(
        f"- FY2025 の水準（FY2022 = 100）: "
        f"SBC 向け売上 {sbc_sales[2025] / sbc_sales[BOOM_FY]:.0%}、"
        f"全体 {rev[2025] / rev[BOOM_FY]:.0%}、SBC 帳簿価額 {carry[2025] / carry[BOOM_FY]:.0%}"
    )
    print(
        f"- 減少額（FY2022 → FY2025、百万）: "
        f"SBC 向け {(sbc_sales[2025] - sbc_sales[BOOM_FY]) / 1e3:+,.0f}、"
        f"全体 {(rev[2025] - rev[BOOM_FY]) / 1e3:+,.0f}"
    )
    oc = change({k: rev[k] - sbc_sales[k] for k in rev}, BOOM_FY, 2025)
    print(f"- SBC 集団向け: {sc:+.1%}、全体: {tc:+.1%}、全体のうち SBC 以外: {oc:+.1%}")
    print(f"- 判定（SBC 向けの落ち幅 > 全体 で整合）: **{judge_h14b(sc, tc)}**")
    print("- 年ごとの変化（前年比）:")
    for fy in POST_FYS:
        a_, b_ = change(sbc_sales, fy - 1, fy), change(rev, fy - 1, fy)
        print(f"  - FY{fy}: SBC 向け {a_:+.1%}、全体 {b_:+.1%}")

    print("\n## 頑健性")
    for thr in (0.2, 0.5):
        print(f"- 閾値 {thr:.0%}: (a) {judge_h14a(share, threshold=thr)}")
    print(f"- 特需後を FY2023–24 に限る: (a) {judge_h14a(share, post=(2023, 2024))}")
    s24, t24 = change(sbc_sales, BOOM_FY, 2024), change(rev, BOOM_FY, 2024)
    j24 = judge_h14b(s24, t24)
    print(f"- (b) を FY2022 → FY2024 で: SBC 向け {s24:+.1%}、全体 {t24:+.1%} → {j24}")
    s25, t25 = change(sbc_sales, 2023, 2025), change(rev, 2023, 2025)
    print(f"- (b) を FY2023 → FY2025（底からの回復）で: SBC 向け {s25:+.1%}、全体 {t25:+.1%}")

    fig_share(share, args.fig_dir / "r7_equity_share.png", src)
    fig_index(
        {"Merida 売上（全体）": rev, "SBC 集団向け売上": sbc_sales, "SBC 帳簿価額": carry},
        args.fig_dir / "r7_sbc_index.png",
        src,
    )
    print(f"\nfigures: {args.fig_dir / 'r7_equity_share.png'}, {args.fig_dir / 'r7_sbc_index.png'}")


if __name__ == "__main__":
    main()
