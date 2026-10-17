"""H8c（事後追加）: 子ども一人当たりの教育投資と学歴社会の圧力（仮説 Q）は、
出生率が 3 人前後から 2 人未満へ下がる段階を説明するか。

事前固定: design/themes/growth-fertility.md「### H8c」（2026-10-18）。H8/H8b の結果を見た後の
追加検証で、検定 Y1〜Y5・判定規則・最終スタンスの文型・頑健性リストは追加データを見る前に
固定した。結果は H8 の判定（M1〜M5）を変えない。

  Y1（主、WDI）  H8 T6 と同じ 10 年長期差分（端点 ±2 年の最近傍、区間開始 TFR < 3、国＋期間 FE、
                 国クラスタ SE、段階の標本の SD で標準化）:
                 Δtfr ~ Δtert_enrol + Δschool_life_exp + Δeduc_exp_gdp + Δfem_sec_enrol
                        + Δln gdp_pcap_const + Δln u5mr
                 短い標本の版: + Δspend_per_student_sec + Δprivate_sec_share、区間 1995→2005→2015
  Y2  OECD 横断  tfr ~ private_share_1T8 + rel_earn_5T8 + ln spend_per_student_Q(1T8)
                        + ln gdp_pcap_ppp
                 （HC1、説明変数は標本の SD で標準化）＋ Spearman。相対賃金なし版も。
  Y3  OECD within 2005–2023 年次、tfr ~ private_share + rel_earn + ln spend
                 + 国 FE + 年 FE（国クラスタ）。
                 補助: 2012（±2）→ 最新の長期差分の横断（HC1）
  Y4  DHS        H8b X2（Total の wanted TFR の horse race）に調査年（±2 年の最近傍）の
                 spend_per_student_sec と tert_enrol を加える（段階 1 の補足、判定外）
  Y5  記述       JPN・KOR vs DNK・FIN・NOR・SWE の推移図

「最新年」の規則（結果を見る前に固定）: 各国について、その式の変数（tfr を含む）が**すべて**
観測される年のうち 2012 年以降で最も新しい年を使う（`latest_common_year`）。国ごとに年が違い得るので
選んだ年を stdout に出す。

判定（事前固定、`global_side`/`oecd_side`/`verdict_q`）:
  全世界 = Y1 主仕様の段階 2 で Δtert_enrol または Δschool_life_exp が負・CI∌0、かつ |b| が同式の
           他の全変数以上（他変数の CI は問わない）
  OECD   = Y2 主仕様または Y3 主仕様で private_share または rel_earn が負・CI∌0。ただし同じ変数の
           もう一方の検定の点推定が正なら「符号の食い違い」としてその変数は数えない
           （設計の「Y2 と Y3 で符号が食い違えば不成立」を、点推定の符号で運用。
           結果を見る前に固定）
  両方 → 支持、片方 → 部分的支持、どちらも無し → 不支持。
  判定対象の変数で正・CI∌0 は「逆向き」と明記。
  一人当たり支出は機械的な逆因果（子が少ないほど 1 人当たりが増える）を含むので判定に使わない。

決定的スクリプト。入力は data/marts/{growth_fertility_panel, oecd_education_finance,
dhs_mechanisms}.parquet。乱数・現在時刻は使わない。欠損は補完しない（listwise）。H8・H8b の
スクリプトは変更せず関数を import する。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋ヘルパ（extract, oecd_wide, variant_spec, latest_common_year, endpoints, attach_nearest,
global_side, oecd_side, reverse_flags, verdict_q, final_stance）は
tests/test_analysis_h8c.py で検証する。
"""

from __future__ import annotations

import argparse
import copy
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261017_h8_mechanisms as h8
from theme_growth_fertility.analysis import a20261018_h8b_within_group as h8b
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

THEME_DIR = h8.THEME_DIR
REPO_ROOT = h8.REPO_ROOT
PANEL_MART = h8.PANEL_MART
OECD_MART = Path("marts") / "oecd_education_finance.parquet"

Coef = tuple[float, float, float, float]  # (b, se, lo, hi)

EAST = ("JPN", "KOR")
NORDIC = ("DNK", "FIN", "NOR", "SWE")
FOCUS = (*EAST, *NORDIC)

# ---- Y1 (WDI)
Y1_COLS = ("tfr", "ln_u5", "sec", "ln_gdp", "smam", "tert", "sle", "eexp", "sps", "pss")
Y1_VARS = ("d_tert", "d_sle", "d_eexp", "d_sec", "d_ln_gdp", "d_ln_u5")
Y1_SHORT_VARS = (*Y1_VARS, "d_sps", "d_pss")
Y1_TARGETS = ("d_tert", "d_sle")
Y1_LABEL = {
    "d_tert": "tertiary enrolment (gross %)",
    "d_sle": "school life expectancy (years)",
    "d_eexp": "gov. education spending (% GDP)",
    "d_sec": "female sec. enrolment",
    "d_ln_gdp": "ln GDP pc (const.)",
    "d_ln_u5": "ln U5MR",
    "d_sps": "gov. spend per sec. student (% GDP pc)",
    "d_pss": "private sec. enrolment share (%)",
    "d_smam": "female mean age at marriage",
}

# ---- Y2 / Y3 (OECD EAG). Filters on the long mart; each must give one value per iso3 × year.
OECD_SPEC: dict[str, dict[str, str]] = {
    "priv": {
        "dataset": "fin_source",
        "unit": "PT_EXP",
        "exp_source": "S1D_NON_EDU",
        "education_level": "ISCED11_1T8",
    },
    "rel": {
        "dataset": "earn_rel",
        "education_level": "ISCED11A_5T8",
        "sex": "_T",
        "work_time": "_T",
    },
    "spend": {
        "dataset": "fin_perstud",
        "price_base": "Q",
        "exp_source": "_T",
        "education_level": "ISCED11_1T8",
    },
}
OECD_TARGETS = ("priv", "rel")
Y2_VARS = ("priv", "rel", "ln_spend", "ln_gdp")
Y2_NOREL = ("priv", "ln_spend", "ln_gdp")
Y3_VARS = ("priv", "rel", "ln_spend")
OECD_LABEL = {
    "priv": "private share of education spending (%)",
    "rel": "tertiary relative earnings (upper sec. = 100)",
    "ln_spend": "ln spending per student (USD PPP 2020)",
    "ln_gdp": "ln GDP pc (PPP)",
    "d_priv": "Δ private share",
    "d_rel": "Δ relative earnings",
    "d_ln_spend": "Δ ln spending per student",
}
LATEST_MIN_YEAR = 2012
Y3_YEARS = (2005, 2023)

VAR_JA = {
    "d_tert": "高等教育進学率",
    "d_sle": "期待就学年数",
    "priv": "教育費の私的負担割合",
    "rel": "高等教育修了者の相対賃金（学歴による賃金差）",
}
VERDICT_JA = {
    "support": "支持",
    "partial_global": "部分的支持（全世界の側のみ）",
    "partial_oecd": "部分的支持（OECD の側のみ）",
    "no": "不支持",
}
WDI_SOURCE = "Source: World Bank WDI (CC BY 4.0; UIS education series via WDI)."
OECD_SOURCE = (
    "Source: OECD (2026), Education at a Glance database (UOE finance / LSO earnings), "
    "https://sdmx.oecd.org; TFR, GDP: World Bank WDI."
)


# ---------------------------------------------------------------- pure helpers (tested)
def extract(o: pl.DataFrame, name: str, filters: Mapping[str, str]) -> pl.DataFrame:
    """Long OECD mart -> (iso3, year, <name>) for the rows matching every filter. A filter on a
    missing column or more than one row per iso3 × year raises ValueError (fail-closed)."""
    f = o
    for col, val in filters.items():
        if col not in o.columns:
            raise ValueError(f"filter column {col!r} not in mart")
        f = f.filter(pl.col(col) == val)
    out = f.select("iso3", "year", pl.col("value").alias(name)).sort("iso3", "year")
    if out.select("iso3", "year").is_duplicated().any():
        raise ValueError(f"{name}: duplicate iso3 × year after filtering {dict(filters)}")
    return out


def oecd_wide(o: pl.DataFrame, spec: Mapping[str, Mapping[str, str]]) -> pl.DataFrame:
    """Full outer join of the `spec` series on (iso3, year), columns in spec order."""
    out: pl.DataFrame | None = None
    for name, filters in spec.items():
        s = extract(o, name, filters)
        out = s if out is None else out.join(s, on=["iso3", "year"], how="full", coalesce=True)
    if out is None:
        raise ValueError("empty spec")
    return out.select("iso3", "year", *spec).sort("iso3", "year")


def variant_spec(changes: Mapping[str, Mapping[str, str]]) -> dict[str, dict[str, str]]:
    """Copy of OECD_SPEC with the named fields of the named series replaced."""
    s = copy.deepcopy(OECD_SPEC)
    for name, ch in changes.items():
        s[name] = {**s[name], **ch}
    return s


def latest_common_year(frame: pl.DataFrame, cols: Sequence[str], *, min_year: int) -> pl.DataFrame:
    """Per iso3, the row of the latest year >= min_year at which every `cols` is observed.
    Countries without such a year are dropped. Sorted by iso3."""
    return (
        frame.filter(pl.col("year") >= min_year)
        .drop_nulls(list(cols))
        .sort("iso3", "year")
        .group_by("iso3", maintain_order=True)
        .last()
    )


def endpoints(
    frame: pl.DataFrame, cols: Sequence[str], *, start: int, window: int, min_gap: int
) -> pl.DataFrame:
    """Per iso3 over years where all `cols` are observed: y0 = year nearest to `start` within
    ±window (tie -> earlier), y1 = latest such year; kept if y1 − y0 >= min_gap.
    Columns: iso3, y0, y1, then <c>_0 and d_<c> for each c."""
    full = frame.drop_nulls(list(cols)).sort("iso3", "year")
    rows: list[dict[str, Any]] = []
    for (iso,), g in full.group_by("iso3", maintain_order=True):
        by_year = {int(r["year"]): r for r in g.iter_rows(named=True)}
        y0 = h8.nearest_value({y: float(y) for y in by_year}, start, window)
        if y0 is None:
            continue
        y1 = max(by_year)
        if y1 - int(y0) < min_gap:
            continue
        a, b = by_year[int(y0)], by_year[y1]
        row: dict[str, Any] = {"iso3": iso, "y0": int(y0), "y1": y1}
        for c in cols:
            row[f"{c}_0"] = float(a[c])
            row[f"d_{c}"] = float(b[c]) - float(a[c])
        rows.append(row)
    schema: dict[str, Any] = {"iso3": pl.Utf8, "y0": pl.Int64, "y1": pl.Int64}
    for c in cols:
        schema[f"{c}_0"] = pl.Float64
        schema[f"d_{c}"] = pl.Float64
    return pl.DataFrame(rows, schema=schema, orient="row")


def attach_nearest(
    frame: pl.DataFrame,
    panel: pl.DataFrame,
    cols: Sequence[str],
    *,
    window: int,
    year_col: str = "survey_year",
) -> pl.DataFrame:
    """Add each panel column at the year nearest to frame[year_col] within ±window
    (tie -> earlier year, `h8.nearest_value`); None if no observation in the window."""
    obs: dict[str, dict[str, dict[int, float]]] = {c: {} for c in cols}
    for c in cols:
        for iso, year, v in panel.select("iso3", "year", c).drop_nulls().iter_rows():
            obs[c].setdefault(str(iso), {})[int(year)] = float(v)
    keys = frame.select("iso3", year_col).rows()
    return frame.with_columns(
        [
            pl.Series(
                c,
                [h8.nearest_value(obs[c].get(str(i), {}), int(y), window) for i, y in keys],
                dtype=pl.Float64,
            )
            for c in cols
        ]
    )


def _sig(c: Coef) -> bool:
    return c[2] > 0 or c[3] < 0


def global_side(
    coefs: Mapping[str, Coef], targets: Sequence[str] = Y1_TARGETS
) -> tuple[str | None, bool]:
    """Pre-fixed 全世界 condition on Y1 stage 2. Among `targets` that are negative with CI
    excluding 0, take the one with the largest |b| (ties -> name); it holds if its |b| is at
    least that of every other variable in the equation. Returns (that target or None, holds)."""
    cand = [t for t in targets if t in coefs and coefs[t][0] < 0 and _sig(coefs[t])]
    if not cand:
        return None, False
    t = sorted(cand, key=lambda k: (-abs(coefs[k][0]), k))[0]
    others = [abs(v[0]) for k, v in coefs.items() if k != t]
    return t, all(abs(coefs[t][0]) >= o for o in others)


def oecd_side(
    y2: Mapping[str, Coef] | None,
    y3: Mapping[str, Coef] | None,
    targets: Sequence[str] = OECD_TARGETS,
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """Pre-fixed OECD condition. A target qualifies if it is negative with CI excluding 0 in Y2
    or Y3 and the other test (if estimated) does not have a positive point estimate for it.
    Returns (holds, qualifying targets, targets dropped for a sign conflict)."""
    ok: list[str] = []
    conflict: list[str] = []
    for t in targets:
        tests = [d[t] for d in (y2, y3) if d is not None and t in d]
        if not any(c[0] < 0 and _sig(c) for c in tests):
            continue
        if any(c[0] > 0 for c in tests):
            conflict.append(t)
        else:
            ok.append(t)
    return bool(ok), tuple(ok), tuple(conflict)


def reverse_flags(coefs: Mapping[str, Coef], targets: Sequence[str]) -> list[str]:
    """Targets with a positive coefficient whose CI excludes 0 (「逆向き」)."""
    return [t for t in targets if t in coefs and coefs[t][0] > 0 and _sig(coefs[t])]


def verdict_q(global_ok: bool, oecd_ok: bool) -> str:
    if global_ok and oecd_ok:
        return "support"
    if global_ok:
        return "partial_global"
    if oecd_ok:
        return "partial_oecd"
    return "no"


def final_stance(
    verdict: str, *, global_var: str | None, oecd_vars: Sequence[str], reverse: Sequence[str]
) -> str:
    """Final stance sentence in the pre-registered form (design H8c 最終スタンスの文型)."""
    if verdict == "support":
        s = (
            "2 人未満への低下は、子どもに長く多く教育を与えることが当たり前になり、"
            "その費用を家計が負う社会ほど進んでいる（学歴社会の副作用）。"
        )
    elif verdict == "partial_global":
        g = VAR_JA[global_var] if global_var else "教育の長さ"
        s = (
            f"2 人未満への低下は、全世界では教育の長さ（{g}）の伸びと並走して進んでいるが、"
            "OECD の中で家計の教育費負担や学歴による賃金差が大きい国ほど出生率が低いとは"
            "確かめられない（部分的支持）。"
        )
    elif verdict == "partial_oecd":
        names = "・".join(VAR_JA[v] for v in oecd_vars) or "家計の教育費負担・学歴による賃金差"
        s = (
            "2 人未満への低下は、全世界では教育の長さ（高等教育進学率・期待就学年数）の伸びでは"
            f"説明できないが、OECD の中では{names}が高い国ほど出生率が低い（部分的支持）。"
        )
    elif verdict == "no":
        s = (
            "2 人未満への低下は、学歴社会の圧力でも説明できない（教育の長さ・家計の教育費負担・"
            "学歴による賃金差のどれも事前に決めた条件を満たさない）。"
            "要因は本シリーズの変数の外にある。"
        )
    else:
        raise ValueError(f"unknown verdict {verdict!r}")
    if reverse:
        names = "・".join(VAR_JA[v] for v in reverse)
        s += f"ただし{names}は逆向き（高いほど・伸びるほど出生率が高い）である。"
    return s


# ---------------------------------------------------------------- small utilities
def _i(v: Any) -> int:
    return int(v)


def _fmt(c: Coef) -> str:
    star = "*" if _sig(c) else " "
    return f"{c[0]:+.3f} [{c[2]:+.3f}, {c[3]:+.3f}]{star}"


def ols_hc1(frame: pl.DataFrame, y: str, xs: Sequence[str], *, label: str) -> Est:
    """Cross-sectional OLS with HC1 SE (one row per country)."""
    import statsmodels.formula.api as smf

    pdf = frame.to_pandas()
    res = smf.ols(f"{y} ~ {' + '.join(xs)}", data=pdf).fit(cov_type="HC1")
    ci = res.conf_int()
    coefs = {
        str(n): (float(res.params[n]), float(res.bse[n]), float(ci.loc[n, 0]), float(ci.loc[n, 1]))
        for n in res.params.index
        if n != "Intercept"
    }
    return Est(label, int(res.nobs), int(pdf["iso3"].nunique()), coefs, {"r2": float(res.rsquared)})


def _print_coefs(
    est: Est, xs: Sequence[str], labels: Mapping[str, str], sds: Mapping[str, float]
) -> None:
    print(f"{est.label}  n={est.n} G={est.countries} r2={est.extra['r2']:.3f}")
    for k in xs:
        sd = f"  SD={sds[k]:.3f}" if k in sds else ""
        print(f"    {k:<10} {_fmt(est.coefs[k])}{sd}  ({labels.get(k, k)})")


# ---------------------------------------------------------------- Y1 (WDI long differences)
def y1_base(panel: pl.DataFrame, *, trim: bool = True) -> pl.DataFrame:
    """H8 T6 base (ln U5MR, ln GDP const, female sec. enrolment, trimmed SMAM) + H8c columns."""
    base, _ = h8.t6_base(panel, trim=trim)
    return base.with_columns(
        pl.col("tert_enrol").alias("tert"),
        pl.col("school_life_exp").alias("sle"),
        pl.col("educ_exp_gdp").alias("eexp"),
        pl.col("spend_per_student_sec").alias("sps"),
        pl.col("private_sec_share").alias("pss"),
    )


@dataclass(frozen=True)
class Y1Result:
    s1: h8.T6Stage | None
    s2: h8.T6Stage | None
    ld: pl.DataFrame
    lead: str | None
    holds: bool
    reverse: list[str]


def _print_stage(label: str, st: h8.T6Stage | None, xs: Sequence[str]) -> None:
    if st is None:
        print(f"{label}: too few rows")
        return
    print(f"{label}  n={st.n} G={st.countries}")
    for x in xs:
        print(f"    {x:<9} {_fmt(st.coefs[x])}  ({Y1_LABEL[x]})")


def run_y1(
    base: pl.DataFrame,
    tag: str,
    *,
    xs: Sequence[str] = Y1_VARS,
    width: int = 10,
    cut: float = 3.0,
    start: int = 1970,
    end: int = 2020,
    stage1: bool = False,
    verbose: bool = True,
) -> Y1Result:
    ld = h8.long_diff_nearest(base, Y1_COLS, width=width, start=start, end=end)
    s1 = None
    if stage1:
        s1 = h8.t6_stage(ld.filter(pl.col("tfr_0") >= cut), xs, f"{tag} s1", verbose=False)
        if verbose:
            _print_stage(f"[{tag}] stage1 TFR0>={cut}", s1, xs)
    s2 = h8.t6_stage(ld.filter(pl.col("tfr_0") < cut), xs, f"{tag} s2", verbose=False)
    lead, holds, rev = None, False, []
    if s2 is not None:
        lead, holds = global_side(s2.coefs)
        rev = reverse_flags(s2.coefs, Y1_TARGETS)
    if verbose:
        _print_stage(f"[{tag}] stage2 TFR0<{cut}", s2, xs)
        print(
            f"[{tag}] 全世界 condition: lead={lead} holds={holds}  reverse={rev if rev else 'none'}"
        )
    return Y1Result(s1, s2, ld, lead, holds, rev)


# ---------------------------------------------------------------- Y2 / Y3 (OECD)
def oecd_panel(
    o: pl.DataFrame, panel: pl.DataFrame, spec: Mapping[str, Mapping[str, str]] = OECD_SPEC
) -> pl.DataFrame:
    """OECD wide series + WDI tfr and gdp_pcap_ppp; ln of spending and GDP."""
    w = oecd_wide(o, spec)
    p = panel.select("iso3", "year", "country", "tfr", "gdp_pcap_ppp")
    return (
        w.join(p, on=["iso3", "year"], how="left")
        .with_columns(
            pl.when(pl.col("spend") > 0).then(pl.col("spend").log()).alias("ln_spend"),
            pl.when(pl.col("gdp_pcap_ppp") > 0).then(pl.col("gdp_pcap_ppp").log()).alias("ln_gdp"),
        )
        .sort("iso3", "year")
    )


@dataclass(frozen=True)
class Y2Result:
    frame: pl.DataFrame  # one row per country (raw values)
    est: Est
    sds: dict[str, float]
    rho: dict[str, tuple[float, float]]


def run_y2(
    op: pl.DataFrame, tag: str, *, xs: Sequence[str] = Y2_VARS, verbose: bool = True
) -> Y2Result:
    cs = latest_common_year(op, ["tfr", *xs], min_year=LATEST_MIN_YEAR)
    f, sds = h8b.standardize(cs, xs)
    est = ols_hc1(f, "tfr", xs, label=f"[{tag}] Y2 OLS HC1 (standardised)")
    rho = {x: h8b.spearman(cs[x].to_list(), cs["tfr"].to_list()) for x in xs}
    if verbose:
        yrs = cs["year"].to_list()
        print(
            f"[{tag}] Y2 latest common year per country (>= {LATEST_MIN_YEAR}): n={cs.height}, "
            f"years {min(yrs)}–{max(yrs)}, median {statistics.median(yrs):.0f}"
        )
        print("    " + " ".join(f"{i}:{y}" for i, y in cs.select("iso3", "year").rows()))
        _print_coefs(est, xs, OECD_LABEL, sds)
        for x in xs:
            r, p = rho[x]
            print(f"    Spearman tfr × {x:<9} rho={r:+.3f} p={p:.3f}")
    return Y2Result(cs, est, sds, rho)


@dataclass(frozen=True)
class Y3Result:
    est: Est
    sds: dict[str, float]
    frame: pl.DataFrame


def run_y3(
    op: pl.DataFrame, tag: str, *, xs: Sequence[str] = Y3_VARS, verbose: bool = True
) -> Y3Result | None:
    f = op.filter(pl.col("year").is_between(*Y3_YEARS)).drop_nulls(["tfr", *xs])
    if f.height < 20 or f["iso3"].n_unique() < 5:
        print(f"[{tag}] Y3: too few rows (n={f.height})")
        return None
    fs, sds = h8b.standardize(f, xs)
    est = fit(fs, f"tfr ~ {' + '.join(xs)} + C(iso3) + C(year)", label=f"[{tag}] Y3 FE", fe=False)
    if verbose:
        print(
            f"[{tag}] Y3 within {Y3_YEARS[0]}–{Y3_YEARS[1]}: years {_i(f['year'].min())}–"
            f"{_i(f['year'].max())}, country-years={f.height}, countries={f['iso3'].n_unique()}"
        )
        _print_coefs(est, xs, OECD_LABEL, sds)
    return Y3Result(est, sds, f)


@dataclass(frozen=True)
class Y3LD:
    frame: pl.DataFrame
    est: Est
    rho: dict[str, tuple[float, float]]


def run_y3_ld(
    op: pl.DataFrame, tag: str, *, xs: Sequence[str] = Y3_VARS, verbose: bool = True
) -> Y3LD | None:
    ld = endpoints(op, ["tfr", *xs], start=2012, window=2, min_gap=5)
    dx = [f"d_{x}" for x in xs]
    if ld.height < len(dx) + 3:
        print(f"[{tag}] Y3-LD: too few countries (n={ld.height})")
        return None
    f, sds = h8b.standardize(ld, dx)
    est = ols_hc1(f, "d_tfr", dx, label=f"[{tag}] Y3-LD 2012→latest (HC1, standardised)")
    rho = {x: h8b.spearman(ld[x].to_list(), ld["d_tfr"].to_list()) for x in dx}
    if verbose:
        print(
            f"[{tag}] Y3-LD start years {sorted(set(ld['y0'].to_list()))}, end years "
            f"{_i(ld['y1'].min())}–{_i(ld['y1'].max())}; "
            f"median ΔTFR {statistics.median(ld['d_tfr'].to_list()):+.3f}"
        )
        _print_coefs(est, dx, OECD_LABEL, sds)
        for x in dx:
            r, p = rho[x]
            print(f"    Spearman Δtfr × {x:<11} rho={r:+.3f} p={p:.3f}")
    return Y3LD(ld, est, rho)


@dataclass(frozen=True)
class OecdSide:
    y2: Y2Result
    y3: Y3Result | None
    holds: bool
    vars: tuple[str, ...]
    conflicts: tuple[str, ...]
    reverse: list[str]


def run_oecd(op: pl.DataFrame, tag: str, *, verbose: bool = True) -> OecdSide:
    y2 = run_y2(op, tag, verbose=verbose)
    y3 = run_y3(op, tag, verbose=verbose)
    c2 = {t: y2.est.coefs[t] for t in OECD_TARGETS}
    c3 = None if y3 is None else {t: y3.est.coefs[t] for t in OECD_TARGETS}
    holds, vs, conf = oecd_side(c2, c3)
    rev = sorted(set(reverse_flags(c2, OECD_TARGETS)) | set(reverse_flags(c3 or {}, OECD_TARGETS)))
    print(
        f"[{tag}] OECD condition: holds={holds} vars={vs or 'none'} sign-conflicts="
        f"{conf or 'none'} reverse={rev or 'none'}"
    )
    return OecdSide(y2, y3, holds, vs, conf, rev)


# ---------------------------------------------------------------- Y4 (DHS × WDI)
Y4_EXTRA = ("sps", "tert")


def y4_frame(d: pl.DataFrame, panel: pl.DataFrame) -> pl.DataFrame:
    tot = h8b.total_frame(h8b.add_derived(h8.survey_table(d, panel)))
    p = panel.select(
        "iso3",
        "year",
        pl.col("spend_per_student_sec").alias("sps"),
        pl.col("tert_enrol").alias("tert"),
    )
    return attach_nearest(tot, p, Y4_EXTRA, window=2)


def run_y4(tot: pl.DataFrame, tag: str) -> h8b.Horse:
    xs = (*h8b.X2_VARS, *Y4_EXTRA)
    same = tot.drop_nulls(["wanted_tfr", *xs])
    base = h8b.horse(
        same, "wanted_tfr", h8b.X2_VARS, label=f"[{tag}] X2 same sample", verbose=False
    )
    h = h8b.horse(tot, "wanted_tfr", xs, label=f"[{tag}] Y4 X2 + sps + tert", verbose=False)
    labels = {
        **h8b.VAR_LABEL,
        "sps": "gov. spend per sec. student (% GDP pc)",
        "tert": "tertiary enrolment (%)",
    }
    print(
        f"[{tag}] H8b X2 on the Y4 sample (without the two)  n={base.est.n} G={base.est.countries}"
    )
    for k in h8b.X2_VARS:
        print(f"    {k:<10} {_fmt(base.est.coefs[k])}")
    _print_coefs(h.est, xs, labels, h.sds)
    print(f"    leader among all (CI∌0, max |b|): {h8b.leader({k: h.est.coefs[k] for k in xs})}")
    return h


# ---------------------------------------------------------------- figures
def _foot(fig: Any, text: str) -> None:
    fig.text(0.01, 0.005, text, fontsize=6.5, color=MUTED, ha="left", va="bottom")


def _save(fig: Any, path: Path) -> None:
    """Like H8 `_save` (no Software metadata -> byte-reproducible) but leaves room for a
    two-line footnote."""
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=150, metadata={"Software": None})
    h8._plt().close(fig)


def fig_y1(main: Y1Result, short: Y1Result, path: Path) -> None:
    plt = h8._plt()
    rows = list(Y1_SHORT_VARS)
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    series = [
        (main.s1, BLUE_RAMP[2], "stage 1: TFR at start >= 3, 1970–2020"),
        (main.s2, ORANGE, "stage 2: TFR at start < 3, 1970–2020 (main)"),
        (short.s2, INK, "stage 2: 1995–2020, 5-year diffs, with spending vars"),
    ]
    for k, (st, col, lab) in enumerate(series):
        if st is None:
            continue
        ks = [x for x in rows if x in st.coefs]
        ys = [rows.index(x) + (k - 1) * 0.25 for x in ks]
        b = [st.coefs[x][0] for x in ks]
        ax.errorbar(
            b,
            ys,
            xerr=[
                [st.coefs[x][0] - st.coefs[x][2] for x in ks],
                [st.coefs[x][3] - st.coefs[x][0] for x in ks],
            ],
            fmt="o",
            ms=4,
            color=col,
            capsize=2,
            label=f"{lab} (n = {st.n}, {st.countries} c.)",
        )
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f"Δ {Y1_LABEL[x]}" for x in rows], fontsize=8)
    ax.set_ylim(len(rows) + 0.6, -0.6)
    ax.set_xlabel("ΔTFR (children per woman) per 1 SD of each long-difference change")
    ax.set_title(
        "Y1: Standardised 10-year long-difference coefficients\n(country + period FE; "
        "education length and cost added to H8 T6)",
        fontsize=10,
        color=INK,
    )
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    _style(ax)
    _foot(
        fig,
        "Non-overlapping 10-year differences (black: 5-year; the 10-year short version is not "
        "identified). 95% CI clustered by country.\n"
        f"{WDI_SOURCE}",
    )
    _save(fig, path)


def _scatter(ax: Any, f: pl.DataFrame, x: str, y: str) -> None:
    for iso, xv, yv in f.select("iso3", x, y).rows():
        col = ORANGE if iso in EAST else (BLUE_RAMP[3] if iso in NORDIC else MUTED)
        ax.scatter([xv], [yv], s=22 if iso in FOCUS else 12, color=col, zorder=3)
        ax.annotate(
            iso,
            (xv, yv),
            fontsize=7 if iso in FOCUS else 5.5,
            color=col,
            xytext=(2, 2),
            textcoords="offset points",
        )


def fig_y2(main: Y2Result, norel: Y2Result, path: Path) -> None:
    plt = h8._plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))
    for ax, res, x, xl in (
        (axes[0], norel, "priv", "Private share of education spending, ISCED 1–8 (%)"),
        (axes[1], main, "rel", "Relative earnings of tertiary graduates (upper sec. = 100)"),
    ):
        _scatter(ax, res.frame, x, "tfr")
        r, p = res.rho[x]
        b = res.est.coefs[x]
        ax.set_xlabel(xl, fontsize=8)
        ax.set_ylabel("TFR (children per woman)", fontsize=8)
        ax.set_title(
            f"n = {res.est.n}; Spearman {r:+.2f} (p = {p:.2f});\nOLS std. coef. {b[0]:+.2f} "
            f"[{b[2]:+.2f}, {b[3]:+.2f}]",
            fontsize=8.5,
            color=INK,
        )
        _style(ax)
    fig.suptitle(
        "Y2: OECD cross-section, latest common year per country (2012 or later)",
        fontsize=10,
        color=INK,
    )
    _foot(
        fig,
        "Orange = JPN/KOR, blue = Nordic 4. Left: model without relative earnings; right: full "
        f"model (controls: private share, ln spending per student, ln GDP pc).\n{OECD_SOURCE}",
    )
    _save(fig, path)


def fig_y3(ld: Y3LD, path: Path) -> None:
    plt = h8._plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.6))
    for ax, x, xl in (
        (axes[0], "d_priv", "Δ private share of education spending (pp)"),
        (axes[1], "d_rel", "Δ relative earnings of tertiary graduates (points)"),
    ):
        _scatter(ax, ld.frame, x, "d_tfr")
        r, p = ld.rho[x]
        b = ld.est.coefs[x]
        ax.axhline(0, color=MUTED, lw=0.5)
        ax.axvline(0, color=MUTED, lw=0.5)
        ax.set_xlabel(xl, fontsize=8)
        ax.set_ylabel("Δ TFR (children per woman)", fontsize=8)
        ax.set_title(
            f"n = {ld.est.n}; Spearman {r:+.2f} (p = {p:.2f}); std. coef. {b[0]:+.2f} "
            f"[{b[2]:+.2f}, {b[3]:+.2f}]",
            fontsize=8.5,
            color=INK,
        )
        _style(ax)
    fig.suptitle(
        "Y3 auxiliary: long differences from 2012 (±2) to the latest common year",
        fontsize=10,
        color=INK,
    )
    _foot(fig, f"Joint OLS (HC1) with Δ ln spending per student.\n{OECD_SOURCE}")
    _save(fig, path)


def fig_y5(op: pl.DataFrame, panel: pl.DataFrame, path: Path) -> None:
    plt = h8._plt()
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.0))
    panels = (
        ("priv", "Private share of education spending, ISCED 1–8 (%)"),
        ("rel", "Tertiary relative earnings (upper sec. = 100)"),
        ("spend", "Spending per student, ISCED 1–8 (USD PPP, 2020 prices)"),
        ("tfr", "TFR (children per woman)"),
    )
    colors = {
        "JPN": ORANGE,
        "KOR": "#b2182b",
        "DNK": BLUE_RAMP[1],
        "FIN": BLUE_RAMP[2],
        "NOR": BLUE_RAMP[3],
        "SWE": BLUE_RAMP[4] if len(BLUE_RAMP) > 4 else INK,
    }
    f = op.drop("tfr").join(
        panel.filter(pl.col("iso3").is_in(FOCUS)).select("iso3", "year", "tfr"),
        on=["iso3", "year"],
        how="full",
        coalesce=True,
    )
    f = f.filter(pl.col("iso3").is_in(FOCUS) & pl.col("year").is_between(1995, 2024))
    for ax, (c, title) in zip(axes.flat, panels, strict=True):
        for iso in FOCUS:
            g = f.filter(pl.col("iso3") == iso).drop_nulls([c]).sort("year")
            if g.height == 0:
                continue
            ax.plot(
                g["year"].to_list(),
                g[c].to_list(),
                marker="o",
                ms=2.5,
                lw=1.2,
                color=colors[iso],
                label=iso,
            )
        ax.set_title(title, fontsize=9, color=INK)
        ax.set_xlim(1994, 2025)
        _style(ax)
    axes.flat[0].legend(fontsize=7, frameon=False, ncol=3)
    fig.suptitle("Y5: Japan and Korea vs the Nordic 4 (descriptive)", fontsize=10, color=INK)
    _foot(
        fig,
        "KOR private share is flagged W (includes other categories) in all years; JPN relative "
        f"earnings only 2005 and 2012. TFR from WDI.\n{OECD_SOURCE}",
    )
    _save(fig, path)


# ---------------------------------------------------------------- data description
def describe(panel: pl.DataFrame, o: pl.DataFrame, op: pl.DataFrame) -> None:
    print("== Data ==")
    print(f"growth_fertility_panel: rows={panel.height} cols={panel.width}")
    for c in (
        "tert_enrol",
        "school_life_exp",
        "educ_exp_gdp",
        "spend_per_student_sec",
        "spend_per_student_tert",
        "private_sec_share",
    ):
        f = panel.filter(pl.col(c).is_not_null())
        print(
            f"  {c:<24} obs={f.height:>5} countries={f['iso3'].n_unique():>3} "
            f"years={_i(f['year'].min())}–{_i(f['year'].max())}"
        )
    print(
        f"oecd_education_finance: rows={o.height} countries={o['iso3'].n_unique()} "
        f"years={_i(o['year'].min())}–{_i(o['year'].max())}"
    )
    for c in ("priv", "rel", "spend"):
        f = op.filter(pl.col(c).is_not_null())
        print(
            f"  {c:<6} {OECD_SPEC[c]}: obs={f.height} countries={f['iso3'].n_unique()} "
            f"years={_i(f['year'].min())}–{_i(f['year'].max())}"
        )
    st = o.filter(
        (pl.col("dataset") == "fin_source")
        & (pl.col("unit") == "PT_EXP")
        & (pl.col("exp_source") == "S1D_NON_EDU")
        & (pl.col("education_level") == "ISCED11_1T8")
    )
    print(
        "  priv obs_status counts: "
        + ", ".join(
            f"{s}={n}" for s, n in st.group_by("obs_status").len().sort("obs_status").rows()
        )
    )
    w = st.filter(pl.col("obs_status") == "W")["iso3"].unique().sort().to_list()
    print(f"  priv obs_status W countries: {w}")
    for iso in FOCUS:
        g = op.filter(pl.col("iso3") == iso)
        parts = []
        for c in ("priv", "rel", "spend"):
            yrs = g.drop_nulls([c])["year"].to_list()
            parts.append(f"{c} {len(yrs)} obs ({min(yrs)}–{max(yrs)})" if yrs else f"{c} none")
        print(f"  {iso}: " + "; ".join(parts))
    no_rel = sorted(set(op["iso3"].to_list()) - set(op.drop_nulls(["rel"])["iso3"].to_list()))
    print(f"  countries without relative earnings: {no_rel}")


def focus_table(op: pl.DataFrame) -> None:
    print("\n== Y5: Japan, Korea and the Nordic 4 (descriptive) ==")
    for c in ("priv", "rel", "spend", "tfr"):
        print(f"-- {c} --")
        for iso in FOCUS:
            g = op.filter((pl.col("iso3") == iso) & pl.col(c).is_not_null()).sort("year")
            pick = g.filter(pl.col("year").is_in([2005, 2012, 2015, 2019, 2022, 2023]))
            vals = "  ".join(
                f"{y}:{v:.1f}" if c != "tfr" else f"{y}:{v:.2f}"
                for y, v in pick.select("year", c).rows()
            )
            print(f"    {iso}  {vals}")


# ---------------------------------------------------------------- driver
def periods_per_country(ld: pl.DataFrame, xs: Sequence[str], cut: float = 3.0) -> str:
    """Distribution of stage-2 periods per country on the listwise sample, e.g. '1:40 2:5'."""
    f = ld.filter(pl.col("tfr_0") < cut).drop_nulls(["d_tfr", *xs])
    c = f.group_by("iso3").len().group_by("len").len(name="k").sort("len")
    return " ".join(f"{n}:{k}" for n, k in c.rows())


def small_countries(panel: pl.DataFrame) -> list[str]:
    last = (
        panel.filter(pl.col("population").is_not_null())
        .sort("year")
        .group_by("iso3")
        .agg(pl.col("population").last().alias("p"))
    )
    return sorted(last.filter(pl.col("p") < SMALL_POP)["iso3"].to_list())


def run(data_dir: Path, fig_dir: Path) -> None:
    panel = pl.read_parquet(data_dir / PANEL_MART)
    o = pl.read_parquet(data_dir / OECD_MART)
    d = pl.read_parquet(data_dir / h8.DHS_MART)
    fig_dir.mkdir(parents=True, exist_ok=True)
    op = oecd_panel(o, panel)
    describe(panel, o, op)

    print("\n== Y1 (main): WDI 10-year long differences, stage 2 (TFR at start < 3) ==")
    base = y1_base(panel)
    y1 = run_y1(base, "M", stage1=True)
    print("-- Y1 short sample: 1995→2005→2015 with spending per student and private enrolment --")
    y1s10 = run_y1(base, "M short 1995+", xs=Y1_SHORT_VARS, start=1995, end=2020)
    print(f"  periods per country in this sample: {periods_per_country(y1s10.ld, Y1_SHORT_VARS)}")
    print(
        "  -> with country FE, countries with a single period carry no within variation; "
        "NaN SEs mean the 10-year short version is not identified."
    )
    print("-- Y1 short sample, operational fallback: 5-year differences 1995–2020 --")
    y1s = run_y1(base, "M short 1995+ 5-year", xs=Y1_SHORT_VARS, width=5, start=1995, end=2020)
    print(f"  periods per country in this sample: {periods_per_country(y1s.ld, Y1_SHORT_VARS)}")
    print("-- Y1 same 1995+ 10-year periods without the two short-sample variables (reference) --")
    y1r = run_y1(base, "M 1995+ no extra", start=1995, end=2020)
    print(f"  periods per country in this sample: {periods_per_country(y1r.ld, Y1_VARS)}")
    fig_y1(y1, y1s, fig_dir / "h8c_y1_stage_coefficients.png")

    print("\n== Y2 (OECD cross-section) and Y3 (OECD within) ==")
    side = run_oecd(op, "M")
    print("-- Y2 without relative earnings (JPN has only 2005, 2012) --")
    y2n = run_y2(op, "M no-rel", xs=Y2_NOREL)
    print("-- Y3 auxiliary: 2012→latest long differences --")
    ld = run_y3_ld(op, "M")
    fig_y2(side.y2, y2n, fig_dir / "h8c_y2_oecd_cross_section.png")
    if ld is not None:
        fig_y3(ld, fig_dir / "h8c_y3_long_differences.png")

    print(
        "\n== Y4: DHS Total wanted TFR horse race (H8b X2) + spend per sec. student + tertiary =="
    )
    run_y4(y4_frame(d, panel), "M")

    focus_table(op)
    fig_y5(op, panel, fig_dir / "h8c_y5_japan_korea_nordic.png")

    print("\n== Verdict (pre-registered) ==")
    reverse = [*y1.reverse, *side.reverse]
    v = verdict_q(y1.holds, side.holds)
    assert y1.s2 is not None
    print(f"全世界 (Y1 stage 2): lead={y1.lead} holds={y1.holds}")
    print(f"OECD (Y2/Y3): holds={side.holds} vars={side.vars} conflicts={side.conflicts}")
    print(f"reverse (positive, CI∌0, among judged variables): {reverse or 'none'}")
    print(f"VERDICT Q: {v} = {VERDICT_JA[v]}")
    stance = final_stance(
        v, global_var=y1.lead if y1.holds else None, oecd_vars=side.vars, reverse=reverse
    )
    print(f"FINAL STANCE: {stance}")

    robustness(panel, base, o, op, y1, side)
    exploratory(panel, base, op, y1)


def robustness(
    panel: pl.DataFrame,
    base: pl.DataFrame,
    o: pl.DataFrame,
    op: pl.DataFrame,
    y1: Y1Result,
    side: OecdSide,
) -> None:
    print("\n== Robustness (pre-registered list; verdict re-evaluated holding the other side) ==")
    print("-- Y1 --")
    small = small_countries(panel)
    rows: list[tuple[str, Y1Result]] = [
        ("R + SMAM", run_y1(base, "R + SMAM", xs=(*Y1_VARS, "d_smam"))),
        ("R 5-year", run_y1(base, "R 5-year", width=5)),
        ("R 20-year", run_y1(base, "R 20-year", width=20)),
        ("R cut 2.5", run_y1(base, "R cut 2.5", cut=2.5)),
        ("R cut 3.5", run_y1(base, "R cut 3.5", cut=3.5)),
        ("R excl 2020–24", run_y1(base.filter(pl.col("year") <= 2019), "R excl 2020–24")),
        (
            "R excl oil states",
            run_y1(base.filter(~pl.col("iso3").is_in(sorted(OIL_STATES))), "R excl oil states"),
        ),
        ("R excl pop<1m", run_y1(base.filter(~pl.col("iso3").is_in(small)), "R excl pop<1m")),
    ]
    print("-- Y2 / Y3 --")
    variants: list[tuple[str, pl.DataFrame]] = [
        (
            "R ISCED 1T4",
            oecd_panel(
                o,
                panel,
                variant_spec(
                    {
                        "priv": {"education_level": "ISCED11_1T4"},
                        "spend": {"education_level": "ISCED11_1T4"},
                    }
                ),
            ),
        ),
        (
            "R ISCED 5T8",
            oecd_panel(
                o,
                panel,
                variant_spec(
                    {
                        "priv": {"education_level": "ISCED11_5T8"},
                        "spend": {"education_level": "ISCED11_5T8"},
                    }
                ),
            ),
        ),
        ("R rel earn full-time", oecd_panel(o, panel, variant_spec({"rel": {"work_time": "FT"}}))),
        ("R rel earn women", oecd_panel(o, panel, variant_spec({"rel": {"sex": "F"}}))),
        ("R excl KOR", op.filter(pl.col("iso3") != "KOR")),
        ("R excl JPN", op.filter(pl.col("iso3") != "JPN")),
        ("R private % GDP", oecd_panel(o, panel, variant_spec({"priv": {"unit": "PT_B1GQ"}}))),
    ]
    orows: list[tuple[str, OecdSide]] = []
    for lab, f in variants:
        print(f"-- {lab} --")
        orows.append((lab, run_oecd(f, lab)))
    print("\n-- Robustness summary --")
    print(f"{'spec':<24} {'side':<6} {'holds':<6} {'detail':<40} verdict")
    for lab, r in rows:
        v = verdict_q(r.holds, side.holds)
        det = f"lead={r.lead} rev={r.reverse or '-'} n={r.s2.n if r.s2 else 0}"
        print(f"{lab:<24} {'Y1':<6} {r.holds!s:<6} {det:<40} {v}")
    for lab, s in orows:
        v = verdict_q(y1.holds, s.holds)
        det = (
            f"vars={s.vars or '-'} conf={s.conflicts or '-'} rev={s.reverse or '-'} n2={s.y2.est.n}"
        )
        print(f"{lab:<24} {'OECD':<6} {s.holds!s:<6} {det:<40} {v}")


def exploratory(panel: pl.DataFrame, base: pl.DataFrame, op: pl.DataFrame, y1: Y1Result) -> None:
    print("\n== Exploratory (post hoc, not part of the verdict) ==")
    # E1: each Y1 education variable alone (with the H8 controls) on stage 2
    for x in ("d_tert", "d_sle", "d_eexp"):
        run_y1(base, f"E1 {x} only + H8 controls", xs=(x, "d_sec", "d_ln_gdp", "d_ln_u5"))
    # E2: Y2 bivariate (no controls) OLS for the two judged variables
    for x in OECD_TARGETS:
        cs = latest_common_year(op, ["tfr", x], min_year=LATEST_MIN_YEAR)
        f, _ = h8b.standardize(cs, [x])
        e = ols_hc1(f, "tfr", [x], label=f"E2 Y2 bivariate {x}")
        print(f"E2 Y2 bivariate {x}: n={e.n} {_fmt(e.coefs[x])}")
    # E3: below-replacement subsample of Y1 stage 2 (start TFR < 2.1)
    run_y1(base, "E3 cut 2.1", cut=2.1)
    # E4: H8 T6's female-enrolment coefficient (-0.120 with SMAM) vanishes in Y1. Sample or
    # collinearity? Re-run the H8 variables without SMAM on the Y1 listwise sample.
    samp = y1.ld.drop_nulls(["d_tfr", *Y1_VARS])
    h8x = ("d_ln_u5", "d_sec", "d_ln_gdp")
    s4 = h8.t6_stage(samp.filter(pl.col("tfr_0") < 3.0), h8x, "E4", verbose=False)
    _print_stage("[E4 H8 vars (no SMAM) on the Y1 sample] stage2 TFR0<3.0", s4, h8x)
    # E4b: which education-length variable absorbs it? H8 variables + one of them at a time.
    for x in ("d_sle", "d_tert"):
        xs4 = (*h8x, x)
        s4b = h8.t6_stage(samp.filter(pl.col("tfr_0") < 3.0), xs4, "E4b", verbose=False)
        _print_stage(f"[E4b H8 vars + {x} on the Y1 sample] stage2 TFR0<3.0", s4b, xs4)
    # E5: 2012→2023 change in TFR and private share (nearest observation within ±3 years of
    # 2012 and ±1 of 2023) for the focus countries, and how many OECD countries saw TFR fall.
    for iso in FOCUS:
        g = op.filter(pl.col("iso3") == iso)
        tf = dict(g.drop_nulls(["tfr"]).select("year", "tfr").rows())
        pv = dict(g.drop_nulls(["priv"]).select("year", "priv").rows())
        p0, p1 = h8.nearest_value(pv, 2012, 3), h8.nearest_value(pv, 2023, 1)
        p = "n/a" if p0 is None or p1 is None else f"{p0:.1f}→{p1:.1f} ({p1 - p0:+.1f} pp)"
        print(
            f"E5 {iso}: TFR 2012→2023 {tf[2012]:.2f}→{tf[2023]:.2f} ({tf[2023] - tf[2012]:+.2f});"
            f" private share {p}"
        )
    t = op.filter(pl.col("year").is_in([2012, 2023])).pivot(
        on="year", index="iso3", values="tfr", aggregate_function=None
    )
    dt = [b - a for a, b in t.select("2012", "2023").drop_nulls().rows()]
    print(
        f"E5 OECD ΔTFR 2012→2023: median {statistics.median(dt):+.2f}, fell in "
        f"{sum(v < 0 for v in dt)}/{len(dt)} countries"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
