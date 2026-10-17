"""H8b（事後追加）: 学歴群の中、特に教育なし群で「望む出生」が下がった真因の候補比較。

事前固定: design/themes/growth-fertility.md「### H8b」（2026-10-18）。
H8 の E10 を見た後の追加検証で、検定 X1〜X5・判定規則・頑健性リストは
追加データ（DHS 就業・収入形態・子どもの就学）を見る前に固定した。
結果は H8 の判定（M1〜M5）を変えない。

候補: W 女性の就業・現金収入 / S 子どもの就学 / C 避妊・小家族規範 / U 子どもの死亡率。
  X1（主）教育なしセルの wanted_tfr ~ 就業(教育なし) + 近代避妊(教育なし) + 初等・中等就学率(Total)
          + ln U5MR(Total, 5 年) + 国 FE + 調査年トレンド。国クラスタ SE、
          説明変数は推定標本の SD で標準化
  X2      Total の wanted_tfr の horse race（＋ married_cash_employed、women_secondary_plus）
  X3      教育なし群の first→last（>= 8 年）の Δ の Spearman
  X4      調査 × 学歴セルの g_w（Secondary − None）に women_employed を加えたときの縮み
  X5      教育なし群の women_employed の first→last の変化
判定: X1 で |標準化係数| 最大かつ CI∌0 の変数の候補。無ければ「どの候補も確かめられない」。
W は X5 の中央値が上昇していることも要る。X2〜X4 が X1 と食い違えば「候補は絞れない」。
「食い違い」の運用（設計に細則が無いので、結果を見る前に実装で固定）は `decide` の docstring。

決定的スクリプト。入力は data/marts/{dhs_mechanisms, growth_fertility_panel}.parquet。
乱数・現在時刻は使わない。欠損は補完しない（listwise）。H8 スクリプトは変更せず関数を import する。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋ヘルパ（cash_employed, add_derived, standardize, leader, candidate_of, decide）は
tests/test_analysis_h8b.py で検証する。
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
    ORANGE,
    Est,
    _style,
    fit,
)
from theme_growth_fertility.analysis.a20261017_h8_mechanisms import (
    DHS_MART,
    DHS_SOURCE,
    EDU,
    PANEL_MART,
    REPO_ROOT,
    THEME_DIR,
    _foot,
    _plt,
    _save,
    _x,
    cell_table,
    fit_w,
    pair_frame,
    survey_table,
    with_country_weight,
)

Coef = tuple[float, float, float, float]  # (b, se, lo, hi)

# variable -> candidate (closed mapping; women_secondary_plus is a control, not a candidate)
CANDIDATE: dict[str, str] = {
    "emp": "W",
    "emp_tot": "W",
    "cash_emp": "W",
    "att_pri": "S",
    "att_sec": "S",
    "mcpr": "C",
    "ln_u5": "U",
}
CAND_NAME = {
    "W": "W（女性の就業・現金収入）",
    "S": "S（子どもの就学）",
    "C": "C（避妊・小家族規範の普及）",
    "U": "U（子どもの死亡率）",
}
VAR_LABEL = {
    "emp": "women employed (No-edu cell, %)",
    "emp_tot": "women employed (Total, %)",
    "cash_emp": "married women earning cash (%)",
    "noncash_emp": "married women employed, no cash (%)",
    "emp_q": "women employed (wealth-quintile cell, %)",
    "att_pri": "child primary attendance (Total, %)",
    "att_sec": "child secondary attendance (Total, %)",
    "mcpr": "modern contraception, married (%)",
    "ln_u5": "ln U5MR (Total, 5 y)",
    "sec": "women secondary+ (%)",
}
X1_VARS = ("emp", "mcpr", "att_pri", "att_sec", "ln_u5")
X2_VARS = ("cash_emp", "emp_tot", "att_pri", "att_sec", "mcpr", "ln_u5", "sec")
FE_TREND = "C(iso3) + survey_year"


# ---------------------------------------------------------------- pure helpers (tested)
def cash_employed(
    married_employed: float | None, cash_only: float | None, cash_inkind: float | None
) -> float | None:
    """% of married women who worked in the last 12 months AND were paid in cash
    (cash only or cash and in-kind): employed × (cash_only + cash_inkind) / 100.
    Any None -> None."""
    if married_employed is None or cash_only is None or cash_inkind is None:
        return None
    return married_employed * (cash_only + cash_inkind) / 100.0


def add_derived(st: pl.DataFrame) -> pl.DataFrame:
    """Survey table -> + married_cash_employed and married_noncash_employed (employed minus
    cash-earning; unpaid / in-kind only). Null propagates (no imputation)."""
    cash = (
        pl.col("married_employed")
        * (pl.col("married_cash_only") + pl.col("married_cash_inkind"))
        / 100.0
    )
    return st.with_columns(cash.alias("married_cash_employed")).with_columns(
        (pl.col("married_employed") - pl.col("married_cash_employed")).alias(
            "married_noncash_employed"
        )
    )


def standardize(
    frame: pl.DataFrame, cols: Sequence[str], *, within: str | None = None
) -> tuple[pl.DataFrame, dict[str, float]]:
    """Centre each column and divide by its sample SD (ddof=1) in `frame`, so a coefficient is
    the change in y per 1 SD of x. With `within`, the SD is that of the deviations from the
    group (e.g. country) mean — the variation a country-FE regression actually uses.
    Returns (frame, {col: sd}). A zero / undefined SD raises ValueError."""
    sds: dict[str, float] = {}
    out = frame
    for c in cols:
        x = pl.col(c) - pl.col(c).mean().over(within) if within else pl.col(c) - pl.col(c).mean()
        sd_raw = frame.select(x.std(ddof=1)).item()
        if sd_raw is None or not math.isfinite(float(sd_raw)) or float(sd_raw) == 0.0:
            raise ValueError(f"SD of {c} is zero or undefined")
        sd = float(sd_raw)
        sds[c] = sd
        out = out.with_columns(((pl.col(c) - pl.col(c).mean()) / sd).alias(c))
    return out, sds


def leader(coefs: Mapping[str, Coef], allowed: Sequence[str] | None = None) -> str | None:
    """Pre-fixed rule: among variables (restricted to `allowed`) whose CI excludes 0, the one with
    the largest |b| (ties -> name). None if no CI excludes 0."""
    keys = [k for k in coefs if allowed is None or k in allowed]
    sig = [k for k in keys if coefs[k][2] > 0 or coefs[k][3] < 0]
    if not sig:
        return None
    return sorted(sig, key=lambda k: (-abs(coefs[k][0]), k))[0]


def candidate_of(var: str | None) -> str | None:
    return None if var is None else CANDIDATE[var]


@dataclass(frozen=True)
class Decision:
    code: str  # "W" | "S" | "C" | "U" | "none" | "W_fails" | "undetermined"
    sentence: str
    conflicts: tuple[str, ...]


def decide(
    x1_cand: str | None,
    *,
    x5_median: float | None,
    checks: Mapping[str, str | None],
    x4_supports_w: bool | None,
) -> Decision:
    """Pre-fixed decision (design H8b 判定).

    1. X1 picks nothing -> 「どの候補も確かめられない」.
    2. X1 picks W but the median first→last change of No-education employment (X5) is not > 0
       (or unavailable) -> 「W は成り立たない」.
    3. Consistency (operationalised before running): a check in `checks` (X2, X3) conflicts when
       it picks a *different* candidate; picking nothing is silent, not a conflict. X4 speaks
       only to W: when X1 picks W and X4 does not support it (`x4_supports_w` is False) that is
       a conflict. Any conflict -> 「候補は絞れない」.
    4. Otherwise the X1 candidate is 「教育なし群の望む数と最も強く並走する候補」.
    """
    if x1_cand is None:
        return Decision("none", "どの候補も確かめられない。", ())
    if x1_cand == "W" and (x5_median is None or x5_median <= 0):
        return Decision(
            "W_fails",
            "W は成り立たない（X1 では就業が選ばれたが、"
            "教育なし群の就業率は中央値で上昇していない）。",
            (),
        )
    conflicts = [f"{k}={v}" for k, v in checks.items() if v is not None and v != x1_cand]
    if x1_cand == "W" and x4_supports_w is False:
        conflicts.append("X4=not W")
    if conflicts:
        return Decision(
            "undetermined",
            f"候補は絞れない（X1 は {CAND_NAME[x1_cand]} を選ぶが、"
            f"{'、'.join(conflicts)} と食い違う）。",
            tuple(conflicts),
        )
    return Decision(
        x1_cand,
        f"教育なし群の望む数と最も強く並走する候補は {CAND_NAME[x1_cand]} である。",
        (),
    )


# ---------------------------------------------------------------- data shaping
def no_edu_frame(cells: pl.DataFrame, st: pl.DataFrame) -> pl.DataFrame:
    """No-education cells with cell employment / contraception and survey Total attendance."""
    return (
        cells.filter(pl.col("edu") == "No education")
        .select(
            "survey_id",
            "iso3",
            "survey_year",
            "survey_type",
            "wanted_tfr",
            "tfr",
            pl.col("women_employed").alias("emp"),
            pl.col("modern_contraception_married").alias("mcpr"),
            "ln_u5",
        )
        .join(
            st.select(
                "survey_id",
                "region",
                pl.col("child_primary_attendance").alias("att_pri"),
                pl.col("child_secondary_attendance").alias("att_sec"),
            ),
            on="survey_id",
            how="left",
        )
        .sort("iso3", "survey_year", "survey_id")
    )


def total_frame(st: pl.DataFrame) -> pl.DataFrame:
    return st.select(
        "survey_id",
        "iso3",
        "survey_year",
        "survey_type",
        "region",
        "wanted_tfr",
        "tfr",
        pl.col("married_cash_employed").alias("cash_emp"),
        pl.col("married_noncash_employed").alias("noncash_emp"),
        pl.col("married_employed").alias("mar_emp"),
        pl.col("women_employed").alias("emp_tot"),
        pl.col("child_primary_attendance").alias("att_pri"),
        pl.col("child_secondary_attendance").alias("att_sec"),
        pl.col("modern_contraception_married").alias("mcpr"),
        "ln_u5",
        "sec",
    )


# ---------------------------------------------------------------- estimation
@dataclass(frozen=True)
class Horse:
    label: str
    est: Est
    sds: dict[str, float]
    lead: str | None


def horse(
    frame: pl.DataFrame,
    y: str,
    xs: Sequence[str],
    *,
    label: str,
    allowed: Sequence[str] | None = None,
    weight: bool = False,
    within_sd: bool = False,
    verbose: bool = True,
) -> Horse:
    """y ~ standardised xs + country FE + survey-year trend, country-clustered SE."""
    f = frame.drop_nulls([y, *xs])
    f, sds = standardize(f, xs, within="iso3" if within_sd else None)
    formula = f"{y} ~ {' + '.join(xs)} + {FE_TREND}"
    if weight:
        est = fit_w(with_country_weight(f), formula, label=label, weight="w_eq")
    else:
        est = fit(f, formula, label=label, fe=False)
    lead = leader({k: est.coefs[k] for k in xs}, allowed)
    if verbose:
        print(f"{label}  n={est.n} G={est.countries} r2={est.extra['r2']:.3f}")
        for k in xs:
            b, se, lo, hi = est.coefs[k]
            star = "*" if lo > 0 or hi < 0 else " "
            print(
                f"    {k:<9} {b:+.3f} (se {se:.3f}) [{lo:+.3f}, {hi:+.3f}]{star}  SD={sds[k]:.3f}"
                f"  ({VAR_LABEL[k]})"
            )
        tr = est.coefs["survey_year"]
        print(f"    trend     {tr[0]:+.4f} per year [{tr[2]:+.4f}, {tr[3]:+.4f}]")
        print(f"    -> leader: {lead} ({candidate_of(lead) if lead else 'none'})")
    return Horse(label, est, sds, lead)


def singles(
    frame: pl.DataFrame, y: str, xs: Sequence[str], *, tag: str, same_sample: bool
) -> dict[str, Coef]:
    """Each variable alone (same FE + trend). same_sample: on the joint listwise sample."""
    base = frame.drop_nulls([y, *xs]) if same_sample else frame
    out: dict[str, Coef] = {}
    for x in xs:
        h = horse(base, y, [x], label=f"{tag} {x} alone", verbose=False)
        out[x] = h.est.coefs[x]
        b, _, lo, hi = out[x]
        star = "*" if lo > 0 or hi < 0 else " "
        print(
            f"{tag:<26} {x:<9} alone: {b:+.3f} [{lo:+.3f}, {hi:+.3f}]{star}  n={h.est.n} "
            f"G={h.est.countries}"
        )
    return out


@dataclass(frozen=True)
class X3Result:
    rho: dict[str, tuple[float, float, int]]  # var -> (rho, p, n)
    lead: str | None
    pairs: pl.DataFrame


def spearman(a: Sequence[float], b: Sequence[float]) -> tuple[float, float]:
    from scipy.stats import spearmanr

    r = spearmanr(a, b)
    return float(r.statistic), float(r.pvalue)


def run_x3(ne: pl.DataFrame, tag: str, *, joint: bool = True) -> X3Result:
    xs = ("emp", "att_pri", "mcpr")
    rho: dict[str, tuple[float, float, int]] = {}
    pf_joint = pair_frame(ne, ("wanted_tfr", *xs), min_gap=8, mode="first_last")
    for x in xs:
        pf = pf_joint if joint else pair_frame(ne, ("wanted_tfr", x), min_gap=8, mode="first_last")
        r, p = spearman(pf["d_wanted_tfr"].to_list(), pf[f"d_{x}"].to_list())
        rho[x] = (r, p, pf.height)
        print(
            f"[{tag}] X3 {'joint' if joint else 'pairwise'} Δwanted(No-edu) vs Δ{x}: "
            f"Spearman ρ={r:+.3f} p={p:.3f} n={pf.height} countries; median Δ{x}="
            f"{statistics.median(pf[f'd_{x}'].to_list()):+.2f}, median Δwanted="
            f"{statistics.median(pf['d_wanted_tfr'].to_list()):+.2f}"
        )
    sig = [k for k in xs if rho[k][1] < 0.05]
    lead = sorted(sig, key=lambda k: (-abs(rho[k][0]), k))[0] if sig else None
    print(f"[{tag}] X3 leader (|ρ| max with p<0.05): {lead} ({candidate_of(lead)})")
    return X3Result(rho, lead, pf_joint)


@dataclass(frozen=True)
class X4Result:
    g0: Coef
    g1: Coef
    emp_coef: Coef
    shrink: float
    emp_grad: dict[str, Coef]
    n: int
    supports_w: bool


def run_x4(cells: pl.DataFrame, tag: str, *, weight: bool = False) -> X4Result:
    f = cells.drop_nulls(["wanted_tfr", "women_employed"])
    dums = "e_pri + e_sec + e_hi"
    fe = "C(survey_id)"

    def est(formula: str, label: str) -> Est:
        if weight:
            return fit_w(with_country_weight(f), formula, label=label, weight="w_eq")
        return fit(f, formula, label=label, fe=False)

    e0 = est(f"wanted_tfr ~ {dums} + {fe}", f"[{tag}] X4 g_w")
    e1 = est(f"wanted_tfr ~ {dums} + women_employed + {fe}", f"[{tag}] X4 g_w + emp")
    eg = est(f"women_employed ~ {dums} + {fe}", f"[{tag}] X4 emp gradient")
    g0, g1, ec = e0.coefs["e_sec"], e1.coefs["e_sec"], e1.coefs["women_employed"]
    shrink = 1.0 - g1[0] / g0[0]
    grad = {
        k: eg.coefs[v]
        for k, v in (("Primary", "e_pri"), ("Secondary", "e_sec"), ("Higher", "e_hi"))
    }
    # W-consistent (fixed before running): employment, within survey, is negatively associated
    # with wanted fertility (CI < 0) AND the Secondary − None gap shrinks when it is added.
    supports = ec[3] < 0 and shrink > 0
    print(
        f"[{tag}] X4 cells n={e0.n} surveys={f['survey_id'].n_unique()} G={e0.countries}"
        f"{' (country-equal)' if weight else ''}\n"
        f"    g_w (Sec−None) without emp {g0[0]:+.3f} [{g0[2]:+.3f}, {g0[3]:+.3f}] -> with emp "
        f"{g1[0]:+.3f} [{g1[2]:+.3f}, {g1[3]:+.3f}]  shrink={shrink:+.1%}\n"
        f"    women_employed (per pp, within survey) {ec[0]:+.4f} [{ec[2]:+.4f}, {ec[3]:+.4f}]\n"
        "    employment gradient vs No education (pp): "
        + ", ".join(f"{k} {v[0]:+.1f} [{v[2]:+.1f}, {v[3]:+.1f}]" for k, v in grad.items())
        + f"\n    -> X4 supports W: {supports}"
    )
    return X4Result(g0, g1, ec, shrink, grad, e0.n, supports)


@dataclass(frozen=True)
class X5Result:
    median: float
    share_up: float
    n: int
    by_edu: dict[str, tuple[float, float, int]]
    pairs: pl.DataFrame


def run_x5(cells: pl.DataFrame, st: pl.DataFrame, tag: str) -> X5Result:
    reg = st.select("survey_id", "region")
    by: dict[str, tuple[float, float, int]] = {}
    keep = pl.DataFrame()
    for e in (*EDU, "Total"):
        if e == "Total":
            fr = st.select("survey_id", "iso3", "survey_year", "region", "women_employed")
        else:
            fr = (
                cells.filter(pl.col("edu") == e)
                .select("survey_id", "iso3", "survey_year", "women_employed")
                .join(reg, on="survey_id", how="left")
            )
        pf = pair_frame(
            fr.sort("iso3", "survey_year", "survey_id"),
            ("women_employed",),
            min_gap=8,
            mode="first_last",
        )
        dv = pf["d_women_employed"].to_list()
        by[e] = (statistics.median(dv), sum(v > 0 for v in dv) / len(dv), len(dv))
        print(
            f"[{tag}] X5 women_employed {e:<13} first→last (>=8 y): countries={len(dv)} "
            f"median Δ={by[e][0]:+.1f} pp, mean Δ={statistics.mean(dv):+.1f}, rose in "
            f"{sum(v > 0 for v in dv)}/{len(dv)} ({by[e][1]:.0%}); median level first "
            f"{statistics.median(pf['women_employed_0'].to_list()):.1f}%"
        )
        if e == "No education":
            keep = pf
    m, sh, n = by["No education"]
    return X5Result(m, sh, n, by, keep)


# ---------------------------------------------------------------- figures
def fig_x1(main: Horse, single_same: Mapping[str, Coef], path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ys = list(range(len(X1_VARS)))[::-1]
    for off, (lab, src, col) in enumerate(
        (
            ("joint (horse race)", {k: main.est.coefs[k] for k in X1_VARS}, BLUE_RAMP[3]),
            ("each alone (same sample)", single_same, ORANGE),
        )
    ):
        yy = [y + (0.15 if off == 0 else -0.15) for y in ys]
        b = [src[k][0] for k in X1_VARS]
        lo = [src[k][0] - src[k][2] for k in X1_VARS]
        hi = [src[k][3] - src[k][0] for k in X1_VARS]
        ax.errorbar(b, yy, xerr=[lo, hi], fmt="o", color=col, ms=5, capsize=2, label=lab)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_yticks(ys)
    ax.set_yticklabels([VAR_LABEL[k] for k in X1_VARS], fontsize=8)
    ax.set_xlabel("wanted TFR, no-education women: change per 1 SD of x (children)", fontsize=8)
    ax.set_title(
        "X1: what moves with wanted fertility among women with no education?\n"
        f"country FE + survey-year trend, 95% CI clustered by country\n(n={main.est.n} surveys, "
        f"{main.est.countries} countries)",
        fontsize=9,
        color=INK,
    )
    _style(ax)
    ax.grid(axis="x", color="#e5e5e5", linewidth=0.6)
    ax.legend(fontsize=7, frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    _foot(fig, DHS_SOURCE)
    _save(fig, path)


def fig_x3(x3: X3Result, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.8), sharey=True)
    pf = x3.pairs
    for ax, x in zip(axes, ("emp", "att_pri", "mcpr"), strict=True):
        ax.scatter(pf[f"d_{x}"], pf["d_wanted_tfr"], s=14, color=BLUE_RAMP[2], alpha=0.8)
        r, p, n = x3.rho[x]
        ax.axhline(0, color=MUTED, lw=0.7)
        ax.axvline(0, color=MUTED, lw=0.7)
        ax.set_xlabel(f"Δ {VAR_LABEL[x]} (pp)", fontsize=8)
        ax.set_title(f"Spearman ρ={r:+.2f} (p={p:.2f}, n={n})", fontsize=8, color=INK)
        _style(ax)
    axes[0].set_ylabel("Δ wanted TFR, no education (children)", fontsize=8)
    fig.suptitle(
        "X3: first→last survey changes (>= 8 years apart), one point per country", fontsize=9
    )
    _foot(fig, DHS_SOURCE + " Attendance is the survey Total (children of all mothers).")
    _save(fig, path)


def fig_x4(x4: X4Result, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    ax = axes[0]
    vals = [x4.g0, x4.g1]
    ax.bar([0, 1], [v[0] for v in vals], color=[BLUE_RAMP[1], BLUE_RAMP[3]], width=0.6)
    ax.errorbar(
        [0, 1],
        [v[0] for v in vals],
        yerr=[[v[0] - v[2] for v in vals], [v[3] - v[0] for v in vals]],
        fmt="none",
        color=INK,
        capsize=3,
    )
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["survey FE only", "+ women employed (cell)"], fontsize=8)
    ax.set_ylabel("Secondary − No education, wanted TFR (children)", fontsize=8)
    ax.set_title(f"gap shrinks by {x4.shrink:.0%} (n={x4.n} cells)", fontsize=9, color=INK)
    _style(ax)
    ax = axes[1]
    labs = list(x4.emp_grad)
    ax.bar(range(len(labs)), [x4.emp_grad[k][0] for k in labs], color=ORANGE, width=0.6)
    ax.errorbar(
        range(len(labs)),
        [x4.emp_grad[k][0] for k in labs],
        yerr=[
            [x4.emp_grad[k][0] - x4.emp_grad[k][2] for k in labs],
            [x4.emp_grad[k][3] - x4.emp_grad[k][0] for k in labs],
        ],
        fmt="none",
        color=INK,
        capsize=3,
    )
    ax.axhline(0, color=MUTED, lw=0.7)
    ax.set_xticks(range(len(labs)))
    ax.set_xticklabels(labs, fontsize=8)
    ax.set_ylabel("women employed, difference vs No education (pp)", fontsize=8)
    ax.set_title("employment gradient by education (within survey)", fontsize=9, color=INK)
    _style(ax)
    fig.suptitle("X4: survey × education cells, survey FE, 95% CI clustered by country", fontsize=9)
    _foot(fig, DHS_SOURCE)
    _save(fig, path)


def fig_x5(x5: X5Result, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 7.0), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axes[0]
    pf = x5.pairs.sort("d_women_employed")
    for i, r in enumerate(pf.iter_rows(named=True)):
        a, b = r["women_employed_0"], r["women_employed_0"] + r["d_women_employed"]
        ax.plot([a, b], [i, i], color=BLUE_RAMP[1] if b > a else ORANGE, lw=1.2)
        ax.plot([b], [i], "o", color=BLUE_RAMP[3] if b > a else ORANGE, ms=3)
    ax.set_yticks(range(pf.height))
    ax.set_yticklabels(pf["iso3"].to_list(), fontsize=5)
    ax.set_xlabel("women with no education currently employed (%), first → last survey", fontsize=8)
    ax.set_title(
        f"No education: median change {x5.median:+.1f} pp, rose in {x5.share_up:.0%} "
        f"(n={x5.n} countries)",
        fontsize=8,
        color=INK,
    )
    _style(ax)
    ax = axes[1]
    labs = list(x5.by_edu)
    ax.bar(range(len(labs)), [x5.by_edu[k][0] for k in labs], color=BLUE_RAMP[2], width=0.6)
    for i, k in enumerate(labs):
        ax.text(i, x5.by_edu[k][0], f"n={x5.by_edu[k][2]}", ha="center", va="bottom", fontsize=6)
    ax.axhline(0, color=MUTED, lw=0.7)
    ax.set_xticks(range(len(labs)))
    ax.set_xticklabels(labs, fontsize=7, rotation=20)
    ax.set_ylabel("median first→last change (pp)", fontsize=8)
    ax.set_title("by education group", fontsize=9, color=INK)
    _style(ax)
    fig.suptitle(
        "X5: did employment of women with no education rise? (>= 8 years apart)", fontsize=9
    )
    _foot(fig, DHS_SOURCE)
    _save(fig, path)


# ---------------------------------------------------------------- run
def describe(d: pl.DataFrame, st: pl.DataFrame, ne: pl.DataFrame, tot: pl.DataFrame) -> None:
    print("== Data ==")
    new = (
        "women_employed",
        "married_employed",
        "married_cash_only",
        "married_cash_inkind",
        "child_primary_attendance",
        "child_secondary_attendance",
    )
    print(
        f"dhs_mechanisms rows={d.height} surveys={d['survey_id'].n_unique()} "
        f"countries={d['iso3'].n_unique()} metrics={d['metric'].n_unique()}"
    )
    for m in new:
        s = d.filter(pl.col("metric") == m)
        for (cat,), g in s.group_by(["characteristic_category"], maintain_order=True):
            print(
                f"  {m:<27} {cat:<16} rows={g.height:>5} surveys={g['survey_id'].n_unique():>3} "
                f"countries={g['iso3'].n_unique():>2} years={int(_x(g['survey_year'].min()))}–"
                f"{int(_x(g['survey_year'].max()))}"
            )
    c = st["married_cash_employed"].drop_nulls()
    print(
        f"  married_cash_employed (derived) surveys={c.len()} median={_x(c.median()):.1f}% "
        f"min={_x(c.min()):.1f} max={_x(c.max()):.1f}"
    )
    for lab, fr, xs in (("X1 No-edu", ne, X1_VARS), ("X2 Total", tot, X2_VARS)):
        f = fr.drop_nulls(["wanted_tfr", *xs])
        print(
            f"  {lab} complete cases: surveys={f.height} countries={f['iso3'].n_unique()} "
            f"years={int(_x(f['survey_year'].min()))}–{int(_x(f['survey_year'].max()))} types="
            f"{dict(sorted(f['survey_type'].value_counts().iter_rows()))}"
        )
        for x in ("wanted_tfr", *xs):
            v = f[x]
            print(
                f"      {x:<10} mean={_x(v.mean()):8.3f} sd={_x(v.std()):7.3f}"
                f" min={_x(v.min()):8.3f} max={_x(v.max()):8.3f}"
            )


def run(data_dir: Path, fig_dir: Path) -> None:
    d = pl.read_parquet(data_dir / DHS_MART)
    panel = pl.read_parquet(data_dir / PANEL_MART)
    fig_dir.mkdir(parents=True, exist_ok=True)
    st = add_derived(survey_table(d, panel))
    cells = cell_table(d, st)
    ne = no_edu_frame(cells, st)
    tot = total_frame(st)
    describe(d, st, ne, tot)

    print("\n== X1 (main): No-education cell wanted TFR horse race ==")
    x1 = horse(ne, "wanted_tfr", X1_VARS, label="X1 joint", allowed=X1_VARS)
    print("-- X1 each variable alone, same sample --")
    s_same = singles(ne, "wanted_tfr", X1_VARS, tag="X1 single(same sample)", same_sample=True)
    print("-- X1 each variable alone, own maximal sample --")
    singles(ne, "wanted_tfr", X1_VARS, tag="X1 single(max sample)", same_sample=False)

    print("\n== X2: Total wanted TFR horse race ==")
    x2 = horse(tot, "wanted_tfr", X2_VARS, label="X2 joint", allowed=tuple(CANDIDATE))
    singles(tot, "wanted_tfr", X2_VARS, tag="X2 single(same sample)", same_sample=True)

    print("\n== X3: first→last changes, No-education group ==")
    x3 = run_x3(ne, "main")

    print("\n== X4: within-survey mediation of the education gradient by employment ==")
    x4 = run_x4(cells, "main")

    print("\n== X5: employment of women with no education, first→last ==")
    x5 = run_x5(cells, st, "main")

    x1c = candidate_of(x1.lead)
    checks = {"X2": candidate_of(x2.lead), "X3": candidate_of(x3.lead)}
    dec = decide(x1c, x5_median=x5.median, checks=checks, x4_supports_w=x4.supports_w)
    print("\n== DECISION (pre-fixed rule) ==")
    print(
        f"X1 leader={x1.lead} -> {x1c}; X2 -> {checks['X2']}; X3 -> {checks['X3']}; "
        f"X4 supports W={x4.supports_w}; X5 median Δ(No-edu emp)={x5.median:+.1f} pp"
    )
    if x1.lead is not None:
        b = x1.est.coefs[x1.lead][0]
        print(f"X1 leader sign: {b:+.3f} children per SD")
    print(f"SELECTED: {dec.code}")
    print(f"判定: {dec.sentence}")

    robustness(ne, tot, cells, x5)
    exploratory(d, st, cells, ne, tot)
    e5_employment_timing(x5)

    fig_x1(x1, s_same, fig_dir / "h8b_01_x1_horse_race.png")
    fig_x3(x3, fig_dir / "h8b_02_x3_changes.png")
    fig_x4(x4, fig_dir / "h8b_03_x4_gradient.png")
    fig_x5(x5, fig_dir / "h8b_04_x5_employment.png")


def _verdict_line(tag: str, h: Horse, x5: X5Result) -> None:
    c = candidate_of(h.lead)
    w_note = ""
    if c == "W" and x5.median <= 0:
        w_note = " (W would fail X5)"
    print(f"[{tag}] -> X1-rule leader {h.lead} ({c}){w_note}")


def robustness(ne: pl.DataFrame, tot: pl.DataFrame, cells: pl.DataFrame, x5: X5Result) -> None:
    print("\n== Robustness (pre-registered list, all reported) ==")
    one_pri = ("emp", "mcpr", "att_pri", "ln_u5")
    one_sec = ("emp", "mcpr", "att_sec", "ln_u5")
    rows: list[tuple[str, pl.DataFrame, Sequence[str], dict[str, Any]]] = [
        ("R X1 primary attendance only", ne, one_pri, {}),
        ("R X1 secondary attendance only", ne, one_sec, {}),
        ("R X1 1999+", ne.filter(pl.col("survey_year") >= 1999), X1_VARS, {}),
        ("R X1 DHS surveys only", ne.filter(pl.col("survey_type") == "DHS"), X1_VARS, {}),
        ("R X1 country-equal weight", ne, X1_VARS, {"weight": True}),
    ]
    for lab, fr, xs, kw in rows:
        h = horse(fr, "wanted_tfr", xs, label=lab, allowed=xs, **kw)
        _verdict_line(lab, h, x5)
    print("-- X2 variants --")
    x2rows: list[tuple[str, pl.DataFrame, Sequence[str], dict[str, Any]]] = [
        (
            "R X2 married_cash_employed instead of women_employed",
            tot,
            ("cash_emp", "att_pri", "att_sec", "mcpr", "ln_u5", "sec"),
            {},
        ),
        (
            "R X2 women_employed only (no cash)",
            tot,
            ("emp_tot", "att_pri", "att_sec", "mcpr", "ln_u5", "sec"),
            {},
        ),
        (
            "R X2 primary attendance only",
            tot,
            ("cash_emp", "emp_tot", "att_pri", "mcpr", "ln_u5", "sec"),
            {},
        ),
        (
            "R X2 secondary attendance only",
            tot,
            ("cash_emp", "emp_tot", "att_sec", "mcpr", "ln_u5", "sec"),
            {},
        ),
        ("R X2 1999+", tot.filter(pl.col("survey_year") >= 1999), X2_VARS, {}),
        ("R X2 DHS surveys only", tot.filter(pl.col("survey_type") == "DHS"), X2_VARS, {}),
        ("R X2 country-equal weight", tot, X2_VARS, {"weight": True}),
    ]
    for lab, fr, xs, kw in x2rows:
        h = horse(fr, "wanted_tfr", xs, label=lab, allowed=tuple(CANDIDATE), **kw)
        print(f"[{lab}] -> leader {h.lead} ({candidate_of(h.lead)})")
    print("-- X3 / X4 variants --")
    run_x3(ne, "R pairwise samples", joint=False)
    run_x3(ne.filter(pl.col("survey_year") >= 1999), "R 1999+")
    run_x4(cells, "R country-equal", weight=True)
    run_x4(cells.filter(pl.col("survey_year") >= 1999), "R 1999+")
    print("-- added at implementation (not in the design list): SD convention --")
    h = horse(
        ne, "wanted_tfr", X1_VARS, label="R X1 within-country SD", allowed=X1_VARS, within_sd=True
    )
    _verdict_line("R X1 within-country SD", h, x5)


def exploratory(
    d: pl.DataFrame, st: pl.DataFrame, cells: pl.DataFrame, ne: pl.DataFrame, tot: pl.DataFrame
) -> None:
    print("\n== Exploratory (post hoc, not part of the decision) ==")
    # E1: kind of work — cash-earning vs non-cash (unpaid / in-kind only) married women.
    horse(
        tot,
        "wanted_tfr",
        ("cash_emp", "noncash_emp", "mcpr", "ln_u5", "sec"),
        label="E1 Total wanted ~ cash vs non-cash employment",
    )
    # E2: wealth quintiles — within each quintile, does employment move with wanted fertility?
    q = d.filter(
        (pl.col("characteristic_category") == "Wealth quintile")
        & pl.col("metric").is_in(["wanted_tfr", "women_employed"])
    ).pivot(
        on="metric",
        index=["survey_id", "iso3", "survey_year", "characteristic_label"],
        values="value",
        aggregate_function=None,
    )
    q = q.rename({"characteristic_label": "quint"}).drop_nulls(["wanted_tfr", "women_employed"])
    q = q.join(
        st.select("survey_id", "ln_u5", pl.col("modern_contraception_married").alias("mcpr")),
        on="survey_id",
        how="left",
    )
    for k in ("Lowest", "Highest"):
        horse(
            q.filter(pl.col("quint") == k).rename({"women_employed": "emp_q"}),
            "wanted_tfr",
            ("emp_q", "mcpr", "ln_u5"),
            label=f"E2 wealth quintile {k}: wanted ~ emp(quintile) + mcpr(Total) + ln U5",
        )
    eq = fit(
        q.with_columns(
            *[
                (pl.col("quint") == k).cast(pl.Float64).alias(f"q_{k}")
                for k in ("Second", "Middle", "Fourth", "Highest")
            ]
        ),
        "wanted_tfr ~ women_employed + q_Second + q_Middle + q_Fourth + q_Highest + C(survey_id)",
        label="E2b quintile cells, survey FE: wanted ~ women_employed + quintile",
        fe=False,
    )
    print(eq.line())
    # E3: No-education cell, actual TFR with the same horse race (does the pattern hold for TFR?)
    horse(ne, "tfr", X1_VARS, label="E3 No-edu cell TFR horse race")
    # E4: is No-edu employment a poverty signal? correlation with wealth gradient of employment
    emp_q = d.filter(pl.col("metric") == "women_employed")
    meds = [
        (k, _x(emp_q.filter(pl.col("characteristic_label") == k)["value"].median()))
        for k in ("Lowest", "Second", "Middle", "Fourth", "Highest")
    ]
    print(
        "E4 employment by wealth quintile (median across surveys, %): "
        + ", ".join(f"{k} {v:.1f}" for k, v in meds)
    )


def e5_employment_timing(x5: X5Result) -> None:
    """E5 (exploratory): is the fall in No-education employment concentrated in pairs whose last
    survey is recent (possible questionnaire / definition change)? Descriptive split only."""
    pf = x5.pairs
    for lab, cond in (
        ("last survey < 2014", pl.col("y1") < 2014),
        ("last survey >= 2014", pl.col("y1") >= 2014),
    ):
        g = pf.filter(cond)
        if g.height == 0:
            continue
        dv = g["d_women_employed"].to_list()
        print(
            f"E5 No-edu employment first→last, {lab}: countries={g.height} median Δ="
            f"{statistics.median(dv):+.1f} pp, rose in {sum(v > 0 for v in dv)}/{g.height}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
