"""fig7: Google Trends（日本）月次検索インタレスト。

入力: data/google_trends.csv（fetch_trends.py の出力、2026-10-24 取得）
実行: venv/bin/python reports/figures/chiikawa/make_fig7.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ACCENT = "#E4572E"
GRAY = "#9A9A9A"
GRAY2 = "#C8C8C8"

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


def main() -> Path:
    df = pd.read_csv(HERE / "data" / "google_trends.csv", index_col=0, parse_dates=True)
    main_cols = ["ちいかわ", "すみっコぐらし", "鬼滅の刃"]
    a = df.loc["2019-01":"2026-10", main_cols].dropna(how="all")
    y = df.loc["2013-01":"2016-12", "妖怪ウォッチ"].dropna()

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [3, 1.3]}, sharey=True
    )

    ax1.plot(a.index, a["鬼滅の刃"], color=GRAY, lw=1.4, label="鬼滅の刃")
    ax1.plot(a.index, a["すみっコぐらし"], color=GRAY2, lw=1.4, label="すみっコぐらし")
    ax1.plot(a.index, a["ちいかわ"], color=ACCENT, lw=2.2, label="ちいかわ")
    ax1.set_title("ちいかわ・すみっコぐらし・鬼滅の刃（2019-01〜2026-10、同一スケール）")
    ax1.set_ylabel("検索インタレスト（期間内最大＝100）")
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.set_ylim(0, 105)
    for x, lab in [
        ("2020-10-01", "無限列車編\n(2020-10)"),
        ("2022-04-01", "めざましTV\nアニメ開始\n(2022-04)"),
        ("2026-07-01", "映画ちいかわ\n(2026-07)"),
    ]:
        ax1.axvline(pd.Timestamp(x), color="#BBBBBB", lw=0.8, ls="--")
        ax1.text(pd.Timestamp(x), 102, lab, fontsize=7, color="#666666", ha="center", va="top")
    ax1.legend(frameon=False, loc="center left", fontsize=9)

    ax2.plot(y.index, y, color=GRAY, lw=1.6, label="妖怪ウォッチ")
    ax2.set_title("妖怪ウォッチ（2013-01〜2016-12、別スケール）")
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.axvline(pd.Timestamp("2014-12-01"), color="#BBBBBB", lw=0.8, ls="--")
    ax2.text(
        pd.Timestamp("2014-12-01"),
        102,
        "映画1作目\n(2014-12)",
        fontsize=7,
        color="#666666",
        ha="center",
        va="top",
    )
    ax2.legend(frameon=False, loc="upper left", fontsize=9)

    fig.suptitle(
        "図7 Google 検索インタレスト（日本）: ちいかわは「山」ではなく「台地」", x=0.01, ha="left"
    )
    fig.text(
        0.01,
        0.01,
        "出典: Google Trends（geo=JP、pytrends 4.9.2 で 2026-10-24 取得、月平均）。左右のパネルは別リクエストのため値は比較不可。"
        "左: 鬼滅の刃 2020-10 =100。ちいかわの最大は 2026-08 の 76。",
        fontsize=7,
        color="#666666",
        ha="left",
        va="bottom",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    out = HERE / "fig7_search_interest.png"
    fig.savefig(out, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(main())
