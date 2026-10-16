"""note 記事のヘッダー画像（1280×670）を marts から決定的に生成する。

実行: uv run python docs/articles/headers/make_headers.py
出力: docs/articles/headers/<article>.png
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[3]
MARTS = ROOT / "data" / "marts"
OUT = Path(__file__).resolve().parent

W, H, DPI = 1280, 670, 100
BLUE, ORANGE, INK, MUTED, PAPER = "#256abf", "#eb6834", "#1f2a37", "#8a94a3", "#f7f5f0"
FONT = "Hiragino Sans"

matplotlib.rcParams["font.family"] = FONT
matplotlib.rcParams["axes.unicode_minus"] = False


def canvas() -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(PAPER)
    bg = fig.add_axes([0, 0, 1, 1])
    bg.set_axis_off()
    bg.patch.set_alpha(0)
    bg.set_zorder(10)
    bg.set_xlim(0, W)
    bg.set_ylim(0, H)
    return fig, bg


def title_block(bg: plt.Axes, title: str, sub: str, *, y: float = 600, size: float = 40) -> None:
    bg.text(64, y, title, fontsize=size, fontweight=900, color=INK, va="top", ha="left")
    bg.text(66, y - 70, sub, fontsize=17, color=MUTED, va="top", ha="left")


def tag(bg: plt.Axes, x: float, y: float, text: str, color: str) -> None:
    bg.text(
        x,
        y,
        text,
        fontsize=15,
        fontweight="bold",
        color="white",
        va="center",
        ha="left",
        bbox={"boxstyle": "round,pad=0.5,rounding_size=0.9", "fc": color, "ec": "none"},
    )


def growth_fertility() -> Path:
    panel = pl.read_parquet(MARTS / "growth_fertility_panel.parquet")
    w = panel.filter(
        (pl.col("year") == 2024)
        & pl.col("tfr").is_not_null()
        & pl.col("gdp_pcap_ppp").is_not_null()
    ).filter(pl.col("population") >= 1_000_000)
    jp = (
        pl.read_parquet(MARTS / "jp_income_class_fertility.parquet")
        .filter(
            (pl.col("metric") == "married_share")
            & (pl.col("sex") == "male")
            & (pl.col("year") == 2024)
            & pl.col("income_class_lower_yen").is_not_null()
        )
        .sort("income_class_lower_yen")
    )

    fig, bg = canvas()
    title_block(
        bg,
        "豊かになると、子どもは減るのか？",
        "世界 217 か国と日本の所得階層を同じ物差しで見たら、向きが逆だった",
    )

    # left: between countries
    ax1 = fig.add_axes([0.07, 0.12, 0.38, 0.55])
    x = np.log(w["gdp_pcap_ppp"].to_numpy())
    y = w["tfr"].to_numpy()
    s = np.sqrt(w["population"].to_numpy() / 1e6) * 3 + 8
    is_jp = (w["iso3"] == "JPN").to_numpy()
    ax1.scatter(x[~is_jp], y[~is_jp], s=s[~is_jp], c=BLUE, alpha=0.35, lw=0)
    ax1.scatter(x[is_jp], y[is_jp], s=s[is_jp] + 40, c=ORANGE, lw=0, zorder=5)
    b, a = np.polyfit(x, y, 1)
    xs = np.linspace(x.min(), x.max(), 2)
    ax1.plot(xs, a + b * xs, color=BLUE, lw=5, solid_capstyle="round")
    ax1.annotate(
        "日本",
        (x[is_jp][0], y[is_jp][0]),
        xytext=(12, -14),
        textcoords="offset points",
        fontsize=13,
        color=ORANGE,
        fontweight="bold",
    )
    ax1.set_xticks([math.log(v) for v in (1000, 10000, 100000)])
    ax1.set_xticklabels(["$1,000", "$10,000", "$100,000"], fontsize=11, color=MUTED)
    ax1.set_yticks([1, 2, 3, 4, 5, 6])
    ax1.tick_params(colors=MUTED, labelsize=11, length=0)
    ax1.set_ylim(0.5, 7)
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_facecolor(PAPER)
    tag(bg, 92, 470, "国の間：豊かな国ほど、子どもが少ない", BLUE)

    # right: within Japan
    ax2 = fig.add_axes([0.59, 0.12, 0.36, 0.55])
    vals = jp["value"].to_numpy() * 100
    idx = np.arange(len(vals))
    ax2.bar(idx, vals, color=ORANGE, width=0.72, alpha=0.9)
    ax2.set_xticks([0, 5, 10, len(vals) - 1])
    ax2.set_xticklabels(["〜50 万円", "300 万", "600 万", "1,000 万〜"], fontsize=11, color=MUTED)
    ax2.set_yticks([25, 50, 75])
    ax2.set_yticklabels(["25%", "50%", "75%"], fontsize=11, color=MUTED)
    ax2.tick_params(colors=MUTED, length=0)
    ax2.set_ylim(0, 100)
    for sp in ax2.spines.values():
        sp.set_visible(False)
    ax2.set_facecolor(PAPER)
    ax2.grid(axis="y", color="#e2ddd3", lw=1)
    ax2.set_axisbelow(True)
    tag(bg, 720, 470, "日本の中：所得が高いほど、結婚している", ORANGE)

    bg.text(
        612,
        250,
        "≠",
        fontsize=72,
        fontweight="bold",
        color=INK,
        ha="center",
        va="center",
        alpha=0.85,
    )
    bg.text(
        W - 40,
        18,
        "出典: World Bank WDI, 国民生活基礎調査 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-05-note-growth-fertility.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def wealth() -> Path:
    panel = (
        pl.read_parquet(MARTS / "wealth_population_panel.parquet")
        .filter(
            (pl.col("year") >= 1950)
            & (pl.col("year") <= 2024)
            & pl.col("top1_wealth_share").is_not_null()
        )
        .sort(["iso3", "year"])
    )
    fig, bg = canvas()
    title_block(
        bg,
        "「金持ちはますます金持ちに」は本当か？",
        "46 か国・75 年分の「上位 1% の資産シェア」を、同じ基準で数えてみた",
    )

    ax = fig.add_axes([0.06, 0.10, 0.60, 0.58])
    for iso3, g in panel.group_by("iso3", maintain_order=True):
        yrs = g["year"].to_numpy()
        v = g["top1_wealth_share"].to_numpy() * 100
        if len(yrs) < 10:
            continue
        key = iso3[0]
        if key == "JPN":
            ax.plot(yrs, v, color=ORANGE, lw=3.5, zorder=6)
            ax.annotate(
                "日本",
                (yrs[-1], v[-1]),
                xytext=(8, 0),
                textcoords="offset points",
                fontsize=13,
                color=ORANGE,
                fontweight="bold",
                va="center",
            )
        elif key == "USA":
            ax.plot(yrs, v, color=BLUE, lw=3.5, zorder=5)
            ax.annotate(
                "アメリカ",
                (yrs[-1], v[-1]),
                xytext=(8, 0),
                textcoords="offset points",
                fontsize=13,
                color=BLUE,
                fontweight="bold",
                va="center",
            )
        else:
            ax.plot(yrs, v, color=MUTED, lw=1.2, alpha=0.3)
    ax.set_xlim(1950, 2034)
    ax.set_ylim(5, 75)
    ax.set_xticks([1950, 1980, 2024])
    ax.set_yticks([20, 40, 60])
    ax.set_yticklabels(["20%", "40%", "60%"])
    ax.tick_params(colors=MUTED, labelsize=11, length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor(PAPER)
    ax.grid(axis="y", color="#e2ddd3", lw=1)
    ax.set_axisbelow(True)
    tag(bg, 80, 470, "上位 1% が持つ資産の割合、46 か国（1950〜2024 年）", INK)

    # stat tile
    bg.add_patch(
        FancyBboxPatch(
            (880, 120), 340, 300, boxstyle="round,pad=0,rounding_size=18", fc="white", ec="#e2ddd3"
        )
    )
    bg.text(1050, 385, "「U 字型」に戻った国は", fontsize=15, color=MUTED, ha="center", va="center")
    bg.text(1050, 290, "12", fontsize=86, fontweight=900, color=BLUE, ha="center", va="center")
    bg.text(
        1050, 215, "／ 46 か国", fontsize=22, fontweight="bold", color=INK, ha="center", va="center"
    )
    bg.text(
        1050,
        160,
        "多数派ではなかった。\nでも「1980 年以降に上がった」は 76%。",
        fontsize=12,
        color=MUTED,
        ha="center",
        va="center",
        linespacing=1.6,
    )
    bg.text(
        W - 40,
        18,
        "出典: WID.world（CC BY-NC-SA 4.0）/ socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-05-note-wealth-population-distribution.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def growth_fertility_h7() -> Path:
    """H7: 転換開始時の所得のばらつき（左）と、転換が終わった国の間の平らな関係（右）。"""
    import sys

    sys.path.insert(0, str(ROOT / "themes" / "growth-fertility" / "src"))
    from theme_growth_fertility.transition import onset_table

    panel = pl.read_parquet(MARTS / "growth_fertility_panel.parquet")
    onset = {
        r["iso3"]: r["onset_year"]
        for r in onset_table(panel.select("iso3", "year", "tfr").to_dicts())
        if r["onset_year"] is not None
    }
    at_onset = np.array(
        [
            r["gdp_pcap_const"]
            for r in panel.filter(pl.col("gdp_pcap_const").is_not_null())
            .select("iso3", "year", "gdp_pcap_const")
            .to_dicts()
            if onset.get(r["iso3"]) == r["year"]
        ]
    )
    p10, p90 = np.percentile(at_onset, 10), np.percentile(at_onset, 90)

    w = panel.filter(
        (pl.col("year") == 2024)
        & pl.col("tfr").is_not_null()
        & pl.col("gdp_pcap_ppp").is_not_null()
        & pl.col("u5_mortality").is_not_null()
        & (pl.col("population") >= 1_000_000)
    )
    done = (w["u5_mortality"] < 10).to_numpy()

    fig, bg = canvas()
    title_block(
        bg,
        "豊かな国ほど子どもが少ないのは、豊かさのせいではない",
        "下がり始めた年の所得は国によって 21.6 倍違い、転換が終わった国の間では関係が消える",
        size=33,
    )

    # left: income at transition onset (log histogram)
    ax1 = fig.add_axes([0.07, 0.13, 0.40, 0.52])
    bins = np.logspace(np.log10(150), np.log10(40000), 22)
    ax1.hist(at_onset, bins=bins, color=BLUE, alpha=0.85, lw=0)
    ax1.set_xscale("log")
    top = ax1.get_ylim()[1] * 1.35
    ax1.set_ylim(0, top)
    for v, lab in ((p10, "下位 10%"), (p90, "上位 10%")):
        ax1.axvline(v, color=ORANGE, lw=2.5, ls="--")
        ax1.text(
            v,
            top * 0.99,
            f"{lab}\n${v:,.0f}",
            color=ORANGE,
            fontsize=11,
            ha="center",
            va="top",
            fontweight="bold",
        )
    ax1.set_xticks([300, 1000, 3000, 10000, 30000])
    ax1.set_xticklabels(
        ["$300", "$1,000", "$3,000", "$10,000", "$30,000"], fontsize=11, color=MUTED
    )
    ax1.set_yticks([])
    ax1.tick_params(colors=MUTED, length=0)
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_facecolor(PAPER)
    tag(bg, 92, 470, f"出生率が下がり始めた年の一人当たり GDP（{len(at_onset)} か国）", BLUE)

    # right: TFR vs GDP 2024, completed-transition countries highlighted with flat fit
    ax2 = fig.add_axes([0.57, 0.13, 0.38, 0.52])
    x = np.log(w["gdp_pcap_ppp"].to_numpy())
    y = w["tfr"].to_numpy()
    s = np.sqrt(w["population"].to_numpy() / 1e6) * 3 + 8
    ax2.scatter(x[~done], y[~done], s=s[~done], c=MUTED, alpha=0.25, lw=0)
    ax2.scatter(x[done], y[done], s=s[done], c=ORANGE, alpha=0.6, lw=0, zorder=5)
    b, a = np.polyfit(x[done], y[done], 1)
    xs = np.linspace(x[done].min(), x[done].max(), 2)
    ax2.plot(xs, a + b * xs, color=ORANGE, lw=5, solid_capstyle="round", zorder=6)
    ax2.set_xticks([math.log(v) for v in (1000, 10000, 100000)])
    ax2.set_xticklabels(["$1,000", "$10,000", "$100,000"], fontsize=11, color=MUTED)
    ax2.set_yticks([1, 2, 3, 4, 5, 6])
    ax2.tick_params(colors=MUTED, labelsize=11, length=0)
    ax2.set_ylim(0.5, 7)
    for sp in ax2.spines.values():
        sp.set_visible(False)
    ax2.set_facecolor(PAPER)
    tag(bg, 730, 470, "転換が終わった国（橙）だけなら、右下がりは消える", ORANGE)

    bg.text(
        W - 40,
        18,
        "出典: World Bank WDI（CC BY 4.0）/ socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-13-note-why-rich-countries-have-fewer-children.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def growth_fertility_h8() -> Path:
    """H8: 出生率低下の内訳（望む／望まない、構成／群内）と学歴群ごとの望む数の変化。"""
    import sys

    sys.path.insert(0, str(ROOT / "themes" / "growth-fertility" / "src"))
    from theme_growth_fertility.analysis import a20261017_h8_mechanisms as h8
    from theme_growth_fertility.analysis.s20261017_h8_summary import median_by_index

    d = pl.read_parquet(ROOT / "data" / h8.DHS_MART)
    panel = pl.read_parquet(ROOT / "data" / h8.PANEL_MART)
    st = h8.survey_table(d, panel)
    cells = h8.cell_table(d, st)
    t1 = h8.run_t1(st, "S")
    fell = set(
        h8.pair_frame(st, ("tfr",), min_gap=8, mode="first_last")
        .filter(pl.col("d_tfr") < 0)["iso3"]
        .to_list()
    )
    g = h8.group_rates(cells, h8.edu_shares(d), st, "wanted_tfr")
    two = h8.e10_rows(g, fell, two=True)
    four = h8.e10_rows(g, fell, two=False)
    comp = sum(r["comp"] for r in two)
    rate = sum(r["rate"] for r in two)
    s_comp = comp / (comp + rate)
    med = median_by_index(four, "d_rates")

    fig, bg = canvas()
    title_block(
        bg,
        "出生率を下げたのは「望む子どもの数」が減ったこと",
        "低下の 4 分の 3 は望む数の減少。"
        "その 6 割は学歴の高い女性が増えたからではなく、低学歴の女性の中で起きた",
        size=33,
    )

    # left: two stacked bars (wanted vs unwanted; within-group vs composition)
    ax1 = fig.add_axes([0.15, 0.14, 0.36, 0.50])
    rows = [
        ("出生率の低下", t1.s_w, "望む数の減少", "望まない出生の減少"),
        ("望む数の低下", 1 - s_comp, "同じ学歴の中で減った", "学歴の高い女性が増えた"),
    ]
    for i, (lab, a, la, lb) in enumerate(rows):
        y = 1 - i
        ax1.barh(y, a, color=BLUE if i == 0 else ORANGE, height=0.6, lw=0)
        ax1.barh(y, 1 - a, left=a, color="#cfd6e0", height=0.6, lw=0)
        ax1.text(
            a / 2,
            y,
            f"{la}\n{a:.0%}",
            ha="center",
            va="center",
            color="white",
            fontsize=13,
            fontweight="bold",
        )
        ax1.text(
            a + (1 - a) / 2,
            y,
            f"{lb}\n{1 - a:.0%}",
            ha="center",
            va="center",
            color=INK,
            fontsize=11,
        )
        ax1.text(-0.02, y, lab, ha="right", va="center", color=INK, fontsize=13, fontweight="bold")
    ax1.set_xlim(0, 1)
    ax1.set_ylim(-0.6, 1.6)
    ax1.set_xticks([])
    ax1.set_yticks([])
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_facecolor(PAPER)
    tag(bg, 92, 470, f"途上国 {t1.n_countries} か国の家計調査（DHS）", BLUE)

    # right: change in wanted TFR by education group
    ax2 = fig.add_axes([0.60, 0.14, 0.36, 0.50])
    labs = ["教育なし", "初等", "中等", "高等"]
    cols = [ORANGE, "#f29b7a", "#9fbbe3", "#9fbbe3"]
    ax2.bar(labs, med, color=cols, width=0.65, lw=0)
    for i, v in enumerate(med):
        ax2.text(
            i,
            v - 0.03,
            f"{v:+.2f} 人",
            ha="center",
            va="top",
            color=INK,
            fontsize=12,
            fontweight="bold",
        )
    ax2.axhline(0, color=MUTED, lw=1)
    ax2.set_ylim(min(med) - 0.3, 0.12)
    ax2.set_yticks([])
    ax2.tick_params(colors=INK, labelsize=12, length=0)
    for sp in ax2.spines.values():
        sp.set_visible(False)
    ax2.set_facecolor(PAPER)
    tag(bg, 770, 470, f"学歴別の望む出生の変化（{len(four)} か国の中央値）", ORANGE)

    bg.text(
        W - 40,
        18,
        "出典: The DHS Program Indicator Data API（ICF）/ World Bank WDI / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-17-note-why-child-survival-and-girls-schooling-lower-fertility.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


if __name__ == "__main__":
    for p in (growth_fertility(), wealth(), growth_fertility_h7(), growth_fertility_h8()):
        print(p)
