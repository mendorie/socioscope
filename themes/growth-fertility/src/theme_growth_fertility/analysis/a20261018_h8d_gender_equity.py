"""H8d（事後追加）: 2 人未満への低下の「深さ」は家庭内の男女分業で決まるか（仮説 G）。
韓国の学校外教育費は加算要因か（仮説 K、記述のみ）。

事前固定: design/themes/growth-fertility.md「### H8d」（2026-10-18）。H8c の結果を見た後の
追加検証で、
検定 Z1〜Z6・判定規則・最終スタンスの文型・頑健性リストは追加データを見る前に固定した。
結果は H8〜H8c の判定を変えない。

  Z1（主、横断）  各国の最新の無償労働観測年（2000 年以降）で、その年の TFR < 2.5 の国:
                 tfr ~ female_share + fem_lfp + ln gdp_pcap_ppp + tert_enrol（HC1、説明変数は
                 標本 SD で標準化）＋ Spearman。WDI の値は観測年、無ければ ±2 年の最近傍
                 （同距離は前の年）。
  Z2 交互作用    Z1 + female_share × fem_lfp（標準化 = 中心化済みの積）。fem_lfp 上位半分
                 （Z1 標本の中央値以上）の部分標本で Z1 式を推定し、female_share の勾配を報告。
  Z3 代替指標    female_share を IC_GEN_MGTL（女性管理職割合）、HDR pr_f（女性議席割合）、
                 lfpr_f/lfpr_m、GII に差し替え（同じ国・年、±2 年の最近傍）。予測の向き:
                 前 3 つは正、GII は負（公平なほど TFR が高い）。
  Z4 within      (a) 同じ年齢層で 5 年以上離れた最初と最後の観測がある国の Δtfr ~ Δfemale_share
                 （HC1、標準化）＋ Spearman。(b) HDR 構成要素の 10 年長期差分（H8 T6 の枠:
                 端点 ±2 年の最近傍、国＋期間 FE、国クラスタ、開始 TFR < 3、1990→2000→2010→2020）:
                 Δtfr ~ Δ(lfpr_f/lfpr_m) + Δpr_f + Δfem_sec_enrol + Δln gdp_pcap_const。
  Z5 記述（K）   韓国の 1 人当たり月平均私教育費（名目）・参加率・TFR の 2007–2025、自녀수별表。
  Z6 記述        東アジア・南欧・北欧・英語圏の female_share × fem_lfp × TFR。

年齢層（事前固定）: 国・年ごとに 15+ → 10+ → 20+ → 16+ → ALLAGE の順で、女性と男性の両方が
ALLAREA で観測される最初の層を使う（`select_band`）。どれも無い国・年（ESP・DNK・BGR は 20-74 のみ、
BEL は 12+ 等）は主仕様から外し、頑健性で「最も近い層」（下限が 15 に近い順 → 幅が広い順、
`nearest_band`）を入れた版を 1 本出す。

判定（事前固定、`verdict_g`）: 支持 = Z1 の female_share が負・CI∌0、または Z2 の交互作用が負・CI∌0
かつ上位半分の勾配が負・CI∌0。部分的支持 = Z1 の点推定が負（CI∋0）で Z3 の 4 指標のうち 2 つ以上が
予測の向きで CI∌0。不支持 = それ以外。Z1・Z2 で予測と逆の符号・CI∌0 は「逆向き」と明記
（`reverse_g`）。
Z4 は整合性の確認（`z4_note`）。K は判定しない。

決定的スクリプト。入力は data/marts/{gender_equity, hdr_gender, kr_private_tutoring,
growth_fertility_panel}.parquet。乱数・現在時刻は使わない。欠損は補完しない（listwise）。
H8・H8b・H8c のスクリプトは変更せず関数を import する。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋ヘルパ（female_share, band_bounds, nearest_band, unpaid_wide, select_band, latest_per_country,
within_pairs, alt_hits, verdict_g, reverse_g, final_stance_g, z4_note）は
tests/test_analysis_h8d.py で検証する。
"""

from __future__ import annotations

import argparse
import re
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261017_h8_mechanisms as h8
from theme_growth_fertility.analysis import a20261018_h8b_within_group as h8b
from theme_growth_fertility.analysis import a20261018_h8c_education_cost as h8c
from theme_growth_fertility.analysis.a20261004_h1_income_tfr import (
    BLUE_RAMP,
    INK,
    MUTED,
    ORANGE,
    Est,
    _style,
)
from theme_growth_fertility.oecd import OECD_MEMBERS

THEME_DIR = h8.THEME_DIR
REPO_ROOT = h8.REPO_ROOT
PANEL_MART = h8.PANEL_MART
GENDER_MART = Path("marts") / "gender_equity.parquet"
HDR_MART = Path("marts") / "hdr_gender.parquet"
KR_MART = Path("marts") / "kr_private_tutoring.parquet"

Coef = tuple[float, float, float, float]  # (b, se, lo, hi)

UNPAID = "SL_DOM_TSPD"
MANAGERS = "IC_GEN_MGTL"
AGE_PRIORITY = ("15+", "10+", "20+", "16+", "ALLAGE")
MIN_YEAR = 2000
CUT = 2.5
WINDOW = 2
CONTROLS = ("flfp", "ln_gdp", "tert")
Z1_VARS = ("share", *CONTROLS)
ALT_SIGN = {"mgr": 1, "parl": 1, "lfp_ratio": 1, "gii": -1}
ALT_LABEL = {
    "mgr": "women in managerial positions (%)",
    "parl": "women's share of parliamentary seats (%)",
    "lfp_ratio": "female / male labour-force participation",
    "gii": "Gender Inequality Index (0-1)",
}
ALT_JA = {
    "mgr": "女性管理職割合",
    "parl": "女性議員割合",
    "lfp_ratio": "労働参加率の男女比",
    "gii": "ジェンダー不平等指数",
}
LABEL = {
    "share": "unpaid-work female share F/(F+M)",
    "flfp": "female LFP (%)",
    "ln_gdp": "ln GDP pc PPP",
    "tert": "tertiary enrolment (%)",
    "inter": "share x female LFP",
    **ALT_LABEL,
}
REVERSE_JA = {
    "z1": "Z1 の無償労働の女性偏り",
    "z2_interaction": "Z2 の交互作用",
    "z2_upper": "Z2 の女性労働参加率上位半分での勾配",
}
VERDICT_JA = {"support": "支持", "partial": "部分的支持", "no": "不支持"}
Z4_VARS = ("d_lfr", "d_prf", "d_sec", "d_ln_gdp")
Z4_COLS = ("tfr", "lfr", "prf", "sec", "ln_gdp")
Z4_LABEL = {
    "d_lfr": "Δ female/male LFP ratio",
    "d_prf": "Δ women's parliament share",
    "d_sec": "Δ female sec. enrolment",
    "d_ln_gdp": "Δ ln GDP pc (const.)",
}

GROUPS: dict[str, tuple[str, ...]] = {
    "East Asia": ("JPN", "KOR"),
    "Southern Europe": ("ITA", "ESP"),
    "Nordic": ("DNK", "FIN", "NOR", "SWE"),
    "English-speaking": ("USA", "GBR", "CAN", "AUS"),
}
GROUP_COLOR = {
    "East Asia": ORANGE,
    "Southern Europe": "#b2182b",
    "Nordic": BLUE_RAMP[3],
    "English-speaking": "#4d9221",
}
FOCUS = tuple(i for g in GROUPS.values() for i in g)

SDG_SOURCE = (
    "Source: UN Statistics Division, SDG Global Database (SL_DOM_TSPD, IC_GEN_MGTL); "
    "TFR, LFP, GDP, enrolment: World Bank WDI (CC BY 4.0)."
)
HDR_SOURCE = (
    "Source: UNDP (2025) HDR composite indices time series (CC BY 3.0 IGO); World Bank WDI."
)
KR_SOURCE = (
    "Source: Ministry of Education (Korea), 2025 Private Education Expenditures Survey press "
    "release (2026-03-12), moe.go.kr (KOGL Type 1); TFR, GDP: World Bank WDI."
)


# ---------------------------------------------------------------- pure helpers (tested)
def female_share(f: float, m: float) -> float | None:
    """F / (F + M); None when the total is not positive."""
    t = f + m
    return None if t <= 0 else f / t


_OPEN = re.compile(r"^(\d+)\+$")
_CLOSED = re.compile(r"^(\d+)-(\d+)$")


def band_bounds(age: str) -> tuple[int, int | None]:
    """'15+' -> (15, None), '20-74' -> (20, 74), 'ALLAGE' -> (0, None). Else ValueError."""
    if age == "ALLAGE":
        return 0, None
    m = _OPEN.match(age)
    if m:
        return int(m.group(1)), None
    m = _CLOSED.match(age)
    if m:
        return int(m.group(1)), int(m.group(2))
    raise ValueError(f"unrecognised age band {age!r}")


def nearest_band(ages: Sequence[str], target: int = 15) -> str:
    """Fallback rule (fixed before looking at results): lower bound nearest to `target`, then the
    widest band (open-ended counts as widest), then name."""

    def key(a: str) -> tuple[int, int, str]:
        lo, hi = band_bounds(a)
        width = 10_000 if hi is None else hi - lo
        return abs(lo - target), -width, a

    return sorted(ages, key=key)[0]


def unpaid_wide(g: pl.DataFrame, series: str = UNPAID) -> pl.DataFrame:
    """Long gender_equity -> (iso3, year, age, F, M) for ALLAREA rows of `series` where both sexes
    are observed. Sorted by iso3, year, age."""
    f = g.filter((pl.col("series") == series) & (pl.col("location") == "ALLAREA"))
    fem = f.filter(pl.col("sex") == "F").select("iso3", "year", "age", pl.col("value").alias("F"))
    mal = f.filter(pl.col("sex") == "M").select("iso3", "year", "age", pl.col("value").alias("M"))
    return fem.join(mal, on=["iso3", "year", "age"], how="inner").sort("iso3", "year", "age")


def _with_share(w: pl.DataFrame) -> pl.DataFrame:
    shares = [female_share(float(a), float(b)) for a, b in w.select("F", "M").rows()]
    return w.with_columns(pl.Series("female_share", shares, dtype=pl.Float64))


def select_band(
    w: pl.DataFrame, *, priority: Sequence[str] = AGE_PRIORITY, fallback: bool = False
) -> pl.DataFrame:
    """One row per iso3 × year: the first band in `priority` present (both sexes). With `fallback`,
    country-years with none of them use `nearest_band` over what they have. Adds female_share."""
    rows: list[dict[str, Any]] = []
    for (iso, year), grp in w.group_by("iso3", "year", maintain_order=True):
        by_age = {str(r["age"]): r for r in grp.iter_rows(named=True)}
        pick = next((a for a in priority if a in by_age), None)
        if pick is None and fallback:
            pick = nearest_band(sorted(by_age))
        if pick is None:
            continue
        r = by_age[pick]
        rows.append({"iso3": iso, "year": year, "age": pick, "F": r["F"], "M": r["M"]})
    schema = {"iso3": pl.Utf8, "year": pl.Int64, "age": pl.Utf8, "F": pl.Float64, "M": pl.Float64}
    out = pl.DataFrame(rows, schema=schema, orient="row").sort("iso3", "year")
    return _with_share(out)


def latest_per_country(frame: pl.DataFrame, *, min_year: int) -> pl.DataFrame:
    """Per iso3, the row of the latest year >= min_year. Sorted by iso3."""
    return (
        frame.filter(pl.col("year") >= min_year)
        .sort("iso3", "year")
        .group_by("iso3", maintain_order=True)
        .last()
    )


def within_pairs(
    w: pl.DataFrame, *, min_gap: int = 5, priority: Sequence[str] = AGE_PRIORITY
) -> pl.DataFrame:
    """Per iso3, the first band in `priority` whose first and last observed years are at least
    `min_gap` apart; returns iso3, age, y0, y1, share_0, share_1, d_share (same band at both
    ends)."""
    s = _with_share(w)
    rows: list[dict[str, Any]] = []
    for (iso,), grp in s.group_by("iso3", maintain_order=True):
        for a in priority:
            g = grp.filter(pl.col("age") == a).sort("year")
            if g.height < 2:
                continue
            y0, y1 = int(g["year"][0]), int(g["year"][-1])
            if y1 - y0 < min_gap:
                continue
            s0, s1 = float(g["female_share"][0]), float(g["female_share"][-1])
            rows.append(
                {
                    "iso3": iso,
                    "age": a,
                    "y0": y0,
                    "y1": y1,
                    "share_0": s0,
                    "share_1": s1,
                    "d_share": s1 - s0,
                }
            )
            break
    schema = {
        "iso3": pl.Utf8,
        "age": pl.Utf8,
        "y0": pl.Int64,
        "y1": pl.Int64,
        "share_0": pl.Float64,
        "share_1": pl.Float64,
        "d_share": pl.Float64,
    }
    return pl.DataFrame(rows, schema=schema, orient="row").sort("iso3")


def _sig(c: Coef | None) -> bool:
    return c is not None and (c[2] > 0 or c[3] < 0)


def _neg_sig(c: Coef | None) -> bool:
    return c is not None and c[0] < 0 and _sig(c)


def _pos_sig(c: Coef | None) -> bool:
    return c is not None and c[0] > 0 and _sig(c)


def alt_hits(alt: Mapping[str, Coef], signs: Mapping[str, int] = ALT_SIGN) -> list[str]:
    """Z3 indicators in the predicted direction (more equal -> higher TFR) with CI excluding 0,
    in `signs` order."""
    out = []
    for k, s in signs.items():
        c = alt.get(k)
        if c is not None and _sig(c) and c[0] * s > 0:
            out.append(k)
    return out


def verdict_g(
    z1: Coef, z2_inter: Coef | None, z2_upper: Coef | None, alt: Mapping[str, Coef]
) -> str:
    """Pre-registered verdict on 仮説 G: 'support' / 'partial' / 'no'."""
    if _neg_sig(z1) or (_neg_sig(z2_inter) and _neg_sig(z2_upper)):
        return "support"
    if z1[0] < 0 and len(alt_hits(alt)) >= 2:
        return "partial"
    return "no"


def reverse_g(z1: Coef, z2_inter: Coef | None, z2_upper: Coef | None) -> list[str]:
    """Z1 / Z2 coefficients opposite to the prediction (positive) with CI excluding 0."""
    named = (("z1", z1), ("z2_interaction", z2_inter), ("z2_upper", z2_upper))
    return [k for k, c in named if _pos_sig(c)]


def final_stance_g(verdict: str, *, hits: Sequence[str], reverse: Sequence[str]) -> str:
    """Final stance sentence in the pre-registered form (design H8d 最終スタンスの文型)."""
    if verdict == "support":
        s = (
            "2 人未満への低下の深さは、女性の就業が進んだのに家事・育児が女性に偏ったままの"
            "社会ほど大きい。"
        )
    elif verdict == "partial":
        names = "・".join(ALT_JA[h] for h in hits)
        s = (
            "2 人未満への低下の深さは、家事・育児時間の女性偏りでは確かめられないが、"
            f"{names}で見て男女が公平な国ほど出生率が高い（部分的支持）。"
        )
    elif verdict == "no":
        s = (
            "家庭内の男女分業でも深さは説明できない。2 人未満への低下について本シリーズで残る"
            "説明は、規範の拡散仮説だけである。"
        )
    else:
        raise ValueError(f"unknown verdict {verdict!r}")
    if reverse:
        names = "・".join(REVERSE_JA[r] for r in reverse)
        s += f"ただし{names}は逆向き（女性偏りが大きいほど出生率が高い）である。"
    return s


ROBUST_JA = {
    "TFR < 2.1": "TFR < 2.1",
    "TFR < 3.0": "TFR < 3.0",
    "OECD members": "OECD 加盟国のみ",
    "10+ band only": "10+ 年齢層のみ",
    "excl JPN": "日本除外",
    "excl KOR": "韓国除外",
    "excl pop < 1m": "人口 100 万未満除外",
    "no income/enrolment": "所得・就学率なし",
}
ISO_JA = {"KOR": "韓国", "JPN": "日本", "ITA": "イタリア"}


def framed_stance(
    verdict: str,
    *,
    hits: Sequence[str],
    reverse: Sequence[str],
    n: int,
    cut: float,
    flips: Sequence[tuple[str, str]],
    depends_on: Sequence[str] = (),
) -> str:
    """Report-facing stance: the pre-registered sentence quoted as 「事前の文型では」, followed by
    the qualifications the methodology review required. `flips` = (pre-registered robustness label,
    verdict) pairs whose verdict differs from the main one; `depends_on` = countries whose removal
    turns an OECD 'support' back into the main verdict."""
    s = f"事前の規則では{VERDICT_JA[verdict]}である。"
    if verdict == "no":
        s += (
            f"TFR < {cut:g} の広い標本（{n} か国）では、事前の条件で無償労働の女性偏りと TFR の"
            "関連を確かめられない。"
        )
    s += f"事前の文型では「{final_stance_g(verdict, hits=hits, reverse=reverse)}」となる。"
    if flips:
        parts = "、".join(f"{ROBUST_JA.get(lab, lab)}では{VERDICT_JA[v]}" for lab, v in flips)
        s += f"ただし{parts}になり、判定は仕様に左右される。"
    if depends_on:
        names = "・".join(ISO_JA.get(i, i) for i in depends_on)
        s += f"OECD の支持は{names} 1 か国に依存する（除くと{VERDICT_JA[verdict]}）。"
    if verdict == "no":
        s += (
            "「残る説明は規範の拡散仮説だけ」は検証した候補が条件を満たさなかったという消去法の"
            "言明で、規範の拡散そのものは測っていない。"
        )
    return s


def z4_note(verdict: str, z4: Coef | None) -> str:
    """Pre-registered consistency remark from the within test (Z4a Δshare coefficient)."""
    if verdict in ("support", "partial"):
        return "" if _neg_sig(z4) else "国の中の変化では確かめられない"
    if _neg_sig(z4):
        return "国の中の変化では負の関連が見られる（主判定と食い違う）"
    return ""


# ---------------------------------------------------------------- frames
def _fmt(c: Coef | None) -> str:
    if c is None:
        return "n/a"
    return f"{c[0]:+.3f} [{c[2]:+.3f}, {c[3]:+.3f}]{'*' if _sig(c) else ' '}"


def hdr_wide(h: pl.DataFrame) -> pl.DataFrame:
    """(iso3, year, gii, pr_f, lfpr_f, lfpr_m, lfp_ratio)."""
    w = h.filter(pl.col("metric").is_in(["gii", "pr_f", "lfpr_f", "lfpr_m"])).pivot(
        on="metric", index=["iso3", "year"], values="value", aggregate_function=None
    )
    for c in ("gii", "pr_f", "lfpr_f", "lfpr_m"):
        if c not in w.columns:
            w = w.with_columns(pl.lit(None, dtype=pl.Float64).alias(c))
    return (
        w.select("iso3", "year", "gii", "pr_f", "lfpr_f", "lfpr_m")
        .with_columns(
            pl.when(pl.col("lfpr_m") > 0)
            .then(pl.col("lfpr_f") / pl.col("lfpr_m"))
            .alias("lfp_ratio")
        )
        .sort("iso3", "year")
    )


def wdi_frame(panel: pl.DataFrame) -> pl.DataFrame:
    return panel.select(
        "iso3",
        "year",
        "tfr",
        pl.col("fem_lfp").alias("flfp"),
        pl.when(pl.col("gdp_pcap_ppp") > 0).then(pl.col("gdp_pcap_ppp").log()).alias("ln_gdp"),
        pl.col("tert_enrol").alias("tert"),
    )


def cross_section(
    sel: pl.DataFrame, panel: pl.DataFrame, g: pl.DataFrame, hw: pl.DataFrame
) -> pl.DataFrame:
    """Latest unpaid-work observation (>= MIN_YEAR) per country with WDI and Z3 indicators at the
    same year (±WINDOW nearest). Not yet cut on TFR."""
    lat = latest_per_country(sel, min_year=MIN_YEAR).select(
        "iso3", "year", "age", "F", "M", pl.col("female_share").alias("share")
    )
    out = h8c.attach_nearest(
        lat, wdi_frame(panel), ("tfr", *CONTROLS), window=WINDOW, year_col="year"
    )
    mgr = g.filter((pl.col("series") == MANAGERS) & (pl.col("sex") == "F")).select(
        "iso3", "year", pl.col("value").alias("mgr")
    )
    out = h8c.attach_nearest(out, mgr, ("mgr",), window=WINDOW, year_col="year")
    hh = hw.select("iso3", "year", pl.col("pr_f").alias("parl"), "lfp_ratio", "gii")
    out = h8c.attach_nearest(out, hh, ("parl", "lfp_ratio", "gii"), window=WINDOW, year_col="year")
    names = panel.select("iso3", "country").unique("iso3")
    return out.join(names, on="iso3", how="left").sort("iso3")


@dataclass(frozen=True)
class GResult:
    frame: pl.DataFrame  # Z1 listwise sample, raw values
    z1: Est
    sds: dict[str, float]
    rho: tuple[float, float]
    z2: Est
    upper: Est | None
    lower: Est | None
    median_flfp: float
    alt: dict[str, Est]
    alt_rho: dict[str, tuple[float, float]]
    verdict: str
    hits: list[str]
    reverse: list[str]

    @property
    def z1c(self) -> Coef:
        return self.z1.coefs["share"]

    @property
    def z2i(self) -> Coef:
        return self.z2.coefs["inter"]

    @property
    def z2u(self) -> Coef | None:
        return None if self.upper is None else self.upper.coefs["share"]


def _print_est(est: Est, xs: Sequence[str], sds: Mapping[str, float]) -> None:
    print(f"  {est.label}  n={est.n} r2={est.extra['r2']:.3f}")
    for k in xs:
        sd = f"  SD={sds[k]:.4f}" if k in sds else ""
        print(f"      {k:<10} {_fmt(est.coefs[k])}{sd}  ({LABEL.get(k, k)})")


def run_g(
    cs: pl.DataFrame,
    tag: str,
    *,
    cut: float = CUT,
    controls: Sequence[str] = CONTROLS,
    verbose: bool = True,
) -> GResult:
    """Z1 + Z2 + Z3 on a cross-section frame from `cross_section` and the verdict."""
    xs = ("share", *controls)
    base = cs.filter(pl.col("tfr") < cut)
    f = base.drop_nulls(["tfr", *xs])
    fs, sds = h8b.standardize(f, xs)
    z1 = h8c.ols_hc1(fs, "tfr", xs, label=f"[{tag}] Z1 OLS HC1 (standardised)")
    rho = h8b.spearman(f["share"].to_list(), f["tfr"].to_list())
    fz2 = fs.with_columns((pl.col("share") * pl.col("flfp")).alias("inter"))
    z2 = h8c.ols_hc1(fz2, "tfr", (*xs, "inter"), label=f"[{tag}] Z2 + share x female LFP")
    med = float(statistics.median(f["flfp"].to_list()))
    hi = fs.filter(pl.Series(f["flfp"].to_list()) >= med)
    lo = fs.filter(pl.Series(f["flfp"].to_list()) < med)
    upper = (
        h8c.ols_hc1(hi, "tfr", xs, label=f"[{tag}] Z2 upper half (female LFP >= {med:.1f})")
        if hi.height >= len(xs) + 3
        else None
    )
    lower = (
        h8c.ols_hc1(lo, "tfr", xs, label=f"[{tag}] Z2 lower half (female LFP < {med:.1f})")
        if lo.height >= len(xs) + 3
        else None
    )
    alt: dict[str, Est] = {}
    alt_rho: dict[str, tuple[float, float]] = {}
    alt_sds: dict[str, float] = {}
    for a in ALT_SIGN:
        xa = (a, *controls)
        fa = base.drop_nulls(["tfr", *xa])
        fas, sa = h8b.standardize(fa, xa)
        alt_sds[a] = sa[a]
        alt[a] = h8c.ols_hc1(fas, "tfr", xa, label=f"[{tag}] Z3 {a}")
        alt_rho[a] = h8b.spearman(fa[a].to_list(), fa["tfr"].to_list())
    alt_c = {a: e.coefs[a] for a, e in alt.items()}
    z2u = None if upper is None else upper.coefs["share"]
    v = verdict_g(z1.coefs["share"], z2.coefs["inter"], z2u, alt_c)
    hits = alt_hits(alt_c)
    rev = reverse_g(z1.coefs["share"], z2.coefs["inter"], z2u)
    if verbose:
        yrs = f["year"].to_list()
        ages = f.group_by("age").len().sort("age").rows()
        print(
            f"[{tag}] Z1 sample: n={f.height} (TFR < {cut}; of {cs.height} countries with an "
            f"unpaid-work observation >= {MIN_YEAR}); years {min(yrs)}–{max(yrs)}, median "
            f"{statistics.median(yrs):.0f}; age bands {ages}"
        )
        _print_est(z1, xs, sds)
        print(f"      Spearman tfr × share rho={rho[0]:+.3f} p={rho[1]:.3f}")
        _print_est(z2, (*xs, "inter"), sds)
        for e in (upper, lower):
            if e is None:
                print("  (half sample too small)")
            else:
                _print_est(e, xs, {})
        for a in ALT_SIGN:
            e = alt[a]
            print(
                f"  [{tag}] Z3 {a:<9} n={e.n} {_fmt(e.coefs[a])} SD={alt_sds[a]:.3f} "
                f"(predicted sign {'+' if ALT_SIGN[a] > 0 else '-'}); Spearman "
                f"rho={alt_rho[a][0]:+.3f} p={alt_rho[a][1]:.3f}  ({ALT_LABEL[a]})"
            )
        print(
            f"[{tag}] verdict={v} ({VERDICT_JA[v]}); Z3 hits={hits or 'none'}; "
            f"reverse={rev or 'none'}"
        )
    return GResult(f, z1, sds, rho, z2, upper, lower, med, alt, alt_rho, v, hits, rev)


# ---------------------------------------------------------------- Z4
@dataclass(frozen=True)
class Z4a:
    frame: pl.DataFrame
    est: Est | None
    rho: tuple[float, float]


def run_z4a(
    w: pl.DataFrame, panel: pl.DataFrame, tag: str, *, max_tfr0: float | None = None
) -> Z4a:
    p = within_pairs(w)
    tf = panel.select("iso3", "year", "tfr")
    a0 = h8c.attach_nearest(
        p.rename({"y0": "year"}), tf, ("tfr",), window=WINDOW, year_col="year"
    ).rename({"year": "y0", "tfr": "tfr_0"})
    a1 = h8c.attach_nearest(
        a0.rename({"y1": "year"}), tf, ("tfr",), window=WINDOW, year_col="year"
    ).rename({"year": "y1", "tfr": "tfr_1"})
    f = a1.drop_nulls(["tfr_0", "tfr_1"]).with_columns(
        (pl.col("tfr_1") - pl.col("tfr_0")).alias("d_tfr")
    )
    if max_tfr0 is not None:
        f = f.filter(pl.col("tfr_0") < max_tfr0)
    rho = h8b.spearman(f["d_share"].to_list(), f["d_tfr"].to_list())
    est = None
    if f.height >= 5:
        fs, _ = h8b.standardize(f, ["d_share"])
        est = h8c.ols_hc1(fs, "d_tfr", ["d_share"], label=f"[{tag}] Z4a Δtfr ~ Δshare (HC1)")
    print(
        f"[{tag}] Z4a pairs: n={f.height}; gap years median "
        f"{statistics.median((f['y1'] - f['y0']).to_list()):.0f}; median Δshare "
        f"{statistics.median(f['d_share'].to_list()):+.4f}; median ΔTFR "
        f"{statistics.median(f['d_tfr'].to_list()):+.3f}; "
        f"bands {f.group_by('age').len().sort('age').rows()}"
    )
    if est is not None:
        print(f"      Δshare {_fmt(est.coefs['d_share'])} (per SD of Δshare)")
    print(f"      Spearman Δtfr × Δshare rho={rho[0]:+.3f} p={rho[1]:.3f}")
    return Z4a(f, est, rho)


def z4b_base(panel: pl.DataFrame, hw: pl.DataFrame) -> pl.DataFrame:
    p = panel.select(
        "iso3",
        "year",
        "tfr",
        pl.col("fem_sec_enrol").alias("sec"),
        pl.when(pl.col("gdp_pcap_const") > 0).then(pl.col("gdp_pcap_const").log()).alias("ln_gdp"),
    )
    hh = hw.select("iso3", "year", pl.col("lfp_ratio").alias("lfr"), pl.col("pr_f").alias("prf"))
    return p.join(hh, on=["iso3", "year"], how="left").sort("iso3", "year")


def run_z4b(base: pl.DataFrame, tag: str, *, cut: float = 3.0) -> h8.T6Stage | None:
    ld = h8.long_diff_nearest(base, Z4_COLS, width=10, start=1990, end=2020)
    st = h8.t6_stage(ld.filter(pl.col("tfr_0") < cut), Z4_VARS, f"[{tag}] Z4b", verbose=False)
    if st is None:
        print(f"[{tag}] Z4b: too few rows")
        return None
    print(
        f"[{tag}] Z4b 10-year LD 1990–2020, TFR0 < {cut}, country + period FE: "
        f"n={st.n} G={st.countries}"
    )
    for x in Z4_VARS:
        print(f"      {x:<9} {_fmt(st.coefs[x])}  ({Z4_LABEL[x]})")
    return st


# ---------------------------------------------------------------- Z5 (Korea)
def korea_frame(k: pl.DataFrame, panel: pl.DataFrame) -> pl.DataFrame:
    a = k.filter((pl.col("table") == "annual") & (pl.col("group") == "총계")).pivot(
        on="metric", index="year", values="value", aggregate_function=None
    )
    p = panel.filter(pl.col("iso3") == "KOR").select("year", "tfr", "gdp_pcap_const")
    return a.join(p, on="year", how="left").sort("year")


def run_z5(k: pl.DataFrame, panel: pl.DataFrame) -> pl.DataFrame:
    kf = korea_frame(k, panel)
    b = kf.filter(pl.col("year") == 2007).row(0, named=True)
    print("== Z5: Korea private tutoring (nominal, descriptive; no identification) ==")
    print(
        "  year  spend/student(10k KRW/month)  idx  participation%  spend/participant  "
        "hours/wk  TFR    GDPpc const idx  spend idx / GDP idx"
    )
    for r in kf.iter_rows(named=True):
        si = 100 * r["spend_per_student_10k_krw"] / b["spend_per_student_10k_krw"]
        gi = (
            None if r["gdp_pcap_const"] is None else 100 * r["gdp_pcap_const"] / b["gdp_pcap_const"]
        )
        ratio = "n/a" if gi is None else f"{100 * si / gi:6.1f}"
        sp = r.get("spend_per_participant_10k_krw")
        print(
            f"  {r['year']}  {r['spend_per_student_10k_krw']:>6.1f}                       "
            f"{si:6.1f}  {r['participation_rate_pct']:>6.1f}          "
            f"{'  n/a' if sp is None else f'{sp:5.1f}'}             {r['hours_per_week']:>4.1f}    "
            f"{'n/a ' if r['tfr'] is None else f'{r["tfr"]:.3f}'}  "
            f"{'n/a' if gi is None else f'{gi:6.1f}'}           {ratio}"
        )
    print(
        "  note: spending is nominal; GDP pc is constant 2015 US$ (real). The index ratio "
        "therefore includes Korean inflation and overstates the real rise; "
        "no CPI / nominal KRW GDP in marts."
    )
    bc = k.filter(pl.col("table") == "by_children").pivot(
        on="metric", index=["year", "group"], values="value", aggregate_function=None
    )
    print("  자녀수별 (by number of children in household):")
    for r in bc.sort("year", "group").iter_rows(named=True):
        print(
            f"    {r['year']} {r['group']:<10} spend/student {r['spend_per_student_10k_krw']:5.1f}"
            f"  participation {r['participation_rate_pct']:5.1f}%"
        )
    lv = k.filter(
        (pl.col("table") == "by_level") & (pl.col("metric") == "spend_per_student_10k_krw")
    )
    print(
        "  학교급별 spend/student (10k KRW/month): "
        + "; ".join(f"{y} {g} {v:.1f}" for y, g, v in lv.select("year", "group", "value").rows())
    )
    return kf


# ---------------------------------------------------------------- figures
def _save(fig: Any, path: Path) -> None:
    h8c._save(fig, path)


def _group_of(iso: str) -> str | None:
    for g, members in GROUPS.items():
        if iso in members:
            return g
    return None


def fig_z1(res: GResult, path: Path) -> None:
    plt = h8._plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.8), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    f = res.frame
    for iso, sh, tfr, fl in f.select("iso3", "share", "tfr", "flfp").rows():
        upper = fl >= res.median_flfp
        col = ORANGE if upper else BLUE_RAMP[1]
        foc = iso in FOCUS
        ax.scatter(
            [sh],
            [tfr],
            s=26 if foc else 13,
            color=col,
            zorder=3,
            edgecolor=INK if foc else "none",
            lw=0.5,
        )
        ax.annotate(
            iso,
            (sh, tfr),
            fontsize=6.5 if foc else 5,
            color=INK if foc else MUTED,
            xytext=(2, 2),
            textcoords="offset points",
        )
    ax.scatter([], [], color=ORANGE, s=13, label=f"female LFP >= median ({res.median_flfp:.0f}%)")
    ax.scatter([], [], color=BLUE_RAMP[1], s=13, label="female LFP < median")
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    b = res.z1c
    ax.set_title(
        f"Z1: n = {res.z1.n}; Spearman {res.rho[0]:+.2f} (p = {res.rho[1]:.2f}); "
        f"std. coef. {b[0]:+.2f} [{b[2]:+.2f}, {b[3]:+.2f}]",
        fontsize=8.5,
        color=INK,
    )
    ax.set_xlabel("Female share of unpaid domestic & care work, F/(F+M)", fontsize=8)
    ax.set_ylabel("TFR (children per woman), same year (±2)", fontsize=8)
    _style(ax)
    ax = axes[1]
    rows: list[tuple[str, Coef | None, str]] = [
        (f"Z1 all (n={res.z1.n})", res.z1c, INK),
        ("Z2 interaction share x LFP", res.z2i, ORANGE),
        (f"Z2 upper LFP half (n={res.upper.n if res.upper else 0})", res.z2u, ORANGE),
        (
            f"lower LFP half (n={res.lower.n if res.lower else 0})",
            None if res.lower is None else res.lower.coefs["share"],
            BLUE_RAMP[1],
        ),
    ]
    for i, (_lab, c, col) in enumerate(rows):
        if c is None:
            continue
        ax.errorbar(
            [c[0]], [i], xerr=[[c[0] - c[2]], [c[3] - c[0]]], fmt="o", color=col, capsize=3, ms=5
        )
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=7.5)
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_xlabel("TFR per 1 SD of unpaid-work female share (95% CI, HC1)", fontsize=8)
    ax.set_title(
        "Coefficient on the female share (controls: LFP, ln GDP, tertiary)", fontsize=8.5, color=INK
    )
    _style(ax)
    fig.suptitle(
        f"H8d Z1/Z2: unpaid-work gender split and TFR, latest observation >= {MIN_YEAR}, "
        f"TFR < {CUT}",
        fontsize=10,
        color=INK,
    )
    _foot(
        fig,
        "Age band 15+ (else 10+, 20+, 16+, ALL). Labelled: focus countries (bold edge).\n"
        f"{SDG_SOURCE}",
    )
    _save(fig, path)


def _foot(fig: Any, text: str) -> None:
    h8c._foot(fig, text)


def fig_z3(res: GResult, robust: Sequence[tuple[str, GResult]], path: Path) -> None:
    plt = h8._plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 5.0))
    ax = axes[0]
    keys = list(ALT_SIGN)
    for i, a in enumerate(keys):
        c = res.alt[a].coefs[a]
        hit = a in res.hits
        ax.errorbar(
            [c[0]],
            [i],
            xerr=[[c[0] - c[2]], [c[3] - c[0]]],
            fmt="o",
            color=ORANGE if hit else INK,
            capsize=3,
            ms=5,
        )
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels(
        [
            f"{ALT_LABEL[a]}\n(pred. {'+' if ALT_SIGN[a] > 0 else '-'}, n={res.alt[a].n})"
            for a in keys
        ],
        fontsize=7,
    )
    ax.set_ylim(len(keys) - 0.4, -0.6)
    ax.set_xlabel("TFR per 1 SD (95% CI, HC1)", fontsize=8)
    ax.set_title("Z3: alternative equality indicators replacing the share", fontsize=8.5, color=INK)
    _style(ax)
    ax = axes[1]
    allr = [("main", res), *robust]
    for i, (_lab, r) in enumerate(allr):
        c = r.z1c
        ax.errorbar(
            [c[0]],
            [i],
            xerr=[[c[0] - c[2]], [c[3] - c[0]]],
            fmt="o",
            color=INK if i == 0 else BLUE_RAMP[2],
            capsize=2,
            ms=4,
        )
        ax.annotate(
            f"{r.verdict}",
            (c[3], i),
            xytext=(4, -3),
            textcoords="offset points",
            fontsize=6.5,
            color=MUTED,
        )
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_yticks(range(len(allr)))
    ax.set_yticklabels([f"{lab} (n={r.z1.n})" for lab, r in allr], fontsize=7)
    ax.set_ylim(len(allr) - 0.4, -0.6)
    ax.set_xlabel("Z1 coefficient on unpaid-work female share (per SD)", fontsize=8)
    ax.set_title("Robustness: Z1 coefficient (label = verdict)", fontsize=8.5, color=INK)
    _style(ax)
    fig.suptitle("H8d Z3 and robustness", fontsize=10, color=INK)
    _foot(
        fig,
        "Orange = predicted direction with CI excluding 0.\n"
        f"{SDG_SOURCE} HDR: UNDP (2025), CC BY 3.0 IGO.",
    )
    _save(fig, path)


def fig_z4(z4a: Z4a, z4b: h8.T6Stage | None, path: Path) -> None:
    plt = h8._plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6))
    ax = axes[0]
    for iso, ds, dt in z4a.frame.select("iso3", "d_share", "d_tfr").rows():
        foc = iso in FOCUS
        ax.scatter([ds], [dt], s=22 if foc else 12, color=ORANGE if foc else MUTED, zorder=3)
        ax.annotate(
            iso,
            (ds, dt),
            fontsize=6.5 if foc else 5,
            color=INK if foc else MUTED,
            xytext=(2, 2),
            textcoords="offset points",
        )
    ax.axhline(0, color=MUTED, lw=0.5)
    ax.axvline(0, color=MUTED, lw=0.5)
    c = None if z4a.est is None else z4a.est.coefs["d_share"]
    ax.set_title(
        f"Z4a: n = {z4a.frame.height}; Spearman {z4a.rho[0]:+.2f} (p = {z4a.rho[1]:.2f})"
        + ("" if c is None else f"; std. coef. {c[0]:+.2f} [{c[2]:+.2f}, {c[3]:+.2f}]"),
        fontsize=8.5,
        color=INK,
    )
    ax.set_xlabel(
        "Change in unpaid-work female share (first to last obs., same age band)", fontsize=8
    )
    ax.set_ylabel("Change in TFR over the same years", fontsize=8)
    _style(ax)
    ax = axes[1]
    if z4b is not None:
        for i, x in enumerate(Z4_VARS):
            cc = z4b.coefs[x]
            ax.errorbar(
                [cc[0]],
                [i],
                xerr=[[cc[0] - cc[2]], [cc[3] - cc[0]]],
                fmt="o",
                color=INK,
                capsize=3,
                ms=5,
            )
        ax.set_yticks(range(len(Z4_VARS)))
        ax.set_yticklabels([Z4_LABEL[x] for x in Z4_VARS], fontsize=7.5)
        ax.set_ylim(len(Z4_VARS) - 0.4, -0.6)
        ax.set_title(
            "Z4b: 10-year differences 1990–2020, TFR at start < 3\n"
            f"(country + period FE; n = {z4b.n}, {z4b.countries} countries)",
            fontsize=8.5,
            color=INK,
        )
    ax.axvline(0, color=MUTED, lw=0.6)
    ax.set_xlabel("ΔTFR per 1 SD of each change (95% CI, clustered by country)", fontsize=8)
    _style(ax)
    fig.suptitle("H8d Z4: within-country changes (auxiliary)", fontsize=10, color=INK)
    _foot(fig, f"{SDG_SOURCE}\n{HDR_SOURCE}")
    _save(fig, path)


def fig_z5(kf: pl.DataFrame, k: pl.DataFrame, path: Path) -> None:
    plt = h8._plt()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.6), gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axes[0]
    yrs = kf["year"].to_list()
    ax.plot(
        yrs,
        kf["spend_per_student_10k_krw"].to_list(),
        color=ORANGE,
        marker="o",
        ms=3,
        label="spend per student (10k KRW / month, nominal)",
    )
    ax.set_ylabel(
        "Private tutoring spend per student\n(10k KRW per month, nominal)", fontsize=8, color=ORANGE
    )
    ax.set_xlabel("Survey year", fontsize=8)
    ax.set_xticks(list(range(2007, 2026, 3)))
    _style(ax)
    ax2 = ax.twinx()
    t = kf.drop_nulls(["tfr"])
    ax2.plot(
        t["year"].to_list(), t["tfr"].to_list(), color=BLUE_RAMP[3], marker="s", ms=3, label="TFR"
    )
    ax2.set_ylabel("TFR (children per woman)", fontsize=8, color=BLUE_RAMP[3])
    ax2.tick_params(labelsize=7)
    ax.set_title("Korea 2007–2025: spending per student and TFR", fontsize=8.5, color=INK)
    ax = axes[1]
    bc = k.filter(pl.col("table") == "by_children").pivot(
        on="metric", index=["year", "group"], values="value", aggregate_function=None
    )
    groups = ["자녀 1명", "자녀 2명", "자녀 3명 이상"]
    glab = ["1 child", "2 children", "3+ children"]
    for j, (y, col) in enumerate(((2024, BLUE_RAMP[1]), (2025, ORANGE))):
        vals = [
            float(
                bc.filter((pl.col("year") == y) & (pl.col("group") == g))[
                    "spend_per_student_10k_krw"
                ][0]
            )
            for g in groups
        ]
        xs = [i + (j - 0.5) * 0.38 for i in range(len(groups))]
        ax.bar(xs, vals, width=0.36, color=col, label=str(y))
        for x, v in zip(xs, vals, strict=True):
            ax.annotate(
                f"{v:.1f}",
                (x, v),
                ha="center",
                fontsize=6.5,
                xytext=(0, 2),
                textcoords="offset points",
            )
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(glab, fontsize=8)
    ax.set_ylabel("Spend per student (10k KRW / month)", fontsize=8)
    ax.set_title("By number of children in the household", fontsize=8.5, color=INK)
    ax.legend(fontsize=7, frameon=False)
    _style(ax)
    fig.suptitle("H8d Z5 (descriptive): Korean private tutoring", fontsize=10, color=INK)
    _foot(
        fig,
        "Nominal values; 2020 dip = COVID. Pre-school and repeat students not surveyed.\n"
        f"{KR_SOURCE}",
    )
    _save(fig, path)


def fig_z6(cs: pl.DataFrame, path: Path) -> None:
    plt = h8._plt()
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    f = cs.drop_nulls(["share", "flfp", "tfr"])
    for iso, sh, fl, tfr in f.select("iso3", "share", "flfp", "tfr").rows():
        g = _group_of(iso)
        if g is None:
            ax.scatter([sh], [fl], s=8, color="#d0d0d0", zorder=2)
            continue
        ax.scatter([sh], [fl], s=40 * tfr, color=GROUP_COLOR[g], zorder=3, alpha=0.9)
        ax.annotate(
            f"{iso} {tfr:.2f}",
            (sh, fl),
            fontsize=7,
            color=GROUP_COLOR[g],
            xytext=(4, 2),
            textcoords="offset points",
        )
    for g, col in GROUP_COLOR.items():
        ax.scatter([], [], color=col, s=30, label=g)
    ax.scatter([], [], color="#d0d0d0", s=8, label="other countries")
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax.set_xlabel("Female share of unpaid domestic & care work, F/(F+M)", fontsize=8)
    ax.set_ylabel("Female labour-force participation (%, ILO est.)", fontsize=8)
    ax.set_title(
        "H8d Z6: unpaid-work split x female LFP, latest observation\n"
        "(marker area ∝ TFR; label = TFR)",
        fontsize=9,
        color=INK,
    )
    _style(ax)
    missing = [i for i in FOCUS if i not in f["iso3"].to_list()]
    _foot(
        fig,
        f"Not shown (no 15+/10+/20+/16+/ALL band): {', '.join(missing) or 'none'}.\n{SDG_SOURCE}",
    )
    _save(fig, path)


# ---------------------------------------------------------------- data description
def _yr(f: pl.DataFrame, how: str) -> int:
    s = f["year"]
    return int(s.min() if how == "min" else s.max())  # type: ignore[arg-type]


def describe(
    g: pl.DataFrame, w: pl.DataFrame, sel: pl.DataFrame, hw: pl.DataFrame, panel: pl.DataFrame
) -> None:
    print("== Data ==")
    print(
        f"gender_equity: rows={g.height} series={g.group_by('series').len().sort('series').rows()}"
    )
    print(
        f"  {UNPAID} ALLAREA with F and M: {w.height} country-year-bands, "
        f"{w.select('iso3', 'year').unique().height} country-years, "
        f"{w['iso3'].n_unique()} countries"
    )
    print(
        f"  selected band (priority {AGE_PRIORITY}): {sel.height} country-years, "
        f"{sel['iso3'].n_unique()} countries; bands {sel.group_by('age').len().sort('age').rows()}"
    )
    span = sel.group_by("iso3").agg(
        pl.col("year").min().alias("a"), pl.col("year").max().alias("b")
    )
    print(
        "  countries with 2 obs >= 5 years apart (any band): "
        f"{span.filter(pl.col('b') - pl.col('a') >= 5).height}"
    )
    left = (
        w.select("iso3", "year")
        .unique()
        .join(sel.select("iso3", "year"), on=["iso3", "year"], how="anti")
    )
    print(
        f"  country-years without a priority band (excluded from main): {left.height}, "
        f"countries only so: {sorted(set(left['iso3'].to_list()) - set(sel['iso3'].to_list()))}"
    )
    print(
        "  nature counts in selected rows' series: "
        + str(g.filter(pl.col("series") == UNPAID).group_by("nature").len().sort("nature").rows())
    )
    m = g.filter(pl.col("series") == MANAGERS)
    print(
        f"  {MANAGERS}: rows={m.height} countries={m['iso3'].n_unique()} "
        f"years={_yr(m, 'min')}–{_yr(m, 'max')}"
    )
    for c in ("gii", "pr_f", "lfp_ratio"):
        f = hw.drop_nulls([c])
        print(
            f"hdr_gender {c}: obs={f.height} countries={f['iso3'].n_unique()} "
            f"years={_yr(f, 'min')}–{_yr(f, 'max')}"
        )
    print(f"growth_fertility_panel: rows={panel.height} cols={panel.width}")
    print(
        "  housework-only (SL_DOM_TSPDDC) and care-only (SL_DOM_TSPDCW) series are NOT in "
        "marts/gender_equity -> those two robustness checks cannot be run."
    )


def focus_table(cs: pl.DataFrame, sel: pl.DataFrame, tfr_obs: pl.DataFrame) -> None:
    print("\n== Z6: focus countries (latest observation; descriptive) ==")
    for grp, members in GROUPS.items():
        for iso in members:
            r = cs.filter(pl.col("iso3") == iso)
            if r.height == 0:
                print(f"  {grp:<17} {iso}: no priority band")
                continue
            x = r.row(0, named=True)
            hist = sel.filter(pl.col("iso3") == iso).select("year", "female_share").rows()
            h = " ".join(f"{y}:{s:.3f}" for y, s in hist)
            tf = {
                int(y): float(y)
                for y, v in tfr_obs.filter(pl.col("iso3") == iso).select("year", "tfr").rows()
                if v is not None
            }
            ty = h8.nearest_value(tf, int(x["year"]), WINDOW)
            print(
                f"  {grp:<17} {iso} {x['year']} [{x['age']}] F={x['F']:.2f} M={x['M']:.2f} "
                f"share={x['share']:.3f} flfp={x['flfp']:.1f} TFR={x['tfr']:.2f} "
                f"(TFR year {'n/a' if ty is None else int(ty)})  history {h}"
            )


# ---------------------------------------------------------------- driver
def run(data_dir: Path, fig_dir: Path) -> None:
    panel = pl.read_parquet(data_dir / PANEL_MART)
    g = pl.read_parquet(data_dir / GENDER_MART)
    hw = hdr_wide(pl.read_parquet(data_dir / HDR_MART))
    k = pl.read_parquet(data_dir / KR_MART)
    fig_dir.mkdir(parents=True, exist_ok=True)
    w = unpaid_wide(g)
    sel = select_band(w)
    describe(g, w, sel, hw, panel)
    cs = cross_section(sel, panel, g, hw)

    print(f"\n== Z1 / Z2 / Z3 (main): TFR < {CUT} ==")
    main = run_g(cs, "M")

    print("\n== Z4a: within, first vs last unpaid-work observation (same band, >= 5 years) ==")
    z4a = run_z4a(w, panel, "M")
    print("-- Z4a restricted to TFR at start < 2.5 --")
    run_z4a(w, panel, "M tfr0<2.5", max_tfr0=CUT)
    print("\n== Z4b: HDR components, 10-year long differences ==")
    z4b = run_z4b(z4b_base(panel, hw), "M")

    print()
    kf = run_z5(k, panel)
    focus_table(cs, sel, panel.select("iso3", "year", "tfr"))

    robust = robustness(panel, g, w, hw, cs)
    fig_z1(main, fig_dir / "h8d_z1_z2_unpaid_share.png")
    fig_z3(main, robust, fig_dir / "h8d_z3_alternatives_robustness.png")
    fig_z4(z4a, z4b, fig_dir / "h8d_z4_within.png")
    fig_z5(kf, k, fig_dir / "h8d_z5_korea_tutoring.png")
    fig_z6(cs, fig_dir / "h8d_z6_focus_groups.png")
    exploratory(cs, main, panel, g)
    depends = exploratory_oecd(cs)

    print("\n== Verdict (pre-registered) ==")
    z4c = None if z4a.est is None else z4a.est.coefs["d_share"]
    print(f"Z1 share: {_fmt(main.z1c)}  (n={main.z1.n})")
    print(f"Z2 interaction: {_fmt(main.z2i)}; upper-half slope: {_fmt(main.z2u)}")
    print(f"Z3 hits (predicted direction, CI∌0): {main.hits or 'none'}")
    print(f"reverse: {main.reverse or 'none'}")
    print(f"VERDICT G: {main.verdict} = {VERDICT_JA[main.verdict]}")
    stance = final_stance_g(main.verdict, hits=main.hits, reverse=main.reverse)
    note = z4_note(main.verdict, z4c)
    print(f"PRE-REGISTERED SENTENCE: {stance}{('（' + note + '）') if note else ''}")
    print(f"Z4 consistency note: {note or 'none'} (Z4a Δshare {_fmt(z4c)})")
    flips = [
        (lab, r.verdict) for lab, r in robust if lab in ROBUST_JA and r.verdict != main.verdict
    ]
    oecd = dict(robust).get("OECD members")
    dep = depends if oecd is not None and oecd.verdict == "support" else ()
    framed = framed_stance(
        main.verdict,
        hits=main.hits,
        reverse=main.reverse,
        n=main.z1.n,
        cut=CUT,
        flips=flips,
        depends_on=dep,
    )
    print(f"STANCE (as reported): {framed}")


def robustness(
    panel: pl.DataFrame, g: pl.DataFrame, w: pl.DataFrame, hw: pl.DataFrame, cs: pl.DataFrame
) -> list[tuple[str, GResult]]:
    print(
        "\n== Robustness (pre-registered list: 8 runnable of 10; the nearest-band run is an "
        "added post hoc variant) =="
    )
    small = h8c.small_countries(panel)
    cs10 = cross_section(select_band(w, priority=("10+",)), panel, g, hw)
    csfb = cross_section(select_band(w, fallback=True), panel, g, hw)
    specs: list[tuple[str, pl.DataFrame, dict[str, Any]]] = [
        ("excl JPN", cs.filter(pl.col("iso3") != "JPN"), {}),
        ("excl KOR", cs.filter(pl.col("iso3") != "KOR"), {}),
        ("TFR < 2.1", cs, {"cut": 2.1}),
        ("TFR < 3.0", cs, {"cut": 3.0}),
        ("10+ band only", cs10, {}),
        ("OECD members", cs.filter(pl.col("iso3").is_in(list(OECD_MEMBERS))), {}),
        ("excl pop < 1m", cs.filter(~pl.col("iso3").is_in(small)), {}),
        ("no income/enrolment", cs, {"controls": ("flfp",)}),
        ("+ nearest band (post hoc, ESP etc.)", csfb, {}),
    ]
    out: list[tuple[str, GResult]] = []
    for lab, f, kw in specs:
        print(f"-- {lab} --")
        out.append((lab, run_g(f, f"R {lab}", **kw)))
    print(
        "-- housework only (SL_DOM_TSPDDC) / care only (SL_DOM_TSPDCW): "
        "not run (series not in mart) --"
    )
    print("\n-- Robustness summary --")
    print(
        f"{'spec':<28} {'n':>3} {'Z1 share':<28} {'Z2 inter':<28} {'Z2 upper':<28} hits / verdict"
    )
    for lab, r in out:
        print(
            f"{lab:<28} {r.z1.n:>3} {_fmt(r.z1c):<28} {_fmt(r.z2i):<28} {_fmt(r.z2u):<28} "
            f"{r.hits or '-'} / {r.verdict} rev={r.reverse or '-'}"
        )
    return out


def exploratory(cs: pl.DataFrame, main: GResult, panel: pl.DataFrame, g: pl.DataFrame) -> None:
    print("\n== Exploratory (post hoc, not part of the verdict) ==")
    # E1: bivariate Z1 (no controls) and with female LFP only
    f = main.frame
    for xs in (("share",), ("share", "flfp")):
        fs, _ = h8b.standardize(f, xs)
        e = h8c.ols_hc1(fs, "tfr", xs, label="E1")
        print(f"E1 tfr ~ {' + '.join(xs)} on the Z1 sample: n={e.n} share {_fmt(e.coefs['share'])}")
    # E2: male unpaid-work level (M, % of day) instead of the share — Japan/Korea male values are
    # low by definition, so this mostly checks whether the share result is driven by men's time.
    for c in ("M", "F"):
        xe = (c, *CONTROLS)
        fs, _ = h8b.standardize(f, xe)
        e = h8c.ols_hc1(fs, "tfr", xe, label="E2")
        print(f"E2 Z1 with {c} (unpaid %, level) instead of share: n={e.n} {c} {_fmt(e.coefs[c])}")
    # E3: TFR < 2.5 but restricted to high-income (WB classification at fetch time)
    hi = panel.select("iso3", "income_group").unique("iso3")
    fh = f.join(hi, on="iso3", how="left").filter(pl.col("income_group") == "High income")
    if fh.height >= 10:
        fs, _ = h8b.standardize(fh, Z1_VARS)
        e = h8c.ols_hc1(fs, "tfr", Z1_VARS, label="E3")
        r = h8b.spearman(fh["share"].to_list(), fh["tfr"].to_list())
        print(
            f"E3 high-income only: n={e.n} share {_fmt(e.coefs['share'])}; Spearman "
            f"rho={r[0]:+.3f} p={r[1]:.3f}"
        )
    # E5: ICATUS-adjusted (Nature=CA) vs country data (C) in the Z1 sample
    nat = (
        g.filter(
            (pl.col("series") == UNPAID)
            & (pl.col("sex") == "F")
            & (pl.col("location") == "ALLAREA")
        )
        .select("iso3", "year", "age", "nature")
        .unique(["iso3", "year", "age"], keep="first")
    )
    fn = f.join(nat, on=["iso3", "year", "age"], how="left")
    counts = fn.group_by("nature").len().sort("nature").rows()
    ca = sorted(fn.filter(pl.col("nature") == "CA")["iso3"].to_list())
    print(f"E5 Z1 sample by Nature: {counts}; CA countries {ca}")
    for nv in ("C", "CA"):
        sub = fn.filter(pl.col("nature") == nv)
        if sub.height >= len(Z1_VARS) + 3:
            fs, _ = h8b.standardize(sub, Z1_VARS)
            e = h8c.ols_hc1(fs, "tfr", Z1_VARS, label="E5")
            print(f"E5 Nature={nv}: n={e.n} share {_fmt(e.coefs['share'])}")
        else:
            rr = (
                h8b.spearman(sub["share"].to_list(), sub["tfr"].to_list())
                if sub.height >= 3
                else None
            )
            print(
                f"E5 Nature={nv}: n={sub.height} (too few for Z1)"
                + ("" if rr is None else f"; Spearman rho={rr[0]:+.3f} p={rr[1]:.3f}")
            )
    # E6: observation year >= 2010 only
    r6 = run_g(cs.filter(pl.col("year") >= 2010), "E6 obs year >= 2010", verbose=False)
    _brief("E6 obs year >= 2010", r6)


def _brief(lab: str, r: GResult) -> None:
    print(
        f"{lab:<34} n={r.z1.n:>2} Z1 {_fmt(r.z1c)}  Z2 inter {_fmt(r.z2i)}  upper {_fmt(r.z2u)}"
        f"  -> {r.verdict}"
    )


def exploratory_oecd(cs: pl.DataFrame) -> tuple[str, ...]:
    """E4: the OECD robustness run gives 'support'. Does it rest on Japan / Korea (or Italy)?"""
    oe = cs.filter(pl.col("iso3").is_in(list(OECD_MEMBERS)))
    print(
        "E4 OECD sample (TFR < 2.5): "
        + " ".join(
            f"{i}:{s:.2f}/{t:.2f}"
            for i, s, t in oe.filter(pl.col("tfr") < CUT)
            .drop_nulls(["tfr", *Z1_VARS])
            .select("iso3", "share", "tfr")
            .rows()
        )
        + "  (iso3:share/TFR)"
    )
    single: list[str] = []
    for lab, drop in (
        ("E4 OECD excl JPN", ("JPN",)),
        ("E4 OECD excl KOR", ("KOR",)),
        ("E4 OECD excl JPN KOR", ("JPN", "KOR")),
        ("E4 OECD excl JPN KOR ITA", ("JPN", "KOR", "ITA")),
    ):
        r = run_g(oe.filter(~pl.col("iso3").is_in(list(drop))), lab, verbose=False)
        _brief(lab, r)
        if len(drop) == 1 and r.verdict != "support":
            single.append(drop[0])
    return tuple(single)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
