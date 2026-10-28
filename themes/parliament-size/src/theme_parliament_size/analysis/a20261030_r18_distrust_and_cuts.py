"""R18（番外編）: 議員への不信は海外でも定数削減の推進力か（H17a〜c、ユーザー提起）。

事後追加の仮説（design/themes/parliament-size.md「事後追加（2026-10-30 夜、番外編 R18）」、
結果の計算前に固定）:
  H17a: 2000 年以降に下院定数の削減が提案・実現した国と無い国で、立法府への信頼（最新年）の
        中央値を比較。提案あり群が 5 pt 以上低ければ整合、±5 pt 以内で不支持、5 pt 以上高ければ逆。
  H17b: 表向きの理由が「不信」「費用」を含む提案と、それ以外の提案の実現（施行）率。記述。
  H17c: 2021〜2023 年に削減が施行された国（イタリア）の信頼の変化（2021 → 2023）が、
        同じ 2 時点がある他国の変化の中央値を 5 pt 以上上回れば整合、±5 pt で不支持、下回れば逆。

決定的スクリプト。入力は src/theme_parliament_size/seat_reduction_proposals.csv
（手入力、出典列あり）と data/marts/{oecd_gov_trust, ipu_parliaments}.parquet。
純粋ヘルパは tests/test_analysis_r18.py で検証する。
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row
from theme_parliament_size.analysis.a20261030_r17_system_oversight_trust import latest, median

THEME_DIR = Path(__file__).resolve().parents[3]
PROPOSALS_CSV = THEME_DIR / "src" / "theme_parliament_size" / "seat_reduction_proposals.csv"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
SINCE = 2000
ENACTED = "enacted"  # 施行された（repealed は成立後に撤回、proposed は未成立）


# ---- pure helpers -------------------------------------------------------------------------------


def is_distrust_or_cost(reason: str) -> bool:
    return "不信" in reason or "費用" in reason


def enacted_rate(rows: Sequence[Mapping[str, str]]) -> tuple[int, int]:
    """(施行された件数, 件数)。"""
    return sum(1 for r in rows if r["status"] == ENACTED), len(rows)


def judge_h17a(diff_pt: float) -> str:
    """提案あり群の中央値 − 提案なし群の中央値（pt）。"""
    if math.isnan(diff_pt):
        return "判定不能"
    if diff_pt <= -5:
        return "整合（不信が高い国ほど提案）"
    if diff_pt >= 5:
        return "逆（信頼が高い国ほど提案）"
    return "不支持（無関係）"


def judge_h17c(diff_pt: float) -> str:
    """削減国の信頼の変化 − 他国の変化の中央値（pt）。"""
    if math.isnan(diff_pt):
        return "判定不能"
    if diff_pt >= 5:
        return "整合（削減後に信頼が回復）"
    if diff_pt <= -5:
        return "逆（削減後に信頼が低下）"
    return "不支持"


# ---- figure --------------------------------------------------------------------------------------


def fig_strip(
    trust: Mapping[str, float],
    proposed: set[str],
    enacted: set[str],
    names: Mapping[str, str],
    path: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    groups = [
        ("提案なし", [k for k in trust if k not in proposed]),
        ("提案あり", sorted(proposed & set(trust))),
    ]
    for gi, (_label, ks) in enumerate(groups):
        ks = sorted(ks, key=lambda k: trust[k])
        for i, k in enumerate(ks):
            color = SERIES[1] if k == JP else (SERIES[2] if k in enacted else "#7f9cc4")
            x = gi + (-0.22 + 0.11 * (i % 5))  # 横に散らして重なりを減らす
            ax.scatter(x, trust[k], s=36, color=color, zorder=3)
            ax.annotate(
                k,
                (x, trust[k]),
                fontsize=6.5,
                color=INK,
                xytext=(5, -2),
                textcoords="offset points",
            )
        med = median([trust[k] for k in ks])
        ax.hlines(med, gi - 0.3, gi + 0.3, color=INK, linewidth=1.2)
        ax.text(gi + 0.33, med, f"中央値 {med:.1f}", fontsize=7.5, va="center", color=INK)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"{g[0]}（{len(g[1])}）" for g in groups], fontsize=9)
    ax.set_xlim(-0.5, 1.9)
    ax.set_ylabel("立法府を信頼する人の割合（%、最新年）", fontsize=8, color=INK)
    ax.set_title(
        "2000 年以降に下院定数の削減が提案された国と、立法府への信頼",
        fontsize=10,
        color=INK,
        loc="left",
    )
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    fig.text(
        0.01,
        0.005,
        "出典: OECD Trust Survey 2023、各国の提案は手入力表（出典列あり）。緑 = 施行、橙 = 日本",
        fontsize=7,
        color=MUTED,
    )
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
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    trust_df = pl.read_parquet(marts / "oecd_gov_trust.parquet")
    lower = ipu.filter(pl.col("oecd_member") & (pl.col("chamber_type") == "lower"))
    names = {str(r["iso3"]): str(r["country"]) for r in lower.iter_rows(named=True)}
    with PROPOSALS_CSV.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if int(r["year"]) >= SINCE]
    proposed = {r["iso3"] for r in rows}
    enacted = {r["iso3"] for r in rows if r["status"] == ENACTED}
    by_year: dict[str, dict[int, float]] = {}
    for r in trust_df.filter(pl.col("metric") == "trust_legislature_pct").iter_rows(named=True):
        if str(r["iso3"]) in names:
            by_year.setdefault(str(r["iso3"]), {})[int(r["year"])] = float(r["value"])
    trust = {
        k: v[1]
        for k in by_year
        if (v := latest([{"year": y, "value": x} for y, x in by_year[k].items()]))
    }

    print("# R18（番外編）議員への不信は海外でも定数削減の推進力か（H17a〜c）（2026-10-30）")
    print(
        "\n事後追加の仮説（設計書 2026-10-30 夜 節）。手入力表の記述と中央値の比較のみ。"
        "因果の主張はない。"
    )
    print(
        f"\n## 表 1: OECD 38 か国の下院定数削減の提案・実現（{SINCE} 年以降、手入力・出典列あり）"
    )
    print(md_row(["国", "年", "状態", "定数", "提案主体", "表向きの理由", "備考"]))
    print("|" + "---|" * 7)
    status_ja = {"enacted": "施行", "repealed": "成立後に撤回", "proposed": "未成立"}
    for r in sorted(rows, key=lambda r: (int(r["year"]), r["iso3"])):
        mark = "**" if r["iso3"] == JP else ""
        print(
            md_row(
                [
                    f"{mark}{names.get(r['iso3'], r['country'])}{mark}",
                    r["year"],
                    status_ja[r["status"]],
                    f"{r['from_seats']} → {r['to_seats']}",
                    r["proposer"],
                    r["reason"],
                    r["note"],
                ]
            )
        )
    print(
        f"\n- 提案または実現があった国: {len(proposed)}（施行 {len(enacted)}: "
        + "、".join(names[k] for k in sorted(enacted))
        + "）。無い国: "
        + "、".join(names[k] for k in sorted(set(names) - proposed))
    )

    # ---- H17a
    with_p = sorted(k for k in trust if k in proposed)
    without = sorted(k for k in trust if k not in proposed)
    med_p, med_n = median([trust[k] for k in with_p]), median([trust[k] for k in without])
    diff = med_p - med_n
    print("\n## H17a: 不信が高い国ほど削減が提案されるか")
    print(md_row(["群", "n（信頼あり）", "信頼の中央値 %", "国（信頼の低い順）"]))
    print("|" + "---|" * 4)
    for label, ks in (("提案あり", with_p), ("提案なし", without)):
        print(
            md_row(
                [
                    label,
                    len(ks),
                    f"{median([trust[k] for k in ks]):.1f}",
                    "、".join(
                        f"{names[k]} {trust[k]:.0f}" for k in sorted(ks, key=lambda k: trust[k])
                    ),
                ]
            )
        )
    print(
        f"\n- 中央値の差（提案あり − なし）= {diff:+.1f} pt → **H17a {judge_h17a(diff)}**"
        "（−5 pt 以下で整合）"
    )
    med_e = median([trust[k] for k in with_p if k in enacted])
    rest = [k for k in trust if k not in enacted]
    formal = {r["iso3"] for r in rows if r["formal"] == "1"}
    with_f = sorted(k for k in trust if k in formal)
    without_f = sorted(k for k in trust if k not in formal)
    med_f, med_nf = median([trust[k] for k in with_f]), median([trust[k] for k in without_f])
    print(
        f"- 参考: 施行した国だけ（n = {len([k for k in with_p if k in enacted])}）の中央値 "
        f"{med_e:.1f}%。"
        f"日本 {trust[JP]:.1f}%（{max(by_year[JP])} 年）"
    )
    med_rest = median([trust[k] for k in rest])
    med_no_jp = median([trust[k] for k in with_p if k != JP])
    n_en = len([k for k in with_p if k in enacted])
    d_en = med_e - med_rest
    print(
        f"- 頑健性: 施行国 {n_en} か国 vs それ以外 {len(rest)} か国"
        f"の中央値 {med_e:.1f}% vs {med_rest:.1f}%（差 {d_en:+.1f} pt、"
        f"{judge_h17a(d_en)}）。日本を除く提案あり群の中央値 {med_no_jp:.1f}%。"
        f"法案提出・国民投票・成立法律に限る（formal = 1、{len(with_f)} か国）と "
        f"{med_f:.1f}% vs {med_nf:.1f}%（差 {med_f - med_nf:+.1f} pt、"
        f"{judge_h17a(med_f - med_nf)}）"
    )

    # ---- H17b
    print("\n## H17b: 不信・費用を理由にした提案は実現したか")
    a = [r for r in rows if is_distrust_or_cost(r["reason"])]
    b = [r for r in rows if not is_distrust_or_cost(r["reason"])]
    print(md_row(["理由", "提案数", "施行", "成立後に撤回", "未成立", "施行率"]))
    print("|" + "---|" * 6)
    for label, rs in (("不信・費用を含む", a), ("効率・制度改革のみ", b), ("全体", rows)):
        e, n = enacted_rate(rs)
        rep = sum(1 for r in rs if r["status"] == "repealed")
        print(md_row([label, n, e, rep, n - e - rep, f"{100 * e / n:.0f}%"]))
    print(
        "\n- 施行された削減の理由: "
        + "、".join(f"{names[r['iso3']]}（{r['reason']}）" for r in rows if r["status"] == ENACTED)
    )

    # ---- H17c
    print("\n## H17c: 削減の後に信頼は回復したか（2021 → 2023）")
    both = {k: v for k, v in by_year.items() if 2021 in v and 2023 in v}
    delta = {k: v[2023] - v[2021] for k, v in both.items()}
    others = [d for k, d in delta.items() if k != "ITA"]
    med_o = median(others)
    print(md_row(["国", "2021", "2023", "変化 pt"]))
    print("|" + "---|" * 4)
    for k in sorted(delta, key=lambda k: -delta[k]):
        mark = "**" if k == "ITA" else ""
        print(
            md_row(
                [
                    f"{mark}{names[k]}{mark}",
                    f"{both[k][2021]:.1f}",
                    f"{both[k][2023]:.1f}",
                    f"{delta[k]:+.1f}",
                ]
            )
        )
    if "ITA" in delta:
        d_it = delta["ITA"] - med_o
        print(
            f"\n- イタリア（2022 年に 630 → 400 施行）の変化 {delta['ITA']:+.1f} pt、"
            f"他 {len(others)} か国の中央値 {med_o:+.1f} pt、差 {d_it:+.1f} pt → "
            f"**H17c {judge_h17c(d_it)}**（+5 pt 以上で整合。n = 1）"
        )
    else:
        print(
            f"\n- イタリアは OECD 調査に 2023 年しか無く（2021 年の値なし）、変化を計算できない → "
            f"**H17c {judge_h17c(math.nan)}**。他 {len(others)} か国の変化の中央値は "
            f"{med_o:+.1f} pt（2023 年のイタリアの信頼は {trust['ITA']:.1f}%）"
        )
    fig_strip(trust, proposed, enacted, names, args.fig_dir / "r18_trust_by_proposal.png")
    print(f"\n図: {args.fig_dir}/r18_trust_by_proposal.png")


if __name__ == "__main__":
    main()
