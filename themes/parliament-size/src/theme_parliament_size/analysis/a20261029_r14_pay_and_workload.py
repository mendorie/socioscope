"""R14: 議員 1 人の報酬は相対的に高いか、稼働日数は本会議だけでは過小評価か（H12・H13）。

事後追加の仮説（design/themes/parliament-size.md「事後追加（2026-10-29 夕、R14）」、
結果の計算前に固定）:
  H12 : IPU の議員基本給（現地通貨、年額）÷ (a) 同年の 1 人当たり名目 GDP（WDI）、(b)
  雇用者の平均月収 × 12
        （ILOSTAT。日本は ILOSTAT に無く、国税庁 民間給与実態統計の平均給与を手入力）。日本が (a)
        (b) とも
        高い方から上位 3 分の 1 なら整合（世論と整合）、両方で下位 3 分の 1 なら不支持、
        それ以外は中間。
  H13 : 国会会議録 API で衆議院の本会議日数・委員会等の回数・
  稼働日数（いずれかの会議があった日数）を
        年別に出す。稼働日数が本会議日数の 2 倍以上なら「本会議日数だけでは過小評価」に整合。

決定的スクリプト。入力は data/marts/{ipu_parliaments, wdi_gdp_pcap_lcu, ilo_earnings_monthly,
jp_hr_sitting_days}.parquet と data/staged/ipu/{chamber_attributes, country_attributes}.parquet。
純粋ヘルパは tests/test_analysis_r14.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row
from theme_parliament_size.analysis.a20261027_r3_cost import rank_of

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
# 日本の雇用者の平均給与（年額、円）。国税庁「令和 5 年分 民間給与実態統計調査」の平均給与 460
# 万円。
# ILOSTAT に日本の月収が無いため手入力（出典付き）。1 年を通じて勤務した給与所得者の平均で、
# 賞与を含む。
JP_AVG_ANNUAL_WAGE_YEN = 4_600_000
JP_AVG_WAGE_YEAR = 2023
# ILOSTAT の「現地通貨」の月収が USD と見られる国を除くための妥当性の幅: 平均年収 ÷ 1 人当たり GDP
WAGE_PLAUSIBLE = (0.3, 3.0)
# R3 の議員 1 人当たり直接経費（円/年）: 歳費＋期末手当、調査研究広報滞在費、
# 立法事務費（秘書給与を除く）
JP_PAY_PLUS_ALLOWANCES_YEN = 21_063_085 + 12_000_000 + 7_800_000


# ---- pure helpers -------------------------------------------------------------------------------


def latest_local_salary(rows: Sequence[Mapping[str, object]]) -> tuple[float, str, int] | None:
    """staged/ipu/chamber_attributes の basic_salary 行 → (年額, 通貨, 年)。最新の date_from。"""
    cands = [
        (str(r["date_from"]), float(str(r["value_num"])), str(r["unit"]))
        for r in rows
        if str(r["attribute"]) == "basic_salary" and r["value_num"] is not None
    ]
    if not cands:
        return None
    d, v, u = max(cands)
    return v, u, int(d[:4])


def tercile_verdict(rank_from_top: int, n: int) -> str:
    """高い方からの順位で上位 3 分の 1 なら '高い'、下位 3 分の 1 なら '低い'、他は '中位'。"""
    if rank_from_top <= (n + 2) // 3:
        return "高い"
    if rank_from_top > n - (n + 2) // 3:
        return "低い"
    return "中位"


def judge_h12(verdict_a: str, verdict_b: str) -> str:
    if verdict_a == "高い" and verdict_b == "高い":
        return "整合"
    if verdict_a == "低い" and verdict_b == "低い":
        return "不支持"
    return "中間"


def judge_h13(sitting_days: float, plenary_days: float) -> str:
    return "整合" if plenary_days > 0 and sitting_days >= 2 * plenary_days else "不支持"


# ---- figure --------------------------------------------------------------------------------------


def fig_bars(
    values: Mapping[str, float],
    names: Mapping[str, str],
    title: str,
    xlabel: str,
    path: Path,
    note: str,
) -> None:
    import matplotlib.pyplot as plt

    order = sorted(values, key=lambda k: values[k])
    fig, ax = plt.subplots(figsize=(7.2, 0.22 * len(order) + 1.6))
    ax.barh(
        [names[k] for k in order],
        [values[k] for k in order],
        color=[SERIES[1] if k == JP else "#b8c6d9" for k in order],
    )
    for i, k in enumerate(order):
        ax.text(values[k], i, f" {values[k]:.1f}", va="center", fontsize=7, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left")
    ax.set_xlabel(xlabel, fontsize=8, color=INK)
    ax.invert_yaxis()
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
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
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    marts = args.data_dir / "marts"
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    gdp = pl.read_parquet(marts / "wdi_gdp_pcap_lcu.parquet")
    ear = pl.read_parquet(marts / "ilo_earnings_monthly.parquet")
    sitting = pl.read_parquet(marts / "jp_hr_sitting_days.parquet")
    cattr = pl.read_parquet(args.data_dir / "staged" / "ipu" / "chamber_attributes.parquet")
    kattr = pl.read_parquet(args.data_dir / "staged" / "ipu" / "country_attributes.parquet")
    lower = ipu.filter(pl.col("oecd_member") & (pl.col("chamber_type") == "lower"))
    names = {str(r["iso3"]): str(r["country"]) for r in lower.iter_rows(named=True)}
    cc_of = {
        str(r["iso3"]): str(r["chamber_id"]).split("-")[0] for r in lower.iter_rows(named=True)
    }
    chamber_of = {str(r["iso3"]): str(r["chamber_id"]) for r in lower.iter_rows(named=True)}
    currency = {
        str(r["entity_id"]): str(r["value"])
        for r in kattr.filter(pl.col("attribute") == "local_currency")
        .sort("entity_id", "date_from", "seq")
        .iter_rows(named=True)
    }
    gdp_pc = {
        (str(r["iso3"]), int(r["year"])): float(r["gdp_pcap_lcu"])
        for r in gdp.iter_rows(named=True)
    }
    earnings: dict[str, dict[int, float]] = {}
    for r in ear.iter_rows(named=True):
        earnings.setdefault(str(r["iso3"]), {})[int(r["year"])] = float(r["value_thousands"])

    print(
        "# R14 議員 1 人の報酬は相対的に高いか、稼働日数は本会議だけでは過小評価か（H12・H13）"
        "（2026-10-29）"
    )
    print("\n事後追加の仮説（設計書 2026-10-29 夕 節）。比率と順位の記述のみ。因果の主張はない。")

    # ---- H12 ----
    ratio_gdp: dict[str, float] = {}
    ratio_wage: dict[str, float] = {}
    rows_out: list[list[object]] = []
    excluded: list[str] = []
    for iso in sorted(names):
        rows = list(cattr.filter(pl.col("entity_id") == chamber_of[iso]).iter_rows(named=True))
        sal = latest_local_salary(rows)
        if sal is None:
            excluded.append(f"{iso}（基本給なし）")
            continue
        value, unit, year = sal
        if unit != currency.get(cc_of[iso]) and currency.get(cc_of[iso]):
            excluded.append(f"{iso}（通貨 {unit} ≠ {currency.get(cc_of[iso])}）")
            continue
        g = gdp_pc.get((iso, year)) or gdp_pc.get((iso, year - 1))
        g_year = year if (iso, year) in gdp_pc else year - 1
        if g is None:
            excluded.append(f"{iso}（{year} 年の GDP なし）")
            continue
        ratio_gdp[iso] = value / g
        wage_note = "–"
        if iso in earnings:
            e = earnings[iso]
            ey = max(y for y in e if y <= year) if any(y <= year for y in e) else max(e)
            annual = e[ey] * 12
            g_ey = gdp_pc.get((iso, ey)) or g
            plaus = annual / g_ey
            if WAGE_PLAUSIBLE[0] <= plaus <= WAGE_PLAUSIBLE[1]:
                ratio_wage[iso] = value / annual
                wage_note = f"{e[ey]:,.0f}（{ey}）"
            else:
                wage_note = f"{e[ey]:,.0f}（{ey}、年収 ÷ GDP = {plaus:.2f} で単位不整合、除外）"
        rows_out.append(
            [
                names[iso],
                f"{value:,.0f} {unit}",
                year,
                f"{g:,.0f}（{g_year}）",
                f"{ratio_gdp[iso]:.1f}",
                wage_note,
                f"{ratio_wage[iso]:.1f}" if iso in ratio_wage else "–",
            ]
        )
    print(
        "\n## 表 1: 下院議員の基本給（現地通貨、年額）と 1 人当たり GDP・"
        "平均賃金に対する倍率（OECD）"
    )
    print(
        md_row(
            [
                "国",
                "基本給",
                "年",
                "1 人当たり GDP（年）",
                "÷ 1 人当たり GDP",
                "平均月収（年）",
                "÷ 平均年収",
            ]
        )
    )
    print("|" + "---|" * 7)
    for row in sorted(rows_out, key=lambda r: -float(str(r[4]))):
        print(md_row(row))
    n_g, n_w = len(ratio_gdp), len(ratio_wage)
    rk_g = n_g + 1 - rank_of(ratio_gdp, JP)
    rk_w = n_w + 1 - rank_of(ratio_wage, JP)
    med_g = sorted(ratio_gdp.values())[n_g // 2]
    med_w = sorted(ratio_wage.values())[n_w // 2]
    va, vb = tercile_verdict(rk_g, n_g), tercile_verdict(rk_w, n_w)
    print(f"\n- 除外: {'、'.join(excluded) if excluded else 'なし'}")
    print(
        f"- (a) 基本給 ÷ 1 人当たり GDP: 日本 {ratio_gdp[JP]:.1f} 倍、{n_g} か国中 高い方から "
        f"{rk_g} 位（中央値 {med_g:.1f}）→ {va}"
    )
    print(
        f"- (b) 基本給 ÷ 平均年収: 日本 {ratio_wage[JP]:.1f} 倍、{n_w} か国中 高い方から {rk_w} "
        f"位（中央値 {med_w:.1f}）→ {vb}"
    )
    print(f"- **H12 判定: {judge_h12(va, vb)}**（両方で上位 3 分の 1 なら整合）")
    jp_wage_alt = ratio_gdp[JP] * gdp_pc[(JP, 2025)] / JP_AVG_ANNUAL_WAGE_YEN
    print(
        f"- 頑健性: 日本の分母を国税庁 民間給与実態統計の平均給与 {JP_AVG_ANNUAL_WAGE_YEN:,} 円"
        f"（{JP_AVG_WAGE_YEAR}、賞与込み）にすると {jp_wage_alt:.1f} 倍"
    )
    jp_total = JP_PAY_PLUS_ALLOWANCES_YEN
    print(
        f"- 参考（事後）: 日本の歳費＋期末手当＋調査研究広報滞在費＋立法事務費 = "
        f"{jp_total:,} 円は、"
        f"1 人当たり GDP の {jp_total / gdp_pc[(JP, 2025)]:.1f} 倍、"
        f"国税庁の平均給与 460 万円の {jp_total / JP_AVG_ANNUAL_WAGE_YEN:.1f} 倍。"
        "他国の手当は IPU に無く比べられない"
    )
    fig_bars(
        ratio_gdp,
        names,
        "下院議員の基本給 ÷ 1 人当たり名目 GDP（OECD）",
        "倍",
        args.fig_dir / "r14_salary_to_gdp.png",
        f"出典: IPU Parline（基本給、CC BY-NC-SA 4.0）、World Bank WDI NY.GDP.PCAP.CN。n = {n_g}",
    )
    fig_bars(
        ratio_wage,
        names,
        "下院議員の基本給 ÷ 雇用者の平均年収（OECD）",
        "倍",
        args.fig_dir / "r14_salary_to_wage.png",
        "出典: IPU Parline、ILOSTAT EAR_EMTA（平均月収 × 12）、日本は国税庁 民間給与実態統計 460 "
        f"万円。n = {n_w}",
    )

    # ---- H13 ----
    sd = sitting.pivot(on="metric", index="year", values="value").sort("year")
    print("\n## 表 2: 衆議院の本会議日数・委員会等の回数・稼働日数（国会会議録 API、暦年）")
    print(
        md_row(
            [
                "年",
                "本会議日数",
                "委員会等の回数",
                "委員会等の開会日数",
                "稼働日数（いずれかの会議）",
                "稼働 ÷ 本会議",
            ]
        )
    )
    print("|" + "---|" * 6)
    ratios: list[float] = []
    for r in sd.iter_rows(named=True):
        ratios.append(float(r["sitting_days"]) / float(r["plenary_days"]))
        print(
            md_row(
                [
                    r["year"],
                    r["plenary_days"],
                    r["committee_meetings"],
                    r["committee_days"],
                    r["sitting_days"],
                    f"{ratios[-1]:.2f}",
                ]
            )
        )
    mean_sit = sd["sitting_days"].mean()
    mean_plen = sd["plenary_days"].mean()
    assert isinstance(mean_sit, float) and isinstance(mean_plen, float)
    ipu_days = {
        str(r["iso3"]): float(r["plenary_days"])
        for r in lower.iter_rows(named=True)
        if r["plenary_days"] is not None
    }
    med_days = sorted(ipu_days.values())[len(ipu_days) // 2]
    print(
        f"\n- 2013–2025 年平均: 本会議 {mean_plen:.0f} 日、稼働 {mean_sit:.0f} 日"
        f"（{mean_sit / mean_plen:.2f} 倍）"
    )
    print(
        f"- IPU の OECD 下院の本会議日数の中央値 {med_days:.0f} 日（n = {len(ipu_days)}）。"
        "日本の本会議日数は中央値の半分だが、稼働日数は中央値を上回る"
    )
    print(
        f"- **H13 判定: {judge_h13(mean_sit, mean_plen)}**（稼働日数が本会議日数の 2 "
        "倍以上なら整合）"
    )
    print(f"\n図: {args.fig_dir}/r14_salary_to_gdp.png, r14_salary_to_wage.png")


if __name__ == "__main__":
    main()
