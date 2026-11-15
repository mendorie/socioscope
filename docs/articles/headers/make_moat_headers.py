"""note 記事「誰でも作れる時代の堀」part1〜4 のヘッダー画像（1280×670）。

数値は research_notes/MOAT 成功失敗事例分析/cross_case_coding.md のものだけを使う。
実行: venv/bin/python docs/articles/headers/make_moat_headers.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
W, H, DPI = 1280, 670, 100
BLUE, ORANGE, INK, MUTED, PAPER = "#256abf", "#eb6834", "#1f2a37", "#8a94a3", "#f7f5f0"
matplotlib.rcParams["font.family"] = "Hiragino Sans"
matplotlib.rcParams["axes.unicode_minus"] = False


def canvas():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(PAPER)
    bg = fig.add_axes([0, 0, 1, 1])
    bg.set_axis_off()
    bg.patch.set_alpha(0)
    bg.set_zorder(10)
    bg.set_xlim(0, W)
    bg.set_ylim(0, H)
    return fig, bg


def title_block(bg, title, sub, size=38):
    bg.text(64, 600, title, fontsize=size, fontweight=900, color=INK, va="top", ha="left")
    bg.text(66, 530, sub, fontsize=17, color=MUTED, va="top", ha="left")


def series_tag(bg, text):
    bg.text(64, 40, text, fontsize=13, color=MUTED, va="bottom", ha="left")
    bg.text(W - 40, 18, "socioscope", fontsize=9, color=MUTED, ha="right")


def hbar(fig, labels, vals, colors, rect=(0.08, 0.10, 0.84, 0.52), unit=" 件"):
    ax = fig.add_axes(list(rect))
    ax.barh(labels[::-1], vals[::-1], color=colors[::-1], height=0.62)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.12, i, f"{v}{unit}", va="center", fontsize=15, color=INK, fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.25 if max(vals) else 1)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=14, colors=INK, length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor(PAPER)
    return ax


def part1():
    fig, bg = canvas()
    title_block(bg, "誰でも作れる時代に、巨大資本に勝った企業は何を堀にしたのか", "成功 16 社の主な堀。「機能の優位・開発速度」は 0 件だった", size=33)
    hbar(fig, ["両面ネットワーク効果", "ワークフローのスイッチングコスト", "業務記録のスイッチングコスト", "カウンターポジショニング", "直接ネットワーク効果", "ブランド", "機能の優位・開発速度"], [5, 3, 3, 2, 2, 1, 0], [BLUE] * 6 + [ORANGE])
    series_tag(bg, "誰でも作れる時代の堀 part1 ｜ 成功・失敗 66 事例の比較")
    fig.savefig(OUT / "2026-11-16-note-moat-part1-what-winners-built.png", dpi=DPI, facecolor=PAPER)
    plt.close(fig)


def part2():
    fig, bg = canvas()
    title_block(bg, "初期市場を取ったのに巨大資本に奪われた企業は、何を間違えたのか", "失敗 13 社の主因。9 社は巨大資本が「配布」を握っていた", size=31)
    hbar(fig, ["配布網に同じ機能を載せた模倣", "プラットフォームの方針変更", "既存製品への無料同梱", "資本戦で持久できず", "単機能のまま吸収", "技術シフトに遅れ"], [5, 3, 1, 2, 1, 1], [ORANGE] * 3 + [MUTED] * 3)
    series_tag(bg, "誰でも作れる時代の堀 part2 ｜ 成功・失敗 66 事例の比較")
    fig.savefig(OUT / "2026-11-16-note-moat-part2-how-leaders-lost.png", dpi=DPI, facecolor=PAPER)
    plt.close(fig)


def part3():
    fig, bg = canvas()
    title_block(bg, "人材業界の堀は「供給側」なのか", "求人メディアはネットワーク効果 4/4、HR SaaS は業務記録 5/5。タイミーとメルカリ ハロが示したもの", size=38)
    ax = fig.add_axes([0.08, 0.12, 0.84, 0.50])
    cats = ["求人メディア・スキマバイト\n（Indeed・LinkedIn・ビズリーチ・タイミー）", "HR SaaS・採用管理\n（Workday・Rippling・Gusto・Deel・Greenhouse）"]
    ax.barh(cats, [4, 0], color=ORANGE, height=0.55, label="ネットワーク効果")
    ax.barh(cats, [0, 5], color=BLUE, height=0.55, label="業務記録・ワークフロー")
    ax.text(2, 1, "4 / 4 がネットワーク効果", ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.text(2.5, 0, "5 / 5 が業務記録・ワークフロー", ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.set_xlim(0, 5.3)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=13, colors=INK, length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor(PAPER)
    series_tag(bg, "誰でも作れる時代の堀 part3 ｜ 成功・失敗 66 事例の比較")
    fig.savefig(OUT / "2026-11-16-note-moat-part3-hr-industry.png", dpi=DPI, facecolor=PAPER)
    plt.close(fig)


def part4():
    fig, bg = canvas()
    title_block(bg, "生成 AI 期にモデルの優位は堀になったのか", "25 社のうち、モデル優位だけで 3 年持った企業は 0 社。Stack Overflow の月間質問数はピークの 1% 未満に", size=38)
    ax = fig.add_axes([0.10, 0.12, 0.80, 0.48])
    xs = ["2022-11", "2024-12", "2025-12", "2026-05"]
    ys = [108563, 25566, 3862, 976]
    ax.plot(xs, ys, marker="o", color=ORANGE, lw=4, markersize=11)
    for x, y in zip(xs, ys):
        ax.annotate(f"{y:,}", (x, y), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=14, color=INK, fontweight="bold")
    ax.set_yscale("log")
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=13, colors=MUTED, length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_facecolor(PAPER)
    bg.text(100, 400, "Stack Overflow の月間質問数（対数軸）", fontsize=14, color=MUTED)
    series_tag(bg, "誰でも作れる時代の堀 part4（最終回）｜ 成功・失敗 66 事例の比較")
    fig.savefig(OUT / "2026-11-16-note-moat-part4-ai-era-and-lessons.png", dpi=DPI, facecolor=PAPER)
    plt.close(fig)


if __name__ == "__main__":
    for f in (part1, part2, part3, part4):
        f()
        print("wrote", f.__name__)
