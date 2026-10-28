"""R6: 比例削減の試算は選挙で変わるか／小選挙区を減らすと選挙区単位の格差はどうなるか。

事後追加の仮説 H3d・H3e・H4c・H4d（design/themes/parliament-size.md
「事後追加の仮説（2026-10-28）」、結果の計算前に固定）:
  H3d : 第 45〜51 回（2009–2026）の 7 回それぞれで比例 131／145（アダムズ方式 × 2020 国勢調査
        日本人人口でブロック配分）を当てはめる。基準線は各選挙の法定定数（180／176）の純ドント。
        ドント 131 で小政党群（全国比例得票率 10% 未満）の減少率 − 大政党群 ≥ 5 pt が判定可能な
        n 回中 n − 1 回以上なら H3 は頑健。修正サンラグ 131 で差 < 5 pt が n − 1 回以上なら H3b は
        頑健。小政党群の基準議席が 5 未満の選挙は判定不能として除く（事後の具体化）。
  H3e : 2014（180）→ 2017（176）の 4 減は小さく識別は期待できない。小政党群の合計得票率・
        有効政党数（得票、Laakso–Taagepera）・議席を得た政党数・比例の Gallagher 指数の推移を
        記述する（判定しない）。
  H4c : (a) アダムズ方式で小選挙区定数を 289 から 1 ずつ減らし、都道府県単位の最大格差が初めて
        2.0 倍を超える定数 N* を求める。(b) 2022 年区割りの選挙区単位の最大格差（画定審勧告
        1.999、2020 日本国民人口）÷ 都道府県単位（1.675）を上乗せ係数とし、260 の都道府県単位
        格差に掛けて 2.0 を超えれば整合。
  H4d : 第 45〜51 回のブロック間格差（1 議席当たり有権者数の最大 ÷ 最小）と定数 10 以下の
        ブロックの参入閾値（ドント）の推移を記述する（判定しない）。

決定的スクリプト。入力は data/marts/{jp_hr_pr_results, jp_hr_electorate, jp_census2020_prefecture}
.parquet。R2 の純粋ヘルパ（配分・減少率・格差）を再利用し、R6 固有のヘルパは
tests/test_analysis_r6.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_parliament_size import apportion
from theme_parliament_size.analysis.a20261027_r2_pr_blocks import (
    SMALL_PARTY_MAX_SHARE,
    allocate,
    block_populations,
    block_votes_of,
    disparity,
    group_reduction,
    md_row,
    national_shares,
    official_block_seats,
    party_totals,
)
from theme_parliament_size.soumu import BLOCKS

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
ELECTIONS: tuple[int, ...] = (45, 46, 47, 48, 49, 50, 51)
SCENARIOS: dict[str, int] = {"145": 145, "131": 131}
MIN_SMALL_SEATS = (
    5  # 小政党群の基準議席がこれ未満の選挙は減少率が意味を持たず判定不能（事後の具体化）
)
SMD_CURRENT = 289
SMD_FLOOR = 230  # 探索の下限（47 都道府県 × 1 以上という制約よりはるかに上）
# 2022 年区割り改定（衆議院議員選挙区画定審議会 勧告 2022-06-16）の選挙区単位の最大格差。
# 2020 年国勢調査の日本国民人口ベース。手入力の定数（出典: 画定審 勧告・総務省公表資料）。
DISTRICT_MAX_RATIO_2022 = 1.999


# ---- pure helpers -------------------------------------------------------------------------------


def effective_number(shares: Mapping[str, float]) -> float:
    """Laakso–Taagepera の有効政党数（% 単位の得票率または議席率）。"""
    s = sum((v / 100.0) ** 2 for v in shares.values())
    return 1.0 / s if s > 0 else 0.0


def seat_shares(seats: Mapping[str, int]) -> dict[str, float]:
    total = sum(seats.values())
    return {p: 100.0 * s / total for p, s in seats.items()} if total else {}


def small_party_share(shares: Mapping[str, float]) -> float:
    return sum(v for v in shares.values() if v < SMALL_PARTY_MAX_SHARE)


def first_seats_over(
    populations: Mapping[str, float], start: int, floor: int, limit: float = 2.0
) -> tuple[int | None, dict[int, float]]:
    """定数を start から 1 ずつ floor まで減らし、都道府県単位の最大格差が初めて limit
    を超える定数と、
    定数ごとの格差を返す。超えなければ (None, 格差表)。"""
    ratios: dict[int, float] = {}
    first: int | None = None
    for n in range(start, floor - 1, -1):
        alloc = apportion.adams(populations, n)
        ratio, _, _ = disparity(populations, alloc)
        ratios[n] = ratio
        if first is None and ratio > limit:
            first = n
    return first, ratios


def district_uplift(district_ratio: float, pref_ratio: float) -> float:
    """区割りの上乗せ係数 = 選挙区単位の最大格差 ÷ 同じ人口での都道府県単位の最大格差。"""
    if pref_ratio <= 0:
        msg = "pref_ratio must be positive"
        raise ValueError(msg)
    return district_ratio / pref_ratio


def judge_robust(hits: int, n: int) -> str:
    """判定可能な n 回のうち n − 1 回以上で基準を満たせば頑健（7 回なら 6 回以上）。"""
    if n < 2:
        return "判定不能"
    return "頑健" if hits >= n - 1 else "選挙により変わる"


def judge_h4c(projected: float) -> str:
    return "整合" if projected > 2.0 else "不支持"


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_history(rows: Sequence[Mapping[str, object]], path: Path) -> None:
    import matplotlib.pyplot as plt

    years = [str(r["year"]) for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.6))
    specs = [
        ("small_share", "小政党群（得票率 <10%）の合計得票率 %", SERIES[1]),
        ("enp_votes", "有効政党数（比例得票）", SERIES[0]),
        ("gallagher_pr", "Gallagher 指数（比例のみ）", SERIES[2]),
    ]
    for ax, (key, title, color) in zip(axes, specs, strict=True):
        ax.plot(years, [float(str(r[key])) for r in rows], marker="o", color=color)
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.axvline(x=2.5, color=MUTED, linestyle=":", linewidth=0.8)  # 2014 → 2017 の間
        _style(ax)
    note = (
        "出典: 総務省 衆議院議員総選挙 結果調（第 45〜51 回）。点線 = 比例定数 180 → 176（2017 "
        "年）。"
        "横軸は選挙年"
    )
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_robustness(
    diffs: Mapping[str, Sequence[float]],
    years: Sequence[int],
    valid: Sequence[bool],
    path: Path,
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    x = np.arange(len(years))
    labels = list(diffs)
    w = 0.8 / len(labels)
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    for i, lab in enumerate(labels):
        vals = [d if ok else 0.0 for d, ok in zip(diffs[lab], valid, strict=True)]
        ax.bar(x + (i - (len(labels) - 1) / 2) * w, vals, width=w, color=SERIES[i], label=lab)
    for xi, ok in zip(x, valid, strict=True):
        if not ok:
            ax.text(
                float(xi),
                1.0,
                "判定不能\n（小政党群の\n基準議席 < 5）",
                ha="center",
                fontsize=7,
                color=MUTED,
            )
    ax.axhline(5.0, color=MUTED, linestyle="--", linewidth=0.8)
    ax.axhline(0.0, color=INK, linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years])
    ax.set_ylabel("小政党群の減少率 − 大政党群の減少率（pt）", fontsize=8, color=INK)
    ax.set_title(
        "比例定数を減らしたときの小政党への偏り（7 選挙、機械的試算）", fontsize=10, loc="left"
    )
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    note = (
        "出典: 総務省 結果調の比例得票から再計算。破線 = 事前基準 5 pt。"
        "基準線は各選挙の法定定数の純ドント"
    )
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_lower_bound(ratios: Mapping[int, float], uplift: float, path: Path) -> None:
    import matplotlib.pyplot as plt

    ns = sorted(ratios)
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.plot(ns, [ratios[n] for n in ns], color=SERIES[0], label="都道府県単位（区割りの下限）")
    ax.plot(
        ns,
        [ratios[n] * uplift for n in ns],
        color=SERIES[1],
        label=f"× 区割り上乗せ係数 {uplift:.2f}",
    )
    ax.axhline(2.0, color=MUTED, linestyle="--", linewidth=0.8)
    ax.set_xlabel("小選挙区の定数（アダムズ方式、2020 国勢調査 日本人人口）", fontsize=8, color=INK)
    ax.set_ylabel("1 議席当たり人口の 最大 ÷ 最小", fontsize=8, color=INK)
    ax.set_title(
        "小選挙区を減らすと一票の格差はどこまで広がるか", fontsize=10, color=INK, loc="left"
    )
    ax.legend(fontsize=8, frameon=False)
    ax.invert_xaxis()
    _style(ax)
    note = (
        "出典: e-Stat 令和 2 年国勢調査 表 2-1、画定審 勧告（2022-06-16）の最大格差 1.999 倍。"
        "破線 = 2.0 倍"
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
    fonts = ["Hiragino Sans", "Noto Sans CJK JP", "IPAPGothic", "IPAGothic", "sans-serif"]
    matplotlib.rcParams["font.family"] = fonts
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    marts = args.data_dir / "marts"
    pr = pl.read_parquet(marts / "jp_hr_pr_results.parquet")
    el = pl.read_parquet(marts / "jp_hr_electorate.parquet")
    census = pl.read_parquet(marts / "jp_census2020_prefecture.parquet")

    el51 = el.filter(pl.col("election") == 51)
    block_of = {str(r["pref"]): str(r["block"]) for r in el51.iter_rows(named=True)}
    prefs = list(census.iter_rows(named=True))
    pops = block_populations(prefs, block_of)
    pref_pop = {str(r["pref"]): float(r["population_japanese"]) for r in prefs}
    scen_seats = {lab: apportion.adams(pops, n) for lab, n in SCENARIOS.items()}
    dates = {int(r["election"]): str(r["election_date"]) for r in pr.iter_rows(named=True)}

    print(
        "# R6 比例削減の試算は選挙で変わるか／小選挙区の格差の見通し（H3d・H3e・H4c・H4d）"
        "（2026-10-28）"
    )
    print("\n事後追加の仮説（設計書 2026-10-28 節）。機械的試算と記述のみ。因果の主張はない。")

    # ---- H3d / H3e ----
    print("\n## 表 1: 7 選挙の比例（基準線 = 各選挙の法定定数の純ドント）と 131／145 の試算")
    print(
        md_row(
            [
                "回（年）",
                "法定",
                "政党数（得票）",
                "議席あり",
                "小政党群 得票率 %",
                "小政党群 議席（基準）",
                "有効政党数（得票）",
                "Gallagher 比例",
                "ドント 145 差 pt",
                "ドント 131 差 pt",
                "修正サンラグ 145 差 pt",
                "修正サンラグ 131 差 pt",
            ]
        )
    )
    print("|" + "---|" * 12)
    hist: list[dict[str, object]] = []
    diffs: dict[str, list[float]] = {
        "ドント 145": [],
        "ドント 131": [],
        "修正サンラグ 145": [],
        "修正サンラグ 131": [],
    }
    for e in ELECTIONS:
        bv = block_votes_of(pr, e)
        shares = national_shares(bv)
        official_seats = official_block_seats(pr, e)
        base = party_totals(allocate(bv, official_seats, "dhondt"))
        legal = sum(official_seats.values())
        row: dict[str, object] = {
            "election": e,
            "year": dates[e][:4],
            "legal": legal,
            "n_parties": len(shares),
            "n_with_seats": sum(1 for s in base.values() if s > 0),
            "small_share": small_party_share(shares),
            "small_seats": sum(s for p, s in base.items() if shares[p] < SMALL_PARTY_MAX_SHARE),
            "enp_votes": effective_number(shares),
            "gallagher_pr": apportion.gallagher(shares, seat_shares(base)),
        }
        cells: list[str] = []
        for method, mlab in (("dhondt", "ドント"), ("msl", "修正サンラグ")):
            for lab in SCENARIOS:
                after = party_totals(allocate(bv, scen_seats[lab], method))
                _, _, d = group_reduction(base, after, shares)
                diffs[f"{mlab} {lab}"].append(d)
                cells.append(f"{d:+.1f}")
        hist.append(row)
        print(
            md_row(
                [
                    f"{e}（{row['year']}）",
                    legal,
                    row["n_parties"],
                    row["n_with_seats"],
                    f"{float(str(row['small_share'])):.1f}",
                    row["small_seats"],
                    f"{float(str(row['enp_votes'])):.2f}",
                    f"{float(str(row['gallagher_pr'])):.2f}",
                    *cells,
                ]
            )
        )
    valid = [i for i, r in enumerate(hist) if int(str(r["small_seats"])) >= MIN_SMALL_SEATS]
    excluded = [
        f"{hist[i]['election']}（{hist[i]['year']}、小政党群 {hist[i]['small_seats']} 議席）"
        for i in range(len(hist))
        if i not in valid
    ]
    n_valid = len(valid)

    def hits(lab: str, ok: Callable[[float], bool]) -> int:
        return sum(1 for i in valid if ok(diffs[lab][i]))

    def rng(lab: str) -> str:
        vals = [diffs[lab][i] for i in valid]
        return f"{min(vals):+.1f}〜{max(vals):+.1f}"

    hits_d = hits("ドント 131", lambda d: d >= 5.0)
    hits_m = hits("修正サンラグ 131", lambda d: d < 5.0)
    hits_d145 = hits("ドント 145", lambda d: d >= 5.0)
    hits_m145 = hits("修正サンラグ 145", lambda d: d < 5.0)
    print(
        f"\n- 判定不能として除外（小政党群の基準議席 < {MIN_SMALL_SEATS}、減少率が 1〜2 "
        "議席で振れる）: " + ("、".join(excluded) if excluded else "なし")
    )
    print(
        f"- ドント 131 で差 ≥ 5 pt: {hits_d}/{n_valid} 回（範囲 {rng('ドント 131')} pt）。"
        f"145 では {hits_d145}/{n_valid} 回（{rng('ドント 145')} pt）"
    )
    print(
        f"- 修正サンラグ 131 で差 < 5 pt: {hits_m}/{n_valid} 回（範囲 {rng('修正サンラグ 131')} "
        "pt）。"
        f"145 では {hits_m145}/{n_valid} 回（{rng('修正サンラグ 145')} pt）"
    )
    print(
        f"- **H3d 判定: H3（ドント）は{judge_robust(hits_d, n_valid)}、"
        f"H3b（修正サンラグ）は{judge_robust(hits_m, n_valid)}**"
        f"（判定可能 {n_valid} 回中 {n_valid - 1} 回以上で頑健）"
    )
    s14 = next(r for r in hist if r["election"] == 47)
    s17 = next(r for r in hist if r["election"] == 48)
    print(
        "- H3e（記述、判定しない）: 2014 → 2017（180 → 176）で小政党群の得票率 "
        f"{float(str(s14['small_share'])):.1f}% → {float(str(s17['small_share'])):.1f}%、"
        f"有効政党数 {float(str(s14['enp_votes'])):.2f} → {float(str(s17['enp_votes'])):.2f}、"
        f"議席あり {s14['n_with_seats']} → {s17['n_with_seats']} 党。"
        "4 議席の削減では定数の効果と政党の離合集散（2017 年の希望の党・立憲民主党の結成）"
        "を分けられない"
    )
    years = [int(str(r["year"])) for r in hist]
    fig_history(hist, args.fig_dir / "r6_small_party_history.png")
    fig_robustness(
        diffs, years, [i in valid for i in range(len(hist))], args.fig_dir / "r6_h3_robustness.png"
    )

    # ---- H4d ----
    print("\n## 表 2: ブロック間の 1 議席当たり有権者数（最大 ÷ 最小）と小ブロックの参入閾値の推移")
    small_blocks = [b for b in BLOCKS if official_block_seats(pr, 51)[b] <= 10]
    print(
        md_row(
            [
                "回（年）",
                "ブロック定数 計",
                "最大（ブロック）",
                "最小（ブロック）",
                "最大 ÷ 最小",
                *small_blocks,
            ]
        )
    )
    print("|" + "---|" * (5 + len(small_blocks)))
    for e in ELECTIONS:
        electorate = dict.fromkeys(BLOCKS, 0.0)
        for r in el.filter(pl.col("election") == e).iter_rows(named=True):
            electorate[str(r["block"])] += float(r["electorate_pr"])
        seats = official_block_seats(pr, e)
        ratio, hi, lo = disparity(electorate, seats)
        bv = block_votes_of(pr, e)
        thr = [
            f"{apportion.threshold_share(bv[b], seats[b], '__new__'):.1f}（{seats[b]}）"
            for b in small_blocks
        ]
        print(
            md_row(
                [
                    f"{e}（{dates[e][:4]}）",
                    sum(seats.values()),
                    f"{electorate[hi] / seats[hi]:,.0f}（{hi}）",
                    f"{electorate[lo] / seats[lo]:,.0f}（{lo}）",
                    f"{ratio:.3f}",
                    *thr,
                ]
            )
        )
    print("- 閾値の列は「1 議席を取るのに必要な得票率 %（ブロック定数）」。H4d は記述のみ。")

    # ---- H4c ----
    first, ratios = first_seats_over(pref_pop, SMD_CURRENT, SMD_FLOOR)
    pref_289 = ratios[SMD_CURRENT]
    pref_260 = ratios[260]
    uplift = district_uplift(DISTRICT_MAX_RATIO_2022, pref_289)
    projected = pref_260 * uplift
    print(
        "\n## 表 3: 小選挙区の定数と都道府県単位の最大格差（アダムズ方式、2020 国勢調査 "
        "日本人人口）"
    )
    print(md_row(["定数", "定数 2 の県", "都道府県単位 最大 ÷ 最小", "× 区割り上乗せ係数"]))
    print("|---|---|---|---|")
    for n in (289, 280, 270, 260, 250, 240, 230):
        alloc = apportion.adams(pref_pop, n)
        n2 = sum(1 for v in alloc.values() if v <= 2)
        print(md_row([n, n2, f"{ratios[n]:.3f}", f"{ratios[n] * uplift:.3f}"]))
    first_txt = f"{first}" if first is not None else f"{SMD_FLOOR} まで超えない"
    print(f"- (a) 都道府県単位の最大格差が初めて 2.0 倍を超える定数 N* = {first_txt}")
    print(
        f"- (b) 区割りの上乗せ係数 = {DISTRICT_MAX_RATIO_2022} ÷ {pref_289:.3f} = {uplift:.3f}。"
        f"260 の都道府県単位 {pref_260:.3f} × {uplift:.3f} = {projected:.3f}"
    )
    print(
        f"- **H4c 判定: {judge_h4c(projected)}**（係数一定の仮定のもとで選挙区単位の最大格差 "
        f"{projected:.2f} 倍）"
    )
    fig_lower_bound(ratios, uplift, args.fig_dir / "r6_smd_lower_bound.png")
    print(
        f"\n図: {args.fig_dir}/r6_small_party_history.png, r6_h3_robustness.png, "
        "r6_smd_lower_bound.png"
    )


if __name__ == "__main__":
    main()
