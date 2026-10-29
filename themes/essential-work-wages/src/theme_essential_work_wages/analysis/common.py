"""Shared, pure helpers for the essential-work-wages analysis scripts.

Tested in tests/test_analysis_common.py.

Occupation-level data only: every row is an occupation (or occupation x industry cell) with a wage
figure and an employment weight. No I/O here except `load_flags`, which reads the committed
definition tables shipped with the package.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import polars as pl
import statsmodels.api as sm

PKG_DIR = Path(__file__).resolve().parents[1]
THEME_DIR = Path(__file__).resolve().parents[3]
REPO_DIR = THEME_DIR.parents[1]
MARTS = REPO_DIR / "data" / "marts"
FIGURES = THEME_DIR / "reports" / "figures"

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"

FLAG_FILES = {
    "jp_bsws2020": "jp_occupation_flags.csv",
    "jp_bsws2009": "jp_occupation_flags_2009.csv",
    "us_census_occ2018": "us_occupation_flags.csv",
}
INT_COLS = (
    "essential",
    "cisa_sector",
    "licensed",
    "admin_price",
    "third_party",
    "boundary",
    "education_years",
)


def load_flags(classification: str) -> pl.DataFrame:
    """Committed definition table for one occupation classification (ints parsed, rest str)."""
    path = PKG_DIR / FLAG_FILES[classification]
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out: list[dict[str, object]] = []
    for r in rows:
        d: dict[str, object] = dict(r)
        for c in INT_COLS:
            if c in d:
                d[c] = int(str(d[c]))
        out.append(d)
    return pl.DataFrame(out)


def weighted_quantile(values: Sequence[float], weights: Sequence[float], q: float) -> float:
    """Weighted quantile (q in [0,1]) by cumulative weight, lower-interpolated at the crossing.

    Raises ValueError on empty input, mismatched lengths, negative weights or zero total weight."""
    if len(values) != len(weights):
        msg = "values and weights differ in length"
        raise ValueError(msg)
    pairs = [(float(v), float(w)) for v, w in zip(values, weights, strict=True) if w is not None]
    if not pairs:
        msg = "no observations"
        raise ValueError(msg)
    if any(w < 0 for _, w in pairs):
        msg = "negative weight"
        raise ValueError(msg)
    pairs.sort(key=lambda p: p[0])
    total = sum(w for _, w in pairs)
    if total <= 0:
        msg = "zero total weight"
        raise ValueError(msg)
    if not 0 <= q <= 1:
        msg = "q outside [0, 1]"
        raise ValueError(msg)
    target = q * total
    cum = 0.0
    for v, w in pairs:
        cum += w
        if cum >= target - 1e-12:
            return v
    return pairs[-1][0]


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float:
    return weighted_quantile(values, weights, 0.5)


def group_ratio(df: pl.DataFrame, flag: str, wage: str, weight: str) -> dict[str, float]:
    """Employment-weighted median wage of flag==1 rows over that of all rows, plus bottom-quartile
    over-representation: share of flag==1 workers in occupations below the weighted P25 wage,
    divided by the flag==1 share of all workers."""
    d = df.filter(pl.col(wage).is_not_null() & pl.col(weight).is_not_null() & (pl.col(weight) > 0))
    all_med = weighted_median(d[wage].to_list(), d[weight].to_list())
    g = d.filter(pl.col(flag) == 1)
    if g.height == 0:
        msg = f"no rows with {flag} == 1"
        raise ValueError(msg)
    g_med = weighted_median(g[wage].to_list(), g[weight].to_list())
    p25 = weighted_quantile(d[wage].to_list(), d[weight].to_list(), 0.25)
    bottom = d.filter(pl.col(wage) <= p25)
    share_all = float(g[weight].sum()) / float(d[weight].sum())
    share_bottom = float(bottom.filter(pl.col(flag) == 1)[weight].sum()) / float(
        bottom[weight].sum()
    )
    return {
        "median_ratio": g_med / all_med,
        "median_group": g_med,
        "median_all": all_med,
        "p25_all": p25,
        "share_all": share_all,
        "share_bottom_quartile": share_bottom,
        "overrepresentation": share_bottom / share_all if share_all > 0 else math.nan,
        "n_occupations": g.height,
        "n_all": d.height,
    }


def wls(
    df: pl.DataFrame, y: str, xs: Sequence[str], weight: str
) -> dict[str, tuple[float, float, float, float]]:
    """Weighted least squares of y on xs (+ const), weights = weight. Returns
    {name: (coef, se, ci_low, ci_high)} with HC1 robust standard errors."""
    d = df.select([y, *xs, weight]).drop_nulls()
    if d.height <= len(xs) + 1:
        msg = f"too few rows ({d.height}) for {len(xs)} regressors"
        raise ValueError(msg)
    x = sm.add_constant(d.select(xs).to_numpy().astype(float), has_constant="add")
    res = sm.WLS(d[y].to_numpy().astype(float), x, weights=d[weight].to_numpy().astype(float)).fit(
        cov_type="HC1"
    )
    names = ["const", *xs]
    ci = np.asarray(res.conf_int())
    out: dict[str, tuple[float, float, float, float]] = {}
    for i, n in enumerate(names):
        out[n] = (float(res.params[i]), float(res.bse[i]), float(ci[i, 0]), float(ci[i, 1]))
    out["_n"] = (float(d.height), float(res.rsquared), math.nan, math.nan)
    return out


def as_float(v: object) -> float:
    """polars aggregate (Decimal/None/...) -> float (NaN for None)."""
    if v is None:
        return math.nan
    return float(str(v))


def md_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    def fmt(v: object) -> str:
        if isinstance(v, float):
            if math.isnan(v):
                return "–"
            return f"{v:.3f}" if abs(v) < 100 else f"{v:,.0f}"
        return str(v)

    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def verdict(value: float, ok: float, bad: float, *, higher_is_ok: bool) -> str:
    """Three-way pre-registered verdict: 整合 / 不支持 / 中間."""
    if higher_is_ok:
        if value >= ok:
            return "整合"
        return "不支持" if value <= bad else "中間"
    if value <= ok:
        return "整合"
    return "不支持" if value >= bad else "中間"


def describe(m: Mapping[str, tuple[float, float, float, float]], name: str) -> str:
    c, se, lo, hi = m[name]
    return f"{c:+.3f} (SE {se:.3f}, 95% CI {lo:+.3f}〜{hi:+.3f})"
