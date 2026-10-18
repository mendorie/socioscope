"""H12 の note 記事（日本語・一般読者）用の図を生成する決定的スクリプト。

H12 レポート（reports/2026-10-18-h12-why-marriage-left.md）の数値を、同じ mart から
a20261018_h12_why_marriage_left の関数（`load`, `compute`, `rows`, `pct`, `no_partner`,
`reasons`, `couples`）で**再計算**して 5 枚の図にする（新しい推定は行わない。H12 スクリプトは
無変更。乱数・現在時刻は使わない）。

    uv run python -m theme_growth_fertility.analysis.s20261018_h12_summary \
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures/summary_h12]

フォント検出・保存規約は s20261005_summary と同じ（関数を import。PNG メタデータの Software を
落としてバイト再現。sha256 はフォント環境に依存する）。純粋ヘルパ（ci_series）は
tests/test_summary_h12.py で検証する。
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261018_h12_why_marriage_left as h12
from theme_growth_fertility.analysis import s20261005_summary as base

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
BLUE_RAMP, ORANGE, INK, MUTED = base.BLUE_RAMP, base.ORANGE, base.INK, base.MUTED
SEX_JA = {"male": "男性", "female": "女性"}
SEX_COL = {"male": BLUE_RAMP[3], "female": ORANGE}

SRC_IPSS = (
    "出典: 国立社会保障・人口問題研究所『第 16 回出生動向基本調査 報告書』グラフデータ（PDL1.0）を加工"  # noqa: E501
    "　分析: socioscope"
)
SRC_NHK = (
    "NHK放送文化研究所「日本人の意識」調査（https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/）"
    "を加工して作成"
)
SRC_K4 = (
    "出典: IPSS『第 16 回出生動向基本調査 報告書』グラフデータ・『人口統計資料集 2026』表 6-1（PDL1.0）、"  # noqa: E501
    "こども家庭庁（2024）、リクルートブライダル総研（2024）、明治安田（2025）　分析: socioscope"
)


# ---------------------------------------------------------------- pure helpers (tested)
def ci_series(df: pl.DataFrame) -> list[tuple[int, float, float, float]]:
    """(survey year, share, CI low, CI high) sorted by year."""
    f = df.sort("survey_year")
    return [
        (int(y), float(v), float(lo), float(hi))
        for y, v, lo, hi in f.select("survey_year", "share_pct", "ci_low", "ci_high").iter_rows()
    ]


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    return base._plt()


def _note(fig: Any, text: str) -> None:
    fig.text(0.01, 0.06, text, fontsize=7.5, color=MUTED, ha="left")


def _label_ends(ax: Any, xs: Sequence[int], vs: Sequence[float], col: str) -> None:
    for x, v in ((xs[0], vs[0]), (xs[-1], vs[-1])):
        ax.annotate(
            f"{v:.1f}%",
            (x, v),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=col,
        )


def fig1_intention(att: pl.DataFrame, nhk: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    ax = axes[0]
    for s in h12.SEXES:
        for item, ls, lab in (
            (h12.INTEND, "-", "いずれ結婚するつもり"),
            (h12.NEVER, "--", "一生結婚するつもりはない"),
        ):
            pts = ci_series(h12.rows(att, "1_1_1", sex=s, item=item))
            xs = [p[0] for p in pts]
            ax.fill_between(
                xs, [p[2] for p in pts], [p[3] for p in pts], color=SEX_COL[s], alpha=0.2, lw=0
            )
            ax.plot(
                xs,
                [p[1] for p in pts],
                ls,
                marker="o",
                ms=3,
                color=SEX_COL[s],
                label=f"{SEX_JA[s]}：{lab}",
            )
            _label_ends(ax, xs, [p[1] for p in pts], SEX_COL[s])
    ax.set_ylim(0, 105)
    ax.set_ylabel("18〜34 歳の未婚者に占める割合（%）")
    ax.set_title("未婚者の結婚意思（帯は 95% 信頼区間）", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7.5, loc="center right")
    base._style(ax)
    ax = axes[1]
    for g, col, lab in (
        ("all", INK, "全体"),
        ("male", BLUE_RAMP[3], "男性"),
        ("female", ORANGE, "女性"),
    ):
        pts2 = h12.nhk_series(nhk, g)
        ax.plot([p[0] for p in pts2], [p[1] for p in pts2], marker="o", ms=3, color=col, label=lab)
        _label_ends(ax, [p[0] for p in pts2], [p[1] for p in pts2], col)
    ax.set_ylim(0, 105)
    ax.set_ylabel("「人は結婚するのが当然だ」の割合（%）")
    ax.set_title("一般の人々（16 歳以上）の結婚観", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8)
    base._style(ax)
    fig.suptitle(
        "結婚するつもりの未婚者は 8 割台で多数のまま、「するのが当然」という規範は弱まった",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(fig, "右: " + SRC_NHK + "（1993〜2018 年）。")
    fig.tight_layout(rect=(0, 0.09, 1, 0.93))
    base._save(fig, path, SRC_IPSS)


def fig2_partner(att: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    ax = axes[0]
    years = sorted(h12.rows(att, "2_1_2")["survey_year"].unique().to_list())
    for s in h12.SEXES:
        vs = [h12.no_partner(att, y, s) for y in years]
        ax.plot(years, vs, marker="o", ms=3, color=SEX_COL[s], label=SEX_JA[s])
        _label_ends(ax, years, vs, SEX_COL[s])
    ys = (2010, 2015, 2021)
    for s in h12.SEXES:
        want = [
            h12.pct(att, "2_1_2", survey_year=y, sex=s, age="18～34歳（総数）", item=h12.WANT)
            for y in ys
        ]
        ax.plot(
            ys, want, ":", marker="s", ms=3, color=SEX_COL[s], label=f"{SEX_JA[s]}：うち交際を望む"
        )
    ax.set_ylim(0, 100)
    ax.set_ylabel("18〜34 歳の未婚者に占める割合（%）")
    ax.set_title(
        "交際相手がいない人（点線: そのうち交際を望む人、2010 年から）", fontsize=9, loc="left"
    )
    ax.legend(frameon=False, fontsize=7.5)
    base._style(ax)
    ax = axes[1]
    ys2 = sorted(h12.rows(att, "1_3_2")["survey_year"].unique().to_list())
    for s in h12.SEXES:
        vs = [float(h12.reasons(att, y, s)[h12.MEET] or 0.0) for y in ys2]
        ax.plot(ys2, vs, marker="o", ms=3, color=SEX_COL[s], label=SEX_JA[s])
        _label_ends(ax, ys2, vs, SEX_COL[s])
    ax.set_ylim(0, 70)
    ax.set_ylabel("挙げた人の割合（%、3 つまで選択）")
    ax.set_title(
        "独身でいる理由「適当な相手にまだめぐり会わない」（25〜34 歳、毎回 1 位）",
        fontsize=9,
        loc="left",
    )
    ax.legend(frameon=False, fontsize=8)
    base._style(ax)
    fig.suptitle(
        "交際相手がいない未婚者は 3 割台から 6〜7 割に増え、増えた分は「望まない」側",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "1982 年は交際希望の設問なし。独身の理由は 1992 年から、結婚する意思のある未婚者が対象。",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.93))
    base._save(fig, path, SRC_IPSS)


def fig3_benefits(att: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    items = (
        (h12.FAMILY, "子どもや家族をもてる"),
        (h12.ECON, "経済的に余裕がもてる"),
        ("精神的な安らぎの場が得られる", "精神的な安らぎの場"),
    )
    width = 0.2
    for j, (s, y) in enumerate(
        (("male", 1987), ("male", 2021), ("female", 1987), ("female", 2021))
    ):
        vs = [h12.pct(att, "1_2_1", survey_year=y, sex=s, item=it) for it, _ in items]
        col = SEX_COL[s]
        xs = [i + (j - 1.5) * width for i in range(len(items))]
        ax.bar(
            xs,
            vs,
            width=width * 0.95,
            color=col,
            alpha=0.45 if y == 1987 else 1.0,
            label=f"{SEX_JA[s]} {y} 年",
        )
        for x, v in zip(xs, vs, strict=True):
            ax.text(x, v + 0.8, f"{v:.0f}", ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(range(len(items)))
    ax.set_xticklabels([lab for _, lab in items], fontsize=9)
    ax.set_ylabel("結婚の利点として選んだ割合（%、2 つまで）")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    base._style(ax)
    fig.suptitle(
        "女性が結婚の利点に「経済的な余裕」を挙げる割合は 7% から 21% に増えた",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "18〜34 歳の未婚者。「利点はない」の選択肢はグラフデータに無く、"
        "「利点があると思う人」の割合は比べられない。",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.93))
    base._save(fig, path, SRC_IPSS)


def fig4_meeting(att: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    keys = [
        ("1982 年調査", h12.couples(att, 1982)),
        ("2002 年調査", h12.couples(att, 2002)),
        ("2015/7〜18/6 結婚", h12.couples(att, 2021, h12.P16A)),
        ("2018/7〜21/6 結婚", h12.couples(att, 2021, h12.P16B)),
    ]
    groups = (
        (h12.OMIAI, "見合い・結婚相談所", BLUE_RAMP[-1]),
        (h12.WORK, "職場・仕事", BLUE_RAMP[1]),
        (h12.NET, "ネット", ORANGE),
    )
    left = [0.0] * len(keys)
    for item, lab, col in groups:
        vals = [c.get(item, 0.0) for _, c in keys]
        ax.barh(range(len(keys)), vals, left=left, color=col, height=0.6, label=lab)
        for i, (v, lft) in enumerate(zip(vals, left, strict=True)):
            if v >= 3:
                ax.text(
                    lft + v / 2, i, f"{v:.1f}", ha="center", va="center", fontsize=8, color="white"
                )
        left = [a + b for a, b in zip(left, vals, strict=True)]
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([k for k, _ in keys], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("結婚 5 年未満の夫婦に占める割合（%）。残りは友人・学校・街なか等")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    base._style(ax)
    fig.suptitle(
        "見合いと職場で出会った夫婦は 55% から 30% に、ネットは 14%", fontsize=11, x=0.01, ha="left"
    )
    _note(
        fig,
        "「ネットで」は最新回で新設。2021 年調査は見合いに結婚相談所（オンラインを含む）を含む。"
        "2018/7〜21/6 はコロナ下の婚姻減の時期。",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.93))
    base._save(fig, path, SRC_IPSS)


def fig5_fill(res: h12.H12Result, path: Path) -> list[tuple[str, float]]:
    plt = _plt()
    sens = dict(res.k4_sens)
    items = [
        ("本体（出生動向基本調査、ネット 13.6%）", res.main.k4.rate),
        ("上限（見合い・相談所を損失から除き補填へ）", sens["upper (agency incl.)"].rate),
        ("上限（見合い・相談所を補填に足すだけ）", sens["upper literal"].rate),
        ("こども家庭庁 2024（アプリ 25.1%）", sens["cfa2024"].rate),
        ("リクルート 2024（ネット系 11.4%）", sens["recruit2024"].rate),
        ("明治安田 2025（アプリ 30.4%）", sens["meiji2025"].rate),
    ]
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    for i, (_, r) in enumerate(items):
        ax.barh(i, 100 * r, color=ORANGE if i == 0 else BLUE_RAMP[2], height=0.6)
        ax.text(100 * r + 1, i, f"{100 * r:.0f}%", va="center", fontsize=9, color=INK)
    for x, t in ((20, "2 割"), (50, "5 割")):
        ax.axvline(x, color=MUTED, ls=":", lw=1)
        ax.text(x, -0.7, t, ha="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([t for t, _ in items], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("ネットで出会った結婚 ÷ 見合い・職場経由で減った結婚（年あたり件数、%）")
    base._style(ax)
    fig.suptitle(
        "見合い・職場で減った結婚のうち、ネットが補ったのは約 4 分の 1（25%）",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    m = res.main.k4
    _note(
        fig,
        f"件数 = 構成比 × 妻の初婚件数（年平均: 1977/7〜82/6 {m.n0:,.0f}、2018/7〜21/6 "
        f"{m.n1:,.0f}）。民間調査はネット調査で、構成比だけを置き換えた。",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.93))
    base._save(fig, path, SRC_K4)
    return items


def run(data_dir: Path, fig_dir: Path) -> list[tuple[str, str]]:
    font = base.setup_matplotlib()
    print(f"font: {font}")
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = h12.load(data_dir)
    att, nhk = d["att"], d["nhk"]
    res = h12.compute(d)
    caps: list[tuple[str, str]] = []

    fig1_intention(att, nhk, fig_dir / "h12s01_intention.png")
    k1 = res.main.k1
    nhk_all = h12.nhk_series(nhk, "all")
    caps.append(
        (
            "h12s01_intention.png",
            f"「いずれ結婚するつもり」の未婚者（18〜34 歳）は 1982→2021 年に男性 {k1['male'].v0:.1f}% → "  # noqa: E501
            f"{k1['male'].v1:.1f}%、女性 {k1['female'].v0:.1f}% → {k1['female'].v1:.1f}%"
            f"（女性の低下 {abs(k1['female'].delta):.1f} ポイントは事前の基準 10 ポイントにわずかに届かない）。"  # noqa: E501
            f"「人は結婚するのが当然」は一般の人々で {nhk_all[0][1]:.0f}%（1993）→ {nhk_all[-1][1]:.0f}%（2018）。",  # noqa: E501
        )
    )

    fig2_partner(att, fig_dir / "h12s02_no_partner.png")
    r = res.main.k2_rise
    caps.append(
        (
            "h12s02_no_partner.png",
            f"交際相手がいない未婚者は男性 {h12.no_partner(att, 1982, 'male'):.1f}% → "
            f"{h12.no_partner(att, 2021, 'male'):.1f}%（{r['male']:+.1f}）、女性 "
            f"{h12.no_partner(att, 1982, 'female'):.1f}% → {h12.no_partner(att, 2021, 'female'):.1f}%"  # noqa: E501
            f"（{r['female']:+.1f}）。2010→2021 年に「交際を望む」はほぼ横ばいで、増えたのは「望まない」。"  # noqa: E501
            "独身の理由の 1 位は 1992 年以降毎回「適当な相手にまだめぐり会わない」"
            f"（2021 年 25〜34 歳で男性 {h12.reasons(att, 2021, 'male')[h12.MEET]}%、"
            f"女性 {h12.reasons(att, 2021, 'female')[h12.MEET]}%）。",
        )
    )

    fig3_benefits(att, fig_dir / "h12s03_benefits.png")
    caps.append(
        (
            "h12s03_benefits.png",
            "結婚の利点に「経済的に余裕がもてる」を挙げる未婚女性は 1987→2021 年に "
            f"{h12.pct(att, '1_2_1', survey_year=1987, sex='female', item=h12.ECON)}% → "
            f"{h12.pct(att, '1_2_1', survey_year=2021, sex='female', item=h12.ECON)}% で、下がっていない。"  # noqa: E501
            "「子どもや家族をもてる」は男女とも上がった。女性側で結婚の評価が下がったことを示す変化は、"
            "測った指標には見られない。",
        )
    )

    fig4_meeting(att, fig_dir / "h12s04_meeting.png")
    c0, c1 = h12.couples(att, 1982), h12.couples(att, 2021, h12.P16B)
    caps.append(
        (
            "h12s04_meeting.png",
            f"結婚 5 年未満の夫婦の出会いは、見合い＋職場が {c0[h12.OMIAI] + c0[h12.WORK]:.1f}%（1982 年調査）→ "  # noqa: E501
            f"{c1[h12.OMIAI] + c1[h12.WORK]:.1f}%（2018/7〜21/6 結婚）、ネットは {c1[h12.NET]:.1f}%"
            "（「ネットで」は最新回で新設、見合いは結婚相談所を含む）。",
        )
    )

    items = fig5_fill(res, fig_dir / "h12s05_fill_rate.png")
    m = res.main.k4
    caps.append(
        (
            "h12s05_fill_rate.png",
            f"見合い・職場経由で減った結婚は年 {m.loss:,.0f} 件、ネット経由は年 {m.filled:,.0f} 件で、補填率は "  # noqa: E501
            f"{h12.wari(m.rate)}（事前の基準で「部分的」。CI は未算出）。"
            "終点を 2015/7〜18/6 にすると 15% で「補われていない」に変わる。感度の各版は "
            + "、".join(f"{100 * r:.0f}%" for _, r in items[1:])
            + "。",
        )
    )

    lines = ["# H12 記事用図のキャプション", "", SRC_IPSS, "", SRC_NHK, "", SRC_K4, ""]
    lines += [f"- `{f}`: {c}" for f, c in caps]
    (fig_dir / "captions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f, cap in caps:
        print(f"caption {f}: {cap}")
    return caps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument(
        "--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures" / "summary_h12"
    )
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
