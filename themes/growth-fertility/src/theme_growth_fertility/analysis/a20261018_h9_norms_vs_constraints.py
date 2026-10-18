"""H9（事後追加）: 2 人未満への低下は「規範の崩れ（N）」か「実現の阻害（C）」か。

事前登録: design/themes/growth-fertility.md「### H9」（2026-10-18、part5）。検定 V1〜V4・分類規則・
最終スタンスの文型・頑健性・言えないことは追加データを見る前に design に固定した。H8〜H8d の判定は
変えない。

  V1 規範 vs 阻害（主）: 最新 TFR < 1.6 で理想が 2 時点以上ある国（欧州 EB2006 → EB2011 → GGS-II、
     日本 1977–2021）。N 型 = 最新の理想（日本は予定）< 2.1 かつ最初から 0.2 以上低下。
     C 型 = 最新の理想 >= 2.2、理想 − TFR >= 0.6、かつ最初の観測より差が拡大。他は混合。過半判定。
  V2 無子化か 1 人止まりか: 期間 TFR の低下の出生順位分解。第 1 子の寄与 >= 50% → 無子化型、
     第 2 子以降 >= 60% → 1 人止まり型、間は混合。補助: OECD SF2.5 無子率 1955 → 1975 コーホート。
  V3 コーホートの回復: 1975 コーホートの完結出生数 − 期間 TFR の最小値 >= 0.3 → 回復型。
     1960 → 1975 で 0.3 以上低下し 1.7 未満 → 量的減少型。
  V4 総合と最終スタンスの文。

運用の細則（design に書かれていない点。最初の実行より前にここで固定し、stdout の冒頭に出す）:
  - 日本の予定の主系列は xlsx 表 4-25 の総数（`planned_children`/総数）。PDF 図表 7-1 の値
    （`planned_children_pdf`/夫婦）は頑健性。理想（`ideal_children`/夫婦）は併記（判定外）。
  - 欧州の理想の主系列: 2006 = EB 253 の両性 25–39（女性 25–39 が無いため）、2011 = EB 75.4 の
    女性 25–39、2020 年代 = GGS-II の女性 30–39。いずれも「個人の理想」の平均。2006 を女性・全年齢に
    差し替える版は頑健性。
  - 「理想 − TFR」の TFR は各調査年の WDI 期間 TFR（GGS は国ごとの調査年）。
    TFR < 1.6 は WDI の最新年。
  - V2 の国別の型（V4 の過半判定に使う）は、3 地域に共通する 2010 → 最新の窓で決める。日本・韓国の
    1990 → 最新は併記する。「主役」（文型）は、低下があった国の第 1 子寄与率の中央値が 50% 以上なら
    第 1 子、未満なら第 2 子以降。
  - V3 の「同時期の期間 TFR の最小値」= 1950–1975 コーホートが 30 歳だった年（1980–2005）の期間 TFR
    の最小値。完結出生数は 45 歳時点の累積（日本は表 4-11、欧州は `cohort_cum` の 45 歳）。
    「回復している」= V3 の対象国の過半が回復型（回復型＋両方）。
  - V4: V1 が N 型過半で V2 が無子化型過半なら「支持」、V1 が C 型過半なら
    「不支持（阻害に置き換え）」、
    V1 が N 型過半でも V2 が無子化型過半でなければ「部分的」、V1 が過半なしなら「国で異なる」。

決定的スクリプト。乱数不使用。補完なし。識別戦略なし（国レベルの記述のみ）。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋関数（classify_v1, majority, order_decline, classify_v2, approx_order_tfr, classify_v3,
v4_verdict, lead_order, final_stance, period_min）は tests/test_analysis_h9.py で検証。
"""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from theme_growth_fertility.analysis.a20261004_h1_income_tfr import (
    BLUE_RAMP,
    INK,
    MUTED,
    ORANGE,
    _style,
)
from theme_growth_fertility.analysis.a20261004_h3_jp_income_class import spearman

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
PANEL_MART = Path("marts") / "growth_fertility_panel.parquet"
IDEALS_MART = Path("marts") / "eu_fertility_ideals.parquet"
JP_SURVEY_MART = Path("marts") / "jp_fertility_survey.parquet"
JP_ORDER_MART = Path("marts") / "jp_births_order_cohort.parquet"
KR_MART = Path("marts") / "kr_births_order_asfr.parquet"
EU_ORDER_MART = Path("marts") / "eu_tfr_by_birth_order.parquet"
EU_COHORT_MART = Path("marts") / "eu_cohort_fertility.parquet"
OECD_CL_MART = Path("marts") / "oecd_childlessness.parquet"

# ---------------------------------------------------------------- pre-registered (design H9)
TFR_MAX = 1.6
N_IDEAL_MAX, N_DROP, C_IDEAL_MIN, C_GAP = 2.1, 0.2, 2.2, 0.6
V2_FIRST_MIN, V2_LATER_MIN = 0.5, 0.6
V3_RECOVERY, V3_DROP, V3_FLOOR = 0.3, 0.3, 1.7
V3_FIRST_COHORT, V3_REF_COHORT, V3_COHORT = 1950, 1960, 1975
V3_PERIOD_AGE, V3_AGE = 30, 45
OECD_FROM, OECD_TO = 1955, 1975

# ---------------------------------------------------------------- operational (fixed pre-run)
JP_PLANNED = ("planned_children", "総数")  # xlsx T04-25 (main)
JP_PLANNED_PDF = ("planned_children_pdf", "夫婦")  # PDF 図表 7-1 (robustness)
JP_IDEAL = ("ideal_children", "夫婦")  # shown, not the main verdict
JP_IDEAL_U35 = ("ideal_children", "夫婦（妻35歳未満）")
JP_PLANNED_U35 = ("planned_children_pdf", "夫婦（妻35歳未満）")
JP_SINGLE_F = ("desired_children_single", "未婚女性")
EU_WAVES: tuple[tuple[str, str, str], ...] = (
    ("eb2006", "T", "25-39"),
    ("eb2011", "F", "25-39"),
    ("ggs2020", "F", "30-39"),
)
EU_WAVES_F2006: tuple[tuple[str, str, str], ...] = (("eb2006", "F", "total"), *EU_WAVES[1:])
EU_WAVES_GENERAL: tuple[tuple[str, str, str], ...] = EU_WAVES[:2]  # GGS has no general ideal
IDEAL_PERSONAL, IDEAL_GENERAL = "ideal_personal_mean", "ideal_general_mean"
V2_START, V2_ALT_STARTS, V2_LONG_START = 2010, (2005, 2015), 1990
JP_ORDERS = ("第1子", "第2子", "第3子", "第4子", "第5子以上")
KR_ORDERS = ("첫째아", "둘째아", "셋째아", "넷째아 이상")
EU_ORDERS = ("1", "2", "3", "GE4")
NORDIC = ("DNK", "FIN", "ISL", "NOR", "SWE")
SOUTH = ("ESP", "GRC", "ITA", "PRT")
COUNTRY_JA = {
    "AUT": "オーストリア",
    "BEL": "ベルギー",
    "CYP": "キプロス",
    "CZE": "チェコ",
    "DEU": "ドイツ",
    "DNK": "デンマーク",
    "ESP": "スペイン",
    "EST": "エストニア",
    "FIN": "フィンランド",
    "FRA": "フランス",
    "GBR": "英国",
    "GRC": "ギリシャ",
    "HUN": "ハンガリー",
    "IRL": "アイルランド",
    "ISL": "アイスランド",
    "ITA": "イタリア",
    "JPN": "日本",
    "KOR": "韓国",
    "LTU": "リトアニア",
    "LUX": "ルクセンブルク",
    "LVA": "ラトビア",
    "MLT": "マルタ",
    "NLD": "オランダ",
    "NOR": "ノルウェー",
    "POL": "ポーランド",
    "PRT": "ポルトガル",
    "SVK": "スロバキア",
    "SVN": "スロベニア",
    "SWE": "スウェーデン",
    "USA": "米国",
    "CAN": "カナダ",
}
V3_KINDS = ("recovery", "quantitative", "both", "neither")
TYPE_LABEL = {"N": "N (norm)", "C": "C (constraint)", "mixed": "mixed"}


# ---------------------------------------------------------------- pure helpers (tested)
def _ge(x: float, threshold: float) -> bool:
    """x >= threshold, robust to binary floating noise in differences of 2-decimal data."""
    return round(x - threshold, 9) >= 0


def classify_v1(
    first_ideal: float,
    last_ideal: float,
    first_gap: float,
    last_gap: float,
    *,
    n_max: float = N_IDEAL_MAX,
    drop: float = N_DROP,
    c_min: float = C_IDEAL_MIN,
    gap: float = C_GAP,
) -> str:
    """'N' / 'C' / 'mixed' by the pre-registered V1 rule (gap = ideal − period TFR)."""
    if not _ge(last_ideal, n_max) and _ge(first_ideal - last_ideal, drop):
        return "N"
    if _ge(last_ideal, c_min) and _ge(last_gap, gap) and round(last_gap - first_gap, 9) > 0:
        return "C"
    return "mixed"


def majority(types: Sequence[str], first: str, second: str) -> str:
    """`first` / `second` when it is held by more than half of `types`, else 'differs'."""
    n = len(types)
    if n == 0:
        return "undetermined"
    if 2 * sum(t == first for t in types) > n:
        return first
    if 2 * sum(t == second for t in types) > n:
        return second
    return "differs"


def order_decline(
    start: Mapping[str, float], end: Mapping[str, float], first: str
) -> tuple[float, float | None]:
    """(Σ Δ over orders observed in both, share of the first order in that Σ).

    The share is None when Σ Δ >= 0 (no decline to decompose)."""
    keys = sorted(set(start) & set(end))
    if first not in keys:
        raise ValueError(f"first order {first!r} missing")
    deltas = {k: end[k] - start[k] for k in keys}
    total = sum(deltas.values())
    if round(total, 9) >= 0:
        return total, None
    return total, deltas[first] / total


def classify_v2(first_share: float | None) -> str:
    if first_share is None:
        return "no_decline"
    if _ge(first_share, V2_FIRST_MIN):
        return "childlessness"
    if _ge(1.0 - first_share, V2_LATER_MIN):
        return "one_child"
    return "mixed"


def approx_order_tfr(tfr: float, births: Mapping[str, float]) -> dict[str, float]:
    """Order-specific TFR approximated as TFR × (births of order / Σ births of known order)."""
    total = sum(births.values())
    if total <= 0:
        raise ValueError("no births")
    return {k: tfr * v / total for k, v in births.items()}


def classify_v3(completed_last: float, completed_ref: float | None, min_tfr: float) -> str:
    """'recovery' / 'quantitative' / 'both' / 'neither' (quantitative needs the 1960 cohort)."""
    rec = _ge(completed_last - min_tfr, V3_RECOVERY)
    quant = (
        completed_ref is not None
        and _ge(completed_ref - completed_last, V3_DROP)
        and completed_last < V3_FLOOR
    )
    if rec and quant:
        return "both"
    if rec:
        return "recovery"
    if quant:
        return "quantitative"
    return "neither"


def period_min(tfr_by_year: Mapping[int, float], years: Sequence[int]) -> tuple[int, float] | None:
    """(year, value) of the lowest TFR among `years` (earliest year on ties); None if none."""
    obs = [(y, tfr_by_year[y]) for y in years if y in tfr_by_year]
    if not obs:
        return None
    return min(obs, key=lambda t: (t[1], t[0]))


def v4_verdict(v1_major: str, v2_major: str) -> str:
    if v1_major == "C":
        return "not_supported"
    if v1_major == "N":
        return "support" if v2_major == "childlessness" else "partial"
    return "differs"


def lead_order(shares: Sequence[float]) -> str:
    """'first' when the median first-order share of the decline is >= 50%, else 'later'."""
    if not shares:
        raise ValueError("no shares")
    return "first" if _ge(statistics.median(shares), V2_FIRST_MIN) else "later"


def final_stance(
    v1_major: str,
    *,
    n_names: Sequence[str],
    c_names: Sequence[str],
    lead: str,
    recovered: bool,
) -> str:
    """The pre-registered sentence (design H9 最終スタンスの文型)."""
    if v1_major == "N":
        a = "規範の崩れ"
    elif v1_major == "C":
        a = "実現の阻害"
    else:
        n = "・".join(n_names) or "なし"
        c = "・".join(c_names) or "なし"
        a = f"国で異なり、{n}は規範型・{c}は阻害型"
    b = "第 1 子の減少" if lead == "first" else "第 2 子以降の減少"
    r = "回復している" if recovered else "回復していない"
    return f"2 人未満への低下は{a}であり、低下の主役は{b}である。コーホートで見ると{r}。"


# ---------------------------------------------------------------- frames
def tfr_lookup(panel: pl.DataFrame) -> dict[tuple[str, int], float]:
    p = panel.filter(pl.col("tfr").is_not_null())
    return {
        (r["iso3"], r["year"]): float(r["tfr"])
        for r in p.select("iso3", "year", "tfr").iter_rows(named=True)
    }


def latest_tfr(panel: pl.DataFrame) -> dict[str, tuple[int, float]]:
    p = panel.filter(pl.col("tfr").is_not_null()).sort(["iso3", "year"])
    last = p.group_by("iso3", maintain_order=True).last()
    return {r["iso3"]: (r["year"], float(r["tfr"])) for r in last.iter_rows(named=True)}


def eu_ideal_points(
    ideals: pl.DataFrame, waves: Sequence[tuple[str, str, str]], metric: str
) -> dict[str, list[tuple[str, int, float]]]:
    """iso3 -> [(wave, survey_year, ideal)] in wave order (no imputation)."""
    out: dict[str, list[tuple[str, int, float]]] = {}
    for src, sex, age in waves:
        sub = ideals.filter(
            (pl.col("source") == src)
            & (pl.col("sex") == sex)
            & (pl.col("age_class") == age)
            & (pl.col("metric") == metric)
            & pl.col("value").is_not_null()
        ).sort("iso3")
        for r in sub.iter_rows(named=True):
            out.setdefault(r["iso3"], []).append(
                (f"{src}:{sex}{age}", int(r["survey_year"]), float(r["value"]))
            )
    return out


def jp_points(survey: pl.DataFrame, key: tuple[str, str]) -> list[tuple[str, int, float]]:
    metric, group = key
    sub = survey.filter((pl.col("metric") == metric) & (pl.col("group") == group)).sort(
        "survey_year"
    )
    return [
        (f"{metric}:{group}", int(r["survey_year"]), float(r["value"]))
        for r in sub.iter_rows(named=True)
    ]


@dataclass(frozen=True)
class V1Row:
    iso3: str
    label: str
    first_year: int
    first_ideal: float
    first_tfr: float
    last_year: int
    last_ideal: float
    last_tfr: float
    latest_tfr: float
    kind: str

    @property
    def first_gap(self) -> float:
        return self.first_ideal - self.first_tfr

    @property
    def last_gap(self) -> float:
        return self.last_ideal - self.last_tfr


def v1_rows(
    points: Mapping[str, Sequence[tuple[str, int, float]]],
    tfr: Mapping[tuple[str, int], float],
    latest: Mapping[str, tuple[int, float]],
    *,
    label: str = "",
    **thresholds: float,
) -> list[V1Row]:
    rows: list[V1Row] = []
    for iso3 in sorted(points):
        pts = [p for p in points[iso3] if (iso3, p[1]) in tfr]
        if len(pts) < 2 or iso3 not in latest or latest[iso3][1] >= TFR_MAX:
            continue
        (_, y0, i0), (_, y1, i1) = pts[0], pts[-1]
        t0, t1 = tfr[(iso3, y0)], tfr[(iso3, y1)]
        kind = classify_v1(i0, i1, i0 - t0, i1 - t1, **thresholds)
        rows.append(V1Row(iso3, label, y0, i0, t0, y1, i1, t1, latest[iso3][1], kind))
    return rows


def v1_points(
    ideals: pl.DataFrame,
    survey: pl.DataFrame,
    *,
    eu_waves: Sequence[tuple[str, str, str]] = EU_WAVES,
    eu_metric: str = IDEAL_PERSONAL,
    jp_key: tuple[str, str] = JP_PLANNED,
) -> dict[str, list[tuple[str, int, float]]]:
    pts = eu_ideal_points(ideals, eu_waves, eu_metric)
    pts["JPN"] = jp_points(survey, jp_key)
    return pts


def summarize_v1(rows: Sequence[V1Row]) -> tuple[str, dict[str, int]]:
    kinds = [r.kind for r in rows]
    counts = {k: kinds.count(k) for k in ("N", "C", "mixed")}
    return majority(kinds, "N", "C"), counts


def print_v1(rows: Sequence[V1Row]) -> None:
    print(
        "  iso3  first(yr ideal TFR gap)        last(yr ideal TFR gap)         "
        "d_ideal d_gap  TFR_latest type"
    )
    for r in rows:
        print(
            f"  {r.iso3}  {r.first_year} {r.first_ideal:.3f} {r.first_tfr:.3f} {r.first_gap:+.3f}"
            f"   {r.last_year} {r.last_ideal:.3f} {r.last_tfr:.3f} {r.last_gap:+.3f}"
            f"   {r.last_ideal - r.first_ideal:+.3f} {r.last_gap - r.first_gap:+.3f}"
            f"  {r.latest_tfr:.3f}  {TYPE_LABEL[r.kind]}"
        )


def jp_order_tfr(order: pl.DataFrame, year: int) -> dict[str, float]:
    sub = order.filter(
        (pl.col("metric") == "tfr_order")
        & (pl.col("year") == year)
        & pl.col("group").is_in(list(JP_ORDERS))
    )
    return {r["group"]: float(r["value"]) for r in sub.iter_rows(named=True)}


def kr_order_tfr(kr: pl.DataFrame, year: int) -> dict[str, float]:
    tfr = kr.filter(
        (pl.col("metric") == "tfr") & (pl.col("year") == year) & (pl.col("group") == "계")
    )
    b = kr.filter(
        (pl.col("metric") == "births")
        & (pl.col("year") == year)
        & pl.col("group").is_in(list(KR_ORDERS))
    )
    if tfr.height != 1 or b.height != len(KR_ORDERS):
        return {}
    births = {r["group"]: float(r["value"]) for r in b.iter_rows(named=True)}
    return approx_order_tfr(float(tfr["value"][0]), births)


def eu_order_tfr(eu: pl.DataFrame, iso3: str, year: int) -> dict[str, float]:
    sub = eu.filter(
        (pl.col("iso3") == iso3) & (pl.col("year") == year) & pl.col("order").is_in(list(EU_ORDERS))
    )
    return {r["order"]: float(r["tfr"]) for r in sub.iter_rows(named=True)}


def eu_unk(eu: pl.DataFrame, iso3: str, year: int) -> float | None:
    sub = eu.filter(
        (pl.col("iso3") == iso3) & (pl.col("year") == year) & (pl.col("order") == "UNK")
    )
    return float(sub["tfr"][0]) if sub.height else None


@dataclass(frozen=True)
class V2Row:
    iso3: str
    start: int
    end: int
    first_start: float
    first_end: float
    total_start: float
    total_end: float
    d_total: float
    share: float | None
    kind: str


def v2_row(
    iso3: str, start: int, end: int, a: Mapping[str, float], b: Mapping[str, float], first: str
) -> V2Row | None:
    if not a or not b:
        return None
    d, share = order_decline(a, b, first)
    return V2Row(
        iso3,
        start,
        end,
        a[first],
        b[first],
        sum(a.values()),
        sum(b.values()),
        d,
        share,
        classify_v2(share),
    )


def eu_complete_years(eu: pl.DataFrame, iso3: str) -> list[int]:
    """Years in which all four known orders (1, 2, 3, GE4) are observed for `iso3`."""
    sub = eu.filter(
        (pl.col("iso3") == iso3)
        & pl.col("order").is_in(list(EU_ORDERS))
        & pl.col("tfr").is_not_null()
    )
    counts = sub.group_by("year").agg(pl.len().alias("n")).filter(pl.col("n") == len(EU_ORDERS))
    return sorted(int(y) for y in counts["year"].to_list())


def v2_rows(
    start: int,
    *,
    jp: pl.DataFrame,
    kr: pl.DataFrame,
    eu: pl.DataFrame,
    missing: list[str] | None = None,
) -> list[V2Row]:
    """Order decomposition `start` -> latest complete year.

    European countries without all orders in `start` are appended to `missing`."""
    rows: list[V2Row] = []
    for iso3 in sorted(eu["iso3"].unique().to_list()):
        years = eu_complete_years(eu, iso3)
        if start not in years:
            if missing is not None:
                missing.append(iso3)
            continue
        end = years[-1]
        r = v2_row(
            iso3, start, end, eu_order_tfr(eu, iso3, start), eu_order_tfr(eu, iso3, end), "1"
        )
        if r:
            rows.append(r)
    jp_end = int(jp.filter(pl.col("metric") == "tfr_order")["year"].max())  # type: ignore[arg-type]
    r = v2_row("JPN", start, jp_end, jp_order_tfr(jp, start), jp_order_tfr(jp, jp_end), "第1子")
    if r:
        rows.append(r)
    kr_end = int(kr["year"].max())  # type: ignore[arg-type]
    r = v2_row("KOR", start, kr_end, kr_order_tfr(kr, start), kr_order_tfr(kr, kr_end), "첫째아")
    if r:
        rows.append(r)
    return rows


def print_v2(rows: Sequence[V2Row]) -> None:
    print("  iso3  window     TFR(Σorders)        1st-order TFR        ΔΣ      1st share  type")
    for r in rows:
        sh = "   n/a" if r.share is None else f"{r.share:6.1%}"
        print(
            f"  {r.iso3}  {r.start}->{r.end}  {r.total_start:.3f}->{r.total_end:.3f}"
            f"   {r.first_start:.3f}->{r.first_end:.3f}   {r.d_total:+.3f}   {sh}   {r.kind}"
        )


def summarize_v2(rows: Sequence[V2Row]) -> tuple[str, dict[str, int], list[float]]:
    dec = [r for r in rows if r.share is not None]
    kinds = [r.kind for r in dec]
    counts = {k: kinds.count(k) for k in ("childlessness", "one_child", "mixed")}
    shares = [float(r.share) for r in dec if r.share is not None]
    return majority(kinds, "childlessness", "one_child"), counts, shares


@dataclass(frozen=True)
class V3Row:
    iso3: str
    age: int
    c_first: float | None
    c_ref: float | None
    c_last: float
    tfr_at30: float | None
    min_year: int
    min_tfr: float
    kind: str


def jp_cohort_cum(order: pl.DataFrame, age: int) -> dict[int, float]:
    sub = order.filter(
        (pl.col("metric") == "cohort_cum_fertility") & (pl.col("group") == f"age {age}")
    )
    return {int(r["cohort"]): float(r["value"]) for r in sub.iter_rows(named=True)}


def eu_cohort_cum(coh: pl.DataFrame, iso3: str, age: int) -> dict[int, float]:
    sub = coh.filter(
        (pl.col("metric") == "cohort_cum") & (pl.col("iso3") == iso3) & (pl.col("age") == age)
    )
    return {int(r["cohort"]): float(r["value"]) for r in sub.iter_rows(named=True)}


def v3_row(
    iso3: str, cum: Mapping[int, float], tfr: Mapping[tuple[str, int], float], age: int
) -> V3Row | None:
    if V3_COHORT not in cum:
        return None
    years = list(range(V3_FIRST_COHORT + V3_PERIOD_AGE, V3_COHORT + V3_PERIOD_AGE + 1))
    by_year = {y: v for (i, y), v in tfr.items() if i == iso3}
    pm = period_min(by_year, years)
    if pm is None:
        return None
    c_last, c_ref = cum[V3_COHORT], cum.get(V3_REF_COHORT)
    return V3Row(
        iso3,
        age,
        cum.get(V3_FIRST_COHORT),
        c_ref,
        c_last,
        by_year.get(V3_COHORT + V3_PERIOD_AGE),
        pm[0],
        pm[1],
        classify_v3(c_last, c_ref, pm[1]),
    )


def v3_rows(
    age: int, *, jp: pl.DataFrame, coh: pl.DataFrame, tfr: Mapping[tuple[str, int], float]
) -> list[V3Row]:
    rows: list[V3Row] = []
    for iso3 in sorted(coh["iso3"].unique().to_list()):
        r = v3_row(iso3, eu_cohort_cum(coh, iso3, age), tfr, age)
        if r:
            rows.append(r)
    r = v3_row("JPN", jp_cohort_cum(jp, age), tfr, age)
    if r:
        rows.append(r)
    return rows


def later_sum(orders: Mapping[str, float], first: str) -> float | None:
    """Σ order-specific TFR over orders other than `first` (None for an empty mapping)."""
    return sum(v for g, v in orders.items() if g != first) if orders else None


def _f(x: float | None, fmt: str = ".3f") -> str:
    return "  n/a" if x is None else format(x, fmt)


def print_v3(rows: Sequence[V3Row]) -> None:
    print(
        "  iso3  CF1950  CF1960  CF1975  TFR@1975+30  min TFR (yr) 1980-2005  CF1975-min  "
        "CF1960-CF1975  type"
    )
    for r in rows:
        drop = None if r.c_ref is None else r.c_ref - r.c_last
        print(
            f"  {r.iso3}  {_f(r.c_first)}  {_f(r.c_ref)}  {r.c_last:.3f}  {_f(r.tfr_at30)}"
            f"        {r.min_tfr:.3f} ({r.min_year})          {r.c_last - r.min_tfr:+.3f}"
            f"      {_f(drop, '+.3f')}      {r.kind}"
        )


def v3_recovered(rows: Sequence[V3Row]) -> tuple[bool, int]:
    rec = sum(r.kind in ("recovery", "both") for r in rows)
    return 2 * rec > len(rows), rec


# ---------------------------------------------------------------- figures (English, byte-stable)
def _plt() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


KIND_COLOR = {"N": ORANGE, "C": BLUE_RAMP[3], "mixed": MUTED}


def fig_v1(rows: Sequence[V1Row], path: Path) -> None:
    plt = _plt()
    rs = sorted(rows, key=lambda r: (r.last_ideal, r.iso3))
    fig, ax = plt.subplots(figsize=(8.2, 7.2))
    for i, r in enumerate(rs):
        c = KIND_COLOR[r.kind]
        ax.plot([r.first_ideal, r.last_ideal], [i, i], color=c, linewidth=1.6)
        ax.scatter([r.first_ideal], [i], color="white", edgecolors=c, s=26, zorder=3)
        ax.scatter([r.last_ideal], [i], color=c, s=30, zorder=3)
        ax.scatter([r.last_tfr], [i], marker="x", color=INK, s=22, zorder=3)
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([f"{r.iso3} ({r.first_year}->{r.last_year})" for r in rs], fontsize=7.5)
    ax.axvline(N_IDEAL_MAX, color=ORANGE, linestyle=":", linewidth=1)
    ax.axvline(C_IDEAL_MIN, color=BLUE_RAMP[3], linestyle=":", linewidth=1)
    ax.set_xlabel(
        "mean ideal number of children (JPN: couples' planned number); "
        "x = period TFR at last survey",
        fontsize=8,
    )
    n = {k: sum(r.kind == k for r in rows) for k in KIND_COLOR}
    ax.set_title(
        f"H9 V1: first (open) -> latest (filled) ideal, TFR<1.6 countries (n={len(rows)}): "
        f"N {n['N']}, C {n['C']}, mixed {n['mixed']}",
        fontsize=9,
        color=INK,
    )
    _style(ax)
    fig.text(
        0.01,
        0.005,
        "Europe: EB 253 (2006, both sexes 25-39) -> EB 75.4 (2011, women 25-39; Testa 2012) -> "
        "GGS-II (2020-23, women 30-39; BiB 2025).\nJapan: IPSS Popular Data 2026 T04-25 "
        "(planned, couples). TFR: World Bank WDI. "
        "Orange = N type, dark blue = C type, grey = mixed.",
        fontsize=6.8,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)


def fig_japan(series: Mapping[str, Sequence[tuple[int, float]]], path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8, 4.6))
    styles = {
        "ideal (couples, JNFS)": (BLUE_RAMP[1], "o", "-"),
        "planned (couples, T04-25)": (ORANGE, "o", "-"),
        "children born (couples, T04-24)": (BLUE_RAMP[3], "s", "-"),
        "desired (unmarried women, JNFS)": (BLUE_RAMP[0], "^", "--"),
        "period TFR (T04-16)": (INK, "", "-"),
        "completed, cohort aged 45 (T04-11, plotted at cohort+30)": (MUTED, "", "--"),
    }
    for name, pts in series.items():
        c, m, ls = styles[name]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        ax.plot(
            xs,
            ys,
            color=c,
            marker=m or None,
            markersize=3.5,
            linestyle=ls,
            linewidth=1.3,
            label=name,
        )
    ax.axhline(2.0, color=MUTED, linewidth=0.6)
    ax.set_xlabel("year (survey year; cohort lines at birth year + 30)", fontsize=8)
    ax.set_ylabel("children per woman / couple", fontsize=8)
    ax.set_title(
        "H9: Japan - ideals and plans stay near 2 while the period TFR falls", fontsize=9, color=INK
    )
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    _style(ax)
    fig.text(
        0.01,
        0.005,
        "Source: IPSS, Popular Data 2026 (T04-11/16/24/25, PDL1.0); "
        "IPSS, 16th JNFS summary (Fig. 7-1, 3-3).",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)


def fig_v2(main: Sequence[V2Row], long: Sequence[V2Row], path: Path) -> None:
    plt = _plt()
    rs = sorted([r for r in main if r.share is not None], key=lambda r: (r.share or 0, r.iso3))
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    for i, r in enumerate(rs):
        share = float(r.share or 0)
        c = {"childlessness": ORANGE, "one_child": BLUE_RAMP[3], "mixed": MUTED}[r.kind]
        ax.barh(i, share, color=c, height=0.6)
        ax.text(share + 0.01, i, f"{share:.0%} (dTFR {r.d_total:+.2f})", va="center", fontsize=7)
    for r in long:
        if r.share is None:
            continue
        order = [x.iso3 for x in rs]
        if r.iso3 in order:
            ax.scatter([r.share], [order.index(r.iso3)], marker="D", color=INK, s=18, zorder=3)
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([f"{r.iso3} {r.start}->{r.end}" for r in rs], fontsize=7.5)
    ax.axvline(V2_FIRST_MIN, color=ORANGE, linestyle=":", linewidth=1)
    ax.axvline(1 - V2_LATER_MIN, color=BLUE_RAMP[3], linestyle=":", linewidth=1)
    ax.set_xlabel(
        "share of the period TFR decline due to first births (diamond = 1990->latest)", fontsize=8
    )
    ax.set_title(
        "H9 V2: first-birth share of the decline (orange >= 50% childlessness type, "
        "blue <= 40% one-child type)",
        fontsize=8.5,
        color=INK,
    )
    _style(ax)
    fig.text(
        0.01,
        0.005,
        "Source: Eurostat demo_fordagec/demo_pjan (order TFR); IPSS T04-16; "
        "KOSTAT 2025 birth statistics "
        f"(order shares x TFR, approx.). n={len(rs)} with a decline; DNK/FRA lack 2010, "
        "DEU (2010->2017)/HUN rose.",
        fontsize=6.8,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)


def fig_v3(rows: Sequence[V3Row], path: Path) -> None:
    plt = _plt()
    rs = sorted(rows, key=lambda r: (r.c_last, r.iso3))
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    for i, r in enumerate(rs):
        ax.plot([r.min_tfr, r.c_last], [i, i], color=MUTED, linewidth=1.2)
        ax.scatter([r.min_tfr], [i], color="white", edgecolors=INK, s=26, zorder=3)
        c = ORANGE if r.kind in ("recovery", "both") else BLUE_RAMP[3]
        ax.scatter([r.c_last], [i], color=c, s=30, zorder=3)
        if r.c_ref is not None:
            ax.scatter([r.c_ref], [i], marker="|", color=INK, s=60, zorder=3)
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([f"{r.iso3} ({r.kind})" for r in rs], fontsize=7.5)
    ax.axvline(V3_FLOOR, color=MUTED, linestyle=":", linewidth=1)
    ax.set_xlabel(
        "open = lowest period TFR 1980-2005; "
        f"filled = completed fertility of the 1975 cohort at {V3_AGE}; "
        "| = 1960 cohort",
        fontsize=7.5,
    )
    ax.set_title(
        "H9 V3: does the 1975 cohort recover what the period TFR lost?", fontsize=9, color=INK
    )
    _style(ax)
    fig.text(
        0.01,
        0.005,
        "Source: Eurostat demo_frate (cumulated ASFR); IPSS T04-11; World Bank WDI (period TFR). "
        "Orange = recovery (>= +0.3).",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)


def fig_childless(cl: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    sub = cl.filter(
        (pl.col("chart") == "SF2.5.A") & (pl.col("metric") == "childless_share_pct")
    ).sort(["iso3", "cohort"])
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    hi = {"JPN": ORANGE, "ITA": BLUE_RAMP[2], "ESP": BLUE_RAMP[1], "FIN": BLUE_RAMP[3], "USA": INK}
    for iso3 in sub["iso3"].unique().sort().to_list():
        s = sub.filter(pl.col("iso3") == iso3)
        c = hi.get(iso3, "#cfcfcf")
        ax.plot(
            s["cohort"],
            s["value"],
            color=c,
            linewidth=1.8 if iso3 in hi else 0.9,
            marker="o",
            markersize=2.5,
        )
        if iso3 in hi:
            ax.annotate(
                iso3,
                (int(s["cohort"][-1]), float(s["value"][-1])),
                fontsize=7.5,
                color=c,
                xytext=(3, 0),
                textcoords="offset points",
            )
    ax.set_xlabel("women's birth cohort", fontsize=8)
    ax.set_ylabel("childless at end of reproductive life (%)", fontsize=8)
    ax.set_title(
        f"H9 V2 aux: cohort childlessness, OECD SF2.5 (n={sub['iso3'].n_unique()} countries)",
        fontsize=9,
        color=INK,
    )
    _style(ax)
    fig.text(0.01, 0.005, "Source: OECD Family Database SF2.5 (Chart A).", fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150, metadata={"Software": None})
    plt.close(fig)


# ---------------------------------------------------------------- driver
@dataclass(frozen=True)
class H9Result:
    v1: list[V1Row]
    v1_major: str
    v2: list[V2Row]
    v2_long: list[V2Row]
    v2_major: str
    v2_shares: list[float]
    v3: list[V3Row]
    recovered: bool
    verdict: str
    stance: str


def load(data_dir: Path) -> dict[str, pl.DataFrame]:
    return {
        "panel": pl.read_parquet(data_dir / PANEL_MART),
        "ideals": pl.read_parquet(data_dir / IDEALS_MART),
        "survey": pl.read_parquet(data_dir / JP_SURVEY_MART),
        "jp": pl.read_parquet(data_dir / JP_ORDER_MART),
        "kr": pl.read_parquet(data_dir / KR_MART),
        "eu": pl.read_parquet(data_dir / EU_ORDER_MART),
        "coh": pl.read_parquet(data_dir / EU_COHORT_MART),
        "cl": pl.read_parquet(data_dir / OECD_CL_MART),
    }


def compute(d: Mapping[str, pl.DataFrame]) -> H9Result:
    """Main specification (no printing): used by the report run and the summary figures."""
    tfr, latest = tfr_lookup(d["panel"]), latest_tfr(d["panel"])
    v1 = v1_rows(v1_points(d["ideals"], d["survey"]), tfr, latest)
    v1_major, _ = summarize_v1(v1)
    v2 = v2_rows(V2_START, jp=d["jp"], kr=d["kr"], eu=d["eu"])
    v2_long = [
        r
        for r in v2_rows(V2_LONG_START, jp=d["jp"], kr=d["kr"], eu=d["eu"])
        if r.iso3 in ("JPN", "KOR")
    ]
    v2_major, _, shares = summarize_v2(v2)
    v3 = v3_rows(V3_AGE, jp=d["jp"], coh=d["coh"], tfr=tfr)
    recovered, _ = v3_recovered(v3)
    verdict = v4_verdict(v1_major, v2_major)
    stance = final_stance(
        v1_major,
        n_names=[COUNTRY_JA[r.iso3] for r in v1 if r.kind == "N"],
        c_names=[COUNTRY_JA[r.iso3] for r in v1 if r.kind == "C"],
        lead=lead_order(shares),
        recovered=recovered,
    )
    return H9Result(v1, v1_major, v2, v2_long, v2_major, shares, v3, recovered, verdict, stance)


def japan_series(d: Mapping[str, pl.DataFrame]) -> dict[str, list[tuple[int, float]]]:
    s, jp = d["survey"], d["jp"]

    def pts(k: tuple[str, str]) -> list[tuple[int, float]]:
        return [(y, v) for _, y, v in jp_points(s, k)]

    tfr = jp.filter(
        (pl.col("metric") == "tfr_order") & (pl.col("group") == "総数") & (pl.col("year") >= 1977)
    )
    born = jp_points(s, ("children_born", "総数"))
    cum = jp_cohort_cum(jp, V3_AGE)
    return {
        "ideal (couples, JNFS)": pts(JP_IDEAL),
        "planned (couples, T04-25)": pts(JP_PLANNED),
        "children born (couples, T04-24)": [(y, v) for _, y, v in born],
        "desired (unmarried women, JNFS)": pts(JP_SINGLE_F),
        "period TFR (T04-16)": [
            (int(r["year"]), float(r["value"])) for r in tfr.sort("year").iter_rows(named=True)
        ],
        "completed, cohort aged 45 (T04-11, plotted at cohort+30)": [
            (c + V3_PERIOD_AGE, v) for c, v in sorted(cum.items()) if c + V3_PERIOD_AGE >= 1977
        ],
    }


def describe_data(d: Mapping[str, pl.DataFrame]) -> None:
    print("== Data ==")
    for k, df in d.items():
        print(f"  {k}: rows={df.height} cols={df.width}")
    s = d["survey"]
    print(
        s.group_by("metric", "group")
        .agg(
            pl.len().alias("n"),
            pl.col("survey_year").min().alias("from"),
            pl.col("survey_year").max().alias("to"),
        )
        .sort("metric", "group")
    )
    i = d["ideals"].filter(pl.col("metric") == IDEAL_PERSONAL)
    print(
        i.group_by("source", "sex", "age_class")
        .agg(pl.col("iso3").n_unique().alias("countries"))
        .sort("source", "sex", "age_class")
    )


def section_v1(
    d: Mapping[str, pl.DataFrame], res: H9Result, fig_dir: Path
) -> list[tuple[str, str, dict[str, int]]]:
    tfr, latest = tfr_lookup(d["panel"]), latest_tfr(d["panel"])
    # ---------------- V1
    print("\n== V1: norms (N) vs constraints (C) — main ==")
    pts = v1_points(d["ideals"], d["survey"])
    excluded = sorted(
        k for k, v in pts.items() if len(v) >= 2 and k in latest and latest[k][1] >= TFR_MAX
    )
    single = sorted(k for k, v in pts.items() if len(v) < 2)
    print(f"  excluded (latest TFR >= {TFR_MAX}): {excluded}; only one ideal point: {single}")
    for iso3 in sorted(pts):
        if iso3 in [r.iso3 for r in res.v1]:
            mid = ", ".join(f"{w}@{y}={v:.3f}" for w, y, v in pts[iso3])
            print(f"    {iso3}: {mid}")
    print_v1(res.v1)
    major, counts = summarize_v1(res.v1)
    print(f"  counts: {counts} of {len(res.v1)} -> V1 majority: {major}")
    lo = [r.iso3 for r in res.v1 if r.last_ideal < 2.0]
    hi = [r.iso3 for r in res.v1 if _ge(r.last_ideal, C_IDEAL_MIN)]
    print(f"  latest ideal < 2.0: {len(lo)} {lo}; >= {C_IDEAL_MIN}: {len(hi)} {hi}")
    jp_ideal = v1_rows({"JPN": jp_points(d["survey"], JP_IDEAL)}, tfr, latest)
    print("  Japan, ideal (couples) shown alongside the planned number:")
    print_v1(jp_ideal)
    fig_v1(res.v1, fig_dir / "h9_01_v1_ideals.png")

    print("\n-- V1 robustness (pre-registered) --")
    grid: list[tuple[str, str, dict[str, int]]] = []
    for n_max in (2.0, 2.1, 2.2):
        for gap in (0.5, 0.6, 0.8):
            rr = v1_rows(pts, tfr, latest, n_max=n_max, gap=gap)
            m, c = summarize_v1(rr)
            grid.append((f"N<{n_max} gap>={gap}", m, c))
    for lab, m, c in grid:
        print(f"  thresholds {lab}: {c} -> {m}")
    variants = {
        "EU general ideal (EB2006 T25-39 -> EB2011 F25-39)": v1_points(
            d["ideals"], d["survey"], eu_waves=EU_WAVES_GENERAL, eu_metric=IDEAL_GENERAL
        ),
        "JP ideal of wives < 35 (couples)": {**pts, "JPN": jp_points(d["survey"], JP_IDEAL_U35)},
        "JP planned of wives < 35 (PDF)": {**pts, "JPN": jp_points(d["survey"], JP_PLANNED_U35)},
        "JP planned from PDF (couples)": {**pts, "JPN": jp_points(d["survey"], JP_PLANNED_PDF)},
        "JP ideal (couples) instead of planned": {**pts, "JPN": jp_points(d["survey"], JP_IDEAL)},
        "EB2006 women all ages instead of both sexes 25-39": v1_points(
            d["ideals"], d["survey"], eu_waves=EU_WAVES_F2006
        ),
    }
    for lab, p in variants.items():
        rr = v1_rows(p, tfr, latest)
        m, c = summarize_v1(rr)
        jp = next((r.kind for r in rr if r.iso3 == "JPN"), "n/a")
        changed = [
            f"{r.iso3}:{r.kind}"
            for r in rr
            if r.kind != next((x.kind for x in res.v1 if x.iso3 == r.iso3), None)
        ]
        print(f"  {lab}: {c} -> {m}; JPN={jp}; changed types: {changed}")
        if lab.startswith("EU general"):
            print_v1(rr)

    return grid


def section_v2(d: Mapping[str, pl.DataFrame], res: H9Result, fig_dir: Path) -> None:
    latest = latest_tfr(d["panel"])
    # ---------------- V2
    print("\n== V2: first births (childlessness) or later births (one-child) — main window ==")
    miss: list[str] = []
    v2_rows(V2_START, jp=d["jp"], kr=d["kr"], eu=d["eu"], missing=miss)
    print(f"  European countries without all four orders in {V2_START} (not evaluable): {miss}")
    print_v2(res.v2)
    m2, c2, shares = summarize_v2(res.v2)
    print(
        f"  counts: {c2} of {len(shares)} declining -> V2 majority: {m2}; "
        f"median first share {statistics.median(shares):.1%} -> lead: {lead_order(shares)}"
    )
    print("  long window (JPN, KOR):")
    print_v2(res.v2_long)
    sub16 = [r for r in res.v2 if r.share is not None and latest.get(r.iso3, (0, 9.0))[1] < TFR_MAX]
    m16 = majority([r.kind for r in sub16], "childlessness", "one_child")
    print(f"  subset latest TFR < {TFR_MAX}: n={len(sub16)} -> {m16}")
    kr_unk = d["kr"].filter(
        (pl.col("metric") == "births") & pl.col("year").is_in([1990, 2010, 2025])
    )
    for y in (1990, 2010, 2025):
        tot = float(kr_unk.filter((pl.col("year") == y) & (pl.col("group") == "계"))["value"][0])
        known = float(
            kr_unk.filter((pl.col("year") == y) & (pl.col("group") != "계"))["value"].sum()
        )
        print(
            f"  KOR {y}: births total {tot:.0f}, known order {known:.0f} "
            f"(unknown {tot - known:.0f})"
        )
    for r in res.v2:
        if r.iso3 in ("JPN", "KOR"):
            continue
        u0, u1 = eu_unk(d["eu"], r.iso3, r.start), eu_unk(d["eu"], r.iso3, r.end)
        if u0 or u1:
            print(f"  {r.iso3} unknown-order TFR {r.start} {_f(u0)} -> {r.end} {_f(u1)}")
    print("-- V2 robustness: start year --")
    for s in V2_ALT_STARTS:
        miss_s: list[str] = []
        rr = v2_rows(s, jp=d["jp"], kr=d["kr"], eu=d["eu"], missing=miss_s)
        print(f"  start {s}: not evaluable {miss_s}")
        print_v2(rr)
        m, c, sh = summarize_v2(rr)
        print(
            f"  start {s}: {c} -> {m}; median share {statistics.median(sh):.1%} "
            f"-> lead {lead_order(sh)}"
        )
    print("-- V2 auxiliary: OECD SF2.5 childlessness (%), 1955 -> 1975 cohort --")
    cl = d["cl"].filter(
        (pl.col("chart") == "SF2.5.A") & (pl.col("metric") == "childless_share_pct")
    )
    w = cl.pivot(on="cohort", index="iso3", values="value", sort_columns=True).sort("iso3")
    rises = []
    for row in w.iter_rows(named=True):
        a, b = row.get(str(OECD_FROM)), row.get(str(OECD_TO))
        if a is not None and b is not None:
            rises.append((row["iso3"], a, b, b - a))
            print(f"  {row['iso3']}: {a:.1f} -> {b:.1f} ({b - a:+.1f} pt)")
    if rises:
        print(f"  n={len(rises)}, median rise {statistics.median([x[3] for x in rises]):+.1f} pt")
    jpn = w.filter(pl.col("iso3") == "JPN").row(0, named=True)
    print(
        "  JPN all cohorts: "
        + ", ".join(f"{k}={v}" for k, v in jpn.items() if k != "iso3" and v is not None)
    )
    fig_v2(res.v2, res.v2_long, fig_dir / "h9_03_v2_birth_order.png")
    fig_childless(d["cl"], fig_dir / "h9_05_childlessness.png")


def section_v3(d: Mapping[str, pl.DataFrame], res: H9Result, fig_dir: Path) -> None:
    tfr = tfr_lookup(d["panel"])
    # ---------------- V3
    print(f"\n== V3: cohort recovery (completed at {V3_AGE}) ==")
    print_v3(res.v3)
    rec, n_rec = v3_recovered(res.v3)
    kinds3 = [r.kind for r in res.v3]
    print(
        f"  types: { {k: kinds3.count(k) for k in V3_KINDS} } "
        f"-> recovered (majority recovery/both): {rec} ({n_rec}/{len(res.v3)})"
    )
    print("-- V3 robustness: truncation age 40 (and Japan 49) --")
    r40 = v3_rows(40, jp=d["jp"], coh=d["coh"], tfr=tfr)
    print_v3(r40)
    print(f"  age 40: recovered={v3_recovered(r40)}")
    r49 = v3_row("JPN", jp_cohort_cum(d["jp"], 49), tfr, 49)
    if r49:
        print_v3([r49])
    print(
        "-- V3 robustness (not pre-registered, reported for transparency): vs TFR at age 30 only --"
    )
    for r in res.v3:
        if r.tfr_at30 is not None:
            print(f"  {r.iso3}: CF1975 − TFR(2005) = {r.c_last - r.tfr_at30:+.3f}")
    n30 = sum(r.tfr_at30 is not None and _ge(r.c_last - r.tfr_at30, V3_RECOVERY) for r in res.v3)
    print(f"  >= {V3_RECOVERY}: {n30}/{len(res.v3)}")
    fig_v3(res.v3, fig_dir / "h9_04_v3_cohort.png")
    fig_japan(japan_series(d), fig_dir / "h9_02_japan_series.png")


def section_v4(
    d: Mapping[str, pl.DataFrame],
    res: H9Result,
    fig_dir: Path,
    grid: Sequence[tuple[str, str, dict[str, int]]],
) -> None:
    # ---------------- V4
    print("\n== V4: overall ==")
    print(
        f"  V1 majority: {res.v1_major}; V2 majority: {res.v2_major}; V3 recovered: {res.recovered}"
    )
    print(f"  verdict on part4's final hypothesis (norm collapse + postponement): {res.verdict}")
    print(f"  FINAL STANCE: {res.stance}")
    print("-- V4 cross-tab: V1 type x V2 type (2010 window; JPN/KOR long window in brackets) --")
    v2k = {r.iso3: r.kind for r in res.v2}
    v2l = {r.iso3: r.kind for r in res.v2_long}
    v1k = {r.iso3: r.kind for r in res.v1}
    for iso3 in sorted(set(v1k) | set(v2k)):
        long_s = f" [{v2l[iso3]}]" if iso3 in v2l else ""
        print(
            f"  {iso3}: V1 {v1k.get(iso3, 'n/a (no ideal series)')}; "
            f"V2 {v2k.get(iso3, 'n/a')}{long_s}"
        )
    print("-- V4 under the V1/V2 robustness variants --")
    for lab, m, _c in grid:
        print(f"  {lab}: V1 {m} -> {v4_verdict(m, res.v2_major)}")
    for s in V2_ALT_STARTS:
        m, _c, _sh = summarize_v2(v2_rows(s, jp=d["jp"], kr=d["kr"], eu=d["eu"]))
        print(f"  V2 start {s}: V2 {m} -> {v4_verdict(res.v1_major, m)}")


def section_exploratory(d: Mapping[str, pl.DataFrame], res: H9Result, fig_dir: Path) -> None:
    tfr, latest = tfr_lookup(d["panel"]), latest_tfr(d["panel"])
    # ---------------- exploratory
    print("\n== Exploratory (not pre-registered; outside the verdict) ==")
    print(
        "-- E1: V1 restricted to countries whose latest ideal is from the 2020s (GGS) or Japan --"
    )
    e1 = [r for r in res.v1 if r.last_year >= 2020]
    print_v1(e1)
    print(f"  E1: {summarize_v1(e1)}")
    print("-- E2: Japan, unmarried women's desired number (1982 -> 2021) under the V1 rule --")
    e2 = v1_rows({"JPN": jp_points(d["survey"], JP_SINGLE_F)}, tfr, latest)
    print_v1(e2)
    um = jp_points(d["survey"], ("desired_children_single", "未婚男性"))
    print("  unmarried men: " + ", ".join(f"{y}={v:.2f}" for _, y, v in um))
    print("-- E3: Japan, married couples' completed (T04-23) vs all women (T04-11 at 45) --")
    t23 = d["survey"].filter(pl.col("metric") == "completed_fertility").sort("birth_cohort")
    cum45 = jp_cohort_cum(d["jp"], 45)
    for r in t23.filter(pl.col("birth_cohort") >= 1950).iter_rows(named=True):
        c = int(r["birth_cohort"])
        pop = cum45.get(c)
        print(
            f"  cohort {r['group']}: couples {r['value']:.2f}; "
            f"all women at 45 (cohort {c}) {_f(pop)}"
        )
    shares_t23 = (
        d["survey"]
        .filter((pl.col("metric") == "completed_parity_share") & (pl.col("survey_year") >= 2002))
        .sort("survey_year", "group")
    )
    print(shares_t23.select("survey_year", "group", "value"))
    print("-- E4: OECD SF2.5 Chart B, 1975 cohort: childlessness vs completed fertility --")
    b = (
        d["cl"]
        .filter(pl.col("chart") == "SF2.5.B")
        .pivot(on="metric", index="iso3", values="value")
        .drop_nulls()
    )
    rho = spearman(b["childless_share_pct"].to_numpy(), b["completed_fertility"].to_numpy())
    r_p = float(
        np.corrcoef(b["childless_share_pct"].to_numpy(), b["completed_fertility"].to_numpy())[0, 1]
    )
    print(f"  n={b.height}: Spearman {rho:+.3f}, Pearson {r_p:+.3f}")
    print(b.sort("childless_share_pct"))
    print("-- E5: Japan and Korea, first-order TFR level by year --")
    for y in (1990, 2000, 2005, 2010, 2015, 2020, 2024):
        j = jp_order_tfr(d["jp"], y)
        k = kr_order_tfr(d["kr"], y)
        print(
            f"  {y}: JPN 1st {_f(j.get('第1子'))} 2nd+ {_f(later_sum(j, '第1子'))}"
            f" | KOR 1st {_f(k.get('첫째아'))} 2nd+ {_f(later_sum(k, '첫째아'))}"
        )


def run(data_dir: Path, fig_dir: Path) -> H9Result:
    pl.Config.set_tbl_rows(-1)
    pl.Config.set_tbl_width_chars(200)
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = load(data_dir)
    print("== Operational choices fixed before the first run ==")
    print(
        f"  JP main V1 series: {JP_PLANNED} (xlsx T04-25 total); PDF {JP_PLANNED_PDF} = robustness"
    )
    print(f"  JP ideal {JP_IDEAL}: shown, not the main verdict")
    print(f"  EU waves (personal ideal): {EU_WAVES}; 2006 alt = {EU_WAVES_F2006[0]}")
    print(f"  V2 type window: {V2_START} -> latest (JPN/KOR {V2_LONG_START} -> latest shown)")
    print(
        f"  V3: completed at age {V3_AGE}; period min over {V3_FIRST_COHORT + V3_PERIOD_AGE}-"
        f"{V3_COHORT + V3_PERIOD_AGE}"
    )
    describe_data(d)
    res = compute(d)
    grid = section_v1(d, res, fig_dir)
    section_v2(d, res, fig_dir)
    section_v3(d, res, fig_dir)
    section_v4(d, res, fig_dir, grid)
    section_exploratory(d, res, fig_dir)
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
