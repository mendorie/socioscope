"""ちいかわ 社会現象の要因分析 — 図版生成スクリプト。

数値はすべて research_notes/ちいかわ 社会現象の要因分析/*.md に記載のものだけを使う。
実行: venv/bin/python reports/figures/chiikawa/make_figures.py
"""

# ruff: noqa: E501  (図の出典脚注は長い文字列をそのまま保持する)
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ACCENT = "#E4572E"
GRAY = "#9A9A9A"
DARK = "#333333"

plt.rcParams.update(
    {
        "font.family": "Hiragino Sans",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#CCCCCC",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#E6E6E6",
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "figure.titlesize": 13,
        "figure.titleweight": "bold",
        "figure.dpi": 150,
        "savefig.dpi": 150,
    }
)


def footnote(fig: plt.Figure, text: str) -> None:
    fig.text(0.01, 0.01, text, fontsize=7, color="#666666", ha="left", va="bottom")


def save(fig: plt.Figure, name: str) -> Path:
    path = OUT / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# fig1: 成長の時系列（累計発行部数・X フォロワー）
# ---------------------------------------------------------------------------
PRINT_RUN = [  # (date, 万部) 電子含む累計発行部数
    (dt.date(2023, 12, 21), 270),
    (dt.date(2024, 11, 18), 360),
    (dt.date(2025, 11, 1), 460),
    (dt.date(2026, 9, 1), 500),
]
FOLLOWERS = [  # (date, 万人) X フォロワー
    (dt.date(2022, 1, 27), 80),
    (dt.date(2022, 9, 30), 140),
    (dt.date(2024, 9, 10), 344),
    (dt.date(2025, 4, 1), 380),
    (dt.date(2025, 7, 1), 410),
    (dt.date(2025, 8, 1), 418),
    (dt.date(2026, 3, 1), 460),
    (dt.date(2026, 8, 19), 527.8),
    (dt.date(2026, 11, 12), 590),
]
MILESTONES = [
    (dt.date(2022, 4, 4), "めざましテレビ\n放送開始"),
    (dt.date(2024, 8, 30), "マクドナルド\nハッピーセット初回"),
    (dt.date(2025, 3, 27), "アプリ\n『ちいかわぽけっと』"),
    (dt.date(2026, 7, 24), "映画公開"),
]


def fig1() -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True)
    x0, x1 = dt.date(2021, 1, 1), dt.date(2026, 12, 31)

    ax = axes[0]
    xs, ys = zip(*PRINT_RUN, strict=True)
    ax.plot(xs, ys, marker="o", color=ACCENT, lw=2)
    for x, y in PRINT_RUN:
        ax.annotate(
            f"{y:g}", (x, y), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8
        )
    ax.set_ylabel("累計発行部数（万部）")
    ax.set_title("単行本 累計発行部数（電子含む）")
    ax.set_ylim(0, 700)

    ax = axes[1]
    xs, ys = zip(*FOLLOWERS, strict=True)
    ax.plot(xs, ys, marker="o", color=ACCENT, lw=2)
    for x, y in FOLLOWERS:
        dx, dy = {410: (-6, 7), 418: (10, -14)}.get(int(y), (0, 7))
        ax.annotate(
            f"{y:g}", (x, y), textcoords="offset points", xytext=(dx, dy), ha="center", fontsize=8
        )
    ax.set_ylabel("X フォロワー（万人）")
    ax.set_title("X（旧 Twitter）フォロワー数")
    ax.set_ylim(0, 640)
    ax.set_xlim(x0, x1)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    for ax in axes:
        for d, label in MILESTONES:
            ax.axvline(d, color=GRAY, lw=0.9, ls="--", zorder=0)
            if ax is axes[0]:
                ax.text(
                    d,
                    690,
                    label,
                    fontsize=7.5,
                    color=DARK,
                    ha="center",
                    va="top",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"),
                )

    fig.suptitle("ちいかわ IP の成長軌跡（2021–2026）", x=0.01, ha="left")
    footnote(
        fig,
        "出典: 発行部数＝モーニング公式（2024-11 360万）、講談社 8巻製品ページ（2025-11 460万）、6巻時点 270万（2023-12）、500万（2026-09 トーハン発表の二次転記）。"
        "\nフォロワー＝電ファミ（2022-01 80万）、HugKum（2022-09 140万）、note/Wikipedia（2024-09 344万）、電ファミ・モデルプレス（2025 380〜418万、2026-03 460万）、Wikipedia（2026-08 527.8万）、MANTANWEB（2026-11 590万突破）。\n記事により原作者／アニメ公式の区別が曖昧。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.97))
    return save(fig, "fig1_growth_timeline.png")


# ---------------------------------------------------------------------------
# fig2: 映画興収の比較
# ---------------------------------------------------------------------------
BOX_OFFICE = [  # (label, 億円, accent?)
    ("鬼滅の刃 無限列車編（2020）", 407.5, False),
    ("映画ちいかわ 人魚の島のひみつ（2026, 11/8 時点）", 187.9, True),
    ("名探偵コナン ハイウェイの堕天使（2026）", 137.0, False),
    ("トイ・ストーリー5（2026）", 130.4, False),
    ("妖怪ウォッチ 第1作（2014）", 78.0, False),
    ("ポケモン ミュウツーの逆襲（1998）", 72.4, False),
    ("すみっコぐらし 第1作（2019）", 14.5, False),
]


def fig2() -> Path:
    fig, ax = plt.subplots(figsize=(9, 5))
    rows = list(reversed(BOX_OFFICE))
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = [ACCENT if r[2] else GRAY for r in rows]
    bars = ax.barh(labels, vals, color=colors, height=0.62)
    for b, v in zip(bars, vals, strict=True):
        ax.text(
            v + 4,
            b.get_y() + b.get_height() / 2,
            f"{v:g} 億円",
            va="center",
            fontsize=9,
            color=DARK,
        )
    ax.set_xlim(0, 470)
    ax.set_xlabel("興行収入（億円）")
    ax.grid(axis="y", visible=False)
    ax.set_title("映画興行収入: 2026 年公開作と過去の子ども向けブーム作品", loc="left")
    footnote(
        fig,
        "出典: ちいかわ・コナン・トイ・ストーリー5＝granza.jp（興行通信社値の二次転記、2026-11-08 時点）。鬼滅・妖怪ウォッチ・ミュウツー＝Wikipedia「日本歴代興行収入上位の映画一覧」集計。"
        "\nすみっコぐらし＝All About（約 110 館・14.5 億円）。",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    return save(fig, "fig2_movie_boxoffice.png")


# ---------------------------------------------------------------------------
# fig3: ビデオリサーチ Kids/ex 2025-10
# ---------------------------------------------------------------------------
GIRLS = [
    ("ちいかわ", 73.9),
    ("シナモロール", 72.9),
    ("すみっコぐらし", 71.4),
    ("クロミ", 70.0),
    ("アナと雪の女王", 67.9),
    ("ハローキティ", 65.0),
    ("マイメロディ", 64.3),
]
TOTAL = [
    ("ドラえもん", 60.1),
    ("星のカービィ", 57.7),
    ("キャプテンピカチュウ", 57.2),
    ("スーパーマリオ", 56.0),
    ("MINECRAFT", 53.8),
    ("TVアニメ ポケモン", 53.1),
    ("ちいかわ", 52.6),
    ("すみっコぐらし", 51.7),
]
BOYS = [
    ("MINECRAFT", 66.1),
    ("スーパーマリオ", 65.1),
    ("ドラえもん", 64.1),
    ("キャプテンピカチュウ", 61.5),
    ("TVアニメ ポケモン", 60.2),
    ("星のカービィ", 60.2),
    ("TVアニメ 鬼滅の刃", 52.6),
    ("ミニオンズ", 51.0),
    ("黄色いルカリオ", 48.4),
    ("おさるのジョージ", 47.7),
]


def _panel(ax: plt.Axes, data: list[tuple[str, float]], title: str) -> None:
    rows = list(reversed(data))
    names = [f"{len(data) - i}. {n}" for i, (n, _) in enumerate(rows)]
    vals = [v for _, v in rows]
    colors = [ACCENT if n == "ちいかわ" else GRAY for n, _ in rows]
    bars = ax.barh(names, vals, color=colors, height=0.65)
    for b, v in zip(bars, vals, strict=True):
        ax.text(
            v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}", va="center", fontsize=8, color=DARK
        )
    ax.set_xlim(0, 90)
    ax.set_title(title)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=8.5)
    ax.tick_params(axis="x", labelsize=8)


def fig3() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(12, 5), gridspec_kw={"width_ratios": [1, 1, 1]})
    _panel(axes[0], GIRLS, "おんなの子 TOP7")
    _panel(axes[1], TOTAL, "子ども総合 TOP8")
    _panel(axes[2], BOYS, "おとこの子 TOP10")
    axes[2].text(
        45,
        -1.3,
        "ちいかわは TOP10 圏外\n（10 位の水準 47.7%）",
        fontsize=8.5,
        color=ACCENT,
        ha="center",
        va="top",
        fontweight="bold",
    )
    axes[1].set_xlabel("人気度（「好き」と回答した割合、%）")
    fig.suptitle(
        "子ども（3〜12 歳）の好きなキャラクター: 女子 1 位、総合 7 位、男子圏外", x=0.01, ha="left"
    )
    footnote(
        fig,
        "出典: ビデオリサーチ「Kids/ex」2025 年 10 月度調査（2026-01-28 発表）。東京 50km 圏、3〜12 歳、有効標本 584、177 キャラ、保護者回答。ちいかわは 2025 年度から調査対象（前回順位なし）。",
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    return save(fig, "fig3_kids_survey.png")


# ---------------------------------------------------------------------------
# fig4: メディア環境
# ---------------------------------------------------------------------------
PANEL_A = [  # (group label, (year label, value) x2, color)
    ("テレビ行為者率\n10〜15 歳（NHK）", [("2015", 78), ("2020", 56)]),
    ("インターネット利用率\n小学生 10 歳以上", [("2021", 96.0), ("2025", 98.5)]),
    ("動画視聴（ネット利用内容）\n小学生 10 歳以上", [("2024", 89.7), ("2025", 88.8)]),
]
KOHAKU = [(1963, 81.4), (1984, 78.1), (1988, 53.9), (2024, 32.7)]


def fig4() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1.25, 1]})

    ax = axes[0]
    width = 0.36
    for gi, (_glabel, pairs) in enumerate(PANEL_A):
        for pi, (ylabel, v) in enumerate(pairs):
            x = gi + (pi - 0.5) * (width + 0.04)
            color = ACCENT if (gi == 0 and pi == 1) else (GRAY if pi == 0 else DARK)
            ax.bar(x, v, width=width, color=color)
            ax.text(x, v + 1.5, f"{v:g}%", ha="center", fontsize=8.5, color=DARK)
            ax.text(x, 3, ylabel, ha="center", fontsize=8, color="white")
    ax.set_xticks(range(len(PANEL_A)))
    ax.set_xticklabels([g for g, _ in PANEL_A], fontsize=8.5)
    ax.set_ylim(0, 110)
    ax.set_ylabel("%")
    ax.grid(axis="x", visible=False)
    ax.set_title("(a) 子どものテレビ接触は急落、ネット・動画はほぼ全員")

    ax = axes[1]
    xs, ys = zip(*KOHAKU, strict=True)
    ax.plot(xs, ys, marker="o", color=GRAY, lw=2, mfc=DARK, mec=DARK)
    for x, y in KOHAKU:
        ax.annotate(
            f"{y}%", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8.5
        )
    ax.set_ylim(0, 100)
    ax.set_xlim(1955, 2032)
    ax.set_xticks(range(1960, 2030, 10))
    ax.set_ylabel("世帯視聴率（%、関東）")
    ax.set_title("(b) NHK 紅白歌合戦 視聴率の長期低下")

    fig.suptitle("テレビの共有視聴は衰退、残る共通接点は少ない", x=0.01, ha="left")
    footnote(
        fig,
        "出典: (a) NHK 放送文化研究所「国民生活時間調査 2020」（平日にテレビを見た人の割合、AV Watch 報道）；こども家庭庁「青少年のインターネット利用環境実態調査」令和3〜7年度"
        "\n（小学生 10 歳以上: ネット利用率 R3 96.0%→R7 98.5%、利用内容「動画視聴」R6 89.7%・R7 88.8%）。(b) ビデオリサーチ 関東世帯視聴率（gendai.media・週刊女性 PRIME 報道、2024 年は第 2 部）。",
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    return save(fig, "fig4_media_environment.png")


if __name__ == "__main__":
    for fn in (fig1, fig2, fig3, fig4):
        print(fn())
