"""R6: 需要側の構造（H11）— サイクリングの乗り手は高齢化し、若年層は補充されていないのか。

事前登録（design/themes/bicycle-industry.md、2026-10-22）:
  H11 (a): 社会生活基本調査「サイクリング」行動者率の 2011 → 2021 変化が、
           20–39 歳（20–24・25–29・30–39 の単純平均）で < 0 かつ 50–69 歳（50–59・60–64・65–69 の
           単純平均）で ≥ 0 なら整合。両方低下 → 全年齢の減少（高齢化ではない）。両方上昇 → 不支持。
           若年上昇・高齢低下 → 不支持（若返り）。
  H11 (b): 行動者の年齢重心（年齢階級の中点を 行動者率 × 階級幅 で加重した平均年齢、人口構成一定の
           近似）が 2011 → 2021 に上がれば整合。
  局面: 2021 年調査は特需期。2016（コロナ前）→ 2021 と 2006 → 2016 を並べる。補助: 男女別、他種目。

決定的スクリプト。入力は data/marts/jp_sports_participation.parquet のみ。

    uv run python themes/bicycle-industry/src/theme_bicycle_industry/analysis/\\
        a20261022_r6_participation.py [--data-dir data] [--fig-dir …]

純粋ヘルパ（group_mean, judge_h11a, age_centroid, judge_h11b）は tests/test_analysis_r6.py で
検証する。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_bicycle_industry.analysis.a20261022_r1_volume_price import (
    INK,
    MUTED,
    SERIES,
    _style,
)

THEME_DIR = Path(__file__).resolve().parents[3]
YOUNG: tuple[str, ...] = ("20_24", "25_29", "30_39")
OLD: tuple[str, ...] = ("50_59", "60_64", "65_69")
# 年齢階級の中点と幅（70 歳以上は 70–84 とみなす: 中点 77、幅 15）
AGE_MID: dict[str, tuple[float, float]] = {
    "10_14": (12.0, 5),
    "15_19": (17.0, 5),
    "20_24": (22.0, 5),
    "25_29": (27.0, 5),
    "30_39": (34.5, 10),
    "40_49": (44.5, 10),
    "50_59": (54.5, 10),
    "60_64": (62.0, 5),
    "65_69": (67.0, 5),
    "70_plus": (77.0, 15),
}
AGE_JA: dict[str, str] = {
    "10_14": "10–14",
    "15_19": "15–19",
    "20_24": "20–24",
    "25_29": "25–29",
    "30_39": "30–39",
    "40_49": "40–49",
    "50_59": "50–59",
    "60_64": "60–64",
    "65_69": "65–69",
    "70_plus": "70+",
    "total": "総数",
}
COMPARE_SPORTS: tuple[str, ...] = (
    "サイクリング",
    "ジョギング・マラソン",
    "登山・ハイキング",
    "ゴルフ(練習場を含む)",
    "つり",
    "総数",
)


def group_mean(rates: Mapping[str, float], ages: Sequence[str]) -> float:
    xs = [rates[a] for a in ages if a in rates]
    return sum(xs) / len(xs) if len(xs) == len(ages) else math.nan


def judge_h11a(young_change: float, old_change: float) -> str:
    if math.isnan(young_change) or math.isnan(old_change):
        return "判定不能"
    if young_change < 0 and old_change >= 0:
        return "整合（高齢化・非補充）"
    if young_change < 0 and old_change < 0:
        return "全年齢の減少（高齢化ではない）"
    if young_change >= 0 and old_change < 0:
        return "不支持（若返り）"
    return "不支持（全年齢の増加）"


def age_centroid(rates: Mapping[str, float]) -> float:
    """行動者率 × 階級幅 を重みにした年齢階級中点の加重平均（人口構成一定の近似）。"""
    num = den = 0.0
    for age, (mid, width) in AGE_MID.items():
        if age in rates:
            w = rates[age] * width
            num += mid * w
            den += w
    return num / den if den > 0 else math.nan


def judge_h11b(delta_years: float) -> str:
    if math.isnan(delta_years):
        return "判定不能"
    return "整合（重心が上がった）" if delta_years > 0 else "不支持（重心が下がった）"


def rates_of(m: pl.DataFrame, sport: str, sex: str, year: int) -> dict[str, float]:
    sub = m.filter((pl.col("sport") == sport) & (pl.col("sex") == sex) & (pl.col("year") == year))
    return {str(r["age"]): float(r["rate_pct"]) for r in sub.iter_rows(named=True)}


def fig_age_profile(
    profiles: Mapping[int, Mapping[str, float]], path: Path, title: str, source: str
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ages = [a for a in AGE_MID if all(a in p for p in profiles.values())]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (year, p), color in zip(sorted(profiles.items()), SERIES, strict=False):
        ax.plot(
            range(len(ages)),
            [p[a] for a in ages],
            color=color,
            linewidth=2,
            marker="o",
            markersize=3.5,
            label=str(year),
        )
    ax.set_xticks(range(len(ages)))
    ax.set_xticklabels([AGE_JA[a] for a in ages], fontsize=8)
    ax.legend(fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=6)
    ax.set_ylabel("行動者率（%）", fontsize=8, color=INK)
    ax.set_xlabel("年齢階級（歳）", fontsize=8, color=INK)
    ax.set_title(title, fontsize=10, color=INK, loc="left", pad=18)
    _style(ax)
    fig.text(0.01, 0.01, f"出典: {source}", fontsize=7, color=MUTED, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    fig_dir: Path = args.fig_dir
    m = pl.read_parquet(args.data_dir / "marts" / "jp_sports_participation.parquet")

    import logging

    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]
    src = "総務省 社会生活基本調査 時系列統計表（スポーツの種類別行動者率、10 歳以上、過去 1 年）"

    print("# R6 需要側の構造（H11）（2026-10-22）")
    print(f"jp_sports_participation {m.height} rows")

    years = (1996, 2006, 2011, 2016, 2021)
    prof = {y: rates_of(m, "サイクリング", "total", y) for y in years}
    print("\n## サイクリング 行動者率（%、男女計）")
    ages = [*AGE_MID, "total"]
    print("| 年齢 | " + " | ".join(str(y) for y in years) + " |")
    print("|---|" + "---|" * len(years))
    for a in ages:
        print(
            f"| {AGE_JA[a]} | "
            + " | ".join(f"{prof[y].get(a, float('nan')):.1f}" for y in years)
            + " |"
        )

    print("\n## H11 (a) 主判定: 2011 → 2021、20–39 歳 vs 50–69 歳（単純平均）")
    for sex in ("total", "male", "female"):
        r11, r21 = rates_of(m, "サイクリング", sex, 2011), rates_of(m, "サイクリング", sex, 2021)
        y11, y21 = group_mean(r11, YOUNG), group_mean(r21, YOUNG)
        o11, o21 = group_mean(r11, OLD), group_mean(r21, OLD)
        tag = {"total": "男女計（主判定）", "male": "男", "female": "女"}[sex]
        mark = "**" if sex == "total" else ""
        print(
            f"- {tag}: 20–39 歳 {y11:.2f} → {y21:.2f}（{y21 - y11:+.2f}pt）, 50–69 歳 {o11:.2f} → {o21:.2f}"  # noqa: E501
            f"（{o21 - o11:+.2f}pt） → {mark}{judge_h11a(y21 - y11, o21 - o11)}{mark}"
        )

    print("\n## H11 (b) 主判定: 行動者の年齢重心（人口構成一定の近似）")
    for sex in ("total", "male", "female"):
        cents = {y: age_centroid(rates_of(m, "サイクリング", sex, y)) for y in years}
        tag = {"total": "男女計（主判定）", "male": "男", "female": "女"}[sex]
        mark = "**" if sex == "total" else ""
        print(
            f"- {tag}: "
            + ", ".join(f"{y} {c:.1f} 歳" for y, c in cents.items())
            + f" → 2011→2021 {cents[2021] - cents[2011]:+.1f} 歳 → {mark}{judge_h11b(cents[2021] - cents[2011])}{mark}"  # noqa: E501
        )

    print("\n## 局面別（男女計）: 2006 → 2016（コロナ前の 10 年）と 2016 → 2021（コロナ前 → 特需）")
    for ya, yb in ((2006, 2016), (2016, 2021), (2011, 2021)):
        ra, rb = prof[ya], prof[yb]
        print(
            f"- {ya}→{yb}: 20–39 歳 {group_mean(rb, YOUNG) - group_mean(ra, YOUNG):+.1f}pt, "
            f"50–69 歳 {group_mean(rb, OLD) - group_mean(ra, OLD):+.1f}pt, 総数 {rb['total'] - ra['total']:+.1f}pt, "  # noqa: E501
            f"重心 {age_centroid(rb) - age_centroid(ra):+.1f} 歳"
        )

    print("\n## 頑健性（男女計）")
    r11, r21 = prof[2011], prof[2021]
    for label, grp in (
        ("20–29 歳", ("20_24", "25_29")),
        ("30–49 歳", ("30_39", "40_49")),
        ("60–69 歳", ("60_64", "65_69")),
    ):
        g11, g21 = group_mean(r11, grp), group_mean(r21, grp)
        print(f"- {label}: {g11:.2f} → {g21:.2f}（{g21 - g11:+.2f}pt）")
    saved = AGE_MID["70_plus"]
    AGE_MID["70_plus"] = (75.0, 11)
    c11, c21 = age_centroid(r11), age_centroid(r21)
    AGE_MID["70_plus"] = saved
    print(
        f"- 70 歳以上の中点を 75 歳（幅 11）にした重心: 2011 {c11:.1f} → 2021 {c21:.1f}（{c21 - c11:+.1f} 歳）"  # noqa: E501
    )

    print("\n## 他種目との比較（男女計、2011 → 2021 の pt 変化と重心の変化）")
    print("| 種目 | 総数 2011 | 総数 2021 | 20–39 歳 | 50–69 歳 | 重心 2011 | 重心 2021 | (a) |")
    print("|---|---|---|---|---|---|---|---|")
    for sp in COMPARE_SPORTS:
        r11, r21 = rates_of(m, sp, "total", 2011), rates_of(m, sp, "total", 2021)
        if not r11 or not r21:
            print(f"| {sp} | – | – | – | – | – | – | – |")
            continue
        dy = group_mean(r21, YOUNG) - group_mean(r11, YOUNG)
        do = group_mean(r21, OLD) - group_mean(r11, OLD)
        print(
            f"| {sp} | {r11.get('total', float('nan')):.1f} | {r21.get('total', float('nan')):.1f} | {dy:+.1f} | {do:+.1f} "  # noqa: E501
            f"| {age_centroid(r11):.1f} | {age_centroid(r21):.1f} | {judge_h11a(dy, do)} |"
        )

    fig_age_profile(
        {y: prof[y] for y in years},
        fig_dir / "r6_h11_cycling_age_profile.png",
        "サイクリングの行動者率: 年齢階級別（男女計）",
        src,
    )
    fig_age_profile(
        {y: rates_of(m, "サイクリング", "male", y) for y in years},
        fig_dir / "r6_h11_cycling_age_profile_male.png",
        "サイクリングの行動者率: 年齢階級別（男）",
        src,
    )
    print("\n図:", ", ".join(p.name for p in sorted(fig_dir.glob("r6_*.png"))))


if __name__ == "__main__":
    main()
