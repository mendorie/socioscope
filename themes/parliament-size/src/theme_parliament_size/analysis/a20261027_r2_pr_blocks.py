"""R2: 比例代表の削減は少数政党と地方ブロックに何をするか（H3・H3b・H3c・H4・H4b）。

事前登録（design/themes/parliament-size.md、2026-10-27）:
  H3  : 第 50 回・第 51 回の比例得票を 176 → 131（ドント）に当てはめると、比例得票率 10% 未満
        の政党の議席減少率は 10% 以上の政党より大きく、差 ≥ 5 pt なら整合。どちらかで差 < 0 なら
        不支持。
  H3b : 修正サンラグ（第 1 除数 1.4）は 131／145 で差を 5 pt 未満に戻す。
  H3c : Gallagher 指数（小選挙区＋比例の合計議席）は 176 → 131 で ≥ 1 pt 上がれば整合。
  H4  : 比例のみの削減で (a) 小選挙区の格差は定義上不変、(b) ブロック間の 1 議席当たり有権者数の
        最大 ÷ 最小 が 1.1 倍以上拡大、(c) 定数 10 以下のブロックの 1 議席の最小得票率が 2 pt 以上
        上がる。
  H4b : アダムズ方式で小選挙区 289 → 260 にすると、最大格差 > 2.0 なら整合。

ブロック定数の再配分は現行法どおり アダムズ方式 × 令和 2 年国勢調査の日本人人口（都道府県 → ブロック
集計）。現行 176 の配分と 289 の都道府県配分を再現できることを先に検算する。比例の議席配分は純粋な
ドント式で、名簿登載者不足による他党への移転（2024 東海・北関東、2026 の複数ブロック）は織り込まない
（事前登録どおり「票が同じなら」の機械的試算）。

決定的スクリプト。入力は data/marts/{jp_hr_pr_results, jp_hr_electorate, jp_hr_seats_by_party,
jp_census2020_prefecture}.parquet。純粋ヘルパは tests/test_analysis_r2.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_parliament_size import apportion
from theme_parliament_size.soumu import BLOCKS

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
SMALL_PARTY_MAX_SHARE = 10.0  # 比例得票率 10% 未満 = 小政党（事前登録）
PR_SCENARIOS: dict[str, int] = {"現行 176": 176, "31 減 145": 145, "45 減 131": 131}
CURRENT, S145, S131 = "現行 176", "31 減 145", "45 減 131"
SMD_CURRENT, SMD_REDUCED = 289, 260

Votes = Mapping[str, float]  # party -> votes
BlockVotes = Mapping[str, Votes]  # block -> party -> votes


# ---- pure helpers -------------------------------------------------------------------------------


def block_populations(
    prefs: Sequence[Mapping[str, object]], block_of: Mapping[str, str]
) -> dict[str, float]:
    out: dict[str, float] = dict.fromkeys(BLOCKS, 0.0)
    for r in prefs:
        out[block_of[str(r["pref"])]] += float(str(r["population_japanese"]))
    return out


def allocate(
    bv: BlockVotes, block_seats: Mapping[str, int], method: str = "dhondt"
) -> dict[str, dict[str, int]]:
    """ブロックごとに配分。method: 'dhondt' | 'msl'（修正サンラグ 1.4）。"""
    out: dict[str, dict[str, int]] = {}
    for b, votes in bv.items():
        n = block_seats[b]
        if method == "dhondt":
            out[b] = apportion.dhondt(votes, n)
        elif method == "msl":
            out[b] = apportion.sainte_lague(votes, n, first_divisor=1.4)
        else:
            msg = f"unknown method {method}"
            raise ValueError(msg)
    return out


def party_totals(alloc: Mapping[str, Mapping[str, int]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for seats in alloc.values():
        for p, s in seats.items():
            out[p] = out.get(p, 0) + s
    return out


def national_shares(bv: BlockVotes) -> dict[str, float]:
    tot: dict[str, float] = {}
    for votes in bv.values():
        for p, v in votes.items():
            tot[p] = tot.get(p, 0.0) + v
    s = sum(tot.values())
    return {p: 100.0 * v / s for p, v in tot.items()}


def group_reduction(
    base: Mapping[str, int], after: Mapping[str, int], shares: Mapping[str, float]
) -> tuple[float, float, float]:
    """(小政党の議席減少率 %, 大政党の議席減少率 %, 差 pt)。議席 0 の群は減少率 0。"""
    small = [p for p in base if shares.get(p, 0.0) < SMALL_PARTY_MAX_SHARE]
    large = [p for p in base if shares.get(p, 0.0) >= SMALL_PARTY_MAX_SHARE]

    def rate(ps: Sequence[str]) -> float:
        b = sum(base[p] for p in ps)
        a = sum(after.get(p, 0) for p in ps)
        return 100.0 * (b - a) / b if b else 0.0

    rs, rl = rate(small), rate(large)
    return rs, rl, rs - rl


def judge_h3(diffs: Sequence[float]) -> str:
    if all(d >= 5.0 for d in diffs):
        return "整合"
    if any(d < 0 for d in diffs):
        return "不支持"
    return "中間"


def judge_h3b(diffs: Sequence[float]) -> str:
    return "整合" if all(d < 5.0 for d in diffs) else "不支持"


def gallagher_chamber(
    shares: Mapping[str, float], smd: Mapping[str, float], pr: Mapping[str, int]
) -> float:
    """得票率は比例の全国得票率、議席率は 小選挙区（実績）＋ 比例（試算）の合計に占める割合。"""
    total = sum(smd.values()) + sum(pr.values())
    keys = set(shares) | set(smd) | set(pr)
    seat_share = {k: 100.0 * (smd.get(k, 0.0) + pr.get(k, 0)) / total for k in keys}
    return apportion.gallagher(shares, seat_share)


def disparity(electorate: Mapping[str, float], seats: Mapping[str, int]) -> tuple[float, str, str]:
    """1 議席当たり有権者数の 最大 ÷ 最小 と、その最大・最小の単位名。"""
    per = {k: electorate[k] / seats[k] for k in seats if seats[k] > 0}
    hi = max(per, key=lambda k: per[k])
    lo = min(per, key=lambda k: per[k])
    return per[hi] / per[lo], hi, lo


def judge_h4(ratio_before: float, ratio_after: float, thr_rise_pts: Sequence[float]) -> str:
    widened = ratio_after >= 1.1 * ratio_before
    thr = all(d >= 2.0 for d in thr_rise_pts)
    if widened and thr:
        return "整合"
    if not widened:
        return "不支持"
    return "中間"


def judge_h4b(max_ratio: float) -> str:
    return "整合" if max_ratio > 2.0 else "不支持"


def md_row(cells: Sequence[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


# ---- loaders -------------------------------------------------------------------------------------


def block_votes_of(pr: pl.DataFrame, election: int) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {b: {} for b in BLOCKS}
    for r in pr.filter(pl.col("election") == election).iter_rows(named=True):
        out[str(r["block"])][str(r["party"])] = float(r["votes"])
    return out


def official_block_seats(pr: pl.DataFrame, election: int) -> dict[str, int]:
    sub = pr.filter(pl.col("election") == election)
    sub = sub.group_by("block").agg(pl.col("block_seats").first())
    return {str(r["block"]): int(r["block_seats"]) for r in sub.iter_rows(named=True)}


def official_pr_seats(pr: pl.DataFrame, election: int) -> dict[str, int]:
    sub = pr.filter(pl.col("election") == election).group_by("party").agg(pl.col("seats").sum())
    return {str(r["party"]): int(r["seats"]) for r in sub.iter_rows(named=True)}


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_party_seats(
    results: Mapping[str, Mapping[str, int]], shares: Mapping[str, float], title: str, path: Path
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    parties = [p for p in sorted(shares, key=lambda p: -shares[p]) if shares[p] >= 1.0]
    labels = list(results)
    x = np.arange(len(parties))
    w = 0.8 / len(labels)
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    for i, lab in enumerate(labels):
        vals = [results[lab].get(p, 0) for p in parties]
        ax.bar(x + (i - (len(labels) - 1) / 2) * w, vals, width=w, color=SERIES[i], label=lab)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{p}\n{shares[p]:.1f}%" for p in parties], fontsize=6.5, rotation=15)
    ax.set_ylabel("比例代表の議席", fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    note = "出典: 総務省 衆議院議員総選挙 結果調（得票）から再計算。純ドント式、名簿不足は無視"
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_block_disparity(
    electorate: Mapping[str, float], seats_by: Mapping[str, Mapping[str, int]], path: Path
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    labels = list(seats_by)
    x = np.arange(len(BLOCKS))
    w = 0.8 / len(labels)
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    for i, lab in enumerate(labels):
        vals = [electorate[b] / seats_by[lab][b] / 1e4 for b in BLOCKS]
        ax.bar(x + (i - (len(labels) - 1) / 2) * w, vals, width=w, color=SERIES[i], label=lab)
    ax.set_xticks(x)
    first, last = labels[0], labels[-1]
    ax.set_xticklabels(
        [f"{b}\n{seats_by[first][b]}→{seats_by[last][b]}" for b in BLOCKS], fontsize=7
    )
    ax.set_ylabel("1 議席当たり有権者数（万人）", fontsize=8, color=INK)
    title = "比例ブロックの 1 議席当たり有権者数（第 51 回の有権者数、アダムズ方式で再配分）"
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    note = "出典: 総務省 結果調（有権者数）、国勢調査 2020（配分の人口）"
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- main ----------------------------------------------------------------------------------------


def _h3_for_election(
    election: int,
    pr: pl.DataFrame,
    win: pl.DataFrame,
    scen_seats: Mapping[str, Mapping[str, int]],
    fig_dir: Path,
) -> tuple[float, list[float], float]:
    """1 選挙分の表 2 を出力し、(ドント 131 の差, 修正サンラグの差 ×2, Gallagher 上昇) を返す。"""
    bv = block_votes_of(pr, election)
    shares = national_shares(bv)
    official = official_pr_seats(pr, election)
    smd = {
        str(r["party"]): float(r["smd_seats"])
        for r in win.filter(pl.col("election") == election).iter_rows(named=True)
    }
    results: dict[str, dict[str, int]] = {}
    for lab in PR_SCENARIOS:
        results[f"ドント {lab}"] = party_totals(allocate(bv, scen_seats[lab], "dhondt"))
    for lab in (S145, S131):
        results[f"修正サンラグ {lab}"] = party_totals(allocate(bv, scen_seats[lab], "msl"))
    base = results[f"ドント {CURRENT}"]
    print(
        f"\n## 表 2-{election - 49}: 第 {election} 回 — 政党別の比例議席"
        "（公式 = 名簿不足の移転込み、以下は純ドント／修正サンラグの機械的試算）"
    )
    cols = ["公式 176", *results]
    print(md_row(["政党", "得票率 %", *cols]))
    print("|---|---|" + "---|" * len(cols))
    for p in sorted(shares, key=lambda p: -shares[p]):
        cells = [official.get(p, 0)] + [results[c].get(p, 0) for c in results]
        print(md_row([p, f"{shares[p]:.2f}", *cells]))
    sums = [sum(official.values())] + [sum(results[c].values()) for c in results]
    print(md_row(["計", 100, *sums]))
    moved = sum(abs(official.get(p, 0) - base.get(p, 0)) for p in set(official) | set(base)) // 2
    print(f"- 公式と純ドントの差（名簿不足による移転）: {moved} 議席")
    print(md_row(["比較", "小政党（得票率 <10%）の議席減少率", "大政党の減少率", "差（pt）"]))
    print("|---|---|---|---|")
    d131 = 0.0
    d_msl: list[float] = []
    for lab in (f"ドント {S145}", f"ドント {S131}", f"修正サンラグ {S145}", f"修正サンラグ {S131}"):
        rs, rl, d = group_reduction(base, results[lab], shares)
        print(md_row([lab, f"{rs:.1f}%", f"{rl:.1f}%", f"{d:+.1f}"]))
        if lab == f"ドント {S131}":
            d131 = d
        if lab.startswith("修正サンラグ"):
            d_msl.append(d)
    g = {
        "公式": gallagher_chamber(shares, smd, official),
        "純ドント 176": gallagher_chamber(shares, smd, base),
        "145": gallagher_chamber(shares, smd, results[f"ドント {S145}"]),
        "131": gallagher_chamber(shares, smd, results[f"ドント {S131}"]),
        "修正サンラグ 131": gallagher_chamber(shares, smd, results[f"修正サンラグ {S131}"]),
    }
    rise = g["131"] - g["純ドント 176"]
    print(
        "- Gallagher 指数（小選挙区の実績 ＋ 比例）: "
        + "、".join(f"{k} {v:.2f}" for k, v in g.items())
        + f"（176 → 131 で {rise:+.2f}）"
    )
    fig_party_seats(
        {
            "現行 176（純ドント）": base,
            "45 減 131（ドント）": results[f"ドント {S131}"],
            "45 減 131（修正サンラグ）": results[f"修正サンラグ {S131}"],
        },
        shares,
        f"第 {election} 回衆院選の比例得票で定数を変えたときの政党別議席（機械的試算）",
        fig_dir / f"r2_party_seats_{election}.png",
    )
    return d131, d_msl, rise


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    fonts = ["Hiragino Sans", "Noto Sans CJK JP", "IPAPGothic", "IPAGothic", "sans-serif"]
    matplotlib.rcParams["font.family"] = fonts
    marts = args.data_dir / "marts"
    pr = pl.read_parquet(marts / "jp_hr_pr_results.parquet")
    el = pl.read_parquet(marts / "jp_hr_electorate.parquet")
    win = pl.read_parquet(marts / "jp_hr_seats_by_party.parquet")
    census = pl.read_parquet(marts / "jp_census2020_prefecture.parquet")
    el51 = el.filter(pl.col("election") == 51)
    block_of = {str(r["pref"]): str(r["block"]) for r in el51.iter_rows(named=True)}
    census_rows = list(census.iter_rows(named=True))
    pops = block_populations(census_rows, block_of)
    pref_pop = {str(r["pref"]): float(r["population_japanese"]) for r in census_rows}

    print("# R2 比例代表の削減は少数政党と地方ブロックに何をするか（H3・H4）（2026-10-27）")
    print(
        f"- mart: jp_hr_pr_results {pr.height} 行、jp_hr_electorate {el.height} 行、"
        f"jp_hr_seats_by_party {win.height} 行、jp_census2020_prefecture {census.height} 行"
    )

    # ---- 配分方式の検算 ----
    official_176 = official_block_seats(pr, 51)
    adams_176 = apportion.adams(pops, 176)
    diff176 = {
        b: (official_176[b], adams_176[b]) for b in BLOCKS if official_176[b] != adams_176[b]
    }
    verdict = "一致" if not diff176 else f"不一致 {diff176}"
    print(f"- 検算: アダムズ方式 × 2020 国勢調査 日本人人口 でブロック定数 176 を再現 → {verdict}")
    adams_289 = apportion.adams(pref_pop, SMD_CURRENT)
    n2 = sum(1 for v in adams_289.values() if v <= 2)
    print(
        f"- 検算: 同方式で小選挙区 289 を都道府県に配分 → 東京 {adams_289['東京都']}、"
        f"神奈川 {adams_289['神奈川県']}、大阪 {adams_289['大阪府']}、鳥取 {adams_289['鳥取県']}、"
        f"定数 2 の県 {n2}"
    )
    scen_seats: dict[str, dict[str, int]] = {
        lab: (dict(official_176) if n == 176 else apportion.adams(pops, n))
        for lab, n in PR_SCENARIOS.items()
    }
    print("\n## 表 1: ブロック定数（現行は法定、削減後はアダムズ方式 × 2020 国勢調査 日本人人口）")
    print(md_row(["ブロック", "日本人人口（千人）", *PR_SCENARIOS]))
    print("|---|---|" + "---|" * len(PR_SCENARIOS))
    for b in BLOCKS:
        print(md_row([b, f"{pops[b] / 1000:,.0f}", *(scen_seats[lab][b] for lab in PR_SCENARIOS)]))

    # ---- H3 ----
    diffs_131: list[float] = []
    diffs_msl: list[float] = []
    gall_rise: list[float] = []
    for election in (50, 51):
        d131, d_msl, rise = _h3_for_election(election, pr, win, scen_seats, args.fig_dir)
        diffs_131.append(d131)
        diffs_msl += d_msl
        gall_rise.append(rise)
    d131_txt = ", ".join(f"{d:+.1f}" for d in diffs_131)
    dmsl_txt = ", ".join(f"{d:+.1f}" for d in diffs_msl)
    gall_txt = ", ".join(f"{g:+.2f}" for g in gall_rise)
    h3c = "整合" if all(g >= 1.0 for g in gall_rise) else "不支持"
    print(f"\n- **H3 判定: {judge_h3(diffs_131)}**（差 = {d131_txt} pt）")
    print(f"- **H3b 判定: {judge_h3b(diffs_msl)}**（修正サンラグでの差 = {dmsl_txt} pt）")
    print(f"- **H3c 判定: {h3c}**（Gallagher の上昇 = {gall_txt} pt）")

    # ---- H4 ----
    electorate = dict.fromkeys(BLOCKS, 0.0)
    for r in el51.iter_rows(named=True):
        electorate[str(r["block"])] += float(r["electorate_pr"])
    print("\n## 表 3: ブロック間の 1 議席当たり有権者数（第 51 回）と小ブロックの参入閾値")
    print(md_row(["シナリオ", "最大（ブロック）", "最小（ブロック）", "最大 ÷ 最小"]))
    print("|---|---|---|---|")
    ratios: dict[str, float] = {}
    for lab in PR_SCENARIOS:
        ratio, hi, lo = disparity(electorate, scen_seats[lab])
        ratios[lab] = ratio
        hi_txt = f"{electorate[hi] / scen_seats[lab][hi]:,.0f}（{hi}）"
        lo_txt = f"{electorate[lo] / scen_seats[lab][lo]:,.0f}（{lo}）"
        print(md_row([lab, hi_txt, lo_txt, f"{ratio:.3f}"]))
    bv51 = block_votes_of(pr, 51)
    small_blocks = [b for b in BLOCKS if official_176[b] <= 10]
    print()
    print(
        md_row(
            [
                "ブロック",
                "定数（176 → 145 → 131）",
                "1 議席の最小得票率 %（176 / 145 / 131）",
                "上昇 pt（176 → 131）",
            ]
        )
    )
    print("|---|---|---|---|")
    rises: list[float] = []
    for b in small_blocks:
        thr = [
            apportion.threshold_share(bv51[b], scen_seats[lab][b], "__new__")
            for lab in PR_SCENARIOS
        ]
        rises.append(thr[2] - thr[0])
        seats_txt = " → ".join(str(scen_seats[lab][b]) for lab in PR_SCENARIOS)
        thr_txt = " / ".join(f"{t:.1f}" for t in thr)
        print(md_row([b, seats_txt, thr_txt, f"{thr[2] - thr[0]:+.1f}"]))
    h4 = judge_h4(ratios[CURRENT], ratios[S131], rises)
    print("\n- (a) 小選挙区の格差は比例のみの削減では不変（定義上）。")
    print(
        f"- (b) ブロック間格差 176 → 131: {ratios[CURRENT]:.3f} → {ratios[S131]:.3f}"
        f"（{ratios[S131] / ratios[CURRENT]:.2f} 倍）、145: {ratios[S145]:.3f}"
    )
    rises_txt = ", ".join(f"{r:+.1f}" for r in rises)
    print(f"- (c) 定数 10 以下のブロックの参入閾値の上昇: {rises_txt} pt")
    print(f"- **H4 判定: {h4}**")
    fig_block_disparity(electorate, scen_seats, args.fig_dir / "r2_block_disparity.png")

    # ---- H4b ----
    adams_260 = apportion.adams(pref_pop, SMD_REDUCED)
    n2_260 = sum(1 for v in adams_260.values() if v <= 2)
    print("\n## 表 4: 小選挙区を 289 → 260 にした場合（アダムズ方式、2020 国勢調査 日本人人口）")
    print(
        md_row(["定数", "定数 2 の県", "1 議席当たり人口 最大（県）", "最小（県）", "最大 ÷ 最小"])
    )
    print("|---|---|---|---|---|")
    r260 = 0.0
    for n, alloc, n2_ in ((SMD_CURRENT, adams_289, n2), (SMD_REDUCED, adams_260, n2_260)):
        ratio, hi, lo = disparity(pref_pop, alloc)
        if n == SMD_REDUCED:
            r260 = ratio
        hi_txt = f"{pref_pop[hi] / alloc[hi]:,.0f}（{hi}）"
        lo_txt = f"{pref_pop[lo] / alloc[lo]:,.0f}（{lo}）"
        print(md_row([n, n2_, hi_txt, lo_txt, f"{ratio:.3f}"]))
    changed = {p: (adams_289[p], adams_260[p]) for p in adams_289 if adams_289[p] != adams_260[p]}
    ordered = sorted(changed.items(), key=lambda kv: kv[1][0] - kv[1][1])
    print(f"- 減る県（{len(changed)}）: " + "、".join(f"{p} {a}→{b}" for p, (a, b) in ordered))
    print(
        f"- **H4b 判定: {judge_h4b(r260)}**"
        "（都道府県単位の最大格差。選挙区単位の格差は区割り次第でこれより大きい）"
    )
    print(
        f"\n図: {args.fig_dir}/r2_party_seats_50.png, r2_party_seats_51.png, r2_block_disparity.png"
    )


if __name__ == "__main__":
    main()
