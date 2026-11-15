"""fig5: 日本の映画興行収入の集中度（2000–2025）。

入力: data/boxoffice_concentration.csv
      （build_boxoffice_dataset.py が生成。出典: 日本映画製作者連盟）
出力: fig5_boxoffice_concentration.png
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
CSV = HERE / "data" / "boxoffice_concentration.csv"
OUT = HERE / "fig5_boxoffice_concentration.png"

GRAY = "#6B6B6B"
LIGHT = "#BDBDBD"
ACCENT = "#E4572E"
plt.rcParams["font.family"] = "Hiragino Sans"
plt.rcParams["axes.unicode_minus"] = False

rows = [r for r in csv.DictReader(CSV.open(encoding="utf-8")) if r["total_oku"]]
years = [int(r["year"]) for r in rows]
top3 = [float(r["top3_share"]) * 100 for r in rows]
top10 = [float(r["top10_share"]) * 100 for r in rows]
n100 = [int(r["n_over_100"]) for r in rows]

fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(10, 7.6), sharex=True, gridspec_kw={"height_ratios": [3, 2], "hspace": 0.12}
)
fig.patch.set_facecolor("white")
for ax in (ax1, ax2):
    ax.set_facecolor("white")
    ax.axvspan(2019.5, 2025.5, color=ACCENT, alpha=0.07, lw=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(LIGHT)
    ax.spines["bottom"].set_color(LIGHT)
    ax.tick_params(colors=GRAY, labelsize=9)
    ax.grid(axis="y", color="#EAEAEA", lw=0.8)
    ax.set_axisbelow(True)

# (a) shares
ax1.plot(years, top10, color=GRAY, lw=2, marker="o", ms=4, label="上位10作品の興収シェア")
ax1.plot(years, top3, color=ACCENT, lw=2.4, marker="o", ms=4, label="上位3作品の興収シェア")
for y, v in zip(years, top3, strict=True):
    if y in (2001, 2020, 2022, 2025):
        ax1.annotate(
            f"{v:.0f}%",
            (y, v),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=8.5,
            color=ACCENT,
        )
ax1.annotate(
    "2020: 鬼滅の刃 無限列車編 407.5億円\n（コロナ禍で総興収は前年の55%）",
    (2020, top3[years.index(2020)]),
    textcoords="offset points",
    xytext=(-150, -120),
    fontsize=8,
    color=GRAY,
    ha="left",
    arrowprops=dict(arrowstyle="-", color=LIGHT, lw=0.8),
)
ax1.set_ylabel("年間興収に占めるシェア（%）", color=GRAY, fontsize=10)
ax1.set_ylim(0, 60)
ax1.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=GRAY)
ax1.set_title("(a) 上位作品への興収集中度", loc="left", fontsize=11, color="#333333")

# (b) count of >=100 oku films
colors = [ACCENT if y >= 2020 else GRAY for y in years]
ax2.bar(years, n100, color=colors, width=0.7)
for y, v in zip(years, n100, strict=True):
    if v:
        ax2.text(y, v + 0.08, str(v), ha="center", va="bottom", fontsize=8, color=GRAY)
ax2.set_ylabel("本数", color=GRAY, fontsize=10)
ax2.set_ylim(0, 5)
ax2.set_yticks(range(0, 5))
ax2.set_title("(b) 興収100億円以上の作品数", loc="left", fontsize=11, color="#333333")
ax2.set_xticks(range(2000, 2026, 5))
ax2.set_xlim(1999.3, 2025.7)
ax2.legend(
    handles=[Patch(color=ACCENT, alpha=0.3, label="2020年代")],
    loc="upper left",
    frameon=False,
    fontsize=9,
    labelcolor=GRAY,
)

fig.suptitle(
    "日本の映画興行収入は上位作品に集中しているか（2000–2025年）",
    x=0.125,
    ha="left",
    fontsize=13,
    color="#222222",
    y=0.975,
)
fig.text(
    0.125,
    0.015,
    "出典: 日本映画製作者連盟「全国映画概況」「興行収入10億円以上番組」(eiren.org)。"
    "シェア＝各年の上位作品の興収（10億円以上番組リスト、暦年集計）÷ 全国興行収入。",
    fontsize=7.5,
    color=GRAY,
)
fig.subplots_adjust(top=0.9, bottom=0.08, left=0.085, right=0.98)
fig.savefig(OUT, dpi=150, facecolor="white")
print("saved", OUT)
