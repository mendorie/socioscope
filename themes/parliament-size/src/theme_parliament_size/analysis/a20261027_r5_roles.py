"""R5: 「議員が少ない」国は「議員の仕事が広い」国か（H2 役割の範囲）。

事前登録（design/themes/parliament-size.md、2026-10-27）:
  H2: 人口当たり議員数が少ない国ほど、(a) 議員 1 人当たりの議会職員数が多く（Spearman ρ ≤ −0.3 で
      整合）、
      (b) 議員立法が成立法律に占める比率が低い（ρ ≥ +0.3 で整合）。どちらも |ρ| < 0.2 なら不支持。
      (b) の各国データ（議員立法の成立シェア）は IPU・ParlGov に無く本レポートでは取れない →
      判定不能とし、
      日本の時系列（内閣法制局）を記述する。

職員数は IPU Parline の permanent_staff_number（議院ごと。`is_staff_combined_parl` が真なら
両院合計の人数）。
補助指標: 本会議日数、常任委員会数、議員 1 人当たり議院予算（PPP）、議員の基本給（PPP）。
決定的スクリプト。純粋ヘルパは tests/test_analysis_r5.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
PEERS = ("USA", "DEU", "GBR", "FRA", "ITA", "KOR", "CAN", "ESP", "AUS")


# ---- pure helpers -------------------------------------------------------------------------------


def ranks(values: Sequence[float]) -> list[float]:
    """平均順位（同値は平均）。"""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = r
        i = j + 1
    return out


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    if n < 3:
        return math.nan
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return math.nan
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True)) / math.sqrt(sxx * syy)


def judge_h2a(rho: float) -> str:
    if math.isnan(rho):
        return "判定不能"
    if rho <= -0.3:
        return "整合"
    if abs(rho) < 0.2:
        return "不支持"
    return "中間"


def staff_per_member(
    chambers: Sequence[Mapping[str, object]],
) -> tuple[float, str] | None:
    """国の議院行（statutory_seats, permanent_staff, staff_combined_parl）→ (職員 ÷ 議員, 注記)。

    - 両院とも職員数がある: 合計 ÷ 両院定数。
    - 片方だけあり、その議院の staff_combined_parl が真: その人数 ÷ 両院定数（両院合計の職員数）。
    - 片方だけあり、偽: その人数 ÷ その議院の定数（議院単位）。
    """
    with_staff = [c for c in chambers if c.get("permanent_staff") is not None]
    if not with_staff:
        return None
    seats_all = sum(float(str(c["statutory_seats"])) for c in chambers)
    staff = sum(float(str(c["permanent_staff"])) for c in with_staff)
    if len(with_staff) == len(chambers):
        return staff / seats_all, "両院合計" if len(chambers) > 1 else "一院"
    c = with_staff[0]
    if c.get("staff_combined_parl") is True:
        return staff / seats_all, "両院合計（1 議院の申告）"
    return staff / float(str(c["statutory_seats"])), "1 議院のみ"


def md_row(cells: Sequence[object]) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_scatter(
    points: Mapping[str, tuple[float, float]], xlabel: str, ylabel: str, title: str, path: Path
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    for iso, (x, y) in points.items():
        col = SERIES[1] if iso == JP else (SERIES[0] if iso in PEERS else "#9bb0c9")
        ax.scatter(x, y, color=col, s=28 if iso == JP else 16, zorder=3)
        if iso == JP or iso in PEERS:
            ax.annotate(iso, (x, y), xytext=(4, 2), textcoords="offset points", fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel(xlabel, fontsize=8, color=INK)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    _style(ax)
    note = f"出典: IPU Parline（2026-10-27 取得、CC BY-NC-SA 4.0）。n = {len(points)}"
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_bills(rows: Sequence[Mapping[str, object]], path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    xs = [f"{r['session']}\n{str(r['start_date'])[:4]}" for r in rows]
    cab = [int(str(r["cabinet_enacted"])) for r in rows]
    mem = [int(str(r["member_enacted"])) for r in rows]
    ax.bar(xs, cab, color=SERIES[0], label="閣法（内閣提出）成立")
    ax.bar(xs, mem, bottom=cab, color=SERIES[1], label="議員立法 成立")
    ax.set_ylabel("成立法律数（会期ごと）", fontsize=8, color=INK)
    ax.set_title(
        "日本の成立法律: 閣法と議員立法（第 183〜221 回国会、2013–2026）",
        fontsize=10,
        color=INK,
        loc="left",
    )
    ax.tick_params(axis="x", labelsize=6)
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    note = (
        "出典: 内閣法制局「過去の法律案の提出・成立件数一覧」（継続審査分は外数、委員長提出を含む）"
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
    marts = args.data_dir / "marts"
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    bills = pl.read_parquet(marts / "jp_bill_counts.parquet")
    o = ipu.filter(pl.col("oecd_member"))

    per_m: dict[str, float] = {}
    spm: dict[str, tuple[float, str]] = {}
    extra: dict[str, dict[str, float | None]] = {}
    names: dict[str, str] = {}
    for iso3, grp in o.group_by("iso3"):
        iso = str(iso3[0])
        rows = list(grp.iter_rows(named=True))
        lower = next(r for r in rows if r["chamber_type"] == "lower")
        names[iso] = str(lower["country"])
        pop = float(lower["population_thousands"]) * 1000
        per_m[iso] = float(lower["statutory_seats"]) / (pop / 1e6)
        s = staff_per_member(rows)
        if s is not None:
            spm[iso] = s
        budget = [r["chamber_budget_ppp"] for r in rows]
        seats_all = sum(float(r["statutory_seats"]) for r in rows)
        extra[iso] = {
            "plenary_days": lower["plenary_days"],
            "committees": lower["committees"],
            "salary_ppp": lower["basic_salary_ppp"],
            "budget_ppp_per_member": (
                sum(float(b) for b in budget) / seats_all
                if all(b is not None for b in budget)
                else None
            ),
        }
    common = sorted(k for k in spm if k in per_m)
    rho = spearman([per_m[k] for k in common], [spm[k][0] for k in common])
    print("# R5 「議員が少ない」国は「議員の仕事が広い」国か（H2）（2026-10-27）")
    print(
        f"- mart: ipu_parliaments（OECD {o['iso3'].n_unique()} か国、職員数あり {len(common)}）、"
        f"jp_bill_counts {bills.height} 回次"
    )
    print("\n## 表 1: 人口当たり議員数と 議員 1 人当たり議会職員数（OECD）")
    print(
        md_row(
            [
                "国",
                "下院 /100 万人",
                "職員 ÷ 議員",
                "計算",
                "本会議日数（下院）",
                "常任委員会数（下院）",
                "議員 1 人当たり議院予算 PPP ドル",
                "基本給 PPP ドル",
            ]
        )
    )
    print("|---|---|---|---|---|---|---|---|")
    for k in sorted(common, key=lambda k: per_m[k]):
        e = extra[k]
        mark = "**" if k == JP else ""
        cells = [
            f"{mark}{names[k]}{mark}",
            f"{per_m[k]:.2f}",
            f"{spm[k][0]:.2f}",
            spm[k][1],
            f"{e['plenary_days']:.0f}" if e["plenary_days"] is not None else "–",
            f"{e['committees']:.0f}" if e["committees"] is not None else "–",
            f"{e['budget_ppp_per_member']:,.0f}" if e["budget_ppp_per_member"] is not None else "–",
            f"{e['salary_ppp']:,.0f}" if e["salary_ppp"] is not None else "–",
        ]
        print(md_row(cells))
    jp_rank_spm = 1 + sum(1 for k in common if spm[k][0] < spm[JP][0])
    med_spm = sorted(v[0] for v in spm.values())[len(spm) // 2]
    print(
        f"\n- 日本: 下院 {per_m[JP]:.2f} 人/100 万人、職員 ÷ 議員 {spm[JP][0]:.2f}（{spm[JP][1]}、"
        f"{len(common)} か国中 少ない方から {jp_rank_spm} 位、中央値 {med_spm:.2f}）"
    )
    print(f"- Spearman ρ（人口当たり議員数 × 職員 ÷ 議員）= {rho:.2f}（n = {len(common)}）")
    print(f"- **H2 (a) 判定: {judge_h2a(rho)}**（ρ ≤ −0.3 で整合、|ρ| < 0.2 で不支持）")
    # 補助: 人口当たり議員数と他の役割指標
    for key, label in (
        ("plenary_days", "本会議日数"),
        ("committees", "常任委員会数"),
        ("budget_ppp_per_member", "議員 1 人当たり議院予算 PPP"),
        ("salary_ppp", "基本給 PPP"),
    ):
        ks = [k for k in per_m if extra[k][key] is not None]
        rho_x = spearman([per_m[k] for k in ks], [float(str(extra[k][key])) for k in ks])
        jv = extra[JP][key]
        jtxt = f"{float(str(jv)):,.0f}" if jv is not None else "–"
        rank = (
            1 + sum(1 for k in ks if float(str(extra[k][key])) < float(str(jv)))
            if jv is not None
            else None
        )
        print(
            f"- 補助: {label} × 人口当たり議員数 ρ = {rho_x:.2f}（n = {len(ks)}）。"
            f"日本 {jtxt}（少ない方から {rank} 位）"
        )

    # 日本の議員立法シェア
    print("\n## 表 2: 日本の法律案の提出・成立（内閣法制局、第 183〜221 回）")
    tot = bills.select(
        pl.col("cabinet_submitted").sum(),
        pl.col("cabinet_enacted").sum(),
        pl.col("member_submitted").sum(),
        pl.col("member_enacted").sum(),
    ).row(0)
    cs, ce, ms, me = (int(v) for v in tot)
    print(md_row(["区分", "提出", "成立", "成立率", "成立法律に占める比率"]))
    print("|---|---|---|---|---|")
    print(
        md_row(
            ["閣法（内閣提出）", cs, ce, f"{100 * ce / cs:.1f}%", f"{100 * ce / (ce + me):.1f}%"]
        )
    )
    print(
        md_row(
            [
                "議員立法（衆法＋参法、委員長提出を含む）",
                ms,
                me,
                f"{100 * me / ms:.1f}%",
                f"{100 * me / (ce + me):.1f}%",
            ]
        )
    )
    by_year = (
        bills.group_by("year")
        .agg(pl.col("cabinet_enacted").sum(), pl.col("member_enacted").sum())
        .sort("year")
    )
    print("\n| 年 | 閣法 成立 | 議員立法 成立 | 議員立法の比率 |")
    print("|---|---|---|---|")
    for r in by_year.iter_rows(named=True):
        c, m = int(r["cabinet_enacted"]), int(r["member_enacted"])
        share = f"{100 * m / (c + m):.0f}%" if c + m else "–"
        print(md_row([r["year"], c, m, share]))
    print(
        "\n- **H2 (b) 判定: 判定不能**（各国の議員立法シェアを持つ構造化ソースが無い。"
        f"日本は成立法律の {100 * me / (ce + me):.0f}% が議員立法、"
        f"閣法の成立率 {100 * ce / cs:.0f}% "
        f"に対し議員立法は {100 * me / ms:.0f}%）"
    )

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    fig_scatter(
        {k: (per_m[k], spm[k][0]) for k in common},
        "人口 100 万人当たりの下院議員数（対数軸）",
        "議会職員数 ÷ 議員定数",
        "議員が少ない国ほど議員 1 人当たりの職員は多いか（OECD）",
        args.fig_dir / "r5_staff_vs_members.png",
    )
    fig_bills(list(bills.sort("session").iter_rows(named=True)), args.fig_dir / "r5_jp_bills.png")
    print(f"\n図: {args.fig_dir}/r5_staff_vs_members.png, r5_jp_bills.png")


if __name__ == "__main__":
    main()
