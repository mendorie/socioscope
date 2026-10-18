"""H12（事後追加）: 日本で「結婚という選択」が外れた背景は何か。アプリは仲介の消失を補っているか。

事前登録: design/themes/growth-fertility.md「### H12」（2026-10-18、part7）。検定 K1〜K4、判定、
最終スタンスの文型、頑健性、言えないことは追加データを見る前に design に固定した。H8〜H11 の
判定は変えない。

  K1 意思 (a): 「いずれ結婚するつもり」（1_1_1、18–34 歳）の 1982→2021 の変化と 95% CI の重なり、
     「一生結婚するつもりはない」の変化、NHK「結婚するのが当然」1993→2018（補強）。
     意思低下型 = 男女とも 10 ポイント以上低下し CI が重ならない。
  K2 到達 (b): 「交際相手なし」（2_1_2、18–34 歳総数）の 1982→2021 の変化、「独身でいる理由」
     （1_3_2、25–34 歳）で「適当な相手にまだめぐり会わない」が首位か、夫婦の出会い（5_2_2）の
     見合い＋職場の構成比の 1982→2021b の低下幅。到達失敗型 = 交際相手なしが男女とも 10 ポイント
     以上上昇し、かつ「めぐり会わない」が首位。
  K3 女性側 (c): 結婚の利点（1_2_1）の「子どもや家族」「経済的に余裕」の 1987→2021 の変化を男女で
     比べる。「結婚に利点がある」の男女差。相手の条件（3_2_1）で女性が経済力を重視する割合。
     女性側型 = 女性の「利点がある」の低下幅が男性より 5 ポイント以上大きい、または「経済的に余裕」
     の女性の選択率が 10 ポイント以上低下。
  K4 補填率: 経路別の推定婚姻件数 = 構成比（5_2_2、第 8 回 と 第 16 回 b）× 妻初婚件数（T06-01★、
     該当期間の年平均）。損失 = 見合い＋職場（1982）− 同（2021b）、補填 = ネット（2021b）。
     ≥ 50% 補われている / < 20% 補われていない / 間は部分的。感度 4 版（結婚相談所込み上限、
     こども家庭庁 25.1%・リクルート 11.4%・明治安田 30.4% を「ネット」の構成比に代入）。
  判定: K1〜K3 の成立した型を全部挙げ、複数なら変化幅（ポイント）で順位。どれも不成立なら
     「意思も到達も評価も、測った指標では大きく動いていない」。K4 は独立。

運用の細則（design に書かれていない点。mart の構造と一部の値を見た後、判定を出す前に書いた。
盲検ではない。stdout の冒頭に要点を出す）。
  - 「結婚に利点がある」（利点なしの補数）は、報告書グラフデータ 1_2_1 に「利点はないと思う」の
    選択肢が無く、選択肢は 2 つまで選ぶ複数回答なので他の項目からも作れない。K3 の第 1 条件は
    **測定不能**とし、第 2 条件（経済的に余裕の女性 −10 ポイント）だけで判定する。
  - 型の「変化幅」（順位と文型の X）は判定に使う指標の男女のうち小さい方の絶対値（「男女とも」
    の条件を縛る側）。K1 = |Δいずれ結婚するつもり|、K2 = Δ交際相手なし、K3 = 女性の経済的余裕の
    低下幅（第 1 条件は測定不能）。
  - 「めぐり会わない」が首位かは 2021 年（第 16 回）の 25–34 歳の男女それぞれで判定する（この
    設問は第 10 回 1992 から）。1_3_2 の母集団は報告書どおり（結婚意思のある未婚者）。
  - 期間の年平均は 7 月〜6 月の調査年度に合わせる: 第 8 回（結婚持続 5 年未満 ≒ 1977/7–1982/6）は
    1977・1982 年を半分、1978–1981 年を全部で 5 で割る。第 9 回は 1982–1987、
    第 16 回 a は 2015–2018、b は 2018–2021 を同様に。
  - 構成比は 5_2_2 の割合（「不詳」を含む分母）をそのまま使う。第 8 回は「ネットで」の選択肢が
    無いので 0 とする。
  - 結婚相談所込み上限: 第 16 回の「見合い結婚」は結婚相談所（オンラインを含む）を含み、相談所
    だけの割合は公表されていない。上限として 2021b の「見合い結婚」の全部を相談所とみなし、損失
    側からも補填側へ移す（補填率 = (ネット＋c)/(損失＋c)）。
  - 民間調査 3 本の代入版は「ネット」の構成比だけを置き換え、件数（妻初婚の年平均）と損失は本体
    と同じ。民間調査の定義（直近 5 年婚 / 2023 年婚姻者 / 1 年以内婚、アプリ / ネット系サービス）は
    5_2_2 と違う。
  - 25–34 歳の頑健性は 25–29・30–34 歳の度数を合算し（1_1_2 は 3 選択肢の度数の和を分母、2_1_2 は
    総数）、CI は単純無作為の近似（報告書の CI は標本設計を反映している可能性があり、主仕様とは
    同列でない）。K3 は年齢別が無いので 25–34 歳版は不実行。

決定的スクリプト。乱数不使用。補完なし。識別戦略なし（記述統計の比較）。

    uv run python themes/growth-fertility/src/theme_growth_fertility/analysis/<this file>
        [--data-dir data] [--fig-dir themes/growth-fertility/reports/figures]

純粋関数（ci_overlap, Change, k1_type, k2_type, k3_type, top_item, period_mean, fill, k4_verdict,
rank_types, final_stance, pooled）は tests/test_analysis_h12.py で検証。
"""

from __future__ import annotations

import argparse
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
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

THEME_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = THEME_DIR.parents[1]
ATT_MART = Path("marts") / "jp_marriage_attitudes.parquet"
SER_MART = Path("marts") / "jp_marriage_series.parquet"
NHK_MART = Path("marts") / "jp_norms_nhk.parquet"

# ---------------------------------------------------------------- pre-registered (design H12)
SEXES = ("male", "female")
Y0, Y1, Y0_ALT = 1982, 2021, 1987
K3_Y0 = 1987
K1_DROP = 10.0
K2_RISE = 10.0
K3_GAP, K3_ECON = 5.0, 10.0
K4_HI, K4_LO = 0.5, 0.2
INTEND = "いずれ結婚するつもり"
NEVER = "一生結婚するつもりはない"
MEET = "適当な相手にまだめぐり会わないから"
FAMILY = "自分の子どもや家族をもてる"
ECON = "経済的に余裕がもてる"
OMIAI, WORK, NET = "見合い結婚", "職場や仕事で", "ネットで"
LOST = (OMIAI, WORK)
WANT, NOWANT = "交際相手なし－交際を望む", "交際相手なし－交際を望まない"
WANT_NA = "交際相手なし－交際希望不詳"
P16A, P16B = "2015/7-2018/6", "2018/7-2021/6"
PERIOD_YEARS = {
    ("1982", ""): (1977, 1982),
    ("1987", ""): (1982, 1987),
    ("2021", P16A): (2015, 2018),
    ("2021", P16B): (2018, 2021),
}
# 補助の引用値（adapter なし。report に出典付きで引用）
EXTERNAL = (
    ("cfa2024", "こども家庭庁 2024（直近 5 年婚のうちマッチングアプリ）", 25.1),
    ("recruit2024", "リクルートブライダル総研 婚活実態調査 2024（2023 年婚姻者、ネット系）", 11.4),
    ("meiji2025", "明治安田「いい夫婦の日」2025（1 年以内婚、アプリ）", 30.4),
)
TYPE_JA = {"will": "意思の低下", "reach": "到達の失敗", "women": "女性側の評価の低下"}
TYPE_ORDER = ("will", "reach", "women")
K3_UNDETERMINED = "判定不能（第 2 条件は不成立、第 1 条件「結婚に利点がある」は測定不能）"


# ---------------------------------------------------------------- pure helpers (tested)
def ci_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """True if the closed intervals a=(lo, hi) and b=(lo, hi) share any point."""
    return a[0] <= b[1] and b[0] <= a[1]


@dataclass(frozen=True)
class Change:
    v0: float
    v1: float
    overlap: bool  # 95% CIs of the two rounds overlap

    @property
    def delta(self) -> float:
        return round(self.v1 - self.v0, 6)


def k1_type(ch: Mapping[str, Change]) -> bool:
    """意思低下型: both sexes fall by ≥ 10 points and the CIs do not overlap."""
    return all(c.delta <= -K1_DROP and not c.overlap for c in ch.values())


def k2_type(rise: Mapping[str, float], top: Mapping[str, bool]) -> bool:
    """到達失敗型: no-partner share rises ≥ 10 points in both sexes and 'not met' is top."""
    return all(round(r, 6) >= K2_RISE for r in rise.values()) and all(top.values())


def k3_type(adv_gap: float | None, econ_f_change: float) -> bool:
    """女性側型: women's 'has an advantage' falls ≥ 5 points more than men's (None = unmeasured),
    or women's 'economic room' choice falls ≥ 10 points."""
    gap_ok = adv_gap is not None and round(adv_gap, 6) >= K3_GAP
    return gap_ok or round(econ_f_change, 6) <= -K3_ECON


def top_item(shares: Mapping[str, float | None]) -> str:
    """The item with the largest share (None ignored)."""
    vals = {k: v for k, v in shares.items() if v is not None}
    return max(vals, key=lambda k: (vals[k], k))


def period_mean(values: Mapping[int, float], y0: int, y1: int) -> float:
    """Annual mean over July y0 – June y1 (half weight on end years). KeyError if missing."""
    total = 0.5 * values[y0] + 0.5 * values[y1] + sum(values[y] for y in range(y0 + 1, y1))
    return total / (y1 - y0)


@dataclass(frozen=True)
class Fill:
    loss: float
    filled: float
    n0: float
    n1: float

    @property
    def rate(self) -> float:
        return self.filled / self.loss


def fill(
    lost0: float, lost1: float, net1: float, n0: float, n1: float, moved1: float = 0.0
) -> Fill:
    """Shares are fractions. loss = lost0·n0 − (lost1 − moved1)·n1, filled = (net1 + moved1)·n1."""
    return Fill(lost0 * n0 - (lost1 - moved1) * n1, (net1 + moved1) * n1, n0, n1)


def k4_verdict(rate: float) -> str:
    if rate >= K4_HI:
        return "補われている"
    if rate < K4_LO:
        return "補われていない"
    return "部分的"


def rank_types(sizes: Mapping[str, float], established: Iterable[str]) -> list[tuple[str, float]]:
    """Established types ordered by the absolute size of change (points), largest first."""
    est = set(established)
    rows = [(k, abs(v)) for k, v in sizes.items() if k in est]
    return sorted(rows, key=lambda kv: (-kv[1], TYPE_ORDER.index(kv[0])))


FRACTIONS = (
    (1 / 10, "10 分の 1"),
    (1 / 5, "5 分の 1"),
    (1 / 4, "4 分の 1"),
    (1 / 3, "3 分の 1"),
    (1 / 2, "半分"),
    (2 / 3, "3 分の 2"),
    (3 / 4, "4 分の 3"),
    (1.0, "全部"),
)


def wari(rate: float) -> str:
    """Nearest simple fraction with the percentage, e.g. 0.252 -> '約 4 分の 1（25%）'."""
    _, name = min(FRACTIONS, key=lambda f: abs(f[0] - rate))
    return f"約 {name}（{100 * rate:.0f}%）"


def final_stance(ranked: Sequence[tuple[str, float]], rate: float) -> str:
    """The pre-registered sentence (design H12), filled mechanically."""
    tail = f"見合い・職場経由で失われた結婚のうち、ネット経由が補ったのは{wari(rate)}である"
    if not ranked:
        return f"意思も到達も評価も、測った指標では大きく動いていない。{tail}"
    main, x = ranked[0]
    others = "・".join(TYPE_JA[k] for k in TYPE_ORDER if k != main)
    return f"結婚が外れた背景は{TYPE_JA[main]}が主で（変化幅 {x:.1f} ポイント）、{others}は従である。{tail}"  # noqa: E501


def pooled(df: pl.DataFrame) -> tuple[float, float, float]:
    """Pooled share % = Σcount / Σdenominator with a simple-random-sampling 95% CI."""
    n = float(df["denominator"].sum())
    p = float(df["count"].sum()) / n
    se = math.sqrt(p * (1 - p) / n)
    return 100 * p, 100 * (p - 1.96 * se), 100 * (p + 1.96 * se)


# ---------------------------------------------------------------- data access
def load(data_dir: Path) -> dict[str, pl.DataFrame]:
    return {
        "att": pl.read_parquet(data_dir / ATT_MART),
        "ser": pl.read_parquet(data_dir / SER_MART),
        "nhk": pl.read_parquet(data_dir / NHK_MART),
    }


def rows(att: pl.DataFrame, figure: str, **eq: Any) -> pl.DataFrame:
    f = att.filter(pl.col("figure") == figure)
    for k, v in eq.items():
        f = f.filter(pl.col(k) == v)
    return f


def one(att: pl.DataFrame, figure: str, **eq: Any) -> dict[str, Any]:
    f = rows(att, figure, **eq)
    if f.height != 1:
        raise ValueError(f"{figure} {eq}: expected 1 row, got {f.height}")
    return f.row(0, named=True)


def pct(att: pl.DataFrame, figure: str, **eq: Any) -> float:
    v = one(att, figure, **eq)["share_pct"]
    if v is None:
        raise ValueError(f"{figure} {eq}: share is NULL")
    return float(v)


def wife_first(ser: pl.DataFrame) -> dict[int, float]:
    f = ser.filter(pl.col("metric") == "first_marriages_wife")
    return {int(y): float(v) for y, v in f.select("year", "value").iter_rows()}


# ---------------------------------------------------------------- K1
def k1_change(att: pl.DataFrame, item: str, y0: int, y1: int) -> dict[str, Change]:
    out: dict[str, Change] = {}
    for s in SEXES:
        a = one(att, "1_1_1", survey_year=y0, sex=s, item=item)
        b = one(att, "1_1_1", survey_year=y1, sex=s, item=item)
        ov = ci_overlap((a["ci_low"], a["ci_high"]), (b["ci_low"], b["ci_high"]))
        out[s] = Change(float(a["share_pct"]), float(b["share_pct"]), ov)
    return out


def k1_pooled_2534(att: pl.DataFrame, y0: int, y1: int) -> dict[str, Change]:
    """25–34 pooled from 1_1_2 (25–29 + 30–34): denominator = Σ counts of the 3 options."""
    out: dict[str, Change] = {}
    for s in SEXES:
        est = []
        for y in (y0, y1):
            f = rows(att, "1_1_2", survey_year=y, sex=s).filter(
                pl.col("age").is_in(["25～29歳", "30～34歳"])
            )
            den = f.group_by("age").agg(pl.col("count").sum().alias("denominator"))
            num = f.filter(pl.col("item") == INTEND).select("age", "count")
            est.append(pooled(num.join(den, on="age")))
        ov = ci_overlap((est[0][1], est[0][2]), (est[1][1], est[1][2]))
        out[s] = Change(est[0][0], est[1][0], ov)
    return out


def nhk_series(nhk: pl.DataFrame, group: str, label: str = "") -> list[tuple[int, float]]:
    f = nhk.filter(
        (pl.col("answer_code") == "01")
        & (pl.col("group") == group)
        & (pl.col("group_label") == label)
    ).sort("year")
    return [(int(y), float(v)) for y, v in f.select("year", "ratio_pct").iter_rows()]


# ---------------------------------------------------------------- K2
def no_partner(
    att: pl.DataFrame, y: int, s: str, ages: Sequence[str] = ("18～34歳（総数）",)
) -> float:
    """交際相手なし % (sum of the 交際希望 sub-items), pooled over `ages` via counts."""
    f = rows(att, "2_1_2", survey_year=y, sex=s).filter(pl.col("age").is_in(list(ages)))
    if len(ages) == 1:
        return float(f["share_pct"].sum())
    den = f.group_by("age").agg(pl.col("denominator").first())
    return 100 * float(f["count"].sum()) / float(den["denominator"].sum())


def reasons(att: pl.DataFrame, y: int, s: str, age: str = "25～34歳") -> dict[str, float | None]:
    f = rows(att, "1_3_2", survey_year=y, sex=s, age=age)
    return {
        str(i): (None if v is None else float(v))
        for i, v in f.select("item", "share_pct").iter_rows()
    }


def couples(att: pl.DataFrame, y: int, period: str = "") -> dict[str, float]:
    f = rows(att, "5_2_2", survey_year=y, period=period)
    return {str(i): float(v) for i, v in f.select("item", "share_pct").iter_rows()}


# ---------------------------------------------------------------- K4
def k4(
    att: pl.DataFrame,
    n_by_year: Mapping[int, float],
    base: tuple[int, str],
    end: tuple[int, str],
    *,
    net_override: float | None = None,
    upper: bool = False,
    upper_numerator_only: bool = False,
    single_year: bool = False,
) -> Fill:
    c0 = couples(att, *base)
    c1 = couples(att, *end)
    y0, y1 = PERIOD_YEARS[(str(base[0]), base[1])], PERIOD_YEARS[(str(end[0]), end[1])]
    if single_year:  # survey years' single-year counts instead of July-June means
        n0, n1 = n_by_year[y0[1]], n_by_year[y1[1]]
    else:
        n0, n1 = period_mean(n_by_year, *y0), period_mean(n_by_year, *y1)
    net1 = (net_override if net_override is not None else c1.get(NET, 0.0)) / 100
    moved = c1[OMIAI] / 100 if upper else 0.0
    if upper_numerator_only:  # design literal: add agency (all 2021b omiai) to the filler only
        net1 += c1[OMIAI] / 100
    return fill(sum(c0[k] for k in LOST) / 100, sum(c1[k] for k in LOST) / 100, net1, n0, n1, moved)


# ---------------------------------------------------------------- compute
@dataclass
class Verdict:
    label: str
    k1: dict[str, Change]
    k2_rise: dict[str, float]
    k2_top: dict[str, bool]
    k3_econ_f: float
    k3_adv_gap: float | None
    k4: Fill
    types: set[str] = field(default_factory=set)
    sizes: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.sizes = {
            "will": min(abs(c.delta) for c in self.k1.values()),
            "reach": min(self.k2_rise.values()),
            "women": -self.k3_econ_f,
        }
        if k1_type(self.k1):
            self.types.add("will")
        if k2_type(self.k2_rise, self.k2_top):
            self.types.add("reach")
        if k3_type(self.k3_adv_gap, self.k3_econ_f):
            self.types.add("women")

    @property
    def ranked(self) -> list[tuple[str, float]]:
        return rank_types(self.sizes, self.types)

    @property
    def stance(self) -> str:
        return final_stance(self.ranked, self.k4.rate)


@dataclass
class H12Result:
    main: Verdict
    robust: list[Verdict]
    k4_sens: list[tuple[str, Fill]]
    n_wife: dict[int, float]


def k3_econ_change(att: pl.DataFrame, s: str, y0: int = K3_Y0, y1: int = Y1) -> float:
    return pct(att, "1_2_1", survey_year=y1, sex=s, item=ECON) - pct(
        att, "1_2_1", survey_year=y0, sex=s, item=ECON
    )


def tops(att: pl.DataFrame, y: int) -> dict[str, bool]:
    return {s: top_item(reasons(att, y, s)) == MEET for s in SEXES}


def compute(d: Mapping[str, pl.DataFrame]) -> H12Result:
    att = d["att"]
    n = wife_first(d["ser"])
    econ_f = k3_econ_change(att, "female")
    rise = {s: no_partner(att, Y1, s) - no_partner(att, Y0, s) for s in SEXES}
    main = Verdict(
        "main (18-34, 1982->2021, 16b)",
        k1_change(att, INTEND, Y0, Y1),
        rise,
        tops(att, Y1),
        econ_f,
        None,
        k4(att, n, (Y0, ""), (Y1, P16B)),
    )
    ages2534 = ("25～29歳", "30～34歳")
    robust = [
        Verdict(
            "R1 ages 25-34 (K1/K2; K3 no age split)",
            k1_pooled_2534(att, Y0, Y1),
            {s: no_partner(att, Y1, s, ages2534) - no_partner(att, Y0, s, ages2534) for s in SEXES},
            tops(att, Y1),
            econ_f,
            None,
            main.k4,
        ),
        Verdict(
            "R2 start 1987 (K1/K2/K4)",
            k1_change(att, INTEND, Y0_ALT, Y1),
            {s: no_partner(att, Y1, s) - no_partner(att, Y0_ALT, s) for s in SEXES},
            tops(att, Y1),
            econ_f,
            None,
            k4(att, n, (Y0_ALT, ""), (Y1, P16B)),
        ),
        Verdict(
            "R3 end 16a 2015/7-2018/6 (K4 only)",
            main.k1,
            main.k2_rise,
            main.k2_top,
            econ_f,
            None,
            k4(att, n, (Y0, ""), (Y1, P16A)),
        ),
        Verdict(
            "R5 upper bound: all 16b omiai = marriage agency (K4)",
            main.k1,
            main.k2_rise,
            main.k2_top,
            econ_f,
            None,
            k4(att, n, (Y0, ""), (Y1, P16B), upper=True),
        ),
    ]
    sens: list[tuple[str, Fill]] = [
        ("upper (agency incl.)", robust[3].k4),
        ("upper literal", k4(att, n, (Y0, ""), (Y1, P16B), upper_numerator_only=True)),
        ("single-year counts", k4(att, n, (Y0, ""), (Y1, P16B), single_year=True)),
    ]
    for key, _label, share in EXTERNAL:
        sens.append((key, k4(att, n, (Y0, ""), (Y1, P16B), net_override=share)))
    return H12Result(main, robust, sens, n)


# ---------------------------------------------------------------- printing
def _ch(c: Change) -> str:
    return f"{c.v0:.1f} -> {c.v1:.1f} ({c.delta:+.1f}, CI overlap={c.overlap})"


def section_data(d: Mapping[str, pl.DataFrame], res: H12Result) -> None:
    att = d["att"]
    print("\n== Data ==")
    print(f"jp_marriage_attitudes rows: {att.height}")
    print(
        att.group_by("figure", maintain_order=True).agg(
            pl.len().alias("rows"),
            pl.col("survey_year").min().alias("y_min"),
            pl.col("survey_year").max().alias("y_max"),
            pl.col("share_pct").null_count().alias("share_null"),
        )
    )
    print(f"jp_marriage_series rows: {d['ser'].height}; jp_norms_nhk rows: {d['nhk'].height}")
    n = res.n_wife
    print(
        "first_marriages_wife (T06-01): "
        + ", ".join(
            f"{y} {n[y]:,.0f}"
            for y in (
                1977,
                1978,
                1979,
                1980,
                1981,
                1982,
                1987,
                2015,
                2016,
                2017,
                2018,
                2019,
                2020,
                2021,
            )
        )
    )
    for k, (y0, y1) in PERIOD_YEARS.items():
        print(f"  period mean {k}: July {y0} - June {y1} = {period_mean(n, y0, y1):,.0f}")
    benefits = rows(att, "1_2_1", survey_year=Y1, sex="female")["item"].to_list()
    print(
        f"1_2_1 options ({len(benefits)}): 'no advantage' option present = "
        f"{any('利点' in str(b) and 'ない' in str(b) for b in benefits)}"
    )


def section_k1(d: Mapping[str, pl.DataFrame], res: H12Result) -> None:
    att = d["att"]
    print("\n== K1 intention (1_1_1, never-married 18-34) ==")
    for s, c in res.main.k1.items():
        print(f"  {INTEND} {s}: {_ch(c)}")
    for s, c in k1_change(att, NEVER, Y0, Y1).items():
        print(f"  {NEVER} {s}: {_ch(c)}")
    print("  series (いずれ M / F):")
    for y in sorted(rows(att, "1_1_1")["survey_year"].unique().to_list()):
        m = one(att, "1_1_1", survey_year=y, sex="male", item=INTEND)
        f = one(att, "1_1_1", survey_year=y, sex="female", item=INTEND)
        print(
            f"    {y}: M {m['share_pct']} [{m['ci_low']}, {m['ci_high']}]  "
            f"F {f['share_pct']} [{f['ci_low']}, {f['ci_high']}]"
        )
    print(f"  K1 意思低下型 = {k1_type(res.main.k1)}")
    print("  NHK Q49 '結婚するのが当然' (all ages 16+):")
    for g in ("all", "male", "female"):
        print(f"    {g}: {nhk_series(d['nhk'], g)}")
    for lab in d["nhk"].filter(pl.col("group") == "age")["group_label"].unique(maintain_order=True):
        print(f"    age {lab}: {nhk_series(d['nhk'], 'age', str(lab))}")


def section_k2(d: Mapping[str, pl.DataFrame], res: H12Result) -> None:
    att = d["att"]
    print("\n== K2 reach ==")
    for s in SEXES:
        print(
            f"  no partner {s} 18-34: {no_partner(att, Y0, s):.1f} -> {no_partner(att, Y1, s):.1f}"
            f" ({res.main.k2_rise[s]:+.1f})"
        )
        split = rows(att, "2_1_2", survey_year=Y1, sex=s, age="18～34歳（総数）")
        print(
            "    2021 split: "
            + ", ".join(f"{i} {v}" for i, v in split.select("item", "share_pct").iter_rows())
        )
    for y in sorted(rows(att, "2_1_2")["survey_year"].unique().to_list()):
        print(f"    {y}: M {no_partner(att, y, 'male'):.1f}  F {no_partner(att, y, 'female'):.1f}")
    print("  reasons for staying single (1_3_2, 25-34): top item and 'not met' share")
    for y in sorted(rows(att, "1_3_2")["survey_year"].unique().to_list()):
        for s in SEXES:
            r = reasons(att, y, s)
            t = top_item(r)
            second = sorted((v for k, v in r.items() if v is not None and k != t), reverse=True)[0]
            print(f"    {y} {s}: top = {t} {r[t]}; not met = {r[MEET]}; 2nd = {second}")
    print(f"  K2 top reason 2021 = {res.main.k2_top}")
    print("  couples' meeting (5_2_2, married < 5 y): omiai / work / omiai+work / net / friends")
    keys = [(y, "") for y in (1982, 1987, 1992, 1997, 2002, 2005, 2010, 2015)] + [
        (2021, P16A),
        (2021, P16B),
    ]
    for y, p in keys:
        c = couples(att, y, p)
        print(
            f"    {y}{p and ' ' + p}: {c[OMIAI]:.1f} / {c[WORK]:.1f} / {c[OMIAI] + c[WORK]:.1f}"
            f" / {c.get(NET, 0.0):.1f} / {c['友人・兄弟姉妹を通じて']:.1f}"
        )
    c0, c1 = couples(att, Y0), couples(att, Y1, P16B)
    print(
        f"  omiai+work 1982 -> 2021b: {c0[OMIAI] + c0[WORK]:.1f} -> {c1[OMIAI] + c1[WORK]:.1f}"
        f" ({c1[OMIAI] + c1[WORK] - c0[OMIAI] - c0[WORK]:+.1f})"
    )
    print("  unmarried with partner: how they met (2_3_1), 1982 -> 2021: omiai / work / net")
    for s in SEXES:
        a = {
            str(i): float(v)
            for i, v in rows(att, "2_3_1", survey_year=Y0, sex=s)
            .select("item", "share_pct")
            .iter_rows()
        }
        b = {
            str(i): float(v)
            for i, v in rows(att, "2_3_1", survey_year=Y1, sex=s)
            .select("item", "share_pct")
            .iter_rows()
        }
        print(
            f"    {s}: {a['見合いで']} / {a['職場や仕事で']} / {a.get('ネットで', 0.0)} -> "
            f"{b['見合いで']} / {b['職場や仕事で']} / {b.get('ネットで', 0.0)}"
        )
    print(f"  K2 到達失敗型 = {'reach' in res.main.types}")


def section_k3(d: Mapping[str, pl.DataFrame], res: H12Result) -> None:
    att = d["att"]
    print("\n== K3 women's evaluation (1_2_1 advantages of marriage, never-married 18-34) ==")
    for item in (
        FAMILY,
        ECON,
        "精神的な安らぎの場が得られる",
        "現在愛情を感じている人と暮らせる",
        "社会的信用を得たり、周囲と対等になれる",
        "親を安心させたり周囲の期待にこたえられる",
    ):
        for s in SEXES:
            ser = [
                (y, pct(att, "1_2_1", survey_year=y, sex=s, item=item))
                for y in (1987, 1992, 1997, 2002, 2005, 2010, 2015, 2021)
            ]
            print(
                f"  {item} {s}: "
                + " ".join(f"{y}:{v}" for y, v in ser)
                + f"  (1987->2021 {ser[-1][1] - ser[0][1]:+.1f})"
            )
    print(
        "  'has an advantage' (complement of 'no advantage'): NOT MEASURABLE (option absent in 1_2_1)"  # noqa: E501
    )
    print("  partner conditions (3_2_1) 経済力: 重視 / 考慮 by sex")
    for y in sorted(rows(att, "3_2_1")["survey_year"].unique().to_list()):
        parts = []
        for s in SEXES:
            a = pct(att, "3_2_1", survey_year=y, sex=s, item="経済力", sub="重視する")
            b = pct(att, "3_2_1", survey_year=y, sex=s, item="経済力", sub="考慮する")
            parts.append(f"{s} {a}/{b} (sum {a + b:.1f})")
        print(f"    {y}: " + "; ".join(parts))
    print(
        f"  econ female 1987->2021 = {res.main.k3_econ_f:+.1f}; K3 女性側型 = {'women' in res.main.types}"  # noqa: E501
    )


def section_k4(res: H12Result) -> None:
    status = "成立" if "women" in res.main.types else K3_UNDETERMINED
    print(f"\n  K3 status: {status}")
    print("\n== K4 fill rate ==")
    f = res.main.k4
    print(f"  wife first marriages, annual mean: base {f.n0:,.0f}, 2021b {f.n1:,.0f}")
    print(
        f"  loss (omiai+work) = {f.loss:,.0f}/yr; filled (net) = {f.filled:,.0f}/yr; "
        f"rate = {f.rate:.3f} -> {k4_verdict(f.rate)}"
    )
    print("  sensitivity:")
    for key, s in res.k4_sens:
        print(
            f"    {key}: loss {s.loss:,.0f}, filled {s.filled:,.0f}, rate {s.rate:.3f} -> "
            f"{k4_verdict(s.rate)}"
        )


def section_exploratory(d: Mapping[str, pl.DataFrame]) -> None:
    att = d["att"]
    print("\n== Exploratory (not pre-registered; not used for the verdict) ==")
    print(
        "  E1 no-partner split by wish to date (2_1_2, 18-34; asked from 2010): want / not want / NA"  # noqa: E501
    )
    for y in (2010, 2015, 2021):
        parts = []
        for s in SEXES:
            f = {
                str(i): float(v)
                for i, v in rows(att, "2_1_2", survey_year=y, sex=s, age="18～34歳（総数）")
                .select("item", "share_pct")
                .iter_rows()
            }
            parts.append(f"{s} {f[WANT]:.1f} / {f[NOWANT]:.1f} / {f[WANT_NA]:.1f}")
        print(f"    {y}: " + "; ".join(parts))
    print("  E2 5_2_1 marriage-year view (first marriages): love / arranged / internet")
    for my in ("1980～84年", "2015～18年", "2019～21年"):
        f = {
            str(i): float(v)
            for i, v in rows(att, "5_2_1", marriage_year=my).select("item", "share_pct").iter_rows()
        }
        print(
            f"    {my}: {f['恋愛結婚']} / {f['見合い結婚']} / {f.get('ネット（インターネット）で', 0.0)}"  # noqa: E501
        )


def section_verdict(res: H12Result) -> None:
    print("\n== Verdict (pre-registered) ==")
    v = res.main
    print(f"  types established: {[TYPE_JA[k] for k, _ in v.ranked] or 'none'}")
    print(f"  sizes (points): {{{', '.join(f'{k}: {s:.1f}' for k, s in v.sizes.items())}}}")
    print(f"  K4: {v.k4.rate:.3f} -> {k4_verdict(v.k4.rate)}")
    print(f"  final stance: {v.stance}")
    print("\n== Robustness (pre-registered list) ==")
    for r in res.robust:
        print(f"  {r.label}")
        print("    K1: " + "; ".join(f"{s} {_ch(c)}" for s, c in r.k1.items()))
        print("    K2 rise: " + "; ".join(f"{s} {x:+.1f}" for s, x in r.k2_rise.items()))
        print(
            f"    K4: loss {r.k4.loss:,.0f} filled {r.k4.filled:,.0f} rate {r.k4.rate:.3f} "
            f"-> {k4_verdict(r.k4.rate)}"
        )
        print(f"    types: {[TYPE_JA[k] for k, _ in r.ranked] or 'none'}; stance: {r.stance}")


# ---------------------------------------------------------------- figures
def _plt() -> Any:
    return h10._plt()


def _save(fig: Any, path: Path, foot: str) -> None:
    h10._save(fig, path, foot)


SRC_IPSS = "Source: IPSS, 16th Japanese National Fertility Survey report, graph data (PDL1.0)."
SEX_COL = {"male": BLUE_RAMP[3], "female": ORANGE}


def fig_k1(d: Mapping[str, pl.DataFrame], path: Path) -> None:
    att = d["att"]
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    ax = axes[0]
    for s in SEXES:
        for item, ls in ((INTEND, "-"), (NEVER, "--")):
            f = rows(att, "1_1_1", sex=s, item=item).sort("survey_year")
            ys, v = f["survey_year"].to_list(), f["share_pct"].to_list()
            ax.fill_between(
                ys, f["ci_low"].to_list(), f["ci_high"].to_list(), color=SEX_COL[s], alpha=0.2, lw=0
            )
            lab = f"{s}, {'intend to marry' if item == INTEND else 'never intend'}"
            ax.plot(ys, v, ls, marker="o", ms=3, color=SEX_COL[s], label=lab)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of never-married aged 18-34")
    ax.set_title("K1: lifetime marriage intention (95% CI band)", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7)
    _style(ax)
    ax = axes[1]
    for g, col in (("all", INK), ("male", BLUE_RAMP[3]), ("female", ORANGE)):
        pts = nhk_series(d["nhk"], g)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=3, color=col, label=g)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% 'people should marry' (age 16+)")
    ax.set_title("NHK 'Japanese values' Q49, general population", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7)
    _style(ax)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    foot = (
        SRC_IPSS + " n per round 2,000-3,300 per sex.\nNHK Broadcasting Culture Research"
        " Institute, 'Japanese values' survey (processed; non-commercial use), 1993-2018."
    )
    _save(fig, path, foot)


def fig_k2(d: Mapping[str, pl.DataFrame], path: Path) -> None:
    att = d["att"]
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    ax = axes[0]
    years = sorted(rows(att, "2_1_2")["survey_year"].unique().to_list())
    for s in SEXES:
        ax.plot(
            years,
            [no_partner(att, y, s) for y in years],
            marker="o",
            ms=3,
            color=SEX_COL[s],
            label=s,
        )
    ax.set_ylim(0, 100)
    ax.set_ylabel("% with no partner (never-married 18-34)")
    ax.set_title("No dating partner", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7)
    _style(ax)
    ax = axes[1]
    ys = sorted(rows(att, "1_3_2")["survey_year"].unique().to_list())
    for s in SEXES:
        ax.plot(
            ys,
            [reasons(att, y, s)[MEET] for y in ys],
            marker="o",
            ms=3,
            color=SEX_COL[s],
            label=f"{s}: not yet met a suitable partner",
        )
        ax.plot(
            ys,
            [
                sorted(
                    (v for k, v in reasons(att, y, s).items() if v is not None and k != MEET),
                    reverse=True,
                )[0]
                for y in ys
            ],
            ":",
            color=SEX_COL[s],
            label=f"{s}: 2nd most cited reason",
        )
    ax.set_ylim(0, 70)
    ax.set_ylabel("% citing (25-34, up to 3 reasons)")
    ax.set_title("Reasons for staying single", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=6.5)
    _style(ax)
    ax = axes[2]
    keys = [(y, "") for y in (1982, 1987, 1992, 1997, 2002, 2005, 2010, 2015)]
    keys += [(2021, P16A), (2021, P16B)]
    xs = [y if not p else (2018 if p == P16A else 2021) for y, p in keys]
    for item, col, lab in (
        (OMIAI, BLUE_RAMP[-1], "arranged / agency"),
        (WORK, BLUE_RAMP[1], "workplace"),
        (NET, ORANGE, "internet"),
    ):
        pts = [(x, couples(att, y, p).get(item)) for x, (y, p) in zip(xs, keys, strict=True)]
        pts2 = [(x, v) for x, v in pts if v is not None]  # internet: option only in the 16th round
        ax.plot([x for x, _ in pts2], [v for _, v in pts2], marker="o", ms=3, color=col, label=lab)
    ax.set_ylim(0, 40)
    ax.set_ylabel("% of couples married < 5 years")
    ax.set_title("How couples met (2018 = 2015/7-18/6, 2021 = 2018/7-21/6)", fontsize=8, loc="left")
    ax.legend(frameon=False, fontsize=7)
    _style(ax)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    foot = (
        SRC_IPSS + " 'Internet' option new in 2021; 'arranged' includes marriage agencies"
        " (incl. online) in 2021.\n2018/7-2021/6 overlaps the COVID-19 marriage drop."
    )
    _save(fig, path, foot)


def fig_k3(d: Mapping[str, pl.DataFrame], path: Path) -> None:
    att = d["att"]
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    ax = axes[0]
    ys = (1987, 1992, 1997, 2002, 2005, 2010, 2015, 2021)
    for s in SEXES:
        for item, ls, lab in ((FAMILY, "-", "children / family"), (ECON, "--", "economic room")):
            ax.plot(
                ys,
                [pct(att, "1_2_1", survey_year=y, sex=s, item=item) for y in ys],
                ls,
                marker="o",
                ms=3,
                color=SEX_COL[s],
                label=f"{s}: {lab}",
            )
    ax.set_ylim(0, 60)
    ax.set_ylabel("% choosing as an advantage of marriage (up to 2)")
    ax.set_title("K3: advantages of marriage (never-married 18-34)", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7)
    _style(ax)
    ax = axes[1]
    ys2 = sorted(rows(att, "3_2_1")["survey_year"].unique().to_list())
    for s, lab in (("female", "women on men"), ("male", "men on women")):
        ax.plot(
            ys2,
            [pct(att, "3_2_1", survey_year=y, sex=s, item="経済力", sub="重視する") for y in ys2],
            marker="o",
            ms=3,
            color=SEX_COL[s],
            label=f"{lab}: 'important'",
        )
        ax.plot(
            ys2,
            [pct(att, "3_2_1", survey_year=y, sex=s, item="経済力", sub="考慮する") for y in ys2],
            ":",
            marker="o",
            ms=3,
            color=SEX_COL[s],
            label=f"{lab}: 'consider'",
        )
    ax.set_ylim(0, 70)
    ax.set_ylabel("% of never-married 18-34")
    ax.set_title("Partner's economic standing (no 2005 question)", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=7)
    _style(ax)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    foot = (
        SRC_IPSS + " 1_2_1 has no 'no advantage' option, so 'sees any advantage' is not measured."
    )
    _save(fig, path, foot)


def fig_k4(res: H12Result, path: Path) -> None:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    items = [("main: IPSS 2018/7-21/6 internet 13.6%", res.main.k4.rate)]
    items += [(r.label, r.k4.rate) for r in res.robust if r.label.startswith(("R2", "R3"))]
    labels = {
        "upper (agency incl.)": "upper: all 2021b 'arranged/agency' moved to filler",
        "upper literal": "upper (design literal): + agency to filler only",
        "single-year counts": "single-year counts (1982, 2021)",
        "cfa2024": "Children & Families Agency 2024: 25.1%",
        "recruit2024": "Recruit Bridal 2024: 11.4%",
        "meiji2025": "Meiji Yasuda 2025: 30.4%",
    }
    items += [(labels[k], s.rate) for k, s in res.k4_sens]
    for i, (_lab, r) in enumerate(items):
        ax.barh(i, 100 * r, color=ORANGE if i == 0 else BLUE_RAMP[2], height=0.6)
        ax.text(100 * r + 1, i, f"{100 * r:.0f}%", va="center", fontsize=7.5, color=INK)
    ax.axvline(20, color=MUTED, ls=":", lw=1)
    ax.axvline(50, color=MUTED, ls=":", lw=1)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([t for t, _ in items], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("internet-met marriages / marriages lost via arranged + workplace (%)")
    ax.set_title("K4: fill rate (dotted: 20% / 50% thresholds)", fontsize=9, loc="left")
    _style(ax)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    foot = (
        SRC_IPSS + " Counts: IPSS Popular Data 2026 T06-01 (bride's first marriages,"
        " July-June means).\nPrivate surveys are online-panel studies; only the internet"
        " share is substituted."
    )
    _save(fig, path, foot)


def run(data_dir: Path, fig_dir: Path) -> H12Result:
    pl.Config.set_tbl_rows(-1)
    pl.Config.set_tbl_width_chars(200)
    fig_dir.mkdir(parents=True, exist_ok=True)
    d = load(data_dir)
    print("== Operational choices fixed before the verdict (also in the module docstring) ==")
    print(
        "  K3 condition 1 ('has an advantage' gap) is unmeasurable: 1_2_1 has no 'no advantage'"
        " option -> K3 judged on condition 2 only"
    )
    print("  type size = smaller |change| of the two sexes on the classifying indicator")
    print("  K2 top reason judged in 2021 for 25-34 by sex; K4 counts = July-June annual means")
    print("  upper bound moves all 2021b 'arranged (incl. agency)' to the filler side")
    res = compute(d)
    section_data(d, res)
    section_k1(d, res)
    section_k2(d, res)
    section_k3(d, res)
    section_k4(res)
    section_verdict(res)
    section_exploratory(d)
    fig_k1(d, fig_dir / "h12_k1_intention.png")
    fig_k2(d, fig_dir / "h12_k2_reach.png")
    fig_k3(d, fig_dir / "h12_k3_benefits.png")
    fig_k4(res, fig_dir / "h12_k4_fill_rate.png")
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = parser.parse_args()
    run(args.data_dir, args.fig_dir)


if __name__ == "__main__":
    main()
