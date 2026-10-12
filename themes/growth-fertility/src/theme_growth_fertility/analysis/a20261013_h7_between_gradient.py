"""H7: 国間で豊かな国ほど TFR が低いのはなぜか — 段階（B）/豊かさ（A）/豊かさ→段階（C）。

事前登録: design/themes/growth-fertility.md「### H7」（2026-10-13）、
docs/specs/growth-fertility-h7-between-gradient.md。判定基準・スコアカード・頑健性リストは固定:
  T1 Gelbach 分解（H4 同一サンプル, PPP）   S >= 0.6 -> B,C / S < 0.4 -> A
  T2 複合段階（PC1）五分位の最上位層の勾配   CI∋0 & |b|<=0.20 -> B,C / hi<0 & b<=-0.30 -> A
  T3 転換開始時所得（固定 US$）の p90/p10   >= 5 -> B / <= 2.5 -> C
  T4 同じ国の中の順序                       share<=50% & 死亡率・教育の |std| > 所得 -> B
                                            share>=70% & 前期所得が予測・前期死亡率は予測せず -> C
  T5 4 象限の反例                           両象限 >= 10 & 「豊かにならず低下」の
                                            U5MR 低下中央値 >= 全体 -> B
                                            「豊かにならず低下」< 5 -> C
  T6 開始後の成長（記述のみ、点なし）

決定的スクリプト。入力は data/marts/growth_fertility_panel.parquet のみ、乱数・現在時刻を使わない。
欠損は補完しない（listwise）。SE は国クラスタ。識別戦略は固定効果・長期差分・イベント時間整列のみ。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋ヘルパ（gelbach, t*_points, select_answer, quadrant, event_time, long_differences, pc1_index,
quintile_of, p90_p10）は tests/test_analysis_h7.py で検証する。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

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
from theme_growth_fertility.analysis.a20261005_h4_stage_vs_gdp import (
    GREEN,
    STAGE_VARS,
    STAGE_VARS_NO_ENROL,
    stage_frame,
)
from theme_growth_fertility.transition import onset_table

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
PANEL_MART = Path("marts") / "growth_fertility_panel.parquet"

TINY_POP = 100_000
END_YEAR = 2024
EVENT_WINDOW = (-20, 40)
COMPOSITE_VARS = ("ln_u5", "life_exp", "fem_sec_enrol")
SOURCE = "Source: World Bank WDI (CC BY 4.0)."
ONSET_DEFS: dict[str, dict[str, Any]] = {
    "main (peak>=4.5, 10%)": {},
    "peak>=4.0": {"min_peak": 4.0},
    "peak>=5.0": {"min_peak": 5.0},
    "drop 15%": {"drop": 0.15},
    "5-yr moving average": {"smooth": 5},
}


# ---------------------------------------------------------------- pure helpers (tested)
@dataclass(frozen=True)
class Gelbach:
    beta0: float
    beta_full: float
    deltas: dict[str, float]
    n: int
    countries: int

    @property
    def share(self) -> float:
        return (self.beta0 - self.beta_full) / self.beta0


def gelbach(
    frame: pl.DataFrame,
    *,
    mediators: Sequence[str],
    y: str = "tfr",
    x: str = "ln_gdp",
    controls: str = "C(year)",
) -> Gelbach:
    """Gelbach (2016) decomposition: delta_k = Gamma_k * beta_k, sum = beta0 - beta_full.

    Gamma_k is from `m_k ~ x + controls`, beta_k from the full model; same sample and controls,
    so the identity is exact and independent of the order of the mediators.
    """
    import statsmodels.formula.api as smf

    pdf = frame.to_pandas()
    base = smf.ols(f"{y} ~ {x} + {controls}", data=pdf).fit()
    full = smf.ols(f"{y} ~ {x} + {' + '.join(mediators)} + {controls}", data=pdf).fit()
    deltas = {}
    for m in mediators:
        aux = smf.ols(f"{m} ~ {x} + {controls}", data=pdf).fit()
        deltas[m] = float(aux.params[x]) * float(full.params[m])
    return Gelbach(
        float(base.params[x]),
        float(full.params[x]),
        deltas,
        int(base.nobs),
        int(pdf["iso3"].nunique()),
    )


def t1_points(share: float) -> set[str]:
    if share >= 0.6:
        return {"B", "C"}
    if share < 0.4:
        return {"A"}
    return set()


def t2_points(b: float, lo: float, hi: float) -> set[str]:
    if lo <= 0 <= hi and abs(b) <= 0.20:
        return {"B", "C"}
    if hi < 0 and b <= -0.30:
        return {"A"}
    return set()


def t3_points(ratio: float) -> set[str]:
    if ratio >= 5:
        return {"B"}
    if ratio <= 2.5:
        return {"C"}
    return set()


def t4_points(share: float, *, stage_dominates: bool, lagged_income_only: bool) -> set[str]:
    if share <= 0.5 and stage_dominates:
        return {"B"}
    if share >= 0.7 and lagged_income_only:
        return {"C"}
    return set()


def t5_points(*, n_poor_fell: int, n_rich_not: int, poor_fell_u5_ok: bool) -> set[str]:
    if n_poor_fell >= 10 and n_rich_not >= 10 and poor_fell_u5_ok:
        return {"B"}
    if n_poor_fell < 5:
        return {"C"}
    return set()


def select_answer(points: Mapping[str, int]) -> str:
    """Pre-registered scorecard rule (top answer; tie or 1-point gap -> quantified mixture)."""
    ranked = sorted(points.items(), key=lambda kv: (-kv[1], kv[0]))
    top = ranked[0][1]
    if top < 2:
        return "none: no answer reaches 2 points"
    tied = [k for k, v in ranked if v == top]
    if len(tied) > 1:
        return f"mixture: {' and '.join(tied)} tied at {top} points"
    second = ranked[1]
    if top - second[1] == 1:
        return f"mixture: mainly {ranked[0][0]} ({top}), with {second[0]} ({second[1]})"
    return f"{ranked[0][0]} ({top} points)"


def quadrant(
    ratio: float | None, drop: float | None, *, ratio_cut: float = 3.0, drop_cut: float = 2.0
) -> str | None:
    if ratio is None or drop is None:
        return None
    richer = "richer" if ratio >= ratio_cut else "not_richer"
    fell = "fell" if drop >= drop_cut else "not_fell"
    return f"{richer}_{fell}"


def event_time(
    panel: pl.DataFrame,
    onsets: Mapping[str, int],
    var: str,
    *,
    window: tuple[int, int] = EVENT_WINDOW,
) -> pl.DataFrame:
    """Rows (iso3, event_time, value, dev = value - value at event_time 0). No imputation."""
    on = pl.DataFrame(
        {"iso3": list(onsets), "onset": list(onsets.values())},
        schema={"iso3": pl.Utf8, "onset": pl.Int64},
    )
    df = (
        panel.select("iso3", "year", var)
        .filter(pl.col(var).is_not_null())
        .join(on, on="iso3", how="inner")
        .with_columns((pl.col("year") - pl.col("onset")).cast(pl.Int64).alias("event_time"))
        .filter(pl.col("event_time").is_between(window[0], window[1]))
    )
    base = df.filter(pl.col("event_time") == 0).select("iso3", pl.col(var).alias("v0"))
    return (
        df.join(base, on="iso3", how="inner")
        .select(
            "iso3",
            "event_time",
            pl.col(var).alias("value"),
            (pl.col(var) - pl.col("v0")).alias("dev"),
        )
        .sort(["iso3", "event_time"])
    )


def long_differences(
    panel: pl.DataFrame, cols: Sequence[str], *, width: int, start: int = 1960, end: int = END_YEAR
) -> pl.DataFrame:
    """Non-overlapping width-year differences per iso3 (period = start year), plus 1-period lags."""
    iso = panel.select("iso3").unique().sort("iso3")
    periods = list(range(start, end - width + 1, width))
    parts = []
    for p in periods:
        a = panel.filter(pl.col("year") == p).select("iso3", *cols)
        b = panel.filter(pl.col("year") == p + width).select("iso3", *cols)
        joined = (
            iso.join(a, on="iso3", how="left")
            .join(b, on="iso3", how="left", suffix="_end")
            .select(
                "iso3",
                pl.lit(p, dtype=pl.Int64).alias("period"),
                *[(pl.col(f"{c}_end") - pl.col(c)).alias(f"d_{c}") for c in cols],
            )
        )
        parts.append(joined)
    out = pl.concat(parts).sort(["iso3", "period"])
    return out.with_columns(
        [pl.col(f"d_{c}").shift(1).over("iso3").alias(f"lag_d_{c}") for c in cols]
    )


def pc1_index(
    frame: pl.DataFrame, cols: Sequence[str], *, anchor: str
) -> tuple[list[float], dict[str, float]]:
    """First principal component of the standardised columns; sign so that `anchor` loads > 0."""
    import numpy as np

    mat = frame.select(cols).to_numpy().astype(float)
    z = (mat - mat.mean(axis=0)) / mat.std(axis=0, ddof=1)
    _, _, vt = np.linalg.svd(z, full_matrices=False)
    w = vt[0]
    if w[list(cols).index(anchor)] < 0:
        w = -w
    return [float(s) for s in z @ w], {c: float(v) for c, v in zip(cols, w, strict=True)}


def quintile_of(values: Sequence[float]) -> list[int]:
    import numpy as np

    cuts = np.percentile(np.asarray(values, dtype=float), [20, 40, 60, 80])
    return [1 + int(sum(v > c for c in cuts)) for v in values]


def p90_p10(values: Iterable[float]) -> float:
    import numpy as np

    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return math.nan
    p10, p90 = np.percentile(arr, [10, 90])
    return float(p90 / p10)


# ---------------------------------------------------------------- data preparation
def with_logs(panel: pl.DataFrame) -> pl.DataFrame:
    return panel.with_columns(
        pl.when(pl.col("gdp_pcap_const") > 0)
        .then(pl.col("gdp_pcap_const").log())
        .alias("ln_gdp_c"),
        pl.when(pl.col("u5_mortality") > 0).then(pl.col("u5_mortality").log()).alias("ln_u5"),
    )


def country_filter(
    panel: pl.DataFrame, *, exclude: Iterable[str] = (), min_pop: float | None = None
) -> pl.DataFrame:
    """Country-level sample filter for T3-T6: drop listed iso3 and countries whose latest
    observed population is below min_pop (countries with no population observed are kept)."""
    out = panel.filter(~pl.col("iso3").is_in(sorted(set(exclude))))
    if min_pop is not None:
        last = (
            out.filter(pl.col("population").is_not_null())
            .sort("year")
            .group_by("iso3")
            .agg(pl.col("population").last().alias("pop_last"))
        )
        small = last.filter(pl.col("pop_last") < min_pop)["iso3"].to_list()
        out = out.filter(~pl.col("iso3").is_in(small))
    return out


def onsets_from(panel: pl.DataFrame, **kw: Any) -> tuple[dict[str, int], pl.DataFrame]:
    table = pl.DataFrame(
        onset_table(panel.select("iso3", "year", "tfr").to_dicts(), **kw),
        schema={
            "iso3": pl.Utf8,
            "peak": pl.Float64,
            "peak_year": pl.Int64,
            "onset_year": pl.Int64,
            "eligible": pl.Boolean,
        },
    )
    onsets = {
        r["iso3"]: int(r["onset_year"])
        for r in table.filter(pl.col("onset_year").is_not_null()).to_dicts()
    }
    return onsets, table


def _num(v: float | None, spec: str = ".0f") -> str:
    return "n/a" if v is None else format(v, spec)


def _mean(s: pl.Series) -> float:
    v = s.cast(pl.Float64).mean()
    return math.nan if v is None else float(cast(float, v))


def _v(x: Any) -> str:
    return str(x)


def _f(v: Any) -> float | None:
    return None if v is None else float(v)


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _b(est: Est, name: str = "ln_gdp") -> tuple[float, float, float, float]:
    return est.coefs[name]


# ---------------------------------------------------------------- T1
def run_t1(
    frame: pl.DataFrame, mediators: Sequence[str], tag: str, *, verbose: bool = True
) -> Gelbach:
    g = gelbach(frame, mediators=mediators)
    if verbose:
        base = fit(
            frame,
            "tfr ~ ln_gdp + C(year)",
            label=f"[{tag} T1 base] tfr ~ ln_gdp + C(year)",
            fe=False,
        )
        full = fit(
            frame,
            f"tfr ~ ln_gdp + {' + '.join(mediators)} + C(year)",
            label=f"[{tag} T1 full] + all stage vars",
            fe=False,
        )
        print(base.line())
        print(full.line())
        for k, d in g.deltas.items():
            print(f"  delta[{k:<14}] = {d:+.4f}  ({_pct(d / g.beta0)} of beta0)")
        print(
            f"  check: sum(delta) = {sum(g.deltas.values()):+.6f}; "
            f"beta0 - beta_full = {g.beta0 - g.beta_full:+.6f}"
        )
    print(
        f"  -> [{tag}] T1 S = {g.share:.3f} (beta0 {g.beta0:+.3f}, beta_full {g.beta_full:+.3f}, "
        f"n={g.n}, G={g.countries}): points {sorted(t1_points(g.share)) or 'none'}"
    )
    return g


# ---------------------------------------------------------------- T2
@dataclass
class T2Result:
    loadings: dict[str, float]
    strata: list[tuple[int, Est]]
    aux: Est | None
    top: tuple[float, float, float, float]
    points: set[str] = field(default_factory=set)


def add_composite(frame: pl.DataFrame, kind: str) -> tuple[pl.DataFrame, dict[str, float]]:
    """kind: 'pc1' (pre-registered), 'u5only' (ln u5, sign flipped), 'zmean' (mean of z-scores)."""
    df = frame.with_columns(pl.col("u5_mortality").log().alias("ln_u5"))
    if kind == "pc1":
        scores, load = pc1_index(df, COMPOSITE_VARS, anchor="life_exp")
    elif kind == "u5only":
        scores, load = [-float(v) for v in df["ln_u5"]], {"ln_u5": -1.0}
    elif kind == "zmean":
        z = df.select(
            [((pl.col(c) - pl.col(c).mean()) / pl.col(c).std()).alias(c) for c in COMPOSITE_VARS]
        )
        scores = [(-a + b + c) / 3 for a, b, c in z.iter_rows()]
        load = {"ln_u5": -1 / 3, "life_exp": 1 / 3, "fem_sec_enrol": 1 / 3}
    else:
        raise ValueError(kind)
    df = df.with_columns(pl.Series("stage_index", scores))
    return df.with_columns(pl.Series("stage_q", quintile_of(scores))), load


def run_t2(
    frame: pl.DataFrame,
    tag: str,
    *,
    kind: str = "pc1",
    onsets: Mapping[str, int] | None = None,
    verbose: bool = True,
) -> T2Result:
    df, load = add_composite(frame, kind)
    if verbose:
        print(
            f"  [{tag}] composite={kind} loadings: "
            + ", ".join(f"{k} {v:+.3f}" for k, v in load.items())
        )
    strata = []
    for q in range(1, 6):
        sub = df.filter(pl.col("stage_q") == q)
        est = fit(
            sub, "tfr ~ ln_gdp + C(year)", label=f"[{tag} T2 q{q}] composite quintile {q}", fe=False
        )
        strata.append((q, est))
        if verbose:
            print(est.line())
            sd = _f(sub["ln_gdp"].std())
            print(
                f"  ln_gdp within quintile {q}: SD {_num(sd, '.3f')}, "
                f"mean {_mean(sub['ln_gdp']):.3f}"
            )
    aux = None
    if onsets is not None:
        on = pl.DataFrame(
            {"iso3": list(onsets), "onset": list(onsets.values())},
            schema={"iso3": pl.Utf8, "onset": pl.Int64},
        )
        sub = df.join(on, on="iso3", how="inner").filter(pl.col("year") - pl.col("onset") >= 30)
        if sub["iso3"].n_unique() >= 5:
            aux = fit(
                sub,
                "tfr ~ ln_gdp + C(year)",
                label=f"[{tag} T2 aux] >= 30 years since onset",
                fe=False,
            )
            if verbose:
                print(aux.line())
    top = _b(strata[-1][1])
    pts = t2_points(top[0], top[2], top[3])
    print(
        f"  -> [{tag}] T2 top-quintile slope {top[0]:+.3f} [{top[2]:+.3f}, {top[3]:+.3f}]: "
        f"points {sorted(pts) or 'none'}; middle quintiles q2-q4: "
        + ", ".join(f"{_b(e)[0]:+.3f}" for q, e in strata if 2 <= q <= 4)
    )
    return T2Result(load, strata, aux, top, pts)


# ---------------------------------------------------------------- T3
def onset_frame(panel: pl.DataFrame, onsets: Mapping[str, int]) -> pl.DataFrame:
    on = pl.DataFrame(
        {"iso3": list(onsets), "year": list(onsets.values())},
        schema={"iso3": pl.Utf8, "year": pl.Int64},
    )
    return on.join(
        panel.select("iso3", "year", "country", "region", "gdp_pcap_const", "u5_mortality"),
        on=["iso3", "year"],
        how="left",
    ).rename({"year": "onset_year"})


def region_earlier_share(panel: pl.DataFrame, table: pl.DataFrame) -> pl.DataFrame:
    """For each country with an onset: share of other same-region countries whose onset is earlier.

    Countries already transitioned in 1960 (not eligible, peak < threshold) count as earlier;
    eligible countries without an identified onset count as not earlier."""
    reg = panel.select("iso3", "region").unique()
    t = table.join(reg, on="iso3", how="left")
    rows = t.to_dicts()
    out = []
    for r in rows:
        if r["onset_year"] is None:
            continue
        others = [o for o in rows if o["region"] == r["region"] and o["iso3"] != r["iso3"]]
        if not others:
            continue
        earlier = sum(
            1
            for o in others
            if (o["peak"] is not None and not o["eligible"])
            or (o["onset_year"] is not None and o["onset_year"] < r["onset_year"])
        )
        out.append({"iso3": r["iso3"], "region_earlier_share": earlier / len(others)})
    return pl.DataFrame(out, schema={"iso3": pl.Utf8, "region_earlier_share": pl.Float64})


@dataclass
class T3Result:
    of: pl.DataFrame
    ratio: float
    u5_ratio: float
    points: set[str]


def run_t3(
    panel: pl.DataFrame,
    onsets: Mapping[str, int],
    table: pl.DataFrame,
    tag: str,
    *,
    verbose: bool = True,
) -> T3Result:
    of = onset_frame(panel, onsets)
    inc = of.filter(pl.col("gdp_pcap_const").is_not_null())
    u5 = of.filter(pl.col("u5_mortality").is_not_null())
    ratio = p90_p10(inc["gdp_pcap_const"].to_list())
    u5_ratio = p90_p10(u5["u5_mortality"].to_list())
    pts = t3_points(ratio)
    if verbose:
        import numpy as np

        q = np.percentile(inc["gdp_pcap_const"].to_numpy(), [10, 25, 50, 75, 90])
        print(
            f"  [{tag}] onsets identified {len(onsets)}; income at onset observed {inc.height} "
            f"(missing {of.height - inc.height}: gdp_pcap_const not available in onset year)"
        )
        print(
            "  income at onset (2015 US$) p10/p25/p50/p75/p90 = "
            + " / ".join(f"{v:,.0f}" for v in q)
        )
        qu = np.percentile(u5["u5_mortality"].to_numpy(), [10, 50, 90])
        print(
            f"  U5MR at onset (n={u5.height}) p10/p50/p90 = " + " / ".join(f"{v:.0f}" for v in qu)
        )
    print(
        f"  -> [{tag}] T3 income p90/p10 = {ratio:.2f} "
        f"(n={inc.height}); U5MR p90/p10 = {u5_ratio:.2f}: "
        f"points {sorted(pts) or 'none'}"
    )
    return T3Result(of, ratio, u5_ratio, pts)


def t3_regression(panel: pl.DataFrame, of: pl.DataFrame, table: pl.DataFrame) -> pl.DataFrame:
    gdp60 = panel.filter((pl.col("year") == 1960) & (pl.col("gdp_pcap_const") > 0)).select(
        "iso3", pl.col("gdp_pcap_const").log().alias("ln_gdp1960")
    )
    reg = (
        of.select("iso3", "onset_year")
        .join(gdp60, on="iso3", how="inner")
        .join(region_earlier_share(panel, table), on="iso3", how="inner")
    )
    print(f"  T3 descriptive regression sample: {reg.height} countries (1960 GDP observed)")
    for rhs in ("ln_gdp1960", "region_earlier_share", "ln_gdp1960 + region_earlier_share"):
        est = fit(reg, f"onset_year ~ {rhs}", label=f"[T3 reg] onset_year ~ {rhs}", fe=False)
        print(est.line())
    return reg


# ---------------------------------------------------------------- T4 / T6
def window_growth(
    panel: pl.DataFrame, iso3: str, y0: int, y1: int, lookup: Mapping[tuple[str, int], float]
) -> float | None:
    a, b = lookup.get((iso3, y0)), lookup.get((iso3, y1))
    if a is None or b is None:
        return None
    return (b - a) / (y1 - y0)


def growth_table(panel: pl.DataFrame, onsets: Mapping[str, int]) -> pl.DataFrame:
    """Per country: annual ln-growth of gdp_pcap_const in [-10,0], [0,+10], [+10,+30] and the
    unweighted world mean over the same calendar windows (all countries with both endpoints)."""
    obs = panel.filter(pl.col("ln_gdp_c").is_not_null()).select("iso3", "year", "ln_gdp_c")
    lookup = {(r[0], r[1]): r[2] for r in obs.iter_rows()}
    isos = sorted(set(obs["iso3"].to_list()))
    world_cache: dict[tuple[int, int], float | None] = {}

    def world(y0: int, y1: int) -> float | None:
        if (y0, y1) not in world_cache:
            vals = [g for i in isos if (g := window_growth(panel, i, y0, y1, lookup)) is not None]
            world_cache[(y0, y1)] = sum(vals) / len(vals) if vals else None
        return world_cache[(y0, y1)]

    rows = []
    for iso, t0 in sorted(onsets.items()):
        row: dict[str, Any] = {"iso3": iso, "onset": t0}
        for name, (a, b) in {"pre": (-10, 0), "post": (0, 10), "late": (10, 30)}.items():
            row[f"g_{name}"] = window_growth(panel, iso, t0 + a, t0 + b, lookup)
            row[f"w_{name}"] = world(t0 + a, t0 + b) if t0 + b <= END_YEAR else None
        rows.append(row)
    schema = {"iso3": pl.Utf8, "onset": pl.Int64} | {
        f"{p}_{n}": pl.Float64 for n in ("pre", "post", "late") for p in ("g", "w")
    }
    return pl.DataFrame(rows, schema=schema)


def ld_frame(panel: pl.DataFrame, width: int, end: int = END_YEAR) -> pl.DataFrame:
    """Long differences; female enrolment = secondary if both endpoints observed, else primary."""
    ld = long_differences(
        panel, ("tfr", "ln_gdp_c", "ln_u5", "fem_sec_enrol", "fem_prim_enrol"), width=width, end=end
    )
    return ld.with_columns(
        pl.coalesce("d_fem_sec_enrol", "d_fem_prim_enrol").alias("d_enrol"),
        pl.when(pl.col("d_fem_sec_enrol").is_not_null())
        .then(pl.lit("secondary"))
        .when(pl.col("d_fem_prim_enrol").is_not_null())
        .then(pl.lit("primary"))
        .alias("enrol_source"),
    )


def standardise(frame: pl.DataFrame, cols: Sequence[str]) -> pl.DataFrame:
    return frame.with_columns(
        [((pl.col(c) - pl.col(c).mean()) / pl.col(c).std()).alias(c) for c in cols]
    )


@dataclass
class T4Result:
    share: float
    n_share: int
    std: dict[str, tuple[float, float, float, float]]
    lag: dict[str, tuple[float, float, float, float]]
    stage_dominates: bool
    lagged_income_only: bool
    points: set[str]
    growth: pl.DataFrame


def run_t4(
    panel: pl.DataFrame,
    onsets: Mapping[str, int],
    tag: str,
    *,
    width: int = 10,
    end: int = END_YEAR,
    verbose: bool = True,
) -> T4Result:
    gt = growth_table(panel, onsets)
    pre = gt.filter(pl.col("g_pre").is_not_null() & pl.col("w_pre").is_not_null())
    share = _mean(pre["g_pre"] > pre["w_pre"]) if pre.height else math.nan
    if verbose:
        print(
            f"  [{tag}] (ii) countries with pre-onset growth "
            f"observed: {pre.height} of {len(onsets)}; "
            f"mean pre {_mean(pre['g_pre']):+.4f} vs world {_mean(pre['w_pre']):+.4f}; "
            f"share pre > world = {_pct(share)}"
        )
        post = gt.filter(pl.col("g_post").is_not_null() & pl.col("w_post").is_not_null())
        print(
            f"  [{tag}] (ii) post-onset (0..+10) n={post.height}: "
            f"mean {_mean(post['g_post']):+.4f} vs world "
            f"{_mean(post['w_post']):+.4f}; share post > world = "
            f"{_pct(_mean(post['g_post'] > post['w_post']))}"
        )
    ld = ld_frame(panel, width, end)
    rhs = ("d_ln_gdp_c", "d_ln_u5", "d_enrol")
    main = ld.drop_nulls(["d_tfr", *rhs])
    fe = " + C(iso3) + C(period)"
    raw = fit(
        main, f"d_tfr ~ {' + '.join(rhs)}{fe}", label=f"[{tag} T4(iii)] d{width} raw", fe=False
    )
    stdf = standardise(main, ["d_tfr", *rhs])
    std = fit(
        stdf,
        f"d_tfr ~ {' + '.join(rhs)}{fe}",
        label=f"[{tag} T4(iii)] d{width} standardised",
        fe=False,
    )
    noedu_df = ld.drop_nulls(["d_tfr", "d_ln_gdp_c", "d_ln_u5"])
    noedu = fit(
        standardise(noedu_df, ["d_tfr", "d_ln_gdp_c", "d_ln_u5"]),
        f"d_tfr ~ d_ln_gdp_c + d_ln_u5{fe}",
        label=f"[{tag} T4(iii)] d{width} standardised, education-free",
        fe=False,
    )
    lagdf = ld.drop_nulls(["d_tfr", "lag_d_ln_gdp_c", "lag_d_ln_u5"])
    lag = fit(
        lagdf,
        f"d_tfr ~ lag_d_ln_gdp_c + lag_d_ln_u5{fe}",
        label=f"[{tag} T4(iv)] d{width} lagged changes",
        fe=False,
    )
    if verbose:
        src = main["enrol_source"].value_counts().sort("enrol_source")
        print(
            f"  [{tag}] (iii) enrolment source in sample: "
            + ", ".join(f"{a}={b}" for a, b in src.iter_rows())
        )
        print(
            f"  [{tag}] (iii) periods: "
            + ", ".join(str(p) for p in sorted(set(main["period"].to_list())))
        )
        for e in (raw, std, noedu, lag):
            print(e.line())
    s = std.coefs
    stage_dom = abs(s["d_ln_u5"][0]) > abs(s["d_ln_gdp_c"][0]) and abs(s["d_enrol"][0]) > abs(
        s["d_ln_gdp_c"][0]
    )
    lg, lu = lag.coefs["lag_d_ln_gdp_c"], lag.coefs["lag_d_ln_u5"]
    lag_inc_only = lg[3] < 0 and lu[2] <= 0 <= lu[3]
    pts = t4_points(share, stage_dominates=stage_dom, lagged_income_only=lag_inc_only)
    print(
        f"  -> [{tag}] T4 share={_pct(share)} (n={pre.height}); "
        f"std d{width}: gdp {s['d_ln_gdp_c'][0]:+.3f}, "
        f"u5 {s['d_ln_u5'][0]:+.3f}, enrol {s['d_enrol'][0]:+.3f} -> stage_dominates={stage_dom}; "
        f"lag gdp {lg[0]:+.3f} [{lg[2]:+.3f},{lg[3]:+.3f}], "
        f"lag u5 {lu[0]:+.3f} [{lu[2]:+.3f},{lu[3]:+.3f}] "
        f"-> lagged_income_only={lag_inc_only}: points {sorted(pts) or 'none'}"
    )
    return T4Result(
        share, pre.height, dict(std.coefs), dict(lag.coefs), stage_dom, lag_inc_only, pts, gt
    )


def run_t6(gt: pl.DataFrame, tag: str) -> None:
    both = gt.filter(pl.col("g_pre").is_not_null() & pl.col("g_late").is_not_null())
    if both.height == 0:
        print(f"  [{tag}] T6: no country with both windows")
        return
    higher = _mean(both["g_late"] > both["g_pre"])
    rel = both.filter(pl.col("w_pre").is_not_null() & pl.col("w_late").is_not_null())
    rel_higher = _mean((rel["g_late"] - rel["w_late"]) > (rel["g_pre"] - rel["w_pre"]))
    print(
        f"  [{tag}] T6 (descriptive, no points): n={both.height}; "
        f"mean growth pre(-10..0) {_mean(both['g_pre']):+.4f}, "
        f"+10..+30 {_mean(both['g_late']):+.4f}; share +10..+30 > pre = {_pct(higher)}; "
        f"relative to world mean (n={rel.height}): share higher = {_pct(rel_higher)}"
    )


# ---------------------------------------------------------------- T5
@dataclass
class T5Result:
    table: pl.DataFrame
    counts: dict[str, int]
    points: set[str]


def t5_table(panel: pl.DataFrame, end: int = END_YEAR) -> pl.DataFrame:
    obs = panel.filter(pl.col("gdp_pcap_const").is_not_null() & (pl.col("year") <= end))
    first = obs.group_by("iso3").agg(pl.col("year").min().alias("start"))
    at_start = first.join(
        panel.select("iso3", "year", "gdp_pcap_const", "tfr", "u5_mortality", "fem_prim_enrol"),
        left_on=["iso3", "start"],
        right_on=["iso3", "year"],
        how="left",
    )
    at_end = panel.filter(pl.col("year") == end).select(
        "iso3",
        "country",
        pl.col("gdp_pcap_const").alias("gdp_end"),
        pl.col("tfr").alias("tfr_end"),
        pl.col("u5_mortality").alias("u5_end"),
    )
    df = at_start.join(at_end, on="iso3", how="inner").with_columns(
        (pl.col("gdp_end") / pl.col("gdp_pcap_const")).alias("income_ratio"),
        (pl.col("tfr") - pl.col("tfr_end")).alias("tfr_drop"),
        (pl.col("u5_mortality") - pl.col("u5_end")).alias("u5_decline"),
        (pl.col("u5_mortality").log() - pl.col("u5_end").log()).alias("u5_log_decline"),
    )
    quads = [
        quadrant(r, d)
        for r, d in zip(df["income_ratio"].to_list(), df["tfr_drop"].to_list(), strict=True)
    ]
    return df.with_columns(pl.Series("quadrant", quads, dtype=pl.Utf8)).sort("iso3")


def enrol_change(panel: pl.DataFrame, end: int = END_YEAR) -> pl.DataFrame:
    """Female primary enrolment: first observed (>=1970) -> last observed (<= end), per country."""
    obs = panel.filter(pl.col("fem_prim_enrol").is_not_null() & (pl.col("year") <= end)).sort(
        "year"
    )
    return obs.group_by("iso3").agg(
        (pl.col("fem_prim_enrol").last() - pl.col("fem_prim_enrol").first()).alias(
            "prim_enrol_change"
        )
    )


def run_t5(
    panel: pl.DataFrame,
    tag: str,
    *,
    end: int = END_YEAR,
    verbose: bool = True,
    only: Iterable[str] | None = None,
) -> T5Result:
    df = t5_table(panel, end).join(enrol_change(panel, end), on="iso3", how="left")
    cls = df.filter(pl.col("quadrant").is_not_null())
    if only is not None:
        cls = cls.filter(pl.col("iso3").is_in(sorted(set(only))))
    counts = {
        q: int((cls["quadrant"] == q).sum())
        for q in ("richer_fell", "richer_not_fell", "not_richer_fell", "not_richer_not_fell")
    }
    overall_med = cls["u5_decline"].median()
    pf = cls.filter(pl.col("quadrant") == "not_richer_fell")
    pf_med = pf["u5_decline"].median()
    ok = (
        pf_med is not None
        and overall_med is not None
        and float(str(pf_med)) >= float(str(overall_med))
    )
    pts = t5_points(
        n_poor_fell=counts["not_richer_fell"],
        n_rich_not=counts["richer_not_fell"],
        poor_fell_u5_ok=ok,
    )
    if verbose:
        sy = cls["start"].value_counts().sort("start")
        print(
            f"  [{tag}] T5 sample {cls.height} countries (start = first year with gdp_pcap_const; "
            f"start==1960: {int((cls['start'] == 1960).sum())}, "
            f"later: {int((cls['start'] > 1960).sum())}, "
            f"latest start {int(str(_v(sy['start'].max())))})"
        )
        summ = (
            cls.group_by("quadrant")
            .agg(
                pl.len().alias("n"),
                pl.col("u5_decline").median().alias("med_u5_decline"),
                pl.col("u5_decline").is_not_null().sum().alias("n_u5"),
                pl.col("u5_log_decline").median().alias("med_u5_log_decline"),
                pl.col("prim_enrol_change").median().alias("med_prim_enrol_change"),
                pl.col("income_ratio").median().alias("med_income_ratio"),
                pl.col("tfr_drop").median().alias("med_tfr_drop"),
            )
            .sort("quadrant")
        )
        with pl.Config(tbl_cols=-1, tbl_width_chars=200):
            print(summ)
        print(
            f"  overall median U5MR decline (per 1000) = {_num(_f(overall_med), '.1f')}; "
            f"all-sample median log decline = {_num(_f(cls['u5_log_decline'].median()), '.3f')}"
        )
        for q in ("not_richer_fell", "richer_not_fell"):
            sub = cls.filter(pl.col("quadrant") == q).sort("iso3")
            print(f"  {q} ({sub.height}):")
            for r in sub.to_dicts():
                print(
                    f"    {r['iso3']} {r['country']:<28} start "
                    f"{r['start']} income x{r['income_ratio']:.2f} "
                    f"TFR {r['tfr']:.2f}->{r['tfr_end']:.2f} U5MR "
                    f"{_num(r['u5_mortality'])}->{_num(r['u5_end'])}"
                )
    print(
        f"  -> [{tag}] T5 counts {counts}; not_richer_fell median U5MR decline "
        f"{_num(_f(pf_med), '.1f')} vs overall {_num(_f(overall_med), '.1f')} "
        f"(ok={ok}): points {sorted(pts) or 'none'}"
    )
    return T5Result(cls, counts, pts)


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


STAGE_LABEL = {
    "u5_mortality": "under-5 mortality",
    "fem_sec_enrol": "female sec. enrolment",
    "urban_share": "urban share",
    "fem_lfp": "female LFP",
    "life_exp": "life expectancy",
}


def fig_t1(g: Gelbach, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    colors = [BLUE_RAMP[3], BLUE_RAMP[2], BLUE_RAMP[1], BLUE_RAMP[0], "#c9dcf5"]
    left = 0.0
    for (k, d), c in zip(g.deltas.items(), colors, strict=True):
        ax.barh([0], [d], left=left, color=c, edgecolor="white", label=f"{STAGE_LABEL[k]} {d:+.2f}")
        left += d
    ax.barh(
        [0],
        [g.beta_full],
        left=left,
        color=ORANGE,
        edgecolor="white",
        label=f"remaining income slope {g.beta_full:+.2f}",
    )
    ax.axvline(0, color=MUTED, linewidth=0.8)
    ax.set_yticks([])
    ax.set_xlabel(
        "contribution to the between-country slope of TFR on ln GDP pc (PPP), TFR per log point",
        fontsize=8,
    )
    ax.set_title(
        f"H7 T1: Gelbach decomposition of beta0 = {g.beta0:+.2f} (S = {g.share:.2f})\n"
        f"pooled OLS + year FE, 1990-2024, n={g.n}, G={g.countries}. {SOURCE}",
        fontsize=9,
        color=INK,
    )
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, frameon=False)
    _style(ax)
    _save(fig, path)


def fig_t2(res: T2Result, overall: float, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    xs: list[float] = []
    labels = []
    for q, est in res.strata:
        b, _, lo, hi = _b(est)
        ax.plot([q, q], [lo, hi], color=BLUE_RAMP[2], linewidth=2)
        ax.plot([q], [b], "o", color=BLUE_RAMP[3])
        xs.append(q)
        labels.append(f"Q{q}\nn={est.n}, G={est.countries}")
    if res.aux is not None:
        b, _, lo, hi = _b(res.aux)
        ax.plot([6.2, 6.2], [lo, hi], color=GREEN, linewidth=2)
        ax.plot([6.2], [b], "s", color=GREEN)
        xs.append(6.2)
        labels.append(f">=30y since\nonset n={res.aux.n}")
    ax.axhline(
        overall,
        color=ORANGE,
        linestyle="--",
        linewidth=1,
        label=f"all strata pooled {overall:+.2f}",
    )
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.axhspan(-0.2, 0.2, color="#eeeeee", zorder=0, label="|slope| <= 0.20 (pre-registered)")
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("TFR per log point of GDP pc (PPP), 95% CI", fontsize=8)
    ax.set_xlabel(
        "quintile of composite stage index (PC1 of ln U5MR, life exp., female sec. enrolment;"
        " Q5 = most advanced)",
        fontsize=7,
    )
    ax.set_title(
        f"H7 T2: income slope within stage quintiles (pooled OLS + year FE). {SOURCE}",
        fontsize=8.5,
        color=INK,
    )
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    _style(ax)
    _save(fig, path)


def fig_t3_hist(of: pl.DataFrame, ratio: float, path: Path) -> None:
    import numpy as np

    plt = _plt()
    vals = of.filter(pl.col("gdp_pcap_const").is_not_null())["gdp_pcap_const"].to_numpy()
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    bins = np.logspace(np.log10(vals.min() * 0.9), np.log10(vals.max() * 1.1), 25)
    ax.hist(vals, bins=bins, color=BLUE_RAMP[2], edgecolor="white")
    top = ax.get_ylim()[1]
    p10, p50, p90 = np.percentile(vals, [10, 50, 90])
    for v, lab in ((p10, "p10"), (p50, "median"), (p90, "p90")):
        ax.axvline(v, color=ORANGE, linestyle="--", linewidth=1)
        ax.text(v, top * 0.95, f" {lab} {v:,.0f}", fontsize=7, color=INK, va="top")
    ax.set_xscale("log")
    ax.set_xlabel("GDP per capita in the onset year (constant 2015 US$, log scale)", fontsize=8)
    ax.set_ylabel("number of countries", fontsize=8)
    ax.set_title(
        f"H7 T3: income at fertility-transition onset, n={len(vals)} countries; "
        f"p90/p10 = {ratio:.1f}\n{SOURCE}",
        fontsize=8.5,
        color=INK,
    )
    _style(ax)
    _save(fig, path)


def fig_t3_scatter(of: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    d = of.filter(pl.col("gdp_pcap_const").is_not_null())
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.scatter(d["onset_year"], d["gdp_pcap_const"], s=14, color=BLUE_RAMP[2], alpha=0.8)
    for r in d.to_dicts():
        if r["gdp_pcap_const"] > 15000 or r["gdp_pcap_const"] < 400:
            ax.annotate(
                r["iso3"],
                (r["onset_year"], r["gdp_pcap_const"]),
                fontsize=6,
                color=INK,
                xytext=(2, 2),
                textcoords="offset points",
            )
    ax.set_yscale("log")
    ax.set_xlabel(
        "onset year (first year TFR is 10% below its 1960-75 peak and never returns)", fontsize=8
    )
    ax.set_ylabel("GDP pc at onset (2015 US$, log)", fontsize=8)
    ax.set_title(
        f"H7 T3: onset year vs income at onset, n={d.height}. {SOURCE}", fontsize=8.5, color=INK
    )
    _style(ax)
    _save(fig, path)


def event_means(panel: pl.DataFrame, onsets: Mapping[str, int], var: str) -> pl.DataFrame:
    et = event_time(panel, onsets, var)
    return (
        et.group_by("event_time")
        .agg(pl.col("dev").mean().alias("m"), pl.len().alias("n"))
        .sort("event_time")
    )


def fig_t4_event(panel: pl.DataFrame, onsets: Mapping[str, int], path: Path) -> None:
    plt = _plt()
    specs = [
        ("ln_gdp_c", "ln GDP pc (2015 US$)"),
        ("ln_u5", "ln under-5 mortality"),
        ("fem_prim_enrol", "female enrolment, gross % (primary solid; secondary dashed)"),
        ("tfr", "TFR"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(8.4, 6.0))
    for ax, (var, lab) in zip(axes.flat, specs, strict=True):
        series = [(var, BLUE_RAMP[3], "-")]
        if var == "fem_prim_enrol":
            series.append(("fem_sec_enrol", BLUE_RAMP[1], "--"))
        for v, color, ls in series:
            m = event_means(panel, onsets, v).filter(pl.col("n") >= 10)
            ax.plot(m["event_time"], m["m"], color=color, linestyle=ls)
            n0 = int(m.filter(pl.col("event_time") == 0)["n"].sum())
            ax.text(
                0.02,
                0.92 if ls == "-" else 0.82,
                f"{v}: countries at t=0: {n0}",
                transform=ax.transAxes,
                fontsize=6.5,
                color=color,
            )
        ax.axvline(0, color=ORANGE, linewidth=0.8)
        ax.axhline(0, color=MUTED, linewidth=0.6)
        ax.set_title(lab, fontsize=8, color=INK)
        ax.set_xlabel("years since transition onset", fontsize=7)
        _style(ax)
    fig.suptitle(
        "H7 T4(i): mean change from the onset-year value, countries aligned on onset"
        " (cells with >= 10 countries)\n" + SOURCE,
        fontsize=8.5,
        color=INK,
    )
    _save(fig, path)


def fig_t4_growth(gt: pl.DataFrame, share: float, path: Path) -> None:
    plt = _plt()
    d = gt.drop_nulls(["g_pre", "w_pre", "g_post", "w_post"])
    x = (d["g_pre"] - d["w_pre"]) * 100
    y = (d["g_post"] - d["w_post"]) * 100
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    ax.scatter(x, y, s=14, color=BLUE_RAMP[2], alpha=0.8)
    ax.axvline(0, color=ORANGE, linewidth=0.8)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xlabel("pre-onset growth (-10..0) minus world mean, % per year", fontsize=8)
    ax.set_ylabel("post-onset growth (0..+10) minus world mean, % per year", fontsize=8)
    ax.set_title(
        f"H7 T4(ii): growth of GDP pc (2015 US$) around onset, n={d.height}\n"
        f"share with pre-onset growth above world mean = {share:.0%}. {SOURCE}",
        fontsize=8,
        color=INK,
    )
    _style(ax)
    _save(fig, path)


def fig_t4_ld(results: list[tuple[str, T4Result]], path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8))
    cur = [
        ("d_ln_gdp_c", "d ln GDP pc", ORANGE),
        ("d_ln_u5", "d ln U5MR", BLUE_RAMP[3]),
        ("d_enrol", "d female enrol.", GREEN),
    ]
    lagged = [
        ("lag_d_ln_gdp_c", "lagged d ln GDP pc", ORANGE),
        ("lag_d_ln_u5", "lagged d ln U5MR", BLUE_RAMP[3]),
    ]
    for j, (_, r) in enumerate(results):
        for ax, spec, coefs, step in ((axes[0], cur, r.std, 4), (axes[1], lagged, r.lag, 3)):
            for i, (k, nm, c) in enumerate(spec):
                b, _, lo, hi = coefs[k]
                y = j * step + i
                ax.plot([lo, hi], [y, y], color=c, linewidth=2)
                ax.plot([b], [y], "o", color=c, label=nm if j == 0 else None)
    for ax, step, mid in ((axes[0], 4, 1.0), (axes[1], 3, 0.5)):
        ax.set_yticks([j * step + mid for j in range(len(results))])
        ax.set_yticklabels([lab for lab, _ in results], fontsize=7)
        ax.axvline(0, color=MUTED, linewidth=0.8)
        ax.legend(fontsize=6.5, frameon=False)
        _style(ax)
    axes[0].set_title("(iii) standardised coefficients on d TFR\n(country + period FE)", fontsize=8)
    axes[1].set_title(
        "(iv) previous-period changes -> d TFR\n(TFR per unit change, country + period FE)",
        fontsize=8,
    )
    fig.suptitle(
        f"H7 T4: non-overlapping long differences from 1960, 95% CI clustered by country. {SOURCE}",
        fontsize=8,
        color=INK,
    )
    _save(fig, path)


def fig_t5(t5: T5Result, path: Path) -> None:
    plt = _plt()
    d = t5.table
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    col = {
        "richer_fell": BLUE_RAMP[2],
        "not_richer_not_fell": MUTED,
        "not_richer_fell": GREEN,
        "richer_not_fell": ORANGE,
    }
    for q, c in col.items():
        s = d.filter(pl.col("quadrant") == q)
        ax.scatter(
            s["income_ratio"],
            s["tfr_drop"],
            s=14,
            color=c,
            label=f"{q.replace('_', ' ')} ({s.height})",
        )
        if q in ("not_richer_fell", "richer_not_fell"):
            for r in s.to_dicts():
                ax.annotate(
                    r["iso3"],
                    (r["income_ratio"], r["tfr_drop"]),
                    fontsize=5.5,
                    color=c,
                    xytext=(2, 1),
                    textcoords="offset points",
                )
    ax.set_xscale("log")
    ax.axvline(3.0, color=INK, linewidth=0.8, linestyle="--")
    ax.axhline(2.0, color=INK, linewidth=0.8, linestyle="--")
    ax.set_xlabel(
        "GDP pc ratio, 2024 / first observed year (2015 US$, log; first year = 1960 if available)",
        fontsize=8,
    )
    ax.set_ylabel("TFR decline over the same span (births per woman)", fontsize=8)
    ax.set_title(
        f"H7 T5: income growth vs TFR decline, n={d.height} countries"
        f" (thresholds x3 and 2.0 fixed in advance). {SOURCE}",
        fontsize=7.5,
        color=INK,
    )
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    _style(ax)
    _save(fig, path)


# ---------------------------------------------------------------- driver
def const_income_frame(frame: pl.DataFrame) -> pl.DataFrame:
    """Same rows, ln_gdp replaced by ln gdp_pcap_const (rows without it dropped, listwise)."""
    return frame.filter(pl.col("gdp_pcap_const") > 0).with_columns(
        pl.col("gdp_pcap_const").log().alias("ln_gdp")
    )


COVERAGE_COLS = (
    "tfr",
    "gdp_pcap_const",
    "gdp_pcap_ppp",
    "u5_mortality",
    "life_exp",
    "fem_sec_enrol",
    "fem_prim_enrol",
    "infant_mortality",
)


def describe(panel: pl.DataFrame, frame: pl.DataFrame, table: pl.DataFrame) -> None:
    print("== data ==")
    print(
        f"panel: {panel.height} rows, {panel['iso3'].n_unique()} economies, "
        f"years {_v(panel['year'].min())}-{_v(panel['year'].max())}"
    )
    cov = (
        panel.filter(pl.col("year").is_in([1960, 1970, 1980, 1990, 2000, 2010, 2020, 2024]))
        .group_by("year")
        .agg([pl.col(c).is_not_null().sum().alias(c) for c in COVERAGE_COLS])
        .sort("year")
    )
    with pl.Config(tbl_cols=-1, tbl_width_chars=200):
        print("non-null countries by year:")
        print(cov)
    print(
        f"T1/T2 frame (H4 same sample): n={frame.height} G={frame['iso3'].n_unique()} "
        f"years {_v(frame['year'].min())}-{_v(frame['year'].max())}"
    )
    elig = table.filter(pl.col("eligible"))
    on = table.filter(pl.col("onset_year").is_not_null())
    print(
        f"onset table: {table.height} countries with a 1960-75 TFR; eligible (peak>=4.5) "
        f"{elig.height}; onset identified {on.height}; "
        f"median onset {_v(on['onset_year'].median())}; "
        f"onset <= 1990: {int((on['onset_year'] <= 1990).sum())}; "
        f"already transitioned by 1960 (peak < 4.5): {table.height - elig.height}"
    )


def block(
    panel: pl.DataFrame, frame: pl.DataFrame, tag: str, *, end: int = END_YEAR
) -> dict[str, int]:
    """All five scored tests on one sample variant (main onset definition), terse output."""
    onsets, table = onsets_from(panel)
    g = run_t1(frame, STAGE_VARS, tag, verbose=False)
    t2 = run_t2(frame, tag, onsets=onsets, verbose=False)
    t3 = run_t3(panel, onsets, table, tag, verbose=False)
    t4 = run_t4(panel, onsets, tag, end=end, verbose=False)
    t5 = run_t5(panel, tag, end=end, verbose=False)
    pts = {"A": 0, "B": 0, "C": 0}
    for s in (t1_points(g.share), t2.points, t3.points, t4.points, t5.points):
        for k in s:
            pts[k] += 1
    print(f"  => [{tag}] points A={pts['A']} B={pts['B']} C={pts['C']}: {select_answer(pts)}")
    return pts


def run(data_dir: Path, fig_dir: Path) -> None:
    raw = pl.read_parquet(data_dir / PANEL_MART)
    panel = with_logs(raw)
    fig_dir.mkdir(parents=True, exist_ok=True)
    frame = stage_frame(raw)
    onsets, table = onsets_from(panel)
    describe(panel, frame, table)

    print("\n== T1 Gelbach decomposition (H4 same sample, PPP income) ==")
    g = run_t1(frame, STAGE_VARS, "M")
    fig_t1(g, fig_dir / "h7_t1_gelbach.png")

    print("\n== T2 composite stage index quintiles (PC1) ==")
    overall = fit(frame, "tfr ~ ln_gdp + C(year)", label="[M T2 all] pooled", fe=False)
    t2 = run_t2(frame, "M", onsets=onsets)
    fig_t2(t2, _b(overall)[0], fig_dir / "h7_t2_strata.png")

    print("\n== T3 income at transition onset (constant 2015 US$) ==")
    t3 = run_t3(panel, onsets, table, "M")
    t3_regression(panel, t3.of, table)
    fig_t3_hist(t3.of, t3.ratio, fig_dir / "h7_t3_onset_income_hist.png")
    fig_t3_scatter(t3.of, fig_dir / "h7_t3_onset_year_income.png")

    print("\n== T4 ordering within countries ==")
    for var in ("ln_gdp_c", "ln_u5", "fem_prim_enrol", "fem_sec_enrol", "tfr"):
        m = event_means(panel, onsets, var)
        pick = m.filter(pl.col("event_time").is_in([-20, -10, -5, 0, 5, 10, 20, 30, 40]))
        print(
            f"  (i) {var}: "
            + "; ".join(f"t={t:+d} {v:+.3f} (G={n})" for t, v, n in pick.iter_rows())
        )
    t4 = run_t4(panel, onsets, "M")
    fig_t4_event(panel, onsets, fig_dir / "h7_t4_event_time.png")
    fig_t4_growth(t4.growth, t4.share, fig_dir / "h7_t4_growth_pre_post.png")
    t4_w = [("10y (main)", t4)]
    for w in (5, 20):
        print(f"-- T4 width {w} years (robustness)")
        t4_w.append((f"{w}y", run_t4(panel, onsets, f"R d{w}", width=w)))
    fig_t4_ld(t4_w, fig_dir / "h7_t4_long_diff.png")

    print("\n== T5 counter-examples (four quadrants) ==")
    t5 = run_t5(panel, "M")
    fig_t5(t5, fig_dir / "h7_t5_quadrants.png")
    print(
        "-- EXPLORATORY (not pre-registered; does not enter the scorecard): T5 restricted to "
        "countries with a 1960-75 TFR peak >= 4.5 (pre-transition), because a country starting "
        "near TFR 2-3 cannot fall by 2.0"
    )
    eligible = table.filter(pl.col("eligible"))["iso3"].to_list()
    run_t5(panel, "X eligible only", verbose=False, only=eligible)
    rn = t5.table.filter(pl.col("quadrant") == "richer_not_fell").join(
        table.select("iso3", "eligible"), on="iso3", how="left"
    )
    print(
        f"  richer_not_fell in main T5: {rn.height}, of which pre-transition in 1960-75 "
        f"(peak >= 4.5): {int(rn['eligible'].fill_null(False).sum())} "
        f"({', '.join(rn.filter(pl.col('eligible').fill_null(False))['iso3'].to_list())})"
    )

    print("\n== T6 post-onset growth (descriptive, no points) ==")
    run_t6(t4.growth, "M")

    print("\n== SCORECARD (main specification) ==")
    rows = [
        ("T1 Gelbach S", f"{g.share:.3f}", t1_points(g.share)),
        (
            "T2 top-quintile slope [95% CI]",
            f"{t2.top[0]:+.3f} [{t2.top[2]:+.3f}, {t2.top[3]:+.3f}]",
            t2.points,
        ),
        ("T3 income p90/p10", f"{t3.ratio:.2f}", t3.points),
        (
            "T4 share / stage_dominates / lagged_income_only",
            f"{t4.share:.3f} / {t4.stage_dominates} / {t4.lagged_income_only}",
            t4.points,
        ),
        (
            "T5 not_richer_fell / richer_not_fell",
            f"{t5.counts['not_richer_fell']} / {t5.counts['richer_not_fell']}",
            t5.points,
        ),
    ]
    pts = {"A": 0, "B": 0, "C": 0}
    for name, val, p in rows:
        for k in p:
            pts[k] += 1
        flags = " ".join(f"{k}={int(k in p)}" for k in ("A", "B", "C"))
        print(f"  {name:<48} {val:<32} {flags}")
    print(f"  TOTAL A={pts['A']} B={pts['B']} C={pts['C']}")
    print(f"  SELECTED: {select_answer(pts)}")
    mids = [_b(e)[0] for q, e in t2.strata if 2 <= q <= 4]
    mid = sum(mids) / len(mids)
    b_all = _b(overall)[0]
    print(
        f"  quantities for the mixture sentence: S = {g.share:.3f} of beta0 {g.beta0:+.3f}; "
        f"remaining income slope beta_full = {g.beta_full:+.3f} ({_pct(g.beta_full / g.beta0)} "
        f"of beta0); T2 top slope {t2.top[0]:+.3f}; middle quintiles (q2-q4) mean {mid:+.3f} "
        f"({_pct(mid / b_all)} of pooled {b_all:+.3f})"
    )

    print("\n== ROBUSTNESS (pre-registered list) ==")
    print("-- sample variants: full scorecard per variant")
    variants: list[tuple[str, pl.DataFrame, pl.DataFrame, int]] = [
        (
            "drop oil states",
            country_filter(panel, exclude=OIL_STATES),
            stage_frame(raw, exclude_iso3=OIL_STATES),
            END_YEAR,
        ),
        (
            f"drop pop < {SMALL_POP:,}",
            country_filter(panel, min_pop=SMALL_POP),
            stage_frame(raw, min_population=SMALL_POP),
            END_YEAR,
        ),
        (
            f"drop pop < {TINY_POP:,}",
            country_filter(panel, min_pop=TINY_POP),
            stage_frame(raw, min_population=TINY_POP),
            END_YEAR,
        ),
        (
            "drop 2020-2024",
            panel.filter(pl.col("year") <= 2019),
            stage_frame(raw, end_year=2019),
            2019,
        ),
    ]
    for name, vp, f, end in variants:
        print(
            f"-- {name}: T1/T2 n={f.height} G={f['iso3'].n_unique()}; "
            f"T3-T5 countries={vp['iso3'].n_unique()}"
        )
        block(vp, f, f"R {name}", end=end)
    print("-- onset definitions (T2 aux, T3, T4, T6; T1 and T5 do not use onsets)")
    for name, kw in ONSET_DEFS.items():
        if not kw:
            continue
        on_r, tab_r = onsets_from(panel, **kw)
        print(f"  [{name}] eligible {int(tab_r['eligible'].sum())}, onsets {len(on_r)}")
        t2r = run_t2(frame, f"R onset {name}", onsets=on_r, verbose=False)
        if t2r.aux is not None:
            b = _b(t2r.aux)
            print(
                f"  [R onset {name}] T2 aux >=30y since onset: "
                f"{b[0]:+.3f} [{b[2]:+.3f}, {b[3]:+.3f}]"
                f" n={t2r.aux.n} G={t2r.aux.countries}"
            )
        run_t3(panel, on_r, tab_r, f"R onset {name}", verbose=False)
        t4r = run_t4(panel, on_r, f"R onset {name}", verbose=False)
        run_t6(t4r.growth, f"R onset {name}")
    print("-- income series: constant 2015 US$ instead of PPP in T1/T2 (same rows)")
    fc = const_income_frame(frame)
    run_t1(fc, STAGE_VARS, "R const US$", verbose=False)
    run_t2(fc, "R const US$", onsets=onsets, verbose=False)
    print("-- composite stage index: mortality only (H4 replication) / standardised mean of 3")
    for kind in ("u5only", "zmean"):
        run_t2(frame, f"R composite {kind}", kind=kind, onsets=onsets, verbose=False)
    print("-- T4 difference width 5 / 20 years: see [R d5] / [R d20] above")
    print("-- T1 with 4 stage variables (no fem_sec_enrol)")
    run_t1(
        stage_frame(raw, stage_vars=STAGE_VARS_NO_ENROL),
        STAGE_VARS_NO_ENROL,
        "R 4 vars",
        verbose=False,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
