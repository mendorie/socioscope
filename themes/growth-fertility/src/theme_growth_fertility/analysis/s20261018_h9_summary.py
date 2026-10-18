"""H9 の note 記事（part5、日本語・一般読者）用の図を生成する決定的スクリプト。

H9 レポート（reports/2026-10-18-h9-norms-vs-constraints.md）の数値を、同じ mart から
a20261018_h9_norms_vs_constraints の関数（`load`, `compute`, `japan_series`, `v1_points`,
`tfr_lookup`, `latest_tfr`, `jp_cohort_cum`, `eu_cohort_cum`）で**再計算**して 5 枚の図にする
（新しい推定は行わない。H9 スクリプトは無変更。乱数・現在時刻は使わない）。

    uv run python -m theme_growth_fertility.analysis.s20261018_h9_summary \
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures/summary_h9]

フォント検出・保存規約は s20261005_summary と同じ（関数を import。PNG メタデータの Software を
落としてバイト再現。sha256 はフォント環境に依存する）。純粋ヘルパ（kind_ja, pick, by_year,
cohort_points）は tests/test_summary_h9.py で検証する。
"""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261018_h9_norms_vs_constraints as h9
from theme_growth_fertility.analysis import s20261005_summary as base

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
BLUE_RAMP, ORANGE, INK, MUTED = base.BLUE_RAMP, base.ORANGE, base.INK, base.MUTED

SRC_JP = (
    "出典: 国立社会保障・人口問題研究所『人口統計資料集 2026』"
    "『第 16 回出生動向基本調査』（PDL1.0）"
    "　分析: socioscope"
)
SRC_EU = (
    "出典: 欧州委員会 Special Eurobarometer 253（2006）・Testa 2012（EB 75.4, 2011）・"
    "BiB 2025（GGS-II, CC BY-SA 4.0）・IPSS・World Bank WDI　分析: socioscope"
)
SRC_ORDER = (
    "出典: Eurostat（出生順位別出生数・女性人口）・IPSS 表 4-16・"
    "韓国 国家データ処「2025年 出生統計」"
    "（KOGL）　分析: socioscope"
)
SRC_COHORT = "出典: Eurostat demo_frate・IPSS 表 4-11・World Bank WDI　分析: socioscope"
SRC_OECD = "出典: OECD Family Database SF2.5（Childlessness）　分析: socioscope"

KIND_JA = {"N": "規範型", "C": "阻害型", "mixed": "どちらでもない"}
V2_JA = {
    "childlessness": "無子化型",
    "one_child": "1 人止まり型",
    "mixed": "混合",
    "no_decline": "低下なし",
}
KIND_COLOR = {"N": ORANGE, "C": BLUE_RAMP[4], "mixed": "#b5b5b5"}
V2_COLOR = {"childlessness": ORANGE, "one_child": BLUE_RAMP[4], "mixed": "#b5b5b5"}
ORDER_FOCUS = ("JPN", "KOR", "FIN", "SWE", "NOR", "ISL", "ITA", "ESP", "POL")
COHORT_FOCUS = ("JPN", "SWE", "FIN", "DNK", "ITA", "ESP")
CL_FOCUS = {
    "JPN": ORANGE,
    "ITA": BLUE_RAMP[2],
    "ESP": BLUE_RAMP[1],
    "FIN": BLUE_RAMP[4],
    "USA": INK,
}


# ---------------------------------------------------------------- pure helpers (tested)
def kind_ja(kind: str) -> str:
    return KIND_JA.get(kind) or V2_JA[kind]


def pick[T](rows: Sequence[T], iso3s: Sequence[str]) -> list[T]:
    """Rows whose `.iso3` is in `iso3s`, in the order of `iso3s` (missing ones skipped)."""
    by = {getattr(r, "iso3"): r for r in rows}  # noqa: B009
    return [by[i] for i in iso3s if i in by]


def by_year(
    tfr: Mapping[tuple[str, int], float], iso3: str, lo: int, hi: int
) -> list[tuple[int, float]]:
    return sorted((y, v) for (i, y), v in tfr.items() if i == iso3 and lo <= y <= hi)


def cohort_points(
    cum: Mapping[int, float], lo: int, hi: int, shift: int
) -> list[tuple[int, float]]:
    """(cohort + shift, completed) for cohorts in [lo, hi].

    Plotted at the year in which the cohort is `shift` years old."""
    return [(c + shift, v) for c, v in sorted(cum.items()) if lo <= c <= hi]


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    return base._plt()


def _note(fig: Any, text: str) -> None:
    fig.text(0.01, 0.045, text, fontsize=7.5, color=MUTED, ha="left")


def fig1_japan(series: Mapping[str, Sequence[tuple[int, float]]], path: Path) -> None:
    plt = _plt()
    ja = {
        "ideal (couples, JNFS)": ("夫婦の理想の子ども数", BLUE_RAMP[1], "o", "-"),
        "planned (couples, T04-25)": ("夫婦の予定の子ども数", ORANGE, "o", "-"),
        "desired (unmarried women, JNFS)": ("未婚女性の希望の子ども数", BLUE_RAMP[0], "^", "--"),
        "children born (couples, T04-24)": (
            "夫婦の出生子ども数（調査時点）",
            BLUE_RAMP[4],
            "s",
            "-",
        ),
        "completed, cohort aged 45 (T04-11, plotted at cohort+30)": (
            "女性全体の完結出生数（生まれ年 + 30 年の位置）",
            MUTED,
            "",
            "--",
        ),
        "period TFR (T04-16)": ("合計特殊出生率（その年）", INK, "", "-"),
    }
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    for key, (label, c, m, ls) in ja.items():
        pts = series[key]
        ax.plot(
            [p[0] for p in pts],
            [p[1] for p in pts],
            color=c,
            marker=m or None,
            markersize=4,
            linestyle=ls,
            linewidth=1.6,
            label=label,
        )
        last = pts[-1]
        ax.annotate(
            f"{last[1]:.2f}", last, xytext=(4, -3), textcoords="offset points", fontsize=8, color=c
        )
    ax.axhline(2.0, color=MUTED, lw=0.6)
    ax.set_xlabel("年（調査年）")
    ax.set_ylabel("子どもの数（人）")
    ax.legend(frameon=False, fontsize=8, loc="lower left", ncol=2)
    base._style(ax)
    fig.suptitle(
        "日本: 望む数・予定する数は 2 人前後、実際の出生率は 1.15 まで下がった",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "理想・予定・出生子ども数は妻 50 歳未満の初婚どうし夫婦（出生動向基本調査）。"
        "完結出生数は 45 歳までの累積で、1966 年（丙午）前後は年齢の数え方による段差がある。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    base._save(fig, path, SRC_JP)


def fig2_europe(
    rows: Sequence[h9.V1Row], pts: Mapping[str, Sequence[tuple[str, int, float]]], path: Path
) -> None:
    plt = _plt()
    rs = sorted(rows, key=lambda r: (r.last_ideal, r.iso3))
    fig, ax = plt.subplots(figsize=(9.6, 8.0))
    for i, r in enumerate(rs):
        c = KIND_COLOR[r.kind]
        vals = [v for _, y, v in pts[r.iso3]]
        ax.plot(vals, [i] * len(vals), color=c, lw=1.6)
        ax.scatter(vals[:-1], [i] * (len(vals) - 1), color="white", edgecolors=c, s=26, zorder=3)
        ax.scatter([vals[-1]], [i], color=c, s=34, zorder=3)
        ax.scatter([r.latest_tfr], [i], marker="x", color=INK, s=24, zorder=3)
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels(
        [f"{h9.COUNTRY_JA[r.iso3]}（{r.first_year}→{r.last_year}）" for r in rs], fontsize=8
    )
    ax.axvline(h9.N_IDEAL_MAX, color=ORANGE, ls=":", lw=1)
    ax.axvline(h9.C_IDEAL_MIN, color=BLUE_RAMP[4], ls=":", lw=1)
    for k in ("N", "C", "mixed"):
        n = sum(r.kind == k for r in rows)
        ax.scatter([], [], color=KIND_COLOR[k], s=30, label=f"{KIND_JA[k]}（{n} か国）")
    ax.scatter([], [], marker="x", color=INK, s=24, label="最新の合計特殊出生率")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_xlabel(
        "理想の子ども数の平均（白丸 = 古い調査、塗り = 最新。日本は夫婦の予定の子ども数）"
    )
    base._style(ax)
    fig.suptitle(
        f"理想の子ども数はほとんどの国で 2 人以上のまま（出生率 1.6 未満の {len(rows)} か国）",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    fig.text(
        0.01,
        0.035,
        "規範型 = 最新の理想が 2.1 未満で 0.2 以上下がった。"
        "阻害型 = 理想 2.2 以上で、理想と出生率の差が"
        " 0.6 以上かつ広がった。\n欧州は 2006 年（男女 25–39 歳）→ 2011 年（女性 25–39 歳）→"
        " 2020 年代（女性 30–39 歳）で質問と対象が違う。",
        fontsize=7.5,
        color=MUTED,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    base._save(fig, path, SRC_EU)


def fig3_order(main: Sequence[h9.V2Row], long: Sequence[h9.V2Row], path: Path) -> None:
    plt = _plt()
    rs = [r for r in pick(main, ORDER_FOCUS) if r.share is not None]
    lg = {r.iso3: r for r in long}
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    for i, r in enumerate(rs):
        share = float(r.share or 0)
        ax.barh(i, share, color=V2_COLOR[r.kind], height=0.6)
        ax.text(
            share + 0.01,
            i,
            f"{share:.0%}（出生率 {r.total_start:.2f}→{r.total_end:.2f}）",
            va="center",
            fontsize=8,
        )
        if r.iso3 in lg and lg[r.iso3].share is not None:
            ax.scatter([lg[r.iso3].share], [i], marker="D", color=INK, s=22, zorder=3)
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([f"{h9.COUNTRY_JA[r.iso3]}（{r.start}→{r.end}）" for r in rs], fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0.5, color=ORANGE, ls=":", lw=1)
    ax.axvline(0.4, color=BLUE_RAMP[4], ls=":", lw=1)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    handles: list[Any] = [
        Patch(color=V2_COLOR[k], label=V2_JA[k]) for k in ("childlessness", "mixed", "one_child")
    ]
    handles.append(
        Line2D([], [], marker="D", color=INK, ls="", label="1990 年からの低下で見た場合")
    )
    ax.legend(
        handles=handles,
        frameon=False,
        fontsize=8,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.09),
        ncol=4,
    )
    ax.set_xlim(0, 0.9)
    ax.set_xlabel("出生率の低下のうち、第 1 子の減少が占める割合")
    base._style(ax)
    fig.suptitle(
        "2010 年以降の低下の中身: 南欧は第 1 子、北欧・韓国は第 2 子以降が中心（日本はほぼ半々）",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "無子化型 = 第 1 子の寄与 50% 以上、1 人止まり型 = 第 2 子以降 60% 以上。"
        "韓国は順位別出生数の比で近似。期間の指標なので、出産の先送りも「減少」に含まれる。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    base._save(fig, path, SRC_ORDER)


def fig4_cohort(
    tfr: Mapping[tuple[str, int], float],
    cums: Mapping[str, Mapping[int, float]],
    v3: Sequence[h9.V3Row],
    path: Path,
) -> None:
    plt = _plt()
    rows = {r.iso3: r for r in v3}
    fig, axes = plt.subplots(2, 3, figsize=(10.4, 6.2), sharey=True)
    for ax, iso3 in zip(axes.flat, COHORT_FOCUS, strict=True):
        p = by_year(tfr, iso3, 1970, 2024)
        ax.plot([x for x, _ in p], [y for _, y in p], color=INK, lw=1.4, label="その年の出生率")
        c = cohort_points(cums[iso3], 1940, 1979, 30)
        ax.plot(
            [x for x, _ in c],
            [y for _, y in c],
            color=ORANGE,
            lw=2.0,
            label="女性が一生で産んだ数（生まれ年 + 30 年の位置）",
        )
        ax.axhline(2.0, color=MUTED, lw=0.6)
        r = rows[iso3]
        ax.set_title(
            f"{h9.COUNTRY_JA[iso3]}: 1975 年生 {r.c_last:.2f}／期間の最低 {r.min_tfr:.2f}",
            fontsize=8.5,
            loc="left",
        )
        ax.set_xlim(1970, 2025)
        base._style(ax)
    axes.flat[0].legend(frameon=False, fontsize=7.5, loc="lower left")
    fig.suptitle(
        "北欧は一生で産む数が 1.9 前後で保たれ、日本・南欧は 1.4 前後まで下がった",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "一生で産んだ数 = 45 歳までの年齢別出生率の累積（コーホート）。"
        "生まれ年 + 30 年の位置に描き、その年の出生率（期間）と並べた。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    base._save(fig, path, SRC_COHORT)


def fig5_childless(cl: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    sub = cl.filter((pl.col("chart") == "SF2.5.A") & (pl.col("metric") == "childless_share_pct"))
    sub = sub.sort(["iso3", "cohort"])
    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    for iso3 in sub["iso3"].unique().sort().to_list():
        s = sub.filter(pl.col("iso3") == iso3)
        c = CL_FOCUS.get(iso3, "#d0d0d0")
        ax.plot(
            s["cohort"].to_list(),
            s["value"].to_list(),
            color=c,
            lw=2.0 if iso3 in CL_FOCUS else 0.9,
            marker="o",
            markersize=2.5,
        )
        if iso3 in CL_FOCUS:
            ax.annotate(
                f"{h9.COUNTRY_JA[iso3]} {float(s['value'][-1]):.0f}%",
                (int(s["cohort"][-1]), float(s["value"][-1])),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=8.5,
                color=c,
            )
    ax.set_xlim(1933, 1981)
    ax.set_xlabel("女性の生まれ年")
    ax.set_ylabel("子どもを持たなかった女性の割合（%）")
    base._style(ax)
    fig.suptitle(
        "子どもを持たない女性の割合: 日本は 1975 年生まれで 28%"
        "（この年の値がある OECD 加盟国で最高）",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(fig, "灰色の線はその他の OECD 加盟国。国により観測できる生まれ年が違う。")
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    base._save(fig, path, SRC_OECD)


# ---------------------------------------------------------------- driver
def run(data_dir: Path, fig_dir: Path) -> list[tuple[str, str]]:
    font = base.setup_matplotlib()
    print(f"font: {font}")
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = h9.load(data_dir)
    res = h9.compute(d)
    tfr = h9.tfr_lookup(d["panel"])
    captions: list[tuple[str, str]] = []

    series = h9.japan_series(d)
    fig1_japan(series, fig_dir / "h9s01_japan_ideal_planned_actual.png")
    ideal = series["ideal (couples, JNFS)"]
    plan = series["planned (couples, T04-25)"]
    single = series["desired (unmarried women, JNFS)"]
    ptfr = series["period TFR (T04-16)"]
    captions.append(
        (
            "h9s01_japan_ideal_planned_actual.png",
            f"日本の夫婦の理想の子ども数は {ideal[0][1]:.2f}（1977）→ {ideal[-1][1]:.2f}（2021）、"
            f"予定は {plan[0][1]:.2f} → {plan[-1][1]:.2f}、未婚女性の希望は {single[0][1]:.2f}"
            f"（1982）→ {single[-1][1]:.2f}。合計特殊出生率は {ptfr[0][1]:.2f}（1977）→ "
            f"{ptfr[-1][1]:.2f}（2024）。",
        )
    )

    pts = h9.v1_points(d["ideals"], d["survey"])
    fig2_europe(res.v1, pts, fig_dir / "h9s02_europe_ideals_types.png")
    n_k = {k: [h9.COUNTRY_JA[r.iso3] for r in res.v1 if r.kind == k] for k in ("N", "C", "mixed")}
    captions.append(
        (
            "h9s02_europe_ideals_types.png",
            f"出生率 1.6 未満で理想の子ども数が 2 時点以上ある {len(res.v1)} か国のうち、規範型は"
            f"{'・'.join(n_k['N'])}（予定の子ども数）の 1 か国、阻害型は{'・'.join(n_k['C'])}の "
            f"{len(n_k['C'])} か国、どちらでもない国が {len(n_k['mixed'])} か国。"
            f"最新の理想が 2 人を下回るのは {sum(r.last_ideal < 2.0 for r in res.v1)} か国"
            "（事後に追加した検証 H9）。",
        )
    )

    fig3_order(res.v2, res.v2_long, fig_dir / "h9s03_birth_order_decline.png")
    sh = {r.iso3: r.share for r in res.v2}
    lg = {r.iso3: r.share for r in res.v2_long}
    captions.append(
        (
            "h9s03_birth_order_decline.png",
            "2010 年以降の出生率の低下のうち第 1 子の減少が占める割合は、"
            f"スペイン {sh['ESP']:.0%}・イタリア {sh['ITA']:.0%}・日本 {sh['JPN']:.0%}、"
            f"フィンランド {sh['FIN']:.0%}・スウェーデン {sh['SWE']:.0%}・韓国 {sh['KOR']:.0%}"
            "（韓国は近似）。1990 年からで見ると日本 "
            f"{lg['JPN']:.0%}・韓国 {lg['KOR']:.0%}。{len(res.v2_shares)} か国の中央値は "
            f"{statistics.median(res.v2_shares):.1%}。",
        )
    )

    cums = {i: h9.eu_cohort_cum(d["coh"], i, h9.V3_AGE) for i in COHORT_FOCUS if i != "JPN"}
    cums["JPN"] = h9.jp_cohort_cum(d["jp"], h9.V3_AGE)
    fig4_cohort(tfr, cums, res.v3, fig_dir / "h9s04_cohort_vs_period.png")
    r3 = {r.iso3: r for r in res.v3}
    drop3 = {i: r.c_ref - r.c_last for i, r in r3.items() if r.c_ref is not None}
    captions.append(
        (
            "h9s04_cohort_vs_period.png",
            "1975 年生まれの女性が 45 歳までに産んだ数は、スウェーデン "
            f"{r3['SWE'].c_last:.2f}・フィンランド {r3['FIN'].c_last:.2f}・デンマーク "
            f"{r3['DNK'].c_last:.2f} に対し、日本 {r3['JPN'].c_last:.2f}・イタリア "
            f"{r3['ITA'].c_last:.2f}・スペイン {r3['ESP'].c_last:.2f}。1960 年生まれからの低下は"
            f"日本 {drop3['JPN']:.2f}、スウェーデン {drop3['SWE']:.2f}。",
        )
    )

    fig5_childless(d["cl"], fig_dir / "h9s05_childlessness_cohorts.png")
    cl = d["cl"].filter(
        (pl.col("chart") == "SF2.5.A") & (pl.col("metric") == "childless_share_pct")
    )
    v = {(r["iso3"], r["cohort"]): r["value"] for r in cl.iter_rows(named=True)}
    captions.append(
        (
            "h9s05_childlessness_cohorts.png",
            f"子どもを持たなかった女性の割合は、日本 {v[('JPN', 1955)]:.1f}%（1955 年生まれ）"
            f"→ {v[('JPN', 1975)]:.1f}%（1975 年生まれ）、フィンランド {v[('FIN', 1975)]:.1f}%、"
            f"イタリア {v[('ITA', 1975)]:.1f}%、米国 {v[('USA', 1955)]:.1f}% → "
            f"{v[('USA', 1975)]:.1f}%。",
        )
    )

    lines = ["# H9 記事用図のキャプション", "", SRC_JP, "", SRC_EU, "", SRC_ORDER, ""]
    lines += [SRC_COHORT, "", SRC_OECD, ""]
    lines += [f"- `{f}`: {cap}" for f, cap in captions]
    (fig_dir / "captions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f, cap in captions:
        print(f"caption {f}: {cap}")
    return captions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument(
        "--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures" / "summary_h9"
    )
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
