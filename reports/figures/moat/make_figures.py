"""MOAT 成功失敗事例分析 — note 記事用の図版生成スクリプト。

数値はすべて research_notes/MOAT 成功失敗事例分析/*.md（特に cross_case_coding.md）に記載のものだけを使う。
実行: venv/bin/python reports/figures/moat/make_figures.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ACCENT = "#E4572E"
GRAY = "#9A9A9A"
DARK = "#333333"
BLUE = "#3B6EA8"

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
    }
)
SRC = "出典: socioscope research_notes/MOAT 成功失敗事例分析/cross_case_coding.md（2026-11-16）を加工"


def footer(fig, text=SRC):
    fig.text(0.01, 0.01, text, fontsize=7.5, color=GRAY, ha="left", va="bottom")


def fig1_success_moat():
    labels = ["両面ネットワーク効果", "ワークフロー・統合の\nスイッチングコスト", "業務記録の\nスイッチングコスト", "カウンター\nポジショニング", "直接ネットワーク効果", "ブランド", "機能の優位・開発速度"]
    vals = [5, 3, 3, 2, 2, 1, 0]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    colors = [ACCENT if v > 0 else GRAY for v in vals]
    ax.barh(labels[::-1], vals[::-1], color=colors[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.08, i, f"{v} 件", va="center", color=DARK)
    ax.set_xlim(0, 6)
    ax.set_xlabel("成功 16 事例の主な堀（1 事例に 1 つ）")
    ax.set_title("成功 16 事例の主な堀。機能の優位・開発速度を主な堀とした事例は 0 件")
    ax.grid(axis="y", visible=False)
    footer(fig)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig1_success_moat.png", dpi=180)
    plt.close(fig)


def fig2_failure_cause():
    labels = ["配布網に同じ機能を載せた模倣", "プラットフォームの方針変更", "既存製品への無料同梱", "資本戦で持久できず（単位経済）", "単機能のまま吸収", "技術シフトに遅れ"]
    vals = [5, 3, 1, 2, 1, 1]
    colors = [ACCENT, ACCENT, ACCENT, GRAY, GRAY, GRAY]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.barh(labels[::-1], vals[::-1], color=colors[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.08, i, f"{v} 件", va="center", color=DARK)
    ax.set_xlim(0, 6)
    ax.set_xlabel("失敗 13 事例の直接原因（主因、1 事例に 1 つ）")
    ax.set_title("失敗 13 事例の主因。赤の 3 つ（計 9 件）は巨大資本が配布を握っていた")
    ax.grid(axis="y", visible=False)
    footer(fig)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig2_failure_cause.png", dpi=180)
    plt.close(fig)


def fig3_capital_gap():
    # 売上比の概算（各ノートの一覧表）。「10 倍超」としか分からない事例は含めない。同値はラベルをまとめる
    success = [(16, "Canva"), (17, "LinkedIn"), (30, "ビズリーチ"), (34, "Airbnb"), (44, "Figma"), (100, "Workday"), (132, "Snowflake"), (177, "Datadog"), (520, "Shopify"), (590, "Zoom"), (700, "Discord")]
    failure = [(10, "Zynga・mixi・GREE/DeNA"), (12, "Vine"), (100, "Fitbit・Origami"), (1000, "Evernote・Pebble")]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for y, (d, c) in enumerate([(success, BLUE), (failure, ACCENT)]):
        ax.scatter([v for v, _ in d], [y] * len(d), s=70, color=c, zorder=3)
        for i, (v, k) in enumerate(d):
            dy = (10 if i % 2 == 0 else 24) if y == 0 else -16
            ax.annotate(k, (v, y), textcoords="offset points", xytext=(0, dy), ha="center", fontsize=7.5, color=DARK)
    ax.set_xscale("log")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["成功 11 事例", "失敗 8 事例"])
    ax.set_ylim(-0.6, 1.6)
    ax.set_xlabel("巨大資本との資本差（売上または時価総額の倍率、概算、対数軸）")
    ax.set_title("資本差の範囲は成功側と失敗側で重なる（数値が分かる事例のみ）")
    footer(fig, SRC + "。「10 倍超」としか分からない事例は除外")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig3_capital_gap.png", dpi=180)
    plt.close(fig)


def fig4_exit_vs_peak():
    names = ["Slack\n（Salesforce へ）", "Loom\n（Atlassian へ）", "Fitbit\n（Google へ）", "Evernote\n（Bending Spoons へ）", "Origami\n（メルペイへ）"]
    ratio = [27.7 / 23, 0.6, 0.21, 0.2, 2.59e-6 / 417 * 1e6 / 1e2 * 1e2]  # Origami: 259 万円 / 417 億円
    ratio[4] = 259e4 / 417e8
    fig, ax = plt.subplots(figsize=(8, 4.2))
    colors = [BLUE, GRAY, ACCENT, ACCENT, ACCENT]
    ax.bar(names, ratio, color=colors)
    ax.set_yscale("log")
    ax.axhline(1, color=DARK, linewidth=0.8, linestyle="--")
    ax.text(4.4, 1.15, "ピーク評価額と同じ", fontsize=8, color=DARK, ha="right")
    for i, r in enumerate(ratio):
        label = f"{r:.1f} 倍" if r >= 0.5 else (f"約 1/{round(1/r)}" if r > 1e-3 else "約 1/16 万")
        ax.text(i, r * 1.3, label, ha="center", fontsize=9, color=DARK)
    ax.set_ylabel("売却額 ÷ ピーク評価額（対数軸）")
    ax.set_title("売却額はピーク評価額を大きく下回る。上回ったのは買収側の戦略で値がついた Slack だけ")
    ax.grid(axis="x", visible=False)
    footer(fig, "出典: 各社開示・報道（socioscope research_notes/MOAT 成功失敗事例分析/tech_failure_global.md、japan_cases.md、ai_era_2022_2026.md）を加工")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig4_exit_vs_peak.png", dpi=180)
    plt.close(fig)


def fig5_hr_split():
    fig, ax = plt.subplots(figsize=(8, 3.8))
    cats = ["求人メディア・スキマバイト\n（Indeed・LinkedIn・ビズリーチ・タイミー）", "HR SaaS・採用管理\n（Workday・Rippling・Gusto・Deel・Greenhouse）"]
    net = [4, 0]
    rec = [0, 5]
    ax.barh(cats, net, color=ACCENT, label="ネットワーク効果が主な堀")
    ax.barh(cats, rec, left=net, color=BLUE, label="業務記録・ワークフロー・独自資源が主な堀")
    ax.text(2, 0, "4 / 4", ha="center", va="center", color="white", fontweight="bold")
    ax.text(2.5, 1, "5 / 5", ha="center", va="center", color="white", fontweight="bold")
    ax.set_xlim(0, 5.5)
    ax.set_xlabel("成功事例の数（暫定を含む）")
    ax.set_title("人材業界の成功事例は、業態で堀の種類がきれいに分かれる")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.grid(axis="y", visible=False)
    footer(fig, SRC + "。業態の分割は事後に追加した探索的なもの")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig5_hr_split.png", dpi=180)
    plt.close(fig)


def fig6_timee_hallo():
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8))
    ax = axes[0]
    ax.bar(["メルカリ ハロ\n（2025-01）", "タイミー\n（2025-07）"], [15, 39.2], color=[GRAY, ACCENT])
    for i, v in enumerate([15, 39.2]):
        ax.text(i, v + 1, f"{v} 万", ha="center", color=DARK)
    ax.set_title("事業所拠点数（万）")
    ax.set_ylim(0, 46)
    ax.grid(axis="x", visible=False)
    ax = axes[1]
    ax.bar(["メルカリ ハロ", "タイミー"], [95, 1805], color=[GRAY, ACCENT])
    for i, v in enumerate([95, 1805]):
        ax.text(i, v + 40, f"約 {v:,} 万人", ha="center", color=DARK)
    ax.set_title("就業実績（2024 年、人数ベース、万人）")
    ax.set_ylim(0, 2100)
    ax.grid(axis="x", visible=False)
    fig.suptitle("メルカリ ハロは登録者 1,200 万人を集めたが、需要側と実績で 19 倍の差を埋められなかった", fontsize=11)
    footer(fig, "出典: 両社の開示・報道（socioscope research_notes/MOAT 成功失敗事例分析/japan_cases.md）を加工。時点は図中のとおりで揃っていない")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(OUT / "fig6_timee_hallo.png", dpi=180)
    plt.close(fig)


def fig7_public_data():
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8))
    ax = axes[0]
    ax.bar(["2021", "2024", "2025"], [776, 617, 377], color=[GRAY, GRAY, ACCENT])
    for i, v in enumerate([776, 617, 377]):
        ax.text(i, v + 15, f"${v}M", ha="center", color=DARK)
    ax.set_title("Chegg の売上（百万ドル）")
    ax.set_ylim(0, 880)
    ax.grid(axis="x", visible=False)
    ax = axes[1]
    xs = ["2022-11", "2024-12", "2025-12", "2026-05"]
    ys = [108563, 25566, 3862, 976]
    ax.plot(xs, ys, marker="o", color=ACCENT)
    for x, y in zip(xs, ys):
        ax.annotate(f"{y:,}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color=DARK)
    ax.set_yscale("log")
    ax.set_title("Stack Overflow の月間質問数（対数軸）")
    fig.suptitle("公開されたデータは堀にならず、競合モデルの学習源になった", fontsize=11)
    footer(fig, "出典: Chegg 10-K、Stack Exchange Data Explorer 等（socioscope research_notes/MOAT 成功失敗事例分析/ai_era_2022_2026.md）を加工")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(OUT / "fig7_public_data.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig1_success_moat, fig2_failure_cause, fig3_capital_gap, fig4_exit_vs_peak, fig5_hr_split, fig6_timee_hallo, fig7_public_data):
        f()
        print("wrote", f.__name__)
