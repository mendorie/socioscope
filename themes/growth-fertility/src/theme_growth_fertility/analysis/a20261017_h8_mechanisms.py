"""H8: 死亡率低下と女子教育は「どの仕組みで」出生率を下げるのか（M1〜M5、最終回）。

事前登録: design/themes/growth-fertility.md「### H8」（2026-10-17）、
docs/specs/growth-fertility-h8-mechanisms.md
（§2 推定量、§3 T1〜T6・判定・スコアカード・文型、§4 頑健性）。
判定基準は固定:
  T1 s_w = ΣΔwanted/ΣΔTFR（ΔTFR<0 の組）      >= 0.6 望む数が主 / <= 0.4 M5 支持 / 間 M5 部分的
  T2(c) tfr ~ ln u5mr + sec + 国FE + 年トレンド  b >= 0.25 (CI∌0) M1 支持 / 0.10–0.25 部分的
  T3 初婚年齢 Sec−None >= +2 年の調査割合, s_m   >= 70% & s_m >= .25 支持 / >= 50% & .10–.25 部分的
  T4 調査 FE + 学歴: g_w, g_u（Sec − None）      g_w <= −1 (CI∌0) & |g_w| >= 2|g_u| M3 支持 …
  T5 学歴 × ln u5mr_s の γ(Sec) − γ(None)        > 0, CI∌0, 150→30 の広がり >= 0.3 M4 支持 …
  T6 WDI 10 年長期差分（国＋期間 FE、標準化）     段階 2（開始 TFR < 3）の |係数| 最大で主役を決める

決定的スクリプト。入力は data/marts/{dhs_mechanisms, growth_fertility_panel, eu_tfr_by_education,
eu_census_marital_by_education, jp_income_age_marital}.parquet。乱数・現在時刻は使わない。
欠損は補完しない（listwise）。SE は国クラスタ。識別戦略は固定効果・分解・調査内比較のみ。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋ヘルパ（bongaarts_cm, tfr_from_asfr, ratio_of_sums, chain_pairs, trim_smam, nearest_value,
long_diff_nearest, verdict_*, score_mechanisms, stage2_leader, final_hypothesis）は
tests/test_analysis_h8.py で検証する。
"""

from __future__ import annotations

import argparse
import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis.a20261004_h1_income_tfr import (
    BLUE_RAMP,
    INK,
    MUTED,
    OIL_STATES,
    ORANGE,
    SMALL_POP,
    Est,
    _style,
    fit,
)

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
DHS_MART = Path("marts") / "dhs_mechanisms.parquet"
PANEL_MART = Path("marts") / "growth_fertility_panel.parquet"

EDU = ("No education", "Primary", "Secondary", "Higher")
EDU_DUMMY = {"Primary": "e_pri", "Secondary": "e_sec", "Higher": "e_hi"}
AGES = (15, 20, 25, 30, 35, 40, 45)
ASFR = tuple(f"asfr_{a}" for a in AGES)
IU = tuple(f"iu_{a}" for a in AGES)
TOTAL_CATS = ("Total", "Total 15-49", "Total 25-49")
U5_BY = {"Five years preceding the survey": "u5_5", "Ten years preceding the survey": "u5_10"}
SOUTHERN_AFRICA = frozenset({"BWA", "LSO", "NAM", "SWZ", "ZAF"})
LATAM = "Latin America & Caribbean"
T6_VARS = ("d_ln_u5", "d_sec", "d_smam", "d_ln_gdp")
T6_LABEL = {
    "d_ln_u5": "ln U5MR",
    "d_sec": "female sec. enrolment",
    "d_smam": "female mean age at marriage",
    "d_ln_gdp": "ln GDP pc (const.)",
    "d_m18": "married by 18 (%)",
    "d_contra": "contraceptive use (%)",
}
DHS_SOURCE = "Source: DHS Program Indicator Data API (ICF), cite per dhs.LICENSE."
WDI_SOURCE = "Source: World Bank WDI (CC BY 4.0); SMAM from UN World Marriage Data via WDI."


# ---------------------------------------------------------------- pure helpers (tested)
def _x(v: Any) -> float:
    """polars scalar aggregate -> float (None -> 0.0; only used on non-empty columns)."""
    return 0.0 if v is None else float(v)


def tfr_from_asfr(asfr: Sequence[float]) -> float:
    """TFR = 5 * sum(ASFR per 1,000 women) / 1000."""
    return 5.0 * sum(asfr) / 1000.0


def bongaarts_cm(
    in_union_pct: Sequence[float | None], asfr: Sequence[float | None]
) -> float | None:
    """Bongaarts marriage index Cm = Σ m_a f_a / Σ f_a over the 7 five-year age groups.

    m_a is the % of women in a union (married or cohabiting), f_a the ASFR. Any missing group
    (or a zero ASFR total) -> None: no imputation.
    """
    if len(in_union_pct) != len(AGES) or len(asfr) != len(AGES):
        return None
    if any(v is None for v in in_union_pct) or any(v is None for v in asfr):
        return None
    m = [float(v) / 100.0 for v in in_union_pct if v is not None]
    f = [float(v) for v in asfr if v is not None]
    den = sum(f)
    if den <= 0:
        return None
    return sum(a * b for a, b in zip(m, f, strict=True)) / den


def ratio_of_sums(
    num: Sequence[float], den: Sequence[float], weights: Sequence[float] | None = None
) -> float:
    """Σ w·num / Σ w·den (the pooled share used by s_w and s_m)."""
    w = list(weights) if weights is not None else [1.0] * len(num)
    d = sum(wi * di for wi, di in zip(w, den, strict=True))
    if d == 0:
        raise ValueError("denominator sums to zero")
    return sum(wi * ni for wi, ni in zip(w, num, strict=True)) / d


def chain_pairs(years: Sequence[int], min_gap: int) -> list[tuple[int, int]]:
    """Greedy non-overlapping chain of survey indices (sorted by year): from survey i the
    partner is the first later survey at least `min_gap` years after it; the chain then
    continues from that partner. Returns index pairs."""
    out: list[tuple[int, int]] = []
    i = 0
    while i < len(years):
        j = next((k for k in range(i + 1, len(years)) if years[k] - years[i] >= min_gap), None)
        if j is None:
            break
        out.append((i, j))
        i = j
    return out


def trim_smam(
    rows: pl.DataFrame, *, col: str = "smam_fe", min_obs: int = 3, max_dev: float = 4.0
) -> tuple[pl.DataFrame, int]:
    """Pre-registered SMAM cleaning: in countries with >= min_obs observations, set to null the
    values at least `max_dev` years from the country median. Returns (frame, n_dropped)."""
    stats = (
        rows.filter(pl.col(col).is_not_null())
        .group_by("iso3")
        .agg(pl.col(col).median().alias("_med"), pl.col(col).count().alias("_n"))
    )
    out = rows.join(stats, on="iso3", how="left")
    bad = (
        pl.col(col).is_not_null()
        & (pl.col("_n") >= min_obs)
        & ((pl.col(col) - pl.col("_med")).abs() >= max_dev)
    )
    n_bad = int(out.select(bad.sum()).item() or 0)
    out = out.with_columns(pl.when(bad).then(None).otherwise(pl.col(col)).alias(col))
    return out.drop("_med", "_n"), n_bad


def nearest_value(obs: Mapping[int, float], target: int, window: int) -> float | None:
    """Observed value at the year nearest to `target` within ±window (tie -> earlier year)."""
    for dist in range(window + 1):
        for y in (target - dist, target + dist):
            if y in obs:
                return obs[y]
    return None


def long_diff_nearest(
    panel: pl.DataFrame,
    cols: Sequence[str],
    *,
    width: int,
    start: int = 1970,
    end: int = 2020,
    window: int = 2,
) -> pl.DataFrame:
    """Non-overlapping `width`-year differences per iso3, periods start, start+width, ... with
    p + width <= end. Endpoint value = observation nearest to the endpoint year within ±window
    (SMAM etc. are irregular; annual series resolve to the exact year). Columns: iso3, period,
    <c>_0 (start value), d_<c>. Rows with any endpoint missing keep null (listwise later)."""
    obs: dict[str, dict[str, dict[int, float]]] = {c: {} for c in cols}
    for c in cols:
        for iso, year, v in panel.select("iso3", "year", c).drop_nulls().iter_rows():
            obs[c].setdefault(str(iso), {})[int(year)] = float(v)
    isos = sorted(set(panel["iso3"].to_list()))
    rows: list[dict[str, Any]] = []
    for iso in isos:
        for p in range(start, end - width + 1, width):
            row: dict[str, Any] = {"iso3": iso, "period": p}
            for c in cols:
                series = obs[c].get(iso, {})
                a = nearest_value(series, p, window)
                b = nearest_value(series, p + width, window)
                row[f"{c}_0"] = a
                row[f"d_{c}"] = None if a is None or b is None else b - a
            rows.append(row)
    schema: dict[str, Any] = {"iso3": pl.Utf8, "period": pl.Int64}
    for c in cols:
        schema[f"{c}_0"] = pl.Float64
        schema[f"d_{c}"] = pl.Float64
    return pl.DataFrame(rows, schema=schema, orient="row")


def verdict_t1(s_w: float) -> str:
    """'wanted' (望む数の低下が主), 'm5' (M5 支持), 'mixed' (M5 部分的支持)."""
    if s_w >= 0.6:
        return "wanted"
    if s_w <= 0.4:
        return "m5"
    return "mixed"


def verdict_m1(b: float, lo: float, hi: float) -> str:
    if lo > 0 and b >= 0.25:
        return "support"
    if lo > 0 and 0.10 <= b < 0.25:
        return "partial"
    return "no"


def verdict_m2(share_ge2: float, s_m: float) -> str:
    if share_ge2 >= 0.7 and s_m >= 0.25:
        return "support"
    if share_ge2 >= 0.5 and s_m >= 0.10:
        return "partial"
    return "no"


def verdict_m3(g_w: float, hi_w: float, g_u: float) -> tuple[str, bool]:
    """Returns (M3 verdict, M5 support from T4)."""
    if abs(g_u) >= abs(g_w):
        return "no", True
    if g_w <= -1.0 and hi_w < 0 and abs(g_w) >= 2 * abs(g_u):
        return "support", False
    if g_w <= -0.5:
        return "partial", False
    return "no", False


def widening(gamma: float, u_hi: float = 150.0, u_lo: float = 30.0) -> float:
    """How much the (negative) Secondary − None gradient widens when U5MR falls u_hi -> u_lo,
    given gradient(u) = g0 + gamma * ln u: gradient(u_hi) − gradient(u_lo) = gamma·ln(u_hi/u_lo)."""
    return gamma * math.log(u_hi / u_lo)


def verdict_m4(gamma: float, lo: float, hi: float) -> str:
    w = widening(gamma)
    if gamma > 0 and lo > 0 and w >= 0.3:
        return "support"
    if gamma > 0 and (lo <= 0 or 0.1 <= w < 0.3):
        return "partial"
    return "no"


def verdict_m5(t1: str, t4_m5: bool) -> str:
    """Both T1 and T4 support -> support; one -> partial; T1 'mixed' alone -> partial (§3 T1)."""
    hits = int(t1 == "m5") + int(t4_m5)
    if hits == 2:
        return "support"
    if hits == 1 or t1 == "mixed":
        return "partial"
    return "no"


def score_mechanisms(
    *,
    s_w: float,
    t2c: tuple[float, float, float],
    share_ge2: float,
    s_m: float,
    g_w: tuple[float, float],
    g_u: float,
    gamma: tuple[float, float, float],
) -> dict[str, str]:
    """Pre-registered scorecard (spec §3). t2c, gamma = (b, lo, hi); g_w = (b, hi)."""
    m3, t4_m5 = verdict_m3(g_w[0], g_w[1], g_u)
    return {
        "M1": verdict_m1(*t2c),
        "M2": verdict_m2(share_ge2, s_m),
        "M3": m3,
        "M4": verdict_m4(*gamma),
        "M5": verdict_m5(verdict_t1(s_w), t4_m5),
    }


def stage2_leader(
    coefs: Mapping[str, tuple[float, float, float, float]],
) -> tuple[str | None, float]:
    """Largest |standardised coefficient| among those whose CI excludes 0 (None if none does);
    second value = its share of Σ|b| over all variables."""
    sig = {k: v for k, v in coefs.items() if v[2] > 0 or v[3] < 0}
    total = sum(abs(v[0]) for v in coefs.values())
    if not sig or total == 0:
        return None, 0.0
    k = sorted(sig, key=lambda n: (-abs(sig[n][0]), n))[0]
    return k, abs(sig[k][0]) / total


def kitagawa(
    r0: Sequence[float], r1: Sequence[float], p0: Sequence[float], p1: Sequence[float]
) -> tuple[float, float]:
    """Kitagawa decomposition of Δ(Σ p_e r_e) into (rate part, composition part):
    Σ (r1 − r0)·(p0 + p1)/2 and Σ (p1 − p0)·(r0 + r1)/2. The two sum exactly to the change."""
    rate = sum((b - a) * (c + d) / 2 for a, b, c, d in zip(r0, r1, p0, p1, strict=True))
    comp = sum((d - c) * (a + b) / 2 for a, b, c, d in zip(r0, r1, p0, p1, strict=True))
    return rate, comp


def m3_qualifier(composition_share: float, s_w: float) -> str:
    """E10 (exploratory) limit on M3's quantity, inserted right after 「（M3）が担い」:
    composition share of the wanted-TFR fall, and of the TFR fall (s_w × share)."""
    return (
        f"（ただし量としては、学歴構成の変化で説明できるのは望む出生の低下の{_wari(composition_share)}、"
        f"TFR 低下の{_wari(s_w * composition_share)}にとどまる）"
    )


def _wari(x: float) -> str:
    return f"約 {round(x * 10)} 割（{x:.0%}）"


STAGE1_NAME = {
    "M1": "子どもの死亡率の低下（M1、保険としての多産が要らなくなる）",
    "M3": "女子教育による『望む数』の低下（M3）",
    "M5": "望まない出生の減少（M5、家族計画）",
}
STAGE2_NAME = {
    "d_smam": "女性の結婚が遅れること（M2、初婚年齢の上昇）",
    "d_sec": "女子の就学の広がり（M3 の経路）",
    "d_ln_u5": "子どもの死亡率の低下（M1）",
    "d_ln_gdp": "所得の上昇（豊かさ）",
}
VERDICT_JA = {"support": "支持", "partial": "部分的支持", "no": "不支持"}


def stage1_actors(
    verdicts: Mapping[str, str], m1_contrib: float, m3_contrib: float
) -> tuple[str, str | None]:
    """Main and secondary stage-1 actor among M1/M3 (used when s_w >= 0.5).

    Spec §3: the main actor is chosen among mechanisms that got 「支持」; M1 vs M3 by
    |quantity|. If neither or both are supported, quantity decides; the other is named as
    secondary only if it got at least 「部分的支持」."""
    sup = [m for m in ("M1", "M3") if verdicts.get(m) == "support"]
    by_qty = ("M1", "M3") if abs(m1_contrib) >= abs(m3_contrib) else ("M3", "M1")
    main = sup[0] if len(sup) == 1 else by_qty[0]
    other = "M3" if main == "M1" else "M1"
    return main, (other if verdicts.get(other) in ("support", "partial") else None)


def final_hypothesis(
    *,
    s_w: float,
    m1_contrib: float,
    m3_contrib: float,
    s_m: float,
    leader2: str | None,
    share2: float,
    u5_sig2: bool,
    verdicts: Mapping[str, str],
    composition_share: float | None = None,
) -> str:
    """Fill the pre-registered sentence (spec §0 / §3 末尾). Contributions are TFR changes
    (negative = lowers TFR)."""
    if s_w >= 0.5:
        main, sub = stage1_actors(verdicts, m1_contrib, m3_contrib)
        q = (
            m3_qualifier(composition_share, s_w)
            if main == "M3" and composition_share is not None
            else ""
        )
        if sub is not None:
            mid = f"{STAGE1_NAME[main]}が主に担い{q}、{STAGE1_NAME[sub]}が従として続き、"
        else:
            other = "M3" if main == "M1" else "M1"
            mid = (
                f"{STAGE1_NAME[main]}が担い{q}、{STAGE1_NAME[other]}は同じ国の中の年トレンドを除くと"
                " TFR との関連が確かめられず、"
            )
        s1 = (
            f"出生率が 6 人から 3 人前後へ下がる段階は、{mid}"
            "望まない出生の減少（M5）の上限（1 − s_w）は"
            f"{_wari(max(0.0, 1.0 - s_w))}にとどまる。"
        )
    else:
        s1 = (
            f"出生率が 6 人から 3 人前後へ下がる段階は、{STAGE1_NAME['M5']}が"
            f"{_wari(1.0 - s_w)}を担い、望む数の低下は{_wari(s_w)}にとどまる。"
        )
    if leader2 is None:
        s2 = (
            "3 人前後から 2 人未満へ下がる段階は、死亡率・女子就学・初婚年齢・所得のどれでも"
            "説明できない。"
        )
    else:
        tail = (
            "死亡率の関連も残る。"
            if (u5_sig2 or leader2 == "d_ln_u5")
            else "死亡率の関連は確かめられない。"
        )
        s2 = (
            f"3 人前後から 2 人未満へ下がる段階は、{STAGE2_NAME[leader2]}が最も整合的な候補で、"
            f"標準化係数の比で{_wari(share2)}（低下に占める割合ではない）を占め、{tail}"
        )
    s3 = f"結婚（同棲を含む）している割合の低下は、TFR 低下の{_wari(s_m)}にあたる。"
    return s1 + s2 + s3


# ---------------------------------------------------------------- data shaping
def survey_table(d: pl.DataFrame, panel: pl.DataFrame) -> pl.DataFrame:
    """One row per DHS survey: Total-family metrics, u5_5/u5_10, ASFR, in-union by age, Cm,
    region (WDI). Pivot fails on duplicate keys (fail-closed)."""
    meta = d.select("iso3", "country", "survey_id", "survey_year", "survey_type").unique(
        "survey_id"
    )
    tot = d.filter(pl.col("characteristic_category").is_in(TOTAL_CATS))
    wide = tot.filter(pl.col("metric") != "u5mr").pivot(
        on="metric", index="survey_id", values="value", aggregate_function=None
    )
    u5 = (
        tot.filter(pl.col("metric") == "u5mr")
        .with_columns(pl.col("by_variable").replace_strict(U5_BY).alias("k"))
        .pivot(on="k", index="survey_id", values="value", aggregate_function=None)
    )
    iu = (
        d.filter(
            (pl.col("metric") == "in_union")
            & (pl.col("characteristic_category") == "Age (5-year groups)")
        )
        .with_columns(("iu_" + pl.col("characteristic_label").str.slice(0, 2)).alias("k"))
        .pivot(on="k", index="survey_id", values="value", aggregate_function=None)
    )
    region = (
        panel.filter(pl.col("region").is_not_null())
        .select("iso3", "region")
        .unique("iso3")
        .sort("iso3")
    )
    out = (
        meta.join(wide, on="survey_id", how="left")
        .join(u5, on="survey_id", how="left")
        .join(iu, on="survey_id", how="left")
        .join(region, on="iso3", how="left")
    )
    for c in (*ASFR, *IU, "u5_5", "u5_10"):
        if c not in out.columns:
            out = out.with_columns(pl.lit(None, dtype=pl.Float64).alias(c))
    cm = [
        bongaarts_cm([r[c] for c in IU], [r[c] for c in ASFR])
        for r in out.select(*IU, *ASFR).iter_rows(named=True)
    ]
    return (
        out.with_columns(
            pl.Series("cm", cm, dtype=pl.Float64),
            pl.col("u5_5").log().alias("ln_u5"),
            pl.col("u5_10").log().alias("ln_u5_10"),
            (pl.col("tfr") - pl.col("ideal_children")).alias("tfr_minus_ideal"),
            pl.col("women_secondary_plus").alias("sec"),
        )
        .with_columns(pl.col("cm").log().alias("ln_cm"))
        .sort("iso3", "survey_year", "survey_id")
    )


def cell_table(d: pl.DataFrame, st: pl.DataFrame) -> pl.DataFrame:
    """Survey × education cells (4 groups): tfr, wanted_tfr, unwanted, afm, mcpr, dummies,
    plus survey-level ln U5MR (Total, 5-year) and meta."""
    e = d.filter(pl.col("characteristic_category") == "Education")
    wide = e.filter(pl.col("metric") != "u5mr").pivot(
        on="metric",
        index=["survey_id", "characteristic_label"],
        values="value",
        aggregate_function=None,
    )
    wide = wide.rename({"characteristic_label": "edu"})
    out = wide.join(
        st.select("survey_id", "iso3", "survey_year", "survey_type", "ln_u5", "ln_u5_10"),
        on="survey_id",
        how="left",
    ).with_columns(
        (pl.col("tfr") - pl.col("wanted_tfr")).alias("unwanted"),
        *[(pl.col("edu") == k).cast(pl.Float64).alias(v) for k, v in EDU_DUMMY.items()],
        (pl.col("edu").is_in(["Secondary", "Higher"])).cast(pl.Float64).alias("e_post"),
        pl.col("edu").replace_strict({k: i for i, k in enumerate(EDU)}).alias("edu_rank"),
    )
    return out.sort("iso3", "survey_year", "survey_id", "edu_rank")


# ---------------------------------------------------------------- estimation
def fit_w(frame: pl.DataFrame, formula: str, *, label: str, weight: str | None = None) -> Est:
    """H1 `fit` (country-clustered OLS) or, with `weight`, the same with WLS weights."""
    if weight is None:
        return fit(frame, formula, label=label, fe=False)
    import statsmodels.formula.api as smf

    pdf = frame.to_pandas()
    res = smf.wls(formula, data=pdf, weights=pdf[weight]).fit(
        cov_type="cluster", cov_kwds={"groups": pdf["iso3"]}
    )
    ci = res.conf_int()
    coefs = {
        str(n): (
            float(res.params[n]),
            float(res.bse[n]),
            float(ci.loc[n, 0]),
            float(ci.loc[n, 1]),
        )
        for n in res.params.index
        if not str(n).startswith("C(") and n != "Intercept"
    }
    return Est(label, int(res.nobs), int(pdf["iso3"].nunique()), coefs, {"r2": float(res.rsquared)})


def with_country_weight(frame: pl.DataFrame) -> pl.DataFrame:
    """Equal weight per country: w = 1 / rows of that country."""
    return frame.with_columns((1.0 / pl.len().over("iso3")).alias("w_eq"))


def _ci(est: Est, name: str) -> tuple[float, float, float, float]:
    return est.coefs[name]


def _fmt(t: tuple[float, float, float, float]) -> str:
    return f"{t[0]:+.3f} [{t[2]:+.3f}, {t[3]:+.3f}]"


@dataclass(frozen=True)
class T1Result:
    s_w: float
    median_ratio: float
    n_pairs: int
    n_countries: int
    pairs: pl.DataFrame


def pair_frame(st: pl.DataFrame, cols: Sequence[str], *, min_gap: int, mode: str) -> pl.DataFrame:
    """Survey pairs within country among surveys with all `cols` non-null.
    mode 'chain' = chain_pairs(min_gap); 'first_last' = first and last survey if gap >= min_gap."""
    s = st.drop_nulls(list(cols)).sort("iso3", "survey_year", "survey_id")
    rows: list[dict[str, Any]] = []
    for (iso,), g in s.group_by(["iso3"], maintain_order=True):
        recs = g.to_dicts()
        years = [int(r["survey_year"]) for r in recs]
        if mode == "chain":
            idx = chain_pairs(years, min_gap)
        else:
            idx = [(0, len(recs) - 1)] if len(recs) >= 2 and years[-1] - years[0] >= min_gap else []
        for i, j in idx:
            a, b = recs[i], recs[j]
            row: dict[str, Any] = {
                "iso3": iso,
                "y0": years[i],
                "y1": years[j],
                "region": a["region"],
            }
            for c in cols:
                row[f"{c}_0"] = float(a[c])
                row[f"d_{c}"] = float(b[c]) - float(a[c])
            rows.append(row)
    schema: dict[str, Any] = {"iso3": pl.Utf8, "y0": pl.Int64, "y1": pl.Int64, "region": pl.Utf8}
    for c in cols:
        schema[f"{c}_0"] = pl.Float64
        schema[f"d_{c}"] = pl.Float64
    return pl.DataFrame(rows, schema=schema, orient="row")


def run_t1(
    st: pl.DataFrame, tag: str, *, min_gap: int = 3, mode: str = "chain", eq: bool = False
) -> T1Result:
    pf = pair_frame(st, ("tfr", "wanted_tfr"), min_gap=min_gap, mode=mode)
    fell = pf.filter(pl.col("d_tfr") < 0).with_columns(
        (1.0 / pl.len().over("iso3")).alias("w_eq"),
        (pl.col("d_wanted_tfr") / pl.col("d_tfr")).alias("ratio"),
    )
    w = fell["w_eq"].to_list() if eq else None
    s_w = ratio_of_sums(fell["d_wanted_tfr"].to_list(), fell["d_tfr"].to_list(), w)
    med = float(statistics.median(fell["ratio"].to_list()))
    res = T1Result(s_w, med, fell.height, fell["iso3"].n_unique(), fell)
    print(
        f"[{tag}] T1 {mode} gap>={min_gap}{' eq-weight' if eq else ''}: pairs(all)={pf.height} "
        f"fell={fell.height} countries={res.n_countries}  ΣΔTFR={fell['d_tfr'].sum():+.2f} "
        f"ΣΔwanted={fell['d_wanted_tfr'].sum():+.2f}  s_w={s_w:.3f}  median pair ratio={med:.3f}"
        f"  -> {verdict_t1(s_w)}"
    )
    return res


@dataclass(frozen=True)
class T2Result:
    a: Est
    b: Est
    c: Est
    frame: pl.DataFrame


def run_t2(st: pl.DataFrame, tag: str, *, u5: str = "ln_u5", weight: str | None = None) -> T2Result:
    f = st.drop_nulls(["tfr", "ideal_children", u5, "sec"])
    if weight:
        f = with_country_weight(f)
    rhs = f"{u5} + sec + C(iso3) + survey_year"
    a = fit_w(f, f"ideal_children ~ {rhs}", label=f"[{tag}] T2a ideal", weight=weight)
    b = fit_w(f, f"tfr_minus_ideal ~ {rhs}", label=f"[{tag}] T2b tfr-ideal", weight=weight)
    c = fit_w(f, f"tfr ~ {rhs}", label=f"[{tag}] T2c tfr", weight=weight)
    for e in (a, b, c):
        print(
            f"{e.label:<34} n={e.n} G={e.countries}  {u5}: {_fmt(_ci(e, u5))}  sec: "
            f"{_fmt(_ci(e, 'sec'))}"
        )
    bc = _ci(c, u5)
    print(f"[{tag}] T2 M1 verdict: {verdict_m1(bc[0], bc[2], bc[3])}")
    return T2Result(a, b, c, f)


@dataclass(frozen=True)
class T3Result:
    share_ge2: float
    n_afm: int
    median_sec: float
    median_hi: float
    n_hi: int
    s_m: float
    n_cm: int
    decomp: pl.DataFrame
    gaps: pl.DataFrame


def afm_gaps(cells: pl.DataFrame) -> pl.DataFrame:
    w = cells.filter(pl.col("age_first_marriage").is_not_null()).pivot(
        on="edu",
        index=["survey_id", "iso3", "survey_year", "survey_type"],
        values="age_first_marriage",
        aggregate_function=None,
    )
    for k in EDU:
        if k not in w.columns:
            w = w.with_columns(pl.lit(None, dtype=pl.Float64).alias(k))
    return w.with_columns(
        (pl.col("Secondary") - pl.col("No education")).alias("gap_sec"),
        (pl.col("Higher") - pl.col("No education")).alias("gap_hi"),
    ).sort("iso3", "survey_year", "survey_id")


def run_t3(
    st: pl.DataFrame,
    cells: pl.DataFrame,
    tag: str,
    *,
    mode: str = "first_last",
    min_gap: int = 8,
    eq: bool = False,
    exclude_union_regions: bool = False,
) -> T3Result:
    g = afm_gaps(cells)
    gs = g.filter(pl.col("gap_sec").is_not_null())
    if eq:
        per = gs.group_by("iso3").agg((pl.col("gap_sec") >= 2).mean().alias("sh"))
        share = _x(per["sh"].mean())
    else:
        share = _x((gs["gap_sec"] >= 2).mean())
    gh = g.filter(pl.col("gap_hi").is_not_null())
    med_sec = _x(gs["gap_sec"].median())
    med_hi = _x(gh["gap_hi"].median())
    s = st
    if exclude_union_regions:
        s = s.filter((pl.col("region") != LATAM) & ~pl.col("iso3").is_in(sorted(SOUTHERN_AFRICA)))
    pf = pair_frame(
        s.with_columns(pl.col("tfr").log().alias("ln_tfr")),
        ("ln_tfr", "ln_cm"),
        min_gap=min_gap,
        mode=mode,
    )
    fell = pf.filter(pl.col("d_ln_tfr") < 0).with_columns(
        (pl.col("d_ln_tfr") - pl.col("d_ln_cm")).alias("d_ln_rest"),
        (1.0 / pl.len().over("iso3")).alias("w_eq"),
    )
    s_m = ratio_of_sums(
        fell["d_ln_cm"].to_list(), fell["d_ln_tfr"].to_list(), fell["w_eq"].to_list()
    )
    print(
        f"[{tag}] T3a AFM Secondary−None: surveys={gs.height} countries={gs['iso3'].n_unique()} "
        f"median={med_sec:+.2f} y, share>=+2y={share:.3f}{' (country-equal)' if eq else ''}; "
        f"Higher−None: n={gh.height} median={med_hi:+.2f} y"
    )
    print(
        f"[{tag}] T3b Cm {mode} gap>={min_gap}"
        f"{' excl LatAm+S.Africa' if exclude_union_regions else ''}:"
        f" pairs fell={fell.height} countries={fell['iso3'].n_unique()} ΣΔlnTFR="
        f"{fell['d_ln_tfr'].sum():+.3f} ΣΔlnCm={fell['d_ln_cm'].sum():+.3f}  s_m={s_m:.3f}"
        f"  -> M2 {verdict_m2(share, s_m)}"
    )
    return T3Result(share, gs.height, med_sec, med_hi, gh.height, s_m, fell.height, fell, g)


@dataclass(frozen=True)
class T4Result:
    g_w: tuple[float, float, float, float]
    g_u: tuple[float, float, float, float]
    h_w: tuple[float, float, float, float]
    h_u: tuple[float, float, float, float]
    p_w: tuple[float, float, float, float]
    est_w: Est
    est_u: Est
    frame: pl.DataFrame


def run_t4(
    cells: pl.DataFrame, tag: str, *, weight: str | None = None, two_groups: bool = False
) -> T4Result:
    f = cells.drop_nulls(["wanted_tfr", "tfr"])
    if weight:
        f = with_country_weight(f)
    dums = "e_post" if two_groups else "e_pri + e_sec + e_hi"
    ew = fit_w(f, f"wanted_tfr ~ {dums} + C(survey_id)", label=f"[{tag}] T4 wanted", weight=weight)
    eu = fit_w(f, f"unwanted ~ {dums} + C(survey_id)", label=f"[{tag}] T4 unwanted", weight=weight)
    key = "e_post" if two_groups else "e_sec"
    nan4 = (math.nan, math.nan, math.nan, math.nan)
    res = T4Result(
        ew.coefs[key],
        eu.coefs[key],
        ew.coefs.get("e_hi", nan4),
        eu.coefs.get("e_hi", nan4),
        ew.coefs.get("e_pri", nan4),
        ew,
        eu,
        f,
    )
    m3, m5 = verdict_m3(res.g_w[0], res.g_w[3], res.g_u[0])
    lab = "Post-primary − (None/Primary)" if two_groups else "Secondary − None"
    print(
        f"[{tag}] T4 cells n={ew.n} surveys={f['survey_id'].n_unique()} G={ew.countries}  "
        f"{lab}: g_w={_fmt(res.g_w)}  g_u={_fmt(res.g_u)}"
    )
    if not two_groups:
        print(
            f"[{tag}]    Higher − None: wanted {_fmt(res.h_w)}  unwanted {_fmt(res.h_u)};"
            f" Primary − None wanted {_fmt(res.p_w)}"
        )
    print(f"[{tag}] T4 verdict: M3 {m3}, M5-from-T4 {m5}")
    return res


@dataclass(frozen=True)
class T5Result:
    gamma: tuple[float, float, float, float]
    est: Est
    center: float
    frame: pl.DataFrame


def run_t5(
    cells: pl.DataFrame, tag: str, *, u5: str = "ln_u5", weight: str | None = None
) -> T5Result:
    f = cells.drop_nulls(["wanted_tfr", u5])
    if weight:
        f = with_country_weight(f)
    center = _x(f[u5].mean())
    f = f.with_columns((pl.col(u5) - center).alias("lu"))
    est = fit_w(
        f,
        "wanted_tfr ~ e_pri + e_sec + e_hi + e_pri:lu + e_sec:lu + e_hi:lu + C(survey_id)",
        label=f"[{tag}] T5",
        weight=weight,
    )
    gam = est.coefs["e_sec:lu"]
    w = widening(gam[0])
    print(
        f"[{tag}] T5 n={est.n} G={est.countries}  γ_Sec−γ_None={_fmt(gam)}  Higher×lu="
        f"{_fmt(est.coefs['e_hi:lu'])}  gradient at mean ln U5 ({math.exp(center):.0f}/1000)="
        f"{est.coefs['e_sec'][0]:+.3f}  widening U5MR 150→30 = {w:+.3f} children"
        f"  -> M4 {verdict_m4(gam[0], gam[2], gam[3])}"
    )
    return T5Result(gam, est, center, f)


# ---------------------------------------------------------------- T6 (WDI)
def t6_base(panel: pl.DataFrame, *, trim: bool = True) -> tuple[pl.DataFrame, int]:
    p = panel.with_columns(
        pl.when(pl.col("u5_mortality") > 0).then(pl.col("u5_mortality").log()).alias("ln_u5"),
        pl.when(pl.col("gdp_pcap_const") > 0).then(pl.col("gdp_pcap_const").log()).alias("ln_gdp"),
        pl.col("fem_sec_enrol").alias("sec"),
        pl.col("married_by18").alias("m18"),
        pl.col("contraceptive_any").alias("contra"),
    )
    if not trim:
        return p.with_columns(pl.col("smam_fe").alias("smam")), 0
    t, n = trim_smam(p.select("iso3", "year", "smam_fe"))
    return p.join(t.rename({"smam_fe": "smam"}), on=["iso3", "year"], how="left"), n


T6_COLS = ("tfr", "ln_u5", "sec", "smam", "ln_gdp", "m18", "contra")


@dataclass(frozen=True)
class T6Stage:
    coefs: dict[str, tuple[float, float, float, float]]
    n: int
    countries: int


def t6_stage(
    ld: pl.DataFrame, xs: Sequence[str], label: str, *, verbose: bool = True
) -> T6Stage | None:
    f = ld.drop_nulls(["d_tfr", *xs])
    if f.height < 10 or f["iso3"].n_unique() < 5:
        print(f"{label}: too few rows (n={f.height})")
        return None
    f = f.with_columns([(pl.col(x) / pl.col(x).std()).alias(x) for x in xs])
    e = fit(f, f"d_tfr ~ {' + '.join(xs)} + C(iso3) + C(period)", label=label, fe=False)
    co = {x: e.coefs[x] for x in xs}
    if verbose:
        parts = "  ".join(f"{T6_LABEL[x]}: {_fmt(co[x])}" for x in xs)
        print(f"{label:<44} n={e.n} G={e.countries}  {parts}")
    return T6Stage(co, e.n, e.countries)


def run_t6(
    base: pl.DataFrame,
    tag: str,
    *,
    width: int = 10,
    xs: Sequence[str] = T6_VARS,
    cut: float = 3.0,
    end: int = 2020,
    verbose: bool = True,
) -> tuple[T6Stage | None, T6Stage | None, pl.DataFrame]:
    ld = long_diff_nearest(base, T6_COLS, width=width, start=1970, end=end)
    s1 = t6_stage(
        ld.filter(pl.col("tfr_0") >= cut), xs, f"[{tag}] stage1 TFR0>={cut}", verbose=verbose
    )
    s2 = t6_stage(
        ld.filter(pl.col("tfr_0") < cut), xs, f"[{tag}] stage2 TFR0<{cut}", verbose=verbose
    )
    if s2 is not None:
        leader, share = stage2_leader(s2.coefs)
        print(
            f"[{tag}] stage-2 leader: {T6_LABEL[leader] if leader else 'none (all CIs include 0)'}"
            f"  share of Σ|b|={share:.3f}"
        )
    return s1, s2, ld


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _save(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150, metadata={"Software": None})
    _plt().close(fig)


def _foot(fig: Any, text: str) -> None:
    fig.text(0.01, 0.005, text, fontsize=6.5, color=MUTED, ha="left", va="bottom")


def fig_t1(t1: T1Result, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    p = t1.pairs
    ax.scatter(p["d_tfr"], p["d_wanted_tfr"], s=12, color=BLUE_RAMP[2], alpha=0.7)
    lo = min(_x(p["d_tfr"].min()), _x(p["d_wanted_tfr"].min())) - 0.2
    xs = [lo, 0.0]
    ax.plot(
        xs, xs, color=MUTED, lw=0.8, ls="--", label="Δwanted = ΔTFR (all of the fall is wanted)"
    )
    ax.plot(
        xs, [t1.s_w * x for x in xs], color=ORANGE, lw=1.4, label=f"pooled share s_w = {t1.s_w:.2f}"
    )
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xlabel("Change in TFR between surveys (children per woman)")
    ax.set_ylabel("Change in wanted TFR (children per woman)")
    ax.set_title(
        "T1: How much of each TFR fall is a fall in wanted fertility", fontsize=10, color=INK
    )
    ax.legend(fontsize=7, frameon=False)
    _style(ax)
    _foot(
        fig,
        f"Survey pairs within country, gap >= 3 y, TFR fell; n = {t1.n_pairs} pairs, "
        f"{t1.n_countries} countries. {DHS_SOURCE}",
    )
    _save(fig, path)


def _residualise(f: pl.DataFrame, y: str, controls: str) -> list[float]:
    import statsmodels.formula.api as smf

    res = smf.ols(f"{y} ~ {controls}", data=f.to_pandas()).fit()
    return [float(v) for v in res.resid]


def fig_t2_within(t2: T2Result, path: Path) -> None:
    plt = _plt()
    f = t2.frame
    ctrl = "sec + C(iso3) + survey_year"
    x = _residualise(f, "ln_u5", ctrl)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharex=True)
    for ax, (y, est, title) in zip(
        axes,
        [
            ("ideal_children", t2.a, "(a) ideal number"),
            ("tfr_minus_ideal", t2.b, "(b) TFR − ideal"),
            ("tfr", t2.c, "(c) TFR"),
        ],
        strict=True,
    ):
        r = _residualise(f, y, ctrl)
        ax.scatter(x, r, s=8, color=BLUE_RAMP[1], alpha=0.6)
        b = est.coefs["ln_u5"]
        xx = [min(x), max(x)]
        ax.plot(xx, [b[0] * v for v in xx], color=ORANGE, lw=1.4)
        ax.set_title(f"{title}: b = {b[0]:+.2f} [{b[2]:+.2f}, {b[3]:+.2f}]", fontsize=9, color=INK)
        ax.set_xlabel("ln U5MR, within country (residual)")
        _style(ax)
    axes[0].set_ylabel("children per woman (residual)")
    fig.suptitle(
        "T2: Within-country association of child mortality with ideal and actual fertility"
        " (country FE + linear year trend + women's secondary+ %)",
        fontsize=9,
        color=INK,
    )
    _foot(
        fig,
        f"n = {t2.c.n} surveys, {t2.c.countries} countries; U5MR = 5 years preceding the "
        f"survey; SE clustered by country. {DHS_SOURCE}",
    )
    _save(fig, path)


def fig_t2_ideal(st: pl.DataFrame, path: Path) -> tuple[int, float, float, float]:
    plt = _plt()
    f = st.drop_nulls(["tfr", "ideal_children", "u5_5"])
    low = f.filter(pl.col("u5_5") < 40)
    hi = f.filter(pl.col("u5_5") >= 40)
    fig, ax = plt.subplots(figsize=(6.0, 4.8))
    ax.scatter(
        hi["ideal_children"],
        hi["tfr"],
        s=10,
        color=BLUE_RAMP[0],
        alpha=0.6,
        label=f"U5MR >= 40 (n = {hi.height})",
    )
    ax.scatter(
        low["ideal_children"],
        low["tfr"],
        s=16,
        color=ORANGE,
        alpha=0.85,
        label=f"U5MR < 40 (n = {low.height})",
    )
    m = max(_x(f["ideal_children"].max()), _x(f["tfr"].max())) + 0.3
    ax.plot([1, m], [1, m], color=MUTED, lw=0.8, ls="--", label="TFR = ideal")
    ax.set_xlabel("Mean ideal number of children (all women)")
    ax.set_ylabel("TFR (children per woman)")
    ax.set_title(
        "T2(d): Where children rarely die, women have fewer than their ideal",
        fontsize=10,
        color=INK,
    )
    ax.legend(fontsize=7, frameon=False)
    _style(ax)
    _foot(fig, f"One point per survey; n = {f.height}. {DHS_SOURCE}")
    _save(fig, path)
    share = _x((low["tfr"] < low["ideal_children"]).mean())
    return (
        low.height,
        _x(low["ideal_children"].median()),
        _x(low["tfr"].median()),
        share,
    )


def fig_t3_afm(t3: T3Result, path: Path) -> None:
    plt = _plt()
    g = t3.gaps.filter(pl.col("gap_sec").is_not_null())
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    ax.hist(g["gap_sec"].to_list(), bins=30, color=BLUE_RAMP[2], alpha=0.85)
    ax.axvline(2.0, color=ORANGE, lw=1.2, ls="--", label="+2 years (criterion)")
    ax.axvline(t3.median_sec, color=INK, lw=1.0, label=f"median {t3.median_sec:+.1f} y")
    ax.set_xlabel("Median age at first marriage (women 25–49): Secondary − No education (years)")
    ax.set_ylabel("Number of surveys")
    ax.set_title(
        f"T3(a): {t3.share_ge2:.0%} of surveys show a gap of +2 years or more",
        fontsize=10,
        color=INK,
    )
    ax.legend(fontsize=7, frameon=False)
    _style(ax)
    _foot(fig, f"n = {g.height} surveys, {g['iso3'].n_unique()} countries. {DHS_SOURCE}")
    _save(fig, path)


def fig_t3_cm(t3: T3Result, path: Path) -> None:
    plt = _plt()
    d = t3.decomp.sort("d_ln_tfr")
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    ys = list(range(d.height))
    ax.barh(ys, d["d_ln_cm"], color=ORANGE, label="Δ ln Cm (share in union)")
    ax.barh(
        ys,
        d["d_ln_rest"],
        left=d["d_ln_cm"],
        color=BLUE_RAMP[2],
        label="Δ ln (TFR / Cm) (fertility within union)",
    )
    ax.set_yticks(ys)
    ax.set_yticklabels(d["iso3"].to_list(), fontsize=5)
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_xlabel("Change in ln TFR, first → last survey (>= 8 years apart)")
    ax.set_title(
        f"T3(b): Union (marriage + cohabitation) accounts for s_m = {t3.s_m:.2f} of the fall",
        fontsize=10,
        color=INK,
    )
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    _style(ax)
    _foot(
        fig,
        f"Bongaarts Cm = Σ m_a f_a / Σ f_a; n = {d.height} countries with falling TFR. "
        f"{DHS_SOURCE}",
    )
    _save(fig, path)


def fig_t4(t4: T4Result, mc: Est | None, path: Path) -> None:
    plt = _plt()
    names = ["Primary", "Secondary", "Higher"]
    keys = ["e_pri", "e_sec", "e_hi"]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    ax = axes[0]
    for k, (est, col, lab) in enumerate(
        [(t4.est_w, BLUE_RAMP[2], "wanted TFR"), (t4.est_u, ORANGE, "unwanted (TFR − wanted)")]
    ):
        xs = [i + (k - 0.5) * 0.35 for i in range(3)]
        b = [est.coefs[x][0] for x in keys]
        lo = [est.coefs[x][0] - est.coefs[x][2] for x in keys]
        hi = [est.coefs[x][3] - est.coefs[x][0] for x in keys]
        ax.bar(xs, b, width=0.35, color=col, label=lab, yerr=[lo, hi], capsize=2, ecolor=INK)
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{n}\n− No educ." for n in names], fontsize=8)
    ax.set_ylabel("children per woman (within survey)")
    ax.set_title("T4: education gap is in wanted, not unwanted, births", fontsize=9, color=INK)
    ax.legend(fontsize=7, frameon=False)
    _style(ax)
    ax = axes[1]
    if mc is not None:
        b = [mc.coefs[x][0] for x in keys]
        lo = [mc.coefs[x][0] - mc.coefs[x][2] for x in keys]
        hi = [mc.coefs[x][3] - mc.coefs[x][0] for x in keys]
        ax.bar(range(3), b, color=BLUE_RAMP[1], yerr=[lo, hi], capsize=2, ecolor=INK)
        ax.set_xticks(range(3))
        ax.set_xticklabels([f"{n}\n− No educ." for n in names], fontsize=8)
        ax.set_ylabel("percentage points (within survey)")
        ax.set_title(
            f"Modern contraception, married women (n = {mc.n} cells)", fontsize=9, color=INK
        )
    _style(ax)
    _foot(
        fig,
        f"Survey FE; 95% CI clustered by country; n = {t4.est_w.n} survey×education cells, "
        f"{t4.est_w.countries} countries. {DHS_SOURCE}",
    )
    _save(fig, path)


def fig_t5(t5: T5Result, path: Path) -> None:
    plt = _plt()
    w = t5.frame.pivot(
        on="edu", index=["survey_id", "ln_u5"], values="wanted_tfr", aggregate_function=None
    ).drop_nulls(["Secondary", "No education"])
    gap = (w["Secondary"] - w["No education"]).to_list()
    u = [math.exp(v) for v in w["ln_u5"].to_list()]
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.scatter(u, gap, s=10, color=BLUE_RAMP[1], alpha=0.6)
    g0 = t5.est.coefs["e_sec"][0]
    gam = t5.gamma[0]
    grid = [min(u) * 1.05**i for i in range(200) if min(u) * 1.05**i <= max(u)]
    ax.plot(
        grid,
        [g0 + gam * (math.log(v) - t5.center) for v in grid],
        color=ORANGE,
        lw=1.5,
        label=f"fit: γ = {gam:+.2f} per ln U5MR; 150→30 widens by {widening(gam):.2f}",
    )
    ax.set_xscale("log")
    ticks = [15, 30, 70, 150, 300]
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])
    ax.minorticks_off()
    ax.set_xlabel("Under-5 mortality, survey total (per 1,000 births, log scale)")
    ax.set_ylabel("Wanted TFR: Secondary − No education")
    ax.set_title(
        "T5: Education gap in wanted fertility by child mortality level", fontsize=10, color=INK
    )
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.invert_xaxis()
    ax.legend(fontsize=7, frameon=False)
    _style(ax)
    _foot(
        fig,
        f"Points: surveys with both cells (n = {len(gap)}). Line: survey-FE model, "
        f"n = {t5.est.n} cells, {t5.est.countries} countries. Source: DHS Program (ICF).",
    )
    _save(fig, path)


def fig_t6(s1: T6Stage | None, s2: T6Stage | None, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    for k, (st, col, lab) in enumerate(
        [
            (s1, BLUE_RAMP[2], "stage 1: TFR at start >= 3"),
            (s2, ORANGE, "stage 2: TFR at start < 3"),
        ]
    ):
        if st is None:
            continue
        ys = [i + (k - 0.5) * 0.3 for i in range(len(T6_VARS))]
        b = [st.coefs[x][0] for x in T6_VARS]
        ax.errorbar(
            b,
            ys,
            xerr=[
                [st.coefs[x][0] - st.coefs[x][2] for x in T6_VARS],
                [st.coefs[x][3] - st.coefs[x][0] for x in T6_VARS],
            ],
            fmt="o",
            color=col,
            capsize=2,
            label=f"{lab} (n = {st.n}, {st.countries} c.)",
        )
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_yticks(range(len(T6_VARS)))
    ax.set_yticklabels([f"Δ {T6_LABEL[x]}" for x in T6_VARS], fontsize=8)
    ax.set_xlabel("ΔTFR (children per woman) per 1 SD of each 10-year change")
    ax.set_title(
        "T6: Standardised 10-year long-difference coefficients by stage\n(country + period FE)",
        fontsize=10,
        color=INK,
    )
    ax.set_ylim(-1.4, len(T6_VARS) - 0.5)
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    _style(ax)
    _foot(
        fig,
        f"10-year non-overlapping differences 1970–2020; 95% CI clustered by country. {WDI_SOURCE}",
    )
    _save(fig, path)


# ---------------------------------------------------------------- descriptive / auxiliaries
def describe(d: pl.DataFrame, st: pl.DataFrame, cells: pl.DataFrame, panel: pl.DataFrame) -> None:
    print("== Data ==")
    print(
        f"dhs_mechanisms: rows={d.height} surveys={d['survey_id'].n_unique()} "
        f"countries={d['iso3'].n_unique()} years="
        f"{_x(d['survey_year'].min()):.0f}–{_x(d['survey_year'].max()):.0f}"
    )
    print("survey types:", dict(sorted(st.group_by("survey_type").len().iter_rows())))
    for c in (
        "tfr",
        "wanted_tfr",
        "ideal_children",
        "u5_5",
        "u5_10",
        "sec",
        "cm",
        "age_first_marriage",
        "modern_contraception_married",
        "want_no_more",
    ):
        s = st.filter(pl.col(c).is_not_null())
        print(f"  survey-level {c:<30} surveys={s.height:>4} countries={s['iso3'].n_unique():>3}")
    asfr_ok = st.drop_nulls(list(ASFR))
    print(
        f"  ASFR 7 groups complete: {asfr_ok.height}; in-union 7 groups complete: "
        f"{st.drop_nulls(list(IU)).height}; Cm computable: {st['cm'].is_not_null().sum()}"
    )
    chk = asfr_ok.with_columns(
        (5 * pl.sum_horizontal(list(ASFR)) / 1000 - pl.col("tfr")).abs().alias("dev")
    )
    print(
        f"  check |5ΣASFR/1000 − TFR|: max={_x(chk['dev'].max()):.3f} "
        f"mean={_x(chk['dev'].mean()):.3f}"
    )
    print(
        f"  survey×education cells: {cells.height}; with wanted & tfr: "
        f"{cells.drop_nulls(['wanted_tfr', 'tfr']).height}"
    )
    print(
        "  no region (not in WDI panel): "
        f"{st.filter(pl.col('region').is_null())['iso3'].unique().sort().to_list()}"
    )
    print(f"growth_fertility_panel: rows={panel.height} economies={panel['iso3'].n_unique()}")
    for c in ("smam_fe", "married_by18", "contraceptive_any", "wanted_tfr_wdi", "fem_sec_enrol"):
        s = panel.filter(pl.col(c).is_not_null())
        print(
            f"  {c:<20} obs={s.height:>5} countries={s['iso3'].n_unique():>3} "
            f"years={_x(s['year'].min()):.0f}–{_x(s['year'].max()):.0f}"
        )


def wdi_wanted_check(st: pl.DataFrame, panel: pl.DataFrame) -> None:
    w = panel.select("iso3", "year", "wanted_tfr_wdi").drop_nulls()
    j = (
        st.select("iso3", pl.col("survey_year").alias("year"), "wanted_tfr")
        .drop_nulls()
        .join(w, on=["iso3", "year"], how="inner")
    )
    if j.height:
        diff = (j["wanted_tfr"] - j["wanted_tfr_wdi"]).abs()
        print(
            f"WDI SP.DYN.WFRT vs DHS wanted TFR (same iso3-year): n={j.height} "
            f"max|diff|={_x(diff.max()):.3f} "
            f"share exact(<=0.05)={_x((diff <= 0.05).mean()):.3f}"
        )


def typical_changes(st: pl.DataFrame) -> tuple[float, float, int]:
    """Per country: first survey >= 1990 with ln_u5 & sec -> last such survey (>= 8 y apart).
    Returns (median Δln U5MR, median Δ secondary+ share as a fraction, n countries)."""
    s = st.filter(pl.col("survey_year") >= 1990)
    pf = pair_frame(s, ("ln_u5", "sec"), min_gap=8, mode="first_last")
    return (
        _x(pf["d_ln_u5"].median()),
        _x(pf["d_sec"].median()) / 100.0,
        pf.height,
    )


def europe_japan(data_dir: Path) -> None:
    print("\n== T6 auxiliaries (re-shown, no new estimation) ==")
    eu = pl.read_parquet(data_dir / "marts" / "eu_tfr_by_education.parquet")
    e = (
        eu.pivot(on="isced_group", index=["iso3", "year"], values="tfr", aggregate_function=None)
        .drop_nulls(["ED0-2", "ED5-8"])
        .sort("iso3", "year")
        .group_by("iso3", maintain_order=True)
        .last()
    )
    for r in e.iter_rows(named=True):
        print(
            f"  EU TFR by education {r['iso3']} {r['year']}: ED0-2={r['ED0-2']:.2f} "
            f"ED5-8={r['ED5-8']:.2f} gap(ED5-8 − ED0-2)={r['ED5-8'] - r['ED0-2']:+.2f}"
        )
    cen = pl.read_parquet(data_dir / "marts" / "eu_census_marital_by_education.parquet")
    c = (
        cen.filter(
            (pl.col("sex") == "F") & pl.col("age_class").is_in(["Y25-29", "Y30-34", "Y35-39"])
        )
        .group_by("isced_group")
        .agg(
            (pl.col("married").sum() / pl.col("total").sum()).alias("share"),
            pl.col("iso3").n_unique().alias("countries"),
        )
        .sort("isced_group")
    )
    for r in c.iter_rows(named=True):
        print(
            f"  EU census 2021 women 25–39 married share (pooled) {r['isced_group']}: "
            f"{r['share']:.3f} ({r['countries']} countries)"
        )
    jp = pl.read_parquet(data_dir / "marts" / "jp_income_age_marital.parquet")
    yr = int(_x(jp["survey_year"].max()))
    j = jp.filter(
        (pl.col("survey_year") == yr)
        & (pl.col("age_class") == "30-34")
        & pl.col("sex").is_in(["female", "male"])
        & pl.col("income_class").is_in(["0-50", "100-150", "300-400", "600-700", "1000-1250"])
    )
    for r in j.sort("sex", "income_class").iter_rows(named=True):
        print(
            f"  Japan {yr} age 30–34 {r['sex']:<6} income {r['income_class']:<9} "
            f"ever-married {r['value']:.3f}"
        )


# ---------------------------------------------------------------- main
def run(data_dir: Path, fig_dir: Path) -> None:
    d = pl.read_parquet(data_dir / DHS_MART)
    panel = pl.read_parquet(data_dir / PANEL_MART)
    fig_dir.mkdir(parents=True, exist_ok=True)
    st = survey_table(d, panel)
    cells = cell_table(d, st)
    describe(d, st, cells, panel)
    wdi_wanted_check(st, panel)

    print("\n== T1 wanted vs unwanted decomposition (M5) ==")
    t1 = run_t1(st, "M")
    t1_fl = run_t1(st, "M", min_gap=8, mode="first_last")
    fig_t1(t1, fig_dir / "h8_t1_wanted_decomposition.png")

    print("\n== T2 child mortality within country (M1) ==")
    t2 = run_t2(st, "M")
    t2_max = fit(
        st.drop_nulls(["tfr", "ln_u5", "sec"]),
        "tfr ~ ln_u5 + sec + C(iso3) + survey_year",
        label="[M] T2c tfr, max sample (ideal not required)",
        fe=False,
    )
    print(t2_max.line())
    fig_t2_within(t2, fig_dir / "h8_t2_within_mortality.png")
    n_low, med_ideal, med_tfr, sh_below = fig_t2_ideal(st, fig_dir / "h8_t2_ideal_vs_tfr.png")
    print(
        f"[M] T2d U5MR<40: surveys={n_low} median ideal={med_ideal:.2f} median TFR={med_tfr:.2f} "
        f"share TFR<ideal={sh_below:.3f}"
        f"{'  -> M1 alone cannot explain low fertility' if sh_below >= 0.5 else ''}"
    )
    ba, bb = t2.a.coefs["ln_u5"][0], t2.b.coefs["ln_u5"][0]
    print(
        f"[M] T2 allocation: (a) ideal {ba:+.3f} / (b) excess {bb:+.3f} of (c) "
        f"{t2.c.coefs['ln_u5'][0]:+.3f} -> "
        f"{'hoarding (ideal)' if abs(ba) > abs(bb) else 'replacement (excess)'}"
    )

    print("\n== T3 marriage (M2) ==")
    t3 = run_t3(st, cells, "M")
    e3c = fit(
        st.drop_nulls(["cm", "sec", "ln_u5"]),
        "cm ~ sec + ln_u5 + C(iso3) + survey_year",
        label="[M] T3c Cm ~ sec + ln u5 (within)",
        fe=False,
    )
    print(e3c.line())
    fig_t3_afm(t3, fig_dir / "h8_t3_marriage_age_gradient.png")
    fig_t3_cm(t3, fig_dir / "h8_t3_cm_decomposition.png")

    print("\n== T4 education gradient: wanted vs unwanted (M3 vs M5) ==")
    t4 = run_t4(cells, "M")
    mcf = cells.drop_nulls(["modern_contraception_married"])
    mc = fit(
        mcf,
        "modern_contraception_married ~ e_pri + e_sec + e_hi + C(survey_id)",
        label="[M] T4 aux modern contraception (married) ~ educ + survey FE",
        fe=False,
    )
    print(mc.line())
    fig_t4(t4, mc, fig_dir / "h8_t4_education_wanted_unwanted.png")

    print("\n== T5 interaction education × child mortality (M4) ==")
    t5 = run_t5(cells, "M")
    fig_t5(t5, fig_dir / "h8_t5_interaction.png")

    print("\n== T6 global WDI long differences (stage 2) ==")
    base, n_trim = t6_base(panel)
    n_smam = panel["smam_fe"].is_not_null().sum()
    print(
        f"SMAM cleaning rule (>=3 obs, |v − country median| >= 4 y): dropped {n_trim} of "
        f"{n_smam} observations"
    )
    s1, s2, ld = run_t6(base, "M")
    assert s2 is not None
    leader2, share2 = stage2_leader(s2.coefs)
    u5c = s2.coefs["d_ln_u5"]
    u5_sig2 = u5c[2] > 0 or u5c[3] < 0
    fig_t6(s1, s2, fig_dir / "h8_t6_stage_coefficients.png")
    europe_japan(data_dir)

    # ---------------------------------------------------------- scorecard
    print("\n== Scorecard (pre-registered, main specification) ==")
    du5, dsec, n_typ = typical_changes(st)
    b_u5 = t2.c.coefs["ln_u5"][0]
    m1_contrib = b_u5 * du5
    m3_contrib = t4.g_w[0] * dsec
    print(
        f"typical change 1990→latest (DHS, first→last >= 8 y, n={n_typ} countries): "
        f"median Δln U5MR={du5:+.3f}, median Δ secondary+ share={dsec:+.3f}"
    )
    print(
        f"M1 quantity = b(T2c) {b_u5:+.3f} × {du5:+.3f} = {m1_contrib:+.3f} children; "
        f"M3 quantity = g_w {t4.g_w[0]:+.3f} × {dsec:+.3f} = {m3_contrib:+.3f} children"
    )
    c2 = t2.c.coefs["ln_u5"]
    score = score_mechanisms(
        s_w=t1.s_w,
        t2c=(c2[0], c2[2], c2[3]),
        share_ge2=t3.share_ge2,
        s_m=t3.s_m,
        g_w=(t4.g_w[0], t4.g_w[3]),
        g_u=t4.g_u[0],
        gamma=(t5.gamma[0], t5.gamma[2], t5.gamma[3]),
    )
    print(f"  M1 (T2c b={c2[0]:+.3f} [{c2[2]:+.3f},{c2[3]:+.3f}]): {score['M1']}")
    print(f"  M2 (T3 share>=2y={t3.share_ge2:.3f}, s_m={t3.s_m:.3f}): {score['M2']}")
    print(
        f"  M3 (T4 g_w={t4.g_w[0]:+.3f} hi={t4.g_w[3]:+.3f}, g_u={t4.g_u[0]:+.3f}): {score['M3']}"
    )
    print(
        f"  M4 (T5 γ={t5.gamma[0]:+.3f} [{t5.gamma[2]:+.3f},{t5.gamma[3]:+.3f}], widening="
        f"{widening(t5.gamma[0]):+.3f}): {score['M4']}"
    )
    print(
        f"  M5 (T1 s_w={t1.s_w:.3f} -> {verdict_t1(t1.s_w)}; T4 |g_u|>=|g_w|: "
        f"{verdict_m3(t4.g_w[0], t4.g_w[3], t4.g_u[0])[1]}): {score['M5']}"
    )
    print(
        f"  stage-2 leader (T6): {T6_LABEL[leader2] if leader2 else 'none'} share={share2:.3f}; "
        f"ln U5MR CI excludes 0 in stage 2: {u5_sig2}"
    )
    e10 = run_e10(d, st, cells, fig_dir / "h8_09_e10_kitagawa.png")
    sentence = final_hypothesis(
        s_w=t1.s_w,
        m1_contrib=m1_contrib,
        m3_contrib=m3_contrib,
        s_m=t3.s_m,
        leader2=leader2,
        share2=share2,
        u5_sig2=u5_sig2,
        verdicts=score,
        composition_share=e10,
    )
    print("\nFINAL HYPOTHESIS:\n" + sentence)
    print("(the bracket after 「（M3）が担い」 is from exploratory E10)")

    robustness(st, cells, panel, t1_fl)
    exploratory(st, cells, base, ld)


def robustness(st: pl.DataFrame, cells: pl.DataFrame, panel: pl.DataFrame, t1_fl: T1Result) -> None:
    print("\n== Robustness (pre-registered list, all reported) ==")
    print(f"[R first→last] T1 s_w={t1_fl.s_w:.3f} (n={t1_fl.n_pairs})")
    variants: list[tuple[str, pl.DataFrame, pl.DataFrame]] = [
        (
            "R DHS only",
            st.filter(pl.col("survey_type") == "DHS"),
            cells.filter(pl.col("survey_type") == "DHS"),
        ),
        (
            "R 1990+",
            st.filter(pl.col("survey_year") >= 1990),
            cells.filter(pl.col("survey_year") >= 1990),
        ),
    ]
    for tag, s, c in variants:
        run_t1(s, tag)
        run_t2(s, tag)
        run_t3(s, c, tag)
        run_t4(c, tag)
        run_t5(c, tag)
    run_t1(st, "R gap>=8", min_gap=8)
    run_t3(st, cells, "R adjacent chain gap>=3", mode="chain", min_gap=3)
    run_t3(st, cells, "R excl LatAm+S.Africa", exclude_union_regions=True)
    run_t2(st, "R U5MR 10y", u5="ln_u5_10")
    run_t5(cells, "R U5MR 10y", u5="ln_u5_10")
    run_t1(st, "R country-equal", eq=True)
    run_t2(st, "R country-equal", weight="w_eq")
    run_t3(st, cells, "R country-equal", eq=True)
    run_t4(cells, "R country-equal", weight="w_eq")
    run_t5(cells, "R country-equal", weight="w_eq")
    run_t4(cells, "R 2 groups (cell approx.)", two_groups=True)

    print("\n-- T6 robustness --")
    base, _ = t6_base(panel)
    raw, _ = t6_base(panel, trim=False)
    run_t6(base, "R 5-year", width=5)
    run_t6(base, "R 20-year", width=20)
    run_t6(raw, "R SMAM untrimmed")
    run_t6(base, "R married_by18 for SMAM", xs=("d_ln_u5", "d_sec", "d_m18", "d_ln_gdp"))
    run_t6(base, "R + contraceptive_any", xs=(*T6_VARS, "d_contra"))
    run_t6(base.filter(pl.col("year") <= 2019), "R excl 2020–24")
    run_t6(base.filter(~pl.col("iso3").is_in(sorted(OIL_STATES))), "R excl oil states")
    last_pop = (
        panel.filter(pl.col("population").is_not_null())
        .sort("year")
        .group_by("iso3")
        .agg(pl.col("population").last().alias("p"))
    )
    small = last_pop.filter(pl.col("p") < SMALL_POP)["iso3"].to_list()
    run_t6(base.filter(~pl.col("iso3").is_in(small)), "R excl pop<1m")
    run_t6(base, "R cut 2.5", cut=2.5)
    run_t6(base, "R cut 3.5", cut=3.5)
    print("-- T5 WDI panel version: Δ10 TFR ~ Δsec + Δsec×1[U5MR start < 50] + FE --")
    ld = (
        long_diff_nearest(base, T6_COLS, width=10, start=1970, end=2020)
        .with_columns((pl.col("ln_u5_0") < math.log(50)).cast(pl.Float64).alias("low_u5"))
        .with_columns((pl.col("d_sec") * pl.col("low_u5")).alias("d_sec_low"))
    )
    e = fit(
        ld.drop_nulls(["d_tfr", "d_sec", "low_u5"]),
        "d_tfr ~ d_sec + d_sec_low + low_u5 + C(iso3) + C(period)",
        label="[R WDI] T5 Δ10 TFR ~ Δsec × 1[U5<50]",
        fe=False,
    )
    print(e.line())


def edu_shares(d: pl.DataFrame) -> pl.DataFrame:
    """Proxy education composition per survey: weighted denominators of the
    modern_contraception_married Education cells (MARRIED women 15-49; the tfr / wanted_tfr
    Education rows carry no denominator). Columns survey_id, edu, w_mar (share within survey)."""
    m = d.filter(
        (pl.col("metric") == "modern_contraception_married")
        & (pl.col("characteristic_category") == "Education")
        & pl.col("denominator_weighted").is_not_null()
    ).select("survey_id", pl.col("characteristic_label").alias("edu"), "denominator_weighted")
    return m.with_columns(
        (
            pl.col("denominator_weighted") / pl.col("denominator_weighted").sum().over("survey_id")
        ).alias("w_mar")
    ).drop("denominator_weighted")


def group_rates(
    cells: pl.DataFrame, shares: pl.DataFrame, st: pl.DataFrame, y: str
) -> pl.DataFrame:
    """Per survey (all 4 education cells required): 4-group rates and married-women shares;
    2-group rates r_lo / r_hi = married-share-weighted mean within (None+Primary) /
    (Secondary+Higher); p_hi2 = women_secondary_plus / 100 (all women 15-49)."""
    c = (
        cells.select("survey_id", "iso3", "survey_year", "edu", y)
        .drop_nulls()
        .join(shares, on=["survey_id", "edu"], how="inner")
    )
    full = c.group_by("survey_id").agg(pl.len().alias("k")).filter(pl.col("k") == 4)
    c = c.join(full.select("survey_id"), on="survey_id", how="inner")
    wide_r = c.pivot(
        on="edu", index=["survey_id", "iso3", "survey_year"], values=y, aggregate_function=None
    )
    wide_p = c.pivot(on="edu", index="survey_id", values="w_mar", aggregate_function=None)
    wide_p = wide_p.rename({k: f"p_{k}" for k in EDU})
    out = wide_r.join(wide_p, on="survey_id").join(
        st.select("survey_id", "sec", pl.col(y).alias("y_total")), on="survey_id", how="left"
    )
    lo = pl.col("p_No education") + pl.col("p_Primary")
    hi = pl.col("p_Secondary") + pl.col("p_Higher")
    return out.with_columns(
        (
            (
                pl.col("No education") * pl.col("p_No education")
                + pl.col("Primary") * pl.col("p_Primary")
            )
            / lo
        ).alias("r_lo"),
        (
            (pl.col("Secondary") * pl.col("p_Secondary") + pl.col("Higher") * pl.col("p_Higher"))
            / hi
        ).alias("r_hi"),
        (pl.col("sec") / 100.0).alias("p_hi2"),
    ).sort("iso3", "survey_year", "survey_id")


def e10_rows(g: pl.DataFrame, fell_iso: set[str], *, two: bool) -> list[dict[str, Any]]:
    need = ["r_lo", "r_hi", "p_hi2"] if two else [*EDU, *[f"p_{k}" for k in EDU]]
    s = g.drop_nulls(need).filter(pl.col("iso3").is_in(sorted(fell_iso)))
    rows: list[dict[str, Any]] = []
    for (iso,), h in s.group_by(["iso3"], maintain_order=True):
        a, b = h.row(0, named=True), h.row(h.height - 1, named=True)
        if int(b["survey_year"]) - int(a["survey_year"]) < 8:
            continue
        if two:
            r0, r1 = [a["r_lo"], a["r_hi"]], [b["r_lo"], b["r_hi"]]
            p0, p1 = [1 - a["p_hi2"], a["p_hi2"]], [1 - b["p_hi2"], b["p_hi2"]]
        else:
            r0, r1 = [a[k] for k in EDU], [b[k] for k in EDU]
            p0, p1 = [a[f"p_{k}"] for k in EDU], [b[f"p_{k}"] for k in EDU]
        rate, comp = kitagawa(r0, r1, p0, p1)
        obs = (
            None
            if a["y_total"] is None or b["y_total"] is None
            else float(b["y_total"]) - float(a["y_total"])
        )
        rows.append(
            {
                "iso3": iso,
                "rate": rate,
                "comp": comp,
                "d_obs": obs,
                "d_rates": [r1[i] - r0[i] for i in range(len(r0))],
            }
        )
    return rows


def run_e10(d: pl.DataFrame, st: pl.DataFrame, cells: pl.DataFrame, fig: Path) -> float:
    """E10 (exploratory): Kitagawa composition vs within-group rate change, first→last (>= 8 y,
    TFR fell). Returns the pooled composition share of the 2-group wanted-TFR version."""
    print("\n== Exploratory E10: Kitagawa decomposition by education (post hoc) ==")
    shares = edu_shares(d)
    fell_iso = set(
        pair_frame(st, ("tfr",), min_gap=8, mode="first_last")
        .filter(pl.col("d_tfr") < 0)["iso3"]
        .to_list()
    )
    main_share = math.nan
    plot: dict[str, list[dict[str, Any]]] = {}
    for y in ("wanted_tfr", "tfr"):
        g = group_rates(cells, shares, st, y)
        for two in (True, False):
            version = (
                "2 groups (p from women_secondary_plus)"
                if two
                else "4 groups (p = married-women proxy)"
            )
            rows = e10_rows(g, fell_iso, two=two)
            if not rows:
                continue
            tot = sum(r["rate"] + r["comp"] for r in rows)
            share = sum(r["comp"] for r in rows) / tot
            per = [r["comp"] / (r["rate"] + r["comp"]) for r in rows if r["rate"] + r["comp"] < 0]
            gaps = [abs(r["rate"] + r["comp"] - r["d_obs"]) for r in rows if r["d_obs"] is not None]
            k = len(rows[0]["d_rates"])
            med = [statistics.median(r["d_rates"][i] for r in rows) for i in range(k)]
            labs = ["None+Primary", "Secondary+Higher"] if two else list(EDU)
            print(
                f"E10 {y:<10} {version}: countries={len(rows)} ΣΔ(reconstructed)={tot:+.2f} "
                f"Σrate={sum(r['rate'] for r in rows):+.2f} "
                f"Σcomp={sum(r['comp'] for r in rows):+.2f}  composition share={share:.3f} "
                f"(median per country {statistics.median(per):.3f}, n={len(per)}); "
                f"median |reconstructed − observed Δtotal|={statistics.median(gaps):.2f}"
            )
            print(
                "      median within-group change first→last: "
                + ", ".join(f"{lab} {v:+.2f}" for lab, v in zip(labs, med, strict=True))
            )
            if not two:
                d0 = [r["d_rates"][0] for r in rows]
                print(
                    f"      No education group {y} first→last: "
                    f"median {statistics.median(d0):+.2f}, "
                    f"mean {statistics.mean(d0):+.2f}, fell in {sum(v < 0 for v in d0)}/{len(d0)}"
                )
            if y == "wanted_tfr":
                plot["two" if two else "four"] = rows
                if two:
                    main_share = share
    ne = (
        cells.filter(pl.col("edu") == "No education")
        .drop_nulls(["wanted_tfr", "ln_u5", "modern_contraception_married"])
        .rename({"modern_contraception_married": "mcpr_none"})
    )
    for y in ("wanted_tfr", "tfr"):
        e = fit(
            ne.drop_nulls([y]),
            f"{y} ~ ln_u5 + mcpr_none + C(iso3) + survey_year",
            label=f"E10b No-education cell {y} (within)",
            fe=False,
        )
        print(e.line())
    fig_e10(plot, fig)
    return main_share


def fig_e10(plot: Mapping[str, list[dict[str, Any]]], path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 5.0))
    titles = ("2 groups: shares from women's secondary+ %", "4 groups: married-women shares")
    for ax, key, title in zip(axes, ("two", "four"), titles, strict=True):
        rows = sorted(plot.get(key, []), key=lambda r: r["rate"] + r["comp"])
        ys = list(range(len(rows)))
        ax.barh(ys, [r["rate"] for r in rows], color=BLUE_RAMP[2], label="within-group change")
        ax.barh(
            ys,
            [r["comp"] for r in rows],
            left=[r["rate"] for r in rows],
            color=ORANGE,
            label="composition change",
        )
        ax.set_yticks(ys)
        ax.set_yticklabels([r["iso3"] for r in rows], fontsize=5)
        ax.axvline(0, color=MUTED, lw=0.6)
        tot = sum(r["rate"] + r["comp"] for r in rows) or 1.0
        sh = sum(r["comp"] for r in rows) / tot
        ax.set_title(f"{title}\ncomposition share = {sh:.2f} (n = {len(rows)})", fontsize=9)
        ax.set_xlabel("Change in wanted TFR, first → last survey")
        _style(ax)
    axes[0].legend(fontsize=7, frameon=False, loc="upper left")
    fig.suptitle("E10 (exploratory): Kitagawa decomposition of the wanted TFR fall", fontsize=10)
    _foot(fig, f"Countries with falling TFR, surveys >= 8 y apart. {DHS_SOURCE}")
    _save(fig, path)


def exploratory(
    st: pl.DataFrame, cells: pl.DataFrame, base: pl.DataFrame, ld: pl.DataFrame
) -> None:
    print("\n== Exploratory (post hoc; not used in any verdict) ==")
    # E1: is the within-union part of T3 itself wanted? Cm vs wanted in the same first→last pairs
    pf = pair_frame(
        st.with_columns(
            pl.col("tfr").log().alias("ln_tfr"), pl.col("wanted_tfr").log().alias("ln_wanted")
        ),
        ("ln_tfr", "ln_cm", "ln_wanted"),
        min_gap=8,
        mode="first_last",
    )
    fell = pf.filter(pl.col("d_ln_tfr") < 0)
    if fell.height:
        print(
            f"E1 first→last, TFR fell, Cm & wanted both present: n={fell.height}; "
            f"ΣΔlnCm/ΣΔlnTFR={_x(fell['d_ln_cm'].sum()) / _x(fell['d_ln_tfr'].sum()):.3f}; "
            f"ΣΔln wanted/ΣΔlnTFR={_x(fell['d_ln_wanted'].sum()) / _x(fell['d_ln_tfr'].sum()):.3f}"
        )
    # E2: s_m by starting TFR level (does marriage matter more at lower TFR?)
    pf2 = pair_frame(
        st.with_columns(pl.col("tfr").log().alias("ln_tfr")),
        ("ln_tfr", "ln_cm"),
        min_gap=8,
        mode="first_last",
    ).filter(pl.col("d_ln_tfr") < 0)
    for lab, cond in (
        ("start TFR >= 5", pl.col("ln_tfr_0") >= math.log(5)),
        ("start TFR 3–5", (pl.col("ln_tfr_0") < math.log(5)) & (pl.col("ln_tfr_0") >= math.log(3))),
        ("start TFR < 3", pl.col("ln_tfr_0") < math.log(3)),
    ):
        g = pf2.filter(cond)
        if g.height:
            print(
                f"E2 s_m {lab}: n={g.height} "
                f"s_m={_x(g['d_ln_cm'].sum()) / _x(g['d_ln_tfr'].sum()):.3f}"
            )
    # E3: s_w by starting TFR level
    pw = pair_frame(st, ("tfr", "wanted_tfr"), min_gap=3, mode="chain").filter(pl.col("d_tfr") < 0)
    for lab, cond in (
        ("start TFR >= 5", pl.col("tfr_0") >= 5),
        ("start TFR 3–5", (pl.col("tfr_0") < 5) & (pl.col("tfr_0") >= 3)),
        ("start TFR < 3", pl.col("tfr_0") < 3),
    ):
        g = pw.filter(cond)
        if g.height:
            print(
                f"E3 s_w {lab}: n={g.height} "
                f"s_w={_x(g['d_wanted_tfr'].sum()) / _x(g['d_tfr'].sum()):.3f}"
            )
    # E4: T2(c) by stage (does mortality still matter once TFR < 4?)
    for lab, cond in (("TFR >= 4", pl.col("tfr") >= 4), ("TFR < 4", pl.col("tfr") < 4)):
        f = st.filter(cond).drop_nulls(["tfr", "ln_u5", "sec"])
        e = fit(f, "tfr ~ ln_u5 + sec + C(iso3) + survey_year", label=f"E4 T2c {lab}", fe=False)
        print(
            f"E4 T2c within, surveys with {lab}: n={e.n} G={e.countries} "
            f"ln_u5 {_fmt(e.coefs['ln_u5'])}"
            f" sec {_fmt(e.coefs['sec'])}"
        )
    # E5: within-country association of women's secondary+ with ideal / wanted (DHS)
    f = st.drop_nulls(["wanted_tfr", "ln_u5", "sec"])
    e = fit(f, "wanted_tfr ~ ln_u5 + sec + C(iso3) + survey_year", label="E5", fe=False)
    print(
        f"E5 wanted TFR within: n={e.n} G={e.countries} ln_u5 {_fmt(e.coefs['ln_u5'])} "
        f"sec(per pp) {_fmt(e.coefs['sec'])}"
    )
    # E6: T5 on the log scale (is the narrowing just compression toward a floor?)
    c6 = cells.drop_nulls(["wanted_tfr", "ln_u5"]).filter(pl.col("wanted_tfr") > 0)
    c6 = c6.with_columns(
        pl.col("wanted_tfr").log().alias("ln_wanted"),
        (pl.col("ln_u5") - pl.col("ln_u5").mean()).alias("lu"),
    )
    e6 = fit(
        c6,
        "ln_wanted ~ e_pri + e_sec + e_hi + e_pri:lu + e_sec:lu + e_hi:lu + C(survey_id)",
        label="E6",
        fe=False,
    )
    print(
        f"E6 T5 on ln wanted TFR: n={e6.n} G={e6.countries} e_sec (log gap at mean) "
        f"{_fmt(e6.coefs['e_sec'])}  e_sec×lu {_fmt(e6.coefs['e_sec:lu'])} "
        f"(negative = proportional gap also narrows as U5MR falls)"
    )
    # E7: T2(c) sensitivity to the pre-registered linear year trend
    f7 = st.drop_nulls(["tfr", "ideal_children", "ln_u5", "sec"])
    for lab, rhs in (
        ("country FE only (no trend)", "ln_u5 + sec + C(iso3)"),
        ("trend, no sec", "ln_u5 + C(iso3) + survey_year"),
        ("no trend, no sec", "ln_u5 + C(iso3)"),
    ):
        e = fit(f7, f"tfr ~ {rhs}", label=f"E7 {lab}", fe=False)
        ea = fit(f7, f"ideal_children ~ {rhs}", label=f"E7a {lab}", fe=False)
        print(
            f"E7 T2 {lab:<28} n={e.n}  tfr: ln_u5 {_fmt(e.coefs['ln_u5'])}  ideal: ln_u5 "
            f"{_fmt(ea.coefs['ln_u5'])}"
        )
    # E8: below-replacement subsample of T6 stage 2 (start TFR < 2.1)
    run_t6(base, "E8 cut 2.1", cut=2.1)
    # E9: T6 stage 2 without SMAM (larger sample; is the enrolment result a sample artefact?)
    run_t6(base, "E9 no SMAM", xs=("d_ln_u5", "d_sec", "d_ln_gdp"))
    _ = ld


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
