"""R8: 成立した法律のうち議員提出はどれだけか — 日本・英国・フランス（H2d）。

H2 (b) の部分的な代替。事後追加の仮説 H2d（design/themes/parliament-size.md
「事後追加（2026-10-28 夕）」、結果の計算前に固定）:
  英国（Bills API、成立 = Royal Assent、Private Members' Bill の 4 類型）と フランス（国民議会
  open data、公布 = PROM-PUB、proposition de loi）で「成立法律のうち議員提出の比率」を出し、
  日本（内閣法制局）と並べる。H2 (b) の向きなら、3 か国の比率の順位は人口当たり下院議員数の
  順位（日本 < 仏 < 英）と一致する。
  判定: 順位が完全に一致すれば整合、日本が最下位でなければ不支持、それ以外は中間。弱い証拠。

決定的スクリプト。入力は data/marts/{uk_acts, fr_laws, jp_bill_counts, ipu_parliaments}.parquet。
純粋ヘルパは tests/test_analysis_r8.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
UK_YEARS = (2008, 2025)  # Bills API の収録が揃う完全年（2006–07 は部分、2026 は途中）
FR_YEARS = (2022, 2026)  # 第 16・17 立法期（2022-06〜）
JP_YEARS = (2013, 2026)  # 内閣法制局の一覧（第 183 回〜）


# ---- pure helpers -------------------------------------------------------------------------------


def member_share(counts: Mapping[str, int]) -> float | None:
    """{origin: 件数} → 議員提出 ÷ (議員提出 ＋ 政府提出) %。

    other（統合法案・私法案など）は分母に入れない。"""
    m, g = counts.get("member", 0), counts.get("government", 0)
    return 100.0 * m / (m + g) if m + g else None


def rank_consistent(shares: Mapping[str, float], per_million: Mapping[str, float]) -> str:
    """H2d の判定: 比率の順位が人口当たり議員数の順位と一致すれば整合。

    日本が最下位でなければ不支持、それ以外は中間。"""
    keys = sorted(shares, key=lambda k: shares[k])
    expected = sorted(per_million, key=lambda k: per_million[k])
    if keys == expected:
        return "整合"
    if keys[0] != expected[0]:
        return "不支持"
    return "中間"


def yearly(
    rows: Sequence[Mapping[str, object]], years: tuple[int, int]
) -> dict[int, dict[str, int]]:
    out: dict[int, dict[str, int]] = {}
    for r in rows:
        y = int(str(r["year"]))
        if years[0] <= y <= years[1]:
            d = out.setdefault(y, {})
            d[str(r["origin"])] = d.get(str(r["origin"]), 0) + 1
    return out


def totals(by_year: Mapping[int, Mapping[str, int]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for d in by_year.values():
        for k, v in d.items():
            out[k] = out.get(k, 0) + v
    return out


# ---- figure --------------------------------------------------------------------------------------


def fig_shares(series: Mapping[str, Mapping[int, float]], path: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    for i, (lab, s) in enumerate(series.items()):
        ys = sorted(s)
        ax.plot(ys, [s[y] for y in ys], marker="o", markersize=3, color=SERIES[i], label=lab)
    ax.set_ylabel("成立法律に占める議員提出の比率（%）", fontsize=8, color=INK)
    ax.set_title(
        "議員立法は成立法律のどれだけを占めるか（日本・英国・フランス）", fontsize=10, loc="left"
    )
    ax.legend(fontsize=8, frameon=False)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    note = (
        "出典: 内閣法制局（日本、年）、UK Parliament Bills API（Royal Assent 年、"
        "Open Parliament Licence）、"
        "Assemblée nationale open data（公布年、Licence Ouverte）"
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
    uk = pl.read_parquet(marts / "uk_acts.parquet")
    fr = pl.read_parquet(marts / "fr_laws.parquet")
    jp = pl.read_parquet(marts / "jp_bill_counts.parquet")
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    lower = ipu.filter(pl.col("chamber_type") == "lower")
    per_m = {
        str(r["iso3"]): float(r["statutory_seats"])
        / (float(r["population_thousands"]) * 1000 / 1e6)
        for r in lower.iter_rows(named=True)
        if r["iso3"] in ("JPN", "GBR", "FRA")
    }

    uk_by = yearly(list(uk.iter_rows(named=True)), UK_YEARS)
    fr_by = yearly(list(fr.iter_rows(named=True)), FR_YEARS)
    jp_by: dict[int, dict[str, int]] = {}
    for r in jp.iter_rows(named=True):
        y = int(r["year"])
        if JP_YEARS[0] <= y <= JP_YEARS[1]:
            d = jp_by.setdefault(y, {"member": 0, "government": 0})
            d["member"] += int(r["member_enacted"])
            d["government"] += int(r["cabinet_enacted"])
    tot = {"JPN": totals(jp_by), "GBR": totals(uk_by), "FRA": totals(fr_by)}
    shares = {k: s for k, v in tot.items() if (s := member_share(v)) is not None}

    print("# R8 成立した法律のうち議員提出はどれだけか — 日本・英国・フランス（H2d）（2026-10-28）")
    print("\n事後追加の仮説（設計書 2026-10-28 夕 節）。記述のみ。因果の主張はない。")
    print("\n## 表 1: 成立法律に占める議員提出の比率（期間合計）")
    print(
        md_row(
            [
                "国",
                "期間",
                "政府提出 成立",
                "議員提出 成立",
                "その他",
                "議員提出の比率 %",
                "下院 /100 万人",
            ]
        )
    )
    print("|---|---|---|---|---|---|---|")
    labels = {"JPN": ("日本", JP_YEARS), "GBR": ("英国", UK_YEARS), "FRA": ("フランス", FR_YEARS)}
    for iso in ("JPN", "FRA", "GBR"):
        name, yrs = labels[iso]
        t = tot[iso]
        print(
            md_row(
                [
                    name,
                    f"{yrs[0]}–{yrs[1]}",
                    t.get("government", 0),
                    t.get("member", 0),
                    t.get("other", 0),
                    f"{shares[iso]:.1f}",
                    f"{per_m[iso]:.2f}",
                ]
            )
        )
    verdict = rank_consistent(shares, per_m)
    order = " < ".join(
        f"{labels[k][0]} {shares[k]:.1f}%" for k in sorted(shares, key=lambda k: shares[k])
    )
    print(f"\n- 比率の順位: {order}。人口当たり議員数の順位: 日本 < フランス < 英国")
    print(f"- **H2d 判定: {verdict}**（3 か国の順位一致で判定、弱い証拠）")

    print("\n## 表 2: 年別（英国は Royal Assent 年、フランスは公布年、日本は国会の開会年）")
    print(
        md_row(
            [
                "年",
                "日本 政府",
                "日本 議員",
                "日本 %",
                "英国 政府",
                "英国 議員",
                "英国 %",
                "仏 政府",
                "仏 議員",
                "仏 %",
            ]
        )
    )
    print("|" + "---|" * 10)
    series: dict[str, dict[int, float]] = {"日本": {}, "英国": {}, "フランス": {}}
    for y in range(2008, 2027):
        cells: list[object] = [y]
        for lab, by in (("日本", jp_by), ("英国", uk_by), ("フランス", fr_by)):
            dy = by.get(y)
            s = member_share(dy) if dy else None
            if s is not None:
                series[lab][y] = s
            cells += [
                dy.get("government", 0) if dy else "–",
                dy.get("member", 0) if dy else "–",
                f"{s:.0f}" if s is not None else "–",
            ]
        print(md_row(cells))
    fig_shares(series, args.fig_dir / "r8_member_bill_share.png")

    uk_types = (
        uk.filter(pl.col("year").is_between(*UK_YEARS))
        .group_by("bill_type")
        .len()
        .sort(["len", "bill_type"], descending=[True, False])
    )
    print("\n## 表 3: 英国の成立法案の種別（2008–2025）")
    print(md_row(["種別", "件数"]))
    print("|---|---|")
    for r in uk_types.iter_rows(named=True):
        print(md_row([r["bill_type"], r["len"]]))
    fr_proc = (
        fr.group_by("procedure", "origin")
        .len()
        .sort(["len", "procedure", "origin"], descending=[True, False, False])
    )
    print("\n## 表 4: フランスの公布法律の手続種別（第 16・17 立法期）")
    print(md_row(["手続", "提出", "件数"]))
    print("|---|---|---|")
    for r in fr_proc.iter_rows(named=True):
        print(md_row([r["procedure"], r["origin"], r["len"]]))
    print(f"\n図: {args.fig_dir}/r8_member_bill_share.png")


if __name__ == "__main__":
    main()
