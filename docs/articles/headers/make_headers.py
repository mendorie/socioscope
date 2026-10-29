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


def growth_fertility_h8_part4() -> Path:
    """Part4: 2 人未満の段階の標準化係数（全部 0 をまたぐ）と、韓国の私教育費 × TFR。"""
    import sys

    sys.path.insert(0, str(ROOT / "themes" / "growth-fertility" / "src"))
    from theme_growth_fertility.analysis import a20261018_h8c_education_cost as h8c
    from theme_growth_fertility.analysis import a20261018_h8d_gender_equity as h8d

    panel = pl.read_parquet(ROOT / "data" / "marts" / "growth_fertility_panel.parquet")
    y1 = h8c.run_y1(h8c.y1_base(panel), "S")
    assert y1.s2 is not None
    kr = pl.read_parquet(ROOT / "data" / "marts" / "kr_private_tutoring.parquet")
    kf = h8d.korea_frame(kr, panel)

    fig, bg = canvas()
    title_block(
        bg,
        "なぜ出生率は 2 人を切るのか",
        "所得・教育・教育費・男女分業のどれでも説明できない。"
        "残るのは「子どもは 2 人」という規範の崩れ",
        size=40,
    )

    # left: stage-2 standardised coefficients, all CIs crossing zero
    ax1 = fig.add_axes([0.16, 0.13, 0.33, 0.52])
    labels = {
        "d_sle": "教育の長さ",
        "d_tert": "大学進学率",
        "d_sec": "女子の就学率",
        "d_eexp": "政府の教育支出",
        "d_ln_gdp": "所得",
        "d_ln_u5": "子どもの死亡率",
    }
    keys = list(labels)
    for i, k in enumerate(keys):
        b, _, lo, hi = y1.s2.coefs[k]
        y = len(keys) - 1 - i
        ax1.plot([lo, hi], [y, y], color=MUTED, lw=4, solid_capstyle="round")
        ax1.plot([b], [y], "o", color=BLUE, ms=11)
    ax1.axvline(0, color=INK, lw=1.2)
    ax1.set_yticks(range(len(keys)))
    ax1.set_yticklabels([labels[k] for k in reversed(keys)], fontsize=13, color=INK)
    ax1.set_xticks([-0.3, 0, 0.3])
    ax1.set_xticklabels(["−0.3", "0", "+0.3"], fontsize=11, color=MUTED)
    ax1.tick_params(length=0)
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_facecolor(PAPER)
    tag(bg, 92, 470, f"出生率 3 未満からの 10 年間、{y1.s2.countries} か国。全部 0 をまたぐ", BLUE)

    # right: Korea private tutoring (nominal) vs TFR
    ax2 = fig.add_axes([0.58, 0.13, 0.36, 0.52])
    yrs = kf["year"].to_list()
    sp_ = kf["spend_per_student_10k_krw"].to_list()
    ax2.plot(yrs, sp_, color=ORANGE, lw=4, marker="o", ms=6)
    ax2.set_ylim(15, 55)
    ax2.set_yticks([20, 30, 40, 50])
    ax2.tick_params(colors=ORANGE, labelsize=11, length=0)
    ax2.set_xticks([2007, 2013, 2019, 2025])
    ax2.tick_params(axis="x", colors=MUTED)
    for sp in ax2.spines.values():
        sp.set_visible(False)
    ax2.set_facecolor(PAPER)
    ax3 = ax2.twinx()
    t = kf.drop_nulls(["tfr"])
    ax3.plot(t["year"].to_list(), t["tfr"].to_list(), color=BLUE, lw=4, marker="s", ms=6)
    ax3.set_ylim(0.6, 1.4)
    ax3.set_yticks([0.7, 1.0, 1.3])
    ax3.tick_params(colors=BLUE, labelsize=11, length=0)
    for sp in ax3.spines.values():
        sp.set_visible(False)
    tag(bg, 770, 470, "韓国: 私教育費（橙、名目）が 2 倍、出生率（青）は 0.75", ORANGE)

    bg.text(
        W - 40,
        18,
        "出典: World Bank WDI / 韓国 教育部 私教育費調査（KOGL 第1類型）/ socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-18-note-why-fertility-falls-below-two.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def growth_fertility_h9_part5() -> Path:
    """Part5: 日本の理想・予定・期間 TFR（左）と 1975 年生まれの完結出生数（右）。"""
    import sys

    sys.path.insert(0, str(ROOT / "themes" / "growth-fertility" / "src"))
    from theme_growth_fertility.analysis import a20261018_h9_norms_vs_constraints as h9

    d = h9.load(ROOT / "data")
    series = h9.japan_series(d)
    cums = {
        i: h9.eu_cohort_cum(d["coh"], i, h9.V3_AGE) for i in ("SWE", "DNK", "FIN", "ITA", "ESP")
    }
    cums["JPN"] = h9.jp_cohort_cum(d["jp"], h9.V3_AGE)

    fig, bg = canvas()
    title_block(
        bg,
        "出生率が 2 人を切っても「2 人」という望みは残っている",
        "崩れたのは望みではなく実現する条件。"
        "日本・南欧は一生に産む数が 1.4 台へ、北欧は 1.9 を保った",
        size=31,
    )

    ax1 = fig.add_axes([0.07, 0.13, 0.40, 0.52])
    keys = [
        ("ideal (couples, JNFS)", BLUE, "夫婦の理想"),
        ("planned (couples, T04-25)", ORANGE, "夫婦の予定"),
        ("period TFR (T04-16)", INK, "その年の出生率"),
    ]
    for k, c, lab in keys:
        xs = [y for y, _ in series[k]]
        ys = [v for _, v in series[k]]
        ax1.plot(
            xs,
            ys,
            color=c,
            lw=4 if k != "period TFR (T04-16)" else 3,
            marker="o" if k != "period TFR (T04-16)" else None,
            ms=6,
        )
        ax1.text(
            xs[-1] + 0.8,
            ys[-1],
            f"{lab} {ys[-1]:.2f}",
            color=c,
            fontsize=11,
            va="center",
            fontweight="bold",
        )
    ax1.axhline(2.0, color=MUTED, lw=1, ls="--")
    ax1.set_xlim(1975, 2040)
    ax1.set_ylim(1.0, 2.8)
    ax1.set_yticks([1.0, 1.5, 2.0, 2.5])
    ax1.set_xticks([1980, 2000, 2020])
    ax1.tick_params(colors=MUTED, labelsize=11, length=0)
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_facecolor(PAPER)
    tag(bg, 92, 470, "日本: 望む数は 2 人前後のまま、出生率だけが下がった", BLUE)

    ax2 = fig.add_axes([0.58, 0.13, 0.38, 0.52])
    names = {
        "SWE": "スウェー\nデン",
        "DNK": "デン\nマーク",
        "FIN": "フィン\nランド",
        "JPN": "日本",
        "ITA": "イタリア",
        "ESP": "スペイン",
    }
    order = ["SWE", "DNK", "FIN", "JPN", "ITA", "ESP"]
    vals = [cums[i][1975] for i in order]
    cols = [BLUE, BLUE, BLUE, ORANGE, ORANGE, ORANGE]
    ax2.bar(range(len(order)), vals, color=cols, width=0.65, lw=0)
    ax2.set_xticks(range(len(order)))
    ax2.set_xticklabels([names[i] for i in order], fontsize=11, color=INK)
    for i, v in enumerate(vals):
        ax2.text(
            i,
            v + 0.03,
            f"{v:.2f}",
            ha="center",
            va="bottom",
            color=INK,
            fontsize=12,
            fontweight="bold",
        )
    ax2.axhline(2.0, color=MUTED, lw=1, ls="--")
    ax2.set_ylim(0, 2.4)
    ax2.set_yticks([])
    ax2.tick_params(colors=INK, labelsize=11, length=0)
    for sp in ax2.spines.values():
        sp.set_visible(False)
    ax2.set_facecolor(PAPER)
    tag(bg, 770, 470, "1975 年生まれの女性が 45 歳までに産んだ数", ORANGE)

    bg.text(
        W - 40,
        18,
        "出典: 国立社会保障・人口問題研究所 / Eurostat / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-18-note-norms-or-constraints.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def growth_fertility_h10_part6() -> Path:
    """Part6: 男性 30–34 歳の雇用形態別未婚率（左）と Kitagawa 分解（右）。"""
    import sys

    sys.path.insert(0, str(ROOT / "themes" / "growth-fertility" / "src"))
    from theme_growth_fertility.analysis import a20261018_h10_family_formation as h10
    from theme_growth_fertility.analysis.s20261018_h10_summary import rate_series

    d = h10.load(ROOT / "data")
    res = h10.compute(d)
    emp = d["emp"]

    fig, bg = canvas()
    title_block(
        bg,
        "結婚を阻んでいるのは、非正規でも家賃でも所得でもなかった",
        "未婚化は正社員でも非正規でも、どの県でも同じように進んだ。残る読みは「結婚という選択からの離脱」",
        size=31,
    )

    ax1 = fig.add_axes([0.07, 0.13, 0.40, 0.52])
    for key, color, lab in (
        ("nonregular", ORANGE, "非正規"),
        ("total_pop", INK, "全体"),
        ("regular", BLUE, "正社員"),
    ):
        pts = rate_series(emp, "male", "30-34", key)
        xs = [y for y, _ in pts]
        ys = [v for _, v in pts]
        ax1.plot(xs, ys, color=color, lw=4, marker="o", ms=7)
        ax1.text(
            xs[-1] + 0.4,
            ys[-1],
            f"{lab} {ys[-1]:.0f}%",
            color=color,
            fontsize=12,
            va="center",
            fontweight="bold",
        )
    ax1.set_xlim(2005, 2029)
    ax1.set_ylim(30, 90)
    ax1.set_yticks([40, 60, 80])
    ax1.set_yticklabels(["40%", "60%", "80%"], fontsize=11, color=MUTED)
    ax1.set_xticks([2007, 2012, 2017, 2022])
    ax1.tick_params(colors=MUTED, labelsize=11, length=0)
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_facecolor(PAPER)
    tag(bg, 92, 470, "30〜34 歳男性の未婚率: どの働き方でも上がった", BLUE)

    ax2 = fig.add_axes([0.58, 0.18, 0.37, 0.42])
    b = res.b
    parts = [
        ("同じ働き方の中で\n未婚が増えた分", 100 * b.rate, BLUE),
        ("年齢構成", 100 * b.age_comp, MUTED),
        ("働き方の構成\n（正社員に寄った）", 100 * b.emp_comp, ORANGE),
    ]
    ys = range(len(parts))
    ax2.barh(list(ys), [v for _, v, _ in parts], color=[c for _, _, c in parts], height=0.6, lw=0)
    for i, (_lab, v, c) in enumerate(parts):
        ax2.text(
            v + (0.15 if v >= 0 else -0.15),
            i,
            f"{v:+.1f}",
            color=c,
            fontsize=12,
            va="center",
            ha="left" if v >= 0 else "right",
            fontweight="bold",
        )
    ax2.set_yticks(list(ys))
    ax2.set_yticklabels([lab for lab, _, _ in parts], fontsize=11, color=INK)
    ax2.axvline(0, color=INK, lw=1)
    ax2.set_xlim(-2.5, 7)
    ax2.set_xticks([])
    ax2.tick_params(length=0)
    for sp in ax2.spines.values():
        sp.set_visible(False)
    ax2.set_facecolor(PAPER)
    ax2.invert_yaxis()
    tag(
        bg,
        770,
        470,
        f"25〜39 歳男性 +{100 * b.total:.1f} ポイントの内訳（2012→22）",
        ORANGE,
    )

    bg.text(
        W - 40,
        18,
        "出典: 就業構造基本調査（総務省）を加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-18-note-what-blocks-family-formation.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def growth_fertility_h12_part7() -> Path:
    """Part7（補遺）: 交際相手なしの推移（左）と夫婦の出会い経路の構成比（右）。

    数値は reports/2026-10-18-h12-why-marriage-left.md（mart jp_marriage_attitudes）から。
    """
    att = pl.read_parquet(MARTS / "jp_marriage_attitudes.parquet")
    nop = att.filter(
        (pl.col("figure") == "2_1_2")
        & (pl.col("age") == "18～34歳（総数）")
        & (pl.col("sex").is_in(["male", "female"]))
    )

    fig, bg = canvas()
    title_block(
        bg,
        "結婚が減った背景で最も動いたのは「交際相手がいない」こと",
        "未婚者の 4 割から 7 割へ。見合い・職場で失われた結婚のうち、ネットが補ったのは 4 分の 1",
        size=30,
    )

    ax1 = fig.add_axes([0.07, 0.13, 0.40, 0.52])
    for sex, color, lab in (("male", BLUE, "男性"), ("female", ORANGE, "女性")):
        d = (
            nop.filter(pl.col("sex") == sex)
            .group_by("survey_year")
            .agg(pl.col("share_pct").sum())
            .sort("survey_year")
        )
        xs = d["survey_year"].to_list()
        ys = d["share_pct"].to_list()
        ax1.plot(xs, ys, color=color, lw=4, marker="o", ms=7)
        ax1.text(
            xs[-1] + 0.8,
            ys[-1],
            f"{lab} {ys[-1]:.0f}%",
            color=color,
            fontsize=12,
            va="center",
            fontweight="bold",
        )
    ax1.set_xlim(1980, 2031)
    ax1.set_ylim(20, 85)
    ax1.set_yticks([30, 50, 70])
    ax1.set_yticklabels(["30%", "50%", "70%"], fontsize=11, color=MUTED)
    ax1.set_xticks([1982, 1992, 2002, 2010, 2021])
    ax1.tick_params(colors=MUTED, labelsize=11, length=0)
    for sp in ax1.spines.values():
        sp.set_visible(False)
    ax1.set_facecolor(PAPER)
    tag(bg, 92, 470, "交際相手のいない未婚者（18〜34 歳）", BLUE)

    ax2 = fig.add_axes([0.58, 0.18, 0.37, 0.42])
    meet = att.filter(pl.col("figure") == "5_2_2")
    r8 = meet.filter(pl.col("survey_round") == 8)
    r16 = meet.filter((pl.col("survey_round") == 16) & (pl.col("period") == "2018/7-2021/6"))

    def pick(df: pl.DataFrame, key: str) -> float:
        rows = df.filter(pl.col("item").str.contains(key))["share_pct"].to_list()
        return float(rows[0]) if rows else 0.0

    labels = ["見合い", "職場", "ネット"]
    keys = ["見合い", "職場", "ネット"]
    v82 = [pick(r8, k) for k in keys]
    v21 = [pick(r16, k) for k in keys]
    x = np.arange(len(labels))
    ax2.bar(x - 0.2, v82, width=0.38, color=MUTED, lw=0, label="1982 年調査")
    ax2.bar(x + 0.2, v21, width=0.38, color=ORANGE, lw=0, label="2018〜21 年結婚")
    for i in range(len(labels)):
        ax2.text(x[i] - 0.2, v82[i] + 1, f"{v82[i]:.0f}%", ha="center", fontsize=11, color=MUTED)
        ax2.text(
            x[i] + 0.2,
            v21[i] + 1,
            f"{v21[i]:.0f}%",
            ha="center",
            fontsize=11,
            color=ORANGE,
            fontweight="bold",
        )
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(labels, fontsize=12, color=INK)
    ax2.set_ylim(0, 36)
    ax2.set_yticks([])
    ax2.tick_params(length=0)
    for sp in ax2.spines.values():
        sp.set_visible(False)
    ax2.set_facecolor(PAPER)
    ax2.legend(frameon=False, fontsize=10, loc="upper right", labelcolor=MUTED)
    tag(bg, 745, 470, "夫婦の出会いのきっかけ（結婚 5 年未満）", ORANGE)

    bg.text(
        W - 40,
        18,
        "出典: 国立社会保障・人口問題研究所『第 16 回出生動向基本調査 報告書』"
        "グラフデータを加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-18-note-why-people-left-marriage.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


# ---- bicycle-industry（2026-10-22、3 本） ----------------------------------------------


def _bare(ax: plt.Axes) -> None:
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor(PAPER)
    ax.tick_params(colors=MUTED, labelsize=11, length=0)


def bicycle_part1() -> Path:
    jb = pl.read_parquet(MARTS / "jp_bicycle_by_type.parquet")
    pos = pl.read_parquet(MARTS / "jp_pos_sales.parquet")
    prod = {
        int(r["year"]): float(r["qty"])
        for r in jb.filter(
            (pl.col("category") == "total") & (pl.col("flow") == "production")
        ).iter_rows(named=True)
    }
    imp = (
        jb.filter(pl.col("flow") == "import").group_by("year").agg(pl.col("qty").sum()).sort("year")
    )
    total = {
        int(r["year"]): prod[int(r["year"])] + float(r["qty"]) for r in imp.iter_rows(named=True)
    }
    years = sorted(total)
    pos25 = (
        pos.filter((pl.col("year") == 2025) & (pl.col("category") != "total"))
        .group_by("category")
        .agg(pl.col("qty").sum(), pl.col("value_jpy").sum())
    )
    order = ["light", "sports", "kids", "infant", "other", "eassist"]
    names = {
        "light": "軽快車",
        "sports": "スポーツ車",
        "kids": "子ども車",
        "infant": "幼児車",
        "other": "その他",
        "eassist": "電動アシスト",
    }
    q = {str(r["category"]): float(r["qty"]) for r in pos25.iter_rows(named=True)}
    v = {str(r["category"]): float(r["value_jpy"]) for r in pos25.iter_rows(named=True)}
    tq, tv = sum(q.values()), sum(v.values())

    fig, bg = canvas()
    title_block(bg, "自転車業界は苦境なのか？", "台数は 3 割減った。でも、お金は減っていない")

    ax1 = fig.add_axes([0.07, 0.12, 0.40, 0.55])
    ax1.bar(
        years,
        [total[y] / 1e6 for y in years],
        color=[BLUE if y == years[0] else ORANGE for y in years],
        width=0.7,
    )
    for y in years:
        ax1.text(
            y,
            total[y] / 1e6 + 0.12,
            f"{total[y] / 1e6:.1f}",
            ha="center",
            fontsize=12,
            color=INK,
            fontweight="bold",
        )
    ax1.set_ylim(0, 8.2)
    ax1.set_yticks([])
    ax1.set_xticks(years)
    _bare(ax1)
    tag(bg, 92, 470, "国内向け自転車の台数（百万台）：2021 → 2025 で −30%", BLUE)

    ax2 = fig.add_axes([0.57, 0.12, 0.38, 0.55])
    left_q = left_v = 0.0
    for c in order:
        col = ORANGE if c == "eassist" else ("#c9c2b5" if c != "sports" else "#9aa7b8")
        ax2.barh(1, q[c] / tq, left=left_q, color=col, height=0.6)
        ax2.barh(0, v[c] / tv, left=left_v, color=col, height=0.6)
        if c in ("eassist", "sports", "light"):
            ax2.text(
                left_q + q[c] / tq / 2,
                1,
                f"{names[c]}\n{q[c] / tq:.0%}",
                ha="center",
                va="center",
                fontsize=11,
                color="white" if c != "light" else INK,
                fontweight="bold",
            )
            ax2.text(
                left_v + v[c] / tv / 2,
                0,
                f"{names[c]}\n{v[c] / tv:.0%}",
                ha="center",
                va="center",
                fontsize=11,
                color="white" if c != "light" else INK,
                fontweight="bold",
            )
        left_q += q[c] / tq
        left_v += v[c] / tv
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["金額", "台数"], fontsize=13, color=INK)
    ax2.set_xticks([])
    ax2.set_xlim(0, 1)
    _bare(ax2)
    tag(bg, 728, 470, "小売 2025 年：電動アシストは台数 16%・金額 42%", ORANGE)

    bg.text(
        W - 40,
        18,
        "出典: 自転車産業振興協会「国内向自転車生産輸入統計」「POS 販売統計」を加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-22-note-bicycle-part1-is-the-industry-in-trouble.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def bicycle_part2() -> Path:
    trade = pl.read_parquet(MARTS / "bicycle_trade.parquet")
    six = ["JPN", "USA", "DEU", "NLD", "GBR", "ITA"]
    t = (
        trade.filter(
            pl.col("iso3").is_in(six)
            & (pl.col("flow") == "import")
            & (pl.col("hs") == "8712")
            & pl.col("qty").is_not_null()
        )
        .group_by("year")
        .agg(pl.col("qty").sum())
        .sort("year")
    )
    s = {
        int(r["year"]): float(r["qty"])
        for r in t.iter_rows(named=True)
        if 2015 <= int(r["year"]) <= 2024
    }
    ys = sorted(s)
    xs = np.array(ys, dtype=float)
    pre = [y for y in ys if y <= 2019]
    b, a = np.polyfit(np.array(pre, dtype=float), np.array([s[y] for y in pre]), 1)
    m = pl.read_parquet(MARTS / "merida_specialized.parquet")
    share = {
        int(r["fy"]): float(r["value_ntd_k"]) / 1e6
        for r in m.filter(pl.col("metric") == "equity_method_share").iter_rows(named=True)
    }

    fig, bg = canvas()
    title_block(bg, "特需は「先食い」だった", "そして 2 年たっても、元の水準には戻っていない")

    ax1 = fig.add_axes([0.07, 0.12, 0.42, 0.55])
    ax1.axvspan(2019.5, 2022.5, color="#ece8e0", zorder=0)
    ax1.plot(xs, a + b * (np.arange(2015, 2025)), color=MUTED, lw=3, ls="--")
    ax1.plot(xs, [s[y] for y in ys], color=BLUE, lw=5, solid_capstyle="round")
    ax1.scatter(xs, [s[y] for y in ys], color=BLUE, s=50, zorder=5)
    ax1.set_xticks([2015, 2019, 2022, 2024])
    ax1.set_yticks([])
    ax1.set_ylim(0, max(s.values()) * 1.25)
    _bare(ax1)
    ax1.text(2024.1, a + b * 2024, "2015–19 年の\nトレンド", fontsize=11, color=MUTED, va="center")
    tag(bg, 92, 470, "6 か国の完成車輸入台数：特需後はトレンドの 0.79 倍", BLUE)

    ax2 = fig.add_axes([0.60, 0.12, 0.35, 0.55])
    fys = sorted(share)
    ax2.bar(
        fys,
        [share[y] for y in fys],
        color=[BLUE if share[y] >= 0 else ORANGE for y in fys],
        width=0.65,
    )
    for y in fys:
        ax2.text(
            y,
            share[y] + (0.15 if share[y] >= 0 else -0.45),
            f"{share[y]:+.1f}",
            ha="center",
            fontsize=12,
            color=INK,
            fontweight="bold",
        )
    ax2.axhline(0, color=MUTED, lw=1)
    ax2.set_xticks(fys)
    ax2.set_yticks([])
    ax2.set_ylim(-5.2, 1.6)
    _bare(ax2)
    tag(bg, 770, 470, "Specialized の持分法損益（十億台湾ドル）", ORANGE)

    bg.text(
        W - 40,
        18,
        "出典: UN Comtrade、Merida Industry 連結財務報告を加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-22-note-bicycle-part2-pandemic-boom-and-aftermath.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def bicycle_part3() -> Path:
    kei = pl.read_parquet(MARTS / "jp_kei_moto_sales.parquet")
    imp = pl.read_parquet(MARTS / "jp_import_car_price_bands.parquet")
    jb = pl.read_parquet(MARTS / "jp_bicycle_by_type.parquet")
    meti = pl.read_parquet(MARTS / "meti_production.parquet")

    def seg(df: pl.DataFrame, col: str, val: str, ycol: str, vcol: str) -> dict[int, float]:
        return {
            int(r[ycol]): float(r[vcol])
            for r in df.filter(pl.col(col) == val).iter_rows(named=True)
        }

    kei4 = seg(kei, "segment", "kei4_total", "year", "units")
    gt = seg(kei, "segment", "moto_gt250", "year", "units")
    high = ("ge_2000", "1000_1999", "900_999", "800_899", "700_799", "600_699", "500_599")
    imp_high = imp.filter(pl.col("band").is_in(high)).group_by("year").agg(pl.col("units").sum())
    ih = {int(r["year"]): float(r["units"]) for r in imp_high.iter_rows(named=True)}
    g1 = {
        int(r["year"]): float(r["value"])
        for r in meti.filter(
            (pl.col("product") == "moto_le50")
            & (pl.col("measure") == "sales_qty")
            & pl.col("period_type").is_in(["cy", "cy_from_months"])
        )
        .sort("year", "period_type")
        .iter_rows(named=True)
    }
    ea = {
        int(r["year"]): float(r["qty"])
        for r in jb.filter(
            (pl.col("category") == "eassist") & (pl.col("flow") == "production")
        ).iter_rows(named=True)
    }
    sp = {
        int(r["year"]): float(r["qty"])
        for r in jb.filter(
            (pl.col("category") == "other_sports_geared") & (pl.col("flow") == "import")
        ).iter_rows(named=True)
    }

    def ch(d: dict[int, float]) -> float:
        return d[2025] / d[2022] - 1

    rows = [
        ("自動車", "軽自動車", ch(kei4), "輸入車 500 万円以上", ch(ih)),
        ("二輪", "原付一種", ch(g1), "大型二輪", ch(gt)),
        ("自転車", "電動アシスト", ch(ea), "スポーツ車", ch(sp)),
    ]

    fig, bg = canvas()
    title_block(
        bg, "自動車・二輪とは、逆向きの分化", "「実用が残り、趣味が縮む」のは自転車だけだった"
    )
    ax = fig.add_axes([0.06, 0.08, 0.90, 0.56])
    ypos = np.arange(len(rows))[::-1] * 1.0
    for yp, (ind, un, uc, hn, hc) in zip(ypos, rows, strict=True):
        ax.barh(yp + 0.18, uc * 100, color=BLUE, height=0.32)
        ax.barh(yp - 0.18, hc * 100, color=ORANGE, height=0.32)
        ax.text(-52, yp, ind, fontsize=18, fontweight="bold", color=INK, va="center", ha="left")
        ax.text(
            uc * 100 + (1.5 if uc >= 0 else -1.5),
            yp + 0.18,
            f"{un} {uc:+.0%}",
            va="center",
            ha="left" if uc >= 0 else "right",
            fontsize=12,
            color=INK,
        )
        ax.text(
            hc * 100 + (1.5 if hc >= 0 else -1.5),
            yp - 0.18,
            f"{hn} {hc:+.0%}",
            va="center",
            ha="left" if hc >= 0 else "right",
            fontsize=12,
            color=INK,
        )
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_xlim(-54, 38)
    ax.set_yticks([])
    ax.set_xticks([])
    _bare(ax)
    tag(bg, 92, 470, "実用層", BLUE)
    tag(bg, 200, 470, "趣味層", ORANGE)
    bg.text(320, 470, "2022 → 2025 年の台数の変化率", fontsize=14, color=MUTED, va="center")

    bg.text(
        W - 40,
        18,
        "出典: 全国軽自動車協会連合会・日本自動車輸入組合・経済産業省 生産動態統計・"
        "自転車産業振興協会を加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-22-note-bicycle-part3-cars-motorcycles-and-what-it-means.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def parliament_size() -> Path:
    ipu = pl.read_parquet(MARTS / "ipu_parliaments.parquet")
    lower = ipu.filter(pl.col("oecd_member") & (pl.col("chamber_type") == "lower"))
    per_m = {
        str(r["iso3"]): float(r["statutory_seats"]) / (float(r["population_thousands"]) / 1000)
        for r in lower.iter_rows(named=True)
    }
    cube = {
        str(r["iso3"]): float(r["statutory_seats"])
        / (float(r["population_thousands"]) * 1000) ** (1 / 3)
        for r in lower.iter_rows(named=True)
    }
    picks = [
        ("USA", "米国"),
        ("JPN", "日本"),
        ("MEX", "メキシコ"),
        ("KOR", "韓国"),
        ("ITA", "イタリア"),
        ("DEU", "ドイツ"),
        ("FRA", "フランス"),
        ("GBR", "英国"),
        ("SWE", "スウェーデン"),
    ]
    rank_pm = sorted(per_m, key=lambda k: per_m[k]).index("JPN") + 1
    rank_cb = sorted(cube, key=lambda k: cube[k]).index("JPN") + 1

    fig, bg = canvas()
    title_block(
        bg,
        "日本の国会議員は減らすべきか？",
        "定数削減の論点に、国内外の公開データで一つずつ答える",
    )
    ax = fig.add_axes([0.11, 0.10, 0.46, 0.58])
    ys = np.arange(len(picks))[::-1]
    for y, (iso, name) in zip(ys, picks, strict=True):
        c = ORANGE if iso == "JPN" else BLUE
        ax.barh(y, per_m[iso], color=c, height=0.62)
        ax.text(per_m[iso] + 0.3, y, f"{per_m[iso]:.1f}", va="center", fontsize=12, color=INK)
        ax.text(-0.4, y, name, va="center", ha="right", fontsize=13, color=INK)
    ax.set_xlim(0, 40)
    ax.set_yticks([])
    ax.set_xticks([])
    _bare(ax)
    bg.text(64, 470, "人口 100 万人当たりの下院議員数", fontsize=14, color=MUTED, va="center")

    x0 = 790
    bg.add_patch(
        FancyBboxPatch(
            (x0, 100), 430, 350, boxstyle="round,pad=0,rounding_size=18", fc="white", ec="none"
        )
    )
    bg.text(x0 + 28, 420, "日本の位置（OECD 38 か国）", fontsize=14, color=MUTED, va="center")
    items = [
        ("人口当たりでは", f"少ない方から {rank_pm} 位", ORANGE),
        ("人口規模を補正すると", f"{rank_cb} 位（真ん中）", BLUE),
        ("比例 45 減で浮く国費", "国民 1 人 25 円/年", INK),
        ("世論の不満に応えるのは", "人数ではなく報酬と透明性", INK),
    ]
    for i, (label, value, color) in enumerate(items):
        y = 372 - i * 78
        bg.text(x0 + 28, y, label, fontsize=13, color=MUTED, va="center")
        bg.text(x0 + 28, y - 30, value, fontsize=19, fontweight="bold", color=color, va="center")

    bg.text(
        W - 40,
        18,
        "出典: IPU Parline（CC BY-NC-SA 4.0）・総務省 衆議院議員総選挙 結果調・"
        "財務省 予算書を加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-27-note-parliament-size.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def parliament_size_extra() -> Path:
    ipu = pl.read_parquet(MARTS / "ipu_parliaments.parquet")
    gov = pl.read_parquet(MARTS / "oecd_gov_finance.parquet")
    lower = ipu.filter(pl.col("oecd_member") & (pl.col("chamber_type") == "lower"))
    cube = {
        str(r["iso3"]): float(r["statutory_seats"])
        / (float(r["population_thousands"]) * 1000) ** (1 / 3)
        for r in lower.iter_rows(named=True)
    }
    ge = (
        gov.filter(
            (pl.col("metric") == "gov_expenditure_pct_gdp") & pl.col("year").is_between(2019, 2023)
        )
        .group_by("iso3")
        .agg(pl.col("value").mean())
    )
    spend = {str(r["iso3"]): float(r["value"]) for r in ge.iter_rows(named=True)}
    keys = sorted(k for k in cube if k in spend)
    labels = {
        "USA": "米国",
        "JPN": "日本",
        "FRA": "フランス",
        "SWE": "スウェーデン",
        "GBR": "英国",
        "DEU": "ドイツ",
        "CRI": "コスタリカ",
        "AUS": "豪州",
        "IRL": "アイルランド",
        "MEX": "メキシコ",
    }

    fig, bg = canvas()
    title_block(
        bg,
        "「小さな政府」の国は議員も少ないのか",
        "人口規模を補正すると、議会の大きさと政府の大きさは同じ向きに並ぶ",
    )
    ax = fig.add_axes([0.10, 0.12, 0.52, 0.56])
    ax.scatter(
        [cube[k] for k in keys],
        [spend[k] for k in keys],
        s=[90 if k == "JPN" else 42 for k in keys],
        color=[ORANGE if k == "JPN" else BLUE for k in keys],
        alpha=0.9,
    )
    for k, name in labels.items():
        if k in cube and k in spend:
            ax.annotate(
                name,
                (cube[k], spend[k]),
                fontsize=11,
                color=INK,
                xytext=(6, 4),
                textcoords="offset points",
            )
    ax.set_xlim(0.25, 1.75)
    ax.set_ylim(20, 62)
    ax.set_xticks([0.5, 1.0, 1.5])
    ax.set_yticks([30, 40, 50, 60])
    ax.tick_params(colors=MUTED, labelsize=11)
    _bare(ax)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color("#dddddd")
    bg.text(
        64,
        470,
        "横軸: 下院定数 ÷ 人口の立方根（1.0 = 法則どおり）",
        fontsize=13,
        color=MUTED,
        va="center",
    )
    bg.text(
        64,
        445,
        "縦軸: 一般政府支出 ÷ GDP（%、2019〜23 年平均）",
        fontsize=13,
        color=MUTED,
        va="center",
    )

    x0 = 790
    bg.add_patch(
        FancyBboxPatch(
            (x0, 100), 430, 350, boxstyle="round,pad=0,rounding_size=18", fc="white", ec="none"
        )
    )
    bg.text(x0 + 28, 420, "順位相関（OECD 38 か国）", fontsize=14, color=MUTED, va="center")
    items = [
        ("素の人口当たり議員数では", "+0.16（関係なし）", MUTED),
        ("人口規模を補正すると", "+0.34（弱く正）", ORANGE),
        ("議員 1 人が監視する政府支出", "日本は 38 か国中 2 位", INK),
        ("小さい議会ほど信頼される？", "そうではない", INK),
    ]
    for i, (label, value, color) in enumerate(items):
        y = 372 - i * 78
        bg.text(x0 + 28, y, label, fontsize=13, color=MUTED, va="center")
        bg.text(x0 + 28, y - 30, value, fontsize=19, fontweight="bold", color=color, va="center")

    bg.text(
        W - 40,
        18,
        "出典: OECD Government at a Glance 2025・IPU Parline（CC BY-NC-SA 4.0）を加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-29-note-parliament-size-extra-government-size.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


def parliament_size_extra2() -> Path:
    eb = pl.read_parquet(MARTS / "eb_trust_parliament.parquet")
    it = {
        int(r["wave"]): float(r["value"])
        for r in eb.filter(pl.col("iso3") == "ITA").iter_rows(named=True)
    }
    eu = {
        int(r["wave"]): float(r["value"])
        for r in eb.filter(pl.col("iso3") == "EU27").iter_rows(named=True)
    }
    waves = sorted(w for w in it if w in eu)

    fig, bg = canvas()
    title_block(
        bg,
        "不信が議員を減らすのは、日本だけか",
        "OECD 15 か国 17 件の定数削減の提案と、減らしたイタリアの信頼の前後を追う",
    )
    ax = fig.add_axes([0.10, 0.13, 0.52, 0.54])
    ax.plot(waves, [it[w] for w in waves], marker="o", color=ORANGE, linewidth=2, label="イタリア")
    ax.plot(waves, [eu[w] for w in waves], marker="o", color=BLUE, linewidth=2, label="EU27 平均")
    ax.axvline(97.5, color=INK, linewidth=1, linestyle="--")
    ax.text(97.7, 41.5, "630 → 400 施行", fontsize=11, color=INK)
    ax.set_xticks([91, 94, 97, 100, 103])
    ax.set_xticklabels(["2019", "2021", "2022", "2023", "2025"], fontsize=11, color=MUTED)
    ax.set_yticks([25, 30, 35, 40])
    ax.set_ylim(22, 44)
    ax.tick_params(colors=MUTED, labelsize=11)
    ax.legend(frameon=False, fontsize=11, loc="upper left")
    _bare(ax)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color("#dddddd")
    bg.text(
        64,
        470,
        "国の議会を信頼する人の割合（%、Eurobarometer 半年ごと）",
        fontsize=13,
        color=MUTED,
        va="center",
    )

    x0 = 790
    bg.add_patch(
        FancyBboxPatch(
            (x0, 100), 430, 350, boxstyle="round,pad=0,rounding_size=18", fc="white", ec="none"
        )
    )
    bg.text(x0 + 28, 420, "OECD 38 か国、2000 年以降", fontsize=14, color=MUTED, va="center")
    items = [
        ("削減を提案した国の信頼", "31% vs しない国 42%", ORANGE),
        ("法案・国民投票に限ると", "差は消える", INK),
        ("不信・費用を理由にした 13 件", "施行は 3 件", INK),
        ("減らしたイタリアの信頼", "+6 pt（政権交代と同時）", BLUE),
    ]
    for i, (label, value, color) in enumerate(items):
        y = 372 - i * 78
        bg.text(x0 + 28, y, label, fontsize=13, color=MUTED, va="center")
        bg.text(x0 + 28, y - 30, value, fontsize=19, fontweight="bold", color=color, va="center")

    bg.text(
        W - 40,
        18,
        "出典: Standard Eurobarometer 91–103（data.europa.eu）・"
        "OECD Trust Survey 2023 を加工 / socioscope",
        fontsize=9,
        color=MUTED,
        ha="right",
    )
    out = OUT / "2026-10-31-note-parliament-size-extra2-distrust.png"
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out


if __name__ == "__main__":
    for p in (
        growth_fertility(),
        wealth(),
        growth_fertility_h7(),
        growth_fertility_h8(),
        growth_fertility_h8_part4(),
        growth_fertility_h9_part5(),
        growth_fertility_h10_part6(),
        growth_fertility_h12_part7(),
        bicycle_part1(),
        bicycle_part2(),
        bicycle_part3(),
        parliament_size(),
        parliament_size_extra(),
        parliament_size_extra2(),
    ):
        print(p)
