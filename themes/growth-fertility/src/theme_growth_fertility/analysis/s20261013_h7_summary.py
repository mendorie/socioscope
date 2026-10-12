"""H7 の note 記事（日本語・一般読者）用の図を生成する決定的スクリプト。

H7 レポート（reports/2026-10-13-h7-between-gradient.md）の主仕様の数値を、同じ mart から
a20261013_h7_between_gradient の関数で**再計算**して最大 6 枚の図にする（新しい推定は行わない。
乱数・現在時刻は使わない）。

    uv run python -m theme_growth_fertility.analysis.s20261013_h7_summary \
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures/summary_h7]

フォント検出・保存規約は s20261005_summary と同じ（Hiragino Sans → … → Yu Gothic、無ければ
DejaVu Sans で stderr に警告。PNG メタデータの Software を落としてバイト再現。sha256 はフォント
環境に依存する）。純粋ヘルパ（scorecard_table, pick_examples, ja_name, stack_segments）は
tests/test_summary_h7.py で検証する。
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from theme_growth_fertility.analysis import a20261013_h7_between_gradient as h7
from theme_growth_fertility.analysis import s20261005_summary as base
from theme_growth_fertility.analysis.a20261004_h1_income_tfr import OIL_STATES, fit
from theme_growth_fertility.analysis.a20261005_h4_stage_vs_gdp import STAGE_VARS, stage_frame

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]

SRC = "出典: World Bank WDI（CC BY 4.0、取得 2026-10-13）　分析: socioscope"
BLUE_RAMP, ORANGE, GREEN, INK, MUTED = (
    base.BLUE_RAMP,
    base.ORANGE,
    base.GREEN,
    base.INK,
    base.MUTED,
)
STAGE_JA = {
    "u5_mortality": "子どもの死亡率",
    "fem_sec_enrol": "女子の中等教育",
    "life_exp": "平均寿命",
    "urban_share": "都市化",
    "fem_lfp": "女性の労働参加",
    "remaining": "残る所得の傾き",
}
JA_NAMES = {
    "JPN": "日本",
    "TUN": "チュニジア",
    "JOR": "ヨルダン",
    "MHL": "マーシャル諸島",
    "PER": "ペルー",
    "NIC": "ニカラグア",
    "ECU": "エクアドル",
    "MLT": "マルタ",
    "CYP": "キプロス",
    "BIH": "ボスニア・ヘルツェゴビナ",
    "HUN": "ハンガリー",
    "PRT": "ポルトガル",
}
QUAD_JA = {
    "richer_fell": "豊かになり、下がった",
    "not_richer_fell": "豊かにならずに下がった",
    "richer_not_fell": "豊かになったが下がり幅は小さい",
    "not_richer_not_fell": "豊かにならず、下がり幅も小さい",
}
N_EXAMPLES = 4


# ---------------------------------------------------------------- pure helpers (tested)
def scorecard_table(
    tests: Sequence[tuple[str, str, set[str]]],
) -> tuple[list[tuple[str, str, tuple[int, int, int]]], dict[str, int], str]:
    """Rows (name, value, (A, B, C) flags), totals and the answer from h7.select_answer."""
    rows = []
    totals = {"A": 0, "B": 0, "C": 0}
    for name, val, pts in tests:
        flags = tuple(int(k in pts) for k in ("A", "B", "C"))
        rows.append((name, val, (flags[0], flags[1], flags[2])))
        for k in pts:
            totals[k] += 1
    return rows, totals, h7.select_answer(totals)


def pick_examples(
    rows: Iterable[Mapping[str, Any]],
    quadrant: str,
    key: str,
    *,
    k: int = N_EXAMPLES,
    descending: bool = True,
) -> list[str]:
    """Up to k iso3 in *quadrant* ranked by *key* (ties by iso3); rows with key None are skipped."""
    sel = [r for r in rows if r["quadrant"] == quadrant and r[key] is not None]
    sign = -1.0 if descending else 1.0
    sel.sort(key=lambda r: (sign * float(r[key]), r["iso3"]))
    return [r["iso3"] for r in sel[:k]]


def ja_name(iso3: str, country: str) -> str:
    return JA_NAMES.get(iso3, country)


def stack_segments(deltas: Mapping[str, float], remaining: float) -> list[tuple[str, float, float]]:
    """(label, width, left edge) for a horizontal stacked bar: deltas in order, then remaining."""
    out = []
    left = 0.0
    for k, d in [*deltas.items(), ("remaining", remaining)]:
        out.append((k, d, left))
        left += d
    return out


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    import matplotlib.pyplot as plt

    return plt


def fig1_decomposition(g: h7.Gelbach, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    colors = [BLUE_RAMP[4], BLUE_RAMP[3], BLUE_RAMP[2], BLUE_RAMP[1], BLUE_RAMP[0], ORANGE]
    from matplotlib.patches import Patch

    segs = stack_segments(g.deltas, g.beta_full)
    handles = []
    for (k, d, left), c in zip(segs, colors, strict=True):
        ax.barh([0], [d], left=left, color=c, edgecolor="white", height=0.5)
        if abs(d) >= 0.15:
            ax.text(left + d / 2, 0, f"{d:+.2f}", ha="center", va="center", fontsize=9,
                    color="white")  # fmt: skip
        handles.append(Patch(color=c, label=f"{STAGE_JA[k]} {d:+.2f}"))
    ax.axvline(0, color=MUTED, linewidth=0.8)
    ax.set_yticks([])
    ax.set_xlim(min(g.beta0, 0) * 1.08, max(0.1, max(d for _, d, _ in segs) + 0.05))
    ax.set_xlabel(
        "所得（一人当たり GDP、購買力平価）が 1 対数単位高いときの出生率の差（子ども数/女性）"
    )
    ax.set_title(
        f"国の間の「豊かな国ほど出生率が低い」傾き {g.beta0:+.2f} のうち、"
        f"{g.share:.0%} は段階指標で説明される\n"
        f"（1990〜2024 年、{g.countries} か国・{g.n:,} 国×年、年固定効果付き Gelbach 分解）",
        fontsize=10.5,
        loc="left",
    )
    ax.legend(handles=handles, fontsize=8.5, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.38),
              ncol=3)  # fmt: skip
    base._style(ax)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    base._save(fig, path, SRC)


def fig2_strata(t2: h7.T2Result, overall: float, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    xs: list[float] = []
    labels: list[str] = []
    for q, est in t2.strata:
        b, _, lo, hi = est.coefs["ln_gdp"]
        ax.plot([q, q], [lo, hi], color=BLUE_RAMP[2], linewidth=2.2)
        ax.plot([q], [b], "o", color=BLUE_RAMP[4])
        ax.text(q + 0.08, b, f"{b:+.2f}", fontsize=8.5, va="center")
        xs.append(q)
        labels.append(f"第{q}層\n{est.countries} か国\nn={est.n:,}")
    if t2.aux is not None:
        b, _, lo, hi = t2.aux.coefs["ln_gdp"]
        ax.plot([6.3, 6.3], [lo, hi], color=GREEN, linewidth=2.2)
        ax.plot([6.3], [b], "s", color=GREEN)
        ax.text(6.38, b, f"{b:+.2f}", fontsize=8.5, va="center")
        xs.append(6.3)
        labels.append(f"転換開始から\n30 年以上\n{t2.aux.countries} か国 n={t2.aux.n:,}")
    ax.axhline(overall, color=ORANGE, linestyle="--", linewidth=1.2,
               label=f"全体（層で分けない）{overall:+.2f}")  # fmt: skip
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlim(0.5, 7.0)
    ax.set_ylabel("所得が 1 対数単位高いときの出生率の差\n（点: 推定値、線: 95% 信頼区間）")
    ax.set_xlabel(
        "人口転換の段階（子どもの死亡率・平均寿命・女子中等就学率の合成指標）の五分位"
        "　第1層 = 最も手前、第5層 = 最も進んだ",
        fontsize=8.5,
    )
    ax.set_title(
        "段階が同じ国どうしで比べると、所得の傾きは小さくなり、最も進んだ層では消える",
        fontsize=10.5,
        loc="left",
    )
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    base._style(ax)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    base._save(fig, path, SRC)


def _dollar_fmt() -> Any:
    from matplotlib.ticker import FuncFormatter

    return FuncFormatter(lambda v, _pos: f"${v:,.0f}")


def fig3_onset_income(t3: h7.T3Result, path: Path) -> None:
    plt = _plt()
    d = t3.of.filter(pl.col("gdp_pcap_const").is_not_null())
    vals = d["gdp_pcap_const"].to_numpy()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.4), gridspec_kw={"width_ratios": [1.3, 1]})
    bins = np.logspace(np.log10(vals.min() * 0.9), np.log10(vals.max() * 1.1), 22)
    ax.hist(vals, bins=bins, color=BLUE_RAMP[2], edgecolor="white")
    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(_dollar_fmt())
    top = ax.get_ylim()[1]
    p10, p50, p90 = np.percentile(vals, [10, 50, 90])
    for v, lab in ((p10, "下位10%"), (p50, "中央値"), (p90, "上位10%")):
        ax.axvline(v, color=ORANGE, linestyle="--", linewidth=1)
        ax.text(v, top * 0.97, f" {lab}\n ${v:,.0f}", fontsize=8, va="top")
    ax.set_xlabel("出生率が下がり始めた年の一人当たり GDP（2015 年固定 US$、対数目盛）")
    ax.set_ylabel("国の数")
    ax.set_title(
        f"(a) 下がり始めたときの所得: 上位10% は下位10% の {t3.ratio:.1f} 倍（{len(vals)} か国）",
        fontsize=10,
        loc="left",
    )
    base._style(ax)
    ax2.scatter(d["onset_year"], d["gdp_pcap_const"], s=12, color=BLUE_RAMP[2], alpha=0.8)
    ax2.set_yscale("log")
    ax2.yaxis.set_major_formatter(_dollar_fmt())
    ax2.set_xlabel("出生率が下がり始めた年")
    ax2.set_ylabel("その年の一人当たり GDP（2015 年 US$、対数目盛）")
    ax2.set_title(f"(b) 開始年と開始時の所得（n={d.height}）", fontsize=10, loc="left")
    base._style(ax2)
    fig.text(
        0.01,
        0.035,
        "開始年 = 1960〜75 年の TFR 最大値（4.5 以上）から 10% 下がり、以後戻らない最初の年",
        fontsize=7.5,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    base._save(fig, path, SRC)


EVENT_SPECS = (
    ("ln_gdp_c", "一人当たり GDP（対数、2015 年 US$）"),
    ("ln_u5", "5 歳未満死亡率（対数）"),
    ("fem_prim_enrol", "女子の就学率（総就学率 %）"),
    ("tfr", "合計特殊出生率（子ども数/女性）"),
)


def fig4_event(panel: pl.DataFrame, onsets: Mapping[str, int], path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.4))
    for ax, (var, lab) in zip(axes.flat, EVENT_SPECS, strict=True):
        series = [(var, BLUE_RAMP[4], "-", "初等")]
        if var == "fem_prim_enrol":
            series.append(("fem_sec_enrol", BLUE_RAMP[1], "--", "中等"))
        counts = []
        for v, color, ls, nm in series:
            m = h7.event_means(panel, onsets, v).filter(pl.col("n") >= 10)
            ax.plot(m["event_time"], m["m"], color=color, linestyle=ls,
                    label=nm if len(series) > 1 else None)  # fmt: skip
            n0 = int(m.filter(pl.col("event_time") == 0)["n"].sum())
            counts.append(f"{nm} {n0}" if len(series) > 1 else str(n0))
        if len(series) > 1:
            ax.legend(frameon=False, fontsize=8, loc="lower right")
        ax.axvline(0, color=ORANGE, linewidth=0.9)
        ax.axhline(0, color=MUTED, linewidth=0.6)
        ax.set_title(f"{lab}\n開始年に観測のある国: {'・'.join(counts)}", fontsize=9.5, loc="left")
        ax.set_xlabel("出生率が下がり始めた年からの年数")
        ax.set_ylabel("開始年の値からの差（国平均）", fontsize=8.5)
        base._style(ax)
    fig.suptitle(
        "下がり始めた年（0）にそろえた各国の平均の動き（10 か国以上が観測される年のみ）",
        fontsize=10.5,
        x=0.01,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    base._save(fig, path, SRC)


_OFFSETS = ((8, 6), (-8, -14), (8, -14), (-8, 6))


def fig5_quadrants(t5: h7.T5Result, labels: Mapping[str, str], path: Path) -> None:
    plt = _plt()
    d = t5.table
    fig, ax = plt.subplots(figsize=(8.6, 6.0))
    col = {
        "richer_fell": BLUE_RAMP[1],
        "not_richer_not_fell": "#bbbbbb",
        "not_richer_fell": GREEN,
        "richer_not_fell": ORANGE,
    }
    for q, c in col.items():
        s = d.filter(pl.col("quadrant") == q)
        ax.scatter(s["income_ratio"], s["tfr_drop"], s=16, color=c,
                   label=f"{QUAD_JA[q]}（{s.height}）")  # fmt: skip
    pos = {r["iso3"]: r for r in d.to_dicts()}
    for i, iso3 in enumerate(labels):  # insertion order = rank; alternate offsets to limit overlap
        r = pos[iso3]
        ax.annotate(labels[iso3], (r["income_ratio"], r["tfr_drop"]), fontsize=8, color=INK,
                    xytext=_OFFSETS[i % 4], textcoords="offset points",
                    ha="left" if _OFFSETS[i % 4][0] > 0 else "right",
                    arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.5})  # fmt: skip
    ax.set_xscale("log")
    from matplotlib.ticker import FixedLocator, FuncFormatter

    ax.xaxis.set_major_locator(FixedLocator([0.3, 0.5, 1, 2, 3, 5, 10, 20, 50]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:g} 倍"))
    ax.axvline(3.0, color=INK, linewidth=0.8, linestyle="--")
    ax.axhline(2.0, color=INK, linewidth=0.8, linestyle="--")
    ax.set_xlabel("一人当たり GDP の倍率: 2024 年 ÷ 最初の観測年（2015 年 US$、対数目盛）")
    ax.set_ylabel("同じ期間の出生率の低下幅（子ども数/女性）")
    ax.set_title(
        f"豊かになることと出生率の低下は一致しない（{d.height} か国、境界 3 倍・2.0 は事前に固定）",
        fontsize=10.5,
        loc="left",
    )
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              ncol=2)  # fmt: skip
    base._style(ax)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    base._save(fig, path, SRC)


TEST_JA = {
    "T1": "T1 段階で説明される割合",
    "T2": "T2 最も進んだ層の所得の傾き",
    "T3": "T3 開始時所得の上位10%/下位10%",
    "T4": "T4 同じ国の中の順序",
    "T5": "T5 反例の数（豊かにならず低下 / 豊かでも低下小）",
}
ANSWER_JA = {
    "A": "A 豊かさそのもの",
    "B": "B 人口転換の段階",
    "C": "C 豊かさ→段階",
}


def fig6_scorecard(
    rows: Sequence[tuple[str, str, tuple[int, int, int]]],
    totals: Mapping[str, int],
    answer: str,
    path: Path,
) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    ax.set_axis_off()
    cols = [0.0, 0.47, 0.80, 0.88, 0.96]
    y = 0.92
    for x, h in zip(cols, ["検定", "結果", "A", "B", "C"], strict=True):
        ax.text(x, y, h, fontsize=10, fontweight="bold", transform=ax.transAxes, ha="left")
    for name, val, flags in rows:
        y -= 0.12
        ax.text(cols[0], y, TEST_JA.get(name, name), fontsize=9.5, transform=ax.transAxes)
        ax.text(cols[1], y, val, fontsize=9.5, transform=ax.transAxes)
        for x, f in zip(cols[2:], flags, strict=True):
            ax.text(x, y, "●" if f else "・", fontsize=10, transform=ax.transAxes,
                    color=ORANGE if f else MUTED)  # fmt: skip
    y -= 0.13
    ax.plot([0, 1], [y + 0.07, y + 0.07], color=MUTED, linewidth=0.8, transform=ax.transAxes)
    ax.text(cols[0], y, "合計点", fontsize=10, fontweight="bold", transform=ax.transAxes)
    for x, k in zip(cols[2:], ("A", "B", "C"), strict=True):
        ax.text(x, y, str(totals[k]), fontsize=10.5, fontweight="bold", transform=ax.transAxes)
    top = answer.split(" ")[0]
    chosen = f"{ANSWER_JA[top]}（{totals[top]} 点）" if top in ANSWER_JA else answer
    ax.text(
        cols[0],
        y - 0.15,
        f"事前に決めた規則（最多得点、同点・1 点差なら混合）で選ばれた答え: {chosen}",
        fontsize=10.5,
        transform=ax.transAxes,
        color=INK,
    )
    ax.set_title(
        "答え A / B / C の採点表（判定基準はデータを見る前に固定、各検定 1 点）",
        fontsize=10.5,
        loc="left",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    base._save(fig, path, SRC)


# ---------------------------------------------------------------- driver
def run(data_dir: Path, fig_dir: Path) -> list[tuple[str, str]]:
    font = base.setup_matplotlib()
    print(f"font: {font}")
    fig_dir.mkdir(parents=True, exist_ok=True)
    raw = pl.read_parquet(data_dir / h7.PANEL_MART)
    panel = h7.with_logs(raw)
    frame = stage_frame(raw)
    onsets, table = h7.onsets_from(panel)
    captions: list[tuple[str, str]] = []

    g = h7.run_t1(frame, STAGE_VARS, "M", verbose=False)
    fig1_decomposition(g, fig_dir / "h7s01_decomposition.png")
    captions.append((
        "h7s01_decomposition.png",
        f"国の間の所得の傾き {g.beta0:+.2f} のうち {g.share:.0%} は"
        "死亡率・教育・寿命などの段階指標で"
        f"説明され、残る所得の傾きは {g.beta_full:+.2f}（{g.countries} か国、1990〜2024 年）。",
    ))  # fmt: skip

    overall = h7._b(fit(frame, "tfr ~ ln_gdp + C(year)", label="[M T2 all] pooled", fe=False))[0]
    t2 = h7.run_t2(frame, "M", onsets=onsets, verbose=False)
    fig2_strata(t2, overall, fig_dir / "h7s02_stage_strata.png")
    mids = [h7._b(e)[0] for q, e in t2.strata if 2 <= q <= 4]
    captions.append((
        "h7s02_stage_strata.png",
        f"段階の五分位ごとの所得の傾き: 最も進んだ層で {t2.top[0]:+.2f}"
        f"（95% CI {t2.top[2]:+.2f}〜{t2.top[3]:+.2f}）、"
        f"中間層の平均 {sum(mids) / len(mids):+.2f}、"
        f"全体 {overall:+.2f}。",
    ))  # fmt: skip

    t3 = h7.run_t3(panel, onsets, table, "M", verbose=False)
    fig3_onset_income(t3, fig_dir / "h7s03_onset_income.png")
    n3 = t3.of.filter(pl.col("gdp_pcap_const").is_not_null()).height
    captions.append((
        "h7s03_onset_income.png",
        f"出生率が下がり始めた年の所得は国によって大きく違い、上位10%は下位10%の {t3.ratio:.1f} 倍"
        f"（{n3} か国、2015 年固定 US$）。",
    ))  # fmt: skip

    t4 = h7.run_t4(panel, onsets, "M", verbose=False)
    fig4_event(panel, onsets, fig_dir / "h7s04_event_time.png")
    captions.append((
        "h7s04_event_time.png",
        "下がり始めた年（0）にそろえると、所得の上昇・死亡率の低下・就学率の上昇は開始の前後で"
        "なだらかに続き、出生率だけが開始後に折れ曲がる（年ごとに構成国は異なる）。開始前 10 年の"
        f"成長率が世界平均を上回った国は {t4.share:.0%}（n={t4.n_share}）。",
    ))  # fmt: skip

    t5 = h7.run_t5(panel, "M", verbose=False)
    rows5 = t5.table.to_dicts()
    # labels: non-oil examples only (oil states' income ratio reflects oil prices, H1 OIL_STATES)
    cand = [r for r in rows5 if r["iso3"] not in OIL_STATES]
    pf = pick_examples(cand, "not_richer_fell", "tfr_drop")
    rn = pick_examples(cand, "richer_not_fell", "income_ratio")
    names = {r["iso3"]: r["country"] for r in rows5}
    labels = {i: ja_name(i, names[i]) for i in [*pf, *rn]}
    print(f"labelled not_richer_fell: {pf}")
    print(f"labelled richer_not_fell: {rn}")
    fig5_quadrants(t5, labels, fig_dir / "h7s05_quadrants.png")
    c = t5.counts
    captions.append((
        "h7s05_quadrants.png",
        f"{t5.table.height} か国のうち、所得が 3 倍未満なのに出生率が 2.0 以上下がった国が "
        f"{c['not_richer_fell']}、3 倍以上になったのに低下が 2.0 未満の国が {c['richer_not_fell']}"
        "（国名は産油国を除いた各象限の端の 4 か国）。",
    ))  # fmt: skip

    rows, totals, answer = scorecard_table([
        ("T1", f"S = {g.share:.2f}", h7.t1_points(g.share)),
        ("T2", f"{t2.top[0]:+.2f} [{t2.top[2]:+.2f}, {t2.top[3]:+.2f}]", t2.points),
        ("T3", f"{t3.ratio:.1f} 倍", t3.points),
        ("T4", f"開始前の成長が世界平均超 {t4.share:.0%}", t4.points),
        ("T5", f"{c['not_richer_fell']} / {c['richer_not_fell']}", t5.points),
    ])  # fmt: skip
    for r in rows:
        print(f"  scorecard {r}")
    print(f"  totals {totals}: {answer}")
    fig6_scorecard(rows, totals, answer, fig_dir / "h7s06_scorecard.png")
    captions.append((
        "h7s06_scorecard.png",
        f"事前に決めた採点表で A={totals['A']}・B={totals['B']}・C={totals['C']} 点、"
        f"選ばれた答えは {answer}。",
    ))  # fmt: skip

    lines = ["# H7 記事用図のキャプション", "", f"{SRC}", ""]
    lines += [f"- `{f}`: {cap}" for f, cap in captions]
    (fig_dir / "captions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f, cap in captions:
        print(f"caption {f}: {cap}")
    return captions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument(
        "--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures" / "summary_h7"
    )
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
