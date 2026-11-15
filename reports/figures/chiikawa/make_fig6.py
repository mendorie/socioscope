"""fig6: テレビで測った「国民的ヒット」の縮小（1990–2025）。

入力:
  data/tv_drama_top_rating.csv  年間最高ドラマの最高回世帯視聴率（関東）
  data/tv_kohaku.csv            NHK紅白歌合戦 第2部 世帯視聴率（関東）
  data/tv_viewing_time.csv      総務省 平日テレビ（リアルタイム）平均視聴時間（全年代・10代）
出力: fig6_tv_decline.png
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "fig6_tv_decline.png"

GRAY = "#6B6B6B"
LIGHT = "#BDBDBD"
ACCENT = "#E4572E"
plt.rcParams["font.family"] = "Hiragino Sans"
plt.rcParams["axes.unicode_minus"] = False


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


drama = [r for r in read("tv_drama_top_rating.csv") if 1990 <= int(r["year"]) <= 2025]
kohaku = [r for r in read("tv_kohaku.csv") if 1990 <= int(r["year"]) <= 2025]
view = read("tv_viewing_time.csv")
all_ages = [r for r in view if r["series"].startswith("全年代(13-69歳)")]
teens = [r for r in view if r["series"].startswith("10代")]

fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(10, 8.4), gridspec_kw={"height_ratios": [3, 2.4], "hspace": 0.38}
)
fig.patch.set_facecolor("white")
for ax in (ax1, ax2):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(LIGHT)
    ax.spines["bottom"].set_color(LIGHT)
    ax.tick_params(colors=GRAY, labelsize=9)
    ax.grid(axis="y", color="#EAEAEA", lw=0.8)
    ax.set_axisbelow(True)

# (a) 紅白 第2部 と 年間最高ドラマ
ky = [int(r["year"]) for r in kohaku]
kv = [float(r["value"]) for r in kohaku]
dy = [int(r["year"]) for r in drama]
dv = [float(r["value"]) for r in drama]
ax1.plot(
    ky, kv, color=GRAY, lw=2, marker="o", ms=3.5, label="NHK紅白歌合戦 第2部（世帯視聴率・関東）"
)
ax1.plot(
    dy,
    dv,
    color=ACCENT,
    lw=2.2,
    marker="o",
    ms=3.5,
    label="年間最高ドラマの最高回（世帯視聴率・関東）",
)
for y, v, lab, ha in [(1998, 57.2, "1998 57.2%", "center"), (2025, 35.2, "2025 35.2%", "right")]:
    ax1.annotate(
        lab,
        (y, v),
        textcoords="offset points",
        xytext=(0, 7),
        ha=ha,
        fontsize=8.5,
        color=GRAY,
    )
for y, lab, off in [
    (2000, "2000 ビューティフルライフ 41.3%", (-6, 8)),
    (2013, "2013 半沢直樹 42.2%", (10, 6)),
    (2020, "2020 半沢直樹 32.7%", (-28, 8)),
    (2024, "2024 13.2%", (-6, -14)),
]:
    v = dv[dy.index(y)]
    ax1.annotate(
        lab,
        (y, v),
        textcoords="offset points",
        xytext=off,
        ha="center",
        fontsize=8.5,
        color=ACCENT,
    )
ax1.set_ylim(0, 65)
ax1.set_xlim(1989.5, 2025.5)
ax1.set_xticks(range(1990, 2026, 5))
ax1.set_ylabel("世帯視聴率（%）", color=GRAY, fontsize=10)
ax1.legend(loc="lower left", frameon=False, fontsize=9, labelcolor=GRAY)
ax1.set_title(
    "(a) テレビの「年間最大ヒット」の世帯視聴率 1990–2025", loc="left", fontsize=11, color="#333333"
)

# (b) 平日 テレビリアルタイム視聴時間
ay = [int(r["year"]) for r in all_ages]
av = [float(r["value"]) for r in all_ages]
ty = [int(r["year"]) for r in teens]
tv = [float(r["value"]) for r in teens]
ax2.plot(ay, av, color=GRAY, lw=2, marker="o", ms=3.5, label="全年代（13〜69歳）")
ax2.plot(ty, tv, color=ACCENT, lw=2.2, marker="o", ms=3.5, label="10代")
for y, v in [(2012, av[0]), (2025, av[-1])]:
    ax2.annotate(
        f"{v:.0f}分",
        (y, v),
        textcoords="offset points",
        xytext=(0, 7),
        ha="center",
        fontsize=8.5,
        color=GRAY,
    )
for y, v in [(2012, tv[0]), (2025, tv[-1])]:
    ax2.annotate(
        f"{v:.0f}分",
        (y, v),
        textcoords="offset points",
        xytext=(0, -14),
        ha="center",
        fontsize=8.5,
        color=ACCENT,
    )
ax2.set_ylim(0, 210)
ax2.set_xlim(2011.5, 2025.5)
ax2.set_xticks(range(2012, 2026, 1))
ax2.set_ylabel("平日1日あたり（分）", color=GRAY, fontsize=10)
ax2.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=GRAY)
ax2.set_title(
    "(b) 平日のテレビ（リアルタイム）平均視聴時間 2012–2025",
    loc="left",
    fontsize=11,
    color="#333333",
)

fig.text(
    0.01,
    0.005,
    "出典: (a) ビデオリサーチ「ドラマ高世帯視聴率番組」「令和ドラマ視聴率ランキング」、"
    "年代流行（出典未記載年あり）、\n"
    "       Wikipedia「NHK紅白歌合戦」（ビデオリサーチ引用）。"
    "いずれも関東地区・世帯・リアルタイム。\n"
    "(b) 総務省情報通信政策研究所「情報通信メディアの利用時間と情報行動に関する調査」"
    "各年度 概要・報告書\n"
    "       （13〜69歳集計。2024年度以降は70代を除いた参考値）。",
    fontsize=7.5,
    color=GRAY,
    ha="left",
    va="bottom",
)
fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.13)
fig.savefig(OUT, dpi=150, facecolor="white")
print(f"wrote {OUT}")
