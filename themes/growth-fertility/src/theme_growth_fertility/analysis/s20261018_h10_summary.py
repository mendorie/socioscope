"""H10 の note 記事（part6、日本語・一般読者）用の図を生成する決定的スクリプト。

H10 レポート（reports/2026-10-18-h10-family-formation.md）の数値を、同じ mart から
a20261018_h10_family_formation の関数（`load`, `compute`, `b_cells`, `NONREG4`）で**再計算**して
5 枚の図にする（新しい推定は行わない。H10 スクリプトは無変更。乱数・現在時刻は使わない）。

    uv run python -m theme_growth_fertility.analysis.s20261018_h10_summary \
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures/summary_h10]

フォント検出・保存規約は s20261005_summary と同じ（関数を import。PNG メタデータの Software を
落としてバイト再現。sha256 はフォント環境に依存する）。純粋ヘルパ（rate_series, coef_items,
pt）は tests/test_summary_h10.py で検証する。
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261018_h10_family_formation as h10
from theme_growth_fertility.analysis import s20261005_summary as base

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
BLUE_RAMP, ORANGE, INK, MUTED = base.BLUE_RAMP, base.ORANGE, base.INK, base.MUTED

SRC_SHUGYO = "出典: 政府統計の総合窓口(e-Stat)、就業構造基本調査（総務省）を加工　分析: socioscope"
SRC_PREF = (
    "出典: 国立社会保障・人口問題研究所『人口統計資料集 2026』（PDL1.0）、e-Stat 就業構造基本調査・"
    "住宅・土地統計調査（総務省）、内閣府『県民経済計算』を加工　分析: socioscope"
)
SRC_OECD = (
    "出典: OECD（住宅価格・有期雇用・若年失業率・Family Database SF3.1）、Eurostat、IPSS、"
    "韓国 国家データ処　分析: socioscope"
)
SRC_LONG = (
    "出典: 国立社会保障・人口問題研究所『人口統計資料集 2026』表 6-24・6-12（PDL1.0）"
    "　分析: socioscope"
)

EMP_JA = {"total_pop": "男性 30〜34 歳 全体", "regular": "正社員（正規）", "nonregular": "非正規"}
EMP_COLOR = {"total_pop": INK, "regular": BLUE_RAMP[4], "nonregular": ORANGE}
X_JA = {
    "nonreg": "非正規の割合（男性）",
    "ln_rent": "家賃（民営借家）",
    "flfp": "若い女性の労働力率",
    "unemp": "失業率（男性）",
    "ln_inc": "1 人当たり県民所得",
    "temp": "有期雇用の割合（15〜24 歳）",
    "une": "若年失業率（15〜24 歳）",
    "hpi": "住宅価格の対所得比",
}
Y_JA = {"fagem": "女性の初婚年齢", "cmr": "婚姻率", "tfr1": "第 1 子の出生率"}


# ---------------------------------------------------------------- pure helpers (tested)
def rate_series(emp: pl.DataFrame, sex: str, age: str, employment: str) -> list[tuple[int, float]]:
    """(survey_year, never-married %) for one employment type; missing years are skipped."""
    sub = emp.filter(
        (pl.col("sex") == sex) & (pl.col("age_class") == age) & (pl.col("employment") == employment)
    )
    v = {(r["survey_year"], r["marital"]): float(r["persons"]) for r in sub.iter_rows(named=True)}
    years = sorted({y for y, _ in v})
    return [
        (y, 100 * v[(y, "never_married")] / v[(y, "total")])
        for y in years
        if (y, "total") in v and (y, "never_married") in v and v[(y, "total")] > 0
    ]


def coef_items(
    fit: h10.Fit | None, xs: Sequence[str], signs: Mapping[str, int]
) -> list[tuple[str, tuple[float, float, float, float] | None, bool]]:
    """(x, coef, passes predicted sign) for each regressor, in order."""
    out: list[tuple[str, tuple[float, float, float, float] | None, bool]] = []
    for x in xs:
        c = fit.coefs.get(x) if fit else None
        out.append((x, c, h10.passes(c, signs[x])))
    return out


def pt(x: float) -> str:
    """Percentage-point label with sign."""
    return f"{x:+.1f} ポイント"


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    return base._plt()


def _note(fig: Any, text: str) -> None:
    fig.text(0.01, 0.045, text, fontsize=7.5, color=MUTED, ha="left")


def fig1_rates(emp: pl.DataFrame, path: Path) -> dict[str, list[tuple[int, float]]]:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    series: dict[str, list[tuple[int, float]]] = {}
    for e in ("nonregular", "total_pop", "regular"):
        pts = rate_series(emp, "male", "30-34", e)
        series[e] = pts
        ax.plot(
            [p[0] for p in pts],
            [p[1] for p in pts],
            marker="o",
            lw=2,
            color=EMP_COLOR[e],
            label=EMP_JA[e],
        )
        for y, v in pts:
            ax.annotate(
                f"{v:.1f}%",
                (y, v),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color=EMP_COLOR[e],
            )
    c = h10.b_cells(emp, 2007, "male", ("30-34",), sum4=True)[("30-34", "nonregular")]
    ax.scatter(
        [2007],
        [100 * c[1] / c[0]],
        marker="o",
        facecolors="white",
        edgecolors=ORANGE,
        s=40,
        zorder=3,
    )
    ax.annotate(
        f"{100 * c[1] / c[0]:.1f}%（2007 年は\nパート・派遣など 4 区分の合計）",
        (2007, 100 * c[1] / c[0]),
        xytext=(6, -4),
        textcoords="offset points",
        fontsize=7.5,
        color=ORANGE,
    )
    ax.set_xticks([2007, 2012, 2017, 2022])
    ax.set_ylim(30, 90)
    ax.set_ylabel("未婚の割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="center right")
    base._style(ax)
    fig.suptitle(
        "30〜34 歳の男性の未婚率は、正社員でも非正規でも上がった",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "全体 = 働いている人 ＋ 働いていない人。正社員と非正規の差は「未婚だから非正規」という逆向"
        "きの関係も含む。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    base._save(fig, path, SRC_SHUGYO)
    return series


def fig2_decomp(rows: Sequence[tuple[str, h10.Decomp]], path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    for i, (_, dc) in enumerate(rows):
        pos = neg = 0.0
        for val, col in ((dc.rate, BLUE_RAMP[3]), (dc.emp_comp, ORANGE), (dc.age_comp, "#b5b5b5")):
            v = 100 * val
            if v >= 0:
                ax.barh(i, v, left=pos, color=col, height=0.55)
                pos += v
            else:
                ax.barh(i, v, left=neg, color=col, height=0.55)
                neg += v
        ax.text(pos + 0.15, i, f"上昇 {pt(100 * dc.total)}", va="center", fontsize=8.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([t for t, _ in rows], fontsize=9)
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("未婚率の変化（ポイント）")
    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(color=BLUE_RAMP[3], label="同じ働き方の中で未婚が増えた分"),
            Patch(color=ORANGE, label="働き方の構成が変わった分"),
            Patch(color="#b5b5b5", label="年齢構成が変わった分"),
        ],
        frameon=False,
        fontsize=8,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.13),
        ncol=3,
    )
    base._style(ax)
    fig.suptitle(
        "男性の未婚化は、ほぼ全部が「同じ働き方の中」で起きた",
        fontsize=11,
        x=0.01,
        ha="left",
        y=0.99,
    )
    _note(
        fig,
        "Kitagawa 分解。働き方 = 正規・非正規・その他（自営・役員・無業）。男性は非正規の割合が下が"
        "ったので構成の分はマイナス。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.9))
    base._save(fig, path, SRC_SHUGYO)


def _dots(
    ax: Any, items: Sequence[tuple[str, tuple[float, float, float, float] | None, bool]]
) -> None:
    for i, (_, c, ok) in enumerate(items):
        if c is None:
            continue
        col = ORANGE if ok else BLUE_RAMP[2]
        ax.plot([c[2], c[3]], [i, i], color=col, lw=2)
        ax.scatter([c[0]], [i], color=col, s=30, zorder=3)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([X_JA[x] for x, _, _ in items], fontsize=8.5)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.invert_yaxis()
    base._style(ax)


def fig3_pref(main: h10.Fit | None, inc: h10.Fit | None, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    _dots(axes[0], coef_items(main, h10.C_X, h10.C_SIGN))
    axes[0].set_title(
        f"30〜34 歳男性の未婚率（{main.n if main else 0} 件"
        f"、{'・'.join(map(str, main.times)) if main else ''} 年）",
        fontsize=9,
        loc="left",
    )
    _dots(axes[1], coef_items(inc, (*h10.C_X, "ln_inc"), h10.C_SIGN))
    axes[1].set_title("所得を加えた場合", fontsize=9, loc="left")
    for ax in axes:
        ax.set_xlabel("説明変数が 1 標準偏差高いときの未婚率の差（ポイント）", fontsize=8)
    fig.suptitle(
        "都道府県で比べても、非正規・家賃・失業と未婚率の上がり方にはっきりした関連は見えない",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "47 都道府県、都道府県と年の固定効果。線は 95% 信頼区間。オレンジ = 事前に決めた向きで 0 を"
        "含まない（該当なし）。"
        "女性の労働力率は逆向き。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    base._save(fig, path, SRC_PREF)


def fig4_country(a: Mapping[str, h10.Fit | None], path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.0), sharey=True)
    for ax, y in zip(axes, h10.A_Y, strict=True):
        f = a[y]
        signs = dict.fromkeys(h10.A_X, h10.A_SIGN[y])
        _dots(ax, coef_items(f, h10.A_X, signs))
        arrow = "上がる" if h10.A_SIGN[y] > 0 else "下がる"
        ax.set_title(
            f"{Y_JA[y]}（予測: {arrow}）\n{f.n if f else 0} 区間・{f.groups if f else 0} か国",
            fontsize=9,
            loc="left",
        )
        ax.set_xlabel("1 標準偏差あたり（5 年の変化）", fontsize=8)
    fig.suptitle(
        "国の間で比べると、若年失業が増えた時期に婚姻率と第 1 子が下がっている",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(
        fig,
        "19 か国、1990〜2025 年の 5 年差分、国と期間の固定効果。オレンジ = 予測した向きで 95% 信頼"
        "区間が 0 を含まない。"
        "南欧の有期雇用と日本の非正規は制度が違う。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    base._save(fig, path, SRC_OECD)


def fig5_long(mar: pl.DataFrame, path: Path) -> dict[str, list[tuple[int, float]]]:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
    out: dict[str, list[tuple[int, float]]] = {}
    ax = axes[0]
    for sex, age, label, col in (
        ("M", "30-34", "男性 30〜34 歳", BLUE_RAMP[4]),
        ("F", "25-29", "女性 25〜29 歳", ORANGE),
        ("F", "30-34", "女性 30〜34 歳", "#f2a37f"),
    ):
        f = mar.filter(
            (pl.col("metric") == "never_married_share")
            & (pl.col("sex") == sex)
            & (pl.col("age_class") == age)
        ).sort("year")
        pts = list(zip(f["year"].to_list(), f["value"].to_list(), strict=True))
        out[f"{sex}{age}"] = pts
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=3, color=col, label=label)
    ax.set_ylabel("未婚の割合（%）")
    ax.set_title("未婚の割合（国勢調査）", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8)
    base._style(ax)
    ax = axes[1]
    for sex, label, col in (("M", "夫", BLUE_RAMP[4]), ("F", "妻", ORANGE)):
        f = mar.filter(
            (pl.col("metric") == "mean_age_first_marriage") & (pl.col("sex") == sex)
        ).sort("year")
        pts = list(zip(f["year"].to_list(), f["value"].to_list(), strict=True))
        out[f"afm_{sex}"] = pts
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=1.8, label=label)
    ax.set_ylabel("歳")
    ax.set_title("平均初婚年齢", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8)
    base._style(ax)
    fig.suptitle(
        "日本の未婚化は 1975 年ごろから 2010 年代まで一本調子で進んだ",
        fontsize=11,
        x=0.01,
        ha="left",
    )
    _note(fig, "1950・1960 年は沖縄県を含まない。")
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    base._save(fig, path, SRC_LONG)
    return out


def run(data_dir: Path, fig_dir: Path) -> list[tuple[str, str]]:
    font = base.setup_matplotlib()
    print(f"font: {font}")
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = h10.load(data_dir)
    res = h10.compute(d)
    caps: list[tuple[str, str]] = []

    s = fig1_rates(d["emp"], fig_dir / "h10s01_never_married_by_employment.png")
    tot, reg, non = s["total_pop"], s["regular"], s["nonregular"]
    caps.append(
        (
            "h10s01_never_married_by_employment.png",
            f"30〜34 歳男性の未婚率は全体で {tot[0][1]:.1f}%（2007）→ {tot[-1][1]:.1f}%（2022）、正"
            "社員 "
            f"{reg[0][1]:.1f}% → {reg[-1][1]:.1f}%、非正規 {non[0][1]:.1f}%（2012）→"
            f" {non[-1][1]:.1f}%。"
            f"2022 年の正社員と非正規の差は {abs(res.gap_2022):.1f} ポイント。",
        )
    )

    rows = [
        ("男性 25〜39 歳 2012→2022", res.b),
        ("男性 25〜39 歳 2007→2022", res.b_lower),
        ("女性 25〜39 歳 2012→2022", dict(res.b_rows)["women 25-39, 2012->2022"]),
    ]
    fig2_decomp(rows, fig_dir / "h10s02_kitagawa.png")
    w = rows[2][1]
    caps.append(
        (
            "h10s02_kitagawa.png",
            f"男性 25〜39 歳の未婚率の上昇 {pt(100 * res.b.total)}（2012→2022）のうち、同じ働き方の"
            "中での上昇が "
            f"{res.b.rate_share:.0%}、働き方の構成の変化は {res.b.comp_share:.0%}（非正規の割合が下"
            "がったため逆向き）。"
            f"女性は構成の分が {w.comp_share:.0%}（正社員の割合が上がり、正社員の女性は未婚率が高い"
            "）。",
        )
    )

    fig3_pref(res.c_main, res.c_inc, fig_dir / "h10s03_prefecture_coefficients.png")
    cm = res.c_main
    assert cm is not None
    caps.append(
        (
            "h10s03_prefecture_coefficients.png",
            f"47 都道府県・{'・'.join(map(str, cm.times))} 年の比較で、30〜34 歳男性の未婚率と、非"
            "正規の割合 "
            f"{cm.coefs['nonreg'][0]:+.2f}・家賃 {cm.coefs['ln_rent'][0]:+.2f}・失業率"
            f" {cm.coefs['unemp'][0]:+.2f}"
            f"（ポイント／1 標準偏差）はいずれも 95% 信頼区間が 0 を含む。若い女性の労働力率は "
            f"{cm.coefs['flfp'][0]:+.2f} で、予測と逆向き。",
        )
    )

    fig4_country(res.a, fig_dir / "h10s04_country_coefficients.png")
    a = {k: f for k, f in res.a.items() if f is not None}
    caps.append(
        (
            "h10s04_country_coefficients.png",
            "19 か国の 5 年差分で、若年失業率が 1 標準偏差多く増えた区間は婚姻率が "
            f"{a['cmr'].coefs['une'][0]:+.2f}（人口千人当たり）、第 1 子の出生率が"
            f" {a['tfr1'].coefs['une'][0]:+.3f}。"
            f"有期雇用は女性の初婚年齢 {a['fagem'].coefs['temp'][0]:+.2f} 歳だけ、住宅価格はどれも "
            "0 を含む。",
        )
    )

    lg = fig5_long(d["mar"], fig_dir / "h10s05_japan_long_run.png")
    m = dict(lg["M30-34"])
    af = dict(lg["afm_F"])
    caps.append(
        (
            "h10s05_japan_long_run.png",
            f"30〜34 歳男性の未婚率は {m[1970]:.1f}%（1970）→ {m[2020]:.1f}%（2020）、"
            f"妻の平均初婚年齢は {af[1970]:.1f} 歳 → {af[max(af)]:.1f} 歳（{max(af)}）。",
        )
    )

    lines = [
        "# H10 記事用図のキャプション",
        "",
        SRC_SHUGYO,
        "",
        SRC_PREF,
        "",
        SRC_OECD,
        "",
        SRC_LONG,
        "",
    ]
    lines += [f"- `{f}`: {c}" for f, c in caps]
    (fig_dir / "captions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for f, c in caps:
        print(f"caption {f}: {c}")
    return caps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument(
        "--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures" / "summary_h10"
    )
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
