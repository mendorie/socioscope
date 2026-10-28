"""R7: 役割指標の補強（質問主意書・政府入り議員）と議会費の対 GDP 比。

事後追加の仮説 H2c・H5c（design/themes/parliament-size.md「事後追加の仮説（2026-10-28）」、結果の
計算前に固定）:
  H2c : IPU の質問主意書数（num_written_question_ask、年）÷ 下院定数 と人口 100 万人当たり下院
        議員数の Spearman ρ ≤ −0.3 なら H2 (a) と同じ向きで整合、|ρ| < 0.2 なら不支持。政府に
        入っている議員の比率（members_government_percentage）と調査権（is_carry_out_inquiries）は
        探索的に記述する。
  H5c : IPU の議院予算（現地通貨、両院合計、予算年）÷ WDI 名目 GDP（現地通貨、同年）で、日本が
        OECD 内で少ない方から中央値以下（rank ≤ ceil(n/2)）なら整合（H5b と同じ規則）。両院の
        予算が揃わない国、予算の通貨が国の通貨と一致しない国は除く。

決定的スクリプト。入力は data/marts/{ipu_parliaments, wdi_gdp_lcu}.parquet と
data/staged/ipu/country_attributes.parquet（local_currency）。R5 の spearman／judge_h2a、R3 の
rank_of／judge_h5b を再利用し、R7 固有のヘルパは tests/test_analysis_r7.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from theme_parliament_size.analysis.a20261027_r3_cost import judge_h5b, md_row, rank_of
from theme_parliament_size.analysis.a20261027_r5_roles import judge_h2a, spearman

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"


# ---- pure helpers -------------------------------------------------------------------------------


def budget_to_gdp(
    chambers: Sequence[Mapping[str, object]],
    gdp: Mapping[tuple[str, int], float],
    local_currency: str,
) -> tuple[float, int, str] | None:
    """国の議院行 → (両院予算 ÷ GDP %, 予算年, 注記)。

    - すべての議院に予算（現地通貨）があり、通貨が国の通貨と一致し、予算年の GDP があるときだけ
      値を返す。
    - 両院で予算年が違うときは各議院の予算年の GDP で割った比率を足す（年ずれを注記）。
    - 1 議院だけに値があり、その議院が「両院合計」と申告していればそれを使う。
    """
    iso3 = str(chambers[0]["iso3"])
    with_budget = [c for c in chambers if c.get("chamber_budget") is not None]
    if not with_budget:
        return None
    if any(str(c.get("budget_currency") or "") != local_currency for c in with_budget):
        return None
    if len(with_budget) < len(chambers) and not (
        len(with_budget) == 1 and with_budget[0].get("budget_combined_parl") is True
    ):
        return None
    total = 0.0
    years: list[int] = []
    for c in with_budget:
        year = int(str(c["budget_year"]))
        g = gdp.get((iso3, year))
        if g is None:
            return None
        total += 100.0 * float(str(c["chamber_budget"])) / g
        years.append(year)
    note = "両院合計" if len(chambers) > 1 else "一院"
    if len(set(years)) > 1:
        note += f"（予算年 {min(years)}／{max(years)}）"
    if len(with_budget) == 1 and len(chambers) > 1:
        note = "両院合計（1 議院の申告）"
    return total, max(years), note


def per_member(value: object, seats: object) -> float | None:
    if value is None or seats is None or float(str(seats)) <= 0:
        return None
    return float(str(value)) / float(str(seats))


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: Any, grid_axis: str = "y") -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_scatter(
    xs: Mapping[str, float], ys: Mapping[str, float], title: str, ylabel: str, path: Path
) -> None:
    import matplotlib.pyplot as plt

    keys = sorted(k for k in xs if k in ys)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.scatter(
        [xs[k] for k in keys],
        [ys[k] for k in keys],
        s=22,
        color=[SERIES[1] if k == JP else "#7f9cc4" for k in keys],
    )
    for k in keys:
        ax.annotate(
            k, (xs[k], ys[k]), fontsize=6.5, color=INK, xytext=(3, 2), textcoords="offset points"
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("人口 100 万人当たり下院議員数（対数軸）", fontsize=8, color=INK)
    ax.set_ylabel(ylabel, fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    _style(ax)
    note = f"出典: IPU Parline（2026-10-28 取得、CC BY-NC-SA 4.0）。n = {len(keys)}。両軸は対数"
    fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_bars(values: Mapping[str, float], names: Mapping[str, str], title: str, path: Path) -> None:
    import matplotlib.pyplot as plt

    order = sorted(values, key=lambda k: values[k])
    fig, ax = plt.subplots(figsize=(7.2, 0.24 * len(order) + 1.6))
    ax.barh(
        [names[k] for k in order],
        [values[k] for k in order],
        color=[SERIES[1] if k == JP else "#b8c6d9" for k in order],
    )
    for i, k in enumerate(order):
        ax.text(values[k], i, f" {values[k]:.4f}", va="center", fontsize=7, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_xlabel("両院の予算 ÷ 名目 GDP（%）", fontsize=8, color=INK)
    ax.invert_yaxis()
    _style(ax, "x")
    note = (
        "出典: IPU Parline（議院予算、現地通貨、CC BY-NC-SA 4.0）、World Bank WDI "
        "NY.GDP.MKTP.CN（CC BY 4.0）。"
        f"n = {len(order)}"
    )
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
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    marts = args.data_dir / "marts"
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    gdp_df = pl.read_parquet(marts / "wdi_gdp_lcu.parquet")
    cattr = pl.read_parquet(args.data_dir / "staged" / "ipu" / "country_attributes.parquet")
    o = ipu.filter(pl.col("oecd_member"))
    gdp = {
        (str(r["iso3"]), int(r["year"])): float(r["gdp_lcu"]) for r in gdp_df.iter_rows(named=True)
    }
    currency = {
        str(r["entity_id"]): str(r["value"])
        for r in cattr.filter(pl.col("attribute") == "local_currency")
        .sort("entity_id", "date_from", "seq")
        .iter_rows(named=True)
    }

    print("# R7 役割指標の補強と議会費の対 GDP 比（H2c・H5c）（2026-10-28）")
    print("\n事後追加の仮説（設計書 2026-10-28 節）。順位相関と比率の記述のみ。因果の主張はない。")

    per_m: dict[str, float] = {}
    names: dict[str, str] = {}
    wq: dict[str, float] = {}
    wq_year: dict[str, int] = {}
    gov_pct: dict[str, float] = {}
    inquiries: dict[str, bool] = {}
    ratio: dict[str, tuple[float, int, str]] = {}
    for iso3, grp in o.group_by("iso3"):
        iso = str(iso3[0])
        rows = list(grp.iter_rows(named=True))
        lower = next(r for r in rows if r["chamber_type"] == "lower")
        names[iso] = str(lower["country"])
        per_m[iso] = float(lower["statutory_seats"]) / (
            float(lower["population_thousands"]) * 1000 / 1e6
        )
        q = per_member(lower["written_questions"], lower["statutory_seats"])
        if q is not None:
            wq[iso] = q
            wq_year[iso] = int(lower["written_questions_year"])
        if lower["members_in_government_pct"] is not None:
            gov_pct[iso] = float(lower["members_in_government_pct"])
        if lower["carries_out_inquiries"] is not None:
            inquiries[iso] = bool(lower["carries_out_inquiries"])
        cc = str(lower["chamber_id"]).split("-")[0]
        b = budget_to_gdp(rows, gdp, currency.get(cc, ""))
        if b is not None:
            ratio[iso] = b

    # ---- H2c ----
    inq_label = {k: ("あり" if v else "なし") for k, v in inquiries.items()}
    keys = sorted(k for k in wq if k in per_m)
    rho = spearman([per_m[k] for k in keys], [wq[k] for k in keys])
    print(
        "\n## 表 1: 議員 1 人当たりの質問主意書数（下院、年）と人口当たり議員数（OECD、"
        "議員数の少ない順）"
    )
    print(
        md_row(
            ["国", "下院 /100 万人", "質問主意書 ÷ 定数（年）", "年", "政府入り議員 %", "調査権"]
        )
    )
    print("|---|---|---|---|---|---|")
    for k in sorted(per_m, key=lambda k: per_m[k]):
        mark = "**" if k == JP else ""
        print(
            md_row(
                [
                    f"{mark}{names[k]}{mark}",
                    f"{per_m[k]:.2f}",
                    f"{wq[k]:.1f}" if k in wq else "–",
                    wq_year.get(k, "–"),
                    f"{gov_pct[k]:.1f}" if k in gov_pct else "–",
                    inq_label.get(k, "–"),
                ]
            )
        )
    jp_rank = rank_of(wq, JP)
    med = sorted(wq.values())[len(wq) // 2]
    print(
        f"\n- Spearman ρ（人口当たり議員数 × 質問主意書 ÷ 定数）= {rho:.2f}（n = {len(keys)}）。"
        f"日本 {wq[JP]:.2f} 件/議員（{wq_year[JP]} 年）は {len(wq)} か国中 少ない方から {jp_rank} "
        f"位（中央値 {med:.2f}）"
    )
    print(f"- **H2c 判定: {judge_h2a(rho)}**（ρ ≤ −0.3 で整合、|ρ| < 0.2 で不支持）")
    gk = sorted(k for k in gov_pct if k in per_m)
    rho_g = spearman([per_m[k] for k in gk], [gov_pct[k] for k in gk])
    n_inq = sum(1 for v in inquiries.values() if v)
    print(
        f"- 探索的: 政府に入っている議員の比率 × 人口当たり議員数 ρ = {rho_g:.2f}（n = {len(gk)}）"
        "。"
        f"日本 {gov_pct.get(JP, float('nan')):.1f}%。調査権あり {n_inq}/{len(inquiries)} "
        "か国（日本: "
        f"{'あり' if inquiries.get(JP) else 'なし'}）"
    )
    fig_scatter(
        per_m,
        wq,
        "議員が少ない国ほど 1 人が多く質問主意書を出すか（OECD 下院）",
        "質問主意書 ÷ 定数（年、対数軸）",
        args.fig_dir / "r7_written_questions.png",
    )

    # ---- H5c ----
    vals = {k: v[0] for k, v in ratio.items()}
    r_jp, n = rank_of(vals, JP), len(vals)
    med_r = sorted(vals.values())[n // 2]
    print("\n## 表 2: 両院の予算 ÷ 名目 GDP（%、OECD、両院とも現地通貨の予算がある国）")
    print(md_row(["順位", "国", "予算 ÷ GDP %", "予算年", "計算"]))
    print("|---|---|---|---|---|")
    for i, k in enumerate(sorted(vals, key=lambda k: vals[k]), start=1):
        mark = "**" if k == JP else ""
        print(md_row([i, f"{mark}{names[k]}{mark}", f"{vals[k]:.4f}", ratio[k][1], ratio[k][2]]))
    excluded = sorted(k for k in per_m if k not in vals)
    print(
        f"\n- 日本 {vals[JP]:.4f}%（{ratio[JP][1]} 年）は {n} か国中 少ない方から {r_jp} "
        f"位（中央値 {med_r:.4f}%）。"
        f"除外 {len(excluded)} か国（予算または通貨の不一致）: {'、'.join(excluded)}"
    )
    print(f"- **H5c 判定: {judge_h5b(r_jp, n)}**（rank ≤ ceil(n/2) で整合）")
    fig_bars(vals, names, "両院の予算 ÷ 名目 GDP（%、OECD）", args.fig_dir / "r7_budget_to_gdp.png")
    print(f"\n図: {args.fig_dir}/r7_written_questions.png, r7_budget_to_gdp.png")


if __name__ == "__main__":
    main()
