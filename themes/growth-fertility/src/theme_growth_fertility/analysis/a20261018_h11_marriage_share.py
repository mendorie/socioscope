"""H11（事後追加）: 日本の出生率低下のうち、結婚の減少（有配偶割合の低下）で説明できるのは何割か。

事前登録: design/themes/growth-fertility.md「### H11」（2026-10-18、part6 の最終的な読みの確認）。
検定 J1・J2・J3、判定規則、最終スタンスの文型、頑健性、言えないことは追加データを見る前に design に
固定した。H8〜H10 の判定は変えない。

  J1 日本の分解（主）: 国勢調査年 1970/1980/1990/2000/2010/2015/2020。女性 15–49 の 5 歳階級ごとに
     m_a = 有配偶割合（T06-24 シート (2)）、f_a = T04-09 の各歳 ASFR を 5 歳階級に合算した値。
     Cm = Σ m_a f_a / Σ f_a、TFR = Σ f_a（= 各歳の和）。Δln TFR = Δln Cm + Δln(TFR/Cm)、
     s_m = Δln Cm / Δln TFR（1980→2020 主、1970→2020、1990→2020、区間 1980→2000・2000→2020）。
     補助: 夫婦の完結出生児数（T04-23）。
  J2 都道府県パネル: 1990/2010/2015/2020 の県 × 年で Δtfr ~ Δnever_married_m30_34（主）、
     Δnever_married_f25_29、Δnever_married_at_50（2000–2020）。県 FE ＋ 年 FE、県クラスタ SE、
     標準化係数。予測符号は負。
  J3 国際比較: 19 か国の 5 年差分（1990–2025）で Δtfr ~ Δ粗婚姻率 + Δ女性初婚年齢（国＋期間 FE、
     国クラスタ SE）を SF2.4 婚外出生割合（最新年）の 低群 < 25% / 中群 / 高群 ≥ 40% で推定。
     予測: 低群で婚姻率の係数が正かつ CI∌0、高群で CI∋0。
  判定: 主経路 = s_m(1980→2020) ≥ 2/3 かつ J2 主仕様が負で CI∌0。両方 = 1/3 ≤ s_m < 2/3。
     夫婦の出生数が主 = s_m < 1/3。

運用の細則（design に書かれていない点。stdout の冒頭に要点を出す）。mart の構造（年・国・群の
構成）は見た後に書いたが、推定値を出す前に固定した（commit 履歴では確かめられない）。
  - J1 の f_a は T04-09 の各歳 15–49 の和（5 歳階級）。35 歳が 1 つでも欠ける年は計算しない。
    m_a は % を 1/100 にする。有配偶は法律婚（国勢調査の届出によらない事実上の配偶を含む）。
  - s_m ≥ 2/3 だが J2 主仕様が不成立のときは design に規定が無い。この場合は「主経路（J2 で確認
    できず）」と書き、文型の X・Y は J1 から埋める。s_m が 1 を超える（夫婦の側の指標 TFR/Cm が
    上がった）ときも文型をそのまま数で埋め、限定は framed_stance に書く。
  - J2 の Δ は県ごとの連続する調査年の差（1990→2010、2010→2015、2015→2020。50 歳時未婚は
    2000→2005 … 2015→2020）。県 FE は差分の上の県固有トレンド、年 FE は区間の終点年。都道府県
    TFR は T12-33 の各年値を調査年に厳密一致で使う。50 歳時未婚は女性を主、男性を併記。
  - J3 の TFR は WDI（growth_fertility_panel）、婚姻率・初婚年齢は H10 の `country_panel`
    （国ごとに出典 1 つ）。端点は ±2 年の最近傍（H8 `long_diff_nearest`）。群ごとの推定は
    n ≥ 10 かつ 4 か国以上（H10 の 4 か国の頑健性と同じ下限。低群は 4 か国しかない。4 クラスタの
    SE は信頼できない）。閾値の頑健性 20% / 30% は低群の上限だけを替える（高群 ≥ 40% は固定）。
  - J3 の「整合」= 低群の婚姻率係数が正で CI∌0、かつ高群の CI が 0 を含む。整合しないとき、最終
    スタンスの第 2 文（北欧では切り離されている）は付けず、確かめられなかったと書く。

決定的スクリプト。乱数不使用。補完なし（listwise）。識別戦略なし（J1 は恒等式の分解、J2・J3 は
固定効果つきの関連）。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋関数（asfr_5yr, cm_index, cm_standard, decompose, verdict, final_stance, framed_stance,
bom_group, j3_consistent, first_diff）は tests/test_analysis_h11.py で検証。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from theme_growth_fertility.analysis import a20261018_h10_family_formation as h10
from theme_growth_fertility.analysis.a20261004_h1_income_tfr import (
    BLUE_RAMP,
    INK,
    MUTED,
    ORANGE,
    _style,
)
from theme_growth_fertility.analysis.a20261017_h8_mechanisms import long_diff_nearest

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
BOM_MART = Path("marts") / "oecd_births_outside_marriage.parquet"
SURVEY_MART = Path("marts") / "jp_fertility_survey.parquet"
WDI_MART = Path("marts") / "growth_fertility_panel.parquet"

# ---------------------------------------------------------------- pre-registered (design H11)
J1_YEARS = (1970, 1980, 1990, 2000, 2010, 2015, 2020)
AGES = ("15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49")
AGES_2039 = ("20-24", "25-29", "30-34", "35-39")
J1_MAIN = (1980, 2020)
J1_WINDOWS = ((1980, 2020), (1970, 2020), (1990, 2020), (1980, 2000), (2000, 2020))
S_HIGH, S_LOW = 2 / 3, 1 / 3
J2_YEARS = (1990, 2010, 2015, 2020)
J2_NM50_YEARS = (2000, 2005, 2010, 2015, 2020)
J3_WIDTH, J3_ALT_WIDTH, J3_START, J3_END = 5, 10, 1990, 2025
BOM_LOW, BOM_HIGH = 25.0, 40.0
BOM_LOW_ALT = (20.0, 30.0)

# ---------------------------------------------------------------- operational (fixed pre-run)
J3_WINDOW, J3_MIN_N, J3_MIN_G = 2, 10, 4
J2_MIN_N, J2_MIN_G = 20, 20
VERDICT_JA = {
    "main": "結婚の減少が主経路",
    "main_unconfirmed": "事前の『主経路』の条件は満たさない（J1 のみ成立、J2 不成立）",
    "both": "結婚と夫婦の出生数の両方",
    "couple": "夫婦の出生数の低下が主",
}

Coef = h10.Coef
Fit = h10.Fit


# ---------------------------------------------------------------- pure helpers (tested)
def asfr_5yr(asfr: Mapping[int, float], ages: Sequence[str] = AGES) -> dict[str, float] | None:
    """Sum single-year ASFRs (age -> births per woman) into 5-year groups 'lo-hi'.

    None if any single year is missing (no imputation)."""
    out: dict[str, float] = {}
    for g in ages:
        lo, hi = (int(x) for x in g.split("-"))
        vals = [asfr.get(a) for a in range(lo, hi + 1)]
        if any(v is None for v in vals):
            return None
        out[g] = float(sum(v for v in vals if v is not None))
    return out


def cm_index(m: Mapping[str, float], f: Mapping[str, float], ages: Sequence[str] = AGES) -> float:
    """Marriage index as fixed in design H11: Cm = Σ m_a f_a / Σ f_a (m_a in 0–1)."""
    den = sum(f[a] for a in ages)
    if den <= 0:
        raise ValueError("Σ f_a must be positive")
    return sum(m[a] * f[a] for a in ages) / den


def cm_standard(
    m: Mapping[str, float], f: Mapping[str, float], ages: Sequence[str] = AGES
) -> float:
    """Bongaarts' original Cm = TFR / TM with TM = Σ f_a / m_a (marital fertility; exploratory)."""
    tm = sum(f[a] / m[a] for a in ages)
    return sum(f[a] for a in ages) / tm


@dataclass(frozen=True)
class J1Decomp:
    y0: int
    y1: int
    tfr0: float
    tfr1: float
    cm0: float
    cm1: float

    @property
    def d_ln_tfr(self) -> float:
        return math.log(self.tfr1 / self.tfr0)

    @property
    def d_ln_cm(self) -> float:
        return math.log(self.cm1 / self.cm0)

    @property
    def d_ln_rest(self) -> float:
        """Δ ln(TFR / Cm): the part not due to the married share."""
        return math.log((self.tfr1 / self.cm1) / (self.tfr0 / self.cm0))

    @property
    def s_m(self) -> float:
        return self.d_ln_cm / self.d_ln_tfr if self.d_ln_tfr != 0 else float("nan")


def decompose(y0: int, y1: int, tfr: Mapping[int, float], cm: Mapping[int, float]) -> J1Decomp:
    return J1Decomp(y0, y1, tfr[y0], tfr[y1], cm[y0], cm[y1])


def verdict(s_m: float, j2_pass: bool) -> str:
    """Pre-registered rule (design H11 判定). 'main_unconfirmed' is the operational gap."""
    if s_m >= S_HIGH:
        return "main" if j2_pass else "main_unconfirmed"
    if s_m >= S_LOW:
        return "both"
    return "couple"


def wari(x: float) -> str:
    return f"{round(x * 10)}"


def final_stance(y0: int, s_m: float, j3_ok: bool, j3_reversed: bool = False) -> str:
    """The pre-registered sentence (design H11 最終スタンスの文型), filled mechanically.

    Kept as a record; the report's lead sentence is `framed_stance`."""
    head = (
        f"日本の出生率低下（{y0}→2020）の {wari(s_m)}"
        " 割は結婚の減少（有配偶割合の低下）で説明でき、"
        f"結婚した夫婦の出生数の低下は {wari(1 - s_m)} 割である。"
    )
    if j3_ok:
        return head + "結婚と出生の結びつきは婚外出生の少ない国に固有で、北欧では切り離されている。"
    if j3_reversed:
        return (
            head + "結婚と出生の結びつきが婚外出生の少ない国に固有だという予測に対し、"
            "国際比較では逆の結果（婚外出生の多い国でも婚姻率と出生率が連動）だった。"
        )
    return (
        head + "結婚と出生の結びつきが婚外出生の少ない国に固有かどうかは、"
        "国際比較では確かめられなかった。"
    )


def wari_approx(x: float) -> str:
    """'4 割強' / '4 割弱' / '4 割' (within ±0.5 percentage of a whole 割 -> no suffix)."""
    r = round(x * 10)
    d = x * 10 - r
    return f"{r} 割" + ("強" if d > 0.05 else "弱" if d < -0.05 else "")


def period_phrase(s_m: float) -> str:
    return "ほぼ全部" if s_m >= 0.9 else f"約 {wari(s_m)} 割"


def framed_stance(
    *,
    main: J1Decomp,
    code: str,
    segments: Sequence[J1Decomp],
    std_s_m: float,
    completed: tuple[int, float, int, float] | None,
    j2_main: Coef | None,
    j3_ok: bool,
    robust_changes: Sequence[str],
    j3_low: Coef | None = None,
    j3_high: Coef | None = None,
    s_m_range: tuple[float, float] | None = None,
    cohort: tuple[int, int, float] | None = None,
) -> str:
    """Reporting sentence (the report's lead): period and cohort shares side by side, then the
    pre-registered verdict and qualifications. The mechanical pattern is `final_stance`."""
    rng = f"、起点で {s_m_range[0]:.2f}〜{s_m_range[1]:.2f}" if s_m_range else ""
    lead = (
        f"期間の分解では {main.y0}→2020 年の低下の{period_phrase(main.s_m)}（s_m = "
        f"{main.s_m:.2f}{rng}）"
    )
    if cohort is not None:
        c0, c1, sh = cohort
        lead += f"、世代の分解（探索的）では {wari_approx(sh)}（{c0}→{c1} 年生まれで {sh:.0%}）"
    lead += "が結婚の減少（有配偶割合の低下）で説明できる。"
    parts = [lead]
    if completed is not None:
        y0, v0, y1, v1 = completed
        parts.append(
            f"夫婦の完結出生児数（結婚持続 15–19 年）も {v0:.2f}（{y0} 年調査）→ {v1:.2f}"
            f"（{y1} 年調査）に下がった。"
        )
    if main.s_m > 1:
        parts.append(
            "期間の s_m が 1 を超えるのは出産年齢の後ろ倒し（テンポ）による見かけの可能性が高いが、"
            "根拠は世代の分解・完結出生児数との対比で、Bongaarts–Feeney 等の直接のテンポ調整は"
            "していない。"
        )
    parts.append(f"事前の判定は「{VERDICT_JA[code]}」。")
    if code == "main_unconfirmed":
        parts.append(
            f"J1 の s_m（{main.s_m:.2f}）は事前の「主経路」の帯（≥ 2/3）にあるが、"
            "AND 条件の J2 が成り立たない。"
        )
    parts.append(
        f"{main.y0}→2020 年に TFR は {main.tfr0:.2f} → {main.tfr1:.2f}"
        f"（Δln {main.d_ln_tfr:+.3f}）、"
        f"結婚指数 Cm は {main.cm0:.3f} → {main.cm1:.3f}（Δln {main.d_ln_cm:+.3f}）、"
        f"TFR/Cm は Δln {main.d_ln_rest:+.3f}。"
    )
    seg = "、".join(f"{d.y0}→{d.y1} は {d.s_m:.2f}" for d in segments)
    if seg:
        parts.append(f"区間別の s_m は {seg}。")
    parts.append(
        f"夫婦の出生率を有配偶出生率 f_a/m_a の和で測る Bongaarts の原定義（探索的）では s_m = "
        f"{std_s_m:.2f}。"
    )
    if j3_low is not None and j3_high is not None:
        rev = h10.passes(j3_high, 1)
        edge = "。CI の下端は 0 の境界上" if abs(j3_low[2]) < 0.01 else ""
        parts.append(
            f"国パネル（J3）は{'予測と逆の結果で' if rev else ''}"
            "、婚姻率の係数は婚外出生の多い国で "
            f"{j3_high[0]:+.3f} [{j3_high[2]:+.3f}, {j3_high[3]:+.3f}]"
            f"{'（CI∌0）' if rev else '（CI∋0）'}、少ない国で {j3_low[0]:+.3f} "
            f"[{j3_low[2]:+.3f}, {j3_low[3]:+.3f}"
            f"]（4 か国で検出力は低い{edge}）。"
        )
    if j2_main is not None:
        parts.append(
            f"都道府県パネル（J2 主仕様）の Δ男性 30–34 歳未婚割合の係数は 1 SD あたり "
            f"{j2_main[0]:+.3f} [{j2_main[2]:+.3f}, {j2_main[3]:+.3f}]。"
        )
    parts.append(
        "頑健性の仕様では判定が変わるものがある（" + "、".join(robust_changes) + "）。"
        if robust_changes
        else "事前の頑健性の仕様では判定は変わらない。"
    )
    parts.append(
        "分解は恒等式であって因果ではなく（有配偶割合と出生率は同時に決まる）、都道府県・国の関連は"
        "集計の関連である。なぜ結婚が減ったかには答えない。"
    )
    return "".join(parts)


def bom_group(share: float, low: float = BOM_LOW, high: float = BOM_HIGH) -> str:
    if share < low:
        return "low"
    if share >= high:
        return "high"
    return "mid"


def j3_consistent(low: Coef | None, high: Coef | None) -> bool:
    """Low group: marriage-rate coefficient > 0 with CI∌0; high group: CI contains 0."""
    if low is None or high is None:
        return False
    return h10.passes(low, 1) and high[2] <= 0 <= high[3]


def first_diff(frame: pl.DataFrame, unit: str, time: str, cols: Sequence[str]) -> pl.DataFrame:
    """Differences between consecutive `time` rows within `unit` (sorted). The row keeps the end
    time; d_<c> is null if either end is null."""
    f = frame.sort(unit, time)
    return (
        f.with_columns([(pl.col(c) - pl.col(c).shift(1).over(unit)).alias(f"d_{c}") for c in cols])
        .with_columns(pl.col(time).shift(1).over(unit).alias("t0"))
        .filter(pl.col("t0").is_not_null())
    )


# ---------------------------------------------------------------- loading
def load(data_dir: Path) -> dict[str, pl.DataFrame]:
    d = h10.load(data_dir)
    d["bom"] = pl.read_parquet(data_dir / BOM_MART)
    d["survey"] = pl.read_parquet(data_dir / SURVEY_MART)
    d["wdi"] = pl.read_parquet(data_dir / WDI_MART)
    return d


def asfr_by_year(jp_order: pl.DataFrame) -> dict[int, dict[int, float]]:
    f = jp_order.filter(pl.col("metric") == "asfr")
    out: dict[int, dict[int, float]] = {}
    for y, g, v in f.select("year", "group", "value").iter_rows():
        out.setdefault(int(y), {})[int(str(g).split()[1])] = float(v)
    return out


def share_by_year(mar: pl.DataFrame, metric: str, sex: str = "F") -> dict[int, dict[str, float]]:
    f = mar.filter((pl.col("metric") == metric) & (pl.col("sex") == sex))
    out: dict[int, dict[str, float]] = {}
    for y, a, v in f.select("year", "age_class", "value").iter_rows():
        out.setdefault(int(y), {})[str(a)] = float(v) / 100.0
    return out


@dataclass(frozen=True)
class J1Year:
    year: int
    tfr: float
    f: dict[str, float]
    m: dict[str, float]  # married / all women
    m_alt: dict[str, float]  # married / (never married + married)


def j1_years(d: Mapping[str, pl.DataFrame]) -> dict[int, J1Year]:
    asfr = asfr_by_year(d["jp_order"])
    mar = share_by_year(d["mar"], "married_share")
    nev = share_by_year(d["mar"], "never_married_share")
    out: dict[int, J1Year] = {}
    for y in J1_YEARS:
        f = asfr_5yr(asfr.get(y, {}))
        if f is None or y not in mar or any(a not in mar[y] for a in AGES):
            continue
        m = {a: mar[y][a] for a in AGES}
        m_alt = {a: mar[y][a] / (mar[y][a] + nev[y][a]) for a in AGES}
        tfr = sum(asfr[y][a] for a in range(15, 50))
        out[y] = J1Year(y, tfr, f, m, m_alt)
    return out


def completed_near(survey: pl.DataFrame, y0: int, y1: int) -> tuple[int, float, int, float] | None:
    f = survey.filter(pl.col("metric") == "completed_fertility").select("survey_year", "value")
    obs = {int(y): float(v) for y, v in f.iter_rows()}
    if not obs:
        return None

    def near(t: int) -> int:
        return min(obs, key=lambda y: (abs(y - t), y))

    a, b = near(y0), near(y1)
    return a, obs[a], b, obs[b]


# ---------------------------------------------------------------- J2
def pref_frame(pref: pl.DataFrame, years: Sequence[int]) -> pl.DataFrame:
    p = pref.filter((pl.col("pref_code") != "00") & pl.col("year").is_in(list(years)))

    def get(metric: str, sex: str, name: str) -> pl.DataFrame:
        return p.filter((pl.col("metric") == metric) & (pl.col("sex") == sex)).select(
            pl.col("pref_code").alias("unit"), "year", pl.col("value").alias(name)
        )

    parts = [
        get("tfr", "T", "tfr"),
        get("never_married_m30_34", "M", "nm_m3034"),
        get("never_married_f25_29", "F", "nm_f2529"),
        get("never_married_at_50", "F", "nm50_f"),
        get("never_married_at_50", "M", "nm50_m"),
    ]
    keys = pl.DataFrame(
        [(u, y) for u in sorted(set(p["pref_code"].to_list())) for y in years],
        schema={"unit": pl.Utf8, "year": pl.Int64},
        orient="row",
    )
    out = keys
    for q in parts:
        out = out.join(q, on=["unit", "year"], how="left")
    return out.with_columns(pl.col("tfr").log().alias("ln_tfr")).sort("unit", "year")


J2_COLS = ("tfr", "ln_tfr", "nm_m3034", "nm_f2529", "nm50_f", "nm50_m")


def run_j2(frame: pl.DataFrame, y: str, x: str) -> Fit | None:
    fd = first_diff(frame, "unit", "year", J2_COLS)
    f = h10.fit_std(
        fd, f"d_{y}", [f"d_{x}"], unit="unit", time="year", min_n=J2_MIN_N, min_g=J2_MIN_G
    )
    if f is None:
        return None
    return Fit({x: f.coefs[f"d_{x}"]}, f.n, f.groups, f.times)


# ---------------------------------------------------------------- J3
def latest_bom(bom: pl.DataFrame) -> dict[str, tuple[int, float]]:
    f = bom.filter(pl.col("metric") == "births_outside_marriage_pct").sort("iso3", "year")
    out: dict[str, tuple[int, float]] = {}
    for iso, y, v in f.select("iso3", "year", "value").iter_rows():
        out[str(iso)] = (int(y), float(v))
    return out


def j3_panel(d: Mapping[str, pl.DataFrame]) -> pl.DataFrame:
    panel, _ = h10.country_panel(d)
    isos = sorted(set(panel["iso3"].to_list()))
    tfr = (
        d["wdi"]
        .filter(pl.col("iso3").is_in(isos))
        .select("iso3", pl.col("year").cast(pl.Int64), "tfr")
        .drop_nulls()
    )
    return (
        panel.select("iso3", "year", "cmr", "fagem")
        .join(tfr, on=["iso3", "year"], how="full", coalesce=True)
        .sort("iso3", "year")
    )


J3_COLS = ("tfr", "cmr", "fagem")


def j3_frame(panel: pl.DataFrame, width: int) -> pl.DataFrame:
    return long_diff_nearest(
        panel, J3_COLS, width=width, start=J3_START, end=J3_END, window=J3_WINDOW
    )


def run_j3(ld: pl.DataFrame, isos: Sequence[str] | None = None) -> Fit | None:
    f = ld if isos is None else ld.filter(pl.col("iso3").is_in(list(isos)))
    fit = h10.fit_std(
        f, "d_tfr", ["d_cmr", "d_fagem"], unit="iso3", time="period",
        min_n=J3_MIN_N, min_g=J3_MIN_G,
    )  # fmt: skip
    if fit is None:
        return None
    return Fit({k[2:]: v for k, v in fit.coefs.items()}, fit.n, fit.groups, fit.times)


def groups_of(
    bom: Mapping[str, tuple[int, float]], isos: Sequence[str], low: float
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"low": [], "mid": [], "high": []}
    for iso in isos:
        if iso in bom:
            out[bom_group(bom[iso][1], low=low)].append(iso)
    return out


@dataclass(frozen=True)
class CohortPoint:
    cohort: int
    ctfr: float  # cumulative fertility at age 49 (T04-11)
    ever: float  # 1 − never-married share at 50 (census year cohort + 50, T06-23)


def cohort_share(c0: CohortPoint, c1: CohortPoint) -> float:
    """Share of Δln completed cohort fertility due to Δln ever-married share (identity)."""
    return math.log(c1.ever / c0.ever) / math.log(c1.ctfr / c0.ctfr)


def cohort_points(d: Mapping[str, pl.DataFrame]) -> dict[int, CohortPoint]:
    nm = {
        int(y): float(v)
        for y, v in d["mar"]
        .filter((pl.col("metric") == "never_married_at_50") & (pl.col("sex") == "F"))
        .select("year", "value")
        .iter_rows()
    }
    ct = {
        int(c): float(v)
        for c, v in d["jp_order"]
        .filter((pl.col("metric") == "cohort_cum_fertility") & (pl.col("group") == "age 49"))
        .select("cohort", "value")
        .iter_rows()
    }
    return {
        y - 50: CohortPoint(y - 50, ct[y - 50], 1 - nm[y] / 100)
        for y in sorted(nm)
        if (y - 50) in ct
    }


def cohort_pairs(d: Mapping[str, pl.DataFrame]) -> list[tuple[CohortPoint, CohortPoint]]:
    cp = cohort_points(d)
    last = max(cp)
    return [(cp[c], cp[last]) for c in sorted(cp) if c < last]


NORDIC = ("DNK", "FIN", "NOR", "SWE")


def explore(pf: pl.DataFrame, ld5: pl.DataFrame) -> dict[str, Fit | None]:
    """Exploratory fits outside the verdict."""
    import statsmodels.formula.api as smf

    out: dict[str, Fit | None] = {}
    # E4: J2 in levels (tfr ~ nm, prefecture + year FE), as in H10 C
    for x in ("nm_m3034", "nm_f2529"):
        out[f"E4 J2 levels tfr ~ {x}, pref + year FE"] = h10.fit_std(
            pf, "tfr", [x], unit="unit", time="year", min_n=J2_MIN_N, min_g=J2_MIN_G
        )
    # E5: J2 first differences with year FE only (no prefecture trend)
    fd = first_diff(pf, "unit", "year", J2_COLS).drop_nulls(["d_tfr", "d_nm_m3034"])
    sd = float(fd["d_nm_m3034"].std() or 1.0)  # type: ignore[arg-type]
    pdf = fd.with_columns((pl.col("d_nm_m3034") / sd).alias("x")).sort("unit", "year").to_pandas()
    r = smf.ols("d_tfr ~ x + C(year)", data=pdf).fit(
        cov_type="cluster", cov_kwds={"groups": pdf["unit"]}
    )
    ci = r.conf_int()
    c = (float(r.params["x"]), float(r.bse["x"]), float(ci.loc["x", 0]), float(ci.loc["x", 1]))
    years = tuple(sorted(int(y) for y in set(fd["year"].to_list())))
    out["E5 J2 first differences, year FE only"] = Fit(
        {"nm_m3034": c}, int(r.nobs), fd["unit"].n_unique(), years
    )
    # E6: J3 Nordic 4 only
    out["E6 J3 Nordic 4"] = run_j3(ld5, NORDIC)
    return out


# ---------------------------------------------------------------- compute
@dataclass(frozen=True)
class H11Result:
    years: dict[int, J1Year]
    cm: dict[str, dict[int, float]]  # variant -> year -> Cm
    tfr: dict[int, float]
    j1: dict[str, list[J1Decomp]]  # variant -> decomps over J1_WINDOWS
    completed: tuple[int, float, int, float] | None
    j2: dict[str, Fit | None]
    j3: dict[str, dict[str, Fit | None]]  # spec -> group -> fit
    j3_groups: dict[str, dict[str, list[str]]]
    bom: dict[str, tuple[int, float]]
    code: str
    j2_pass: bool
    j3_ok: bool
    robust: dict[str, tuple[str, bool]]  # spec -> (verdict, j3_ok)
    final: str
    framed: str
    cohort_pairs: list[tuple[CohortPoint, CohortPoint]]
    explore: dict[str, Fit | None]


def compute(d: Mapping[str, pl.DataFrame]) -> H11Result:
    ys = j1_years(d)
    tfr = {y: v.tfr for y, v in ys.items()}
    cm = {
        "main": {y: cm_index(v.m, v.f) for y, v in ys.items()},
        "ages 20-39": {y: cm_index(v.m, v.f, AGES_2039) for y, v in ys.items()},
        "denominator never+married": {y: cm_index(v.m_alt, v.f) for y, v in ys.items()},
        "standard Bongaarts (exploratory)": {y: cm_standard(v.m, v.f) for y, v in ys.items()},
    }
    j1 = {
        k: [decompose(a, b, tfr, c) for a, b in J1_WINDOWS if a in c and b in c]
        for k, c in cm.items()
    }
    main = j1["main"][0]
    assert (main.y0, main.y1) == J1_MAIN
    completed = completed_near(d["survey"], *J1_MAIN)

    pf = pref_frame(d["pref"], J2_YEARS)
    p50 = pref_frame(d["pref"], J2_NM50_YEARS)
    pf_no90 = pref_frame(d["pref"], J2_YEARS[1:])
    j2: dict[str, Fit | None] = {
        "main nm_m3034": run_j2(pf, "tfr", "nm_m3034"),
        "nm_f2529": run_j2(pf, "tfr", "nm_f2529"),
        "nm50_f (2000-2020)": run_j2(p50, "tfr", "nm50_f"),
        "nm50_m (2000-2020)": run_j2(p50, "tfr", "nm50_m"),
        "robust ln TFR": run_j2(pf, "ln_tfr", "nm_m3034"),
        "robust drop 1990": run_j2(pf_no90, "tfr", "nm_m3034"),
    }

    def j2_ok(f: Fit | None) -> bool:
        return f is not None and h10.passes(f.coefs.get("nm_m3034"), -1)

    j2_pass = j2_ok(j2["main nm_m3034"])

    panel = j3_panel(d)
    bom = latest_bom(d["bom"])
    isos = sorted(set(panel["iso3"].to_list()))
    ld5, ld10 = j3_frame(panel, J3_WIDTH), j3_frame(panel, J3_ALT_WIDTH)
    j3: dict[str, dict[str, Fit | None]] = {}
    j3_groups: dict[str, dict[str, list[str]]] = {}
    for spec, ld, low in (
        ("main (5y, <25%)", ld5, BOM_LOW),
        ("low < 20%", ld5, BOM_LOW_ALT[0]),
        ("low < 30%", ld5, BOM_LOW_ALT[1]),
        ("10-year differences", ld10, BOM_LOW),
    ):
        g = groups_of(bom, isos, low)
        j3_groups[spec] = g
        j3[spec] = {k: run_j3(ld, v) for k, v in g.items()}
        j3[spec]["all"] = run_j3(ld)

    def ok3(spec: str) -> bool:
        r = j3[spec]
        return j3_consistent(
            r["low"].coefs.get("cmr") if r["low"] else None,
            r["high"].coefs.get("cmr") if r["high"] else None,
        )

    j3_ok = ok3("main (5y, <25%)")
    code = verdict(main.s_m, j2_pass)

    robust: dict[str, tuple[str, bool]] = {}
    for k, ds in j1.items():
        if "exploratory" in k:
            continue
        for dc in ds:
            if dc.y1 != 2020 or dc.y0 not in (1970, 1980, 1990) or (k == "main" and dc.y0 == 1980):
                continue
            robust[f"J1 {k} {dc.y0}->2020"] = (verdict(dc.s_m, j2_pass), j3_ok)
    for k in ("robust ln TFR", "robust drop 1990"):
        f = j2[k]
        ok = f is not None and h10.passes(f.coefs.get("nm_m3034"), -1)
        robust[f"J2 {k}"] = (verdict(main.s_m, ok), j3_ok)
    for k in ("low < 20%", "low < 30%", "10-year differences"):
        robust[f"J3 {k}"] = (code, ok3(k))
    changes = [
        f"{k} で「{VERDICT_JA[v]}」{'' if j == j3_ok else '・J3 ' + ('整合' if j else '不整合')}"
        for k, (v, j) in robust.items()
        if (v, j) != (code, j3_ok)
    ]
    j2m = j2["main nm_m3034"]
    j3m = j3["main (5y, <25%)"]
    j3_rev = j3m["high"] is not None and h10.passes(j3m["high"].coefs.get("cmr"), 1)
    final = final_stance(main.y0, main.s_m, j3_ok, j3_rev)
    starts = [x.s_m for x in j1["main"] if x.y1 == 2020 and x.y0 in (1970, 1980, 1990)]
    cps = {c0.cohort: (c0, c1) for c0, c1 in cohort_pairs(d)}
    coh = (1950, cps[1950][1].cohort, cohort_share(*cps[1950])) if 1950 in cps else None
    framed = framed_stance(
        main=main,
        code=code,
        segments=[x for x in j1["main"] if (x.y0, x.y1) in ((1980, 2000), (2000, 2020))],
        std_s_m=j1["standard Bongaarts (exploratory)"][0].s_m,
        completed=completed,
        j2_main=j2m.coefs["nm_m3034"] if j2m else None,
        j3_ok=j3_ok,
        robust_changes=changes,
        j3_low=j3m["low"].coefs["cmr"] if j3m["low"] else None,
        j3_high=j3m["high"].coefs["cmr"] if j3m["high"] else None,
        s_m_range=(min(starts), max(starts)),
        cohort=coh,
    )
    return H11Result(
        ys, cm, tfr, j1, completed, j2, j3, j3_groups, bom, code, j2_pass, j3_ok, robust,
        final, framed, cohort_pairs(d), explore(pf, ld5),
    )  # fmt: skip


# ---------------------------------------------------------------- printing
def _f(c: Coef | None) -> str:
    return h10._f(c)


def section_data(res: H11Result, d: Mapping[str, pl.DataFrame]) -> None:
    print("\n== Data ==")
    for k in ("mar", "jp_order", "survey", "pref", "oecd", "eu", "bom", "wdi"):
        print(f"  {k}: {d[k].height} rows")
    print(f"  J1 census years with full m_a and f_a: {sorted(res.years)}")
    print("  J1 married share m_a (women, %) and f_a (5-year sum of single-year ASFR):")
    for y, v in sorted(res.years.items()):
        ms = " ".join(f"{100 * v.m[a]:5.1f}" for a in AGES)
        fs = " ".join(f"{v.f[a]:.4f}" for a in AGES)
        print(f"   {y} m: {ms}\n        f: {fs}  TFR={v.tfr:.4f}")
    print("  SF2.4 latest births outside marriage (%):")
    for iso, (by, bv) in sorted(res.bom.items(), key=lambda t: t[1][1]):
        if iso in {i for g in res.j3_groups["main (5y, <25%)"].values() for i in g}:
            print(f"   {iso} {by} {bv:5.1f} -> {bom_group(bv)}")


def section_j1(res: H11Result) -> None:
    print("\n== J1: Bongaarts marriage index decomposition (Japan, census years) ==")
    print("  year   TFR     Cm     TFR/Cm  | Cm 20-39  Cm alt-denom  Cm standard")
    for y in sorted(res.tfr):
        c = res.cm
        print(
            f"  {y}  {res.tfr[y]:.3f}  {c['main'][y]:.4f}  {res.tfr[y] / c['main'][y]:.4f}  | "
            f"{c['ages 20-39'][y]:.4f}   {c['denominator never+married'][y]:.4f}       "
            f"{c['standard Bongaarts (exploratory)'][y]:.4f}"
        )
    for k, ds in res.j1.items():
        print(f"  -- {k}")
        for dc in ds:
            print(
                f"   {dc.y0}->{dc.y1}: Δln TFR={dc.d_ln_tfr:+.4f}  Δln Cm={dc.d_ln_cm:+.4f}  "
                f"Δln(TFR/Cm)={dc.d_ln_rest:+.4f}  s_m={dc.s_m:.3f}  "
                f"(check {dc.d_ln_cm + dc.d_ln_rest - dc.d_ln_tfr:+.1e})"
            )
    if res.completed:
        a, va, b, vb = res.completed
        print(
            f"  auxiliary T04-23 completed fertility: {a} {va:.2f}"
            f" -> {b} {vb:.2f} (Δln {math.log(vb / va):+.4f})"
        )


def section_j2(res: H11Result) -> None:
    print("\n== J2: prefecture first differences, prefecture + year FE (pred. sign −) ==")
    for k, f in res.j2.items():
        if f is None:
            print(f"  [{k}] not estimable")
            continue
        ((x, c),) = f.coefs.items()
        print(
            f"  [{k}] n={f.n} G={f.groups} end-years={f.times}"
            f"  Δ{x}: {_f(c)}{'+' if h10.passes(c, -1) else ''}"
        )
    print(f"  J2 main passes: {res.j2_pass}")


def section_j3(res: H11Result) -> None:
    print("\n== J3: 5-year differences, country + period FE, by births outside marriage ==")
    for spec, gs in res.j3.items():
        print(f"  -- {spec}: groups {res.j3_groups[spec]}")
        for g, f in gs.items():
            if f is None:
                print(f"   [{g}] not estimable (n<{J3_MIN_N} or G<{J3_MIN_G} or collinear)")
                continue
            print(
                f"   [{g}] n={f.n} G={f.groups}  cmr: {_f(f.coefs['cmr'])}"
                f"  fagem: {_f(f.coefs['fagem'])}"
            )
    print(f"  J3 consistent (low +, CI∌0; high CI∋0): {res.j3_ok}")


def section_verdict(res: H11Result) -> None:
    m = res.j1["main"][0]
    print("\n== Verdict (pre-registered) ==")
    print(
        f"  s_m(1980->2020) = {m.s_m:.3f}; J2 main passe"
        f"s = {res.j2_pass}; J3 consistent = {res.j3_ok}"
    )
    print(f"  verdict: {res.code} = {VERDICT_JA[res.code]}")
    print(f"  final_stance: {res.final}")
    print(f"  framed_stance: {res.framed}")
    print("\n-- verdict under each robustness spec --")
    for k, (v, j) in res.robust.items():
        print(f"  {k:<48} {v:<17} J3 {j}")


def section_exploratory(res: H11Result) -> None:
    print("\n== Exploratory (not pre-registered, outside the verdict) ==")
    # E1: counterfactual TFR with marital fertility of year t and married shares of 1980
    base = res.years[1980]
    for y in sorted(res.years):
        v = res.years[y]
        cf = sum(base.m[a] * v.f[a] / v.m[a] for a in AGES)
        print(
            f"  E1 {y}: TFR {v.tfr:.3f}; with 1980 married shares and {y} marital fertility f/m: "
            f"{cf:.3f}"
        )
    # E2: marital fertility f_a / m_a by age
    for y in sorted(res.years):
        v = res.years[y]
        print(f"  E2 {y} f/m: " + " ".join(f"{a}:{v.f[a] / v.m[a]:.3f}" for a in AGES))
    # E3: cohort version (tempo-free): completed cohort fertility = ever-married share at 50 ×
    # births per ever-married woman. Census year t's never-married-at-50 ≈ cohort born t − 50.
    for c0, c1 in res.cohort_pairs:
        print(
            f"  E3 cohort {c0.cohort}->{c1.cohort}: CTFR {c0.ctfr:.3f}->{c1.ctfr:.3f} "
            f"ever-married {c0.ever:.4f}->{c1.ever:.4f}  "
            f"Δln CTFR={math.log(c1.ctfr / c0.ctfr):+.4f}"
            f"  Δln ever={math.log(c1.ever / c0.ever):+.4f}  share={cohort_share(c0, c1):.3f}"
        )
    for k, f in res.explore.items():
        if f is None:
            print(f"  [{k}] not estimable")
            continue
        print(
            f"  [{k}] n={f.n} G={f.groups} "
            + "  ".join(f"{x}: {_f(c)}" for x, c in f.coefs.items())
        )


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    return h10._plt()


def _save(fig: Any, path: Path, foot: str) -> None:
    h10._save(fig, path, foot)


def fig_j1(res: H11Result, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ds = res.j1["main"]
    labels = [f"{d.y0}→{d.y1}" for d in ds]
    xs = range(len(ds))
    w = 0.27
    ax.bar([x - w for x in xs], [d.d_ln_tfr for d in ds], w, color=INK, label="Δ ln TFR")
    ax.bar(list(xs), [d.d_ln_cm for d in ds], w, color=ORANGE, label="Δ ln Cm (married share)")
    ax.bar(
        [x + w for x in xs], [d.d_ln_rest for d in ds], w, color=BLUE_RAMP[2], label="Δ ln (TFR/Cm)"
    )
    for x, d in zip(xs, ds, strict=True):
        ax.text(x, 0.115, f"s_m={d.s_m:.2f}", ha="center", fontsize=7.5, color=INK)
    ax.set_ylim(-0.52, 0.15)
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=8)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_ylabel("log change")
    ax.set_title("J1: Δln TFR = Δln Cm + Δln(TFR/Cm), Japan", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    _style(ax)
    ax = axes[1]
    yrs = sorted(res.tfr)
    ax.plot(yrs, [res.tfr[y] for y in yrs], marker="o", color=INK, label="TFR")
    ax.plot(yrs, [res.cm["main"][y] for y in yrs], marker="o", color=ORANGE, label="Cm")
    ax.plot(
        yrs,
        [res.tfr[y] / res.cm["main"][y] for y in yrs],
        marker="o",
        color=BLUE_RAMP[2],
        label="TFR / Cm",
    )
    ax.set_title("Levels (census years)", fontsize=9)
    ax.legend(frameon=False, fontsize=7.5)
    _style(ax)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    foot = (
        "Cm = Σ m_a f_a / Σ f_a, women 15-49, m_a = married share (census), f_a = 5-year "
        "sum of single-year ASFR. Source: IPSS Popular Data 2026 T06-24, T04-09 (PDL1.0)."
        " n = 7 census years."
    )
    _save(fig, path, foot)


def fig_j1_profiles(res: H11Result, path: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    cols = {1970: BLUE_RAMP[0], 1980: BLUE_RAMP[1], 1990: BLUE_RAMP[2], 2000: BLUE_RAMP[3],
            2010: "#f2a37f", 2015: ORANGE, 2020: "#a8401a"}  # fmt: skip
    for y, v in sorted(res.years.items()):
        axes[0].plot(
            AGES, [100 * v.m[a] for a in AGES], marker="o", ms=3, color=cols[y], label=str(y)
        )
        axes[1].plot(AGES, [v.f[a] for a in AGES], marker="o", ms=3, color=cols[y], label=str(y))
    axes[0].set_ylabel("married (% of women)")
    axes[0].set_title("Married share by age, women (census)", fontsize=9)
    axes[1].set_ylabel("births per woman in the 5-year group")
    axes[1].set_title("f_a: ASFR summed over 5 ages", fontsize=9)
    for ax in axes:
        ax.legend(frameon=False, fontsize=7)
        ax.tick_params(axis="x", labelsize=7.5)
        _style(ax)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _save(
        fig,
        path,
        "Source: IPSS Popular Data 2026 T06-24 (marrie"
        "d), T04-09 (ASFR). 1970 ASFR excludes Okinawa.",
    )


def _dots(ax: Any, items: Sequence[tuple[str, Coef | None, bool]]) -> None:
    h10._dots(ax, items)


def fig_j2(res: H11Result, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    items = []
    for k, f in res.j2.items():
        c = next(iter(f.coefs.values())) if f else None
        items.append((f"{k} (n={f.n if f else 0})", c, h10.passes(c, -1)))
    _dots(ax, items)
    ax.set_xlabel("Δ TFR (Δ ln TFR for the ln row) per 1 SD of Δ never-married share", fontsize=7.5)
    ax.set_title(
        "J2: 47 prefectures, first differences, prefecture + year FE, 95% CI (cluster)", fontsize=9
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    foot = (
        "Orange = predicted sign (−) with CI excluding 0. Source: IPSS Popular Data 2026 "
        "T12-33, T12-36, T12-37 (census never-married shares; prefectural TFR)."
    )
    _save(fig, path, foot)


def fig_j3(res: H11Result, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    items = []
    for spec, gs in res.j3.items():
        for g in ("low", "mid", "high", "all"):
            f = gs.get(g)
            c = f.coefs["cmr"] if f else None
            lab = f"{spec} | {g} " + (f"(G={f.groups}, n={f.n})" if f else "(not estimable)")
            items.append((lab, c, h10.passes(c, 1) if g == "low" else False))
    _dots(ax, items)
    ax.set_xlabel(
        "Δ TFR per 1 SD of Δ crude marriage rate (controls: Δ female age at 1st marriage)",
        fontsize=7.5,
    )
    ax.set_title("J3: country + period FE, by births outside marriage (SF2.4 latest)", fontsize=9)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    foot = (
        "Groups by births outside marriage: low < 25% / mid / high >= 40% (alt. low < 20%"
        ", < 30%). 4-5 cluster SEs are unreliable.\nSources: OECD SF2.4, SF3.1, Eurostat "
        "demo_nind, IPSS T06-12, World Bank WDI (TFR)."
    )
    _save(fig, path, foot)


def run(data_dir: Path, fig_dir: Path) -> H11Result:
    pl.Config.set_tbl_rows(-1)
    pl.Config.set_tbl_width_chars(200)
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = load(data_dir)
    print("== Operational choices fixed before the first run (also in the module docstring) ==")
    print(f"  J1: ages {AGES}, f_a = 5-year sum of single-year ASFR, windows {J1_WINDOWS}")
    print(
        "  verdict: s_m>=2/3 & J2 pass -> main; s_m>=2/3 & J2"
        " fail -> main_unconfirmed; 1/3..2/3 both; <1/3 couple"
    )
    print(
        f"  J2: first differences between consecutive census years {J2_YEARS}; nm50 {J2_NM50_YEARS}"
    )
    print(
        f"  J3: width {J3_WIDTH}, ±{J3_WINDOW}, n>={J3_MIN_N}"
        f", G>={J3_MIN_G}; low<{BOM_LOW}, high>={BOM_HIGH}"
    )
    res = compute(d)
    section_data(res, d)
    section_j1(res)
    section_j2(res)
    section_j3(res)
    section_verdict(res)
    section_exploratory(res)
    fig_j1(res, fig_dir / "h11_j1_decomposition.png")
    fig_j1_profiles(res, fig_dir / "h11_j1_age_profiles.png")
    fig_j2(res, fig_dir / "h11_j2_prefecture.png")
    fig_j3(res, fig_dir / "h11_j3_country_groups.png")
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
