"""H8 の note 記事（日本語・一般読者）用の図を生成する決定的スクリプト。

H8 レポート（reports/2026-10-17-h8-mechanisms.md）の数値を、同じ mart から
a20261017_h8_mechanisms の関数で**再計算**して 11 枚の図にする
（h8s07 は H8b レポートの X1・X5 を a20261018_h8b_within_group の関数で、h8s08・h8s09 は
H8c レポートの Y1・Y2 を a20261018_h8c_education_cost の関数で、h8s10・h8s11 は H8d レポートの
Z1/Z2/Z6・Z5 を a20261018_h8d_gender_equity の関数で再計算）
（新しい推定は行わない。
T2 の仕様依存の 2 本は H8 の探索的 E4・E7 と同じ式を H1 の `fit` で再実行する。
乱数・現在時刻は使わない）。H8 の関数は途中経過を stdout に出す。

    uv run python -m theme_growth_fertility.analysis.s20261017_h8_summary \
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures/summary_h8]

フォント検出・保存規約は s20261005_summary と同じ（関数を import。PNG メタデータの Software を
落としてバイト再現。sha256 はフォント環境に依存する）。純粋ヘルパ（split_share, median_by_index,
scorecard_rows, spec_rows, rise_summary, country_ja, ge_label）は tests/test_summary_h8.py で
検証する。
"""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261017_h8_mechanisms as h8
from theme_growth_fertility.analysis import a20261018_h8b_within_group as h8b
from theme_growth_fertility.analysis import a20261018_h8c_education_cost as h8c
from theme_growth_fertility.analysis import a20261018_h8d_gender_equity as h8d
from theme_growth_fertility.analysis import s20261005_summary as base
from theme_growth_fertility.analysis.a20261004_h1_income_tfr import fit

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]

SRC_DHS = "出典: The DHS Program Indicator Data API（ICF）/ World Bank WDI　分析: socioscope"
SRC_WDI = "出典: World Bank WDI（CC BY 4.0、初婚年齢は国連 World Marriage Data）　分析: socioscope"
BLUE_RAMP, ORANGE, INK, MUTED = base.BLUE_RAMP, base.ORANGE, base.INK, base.MUTED
EDU_JA = {"No education": "教育なし", "Primary": "初等", "Secondary": "中等", "Higher": "高等"}
MECH_JA = {
    "M1": "子どもの死亡率の低下（保険としての多産が要らなくなる）",
    "M2": "結婚が遅れる・結婚している割合が下がる",
    "M3": "女子教育で「望む子ども数」が下がる",
    "M4": "死亡率が下がると教育による差が広がる",
    "M5": "望まない出生の減少（家族計画）が主役",
}
T6_JA = {
    "d_ln_u5": "子どもの死亡率（対数）",
    "d_sec": "女子の中等就学率",
    "d_smam": "女性の平均初婚年齢",
    "d_ln_gdp": "一人当たり GDP（対数）",
}
SRC_OECD = (
    "出典: OECD Education at a Glance（UOE finance / LSO earnings）/ World Bank WDI"
    "　分析: socioscope"
)
COUNTRY_JA = {
    "JPN": "日本",
    "KOR": "韓国",
    "DNK": "デンマーク",
    "FIN": "フィンランド",
    "NOR": "ノルウェー",
    "SWE": "スウェーデン",
}
GE_LABEL_JA = {
    **COUNTRY_JA,
    "ITA": "イタリア",
    "ESP": "スペイン",
    "USA": "米国",
    "GBR": "英国",
}
SRC_SDG = "出典: 国連統計部 SDG Global Database（SL_DOM_TSPD）/ World Bank WDI　分析: socioscope"
SRC_KR = (
    "出典: 韓国 教育部「2025年 初中高 私教育費調査 結果」報道資料（KOGL 第1類型）/ World Bank WDI"
    "　分析: socioscope"
)
NORDIC_MARKER = {"DNK": "o", "FIN": "s", "NOR": "^", "SWE": "D"}
Coef = tuple[float, float, float, float]


# ---------------------------------------------------------------- pure helpers (tested)
def split_share(part: float, total: float) -> tuple[float, float]:
    """(part / total, 1 − part / total); total must be non-zero."""
    if total == 0:
        raise ValueError("total must be non-zero")
    s = part / total
    return s, 1.0 - s


def median_by_index(rows: Sequence[Mapping[str, Any]], key: str) -> list[float]:
    """Element-wise median of the equal-length lists rows[i][key]."""
    if not rows:
        return []
    k = len(rows[0][key])
    return [float(statistics.median(r[key][i] for r in rows)) for i in range(k)]


def scorecard_rows(verdicts: Mapping[str, str]) -> list[tuple[str, str, str]]:
    """(M, Japanese name, Japanese verdict) in M1..M5 order."""
    return [(m, MECH_JA[m], h8.VERDICT_JA[verdicts[m]]) for m in sorted(MECH_JA) if m in verdicts]


def spec_rows(specs: Sequence[tuple[str, Coef]]) -> list[tuple[str, float, float, float, bool]]:
    """(label, b, lo, hi, CI excludes 0) from (label, (b, se, lo, hi))."""
    return [(lab, c[0], c[2], c[3], c[2] > 0 or c[3] < 0) for lab, c in specs]


def country_ja(iso3: str) -> str | None:
    """Japanese name for the countries labelled in h8s09 (Japan, Korea, Nordic 4); else None."""
    return COUNTRY_JA.get(iso3)


def ge_label(iso3: str) -> str | None:
    """Japanese name for the countries labelled in h8s10 (Japan, Korea, Nordic 4, Italy, Spain,
    US, UK); else None."""
    return GE_LABEL_JA.get(iso3)


def rise_summary(deltas: Sequence[float]) -> tuple[float, int, int]:
    """(median change, number of countries with a rise (> 0), number of countries)."""
    if not deltas:
        raise ValueError("no changes")
    return statistics.median(deltas), sum(v > 0 for v in deltas), len(deltas)


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    import matplotlib.pyplot as plt

    return plt


def _share_bar(ax: Any, left: tuple[float, str], right: tuple[float, str], xlabel: str) -> None:
    (a, la), (b, lb) = left, right
    ax.barh([0], [a], color=BLUE_RAMP[3], height=0.5)
    ax.barh([0], [b], left=[a], color=ORANGE, height=0.5)
    ax.text(a / 2, 0, f"{la}\n{a:.0%}", ha="center", va="center", color="white", fontsize=10.5)
    ax.text(a + b / 2, 0, f"{lb}\n{b:.0%}", ha="center", va="center", color="white", fontsize=9.5)
    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel(xlabel)
    base._style(ax)


def _note(fig: Any, text: str) -> None:
    fig.text(0.01, 0.045, text, fontsize=7.5, color=MUTED, ha="left")


def fig1_wanted(t1: h8.T1Result, path: Path) -> None:
    plt = _plt()
    p = t1.pairs
    d_tfr = float(p["d_tfr"].sum())
    d_w = float(p["d_wanted_tfr"].sum())
    sw, su = split_share(d_w, d_tfr)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.6), gridspec_kw={"width_ratios": [1, 1.1]})
    _share_bar(ax, (sw, "望む出生の低下"), (su, "望まない\n出生の減少"),
               "出生率（TFR）の低下の合計に占める割合")  # fmt: skip
    ax.set_title(f"(a) 低下の合計 {d_tfr:+.1f} 人のうち、望む出生の低下が {d_w:+.1f} 人",
                 fontsize=10, loc="left")  # fmt: skip
    xs, ys = p["d_tfr"].to_list(), p["d_wanted_tfr"].to_list()
    ax2.scatter(xs, ys, s=12, color=BLUE_RAMP[2], alpha=0.75)
    lo = min(min(xs), min(ys)) - 0.2
    ax2.plot([lo, 0], [lo, 0], color=MUTED, ls="--", lw=0.8, label="すべて望む出生の低下（y = x）")
    ax2.axhline(0, color=MUTED, lw=0.6)
    ax2.set_xlabel("TFR の変化（2 回の調査の間、子ども数/女性）")
    ax2.set_ylabel("望む出生（wanted TFR）の変化")
    ax2.set_title("(b) 調査の組ごと（点 1 つ = 同じ国の 2 回の調査）", fontsize=10, loc="left")
    ax2.legend(frameon=False, fontsize=8, loc="upper left")
    base._style(ax2)
    fig.suptitle(
        f"出生率の低下の約 4 分の 3 は「望む子ども数」の低下"
        f"（{t1.n_pairs} 組・{t1.n_countries} か国）",
        fontsize=11, x=0.01, ha="left",
    )  # fmt: skip
    _note(fig, "同じ国で 3 年以上離れた DHS 調査の組のうち、TFR が下がったもの。"
               "望まない出生 = TFR − wanted TFR（望んだ数を超えた出生）。")  # fmt: skip
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    base._save(fig, path, SRC_DHS)


def fig2_edu_gradient(t4: h8.T4Result, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    groups = ("Primary", "Secondary", "Higher")
    width = 0.36
    series = (
        (t4.est_w, "望む出生（wanted TFR）", BLUE_RAMP[3]),
        (t4.est_u, "望まない出生（TFR − wanted）", ORANGE),
    )
    for j, (est, lab, col) in enumerate(series):
        xs = [i + (j - 0.5) * width for i in range(len(groups))]
        cs = [est.coefs[h8.EDU_DUMMY[g]] for g in groups]
        bs = [c[0] for c in cs]
        err = [[c[0] - c[2] for c in cs], [c[3] - c[0] for c in cs]]
        ax.bar(xs, bs, width=width, color=col, label=lab)
        ax.errorbar(xs, bs, yerr=err, fmt="none", ecolor=INK, elinewidth=0.9, capsize=3)
        for x, c in zip(xs, cs, strict=True):
            ax.text(x, c[2] - 0.05, f"{c[0]:+.2f}", ha="center", va="top", fontsize=8.5)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([f"{EDU_JA[g]}教育" for g in groups])
    ax.set_ylim(min(t4.h_w[2], t4.h_u[2]) - 0.45, 0.2)
    ax.set_ylabel("「教育なし」の女性との差（子ども数/女性）\n棒: 推定値、線: 95% 信頼区間")
    ax.set_title(
        f"同じ調査の中で比べると、学歴による差は主に「望む数」に出る\n"
        f"（中等教育: 望む出生 {t4.g_w[0]:+.2f}、望まない出生 {t4.g_u[0]:+.2f}）",
        fontsize=10.5, loc="left",
    )  # fmt: skip
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    base._style(ax)
    _note(fig, f"{t4.est_w.n:,} セル（調査 × 学歴）・{t4.frame['survey_id'].n_unique()} 調査・"
               f"{t4.est_w.countries} か国。調査ごとの固定効果、国クラスタ標準誤差。")  # fmt: skip
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    base._save(fig, path, SRC_DHS)


def fig3_kitagawa(
    two: Sequence[Mapping[str, Any]], four: Sequence[Mapping[str, Any]], path: Path
) -> tuple[float, list[float]]:
    plt = _plt()
    rate = sum(r["rate"] for r in two)
    comp = sum(r["comp"] for r in two)
    sc, sr = split_share(comp, rate + comp)
    med = median_by_index(four, "d_rates")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.8), gridspec_kw={"width_ratios": [1, 1.2]})
    _share_bar(ax, (sr, "同じ学歴の中で\n望む数が下がった"), (sc, "学歴の高い\n女性が増えた"),
               "望む出生（wanted TFR）の低下の合計に占める割合")  # fmt: skip
    ax.set_title(f"(a) 望む数の低下の内訳（{len(two)} か国）", fontsize=10, loc="left")
    labs = [EDU_JA[e] for e in h8.EDU]
    cols = [BLUE_RAMP[4], BLUE_RAMP[3], BLUE_RAMP[1], BLUE_RAMP[0]]
    ax2.bar(labs, med, color=cols)
    for i, v in enumerate(med):
        ax2.text(i, v - 0.02, f"{v:+.2f}", ha="center", va="top", fontsize=10.5)
    ax2.axhline(0, color=MUTED, lw=0.8)
    ax2.set_ylim(min(med) - 0.2, 0.1)
    ax2.set_ylabel("最初→最後の調査での望む出生の変化\n（国の中央値、子ども数/女性）")
    ax2.set_title(f"(b) 学歴群ごとの変化（{len(four)} か国）", fontsize=10, loc="left")
    base._style(ax2)
    fig.suptitle(
        "望む子ども数の低下は、学歴の高い女性が増えたことよりも、学歴の低い女性の中で起きた",
        fontsize=11, x=0.01, ha="left",
    )  # fmt: skip
    _note(fig, "TFR が下がった国の最初と最後の DHS 調査（8 年以上離れたもの）の Kitagawa 分解"
               "（探索的）。(a) は 2 群（初等以下 / 中等以上、構成は中等以上の女性の割合）、"
               "(b) は 4 群。")  # fmt: skip
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    base._save(fig, path, SRC_DHS)
    return sc, med


def fig4_marriage(t3: h8.T3Result, path: Path) -> None:
    plt = _plt()
    gaps = t3.gaps.filter(pl.col("gap_sec").is_not_null())["gap_sec"].to_list()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.6), gridspec_kw={"width_ratios": [1.2, 1]})
    ax.hist(gaps, bins=24, color=BLUE_RAMP[2], edgecolor="white")
    ax.axvline(t3.median_sec, color=ORANGE, ls="--", lw=1.2)
    ax.axvline(2.0, color=INK, ls=":", lw=1)
    top = ax.get_ylim()[1]
    ax.text(t3.median_sec, top * 0.97, f" 中央値 {t3.median_sec:+.1f} 年", fontsize=9, va="top",
            color=ORANGE)  # fmt: skip
    ax.text(2.0, top * 0.80, f"+2 年以上: {t3.share_ge2:.0%} ", fontsize=9, va="top", ha="right")
    ax.set_xlabel("初婚年齢の差: 中等教育の女性 − 教育なしの女性（年）")
    ax.set_ylabel("調査の数")
    ax.set_title(f"(a) 学歴が高い女性ほど遅く結婚する（{t3.n_afm} 調査）", fontsize=10, loc="left")
    base._style(ax)
    sm, rest = split_share(float(t3.decomp["d_ln_cm"].sum()), float(t3.decomp["d_ln_tfr"].sum()))
    ax2.bar(["結婚している\n割合の低下", "結婚の中での\n出生の低下"], [sm, rest],
            color=[ORANGE, BLUE_RAMP[3]])  # fmt: skip
    for i, v in enumerate((sm, rest)):
        ax2.text(i, v + 0.01, f"{v:.0%}", ha="center", va="bottom", fontsize=11)
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("ln TFR の低下の合計に占める割合")
    ax2.set_title(f"(b) 出生率の低下の内訳（{t3.n_cm} か国）", fontsize=10, loc="left")
    base._style(ax2)
    fig.suptitle(
        f"学歴が高いほど結婚は遅く、結婚している割合の低下は出生率の低下の約 3 分の 1（{sm:.0%}）",
        fontsize=11, x=0.01, ha="left",
    )  # fmt: skip
    _note(fig, "(b) は Bongaarts の結婚指数（年齢別の結婚・同棲の割合）による分解。"
               "TFR が下がった国の最初と最後の調査（8 年以上離れたもの）。")  # fmt: skip
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    base._save(fig, path, SRC_DHS)


def fig5_mortality(
    rows: Sequence[tuple[str, float, float, float, bool]], st: pl.DataFrame, path: Path
) -> tuple[int, float]:
    plt = _plt()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.6, 4.8), gridspec_kw={"width_ratios": [1.1, 1]})
    for i, (_, b, lo, hi, sig) in enumerate(rows):
        col = ORANGE if sig else BLUE_RAMP[2]
        ax.plot([lo, hi], [i, i], color=col, lw=2.2)
        ax.plot([b], [i], "o", color=col)
        ax.text(b, i - 0.2, f"{b:+.2f} [{lo:+.2f}, {hi:+.2f}]", ha="center", fontsize=8.5)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_ylim(len(rows) - 0.5, -0.7)
    ax.set_xlabel("子どもの死亡率（対数）が 1 単位高いときの TFR の差\n"
                  "（同じ国の中、点: 推定値、線: 95% 信頼区間）")  # fmt: skip
    ax.set_title("(a) 死亡率と出生率の関連は、仕様によって変わる", fontsize=10, loc="left")
    base._style(ax)
    f = st.drop_nulls(["tfr", "ideal_children", "u5_5"])
    low = f.filter(pl.col("u5_5") < 40)
    high = f.filter(pl.col("u5_5") >= 40)
    below = [t < i for t, i in zip(low["tfr"].to_list(), low["ideal_children"].to_list(),
                                   strict=True)]  # fmt: skip
    share = sum(below) / len(below)
    ax2.scatter(high["ideal_children"], high["tfr"], s=9, color=BLUE_RAMP[0], alpha=0.6,
                label=f"死亡率 40 以上（{high.height} 調査）")  # fmt: skip
    ax2.scatter(low["ideal_children"], low["tfr"], s=15, color=ORANGE, alpha=0.85,
                label=f"死亡率 40 未満（{low.height} 調査）")  # fmt: skip
    m = max(max(f["ideal_children"].to_list()), max(f["tfr"].to_list())) + 0.3
    ax2.plot([1, m], [1, m], color=MUTED, lw=0.8, ls="--", label="TFR = 理想の子ども数")
    ax2.set_xlabel("理想の子ども数（女性の平均）")
    ax2.set_ylabel("TFR（子ども数/女性）")
    ax2.set_title(f"(b) 死亡率が低い調査の {share:.0%} で、出生は理想より少ない", fontsize=10,
                  loc="left")  # fmt: skip
    ax2.legend(frameon=False, fontsize=8, loc="upper left")
    base._style(ax2)
    _note(fig, "死亡率 = 5 歳未満死亡率（出生千対、調査前 5 年）。"
               "(a) 上段が事前に決めた仕様（国の固定効果"
               "＋年トレンド＋中等以上の女性の割合）、下 2 段は探索的。"
               "橙 = 95% CI が 0 を含まない。")  # fmt: skip
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    base._save(fig, path, SRC_DHS)
    return low.height, share


def fig6_stage2(s2: h8.T6Stage, verdicts: Mapping[str, str], path: Path) -> None:
    plt = _plt()
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(11.0, 4.8), gridspec_kw={"width_ratios": [1, 1.15]}
    )
    names = list(h8.T6_VARS)
    for i, k in enumerate(names):
        b, _, lo, hi = s2.coefs[k]
        col = ORANGE if (lo > 0 or hi < 0) else BLUE_RAMP[2]
        ax.plot([lo, hi], [i, i], color=col, lw=2.2)
        ax.plot([b], [i], "o", color=col)
        ax.text(b, i - 0.2, f"{b:+.3f}", ha="center", fontsize=9)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([T6_JA[k] for k in names], fontsize=9)
    ax.set_ylim(len(names) - 0.5, -0.7)
    ax.set_xlabel(
        "10 年間の変化が 1 標準偏差大きいときの TFR の変化\n（点: 推定値、線: 95% 信頼区間）"
    )
    ax.set_title(f"(a) TFR 3 未満から始まる 10 年間（{s2.n} 区間・{s2.countries} か国）",
                 fontsize=10, loc="left")  # fmt: skip
    base._style(ax)
    ax2.set_axis_off()
    ax2.text(0.0, 0.95, "(b) 事前に決めた採点表の結果", fontsize=10, transform=ax2.transAxes)
    y = 0.80
    for m, name, v in scorecard_rows(verdicts):
        col = ORANGE if v == "支持" else MUTED
        ax2.text(0.0, y, m, fontsize=10, fontweight="bold", transform=ax2.transAxes)
        ax2.text(0.09, y, name, fontsize=9, transform=ax2.transAxes)
        ax2.text(0.88, y, v, fontsize=10, color=col, fontweight="bold", transform=ax2.transAxes)
        y -= 0.14
    fig.suptitle("2 人未満へ下がる段階では、女子の就学の広がりが最も整合的な候補（ただし脆い）",
                 fontsize=11, x=0.01, ha="left")  # fmt: skip
    fig.text(0.01, 0.045,
             "(a) 国と期間の固定効果つきの 10 年差分、橙 = 95% CI が 0 を含まない。"
             "区切りを TFR 3.5・2.1 に"
             "したとき、初婚年齢を外して標本を広げたときは、どの変数の CI も 0 を含む。\n"
             "区切りを 2.5 にすると、"
             "係数が最大になるのは所得（符号は正）に変わる。",
             fontsize=7.5, color=MUTED, ha="left")  # fmt: skip
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    base._save(fig, path, SRC_WDI)


H8B_JA = {
    "emp": "就業している割合\n（教育なしの女性）",
    "mcpr": "近代的避妊の実行率\n（教育なしの既婚女性）",
    "att_pri": "子どもの初等教育の就学率",
    "att_sec": "子どもの中等教育の就学率",
    "ln_u5": "子どもの死亡率\n（5 歳未満、対数）",
}


def fig7_within_group(x1: h8b.Horse, x5: h8b.X5Result, path: Path) -> None:
    plt = _plt()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.0, 5.0), gridspec_kw={"width_ratios": [1.1, 1]})
    rows = spec_rows([(H8B_JA[k], x1.est.coefs[k]) for k in h8b.X1_VARS])
    for i, (_lab, b, lo, hi, sig) in enumerate(rows):
        col = ORANGE if sig else BLUE_RAMP[2]
        ax.plot([lo, hi], [i, i], color=col, lw=2.2)
        ax.plot([b], [i], "o", color=col)
        ax.text(b, i - 0.22, f"{b:+.2f}", ha="center", fontsize=9)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_ylim(len(rows) - 0.5, -0.7)
    ax.set_xlabel("1 標準偏差高いときの、教育なしの女性の望む出生の差（人）\n"
                  "（点: 推定値、線: 95% 信頼区間）")  # fmt: skip
    ax.set_title(f"(a) 同じ国の中で並んで動いたもの（{x1.est.n} 調査・{x1.est.countries} か国）",
                 fontsize=10, loc="left")  # fmt: skip
    base._style(ax)
    med, up, n = rise_summary(x5.pairs["d_women_employed"].to_list())
    dv = sorted(x5.pairs["d_women_employed"].to_list())
    ax2.barh(range(n), dv, color=[BLUE_RAMP[2] if v > 0 else ORANGE for v in dv], height=0.8)
    ax2.axvline(0, color=MUTED, lw=0.8)
    ax2.axvline(med, color="#333333", ls="--", lw=1.0)
    ax2.text(med, n + 0.5, f"中央値 {med:+.1f} ポイント", ha="right", fontsize=9)
    ax2.set_yticks([])
    ax2.set_ylim(-1, n + 2.5)
    ax2.set_xlabel("就業している割合の変化（ポイント、最初 → 最後の調査、8 年以上）")
    ax2.set_title(f"(b) 教育なしの女性の就業率: 上がった国は {n} か国中 {up}",
                  fontsize=10, loc="left")  # fmt: skip
    base._style(ax2)
    fig.suptitle("教育なしの女性の望む子ども数と並んで動いたのは、就業ではなく避妊の普及",
                 fontsize=11, x=0.01, ha="left")  # fmt: skip
    _note(fig, "(a) 国の固定効果と年トレンドつきの回帰に 5 つを同時に入れた。橙 = 95% CI が 0 を"
               "含まない。並んで動いたことを示すだけで、原因とは限らない（避妊は少なく産みたい"
               "気持ちの表れでもある）。\n(b) 1 本 = 1 か国。橙 = 下がった国。就業には農業・"
               "家族従業も含む（DHS の定義）。事後に追加した検証（H8b）。")  # fmt: skip
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    base._save(fig, path, SRC_DHS)


Y1_JA = {
    "d_tert": "高等教育の進学率",
    "d_sle": "期待就学年数（教育の長さ）",
    "d_eexp": "政府の教育支出（GDP 比）",
    "d_sec": "女子の中等就学率",
    "d_ln_gdp": "一人当たり GDP（対数）",
    "d_ln_u5": "子どもの死亡率（対数）",
}


def fig8_education_length(y1: h8c.Y1Result, path: Path) -> None:
    s2 = y1.s2
    assert s2 is not None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    rows = spec_rows([(Y1_JA[k], s2.coefs[k]) for k in h8c.Y1_VARS])
    for i, (_lab, b, lo, hi, sig) in enumerate(rows):
        col = ORANGE if sig else BLUE_RAMP[2]
        ax.plot([lo, hi], [i, i], color=col, lw=2.2)
        ax.plot([b], [i], "o", color=col)
        ax.text(b, i - 0.22, f"{b:+.2f}", ha="center", fontsize=9)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)
    ax.set_ylim(len(rows) - 0.5, -0.7)
    ax.set_xlabel(
        "10 年間の変化が 1 標準偏差大きいときの TFR の変化（人）\n"
        "（点: 推定値、線: 95% 信頼区間。左ほど出生率の低下と並ぶ）"
    )
    ax.set_title(
        f"TFR 3 未満から始まる 10 年間（{s2.n} 区間・{s2.countries} か国）", fontsize=10, loc="left"
    )
    base._style(ax)
    fig.suptitle(
        "2 人未満へ下がる段階で、教育の長さ・教育費の伸びは出生率の低下と並んでいない",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "国と期間の固定効果つきの 10 年差分に 6 つを同時に入れた（青 = 95% CI が 0 を含む）。"
        "区切り・差分の幅・標本を変えても、\n教育の長さが負で CI が 0 を含まない仕様はない。"
        "事後に追加した検証（H8c）。",
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    base._save(fig, path, SRC_WDI)


def _oecd_panel(ax: Any, res: h8c.Y2Result, x: str, xlabel: str) -> None:
    for iso, xv, yv in res.frame.select("iso3", x, "tfr").rows():
        name = country_ja(iso)
        if name is None:
            ax.scatter([xv], [yv], s=14, color="#bbbbbb", zorder=2)
            continue
        if iso in h8c.EAST:
            ax.scatter([xv], [yv], s=36, color=ORANGE, zorder=3)
            ax.annotate(
                name, (xv, yv), fontsize=9, color=ORANGE, xytext=(4, 3), textcoords="offset points"
            )
        else:  # Nordic points sit close together: distinct markers + legend instead of labels
            ax.scatter([xv], [yv], s=40, color=BLUE_RAMP[3], marker=NORDIC_MARKER[iso],
                       zorder=3, label=name)  # fmt: skip
    ax.legend(fontsize=8, frameon=False, loc="upper right", title="北欧", title_fontsize=8)
    r, p = res.rho[x]
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel("合計特殊出生率（TFR）")
    ax.set_title(f"{res.est.n} か国、順位相関 {r:+.2f}（p = {p:.2f}）", fontsize=10, loc="left")
    base._style(ax)


def fig9_oecd(main: h8c.Y2Result, norel: h8c.Y2Result, path: Path) -> None:
    plt = _plt()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.9))
    _oecd_panel(ax, norel, "priv", "教育費のうち家計など民間が負担する割合（%、初等〜高等）")
    _oecd_panel(ax2, main, "rel", "大卒の賃金（高卒 = 100、25〜64 歳）")
    fig.suptitle(
        "OECD の中で、教育費の家計負担や学歴の賃金差が大きい国ほど"
        "出生率が低い、という関係は見えない",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "各国の最新年（値と TFR がそろう 2012 年以降の最新年。日本の賃金差は 2012 年）。"
        "日本・韓国は家計負担が大きく出生率が低いが、\n英語圏・チリも家計負担が大きく、"
        "北欧は負担が小さいのに 2010 年代に出生率が大きく下がった。事後に追加した検証（H8c）。",
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    base._save(fig, path, SRC_OECD)


def fig10_gender_equity(res: h8d.GResult, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    hi_col, lo_col = ORANGE, BLUE_RAMP[1]
    for iso, sh, tfr, fl in res.frame.select("iso3", "share", "tfr", "flfp").rows():
        col = hi_col if fl >= res.median_flfp else lo_col
        name = ge_label(iso)
        ax.scatter([sh], [tfr], s=44 if name else 18, color=col, zorder=3,
                   edgecolor=INK if name else "none", linewidth=0.6)  # fmt: skip
        if name:
            ax.annotate(name, (sh, tfr), fontsize=9, color=INK, xytext=(4, 3),
                        textcoords="offset points")  # fmt: skip
    ax.scatter(
        [],
        [],
        s=30,
        color=hi_col,
        label=f"女性の労働参加率が高い半分（{res.median_flfp:.0f}% 以上）",
    )
    ax.scatter([], [], s=30, color=lo_col, label="女性の労働参加率が低い半分")
    ax.legend(fontsize=8.5, frameon=False, loc="lower left")
    b, u = res.z1c, res.z2u
    r, p = res.rho
    ax.set_xlabel("家事・育児など無償労働のうち女性が担う割合（女性 ÷（女性＋男性））")
    ax.set_ylabel("合計特殊出生率（TFR、同じ年）")
    upper = "" if u is None else f"、参加率が高い半分では {u[0]:+.2f} [{u[2]:+.2f}, {u[3]:+.2f}]"
    ax.set_title(
        f"{res.z1.n} か国、順位相関 {r:+.2f}（p = {p:.2f}）。所得・就業・進学率をそろえた"
        f"標準化係数 {b[0]:+.2f} [{b[2]:+.2f}, {b[3]:+.2f}]{upper}",
        fontsize=9,
        loc="left",
    )
    base._style(ax)
    fig.suptitle(
        "家事・育児が女性に偏った国ほど出生率が低い、という関係は全体では確かめられない",
        fontsize=11.5,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "各国の最新の観測年（2000 年以降）で TFR が 2.5 未満の国。スペインは年齢区分が合わず除外。"
        "日本・韓国の男性値は調査の定義差で低めに出る。\n"
        "OECD 加盟国だけ・TFR 2.1 未満だけに絞ると負の関連が出るが、"
        "OECD の結果は韓国を外すと消える。"
        "事後に追加した検証（H8d）。",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    base._save(fig, path, SRC_SDG)


def fig11_korea(kf: pl.DataFrame, k: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    fig, (ax, ax3) = plt.subplots(1, 2, figsize=(11.0, 4.9), gridspec_kw={"width_ratios": [1.5, 1]})
    yrs = kf["year"].to_list()
    ax.plot(yrs, kf["spend_per_student_10k_krw"].to_list(), color=ORANGE, marker="o", ms=3.5)
    ax.set_ylabel("生徒 1 人当たり月平均の私教育費（万ウォン、名目）", color=ORANGE, fontsize=9)
    ax.set_xticks(list(range(2007, 2026, 3)))
    base._style(ax)
    ax2 = ax.twinx()
    t = kf.drop_nulls(["tfr"])
    ax2.plot(t["year"].to_list(), t["tfr"].to_list(), color=BLUE_RAMP[3], marker="s", ms=3.5)
    ax2.set_ylabel("合計特殊出生率（TFR）", color=BLUE_RAMP[3], fontsize=9)
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(labelsize=9)
    ax.set_title("韓国 2007〜2025 年: 私教育費（橙）と出生率（青）", fontsize=10, loc="left")
    bc = k.filter(pl.col("table") == "by_children").pivot(
        on="metric", index=["year", "group"], values="value", aggregate_function=None
    )
    groups = ["자녀 1명", "자녀 2명", "자녀 3명 이상"]
    for j, (y, col) in enumerate(((2024, BLUE_RAMP[1]), (2025, ORANGE))):
        sub = [
            bc.filter((pl.col("year") == y) & (pl.col("group") == g)).row(0, named=True)
            for g in groups
        ]
        xs = [i + (j - 0.5) * 0.38 for i in range(len(groups))]
        vals = [float(r["spend_per_student_10k_krw"]) for r in sub]
        ax3.bar(xs, vals, width=0.36, color=col, label=f"{y} 年")
        for x, r in zip(xs, sub, strict=True):
            ax3.annotate(
                f"{r['spend_per_student_10k_krw']:.1f}\n({r['participation_rate_pct']:.0f}%)",
                (x, r["spend_per_student_10k_krw"]),
                ha="center",
                fontsize=7.5,
                xytext=(0, 2),
                textcoords="offset points",
            )
    ax3.set_xticks(range(len(groups)))
    ax3.set_xticklabels(["子 1 人", "子 2 人", "子 3 人以上"])
    ax3.set_ylabel("生徒 1 人当たり月平均（万ウォン）", fontsize=9)
    ax3.set_ylim(0, 64)
    ax3.legend(fontsize=8, frameon=False, loc="upper right")
    ax3.set_title("世帯の子ども数別（かっこ内は参加率）", fontsize=10, loc="left")
    base._style(ax3)
    fig.suptitle(
        "韓国では 2016 年以降に私教育費が急に上がり、同じ時期に出生率が下がった（記述のみ）",
        fontsize=11.5,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "金額は名目（物価調整なし）。2020 年は新型コロナで落ち込み。就学前・浪人生は調査対象外。"
        "1 国の時系列で、私教育費が出生率を下げたとは言えない。\n"
        "子どもが少ない世帯ほど 1 人当たりの費用が高い。事後に追加した記述（H8d）。",
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.94))
    base._save(fig, path, SRC_KR)


# ---------------------------------------------------------------- driver
def t2_specs(st: pl.DataFrame, t2: h8.T2Result) -> list[tuple[str, Coef]]:
    """Main T2(c) and the two specification checks of H8's exploratory E7 (no trend) and
    E4 (surveys with TFR >= 4); same samples and formulas as a20261017_h8_mechanisms."""
    f7 = st.drop_nulls(["tfr", "ideal_children", "ln_u5", "sec"])
    e7 = fit(f7, "tfr ~ ln_u5 + sec + C(iso3)", label="E7 no trend", fe=False)
    f4 = st.filter(pl.col("tfr") >= 4).drop_nulls(["tfr", "ln_u5", "sec"])
    e4 = fit(f4, "tfr ~ ln_u5 + sec + C(iso3) + survey_year", label="E4 TFR>=4", fe=False)
    return [
        (f"事前に決めた仕様\n（年トレンドあり、n={t2.c.n}）", t2.c.coefs["ln_u5"]),
        (f"年トレンドを外す\n（n={e7.n}）", e7.coefs["ln_u5"]),
        (f"TFR 4 以上の調査に限る\n（n={e4.n}）", e4.coefs["ln_u5"]),
    ]


def run(data_dir: Path, fig_dir: Path) -> list[tuple[str, str]]:
    font = base.setup_matplotlib()
    print(f"font: {font}")
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = pl.read_parquet(data_dir / h8.DHS_MART)
    panel = pl.read_parquet(data_dir / h8.PANEL_MART)
    st = h8.survey_table(d, panel)
    cells = h8.cell_table(d, st)
    captions: list[tuple[str, str]] = []

    t1 = h8.run_t1(st, "S")
    fig1_wanted(t1, fig_dir / "h8s01_wanted_unwanted.png")
    captions.append((
        "h8s01_wanted_unwanted.png",
        f"出生率の低下の合計のうち {t1.s_w:.0%} は「望む子ども数」の低下、残る {1 - t1.s_w:.0%} が"
        f"望まない出生の減少（{t1.n_pairs} 組・{t1.n_countries} か国の DHS 調査の組）。",
    ))  # fmt: skip

    t4 = h8.run_t4(cells, "S")
    fig2_edu_gradient(t4, fig_dir / "h8s02_education_wanted.png")
    captions.append((
        "h8s02_education_wanted.png",
        f"同じ調査の中で、中等教育の女性は教育なしの女性より望む出生が {t4.g_w[0]:+.2f} 人、"
        f"望まない出生が {t4.g_u[0]:+.2f} 人（高等教育は {t4.h_w[0]:+.2f} / {t4.h_u[0]:+.2f}）。"
        f"学歴の差は主に望む数に出る（{t4.frame['survey_id'].n_unique()} 調査・"
        f"{t4.est_w.countries} か国）。",
    ))  # fmt: skip

    shares = h8.edu_shares(d)
    fell_iso = set(
        h8.pair_frame(st, ("tfr",), min_gap=8, mode="first_last")
        .filter(pl.col("d_tfr") < 0)["iso3"]
        .to_list()
    )
    g = h8.group_rates(cells, shares, st, "wanted_tfr")
    two = h8.e10_rows(g, fell_iso, two=True)
    four = h8.e10_rows(g, fell_iso, two=False)
    sc, med = fig3_kitagawa(two, four, fig_dir / "h8s03_within_education.png")
    captions.append((
        "h8s03_within_education.png",
        f"望む出生の低下のうち、学歴の高い女性が増えたこと（構成）で説明できるのは {sc:.0%}、"
        f"残る {1 - sc:.0%} は同じ学歴の中での低下（{len(two)} か国）。学歴群ごとの変化の中央値は"
        + "、".join(f"{EDU_JA[e]} {v:+.2f}" for e, v in zip(h8.EDU, med, strict=True))
        + f" 人（{len(four)} か国、探索的）。",
    ))  # fmt: skip

    t3 = h8.run_t3(st, cells, "S")
    fig4_marriage(t3, fig_dir / "h8s04_marriage.png")
    captions.append((
        "h8s04_marriage.png",
        f"中等教育の女性の初婚年齢は教育なしの女性より中央値で {t3.median_sec:+.1f} 年遅く、"
        f"{t3.share_ge2:.0%} の調査で +2 年以上（{t3.n_afm} 調査）。結婚している割合の低下は "
        f"ln TFR の低下の {t3.s_m:.0%} にあたる（{t3.n_cm} か国）。",
    ))  # fmt: skip

    t2 = h8.run_t2(st, "S")
    rows5 = spec_rows(t2_specs(st, t2))
    for r in rows5:
        print(f"  T2 spec {r[0].splitlines()[0]}: {r[1]:+.3f} [{r[2]:+.3f}, {r[3]:+.3f}]")
    n_low, share_below = fig5_mortality(rows5, st, fig_dir / "h8s05_mortality.png")
    main_, notrend, hi4 = rows5
    captions.append((
        "h8s05_mortality.png",
        f"同じ国の中での死亡率と出生率の関連は、事前に決めた仕様では {main_[1]:+.3f}"
        f" [{main_[2]:+.2f}, {main_[3]:+.2f}] で確かめられないが、年トレンドを外すと "
        f"{notrend[1]:+.3f}、TFR 4 以上の調査では {hi4[1]:+.3f}（どちらも探索的）。"
        f"死亡率が千対 40 未満の {n_low} 調査の {share_below:.0%} で"
        " TFR は理想の子ども数を下回る。",
    ))  # fmt: skip

    t5 = h8.run_t5(cells, "S")
    t6base, _ = h8.t6_base(panel)
    _, s2, _ = h8.run_t6(t6base, "S")
    assert s2 is not None
    c2 = t2.c.coefs["ln_u5"]
    verdicts = h8.score_mechanisms(
        s_w=t1.s_w,
        t2c=(c2[0], c2[2], c2[3]),
        share_ge2=t3.share_ge2,
        s_m=t3.s_m,
        g_w=(t4.g_w[0], t4.g_w[3]),
        g_u=t4.g_u[0],
        gamma=(t5.gamma[0], t5.gamma[2], t5.gamma[3]),
    )
    print(f"  scorecard {verdicts}")
    fig6_stage2(s2, verdicts, fig_dir / "h8s06_stage2_scorecard.png")
    sec, inc = s2.coefs["d_sec"], s2.coefs["d_ln_gdp"]
    captions.append((
        "h8s06_stage2_scorecard.png",
        f"TFR 3 未満からの 10 年間では女子就学率の標準化係数 {sec[0]:+.3f}"
        f" [{sec[2]:+.3f}, {sec[3]:+.3f}] が最も整合的で、所得 {inc[0]:+.3f} は CI が 0 を含む"
        f"（{s2.n} 区間・{s2.countries} か国、区切りや標本で変わる脆い結果）。採点表: "
        + "・".join(f"{mm} {v}" for mm, _, v in scorecard_rows(verdicts))
        + "。",
    ))  # fmt: skip

    ne = h8b.no_edu_frame(cells, st)
    x1 = h8b.horse(ne, "wanted_tfr", h8b.X1_VARS, label="S X1", allowed=h8b.X1_VARS)
    x5 = h8b.run_x5(cells, st, "S")
    fig7_within_group(x1, x5, fig_dir / "h8s07_within_group_drivers.png")
    mc, emp = x1.est.coefs["mcpr"], x1.est.coefs["emp"]
    med5, up, n5 = rise_summary(x5.pairs["d_women_employed"].to_list())
    captions.append((
        "h8s07_within_group_drivers.png",
        f"同じ国の中で、教育なしの女性の望む出生と並んで動いたのは近代的避妊の普及だけで、"
        f"1 標準偏差あたり {mc[0]:+.2f} 人 [{mc[2]:+.2f}, {mc[3]:+.2f}]。就業は {emp[0]:+.2f} 人"
        f" [{emp[2]:+.2f}, {emp[3]:+.2f}] で確かめられず、子どもの就学率・死亡率も CI が 0 を含む"
        f"（{x1.est.n} 調査・{x1.est.countries} か国）。教育なしの女性の就業率は中央値で"
        f" {med5:+.1f} ポイント変化し、上がった国は {n5} か国中 {up}（事後に追加した検証 H8b）。",
    ))  # fmt: skip

    y1 = h8c.run_y1(h8c.y1_base(panel), "S")
    fig8_education_length(y1, fig_dir / "h8s08_education_length.png")
    assert y1.s2 is not None
    c8 = y1.s2.coefs
    captions.append((
        "h8s08_education_length.png",
        f"TFR 3 未満からの 10 年間で、期待就学年数 {c8['d_sle'][0]:+.2f}"
        f" [{c8['d_sle'][2]:+.2f}, {c8['d_sle'][3]:+.2f}]、高等教育進学率 {c8['d_tert'][0]:+.2f}"
        f" [{c8['d_tert'][2]:+.2f}, {c8['d_tert'][3]:+.2f}]、政府の教育支出 "
        f"{c8['d_eexp'][0]:+.2f} [{c8['d_eexp'][2]:+.2f}, {c8['d_eexp'][3]:+.2f}] のどれも CI が"
        f" 0 を含む（{y1.s2.n} 区間・{y1.s2.countries} か国、事後に追加した検証 H8c）。",
    ))  # fmt: skip
    o = pl.read_parquet(data_dir / h8c.OECD_MART)
    op = h8c.oecd_panel(o, panel)
    y2 = h8c.run_y2(op, "S")
    y2n = h8c.run_y2(op, "S no-rel", xs=h8c.Y2_NOREL)
    fig9_oecd(y2, y2n, fig_dir / "h8s09_oecd_education_cost.png")
    rp, rr = y2n.rho["priv"], y2.rho["rel"]
    bp, br = y2.est.coefs["priv"], y2.est.coefs["rel"]
    captions.append((
        "h8s09_oecd_education_cost.png",
        f"OECD の最新年で、教育費の私的負担割合と TFR の順位相関は {rp[0]:+.2f}"
        f"（{y2n.est.n} か国）、"
        f"大卒の相対賃金とは {rr[0]:+.2f}（{y2.est.n} か国）。所得と一人当たり支出をそろえた"
        f"標準化係数も {bp[0]:+.2f} [{bp[2]:+.2f}, {bp[3]:+.2f}]・{br[0]:+.2f}"
        f" [{br[2]:+.2f}, {br[3]:+.2f}] で、負の関連は確かめられない（事後に追加した検証 H8c）。",
    ))  # fmt: skip

    g = pl.read_parquet(data_dir / h8d.GENDER_MART)
    hw = h8d.hdr_wide(pl.read_parquet(data_dir / h8d.HDR_MART))
    sel = h8d.select_band(h8d.unpaid_wide(g))
    gres = h8d.run_g(h8d.cross_section(sel, panel, g, hw), "S", verbose=False)
    fig10_gender_equity(gres, fig_dir / "h8s10_gender_equity.png")
    b10, u10 = gres.z1c, gres.z2u
    assert u10 is not None
    captions.append((
        "h8s10_gender_equity.png",
        f"TFR 2.5 未満の {gres.z1.n} か国で、家事・育児時間の女性偏りと TFR の順位相関は "
        f"{gres.rho[0]:+.2f}、所得・女性の就業・進学率をそろえた標準化係数は {b10[0]:+.2f}"
        f" [{b10[2]:+.2f}, {b10[3]:+.2f}]。女性の労働参加率が高い半分では {u10[0]:+.2f}"
        f" [{u10[2]:+.2f}, {u10[3]:+.2f}] だが、交互作用は {gres.z2i[0]:+.2f}"
        f" [{gres.z2i[2]:+.2f}, {gres.z2i[3]:+.2f}] で確かめられず、事前に決めた判定は"
        f"「{h8d.VERDICT_JA[gres.verdict]}」（事後に追加した検証 H8d）。",
    ))  # fmt: skip
    kr = pl.read_parquet(data_dir / h8d.KR_MART)
    kf = h8d.korea_frame(kr, panel)
    fig11_korea(kf, kr, fig_dir / "h8s11_korea_tutoring.png")
    sp = dict(kf.select("year", "spend_per_student_10k_krw").rows())
    tf = dict(kf.drop_nulls(["tfr"]).select("year", "tfr").rows())
    bc = dict(
        kr.filter(
            (pl.col("table") == "by_children")
            & (pl.col("year") == 2025)
            & (pl.col("metric") == "spend_per_student_10k_krw")
        )
        .select("group", "value")
        .rows()
    )
    ty = max(tf)
    captions.append((
        "h8s11_korea_tutoring.png",
        f"韓国の生徒 1 人当たり月平均の私教育費（名目）は 2007 年 {sp[2007]:.1f} 万ウォン、"
        f"2015 年 {sp[2015]:.1f}、2025 年 {sp[2025]:.1f}。同じ期間に TFR は {tf[2007]:.2f}"
        f"（2007）→ {tf[2015]:.2f}（2015）→ {tf[ty]:.2f}（{ty}）。2025 年の 1 人当たり"
        f"費用は子 1 人の世帯 {bc['자녀 1명']:.1f}、子 3 人以上の世帯 {bc['자녀 3명 이상']:.1f}"
        " 万ウォン（記述のみ、事後に追加した H8d）。",
    ))  # fmt: skip

    lines = ["# H8 記事用図のキャプション", "", SRC_DHS, "", SRC_WDI, "", SRC_OECD, ""]
    lines += [SRC_SDG, "", SRC_KR, ""]
    lines += [f"- `{f}`: {cap}" for f, cap in captions]
    (fig_dir / "captions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f, cap in captions:
        print(f"caption {f}: {cap}")
    return captions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument(
        "--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures" / "summary_h8"
    )
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
