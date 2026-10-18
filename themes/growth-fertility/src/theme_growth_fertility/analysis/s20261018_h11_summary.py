"""H11 の note 記事（日本語・一般読者）用の図を生成する決定的スクリプト。

H11 レポート（reports/2026-10-18-h11-marriage-share.md）の数値を、同じ mart から
a20261018_h11_marriage_share の関数（`load`, `compute`, `asfr_by_year`）で**再計算**して
3 枚の図にする（新しい推定は行わない。H11 スクリプトは無変更。乱数・現在時刻は使わない）。

    uv run python -m theme_growth_fertility.analysis.s20261018_h11_summary \
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures/summary_h11]

フォント検出・保存規約は s20261005_summary と同じ（関数を import。PNG メタデータの Software を
落としてバイト再現。sha256 はフォント環境に依存する）。純粋ヘルパ（parts_pct, tfr_series,
share_series）は tests/test_summary_h11.py で検証する。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261018_h11_marriage_share as h11
from theme_growth_fertility.analysis import s20261005_summary as base

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
BLUE_RAMP, ORANGE, INK, MUTED = base.BLUE_RAMP, base.ORANGE, base.INK, base.MUTED

SRC_JP = (
    "出典: 国立社会保障・人口問題研究所『人口統計資料集 2026"
    "』表 4-9・4-11・6-23・6-24（PDL1.0）を加工"
    "　分析: socioscope"
)
SRC_OECD = (
    "出典: OECD Family Database（SF2.4 婚外出生割合・SF3.1 婚姻）、Eurostat、World Bank WDI、IPSS"
    "　分析: socioscope"
)


# ---------------------------------------------------------------- pure helpers (tested)
def parts_pct(d_ln_tfr: float, d_ln_cm: float) -> tuple[float, float, float]:
    """(marriage part, couple part, total) as log changes × 100 (≈ % change); parts sum to total."""
    return 100 * d_ln_cm, 100 * (d_ln_tfr - d_ln_cm), 100 * d_ln_tfr


def tfr_series(
    asfr: Mapping[int, Mapping[int, float]], y0: int, y1: int
) -> list[tuple[int, float]]:
    """(year, TFR = Σ ASFR 15–49) for years with all 35 single-year rates."""
    out: list[tuple[int, float]] = []
    for y in range(y0, y1 + 1):
        a = asfr.get(y, {})
        if all(k in a for k in range(15, 50)):
            out.append((y, sum(a[k] for k in range(15, 50))))
    return out


def share_series(mar: pl.DataFrame, age: str, y0: int, y1: int) -> list[tuple[int, float]]:
    """(census year, married share % of women) for one age class within [y0, y1]."""
    f = mar.filter(
        (pl.col("metric") == "married_share")
        & (pl.col("sex") == "F")
        & (pl.col("age_class") == age)
        & pl.col("year").is_between(y0, y1)
    ).sort("year")
    return [(int(y), float(v)) for y, v in f.select("year", "value").iter_rows()]


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    return base._plt()


def _note(fig: Any, text: str) -> None:
    fig.text(0.01, 0.045, text, fontsize=7.5, color=MUTED, ha="left")


def fig1_decomp(rows: Sequence[tuple[str, tuple[float, float, float]]], path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    for i, (_, (mar, cou, tot)) in enumerate(rows):
        ax.barh(
            i, mar, color=ORANGE, height=0.55, label="結婚の減少（有配偶割合）" if i == 0 else None
        )
        left = mar if (mar < 0) == (cou < 0) else 0.0
        ax.barh(
            i, cou, left=left, color=BLUE_RAMP[2], height=0.55,
            label="結婚した夫婦の側" if i == 0 else None,
        )  # fmt: skip
        ax.scatter(
            [tot],
            [i],
            marker="D",
            color=INK,
            zorder=3,
            label="出生率の変化（合計）" if i == 0 else None,
        )
        ax.annotate(
            f"合計 {tot:+.0f}%：結婚 {mar:+.0f}%、夫婦 {cou:+.0f}%",
            (min(mar, tot, mar + cou, 0), i), xytext=(-6, 0), textcoords="offset points",
            ha="right", va="center", fontsize=8, color=INK,
        )  # fmt: skip
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlim(-75, 25)
    ax.set_xlabel("変化（対数差 ×100、おおよそ % の変化）")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    base._style(ax)
    fig.suptitle(
        "期間の出生率で見ると低下はほぼ全部が結婚の減少、世代で見ると 4 割前後",
        fontsize=11, x=0.01, ha="left",
    )  # fmt: skip
    _note(
        fig,
        "上 3 本: 合計特殊出生率 = 結婚指数（年齢別出"
        "生率で重みを付けた有配偶割合）× 残り、国勢調査年。"
        "下 2 本（探索的）: 49 歳までに産んだ子ども数\n= 5"
        "0 歳時に結婚経験がある割合 × 結婚経験者 1 人当たりの数。"
        "期間の分解で夫婦の側がプラスなのは出産の高年齢化を含むため。",
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.93))
    base._save(fig, path, SRC_JP)


def fig2_series(
    shares: Mapping[str, list[tuple[int, float]]], tfr: list[tuple[int, float]], path: Path
) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
    ax = axes[0]
    for age, label, col in (
        ("25-29", "女性 25〜29 歳", ORANGE),
        ("30-34", "女性 30〜34 歳", BLUE_RAMP[3]),
    ):
        pts = shares[age]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=col, lw=2, label=label)
        for y, v in (pts[0], pts[-1]):
            ax.annotate(f"{v:.1f}%", (y, v), xytext=(0, 7), textcoords="offset points",
                        ha="center", fontsize=8, color=col)  # fmt: skip
    ax.set_ylim(0, 100)
    ax.set_ylabel("結婚している人の割合（%）")
    ax.set_title("結婚している女性の割合（国勢調査）", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8)
    base._style(ax)
    ax = axes[1]
    ax.plot([p[0] for p in tfr], [p[1] for p in tfr], color=INK, lw=1.8)
    d = dict(tfr)
    for y in (1970, 1980, 2005, 2015, 2020):
        if y in d:
            ax.annotate(f"{d[y]:.2f}", (y, d[y]), xytext=(0, 7), textcoords="offset points",
                        ha="center", fontsize=8, color=INK)  # fmt: skip
    ax.set_ylabel("合計特殊出生率")
    ax.set_title("合計特殊出生率（各年）", fontsize=9, loc="left")
    base._style(ax)
    fig.suptitle(
        "20 代後半で結婚している女性は 8 割から 3 割に、出生率は 2.1 から 1.3 に",
        fontsize=11, x=0.01, ha="left",
    )  # fmt: skip
    _note(
        fig,
        "有配偶 = 国勢調査の配偶関係（事実上の配偶を含む）。1970 年の出生率は沖縄県を含まない。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    base._save(fig, path, SRC_JP)


def fig3_country(
    items: Sequence[tuple[str, tuple[float, float, float, float] | None]], path: Path
) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    for i, (_, c) in enumerate(items):
        if c is None:
            continue
        col = ORANGE if c[2] > 0 or c[3] < 0 else BLUE_RAMP[2]
        ax.plot([c[2], c[3]], [i, i], color=col, lw=2)
        ax.scatter([c[0]], [i], color=col, s=34, zorder=3)
        ax.annotate(f"{c[0]:+.3f}", (c[0], i), xytext=(0, 7), textcoords="offset points",
                    ha="center", fontsize=8, color=col)  # fmt: skip
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([t for t, _ in items], fontsize=8.5)
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("婚姻率が 1 標準偏差多く増えたときの出生率の変化（5 年差分）")
    base._style(ax)
    fig.suptitle(
        "婚外出生の多い国でも、婚姻率と出生率は一緒に動いている",
        fontsize=11, x=0.01, ha="left",
    )  # fmt: skip
    _note(
        fig,
        "1990〜2025 年の 5 年差分、国と期間の固定効果、初婚年齢の変化を調整。線は 95% 信頼区間"
        "（オレンジ = 0 を含まない）。4 か国の区間は不確か。",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.92))
    base._save(fig, path, SRC_OECD)


def run(data_dir: Path, fig_dir: Path) -> list[tuple[str, str]]:
    font = base.setup_matplotlib()
    print(f"font: {font}")
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = h11.load(data_dir)
    res = h11.compute(d)
    caps: list[tuple[str, str]] = []

    dm = {(x.y0, x.y1): x for x in res.j1["main"]}
    rows: list[tuple[str, tuple[float, float, float]]] = [
        (f"{a}→{b} 年（期間）", parts_pct(dm[(a, b)].d_ln_tfr, dm[(a, b)].d_ln_cm))
        for a, b in ((1980, 2020), (1980, 2000), (2000, 2020))
    ]
    coh = {c0.cohort: (c0, c1) for c0, c1 in res.cohort_pairs}
    for cohort in (1950, 1960):
        c0, c1 = coh[cohort]
        rows.append(
            (
                f"{c0.cohort}→{c1.cohort} 年生まれ（世代）",
                parts_pct(math.log(c1.ctfr / c0.ctfr), math.log(c1.ever / c0.ever)),
            )
        )
    fig1_decomp(rows, fig_dir / "h11s01_decomposition.png")
    m = dm[(1980, 2020)]
    c50 = coh[1950]
    caps.append(
        (
            "h11s01_decomposition.png",
            f"出生率は 1980→2020 年に {m.tfr0:.2f} → {m.tfr1:.2f}"
            f"。結婚指数の低下（{rows[0][1][0]:+.0f}%）"
            f"は出生率の低下（{rows[0][1][2]:+.0f}%）より大"
            f"きく、期間の分解では低下の {m.s_m:.0%} が結婚の減少。"
            "世代で見ると（1950→1970 年生まれ、探索的）49 歳までの子ども数"
            f" {c50[0].ctfr:.2f} → {c50[1].ctfr:.2f}"
            f" のうち結婚経験の減少は {h11.cohort_share(*c50):.0%}。"
            "期間の分解が 100% を超えるのは出産年齢の後ろ倒しによる見かけの可能性が高い"
            "（直接のテンポ調整はしていない）。",
        )
    )

    shares = {a: share_series(d["mar"], a, 1970, 2020) for a in ("25-29", "30-34")}
    tfr = tfr_series(h11.asfr_by_year(d["jp_order"]), 1970, 2020)
    fig2_series(shares, tfr, fig_dir / "h11s02_married_share_tfr.png")
    t = dict(tfr)
    caps.append(
        (
            "h11s02_married_share_tfr.png",
            f"結婚している女性の割合は 25〜29 歳で {shares['25-29'][0][1]:.1f}%（1970）→ "
            f"{shares['25-29'][-1][1]:.1f}%（2020）、30〜34 歳で {shares['30-34'][0][1]:.1f}% → "
            f"{shares['30-34'][-1][1]:.1f}%。合計特殊出生率は {t[1970]:.2f} → {t[2020]:.2f}。",
        )
    )

    j3 = res.j3["main (5y, <25%)"]
    g = res.j3_groups["main (5y, <25%)"]

    def cmr_of(k: str) -> tuple[float, float, float, float] | None:
        f = j3.get(k)
        return f.coefs["cmr"] if f else None

    items = [
        (f"婚外出生が少ない国（25% 未満、{len(g['low'])} か国）", cmr_of("low")),
        (f"婚外出生が多い国（40% 以上、{len(g['high'])} か国）", cmr_of("high")),
        ("19 か国すべて", cmr_of("all")),
    ]
    fig3_country(items, fig_dir / "h11s03_country_marriage_coef.png")
    lo, hi = cmr_of("low"), cmr_of("high")
    assert lo is not None and hi is not None
    caps.append(
        (
            "h11s03_country_marriage_coef.png",
            f"婚姻率の係数は婚外出生が少ない国（{'・'.join(g['low'])}）で {lo[0]:+.3f}"
            f"（95% 区間 {lo[2]:+.3f}〜{lo[3]:+.3f}"
            "）、多い国（北欧・フランス・南欧など 13 か国）で "
            f"{hi[0]:+.3f}（{hi[2]:+.3f}〜{hi[3]:+.3f}）。予測と違い、婚外出生の多い国でも結びつきは切れていない。",
        )
    )

    lines = ["# H11 記事用図のキャプション", "", SRC_JP, "", SRC_OECD, ""]
    lines += [f"- `{f}`: {c}" for f, c in caps]
    (fig_dir / "captions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f, cap in caps:
        print(f"caption {f}: {cap}")
    return caps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument(
        "--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures" / "summary_h11"
    )
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
