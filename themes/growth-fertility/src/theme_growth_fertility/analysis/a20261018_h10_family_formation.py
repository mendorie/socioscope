"""H10（事後追加）: 日本・南欧で結婚と第 1 子を阻んでいる制約は何か（E/H/Y/W）。

事前登録: design/themes/growth-fertility.md「### H10」（2026-10-18、part6）。検定
A・B・C、判定規則、
最終スタンスの文型、頑健性、言えないことは追加データを見る前に design に固定した。H8〜H9 の判定は
変えない。検定 B の分母は「有業者 ＋ 無業者」（design 最終段落。第 1-1 表は使わない）。

  A 国 × 年パネル: 5 年差分（1990–2025、重ならない区間）、国＋期間 FE、国クラスタ SE、標準化係数。
     結果 (i) 女性の平均初婚年齢 (ii) 粗婚姻率 (iii) 第 1 子 TFR。説明 有期雇用 15–24・若年失業
     15–24・
     住宅価格対所得比。予測符号: 説明変数↑ → 初婚年齢↑・婚姻率↓・第 1 子 TFR↓。
  B 日本の雇用形態別 Kitagawa 分解（主）: 男性 25–39 歳の未婚率 2012 → 2022（主）、2007 →
  2022（下限）。
     2022 年 30–34 歳男性の未婚率 正規 − 非正規。
  C 都道府県パネル: 男 30–34 未婚割合（1990/2010/2015/2020）、都道府県 FE ＋ 年
  FE、都道府県クラスタ SE、
     標準化係数。説明 非正規比率・家賃・女性労働力率・失業率（＋ 2010–2020
     の短いパネルで県民所得）。
  判定: E = A(有期)・B(構成効果 >= 30%)・C(非正規)、H = A(住宅)・C(家賃)、Y =
  A(失業)・C(所得・失業)、
     W = C(女性労働力率)。適用できる検定の過半で「予測符号かつ CI∌0」なら支持。

運用の細則（design に書かれていない点。最初の実行より前にここで固定し、stdout の冒頭に出す）:
  - A の結果変数の出典は国ごとに 1 つ: 日本は IPSS T06-12（初婚年齢）、Eurostat の 16 か国は
      demo_nind
    （FAGEMAR1・GNUPRT）、それ以外（英・米・韓、日本の婚姻率）は OECD SF3.1（MAFM・CMR）。第 1 子
    TFR は
    欧州 `eu_tfr_by_birth_order` の順位 1、日本 T04-16 第 1 子、韓国は TFR × 第 1 子の割合（H9
    と同じ近似）。
    説明変数は 19 か国とも OECD（EMP_TEMP・UNE_RATE の _T、HPI_YDH）。差分の端点は ±2 年の最近傍
    （H8 `long_diff_nearest` と同じ）。推定は n >= 10 かつ 5 か国以上（南欧・北欧 4 か国の頑健性は
    4 か国）。
  - A の 1 つの説明変数の「検定」は、3 つの結果変数のうち推定できたものの過半で予測符号かつ CI∌0。
  - B のセルは 年齢 5 歳階級 × 雇用形態 3 区分（正規 / 非正規 / その他 = 15 歳以上人口 − 正規 −
      非正規。
    役員・自営・無業を含む）。年齢構成の変化は別の項に分け（Δr = 雇用形態内 + 雇用構成 + 年齢構成、
    恒等式）、「構成効果の割合」= 雇用構成の項 / Δr。2007 → 2022 は非正規を 4
    細分類（パート・アルバイト・
    派遣・契約）の和に両年でそろえる（定義をそろえた下限）。
  - C の説明変数: 非正規比率 = 男性 非正規 /（正規 + 非正規）%（総数は探索的に併記）、家賃 = log
      民営借家
    （非木造）1 か月家賃、女性労働力率 = 女 15–29 歳（T12-52）、失業率 = 男（T12-53）、所得 = log 1
    人当たり
    県民所得。最近傍年は ±5 年（同距離は前の年）。女性労働力率は 1980/2000/2010/2020 しか無いため、
    主仕様は事実上 2010/2015/2020 になる（1990 は女性労働力率なしの仕様を探索的に併記）。
  - C の予測符号（男 30–34 未婚・50 歳時未婚）: 非正規↑・家賃↑・失業↑・女性労働力率↑ → 未婚↑、所得↑
      → 未婚↓。
    TFR を結果にするときは全部逆。女性労働力率の符号は「女性の就業が両立の制約になる」読み（W）。
  - C の Y 検定 = 所得（短いパネル）か失業率（主仕様）の少なくとも一方が予測符号かつ CI∌0、かつ
    どちらも逆符号で CI∌0 でない。
  - 主要な制約: 支持された制約のうち通った検定の数が最多のもの。同点は B を通ったもの（E）を優先、
    なお同点なら通った割合、なお同点なら E・H・Y・W の順。

決定的スクリプト。乱数不使用。補完なし（listwise）。識別戦略なし（固定効果つきの関連のみ）。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋関数（kitagawa_age, passes, a_test, c_y_test, support, leader, final_stance, framed_stance,
wari, nearest_panel, b_cells, nonreg_share, fit_std）は tests/test_analysis_h10.py で検証。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
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
from theme_growth_fertility.analysis.a20261017_h8_mechanisms import (
    kitagawa,
    long_diff_nearest,
    nearest_value,
)

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
OECD_MART = Path("marts") / "oecd_family_formation.parquet"
EU_MART = Path("marts") / "eu_family_formation.parquet"
JP_EMP_MART = Path("marts") / "jp_marital_by_employment.parquet"
JP_MAR_MART = Path("marts") / "jp_marriage_series.parquet"
PREF_MART = Path("marts") / "jp_prefecture_panel.parquet"
EU_ORDER_MART = Path("marts") / "eu_tfr_by_birth_order.parquet"
JP_ORDER_MART = Path("marts") / "jp_births_order_cohort.parquet"
KR_MART = Path("marts") / "kr_births_order_asfr.parquet"

# ---------------------------------------------------------------- pre-registered (design H10)
A_WIDTH, A_ALT_WIDTH, A_START, A_END = 5, 10, 1990, 2025
B_COMP_MIN = 0.30
B_AGES = ("25-29", "30-34", "35-39")
B_AGES_ALT = (("25-29", "30-34"), ("30-34", "35-39"))
B_MAIN, B_LOWER = (2012, 2022), (2007, 2022)
C_YEARS = (1990, 2010, 2015, 2020)
C_INC_YEARS = (2010, 2015, 2020)
C_NM50_YEARS = (2000, 2005, 2010, 2015, 2020)
SOUTH = ("ESP", "GRC", "ITA", "PRT")
NORDIC = ("DNK", "FIN", "NOR", "SWE")

# ---------------------------------------------------------------- operational (fixed pre-run)
A_WINDOW, C_WINDOW = 2, 5
A_MIN_N, A_MIN_G = 10, 5
NONREG4 = ("part_time", "arbeit", "dispatched", "contract")
EMP3 = ("regular", "nonregular", "other")
A_Y = ("fagem", "cmr", "tfr1")
A_X = ("temp", "une", "hpi")
A_SIGN = {"fagem": 1, "cmr": -1, "tfr1": -1}  # sign of y-response to a rise in any A_X
A_X_OF = {"E": "temp", "H": "hpi", "Y": "une"}
C_X = ("nonreg", "ln_rent", "flfp", "unemp")
C_SIGN = {"nonreg": 1, "ln_rent": 1, "flfp": 1, "unemp": 1, "ln_inc": -1}  # for never-married
CONSTRAINTS = ("E", "H", "Y", "W")
CONSTRAINT_JA = {
    "E": "若年層の雇用の不安定さ（非正規化）",
    "H": "住宅費",
    "Y": "所得・失業",
    "W": "女性の就業",
}
LABEL = {
    "temp": "temporary employment 15-24 (%)",
    "une": "unemployment 15-24 (%)",
    "hpi": "house price-to-income (index)",
    "fagem": "female mean age at 1st marriage",
    "cmr": "crude marriage rate (per 1,000)",
    "tfr1": "1st-birth TFR",
    "nonreg": "non-regular share, men (%)",
    "ln_rent": "log private rent (non-wooden)",
    "flfp": "female LFP 15-29 (%)",
    "unemp": "unemployment rate, men (%)",
    "ln_inc": "log income per capita",
}


# ---------------------------------------------------------------- pure helpers (tested)
Coef = tuple[float, float, float, float]  # b, se, lo, hi


@dataclass(frozen=True)
class Fit:
    coefs: dict[str, Coef]
    n: int
    groups: int
    times: tuple[int, ...]


def fit_std(
    frame: pl.DataFrame,
    y: str,
    xs: Sequence[str],
    *,
    unit: str,
    time: str,
    min_n: int = A_MIN_N,
    min_g: int = A_MIN_G,
) -> Fit | None:
    """y ~ (x / SD(x)) + C(unit) + C(time), SE clustered by unit. Listwise.

    None if too small or a regressor is collinear with the FE."""
    import statsmodels.formula.api as smf

    f = frame.drop_nulls([y, *xs])
    if f.height < min_n or f[unit].n_unique() < min_g:
        return None
    sds = {x: float(f[x].std() or 0.0) for x in xs}  # type: ignore[arg-type]
    if any(s <= 0 for s in sds.values()):
        return None
    f = f.with_columns([(pl.col(x) / sds[x]).alias(x) for x in xs]).sort(unit, time)
    pdf = f.to_pandas()
    formula = f"{y} ~ {' + '.join(xs)} + C({unit}) + C({time})"
    model = smf.ols(formula, data=pdf)
    exog = model.exog
    if int(np.linalg.matrix_rank(exog)) < exog.shape[1] or exog.shape[0] <= exog.shape[1]:
        return None  # regressor collinear with the FE (no within variation) or no residual df
    res = model.fit(cov_type="cluster", cov_kwds={"groups": pdf[unit]})
    ci = res.conf_int()
    coefs = {
        x: (float(res.params[x]), float(res.bse[x]), float(ci.loc[x, 0]), float(ci.loc[x, 1]))
        for x in xs
    }
    times = tuple(sorted(int(t) for t in set(f[time].to_list())))
    return Fit(coefs, int(res.nobs), int(f[unit].n_unique()), times)


def passes(c: Coef | None, sign: int) -> bool:
    """Predicted sign with a 95% CI that excludes 0."""
    if c is None:
        return False
    _, _, lo, hi = c
    return lo > 0 if sign > 0 else hi < 0


def a_test(fits: Mapping[str, Fit | None], x: str, signs: Mapping[str, int] = A_SIGN) -> bool:
    """A's test for one regressor: a majority of the estimated outcomes pass."""
    est = [y for y, f in fits.items() if f is not None and x in f.coefs]
    ok = sum(passes(fits[y].coefs[x], signs[y]) for y in est)  # type: ignore[union-attr]
    return len(est) > 0 and ok * 2 > len(est)


def c_y_test(inc: Coef | None, unemp: Coef | None, *, flip: bool = False) -> bool:
    """C's Y test: income (−) or unemployment (+) passes; neither significant the wrong way."""
    s_inc, s_un = (-1, 1) if not flip else (1, -1)
    good = passes(inc, s_inc) or passes(unemp, s_un)
    bad = passes(inc, -s_inc) or passes(unemp, -s_un)
    return good and not bad


def support(tests: Sequence[bool]) -> bool:
    return len(tests) > 0 and sum(tests) * 2 > len(tests)


def leader(
    tests: Mapping[str, Sequence[bool]], b_passed: bool, order: Sequence[str] = CONSTRAINTS
) -> str | None:
    """Most-supported constraint (tie-break: B first, then pass ratio, then order)."""
    sup = [k for k in order if support(tests[k])]
    if not sup:
        return None

    def key(k: str) -> tuple[int, int, float, int]:
        ts = tests[k]
        return (
            -sum(ts),
            -(1 if (k == "E" and b_passed) else 0),
            -sum(ts) / len(ts),
            order.index(k),
        )

    return sorted(sup, key=key)[0]


def wari(x: float) -> str:
    return f"{round(x * 10)}"


def final_stance(lead: str | None, comp_share: float) -> str:
    """The pre-registered sentence (design H10 最終スタンスの文型)."""
    if lead is None:
        return "測れた制約では確かめられず、未婚化の大半は同じ雇用形態・同じ地域条件の中で進んだ。"
    return (
        f"日本で結婚と第 1 子を阻んでいる主要な制約は{CONSTRAINT_JA[lead]}で、未婚化の"
        f"{wari(comp_share)}割はそれで説明できる。残る{wari(1 - comp_share)}割は同じ条件の中で"
        "結婚しなくなった分である。"
    )


def comp_clause(comp_share: float, comp_lower: float) -> str:
    """The composition part of the framed sentence; a negative share means the mix moved away
    from non-regular work (it pushed the never-married share down)."""
    if comp_share >= 0:
        return (
            f"男性 25–39 歳の未婚率の上昇のうち、雇用形態の構成が非正規に寄った分は "
            f"{comp_share:.0%}（2007 年からの定義をそろえた比較では {comp_lower:.0%}）"
        )
    return (
        "男性 25–39 歳では雇用形態の構成はむしろ正規に寄り、構成の変化は未婚率の上昇の "
        f"{comp_share:.0%}（2007 年からの定義をそろえた比較では {comp_lower:.0%}）と逆向きで"
    )


def framed_stance(
    *,
    lead: str | None,
    comp_share: float,
    comp_lower: float,
    rate_share: float,
    gap: float,
    passed: Mapping[str, Sequence[str]],
    robust_changes: Sequence[str],
) -> str:
    """Reporting sentence: the pre-registered pattern plus the qualifications the results need."""
    head = final_stance(lead, comp_share)
    got = [f"{k}（{'・'.join(v)}）" for k, v in passed.items() if v]
    tested = "通った検定は " + ("、".join(got) if got else "なし")
    rob = (
        "頑健性の仕様では判定が変わるものがある（" + "、".join(robust_changes) + "）"
        if robust_changes
        else "事前の頑健性の仕様では判定は変わらない"
    )
    return (
        f"{head}"
        f"{comp_clause(comp_share, comp_lower)}、同じ雇用形態の中での上昇が "
        f"{rate_share:.0%} である。2022 年の 30–34 歳男性では非正規の未婚率が正規より "
        f"{abs(gap):.1f} ポイント高いが、この差は逆の因果（未婚だから非正規）を含む。"
        f"{tested}。{rob}。すべて関連で、因果効果ではない。"
    )


def nonreg_share(regular: float | None, nonregular: float | None) -> float | None:
    if regular is None or nonregular is None or regular + nonregular <= 0:
        return None
    return 100.0 * nonregular / (regular + nonregular)


Cells = dict[tuple[str, str], tuple[float, float]]  # (age, emp) -> (persons, never_married)


def b_cells(
    df: pl.DataFrame, year: int, sex: str, ages: Sequence[str], *, sum4: bool = False
) -> Cells:
    """Age × {regular, nonregular, other} cells; other = 15+ population − regular − nonregular."""
    sub = df.filter(
        (pl.col("survey_year") == year) & (pl.col("sex") == sex) & pl.col("age_class").is_in(ages)
    )
    v: dict[tuple[str, str, str], float] = {
        (r["age_class"], r["employment"], r["marital"]): float(r["persons"])
        for r in sub.iter_rows(named=True)
    }
    out: Cells = {}
    for a in ages:

        def g(emp: str, m: str, a: str = a) -> float:
            if (a, emp, m) not in v:
                raise KeyError(f"{year} {sex} {a} {emp} {m}")
            return v[(a, emp, m)]

        for m_i, m in enumerate(("total", "never_married")):
            reg = g("regular", m)
            non = sum(g(e, m) for e in NONREG4) if sum4 else g("nonregular", m)
            oth = g("total_pop", m) - reg - non
            for emp, val in (("regular", reg), ("nonregular", non), ("other", oth)):
                prev = out.get((a, emp), (0.0, 0.0))
                out[(a, emp)] = (val, prev[1]) if m_i == 0 else (prev[0], val)
    return out


@dataclass(frozen=True)
class Decomp:
    r0: float
    r1: float
    rate: float  # within-employment-type change
    emp_comp: float  # employment-composition change
    age_comp: float  # age-composition change

    @property
    def total(self) -> float:
        return self.r1 - self.r0

    @property
    def comp_share(self) -> float:
        return self.emp_comp / self.total if self.total != 0 else float("nan")

    @property
    def rate_share(self) -> float:
        return self.rate / self.total if self.total != 0 else float("nan")


def kitagawa_age(c0: Cells, c1: Cells, emps: Sequence[str] = EMP3) -> Decomp:
    """Δ never-married rate = Σ_a w̄_a (rate_a + comp_a) + Σ_a Δw_a r̄_a (exact)."""
    ages = sorted({a for a, _ in c0})
    n0 = sum(c0[(a, e)][0] for a in ages for e in emps)
    n1 = sum(c1[(a, e)][0] for a in ages for e in emps)
    rate = emp = age = 0.0
    r0_tot = r1_tot = 0.0
    for a in ages:
        na0 = sum(c0[(a, e)][0] for e in emps)
        na1 = sum(c1[(a, e)][0] for e in emps)
        p0 = [c0[(a, e)][0] / na0 for e in emps]
        p1 = [c1[(a, e)][0] / na1 for e in emps]
        q0 = [c0[(a, e)][1] / c0[(a, e)][0] for e in emps]
        q1 = [c1[(a, e)][1] / c1[(a, e)][0] for e in emps]
        ra, ca = kitagawa(q0, q1, p0, p1)
        ra0 = sum(x * y for x, y in zip(p0, q0, strict=True))
        ra1 = sum(x * y for x, y in zip(p1, q1, strict=True))
        w0, w1 = na0 / n0, na1 / n1
        rate += (w0 + w1) / 2 * ra
        emp += (w0 + w1) / 2 * ca
        age += (w1 - w0) * (ra0 + ra1) / 2
        r0_tot += w0 * ra0
        r1_tot += w1 * ra1
    return Decomp(r0_tot, r1_tot, rate, emp, age)


def nearest_panel(
    obs: Mapping[str, Mapping[str, Mapping[int, float]]],
    units: Sequence[str],
    years: Sequence[int],
    window: int,
) -> pl.DataFrame:
    """unit × target-year frame; each variable at its observation nearest to the target year
    within ±window (tie -> earlier). Missing stays null."""
    rows: list[dict[str, Any]] = []
    for u in units:
        for y in years:
            row: dict[str, Any] = {"unit": u, "year": y}
            for var, by_unit in obs.items():
                row[var] = nearest_value(by_unit.get(u, {}), y, window)
            rows.append(row)
    schema: dict[str, Any] = {"unit": pl.Utf8, "year": pl.Int64}
    schema.update({v: pl.Float64 for v in obs})
    return pl.DataFrame(rows, schema=schema, orient="row")


# ---------------------------------------------------------------- loading
def load(data_dir: Path) -> dict[str, pl.DataFrame]:
    return {
        "oecd": pl.read_parquet(data_dir / OECD_MART),
        "eu": pl.read_parquet(data_dir / EU_MART),
        "emp": pl.read_parquet(data_dir / JP_EMP_MART),
        "mar": pl.read_parquet(data_dir / JP_MAR_MART),
        "pref": pl.read_parquet(data_dir / PREF_MART),
        "eu_order": pl.read_parquet(data_dir / EU_ORDER_MART),
        "jp_order": pl.read_parquet(data_dir / JP_ORDER_MART),
        "kr": pl.read_parquet(data_dir / KR_MART),
    }


def _s(df: pl.DataFrame, name: str, **eq: str) -> pl.DataFrame:
    f = df
    for k, v in eq.items():
        f = f.filter(pl.col(k) == v)
    return f.select("iso3", "year", pl.col("value").alias(name))


def country_panel(d: Mapping[str, pl.DataFrame]) -> tuple[pl.DataFrame, dict[str, str]]:
    """iso3 × year with A's outcomes and regressors (one source per country and variable)."""
    o, eu = d["oecd"], d["eu"]
    eu_iso = sorted(set(eu["iso3"].to_list()))
    oecd_iso = sorted(set(o["iso3"].to_list()))
    src: dict[str, str] = {}
    fag_eu = _s(eu, "fagem", dataset="demo_nind", indicator="FAGEMAR1")
    fag_oe = _s(o, "fagem", dataset="mean_age_first_marriage", measure="MAFM", sex="F").filter(
        ~pl.col("iso3").is_in(eu_iso) & (pl.col("iso3") != "JPN")
    )
    fag_jp = (
        d["mar"]
        .filter((pl.col("metric") == "mean_age_first_marriage") & (pl.col("sex") == "F"))
        .select(pl.lit("JPN").alias("iso3"), "year", pl.col("value").alias("fagem"))
    )
    cmr_eu = _s(eu, "cmr", dataset="demo_nind", indicator="GNUPRT")
    cmr_oe = _s(o, "cmr", dataset="marriage_rate", measure="CMR").filter(
        ~pl.col("iso3").is_in(eu_iso)
    )
    eo = (
        d["eu_order"]
        .filter(pl.col("order") == "1")
        .select("iso3", "year", pl.col("tfr").alias("tfr1"))
    )
    jo = (
        d["jp_order"]
        .filter((pl.col("metric") == "tfr_order") & (pl.col("group") == "第1子"))
        .select(pl.lit("JPN").alias("iso3"), "year", pl.col("value").alias("tfr1"))
    )
    kr = d["kr"]
    kt = kr.filter((pl.col("metric") == "tfr") & (pl.col("group") == "계")).select(
        "year", pl.col("value").alias("t")
    )
    kb = (
        kr.filter((pl.col("metric") == "births") & (pl.col("group") != "계"))
        .group_by("year")
        .agg(
            pl.col("value").sum().alias("all"),
            pl.col("value").filter(pl.col("group") == "첫째아").sum().alias("first"),
        )
    )
    ko = kt.join(kb, on="year").select(
        pl.lit("KOR").alias("iso3"),
        "year",
        (pl.col("t") * pl.col("first") / pl.col("all")).alias("tfr1"),
    )
    xs = [
        _s(o, "temp", dataset="temp_employment", sex="_T", age="Y15T24"),
        _s(o, "une", dataset="youth_unemployment", sex="_T", age="Y15T24"),
        _s(o, "une2534", dataset="youth_unemployment", sex="_T", age="Y25T34"),
        _s(o, "hpi", dataset="house_prices", measure="HPI_YDH"),
        _s(o, "rhp", dataset="house_prices", measure="RHP"),
    ]
    parts = [
        pl.concat([fag_eu, fag_oe, fag_jp]),
        pl.concat([cmr_eu, cmr_oe]),
        pl.concat([eo, jo, ko.with_columns(pl.col("year").cast(pl.Int64))]),
        *xs,
    ]
    keys = (
        pl.concat([p.select("iso3", pl.col("year").cast(pl.Int64)) for p in parts])
        .unique()
        .filter(pl.col("iso3").is_in(oecd_iso))
    )
    panel = keys
    for p in parts:
        panel = panel.join(
            p.with_columns(pl.col("year").cast(pl.Int64)), on=["iso3", "year"], how="left"
        )
    for iso in oecd_iso:
        src[iso] = (
            ("T06-12" if iso == "JPN" else "Eurostat" if iso in eu_iso else "OECD SF3.1")
            + " / "
            + ("Eurostat" if iso in eu_iso else "OECD SF3.1")
        )
    return panel.sort("iso3", "year"), src


A_COLS = ("fagem", "cmr", "tfr1", "temp", "une", "une2534", "hpi", "rhp")


def a_frame(panel: pl.DataFrame, width: int) -> pl.DataFrame:
    return long_diff_nearest(panel, A_COLS, width=width, start=A_START, end=A_END, window=A_WINDOW)


def run_a(
    ld: pl.DataFrame,
    xs: Sequence[str] = A_X,
    *,
    min_g: int = A_MIN_G,
) -> dict[str, Fit | None]:
    out: dict[str, Fit | None] = {}
    for y in A_Y:
        out[y] = fit_std(
            ld, f"d_{y}", [f"d_{x}" for x in xs], unit="iso3", time="period", min_g=min_g
        )
        if out[y] is not None:
            f = out[y]
            assert f is not None
            out[y] = replace(f, coefs={k[2:]: v for k, v in f.coefs.items()})
    return out


def pref_obs(pref: pl.DataFrame) -> dict[str, dict[str, dict[int, float]]]:
    p = pref.filter(pl.col("pref_code") != "00")

    def get(metric: str, sex: str, age: str | None = None) -> dict[str, dict[int, float]]:
        f = p.filter((pl.col("metric") == metric) & (pl.col("sex") == sex))
        f = (
            f.filter(pl.col("age_class").is_null())
            if age is None
            else f.filter(pl.col("age_class") == age)
        )
        out: dict[str, dict[int, float]] = {}
        for code, year, v in f.select("pref_code", "year", "value").iter_rows():
            out.setdefault(str(code), {})[int(year)] = float(v)
        return out

    def ratio(sex: str) -> dict[str, dict[int, float]]:
        reg, non = get("regular_employees", sex), get("nonregular_employees", sex)
        out: dict[str, dict[int, float]] = {}
        for c in reg:
            for y in reg[c]:
                s = nonreg_share(reg[c].get(y), non.get(c, {}).get(y))
                if s is not None:
                    out.setdefault(c, {})[y] = s
        return out

    def log(m: dict[str, dict[int, float]]) -> dict[str, dict[int, float]]:
        return {c: {y: math.log(v) for y, v in s.items() if v > 0} for c, s in m.items()}

    return {
        "nm3034": get("never_married_m30_34", "M", "30-34"),
        "nm50": get("never_married_at_50", "M"),
        "nm50_f": get("never_married_at_50", "F"),
        "tfr": get("tfr", "T"),
        "nonreg": ratio("M"),
        "nonreg_t": ratio("T"),
        "ln_rent": log(get("rent_private_nonwood", "T")),
        "ln_rent_priv": log(get("rent_private", "T")),
        "ln_inc": log(get("income_per_capita", "T")),
        "flfp": get("lfp", "F", "15-29"),
        "flfp3044": get("lfp", "F", "30-44"),
        "unemp": get("unemployment_rate", "M"),
    }


def c_frame(
    obs: Mapping[str, Mapping[str, Mapping[int, float]]], years: Sequence[int]
) -> pl.DataFrame:
    units = sorted({u for m in obs.values() for u in m})
    return nearest_panel(obs, units, years, C_WINDOW)


def run_c(frame: pl.DataFrame, y: str, xs: Sequence[str]) -> Fit | None:
    return fit_std(frame, y, xs, unit="unit", time="year", min_n=20, min_g=20)


# ---------------------------------------------------------------- judgement
@dataclass(frozen=True)
class Inputs:
    a: dict[str, Fit | None]
    b: Decomp
    c_main: Fit | None
    c_inc: Fit | None
    c_flip: bool = False  # True when C's outcome is TFR (all signs reversed)
    c_rent: str = "ln_rent"


@dataclass(frozen=True)
class Verdict:
    tests: dict[str, list[bool]]
    names: dict[str, list[str]]
    supported: list[str]
    lead: str | None
    b_passed: bool
    comp_share: float
    extra: dict[str, Any] = field(default_factory=dict)


def judge(inp: Inputs) -> Verdict:
    s = -1 if inp.c_flip else 1
    cm = inp.c_main.coefs if inp.c_main else {}
    ci = inp.c_inc.coefs if inp.c_inc else {}
    b_ok = inp.b.total > 0 and inp.b.comp_share >= B_COMP_MIN
    rows: dict[str, list[tuple[str, bool]]] = {
        "E": [
            ("A 有期雇用", a_test(inp.a, "temp")),
            ("B 構成効果", b_ok),
            ("C 非正規比率", passes(cm.get("nonreg"), s)),
        ],
        "H": [("A 住宅対所得比", a_test(inp.a, "hpi")), ("C 家賃", passes(cm.get(inp.c_rent), s))],
        "Y": [
            ("A 若年失業", a_test(inp.a, "une")),
            ("C 所得・失業", c_y_test(ci.get("ln_inc"), cm.get("unemp"), flip=inp.c_flip)),
        ],
        "W": [("C 女性労働力率", passes(cm.get("flfp"), s))],
    }
    tests = {k: [ok for _, ok in v] for k, v in rows.items()}
    names = {k: [n for n, ok in v if ok] for k, v in rows.items()}
    sup = [k for k in CONSTRAINTS if support(tests[k])]
    return Verdict(tests, names, sup, leader(tests, b_ok), b_ok, inp.b.comp_share)


def verdict_line(v: Verdict) -> str:
    parts = [
        f"{k}: {sum(v.tests[k])}/{len(v.tests[k])}{'*' if k in v.supported else ''}"
        for k in CONSTRAINTS
    ]
    return f"{'  '.join(parts)}  -> lead={v.lead}  B comp share={v.comp_share:.3f}"


# ---------------------------------------------------------------- printing
def _f(c: Coef | None) -> str:
    if c is None:
        return "n/a"
    return f"{c[0]:+.3f} [{c[2]:+.3f}, {c[3]:+.3f}]"


def print_a(fits: Mapping[str, Fit | None], tag: str, xs: Sequence[str] = A_X) -> None:
    for y in A_Y:
        f = fits[y]
        if f is None:
            print(f"[{tag}] {LABEL[y]:<34} not estimable (too few rows / collinear with FE)")
            continue
        parts = "  ".join(
            f"{x}: {_f(f.coefs.get(x))}{'+' if passes(f.coefs.get(x), A_SIGN[y]) else ''}"
            for x in xs
        )
        print(f"[{tag}] {LABEL[y]:<34} n={f.n:>3} G={f.groups:>2}  {parts}")


def print_c(f: Fit | None, tag: str, xs: Sequence[str], flip: bool = False) -> None:
    if f is None:
        print(f"[{tag}] not estimable (too few rows, or a regressor has no within variation)")
        return
    s = -1 if flip else 1
    parts = "  ".join(
        f"{x}: {_f(f.coefs[x])}{'+' if passes(f.coefs[x], s * C_SIGN[x]) else ''}" for x in xs
    )
    print(f"[{tag}] n={f.n} G={f.groups} years={f.times}\n    {parts}")


def print_b(dc: Decomp, tag: str) -> None:
    print(
        f"[{tag}] r0={dc.r0:.4f} r1={dc.r1:.4f} Δ={dc.total:+.4f}  within={dc.rate:+.4f} "
        f"({dc.rate_share:.1%})  emp-comp={dc.emp_comp:+.4f} ({dc.comp_share:.1%})  "
        f"age-comp={dc.age_comp:+.4f}"
    )


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _save(fig: Any, path: Path, foot: str) -> None:
    fig.text(0.01, 0.005, foot, fontsize=6.8, color=MUTED, ha="left", va="bottom")
    fig.savefig(path, dpi=150, metadata={"Software": None})
    _plt().close(fig)
    print(f"figure: {path.name}")


def _dots(ax: Any, items: Sequence[tuple[str, Coef | None, bool]]) -> None:
    for i, (_, c, ok) in enumerate(items):
        if c is None:
            continue
        col = ORANGE if ok else BLUE_RAMP[3]
        ax.plot([c[2], c[3]], [i, i], color=col, lw=1.6)
        ax.scatter([c[0]], [i], color=col, s=26, zorder=3)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([t for t, _, _ in items], fontsize=7.5)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.invert_yaxis()
    _style(ax)


def fig_a(fits: Mapping[str, Fit | None], path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, y in zip(axes, A_Y, strict=True):
        f = fits[y]
        items = [
            (
                LABEL[x],
                f.coefs.get(x) if f else None,
                passes(f.coefs.get(x), A_SIGN[y]) if f else False,
            )
            for x in A_X
        ]
        _dots(ax, items)
        sg = "+" if A_SIGN[y] > 0 else "−"
        ax.set_title(
            f"Δ {LABEL[y]} (pred. {sg})\nn={f.n if f else 0}, G={f.groups if f else 0}",
            fontsize=8.5,
            color=INK,
        )
        ax.set_xlabel("per 1 SD of the 5-year change", fontsize=7.5)
    fig.suptitle(
        "H10 A: 5-year differences 1990-2025, country + period FE, 95% CI clustered by country",
        fontsize=9.5,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    _save(
        fig,
        path,
        "Orange = predicted sign with CI excluding 0. Regressors: OECD (EMP_TEMP, UNE_RATE, "
        "HPI_YDH 2015=100). Outcomes: Eurostat demo_nind / OECD SF3.1 / IPSS T06-12; 1st-birth TFR:"
        " "
        "Eurostat, IPSS T04-16, KOSTAT (approx.).",
    )


def fig_b_rates(emp: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    years = (2007, 2012, 2017, 2022)
    sub = emp.filter((pl.col("sex") == "male") & (pl.col("age_class") == "30-34"))
    v = {
        (r["survey_year"], r["employment"], r["marital"]): r["persons"]
        for r in sub.iter_rows(named=True)
    }

    def rate(y: int, e: str) -> float | None:
        if (y, e, "total") not in v:
            return None
        return 100 * float(v[(y, e, "never_married")]) / float(v[(y, e, "total")])

    ax = axes[0]
    for e, lab, col in (
        ("total_pop", "all men 30-34", INK),
        ("regular", "regular employees", BLUE_RAMP[3]),
        ("nonregular", "non-regular employees", ORANGE),
    ):
        pts = [(y, rate(y, e)) for y in years if rate(y, e) is not None]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=col, label=lab)
    sum4 = [
        100
        * sum(v[(2007, e, "never_married")] for e in NONREG4)
        / sum(v[(2007, e, "total")] for e in NONREG4)
    ]
    ax.scatter([2007], sum4, marker="x", color=ORANGE, label="2007 non-regular (4 sub-types)")
    ax.set_ylabel("never married (%)")
    ax.set_title("Never-married share, men 30-34, by employment type", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5)
    _style(ax)
    ax = axes[1]
    for e, lab, col in (
        ("regular", "regular", BLUE_RAMP[3]),
        ("nonregular", "non-regular", ORANGE),
        ("not_employed", "not employed", MUTED),
    ):
        pts = [
            (y, 100 * v[(y, e, "total")] / v[(y, "total_pop", "total")])
            for y in years
            if (y, e, "total") in v
        ]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", color=col, label=lab)
    ax.set_ylabel("share of all men 30-34 (%)")
    ax.set_title("Employment composition, men 30-34", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5)
    _style(ax)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _save(
        fig,
        path,
        "Source: Statistics Bureau of Japan, Employment Status Survey 2007/2012/2017/2022 (employed"
        " + "
        "not employed). 2007 has no non-regular total.",
    )


def fig_b_decomp(rows: Sequence[tuple[str, Decomp]], path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(rows) + 1.6))
    for i, (_, dc) in enumerate(rows):
        left_pos = 0.0
        left_neg = 0.0
        for val, col in ((dc.rate, BLUE_RAMP[2]), (dc.emp_comp, ORANGE), (dc.age_comp, MUTED)):
            v = 100 * val
            if v >= 0:
                ax.barh(i, v, left=left_pos, color=col, height=0.6)
                left_pos += v
            else:
                ax.barh(i, v, left=left_neg, color=col, height=0.6)
                left_neg += v
        ax.text(
            max(left_pos, 0) + 0.1,
            i,
            f"Δ={100 * dc.total:+.1f} pt, comp {dc.comp_share:.0%}",
            va="center",
            fontsize=7.5,
        )
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([t for t, _ in rows], fontsize=7.5)
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlabel("change in never-married share (percentage points)")
    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(color=BLUE_RAMP[2], label="within employment type"),
            Patch(color=ORANGE, label="employment composition"),
            Patch(color=MUTED, label="age composition"),
        ],
        frameon=False,
        fontsize=7.5,
        loc="lower right",
    )
    ax.set_title("H10 B: Kitagawa decomposition of the rise in never-married share", fontsize=9)
    _style(ax)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _save(
        fig,
        path,
        "Cells: 5-year age × {regular, non-regular, other}. Source: Employment Status Survey "
        "(e-Stat). 2007->2022 uses the 4 non-regular sub-types in both years.",
    )


def fig_c(specs: Sequence[tuple[str, Fit | None, Sequence[str], bool]], path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, len(specs), figsize=(3.6 * len(specs), 3.8), sharey=False)
    for ax, (title, f, xs, flip) in zip(axes, specs, strict=True):
        s = -1 if flip else 1
        items = [
            (
                LABEL[x],
                f.coefs.get(x) if f else None,
                passes(f.coefs.get(x), s * C_SIGN[x]) if f else False,
            )
            for x in xs
        ]
        _dots(ax, items)
        ax.set_title(
            f"{title}\nn={f.n if f else 0}, years={','.join(map(str, f.times)) if f else '-'}",
            fontsize=8,
            color=INK,
        )
        ax.set_xlabel("per 1 SD", fontsize=7.5)
    fig.suptitle(
        "H10 C: 47 prefectures, prefecture + year FE, 95% CI clustered by prefecture", fontsize=9.5
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    _save(
        fig,
        path,
        "Orange = predicted sign with CI excluding 0. Sources: IPSS Popular Data 2026 (T12-33/36/37"
        "/52/"
        "53), Employment Status Survey TS-18, Housing and Land Survey TS-34-2, Cabinet Office prefe"
        "ctural "
        "accounts.",
    )


def fig_long(mar: pl.DataFrame, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    ax = axes[0]
    for sex, age, col in (
        ("M", "30-34", BLUE_RAMP[3]),
        ("F", "25-29", ORANGE),
        ("M", "25-29", BLUE_RAMP[1]),
        ("F", "30-34", "#f2a37f"),
    ):
        f = mar.filter(
            (pl.col("metric") == "never_married_share")
            & (pl.col("sex") == sex)
            & (pl.col("age_class") == age)
        ).sort("year")
        ax.plot(f["year"], f["value"], marker="o", ms=3, color=col, label=f"{sex} {age}")
    ax.set_ylabel("never married (%)")
    ax.set_title("Japan: never-married share (census, T06-24)", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5)
    _style(ax)
    ax = axes[1]
    for sex, col in (("M", BLUE_RAMP[3]), ("F", ORANGE)):
        f = mar.filter(
            (pl.col("metric") == "mean_age_first_marriage") & (pl.col("sex") == sex)
        ).sort("year")
        ax.plot(f["year"], f["value"], color=col, label=sex)
    ax.set_ylabel("years")
    ax.set_title("Japan: mean age at first marriage (T06-12)", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5)
    _style(ax)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _save(fig, path, "Source: IPSS Popular Data 2026 T06-24, T06-12 (PDL1.0).")


# ---------------------------------------------------------------- sections
@dataclass(frozen=True)
class H10Result:
    a: dict[str, Fit | None]
    b: Decomp
    b_lower: Decomp
    gap_2022: float
    c_main: Fit | None
    c_inc: Fit | None
    verdict: Verdict
    final: str
    framed: str
    robust: dict[str, Verdict]
    b_rows: list[tuple[str, Decomp]]
    c_specs: dict[str, Fit | None]
    a_alt: dict[str, dict[str, Fit | None]]


def male_gap(emp: pl.DataFrame, year: int = 2022, age: str = "30-34") -> float:
    c = b_cells(emp, year, "male", (age,))
    r = {e: c[(age, e)][1] / c[(age, e)][0] for e in ("regular", "nonregular")}
    return 100 * (r["regular"] - r["nonregular"])


def compute(d: Mapping[str, pl.DataFrame]) -> H10Result:
    panel, _ = country_panel(d)
    ld5 = a_frame(panel, A_WIDTH)
    a = run_a(ld5)
    emp = d["emp"]
    b = kitagawa_age(
        b_cells(emp, B_MAIN[0], "male", B_AGES), b_cells(emp, B_MAIN[1], "male", B_AGES)
    )
    bl = kitagawa_age(
        b_cells(emp, B_LOWER[0], "male", B_AGES, sum4=True),
        b_cells(emp, B_LOWER[1], "male", B_AGES, sum4=True),
    )
    obs = pref_obs(d["pref"])
    cf = c_frame(obs, C_YEARS)
    c_main = run_c(cf, "nm3034", C_X)
    cfi = c_frame(obs, C_INC_YEARS)
    c_inc = run_c(cfi, "nm3034", (*C_X, "ln_inc"))
    v = judge(Inputs(a, b, c_main, c_inc))

    # ---- robustness (design list, all)
    a_alt: dict[str, dict[str, Fit | None]] = {
        "width 10": run_a(a_frame(panel, A_ALT_WIDTH)),
        "unemployment 25-34": run_a(ld5, ("temp", "une2534", "hpi")),
        "real house prices": run_a(ld5, ("temp", "une", "rhp")),
        "South 4": run_a(ld5.filter(pl.col("iso3").is_in(SOUTH)), min_g=4),
        "Nordic 4": run_a(ld5.filter(pl.col("iso3").is_in(NORDIC)), min_g=4),
    }

    def rename(fits: dict[str, Fit | None], old: str, new: str) -> dict[str, Fit | None]:
        out: dict[str, Fit | None] = {}
        for k, f in fits.items():
            out[k] = (
                None
                if f is None
                else replace(f, coefs={(new if x == old else x): c for x, c in f.coefs.items()})
            )
        return out

    a_for_judge = dict(a_alt)
    a_for_judge["unemployment 25-34"] = rename(a_alt["unemployment 25-34"], "une2534", "une")
    a_for_judge["real house prices"] = rename(a_alt["real house prices"], "rhp", "hpi")
    b_rows: list[tuple[str, Decomp]] = [
        ("men 25-39, 2012->2022 (main)", b),
        ("men 25-39, 2007->2022 (4 sub-types)", bl),
    ]
    b_alt: dict[str, Decomp] = {"2007->2022": bl}
    for ages in B_AGES_ALT:
        tag = f"men {ages[0][:2]}-{ages[-1][-2:]}"
        dc = kitagawa_age(b_cells(emp, 2012, "male", ages), b_cells(emp, 2022, "male", ages))
        b_alt[tag] = dc
        b_rows.append((f"{tag}, 2012->2022", dc))
    fdc = kitagawa_age(b_cells(emp, 2012, "female", B_AGES), b_cells(emp, 2022, "female", B_AGES))
    b_alt["women 25-39"] = fdc
    b_rows.append(("women 25-39, 2012->2022", fdc))

    c_specs: dict[str, Fit | None] = {"main": c_main, "income": c_inc}
    c50 = c_frame(obs, C_NM50_YEARS)
    c_specs["nm50"] = run_c(c50, "nm50", C_X)
    c_specs["nm50_inc"] = run_c(c_frame(obs, C_INC_YEARS), "nm50", (*C_X, "ln_inc"))
    c_specs["tfr"] = run_c(cf, "tfr", C_X)
    c_specs["tfr_inc"] = run_c(cfi, "tfr", (*C_X, "ln_inc"))
    c_specs["rent_priv"] = run_c(cf, "nm3034", ("nonreg", "ln_rent_priv", "flfp", "unemp"))
    c_specs["rent_priv_inc"] = run_c(
        cfi, "nm3034", ("nonreg", "ln_rent_priv", "flfp", "unemp", "ln_inc")
    )

    robust: dict[str, Verdict] = {}
    for k, fits in a_for_judge.items():
        robust[f"A {k}"] = judge(Inputs(fits, b, c_main, c_inc))
    for k, dc in b_alt.items():
        robust[f"B {k}"] = judge(Inputs(a, dc, c_main, c_inc))
    robust["C outcome nm50"] = judge(Inputs(a, b, c_specs["nm50"], c_specs["nm50_inc"]))
    robust["C outcome TFR"] = judge(Inputs(a, b, c_specs["tfr"], c_specs["tfr_inc"], c_flip=True))
    robust["C private rent"] = judge(
        Inputs(a, b, c_specs["rent_priv"], c_specs["rent_priv_inc"], c_rent="ln_rent_priv")
    )
    changes = [
        f"{k} で {'・'.join(r.supported) or 'なし'} が支持・主要 {r.lead or 'なし'}"
        for k, r in robust.items()
        if (r.lead, r.supported) != (v.lead, v.supported)
    ]
    gap = male_gap(emp)
    final = final_stance(v.lead, b.comp_share)
    framed = framed_stance(
        lead=v.lead,
        comp_share=b.comp_share,
        comp_lower=bl.comp_share,
        rate_share=b.rate_share,
        gap=gap,
        passed=v.names,
        robust_changes=changes,
    )
    return H10Result(a, b, bl, gap, c_main, c_inc, v, final, framed, robust, b_rows, c_specs, a_alt)


def describe_data(d: Mapping[str, pl.DataFrame]) -> None:
    print("\n== Data ==")
    for k, df in d.items():
        print(f"  {k}: {df.height} rows")
    panel, src = country_panel(d)
    cov = (
        panel.group_by("iso3")
        .agg(
            *[pl.col(c).drop_nulls().len().alias(c) for c in A_COLS],
        )
        .sort("iso3")
    )
    print("  A country-year coverage (non-null years per variable):")
    print(cov)
    print("  A outcome source (fagem / cmr):", src)


def section_a(res: H10Result, d: Mapping[str, pl.DataFrame], fig_dir: Path) -> None:
    print("\n== A: country × period panel (5-year differences, country + period FE) ==")
    panel, _ = country_panel(d)
    ld = a_frame(panel, A_WIDTH)
    for y in A_Y:
        f = ld.drop_nulls([f"d_{y}", *[f"d_{x}" for x in A_X]])
        print(f"  sample {y}: n={f.height} countries={sorted(set(f['iso3'].to_list()))}")
    print_a(res.a, "A main")
    for x in A_X:
        print(f"  A test {x}: {a_test(res.a, x)}")
    print("\n-- A robustness --")
    for k, fits in res.a_alt.items():
        xs = list(next((f.coefs.keys() for f in fits.values() if f is not None), A_X))
        print_a(fits, f"A {k}", xs)
    fig_a(res.a, fig_dir / "h10_a_country_panel.png")


def section_b(res: H10Result, d: Mapping[str, pl.DataFrame], fig_dir: Path) -> None:
    print("\n== B: Kitagawa decomposition (Employment Status Survey, employed + not employed) ==")
    emp = d["emp"]
    for sex in ("male", "female"):
        for y in (2007, 2012, 2017, 2022):
            for a in B_AGES:
                c = b_cells(emp, y, sex, (a,), sum4=(y == 2007))
                tot = sum(c[(a, e)][0] for e in EMP3)
                parts = "  ".join(
                    f"{e}: share {c[(a, e)][0] / tot:.3f} nm {c[(a, e)][1] / c[(a, e)][0]:.3f}"
                    for e in EMP3
                )
                print(
                    f"  {sex:<6} {y} {a}  N={tot:>10.0f}  {parts}"
                    f"{'  (nonreg = 4 sub-types)' if y == 2007 else ''}"
                )
    for tag, dc in res.b_rows:
        print_b(dc, tag)
    print(f"  2022 men 30-34 never-married: regular − non-regular = {res.gap_2022:+.1f} pt")
    for y in (2012, 2017, 2022):
        print(f"  {y} men 30-34 regular − non-regular = {male_gap(emp, y):+.1f} pt")
    print(f"  B test (comp share >= {B_COMP_MIN:.0%}): {res.verdict.b_passed}")
    fig_b_rates(emp, fig_dir / "h10_b_rates_by_employment.png")
    fig_b_decomp(res.b_rows, fig_dir / "h10_b_kitagawa.png")


def section_c(res: H10Result, fig_dir: Path) -> None:
    print("\n== C: prefecture panel (prefecture + year FE) ==")
    specs = {
        "main": ("nm3034 main", C_X, False),
        "income": ("nm3034 + income (2010-2020)", (*C_X, "ln_inc"), False),
        "nm50": ("never married at 50 (M)", C_X, False),
        "nm50_inc": ("never married at 50 + income", (*C_X, "ln_inc"), False),
        "tfr": ("TFR", C_X, True),
        "tfr_inc": ("TFR + income", (*C_X, "ln_inc"), True),
        "rent_priv": (
            "nm3034, private rent (2018-)",
            ("nonreg", "ln_rent_priv", "flfp", "unemp"),
            False,
        ),
        "rent_priv_inc": (
            "nm3034, private rent + income",
            ("nonreg", "ln_rent_priv", "flfp", "unemp", "ln_inc"),
            False,
        ),
    }
    for k, (tag, xs, flip) in specs.items():
        print_c(res.c_specs[k], tag, xs, flip)
    fig_c(
        [
            ("Never married, men 30-34", res.c_specs["main"], C_X, False),
            ("+ log income (2010-2020)", res.c_specs["income"], (*C_X, "ln_inc"), False),
            ("Never married at 50, men", res.c_specs["nm50"], C_X, False),
            ("TFR (signs reversed)", res.c_specs["tfr"], C_X, True),
        ],
        fig_dir / "h10_c_prefecture_panel.png",
    )


def section_verdict(res: H10Result) -> None:
    v = res.verdict
    print("\n== Verdict (pre-registered) ==")
    for k in CONSTRAINTS:
        print(
            f"  {k} {CONSTRAINT_JA[k]}: {sum(v.tests[k])}/{len(v.tests[k])} "
            f"passed {v.names[k]} -> {'supported' if k in v.supported else 'not supported'}"
        )
    print(f"  lead constraint: {v.lead}")
    print(f"  final_stance: {res.final}")
    print(f"  framed_stance: {res.framed}")
    print("\n-- verdict under each robustness spec --")
    print(f"  {'main':<28} {verdict_line(v)}")
    for k, r in res.robust.items():
        print(f"  {k:<28} {verdict_line(r)}")


def section_exploratory(res: H10Result, d: Mapping[str, pl.DataFrame]) -> None:
    print("\n== Exploratory (not pre-registered, outside the verdict) ==")
    emp = d["emp"]

    # E1: 4-group split of "other" into other-employed / not employed
    def cells4(y: int) -> Cells:
        c3 = b_cells(emp, y, "male", B_AGES)
        sub = emp.filter(
            (pl.col("survey_year") == y)
            & (pl.col("sex") == "male")
            & (pl.col("employment") == "not_employed")
        )
        ne = {
            (r["age_class"], r["marital"]): float(r["persons"]) for r in sub.iter_rows(named=True)
        }
        out: Cells = {}
        for a in B_AGES:
            o = c3[(a, "other")]
            n = (ne[(a, "total")], ne[(a, "never_married")])
            out[(a, "regular")] = c3[(a, "regular")]
            out[(a, "nonregular")] = c3[(a, "nonregular")]
            out[(a, "not_employed")] = n
            out[(a, "other_employed")] = (o[0] - n[0], o[1] - n[1])
        return out

    e1 = kitagawa_age(
        cells4(2012), cells4(2022), ("regular", "nonregular", "other_employed", "not_employed")
    )
    print_b(e1, "E1 men 25-39 2012->2022, 4 groups (other split into employed / not employed)")
    obs = pref_obs(d["pref"])
    # E2: C without female LFP so that 1990 stays in
    cf = c_frame(obs, C_YEARS)
    print_c(
        run_c(cf, "nm3034", ("nonreg", "ln_rent", "unemp")),
        "E2 C main without female LFP (keeps 1990)",
        ("nonreg", "ln_rent", "unemp"),
    )
    # E3: total (both sexes) non-regular share, and female LFP 30-44
    print_c(
        run_c(cf, "nm3034", ("nonreg_t", "ln_rent", "flfp", "unemp")),
        "E3 C, non-regular share both sexes",
        ("nonreg_t", "ln_rent", "flfp", "unemp"),
    )
    print_c(
        run_c(cf, "nm3034", ("nonreg", "ln_rent", "flfp3044", "unemp")),
        "E4 C, female LFP 30-44",
        ("nonreg", "ln_rent", "flfp3044", "unemp"),
    )
    # E5: within-type rise of never-married share, men 30-34, by type
    for e in ("regular", "nonregular", "other"):
        r12 = b_cells(emp, 2012, "male", ("30-34",))[("30-34", e)]
        r22 = b_cells(emp, 2022, "male", ("30-34",))[("30-34", e)]
        print(f"  E5 men 30-34 {e:<10} {r12[1] / r12[0]:.3f} -> {r22[1] / r22[0]:.3f}")
    # E6: private rent (2018/2023 only) matched to the *next* survey (2015 <- 2018, 2020 <- 2023);
    # the pre-registered nearest-year match gives 2018 for both years (no within variation).
    nxt = {
        c: {2015: s[2018], 2020: s[2023]}
        for c, s in obs["ln_rent_priv"].items()
        if 2018 in s and 2023 in s
    }
    obs6 = {**obs, "ln_rent_priv": nxt}
    f6 = c_frame(obs6, (2015, 2020))
    xs6 = ("nonreg", "ln_rent_priv", "flfp", "unemp")
    print_c(run_c(f6, "nm3034", xs6), "E6 C, private rent matched to next survey (2015, 2020)", xs6)
    # E7: each C regressor alone (FE as in the main spec): is the joint null collinearity?
    for x in C_X:
        print_c(run_c(cf, "nm3034", (x,)), f"E7 C, {x} alone", (x,))
    print_c(
        run_c(c_frame(obs, C_INC_YEARS), "nm3034", ("ln_inc",)), "E7 C, ln_inc alone", ("ln_inc",)
    )


for _k in ("nonreg_t", "flfp3044", "ln_rent_priv"):
    C_SIGN.setdefault(_k, 1)
LABEL.update(
    {
        "nonreg_t": "non-regular share, both sexes (%)",
        "flfp3044": "female LFP 30-44 (%)",
        "ln_rent_priv": "log private rent (all)",
    }
)


def run(data_dir: Path, fig_dir: Path) -> H10Result:
    pl.Config.set_tbl_rows(-1)
    pl.Config.set_tbl_width_chars(200)
    pl.Config.set_tbl_cols(-1)
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = load(data_dir)
    print("== Operational choices fixed before the first run (also in the module docstring) ==")
    print(
        f"  A: width {A_WIDTH} ({A_START}-{A_END}), endpoint window ±{A_WINDOW}, n>={A_MIN_N}, G>"
        f"={A_MIN_G}"
    )
    print("  A test per regressor = majority of the estimated outcomes pass")
    print(
        f"  B: cells age {B_AGES} × {EMP3}; main {B_MAIN}, lower {B_LOWER} with 4 sub-types both ye"
        "ars"
    )
    print(f"  C: years {C_YEARS} (income {C_INC_YEARS}), nearest ±{C_WINDOW}; signs {C_SIGN}")
    print("  Lead tie-break: passes, then B-passed, then pass ratio, then E,H,Y,W")
    describe_data(d)
    res = compute(d)
    section_a(res, d, fig_dir)
    section_b(res, d, fig_dir)
    section_c(res, fig_dir)
    section_verdict(res)
    section_exploratory(res, d)
    fig_long(d["mar"], fig_dir / "h10_japan_long_run.png")
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
