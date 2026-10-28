"""R12: 将来人口で一票の格差はどうなるか — 定数を減らさなくても 2 倍を超えるのか（H11）。

事後追加の仮説 H11（design/themes/parliament-size.md「事後追加（2026-10-29、R11〜R13）」、
結果の計算前に固定）:
  IPSS 地域別将来推計人口（2023 年推計）の都道府県別 2030・2040・2050 年人口にアダムズ方式を当て、
  小選挙区 289 と 260 の都道府県単位の最大格差と、2022 年区割りの上乗せ係数（1.193）
  を掛けた見込みを出す。
  判定: 289 でも 2040 年に 2.0 倍を超える見込みなら「問題は定数ではなく区割り」に整合。

決定的スクリプト。入力は data/marts/{jp_prefecture_projection, jp_census2020_prefecture}.parquet。
推計は総人口（外国人を含む）で、画定審が使う日本人人口とは違う（2020
年の両者の格差を併記して差を示す）。
純粋ヘルパは tests/test_analysis_r12.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size import apportion
from theme_parliament_size.analysis.a20261027_r2_pr_blocks import disparity, md_row
from theme_parliament_size.analysis.a20261028_r6_pr_history import DISTRICT_MAX_RATIO_2022

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
YEARS = (2020, 2030, 2040, 2050)
SEATS = (289, 260)
PREF_RATIO_2020_JAPANESE = 1.675  # R2: 2020 日本人人口・289 の都道府県単位格差（係数 1.193 の分母）


# ---- pure helpers -------------------------------------------------------------------------------


def pref_ratio(populations: Mapping[str, float], seats: int) -> tuple[float, str, str, int]:
    """アダムズ配分での都道府県単位の最大 ÷ 最小、最大県、最小県、定数 2 以下の県の数。"""
    alloc = apportion.adams(populations, seats)
    ratio, hi, lo = disparity(populations, alloc)
    return ratio, hi, lo, sum(1 for v in alloc.values() if v <= 2)


def judge_h11(projected_289_2040: float) -> str:
    return "整合" if projected_289_2040 > 2.0 else "不支持"


# ---- figure --------------------------------------------------------------------------------------


def fig_lines(table: Mapping[int, Mapping[int, float]], uplift: float, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for i, n in enumerate(SEATS):
        ys = [table[y][n] for y in YEARS]
        ax.plot(YEARS, ys, marker="o", color=SERIES[i], label=f"{n} 都道府県単位")
        ax.plot(
            YEARS,
            [v * uplift for v in ys],
            marker="o",
            linestyle="--",
            color=SERIES[i],
            label=f"{n} × 区割り係数 {uplift:.2f}",
        )
    ax.axhline(2.0, color=MUTED, linestyle=":", linewidth=0.8)
    ax.set_xticks(YEARS)
    ax.set_ylabel("1 議席当たり人口の 最大 ÷ 最小", fontsize=8, color=INK)
    ax.set_title("将来推計人口で見た小選挙区の一票の格差（アダムズ方式）", fontsize=10, loc="left")
    ax.legend(fontsize=7, frameon=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    note = (
        "出典: IPSS 日本の地域別将来推計人口（令和 5 年推計、総人口）、画定審 勧告 2022 の係数。"
        "点線 = 2.0 倍"
    )
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    marts = args.data_dir / "marts"
    proj = pl.read_parquet(marts / "jp_prefecture_projection.parquet")
    census = pl.read_parquet(marts / "jp_census2020_prefecture.parquet")
    uplift = DISTRICT_MAX_RATIO_2022 / PREF_RATIO_2020_JAPANESE

    print("# R12 将来人口で一票の格差はどうなるか（H11）（2026-10-29）")
    print("\n事後追加の仮説（設計書 2026-10-29 節）。機械的試算のみ。因果の主張はない。")
    jp_pop = {str(r["pref"]): float(r["population_japanese"]) for r in census.iter_rows(named=True)}
    r_jp, hi, lo, _ = pref_ratio(jp_pop, 289)
    print(
        f"\n- 検算: 2020 国勢調査 日本人人口・289 の都道府県単位格差 = {r_jp:.3f}（R2 の 1.675 "
        "と一致するか）"
    )
    print(
        f"- 区割りの上乗せ係数 = {DISTRICT_MAX_RATIO_2022} ÷ {PREF_RATIO_2020_JAPANESE} = "
        f"{uplift:.3f}"
    )
    print(
        "\n## 表 1: 都道府県単位の最大格差（アダムズ方式、IPSS 推計の総人口）"
        "と区割り係数を掛けた見込み"
    )
    print(
        md_row(
            [
                "年",
                "定数",
                "最大（県）",
                "最小（県）",
                "都道府県単位 最大 ÷ 最小",
                "× 係数（選挙区単位の見込み）",
                "定数 2 以下の県",
            ]
        )
    )
    print("|" + "---|" * 7)
    table: dict[int, dict[int, float]] = {}
    for y in YEARS:
        pops = {
            str(r["pref"]): float(r["population"])
            for r in proj.filter(pl.col("year") == y).iter_rows(named=True)
        }
        table[y] = {}
        for n in SEATS:
            ratio, hi, lo, n2 = pref_ratio(pops, n)
            table[y][n] = ratio
            print(
                md_row(
                    [
                        y,
                        n,
                        f"{pops[hi] / apportion.adams(pops, n)[hi]:,.0f}（{hi}）",
                        f"{pops[lo] / apportion.adams(pops, n)[lo]:,.0f}（{lo}）",
                        f"{ratio:.3f}",
                        f"{ratio * uplift:.3f}",
                        n2,
                    ]
                )
            )
    p289 = table[2040][289] * uplift
    print(
        f"\n- 2020 年の総人口ベース 289 は {table[2020][289]:.3f}（日本人人口ベース "
        f"{PREF_RATIO_2020_JAPANESE}）。"
        "総人口は外国人の多い都市部を重く見るため、格差がやや大きく出る"
    )
    print(
        f"- 289 のまま 2040 年: 都道府県単位 {table[2040][289]:.3f}、係数込み {p289:.3f}。260 "
        f"なら {table[2040][260] * uplift:.3f}"
    )
    print(f"- **H11 判定: {judge_h11(p289)}**（289 でも 2040 年に係数込みで 2.0 倍を超えれば整合）")
    fig_lines(table, uplift, args.fig_dir / "r12_future_disparity.png")
    print(f"\n図: {args.fig_dir}/r12_future_disparity.png")


if __name__ == "__main__":
    main()
