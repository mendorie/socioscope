"""R3: 定数削減で浮く国費はどれだけか（H5・H5b）。

事前登録（design/themes/parliament-size.md、2026-10-27）:
  H5  : 議員 1 人当たりの直接経費（歳費・期末手当・調査研究広報滞在費・立法事務費・公設秘書 3 人分の
        給与）× 45 は、国会所管歳出の 5% 未満、国の一般会計歳出の 0.01% 未満なら整合。
        一般会計比が 0.05% 以上なら不支持。
  H5b : 議会費の対 GDP 比・人口 1 人当たりで、日本は OECD 中位以下なら整合。
        （本スクリプトでは IPU の「議会予算 ÷ 政府予算 %」と「議院予算（PPP）÷ 人口」を使う。
        事後の具体化）

入力: data/marts/{jp_budget_by_organ, ipu_parliaments}.parquet、
src/theme_parliament_size/jp_member_costs.csv（法定額を手入力、出典は CSV の source 列）。
決定的スクリプト。純粋ヘルパは tests/test_analysis_r3.py で検証する。
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

THEME_DIR = Path(__file__).resolve().parents[3]
COSTS_CSV = Path(__file__).resolve().parents[1] / "jp_member_costs.csv"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
JP_POP = 124_371_000  # IPU 2023
CUTS = {"比例 45 減": 45, "比例 31 減": 31}
BASIS = {
    "歳費＋期末手当": "歳費法 1 条 月額 1,294,000 円 × 12 ＋ 期末手当（IPU basic_salary 2025）",
    "調査研究広報滞在費": "歳費法 9 条 月額 1,000,000 円 × 12",
    "立法事務費": "立法事務費交付法 3 条 議員 1 人月額 650,000 円 × 12（会派に交付）",
    "公設秘書 3 人の給与": (
        "秘書給与法 別表第二 一級一号給 288,800 円〜別表第一 三級四号給 556,900 円"
        " × (12 ＋ 4.6) か月 × 3 人"
    ),
}


# ---- pure helpers -------------------------------------------------------------------------------


def load_costs(path: Path = COSTS_CSV) -> dict[str, float]:
    with path.open(encoding="utf-8") as f:
        return {row["item"]: float(row["amount_yen"]) for row in csv.DictReader(f)}


def per_member_cost(costs: Mapping[str, float]) -> dict[str, tuple[float, float]]:
    """議員 1 人当たり年間の直接経費（円）: 項目 → (下限, 上限)。秘書給与だけ別表で幅を持つ。"""
    salary = costs["歳費・期末手当 年額（IPU basic_salary）"]
    allowance = costs["調査研究広報滞在費"] * 12
    legis = costs["立法事務費（会派交付、議員 1 人当たり）"] * 12
    n_sec = costs["公設秘書 人数"]
    months = 12 + costs["公設秘書 期末・勤勉手当 年間月数（一般職の例、仮定）"]
    lo_key = "公設秘書 給料月額 下限（公設第一・第二秘書、別表第二 一級一号給）"
    hi_key = "公設秘書 給料月額 上限（政策担当秘書、別表第一 三級四号給）"
    sec_lo = costs[lo_key] * months * n_sec
    sec_hi = costs[hi_key] * months * n_sec
    return {
        "歳費＋期末手当": (salary, salary),
        "調査研究広報滞在費": (allowance, allowance),
        "立法事務費": (legis, legis),
        "公設秘書 3 人の給与": (sec_lo, sec_hi),
    }


def totals(items: Mapping[str, tuple[float, float]]) -> tuple[float, float]:
    return sum(v[0] for v in items.values()), sum(v[1] for v in items.values())


def saving_share(per_member_yen: float, cut: int, denominator_yen: float) -> float:
    """削減人数 × 1 人当たり経費 ÷ 分母（%）。"""
    return 100.0 * per_member_yen * cut / denominator_yen


def judge_h5(share_diet_pct: float, share_budget_pct: float) -> str:
    if share_diet_pct < 5.0 and share_budget_pct < 0.01:
        return "整合"
    if share_budget_pct >= 0.05:
        return "不支持"
    return "中間"


def rank_of(values: Mapping[str, float], iso3: str) -> int:
    v = values[iso3]
    return 1 + sum(1 for k, x in values.items() if k != iso3 and x < v)


def judge_h5b(rank: int, n: int) -> str:
    """少ない方から数えて中央値以下（rank ≤ ceil(n/2)）なら整合。"""
    return "整合" if rank <= (n + 1) // 2 else "不支持"


def md_row(cells: Sequence[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_bars(
    values: Mapping[str, float], names: Mapping[str, str], title: str, xlabel: str, path: Path
) -> None:
    import matplotlib.pyplot as plt

    order = sorted(values, key=lambda k: values[k])
    fig, ax = plt.subplots(figsize=(7.2, 0.22 * len(order) + 1.6))
    colors = [SERIES[1] if k == JP else "#b8c6d9" for k in order]
    ax.barh([names[k] for k in order], [values[k] for k in order], color=colors)
    for i, k in enumerate(order):
        txt = f" {values[k]:.3f}" if values[k] < 1 else f" {values[k]:.1f}"
        ax.text(values[k], i, txt, va="center", fontsize=7, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_xlabel(xlabel, fontsize=8, color=INK)
    ax.invert_yaxis()
    _style(ax)
    note = f"出典: IPU Parline（2026-10-27 取得、CC BY-NC-SA 4.0）。n = {len(order)}"
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
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
    marts = args.data_dir / "marts"
    budget = pl.read_parquet(marts / "jp_budget_by_organ.parquet").filter(pl.col("fy") == 2025)
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    costs = load_costs()
    items = per_member_cost(costs)
    lo, hi = totals(items)
    diet = float(budget.filter(pl.col("organ") == "国会")["amount_100m_jpy"][0]) * 1e8
    total = float(budget.filter(pl.col("organ") == "合計")["amount_100m_jpy"][0]) * 1e8
    jp = ipu.filter(pl.col("iso3") == JP)
    hr = float(jp.filter(pl.col("chamber_type") == "lower")["chamber_budget"][0])
    hc = float(jp.filter(pl.col("chamber_type") == "upper")["chamber_budget"][0])

    print("# R3 定数削減で浮く国費はどれだけか（H5・H5b）（2026-10-27）")
    print(
        "- mart: jp_budget_by_organ（FY2025 修正後）、ipu_parliaments。"
        "法定額: src/theme_parliament_size/jp_member_costs.csv"
    )
    print(
        f"- 一般会計歳出 {total / 1e12:,.1f} 兆円、国会所管 {diet / 1e8:,.0f} 億円"
        f"（{100 * diet / total:.3f}%）。IPU の議院予算（2025）: "
        f"衆議院 {hr / 1e8:,.0f} 億円、参議院 {hc / 1e8:,.0f} 億円"
    )
    print("\n## 表 1: 議員 1 人当たりの年間直接経費（法定額から積み上げ、円）")
    print(md_row(["項目", "下限", "上限", "根拠"]))
    print("|---|---|---|---|")
    for k, (a, b) in items.items():
        print(md_row([k, f"{a:,.0f}", f"{b:,.0f}", BASIS[k]]))
    print(md_row(["**計**", f"**{lo:,.0f}**", f"**{hi:,.0f}**", ""]))

    print("\n## 表 2: 削減で浮く直接経費と、その分母に対する比率")
    print(
        md_row(
            [
                "削減",
                "年間節約額（下限〜上限、億円）",
                "国会所管歳出比",
                "一般会計歳出比",
                "衆参の議院予算比",
            ]
        )
    )
    print("|---|---|---|---|---|")
    verdict = ""
    for label, cut in CUTS.items():
        sh_diet = (saving_share(lo, cut, diet), saving_share(hi, cut, diet))
        sh_total = (saving_share(lo, cut, total), saving_share(hi, cut, total))
        sh_ch = (saving_share(lo, cut, hr + hc), saving_share(hi, cut, hr + hc))
        cells = [
            f"{label}（{cut} 人）",
            f"{lo * cut / 1e8:.1f}〜{hi * cut / 1e8:.1f}",
            f"{sh_diet[0]:.2f}〜{sh_diet[1]:.2f}%",
            f"{sh_total[0]:.4f}〜{sh_total[1]:.4f}%",
            f"{sh_ch[0]:.2f}〜{sh_ch[1]:.2f}%",
        ]
        print(md_row(cells))
        if cut == 45:
            verdict = judge_h5(sh_diet[1], sh_total[1])
    d45, b45 = saving_share(hi, 45, diet), saving_share(hi, 45, total)
    print(
        f"\n- **H5 判定: {verdict}**（45 減・上限で 国会所管比 {d45:.2f}%、一般会計比 {b45:.4f}%）"
    )
    print(
        f"- 参考: 国民 1 人当たりの節約額（上限）= {hi * 45 / JP_POP:,.0f} 円/年。"
        "議員会館・事務局・委員会運営費は議員数に比例しないため、ここには含めない（固定費）。"
    )

    # ---- H5b ----
    o = ipu.filter(pl.col("oecd_member") & pl.col("chamber_type").eq("lower"))
    names = {str(r["iso3"]): str(r["country"]) for r in o.iter_rows(named=True)}
    pct = {
        str(r["iso3"]): float(r["parliament_budget_pct_gov"])
        for r in o.iter_rows(named=True)
        if r["parliament_budget_pct_gov"] is not None
    }
    # 議院予算 PPP ÷ 人口（両院合計。片方の議院に PPP が無い国は除く）
    ppp: dict[str, float] = {}
    for iso3, grp in ipu.filter(pl.col("oecd_member")).group_by("iso3"):
        vals = grp["chamber_budget_ppp"].to_list()
        if any(v is None for v in vals):
            continue
        pop = float(grp["population_thousands"][0]) * 1000
        ppp[str(iso3[0])] = sum(float(v) for v in vals) / pop
    r_pct, n_pct = rank_of(pct, JP), len(pct)
    r_ppp, n_ppp = rank_of(ppp, JP), len(ppp)
    med_pct = sorted(pct.values())[n_pct // 2]
    med_ppp = sorted(ppp.values())[n_ppp // 2]
    print("\n## 表 3: 国際比較（IPU Parline）")
    print(
        f"- 議会予算 ÷ 政府予算（%）: 日本 {pct[JP]:.3f}%、OECD {n_pct} か国中 少ない方から "
        f"{r_pct} 位（中央値 {med_pct:.3f}%）"
    )
    print(
        f"- 両院の予算（PPP ドル）÷ 人口: 日本 {ppp[JP]:.2f} ドル/人、両院とも PPP 値のある "
        f"OECD {n_ppp} か国中 少ない方から {r_ppp} 位（中央値 {med_ppp:.2f}）"
    )
    print(md_row(["順位", "国", "議会予算 ÷ 政府予算 %"]))
    print("|---|---|---|")
    for i, k in enumerate(sorted(pct, key=lambda k: pct[k]), start=1):
        mark = "**" if k == JP else ""
        print(md_row([i, f"{mark}{names[k]}{mark}", f"{pct[k]:.3f}"]))
    h5b_pct, h5b_ppp = judge_h5b(r_pct, n_pct), judge_h5b(r_ppp, n_ppp)
    print(
        f"\n- **H5b 判定: {h5b_pct}**（対政府予算比の順位 {r_pct}/{n_pct}。"
        f"PPP 人口当たりでは {h5b_ppp}（{r_ppp}/{n_ppp}）。対 GDP 比は IPU に無く未計算）"
    )

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    fig_bars(
        pct,
        names,
        "議会予算 ÷ 政府予算（%、OECD、IPU Parline）",
        "議会予算の政府予算に占める割合（%）",
        args.fig_dir / "r3_budget_share.png",
    )
    fig_bars(
        ppp,
        names,
        "両院の予算（PPP ドル）÷ 人口（OECD、両院とも PPP 値のある国）",
        "1 人当たり議会予算（PPP ドル）",
        args.fig_dir / "r3_budget_per_capita.png",
    )
    print(f"\n図: {args.fig_dir}/r3_budget_share.png, r3_budget_per_capita.png")


if __name__ == "__main__":
    main()
