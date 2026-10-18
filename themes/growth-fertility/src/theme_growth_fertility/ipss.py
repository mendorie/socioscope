"""国立社会保障・人口問題研究所 (IPSS) 人口統計資料集 2026 xlsx tables and 第16回出生動向基本調査
結果の概要 PDF -> long rows. Pure; no I/O (H9-JP: norms vs constraints, birth order, cohorts).

Sources (PDL1.0 = 公共データ利用規約 第1.0版, attribution only):

- ``T04-NN.xlsx`` from ``https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/``. Each
  workbook has one worksheet; ★ tables (T04-09, T04-11, T04-16) carry a second sheet ``T04-NN★``
  with every year, which is the one read here. The layout of each table (title, header labels,
  year / age / round ranges, column counts, totals) is checked and any deviation raises
  ``ValueError`` (fail closed; nothing is imputed, '…' cells produce no row).
- ``JNFS16gaiyo.pdf`` (AES-encrypted, pypdf needs ``cryptography``): the data labels of 図表 7-1
  (夫婦の平均理想・予定子ども数, rounds 7–16 = 1977–2021) and 図表 3-3 (未婚者の平均希望子ども数,
  1982–2021, men / women) plus the 妻 35 歳未満 series printed in the note under 図表 7-1. Label
  order is verified against the published 7th- and 16th-round values (not monotonicity).

Two marts:

- ``survey``: survey_year, metric (planned_children / children_born / completed_fertility /
  completed_parity_share from the xlsx; ideal_children / planned_children_pdf /
  desired_children_single from the PDF), group, birth_cohort (T04-23 only), value, table, source.
- ``births``: year, metric (births / births_share / tfr_order / mean_age_order / asfr /
  cohort_cum_fertility), group (総数 / 第1子…第5子以上 / age 15..49), cohort (T04-11 only:
  birth year; the sheet's column label is the year the cohort turned 15, so cohort = label − 15
  and year = cohort + age), value, table, source.

H10 (family-formation constraints) adds two more mart sides, see the ``# ---- H10`` section:

- ``marriage`` (``marts/jp_marriage_series``): T06-24(1) never_married_share by sex x 5-year age
  class (census 1920–2020), T06-12 mean_age_marriage_all / mean_age_first_marriage by sex
  (1899–2024, two column blocks), T06-23 never_married_at_50 by sex (1920–2020).
- ``prefecture`` (``marts/jp_prefecture_panel``, built in ``prefecture.py`` together with the
  e-Stat / 内閣府 sources): T12-33★ tfr (every year), T12-35 mean_age_first_marriage, T12-36
  never_married_m30_34 / never_married_f25_29, T12-37 never_married_at_50, T12-52 lfp by sex x
  age class, T12-53 unemployment_rate by sex. 全国 is ``pref_code`` "00"; the 47 prefectures must
  appear in JIS order.

H12 (why marriage dropped out) appends, see the ``# ---- H12`` section:

- T06-01★ (``marriage`` side): marriages_total / first_marriages_* / remarriages_* /
  first_marriage_share_*_pct / crude_marriage_rate, every year 1884–2024.
- 第16回出生動向基本調査 報告書グラフデータ CSV (``GRAPH_FILES``, CP932, tidy, PDL1.0):
  ``graph_rows`` -> one long row per (figure, round / period / marriage year, sex, age, category,
  item, sub) with count / share_pct / se / ci / denominator; ``build_attitudes_mart`` ->
  ``marts/jp_marriage_attitudes``.
"""

import csv
import io
import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from theme_growth_fertility import prefecture
from theme_growth_fertility.estat import xlsx_rows
from theme_growth_fertility.kostat import pdf_text

SOURCE = "ipss"
BASE_URL = "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/"
PDF_URL = "https://www.ipss.go.jp/ps-doukou/j/doukou16/JNFS16gaiyo.pdf"
PDF_RAW_NAME = "JNFS16gaiyo.pdf"
PDF_KEY = "jnfs16"
# IPSS publishes under 公共データ利用規約（第1.0版）= PDL1.0 (attribution only; checked 2026-10-18).
LICENSE = (
    "PDL1.0 (公共データ利用規約（第1.0版）; https://www.ipss.go.jp/). "
    "Attribution: 国立社会保障・人口問題研究所『人口統計資料集 2026』"
    "『第 16 回出生動向基本調査 結果の概要』（PDL1.0）"
)

SURVEY_YEARS: tuple[int, ...] = (1977, 1982, 1987, 1992, 1997, 2002, 2005, 2010, 2015, 2021)
SURVEY_ROUNDS: tuple[int, ...] = tuple(range(7, 17))
SINGLE_YEARS: tuple[int, ...] = SURVEY_YEARS[1:]

SURVEY_METRICS: tuple[str, ...] = (
    "planned_children",
    "children_born",
    "completed_fertility",
    "completed_parity_share",
    "ideal_children",
    "planned_children_pdf",
    "desired_children_single",
)
BIRTHS_METRICS: tuple[str, ...] = (
    "births",
    "births_share",
    "tfr_order",
    "mean_age_order",
    "asfr",
    "cohort_cum_fertility",
)
TOTAL = "総数"
WIFE_AGE_GROUPS: tuple[str, ...] = (
    TOTAL,
    "妻 20-24",
    "妻 25-29",
    "妻 30-34",
    "妻 35-39",
    "妻 40-44",
    "妻 45-49",
)
PARITY_GROUPS: tuple[str, ...] = ("無子", "1人", "2人", "3人", "4人以上")
ORDER_GROUPS: tuple[str, ...] = (TOTAL, "第1子", "第2子", "第3子", "第4子", "第5子以上")
COUPLE = "夫婦"
COUPLE_U35 = "夫婦（妻35歳未満）"
SINGLE_MEN = "未婚男性"
SINGLE_WOMEN = "未婚女性"
AGES: tuple[int, ...] = tuple(range(15, 50))


@dataclass(frozen=True)
class Table:
    key: str
    code: str
    sheet: str
    mart: str  # "survey" | "births" | "marriage" | "prefecture"

    @property
    def url(self) -> str:
        return f"{BASE_URL}{self.code}.xlsx"

    @property
    def raw_name(self) -> str:
        return f"{self.code}.xlsx"


TABLES: tuple[Table, ...] = (
    Table("t04_25", "T04-25", "T04-25", "survey"),
    Table("t04_24", "T04-24", "T04-24", "survey"),
    Table("t04_23", "T04-23", "T04-23", "survey"),
    Table("t04_15", "T04-15", "T04-15", "births"),
    Table("t04_16", "T04-16", "T04-16★", "births"),
    Table("t04_09", "T04-09", "T04-09★", "births"),
    Table("t04_11", "T04-11", "T04-11★", "births"),
    # ---- H10 (appended; the sheet of a multi-sheet table is the first one it reads)
    Table("t06_24", "T06-24", "T06-24(1)", "marriage"),
    Table("t06_12", "T06-12", "T06-12", "marriage"),
    Table("t06_23", "T06-23", "T06-23", "marriage"),
    Table("t12_33", "T12-33", "T12-33★", "prefecture"),
    Table("t12_35", "T12-35", "T12-35(1)", "prefecture"),
    Table("t12_36", "T12-36", "T12-36", "prefecture"),
    Table("t12_37", "T12-37", "T12-37(1)", "prefecture"),
    Table("t12_52", "T12-52", "T12-52(1)", "prefecture"),
    Table("t12_53", "T12-53", "T12-53", "prefecture"),
    # ---- H12 (appended): 初婚・再婚別婚姻数, every year 1884–2024 on the second sheet
    Table("t06_01", "T06-01", "T06-01★", "marriage"),
)

Rows = Sequence[dict[int, str]]


# ---- helpers -------------------------------------------------------------------------------


def _norm(text: str | None) -> str:
    """NFKC (full-width digits/parens/tilde -> ASCII), wave dash -> '~', all whitespace removed."""
    if text is None:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).replace("〜", "~")


def _num(text: str | None, where: str) -> float:
    try:
        return float(_norm(text))
    except ValueError:
        msg = f"{where}: non-numeric cell {text!r}"
        raise ValueError(msg) from None


def _int(text: str | None) -> int | None:
    """Integer value of a cell ('1977', '1977.0') or None when it is not one."""
    s = _norm(text)
    if re.fullmatch(r"\d{4}(?:\.0+)?", s):
        return int(float(s))
    return None


def _title(rows: Rows, prefix: str, code: str) -> None:
    first = _norm(rows[0].get(1)) if rows else ""
    if not first.startswith(prefix):
        msg = f"{code}: unexpected title {first!r} (expected {prefix!r}…)"
        raise ValueError(msg)


def _header_row(rows: Rows, first_cell: str, code: str) -> int:
    for i, r in enumerate(rows):
        if _norm(r.get(1)) == first_cell:
            return i
    msg = f"{code}: header row starting with {first_cell!r} not found"
    raise ValueError(msg)


def _check_header(row: dict[int, str], expected: dict[int, str], code: str) -> None:
    got = {c: _norm(row.get(c)) for c in expected}
    if got != expected:
        msg = f"{code}: unexpected header {got} (expected {expected})"
        raise ValueError(msg)


def _survey_row(
    survey_year: int,
    metric: str,
    group: str,
    birth_cohort: int | None,
    value: float,
    table: str,
) -> dict[str, object]:
    return {
        "survey_year": survey_year,
        "metric": metric,
        "group": group,
        "birth_cohort": birth_cohort,
        "value": value,
        "table": table,
        "source": SOURCE,
    }


def _births_row(
    year: int, metric: str, group: str, cohort: int | None, value: float | int, table: str
) -> dict[str, object]:
    return {
        "year": year,
        "metric": metric,
        "group": group,
        "cohort": cohort,
        "value": value,
        "table": table,
        "source": SOURCE,
    }


def sheet_rows(payload: bytes, sheet: str) -> list[dict[int, str]]:
    """Cells of the named worksheet ({1-based column: text} per row). ``ValueError`` when the
    payload is not an xlsx or has no such sheet."""
    return xlsx_rows(payload, sheet)


# ---- T04-25 / T04-24: 妻の年齢（5歳階級）別 予定子ども数 / 平均出生児数 ------------

_WIFE_AGE_HEADER: dict[int, str] = {
    1: "年次",
    2: "(調査回)",
    3: "総数",
    4: "20~24歳",
    5: "25~29歳",
    6: "30~34歳",
    7: "35~39歳",
    8: "40~44歳",
    9: "45~49歳",
}
_ROUND = re.compile(r"^\(第(\d+)回\)$")


def _wife_age_rows(rows: Rows, code: str, title: str, metric: str) -> list[dict[str, object]]:
    _title(rows, title, code)
    h = _header_row(rows, "年次", code)
    _check_header(rows[h], _WIFE_AGE_HEADER, code)
    out: list[dict[str, object]] = []
    years: list[int] = []
    rounds: list[int] = []
    for r in rows[h + 1 :]:
        year = _int(r.get(1))
        if year is None:
            break
        m = _ROUND.match(_norm(r.get(2)))
        if m is None:
            msg = f"{code} {year}: survey round label {r.get(2)!r} not recognised"
            raise ValueError(msg)
        years.append(year)
        rounds.append(int(m.group(1)))
        for col, group in zip(range(3, 10), WIFE_AGE_GROUPS, strict=True):
            if col not in r:
                msg = f"{code} {year}: column {col} ({group}) is empty"
                raise ValueError(msg)
            out.append(_survey_row(year, metric, group, None, _num(r[col], f"{code} {year}"), code))
    if tuple(years) != SURVEY_YEARS:
        msg = f"{code}: survey years must be {SURVEY_YEARS}, got {tuple(years)}"
        raise ValueError(msg)
    if tuple(rounds) != SURVEY_ROUNDS:
        msg = f"{code}: survey rounds must be 第7回..第16回, got {rounds}"
        raise ValueError(msg)
    return out


def planned_children_rows(rows: Rows) -> list[dict[str, object]]:
    """T04-25: metric ``planned_children`` x (総数, 妻 20-24 … 45-49) x 10 surveys."""
    return _wife_age_rows(
        rows, "T04-25", "表4-25妻の年齢(5歳階級)別予定子ども数", "planned_children"
    )


def children_born_rows(rows: Rows) -> list[dict[str, object]]:
    """T04-24: metric ``children_born`` x (総数, 妻 20-24 … 45-49) x 10 surveys."""
    return _wife_age_rows(rows, "T04-24", "表4-24妻の年齢(5歳階級)別平均出生児数", "children_born")


# ---- T04-23: 妻の生まれ年別 出生児数割合・平均出生児数（完結出生児数） -------------

_COHORT_LABEL = re.compile(r"^(\d{4})[~-](\d{4})$")
_FIRST_COHORT = 1890
_LAST_COHORT = 1971
_SHARE_TOL = 0.3


def completed_fertility_rows(rows: Rows) -> list[dict[str, object]]:
    """T04-23: ``completed_fertility`` (group 妻の生まれ年 YYYY-YYYY) and ``completed_parity_share``
    (無子 / 1人 / 2人 / 3人 / 4人以上, %) per wife birth cohort; ``birth_cohort`` = lower bound."""
    code = "T04-23"
    _title(rows, "表4-23妻の生まれ年別出生児数割合および平均出生児数", code)
    h = _header_row(rows, "妻の生まれ年", code)
    _check_header(
        rows[h], {1: "妻の生まれ年", 3: "調査", 4: "出生児数割合(%)", 9: "平均出生"}, code
    )
    _check_header(
        rows[h + 1],
        {3: "年次", 4: "無子", 5: "1人", 6: "2人", 7: "3人", 8: "4人以上", 9: "児数(人)"},
        code,
    )
    out: list[dict[str, object]] = []
    cohorts: list[int] = []
    last_survey = 0
    for r in rows[h + 2 :]:
        label = _norm(r.get(1))
        if not label:
            continue
        m = _COHORT_LABEL.match(label)
        if m is None:
            if cohorts:
                break  # note rows after the data
            msg = f"{code}: cohort label {label!r} not recognised"
            raise ValueError(msg)
        lo, hi = int(m.group(1)), int(m.group(2))
        survey = _int(r.get(3))
        if survey is None:
            msg = f"{code} {label}: survey year {r.get(3)!r} not recognised"
            raise ValueError(msg)
        if survey < last_survey:
            msg = f"{code} {label}: survey year {survey} goes backwards (after {last_survey})"
            raise ValueError(msg)
        last_survey = survey
        where = f"{code} {label}"
        shares = [_num(r.get(c), where) for c in range(4, 9)]
        if abs(sum(shares) - 100.0) > _SHARE_TOL:
            msg = f"{where}: parity shares sum to {sum(shares):.1f}, not 100"
            raise ValueError(msg)
        group = f"妻の生まれ年 {lo}-{hi}"
        out.append(
            _survey_row(survey, "completed_fertility", group, lo, _num(r.get(9), where), code)
        )
        for pg, v in zip(PARITY_GROUPS, shares, strict=True):
            out.append(_survey_row(survey, "completed_parity_share", pg, lo, v, code))
        cohorts.append(lo)
    if not cohorts or cohorts[0] != _FIRST_COHORT or cohorts[-1] != _LAST_COHORT:
        msg = f"{code}: cohorts must run {_FIRST_COHORT}…{_LAST_COHORT}, got {cohorts}"
        raise ValueError(msg)
    return out


# ---- T04-15: 出生順位別出生数および割合 -------------------------------------------------------

_ORDER_HEADER: dict[int, str] = {
    1: "年次",
    3: "総数",
    4: "第1子",
    5: "第2子",
    6: "第3子",
    7: "第4子",
    8: "第5子~",
}
_BIRTHS_FIRST = 1950
_BIRTHS_LAST = 2024


def births_order_rows(rows: Rows) -> list[dict[str, object]]:
    """T04-15: ``births`` (counts, 1950–2024 as printed) and ``births_share`` (%, selected years)
    by birth order. 総数 includes unknown order, so 総数 >= Σ orders; share 総数 must be 100."""
    code = "T04-15"
    _title(rows, "表4-15出生順位別出生数および割合", code)
    h = _header_row(rows, "年次", code)
    _check_header(rows[h], _ORDER_HEADER, code)
    out: list[dict[str, object]] = []
    block: str | None = None
    years: list[int] = []
    share_years: list[int] = []
    for r in rows[h + 1 :]:
        marker = _norm(r.get(3))
        if marker == "実数":
            block = "births"
            continue
        if marker == "割合(%)":
            block = "births_share"
            continue
        year = _int(r.get(1))
        if year is None or block is None:
            continue
        where = f"{code} {year} ({block})"
        values = [_num(r.get(c), where) for c in range(3, 9)]
        if block == "births":
            if years and year <= years[-1]:
                msg = (
                    f"{code}: count years must increase, got {year} after {years[-1]} "
                    "(share block marker 割合 missing?)"
                )
                raise ValueError(msg)
            ints = [round(v) for v in values]
            if ints[0] < sum(ints[1:]):
                msg = f"{where}: total {ints[0]} smaller than the sum of orders {sum(ints[1:])}"
                raise ValueError(msg)
            years.append(year)
            for g, v in zip(ORDER_GROUPS, ints, strict=True):
                out.append(_births_row(year, "births", g, None, v, code))
        else:
            if values[0] != 100.0:
                msg = f"{where}: share total must be 100, got {values[0]}"
                raise ValueError(msg)
            share_years.append(year)
            for g, share in zip(ORDER_GROUPS, values, strict=True):
                out.append(_births_row(year, "births_share", g, None, share, code))
    for label, ys in (("count", years), ("share", share_years)):
        if not ys:
            msg = f"{code}: {label} block ({'実数' if label == 'count' else '割合'}) not found"
            raise ValueError(msg)
        if ys != sorted(set(ys)) or ys[0] != _BIRTHS_FIRST or ys[-1] != _BIRTHS_LAST:
            msg = (
                f"{code}: {label} years must increase from {_BIRTHS_FIRST} to "
                f"{_BIRTHS_LAST}, got {ys}"
            )
            raise ValueError(msg)
    return out


# ---- T04-16: 出生順位別合計特殊出生率および平均出生年齢 -----------------------------------------

_TFR_SUM_TOL = 0.05  # 1950-64 and 1966-67 orders come from 5-year age groups (gap <= 0.03)
_MISSING = ("…", "...")  # NFKC turns U+2026 into three dots


def tfr_order_rows(rows: Rows) -> list[dict[str, object]]:
    """T04-16★: ``tfr_order`` and ``mean_age_order`` by birth order, every year 1950–2024.
    '…' cells (orders not published for 1951–1953) produce no row."""
    code = "T04-16"
    _title(rows, "表4-16出生順位別合計特殊出生率および平均出生年齢", code)
    h = _header_row(rows, "年次", code)
    _check_header(rows[h], {1: "年次", 2: "合計特殊出生率", 8: "平均出生年齢(歳)"}, code)
    sub = {
        c: g.replace("第5子以上", "第5子~") for c, g in zip(range(2, 8), ORDER_GROUPS, strict=True)
    }
    sub |= {c + 6: g for c, g in sub.items()}
    _check_header(rows[h + 1], sub, code)
    out: list[dict[str, object]] = []
    years: list[int] = []
    for r in rows[h + 2 :]:
        year = _int(r.get(1))
        if year is None:
            if years:
                break
            continue
        years.append(year)
        for metric, first_col in (("tfr_order", 2), ("mean_age_order", 8)):
            values: list[float | None] = []
            for c in range(first_col, first_col + 6):
                cell = r.get(c)
                if _norm(cell) in _MISSING:
                    values.append(None)
                else:
                    values.append(_num(cell, f"{code} {year} {metric}"))
            total, orders = values[0], values[1:]
            if metric == "tfr_order" and total is not None and all(o is not None for o in orders):
                s = sum(o for o in orders if o is not None)
                if abs(s - total) > _TFR_SUM_TOL:
                    msg = f"{code} {year}: order TFRs sum to {s:.2f}, total is {total}"
                    raise ValueError(msg)
            for g, v in zip(ORDER_GROUPS, values, strict=True):
                if v is not None:
                    out.append(_births_row(year, metric, g, None, v, code))
    expected = list(range(_BIRTHS_FIRST, _BIRTHS_LAST + 1))
    if years != expected:
        msg = f"{code}: years must be {_BIRTHS_FIRST}-{_BIRTHS_LAST} consecutive, got {years}"
        raise ValueError(msg)
    return out


# ---- T04-09 / T04-11: 年齢各歳別出生率 / コーホート別累積出生率 (age x year grids) ------

_YEAR_LABEL = re.compile(r"^(\d{4})年$")
_ASFR_FIXED_YEARS = (1925, 1930, 1940)
_ASFR_FIRST_ANNUAL = 1947
_COHORT_FIRST = 1950
_COHORT_LAST = 2020
_TOTAL_TOL = 5e-4


def _grid(rows: Rows, code: str) -> tuple[int, list[tuple[int, int]], list[dict[int, str]]]:
    """Header index, [(column, year)], and the 35 age rows (15..49) of an age x year sheet."""
    h = _header_row(rows, "年齢", code)
    cols: list[tuple[int, int]] = []
    for c in sorted(rows[h]):
        if c == 1:
            continue
        m = _YEAR_LABEL.match(_norm(rows[h][c]))
        if m is None:
            msg = f"{code}: column {c} header {rows[h][c]!r} is not a year"
            raise ValueError(msg)
        cols.append((c, int(m.group(1))))
    age_rows = rows[h + 1 : h + 1 + len(AGES)]
    ages = [_norm(r.get(1)) for r in age_rows]
    if ages != [str(a) for a in AGES]:
        msg = f"{code}: age rows must be 15..49 in order, got {ages}"
        raise ValueError(msg)
    return h, cols, list(age_rows)


def asfr_rows(rows: Rows) -> list[dict[str, object]]:
    """T04-09★: ``asfr`` (group ``age 15``..``age 49``) per calendar year 1925/1930/1940 and
    1947–2024. The 合計 row (= TFR) must equal each column's sum."""
    code = "T04-09"
    _title(rows, "表4-9女性の年齢(各歳)別出生率", code)
    h, cols, age_rows = _grid(rows, code)
    years = [y for _, y in cols]
    annual = years[len(_ASFR_FIXED_YEARS) :]
    if tuple(years[: len(_ASFR_FIXED_YEARS)]) != _ASFR_FIXED_YEARS or annual != list(
        range(_ASFR_FIRST_ANNUAL, annual[-1] + 1 if annual else _ASFR_FIRST_ANNUAL)
    ):
        msg = (
            f"{code}: years must be {_ASFR_FIXED_YEARS} then consecutive from "
            f"{_ASFR_FIRST_ANNUAL}, got {years}"
        )
        raise ValueError(msg)
    total_row = rows[h + 1 + len(AGES)] if len(rows) > h + 1 + len(AGES) else {}
    if _norm(total_row.get(1)) != "合計":
        msg = f"{code}: 合計 row not found after the age rows"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for c, year in cols:
        s = 0.0
        for age, r in zip(AGES, age_rows, strict=True):
            v = _num(r.get(c), f"{code} year {year} age {age}")
            s += v
            out.append(_births_row(year, "asfr", f"age {age}", None, v, code))
        total = _num(total_row.get(c), f"{code} year {year} 合計")
        if abs(s - total) > _TOTAL_TOL:
            msg = f"{code} year {year}: 合計 {total} differs from the column sum {s:.5f}"
            raise ValueError(msg)
    return out


def cohort_rows(rows: Rows) -> list[dict[str, object]]:
    """T04-11★: ``cohort_cum_fertility`` (group ``age 15``..``age 49``). Column label = year the
    cohort turned 15 (1950–2020) -> ``cohort`` = label − 15 (birth year), ``year`` = cohort + age.
    Blank cells (ages not yet reached) produce no row; a column must not decrease with age."""
    code = "T04-11"
    _title(rows, "表4-11女性のコーホート別累積出生率", code)
    _, cols, age_rows = _grid(rows, code)
    years = [y for _, y in cols]
    if years != list(range(_COHORT_FIRST, _COHORT_LAST + 1)):
        msg = f"{code}: columns must be {_COHORT_FIRST}-{_COHORT_LAST} consecutive, got {years}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for c, label in cols:
        cohort = label - 15
        prev: float | None = None
        ended = False
        for age, r in zip(AGES, age_rows, strict=True):
            cell = r.get(c)
            if cell is None or not _norm(cell):
                ended = True
                continue
            if ended:
                msg = f"{code} column {label}: value at age {age} after a blank cell"
                raise ValueError(msg)
            v = _num(cell, f"{code} column {label} age {age}")
            if prev is not None and v < prev:
                msg = (
                    f"{code} column {label}: cumulative rate decreases at age {age} ({v} < {prev})"
                )
                raise ValueError(msg)
            prev = v
            out.append(
                _births_row(cohort + age, "cohort_cum_fertility", f"age {age}", cohort, v, code)
            )
    return out


# ---- dispatch ------------------------------------------------------------------------------

_PARSERS: dict[str, Callable[[Rows], list[dict[str, object]]]] = {
    "T04-25": planned_children_rows,
    "T04-24": children_born_rows,
    "T04-23": completed_fertility_rows,
    "T04-15": births_order_rows,
    "T04-16": tfr_order_rows,
    "T04-09": asfr_rows,
    "T04-11": cohort_rows,
}


def parse_table(payload: bytes, table: Table) -> list[dict[str, object]]:
    """xlsx bytes -> long rows of *table* (``ValueError`` on any layout mismatch). Tables that
    read several sheets (``_PAYLOAD_PARSERS``) get the payload; the rest get ``table.sheet``."""
    if table.code in _PAYLOAD_PARSERS:
        return _PAYLOAD_PARSERS[table.code](payload)
    return _PARSERS[table.code](sheet_rows(payload, table.sheet))


# ---- 第16回出生動向基本調査 結果の概要 PDF: 図表 7-1 / 図表 3-3 data labels ----------

PDF_TABLE_COUPLES = "JNFS16-7-1"
PDF_TABLE_SINGLES = "JNFS16-3-3"
# Anchored at both ends so the table-of-contents entries (dot leaders + page number) do not match.
_FIG71 = re.compile(r"^図表\s*7-1\s*調査別にみた、夫婦の平均理想子ども数と平均予定子ども数$")
_FIG33 = re.compile(r"^図表\s*3-3\s*調査別にみた、未婚者の平均希望子ども数$")
_LABEL = re.compile(r"\d\.\d{2}")
_NOTE_ENTRY = re.compile(r"第(\d+)回\((\d{4})\)(\d\.\d{2})")
# Published anchors (IPSS, 第16回 結果の概要): first and last point of every series.
_ANCHORS: dict[str, tuple[float, float]] = {
    "ideal": (2.61, 2.25),
    "planned": (2.17, 2.01),
    "men": (2.33, 1.82),
    "women": (2.28, 1.79),
    "ideal_u35": (2.52, 2.29),
    "planned_u35": (2.18, 2.17),
}


def _lines(page: str) -> list[str]:
    out: list[str] = []
    for raw in unicodedata.normalize("NFKC", page).splitlines():
        line = " ".join(raw.split())
        if line:
            out.append(line)
    return out


def _figure_labels(pages: Sequence[str], title: re.Pattern[str], what: str, n: int) -> list[float]:
    """Decimal labels (d.dd) printed between the figure title and the first axis tick '0'."""
    for page in pages:
        lines = _lines(page)
        for i, line in enumerate(lines):
            if title.match(line):
                body: list[str] = []
                for nxt in lines[i + 1 :]:
                    if nxt == "0":
                        break
                    body.append(nxt)
                labels = [float(t) for t in _LABEL.findall(" ".join(body))]
                if len(labels) != n:
                    msg = f"figure {what}: expected {n} data labels, got {len(labels)}"
                    raise ValueError(msg)
                return labels
    msg = f"figure {what} not found in any page"
    raise ValueError(msg)


def _check_anchor(name: str, series: Sequence[float], what: str, rounds: Sequence[int]) -> None:
    first, last = _ANCHORS[name]
    if series[0] != first:
        msg = f"figure {what}: 第{rounds[0]}回 {name} label {series[0]} != published {first}"
        raise ValueError(msg)
    if series[-1] != last:
        msg = f"figure {what}: 第{rounds[-1]}回 {name} label {series[-1]} != published {last}"
        raise ValueError(msg)


def _note_series(text: str, start: str, end: str, what: str) -> list[float]:
    i = text.find(start)
    j = text.find(end, i + len(start)) if i >= 0 else -1
    if i < 0 or j < 0:
        msg = f"figure 7-1 note (妻35歳未満): segment {start!r}…{end!r} not found"
        raise ValueError(msg)
    entries = _NOTE_ENTRY.findall(text[i + len(start) : j])
    rounds = tuple(int(r) for r, _, _ in entries)
    years = tuple(int(y) for _, y, _ in entries)
    if rounds != SURVEY_ROUNDS or years != SURVEY_YEARS:
        msg = (
            f"figure 7-1 note (妻35歳未満): expected rounds 7..16 / years {SURVEY_YEARS} for "
            f"{what}, got {len(entries)} entries {list(zip(rounds, years, strict=True))}"
        )
        raise ValueError(msg)
    return [float(v) for _, _, v in entries]


def survey_pdf_rows_from_pages(pages: Sequence[str]) -> list[dict[str, object]]:
    """Rows: ideal_children / planned_children_pdf (夫婦; 夫婦（妻35歳未満） from the note) for
    1977–2021 and desired_children_single (未婚男性 / 未婚女性) for 1982–2021. Label counts and
    the 7th- and 16th-round anchors are verified; any mismatch raises ``ValueError``."""
    labels = _figure_labels(pages, _FIG71, "7-1", 2 * len(SURVEY_YEARS))
    ideal, planned = labels[: len(SURVEY_YEARS)], labels[len(SURVEY_YEARS) :]
    _check_anchor("ideal", ideal, "7-1", SURVEY_ROUNDS)
    _check_anchor("planned", planned, "7-1", SURVEY_ROUNDS)
    singles = _figure_labels(pages, _FIG33, "3-3", 2 * len(SINGLE_YEARS))
    men, women = singles[: len(SINGLE_YEARS)], singles[len(SINGLE_YEARS) :]
    _check_anchor("men", men, "3-3", SURVEY_ROUNDS[1:])
    _check_anchor("women", women, "3-3", SURVEY_ROUNDS[1:])
    page71 = next(p for p in pages if any(_FIG71.match(ln) for ln in _lines(p)))
    text = _norm(page71)
    note = text[text.find("妻の年齢を35歳未満に限定すると") :]
    ideal_u35 = _note_series(note, "平均理想子ども数は", "平均予定子ども数は", "ideal")
    planned_u35 = _note_series(note, "平均予定子ども数は", "である", "planned")
    _check_anchor("ideal_u35", ideal_u35, "7-1 note", SURVEY_ROUNDS)
    _check_anchor("planned_u35", planned_u35, "7-1 note", SURVEY_ROUNDS)
    out: list[dict[str, object]] = []
    for y, i, p, iu, pu in zip(SURVEY_YEARS, ideal, planned, ideal_u35, planned_u35, strict=True):
        out.append(_survey_row(y, "ideal_children", COUPLE, None, i, PDF_TABLE_COUPLES))
        out.append(_survey_row(y, "planned_children_pdf", COUPLE, None, p, PDF_TABLE_COUPLES))
        out.append(_survey_row(y, "ideal_children", COUPLE_U35, None, iu, PDF_TABLE_COUPLES))
        out.append(_survey_row(y, "planned_children_pdf", COUPLE_U35, None, pu, PDF_TABLE_COUPLES))
    for y, m, w in zip(SINGLE_YEARS, men, women, strict=True):
        out.append(
            _survey_row(y, "desired_children_single", SINGLE_MEN, None, m, PDF_TABLE_SINGLES)
        )
        out.append(
            _survey_row(y, "desired_children_single", SINGLE_WOMEN, None, w, PDF_TABLE_SINGLES)
        )
    return out


def survey_pdf_rows(payload: bytes) -> list[dict[str, object]]:
    return survey_pdf_rows_from_pages(pdf_text(payload))


# ---- marts ---------------------------------------------------------------------------------


def group_order(group: str) -> int:
    """Sort rank of a births-mart group: 総数, 第1子…第5子以上, then ``age N`` by age."""
    if group in ORDER_GROUPS:
        return ORDER_GROUPS.index(group)
    if group.startswith("age "):
        return 100 + int(group[4:])
    msg = f"unknown births group {group!r}"
    raise ValueError(msg)


def _combine(
    parts: dict[str, Sequence[dict[str, object]]],
    key: Callable[[dict[str, object]], tuple[object, ...]],
    name: str,
) -> list[dict[str, object]]:
    out = sorted((dict(r) for rows in parts.values() for r in rows), key=key)
    keys = [key(r) for r in out]
    if len(keys) != len(set(keys)):
        dup = next(k for i, k in enumerate(keys) if k in keys[:i])
        msg = f"duplicate key {name} = {dup}"
        raise ValueError(msg)
    return out


def build_survey_mart(parts: dict[str, Sequence[dict[str, object]]]) -> list[dict[str, object]]:
    """``marts/jp_fertility_survey``: staged tables combined, sorted by (survey_year, metric,
    group, birth_cohort); duplicate keys raise ``ValueError``. Pure and deterministic."""

    def key(r: dict[str, object]) -> tuple[object, ...]:
        bc = r["birth_cohort"]
        return (
            int(str(r["survey_year"])),
            SURVEY_METRICS.index(str(r["metric"])),
            str(r["group"]),
            -1 if bc is None else int(str(bc)),
        )

    return _combine(parts, key, "(survey_year, metric, group, birth_cohort)")


def build_births_mart(parts: dict[str, Sequence[dict[str, object]]]) -> list[dict[str, object]]:
    """``marts/jp_births_order_cohort``: sorted by (year, metric, group, cohort); duplicate keys
    raise ``ValueError``."""

    def key(r: dict[str, object]) -> tuple[object, ...]:
        co = r["cohort"]
        return (
            int(str(r["year"])),
            BIRTHS_METRICS.index(str(r["metric"])),
            group_order(str(r["group"])),
            -1 if co is None else int(str(co)),
        )

    return _combine(parts, key, "(year, metric, group, cohort)")


# ============================================================================================
# ---- H10: 婚姻時系列 (T06-24 / T06-12 / T06-23) と 都道府県表 (T12-33★ … T12-53) -----------
# ============================================================================================

# H12 T06-01★ (appended after the H10 / H11 metrics so the mart order of earlier rows is unchanged)
FIRST_MARRIAGE_METRICS: tuple[str, ...] = (
    "marriages_total",
    "first_marriages_husband",
    "remarriages_husband",
    "first_marriages_wife",
    "remarriages_wife",
    "first_marriage_share_husband_pct",
    "first_marriage_share_wife_pct",
    "crude_marriage_rate",
)
MARRIAGE_METRICS: tuple[str, ...] = (
    "never_married_share",
    "mean_age_marriage_all",
    "mean_age_first_marriage",
    "never_married_at_50",
    # H11 (appended so the mart order of the earlier rows is unchanged)
    "married_share",
    "widowed_share",
    "divorced_share",
    *FIRST_MARRIAGE_METRICS,
)
SEX_LABELS: dict[str, str] = {"男": "M", "女": "F"}
CENSUS_YEARS: tuple[int, ...] = (
    1920,
    1930,
    1950,
    1960,
    1970,
    1980,
    1990,
    2000,
    2010,
    2015,
    2020,
)
AGE_CLASSES_5Y: tuple[str, ...] = (
    "total",
    *(f"{a}-{a + 4}" for a in range(15, 85, 5)),
    "85-",
)
_YEAR_CELL = re.compile(r"^(\d{4})年?(?:\d\)|\*)?$")  # '1950年1)', '2015年*', '2015*', '1951'
_AGE_CELL = re.compile(r"^(\d{2})~(\d{2})$")


def _year_cell(text: str | None) -> int | None:
    m = _YEAR_CELL.match(_norm(text))
    return int(m.group(1)) if m else None


def _year_columns(row: dict[int, str], cols: Sequence[int], code: str) -> list[int]:
    out: list[int] = []
    for c in cols:
        y = _year_cell(row.get(c))
        if y is None:
            msg = f"{code}: header column {c} is {row.get(c)!r}, not a year"
            raise ValueError(msg)
        out.append(y)
    return out


def _expect_years(got: Sequence[int], want: Sequence[int], code: str) -> None:
    if tuple(got) != tuple(want):
        msg = f"{code}: header years must be {tuple(want)}, got {tuple(got)}"
        raise ValueError(msg)


def _age_class(text: str | None) -> str | None:
    s = _norm(text)
    if s.startswith("総数"):
        return "total"
    if s == "85歳以上":
        return "85-"
    m = _AGE_CELL.match(s)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def _marriage_row(
    year: int, metric: str, sex: str, age_class: str | None, value: float, table: str
) -> dict[str, object]:
    return {
        "year": year,
        "metric": metric,
        "sex": sex,
        "age_class": age_class,
        "value": value,
        "table": table,
        "source": SOURCE,
    }


def _opt_num(text: str | None, where: str) -> float | None:
    """Float of a cell, ``None`` for the not-published marks ('…', '...')."""
    if _norm(text) in _MISSING:
        return None
    return _num(text, where)


# ---- T06-24(1)–(4): 性，年齢（5 歳階級），配偶関係別割合 — 未婚 / 有配偶 / 死別 / 離別 ----------

# (sheet number, label after "(n)", metric). Sheet (1) is H10, (2)–(4) are H11; same layout.
_MARITAL_SHEETS: tuple[tuple[int, str, str], ...] = (
    (1, "未婚", "never_married_share"),
    (2, "有配偶", "married_share"),
    (3, "死別", "widowed_share"),
    (4, "離別", "divorced_share"),
)
MARITAL_STATUS_METRICS: tuple[str, ...] = tuple(m for _, _, m in _MARITAL_SHEETS)
_SHARE_SUM_TOL = 0.3
_ERROR_CELL = "#DIV/0!"  # 1950 85歳以上 on sheets (2)–(4): the census did not tabulate it


def _marital_share_rows(rows: Rows, n: int, label: str, metric: str) -> list[dict[str, object]]:
    """One T06-24 sheet ``(n) <label>``: *metric* (%) by sex x 16 age classes (total, 15-19 …
    80-84, 85-) for the 11 census years 1920–2020 (1940 not published). A '…' or ``#DIV/0!``
    cell gives no row; any other non-numeric cell is a ``ValueError``."""
    code = "T06-24"
    _title(rows, "表6-24性,年齢(5歳階級),配偶関係別割合", code)
    got = _norm(rows[1].get(1)) if len(rows) > 1 else ""
    if not got.startswith(f"({n}){label}"):
        msg = f"{code}: sheet ({n}) {label} expected, got {got!r}"
        raise ValueError(msg)
    h = _header_row(rows, "年齢", code)
    _expect_years(_year_columns(rows[h], range(2, 13), code), CENSUS_YEARS, code)
    out: list[dict[str, object]] = []
    i = h + 1
    for sex_label, sex in SEX_LABELS.items():
        if i >= len(rows) or _norm(rows[i].get(2)) != sex_label or rows[i].get(1):
            msg = f"{code}: sex marker row {sex_label!r} expected at row {i}"
            raise ValueError(msg)
        block = rows[i + 1 : i + 1 + len(AGE_CLASSES_5Y)]
        ages = [_age_class(r.get(1)) for r in block]
        if ages != list(AGE_CLASSES_5Y):
            msg = f"{code} {sex_label}: age rows must be {AGE_CLASSES_5Y}, got {ages}"
            raise ValueError(msg)
        for r, ac in zip(block, AGE_CLASSES_5Y, strict=True):
            for c, year in zip(range(2, 13), CENSUS_YEARS, strict=True):
                if _norm(r.get(c)) in (*_MISSING, _ERROR_CELL):
                    continue
                v = _num(r.get(c), f"{code} ({n}) {sex_label} {ac} {year}")
                out.append(_marriage_row(year, metric, sex, ac, v, code))
        i += 1 + len(AGE_CLASSES_5Y)
    return out


def never_married_share_rows(rows: Rows) -> list[dict[str, object]]:
    """T06-24 sheet (1) 未婚 only: ``never_married_share`` (H10)."""
    n, label, metric = _MARITAL_SHEETS[0]
    return _marital_share_rows(rows, n, label, metric)


def _check_share_sums(rows: Sequence[dict[str, object]], code: str) -> None:
    """The four marital-status shares of a (year, sex, age class) add to 100 ± 0.3 wherever all
    four are published (rounding leaves 99.9–100.1 in the 2026 file)."""
    cells: dict[tuple[object, object, object], dict[str, float]] = {}
    for r in rows:
        key = (r["year"], r["sex"], r["age_class"])
        cells.setdefault(key, {})[str(r["metric"])] = float(str(r["value"]))
    for (year, sex, ac), shares in cells.items():
        if len(shares) < len(MARITAL_STATUS_METRICS):
            continue
        total = sum(shares.values())
        if abs(total - 100) > _SHARE_SUM_TOL:
            msg = (
                f"{code}: shares of {sex} {ac} {year} sum to {total:.1f}, not 100 "
                f"(±{_SHARE_SUM_TOL}): {shares}"
            )
            raise ValueError(msg)


def marital_status_share_rows(payload: bytes) -> list[dict[str, object]]:
    """T06-24 sheets (1)–(4): ``never_married_share`` / ``married_share`` / ``widowed_share`` /
    ``divorced_share`` (%) by sex x age class x census year, checked to add to 100 (H11)."""
    code = "T06-24"
    out: list[dict[str, object]] = []
    for n, label, metric in _MARITAL_SHEETS:
        out += _marital_share_rows(sheet_rows(payload, f"{code}({n})"), n, label, metric)
    _check_share_sums(out, code)
    return out


# ---- T06-12: 全婚姻および初婚の平均婚姻年齢 (two column blocks: 1899–1989 | 1990–) ------------

_T0612_COLS: tuple[tuple[int, str, str], ...] = (
    (2, "mean_age_marriage_all", "M"),
    (3, "mean_age_marriage_all", "F"),
    (5, "mean_age_first_marriage", "M"),
    (6, "mean_age_first_marriage", "F"),
)
_T0612_FIRST_YEAR = 1899
_T0612_RIGHT_OFFSET = 7


def mean_marriage_age_rows(rows: Rows) -> list[dict[str, object]]:
    """T06-12: ``mean_age_marriage_all`` / ``mean_age_first_marriage`` by sex (歳). The sheet
    prints two blocks side by side (年次 in A and H); the right block must continue the left
    one year by year. '…' produces no row."""
    code = "T06-12"
    _title(rows, "表6-12全婚姻および初婚の平均婚姻年齢", code)
    h = _header_row(rows, "年次", code)
    _check_header(
        rows[h], {1: "年次", 3: "全婚姻", 6: "初婚", 8: "年次", 10: "全婚姻", 13: "初婚"}, code
    )
    sub = {2: "夫", 3: "妻", 4: "年齢差", 5: "夫", 6: "妻", 7: "年齢差"}
    _check_header(rows[h + 1], sub | {c + _T0612_RIGHT_OFFSET: g for c, g in sub.items()}, code)
    left: list[tuple[int, dict[int, str]]] = []
    right: list[tuple[int, dict[int, str]]] = []
    for r in rows[h + 2 :]:
        y = _int(r.get(1))
        if y is None:
            break
        left.append((y, r))
        yr = _int(r.get(1 + _T0612_RIGHT_OFFSET))
        if yr is not None:
            right.append((yr, r))
    years_l = [y for y, _ in left]
    if not years_l or years_l[0] != _T0612_FIRST_YEAR or years_l != sorted(set(years_l)):
        msg = f"{code}: left block years must increase from {_T0612_FIRST_YEAR}, got {years_l}"
        raise ValueError(msg)
    years_r = [y for y, _ in right]
    want_r = list(range(years_l[-1] + 1, years_l[-1] + 1 + len(years_r)))
    if not years_r or years_r != want_r:
        msg = f"{code}: right block must run {want_r[0]}…{want_r[-1]} consecutively, got {years_r}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for block, offset in ((left, 0), (right, _T0612_RIGHT_OFFSET)):
        for year, r in block:
            for c, metric, sex in _T0612_COLS:
                v = _opt_num(r.get(c + offset), f"{code} {year} {metric} {sex}")
                if v is not None:
                    out.append(_marriage_row(year, metric, sex, None, v, code))
    return out


# ---- T06-23: 性別 50 歳時の未婚割合 ----------------------------------------------------------

_T0623_YEARS: tuple[int, ...] = (1920, 1930, 1940, *CENSUS_YEARS[2:])


def never_married_at_50_rows(rows: Rows) -> list[dict[str, object]]:
    """T06-23: ``never_married_at_50`` (%) by sex for the 12 census years 1920–2020 (the
    有配偶 / 死別 / 離別 columns are not kept)."""
    code = "T06-23"
    _title(rows, "表6-23性別50歳時の未婚割合", code)
    h = _header_row(rows, "年次", code)
    _check_header(rows[h], {1: "年次", 2: "男", 6: "女"}, code)
    _check_header(rows[h + 1], {2: "未婚", 3: "有配偶", 6: "未婚", 7: "有配偶"}, code)
    out: list[dict[str, object]] = []
    years: list[int] = []
    for r in rows[h + 2 :]:
        y = _year_cell(r.get(1))
        if y is None:
            break
        years.append(y)
        for c, sex in ((2, "M"), (6, "F")):
            v = _num(r.get(c), f"{code} {y} {sex}")
            out.append(_marriage_row(y, "never_married_at_50", sex, None, v, code))
    if tuple(years) != _T0623_YEARS:
        msg = f"{code}: years must be {_T0623_YEARS}, got {years}"
        raise ValueError(msg)
    return out


# ---- T12-NN: 都道府県表 (全国 + 47 prefectures in JIS order) --------------------------------


def _pref_header(rows: Rows, code: str, title: str) -> int:
    _title(rows, title, code)
    return _header_row(rows, "都道府県", code)


def _pref_label(r: dict[int, str]) -> str | None:
    return r.get(1)


def _pref_year_grid(
    rows: Rows,
    start: int,
    code: str,
    cols_years: Sequence[tuple[int, int]],
    metric: str,
    sex: str,
    age_class: str | None,
) -> list[dict[str, object]]:
    """Region rows from *start*: (column, year) cells -> metric rows; '…' produces no row."""
    out: list[dict[str, object]] = []
    for pc, r in prefecture.regions(rows, start, code, _pref_label):
        for c, year in cols_years:
            v = _opt_num(r.get(c), f"{code} {prefecture.pref_name(pc)} {year} {metric} {sex}")
            if v is not None:
                out.append(prefecture.panel_row(pc, year, metric, sex, age_class, v, code, SOURCE))
    return out


_T1233_FIXED: tuple[int, ...] = (1925, 1930)
_T1233_FIRST_ANNUAL = 1950


def pref_tfr_rows(rows: Rows) -> list[dict[str, object]]:
    """T12-33★: ``tfr`` per prefecture, columns 1925, 1930 and every year 1950–. The unnamed
    全国 row (5-year-class computation, in parentheses) right under 全国 has no label: skipped."""
    code = "T12-33"
    h = _pref_header(rows, code, "表12-33都道府県別合計特殊出生率")
    cols = [c for c in sorted(rows[h]) if c > 1]
    years = _year_columns(rows[h], cols, code)
    annual = years[len(_T1233_FIXED) :]
    if tuple(years[: len(_T1233_FIXED)]) != _T1233_FIXED or annual != list(
        range(_T1233_FIRST_ANNUAL, _T1233_FIRST_ANNUAL + len(annual))
    ):
        msg = f"{code}: header years must be {_T1233_FIXED} then consecutive from 1950, got {years}"
        raise ValueError(msg)
    return _pref_year_grid(rows, h + 1, code, list(zip(cols, years, strict=True)), "tfr", "T", None)


_T1235_YEARS: tuple[int, ...] = (1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2024)


def _sex_sheets(payload: bytes, code: str) -> list[tuple[str, list[dict[int, str]]]]:
    """[(sex, rows)] of the sheets ``<code>(1)`` 男 and ``<code>(2)`` 女."""
    out: list[tuple[str, list[dict[int, str]]]] = []
    for n, (label, sex) in enumerate(SEX_LABELS.items(), start=1):
        rows = sheet_rows(payload, f"{code}({n})")
        cell = _norm(rows[1].get(1)) if len(rows) > 1 else ""
        if not cell.startswith(f"({n}){label}"):
            msg = f"{code}({n}): sheet label ({n}){label} expected, got {cell!r}"
            raise ValueError(msg)
        out.append((sex, rows))
    return out


def pref_first_marriage_age_rows(payload: bytes) -> list[dict[str, object]]:
    """T12-35 sheets (1) 男 / (2) 女: ``mean_age_first_marriage`` (歳) for 1950…2020, 2024."""
    code = "T12-35"
    out: list[dict[str, object]] = []
    for sex, rows in _sex_sheets(payload, code):
        h = _pref_header(rows, code, "表12-35都道府県,性別平均初婚年齢")
        _expect_years(_year_columns(rows[h], range(2, 11), code), _T1235_YEARS, code)
        cols = list(zip(range(2, 11), _T1235_YEARS, strict=True))
        out += _pref_year_grid(rows, h + 1, code, cols, "mean_age_first_marriage", sex, None)
    return out


_T1236_YEARS: tuple[int, ...] = (1970, 1990, 2010, 2015, 2020)


def pref_never_married_young_rows(rows: Rows) -> list[dict[str, object]]:
    """T12-36: ``never_married_m30_34`` (男 30–34 歳) and ``never_married_f25_29`` (女 25–29 歳)
    (%) for 1970, 1990, 2010, 2015, 2020."""
    code = "T12-36"
    h = _pref_header(rows, code, "表12-36都道府県別男子30~34歳,女子25~29歳未婚者割合")
    men, women = _norm(rows[h].get(2)), _norm(rows[h].get(7))
    if not men.startswith("男性30~34歳") or not women.startswith("女性25~29歳"):
        msg = f"{code}: header groups 男性30~34歳 / 女性25~29歳 expected, got {men!r} / {women!r}"
        raise ValueError(msg)
    _expect_years(_year_columns(rows[h + 1], range(2, 12), code), _T1236_YEARS * 2, code)
    out = _pref_year_grid(
        rows,
        h + 2,
        code,
        list(zip(range(2, 7), _T1236_YEARS, strict=True)),
        "never_married_m30_34",
        "M",
        "30-34",
    )
    out += _pref_year_grid(
        rows,
        h + 2,
        code,
        list(zip(range(7, 12), _T1236_YEARS, strict=True)),
        "never_married_f25_29",
        "F",
        "25-29",
    )
    return out


_T1237_YEARS: tuple[int, ...] = (1920, 1930, 1940, 1950, 1970, 1990, 2000, 2005, 2010, 2015, 2020)


def pref_never_married_at_50_rows(payload: bytes) -> list[dict[str, object]]:
    """T12-37 sheets (1) 男 / (2) 女: ``never_married_at_50`` (%) for 11 census years."""
    code = "T12-37"
    out: list[dict[str, object]] = []
    for sex, rows in _sex_sheets(payload, code):
        h = _pref_header(rows, code, "表12-37都道府県,性別50歳時未婚割合")
        _expect_years(_year_columns(rows[h], range(2, 13), code), _T1237_YEARS, code)
        cols = list(zip(range(2, 13), _T1237_YEARS, strict=True))
        out += _pref_year_grid(rows, h + 1, code, cols, "never_married_at_50", sex, None)
    return out


_T1252_YEARS: tuple[int, ...] = (1980, 2000, 2010, 2020)
_T1252_AGES: tuple[tuple[str, str], ...] = (
    ("総数1)", "total"),
    ("15~29歳", "15-29"),
    ("30~44歳", "30-44"),
    ("45~59歳", "45-59"),
    ("60歳以上", "60-"),
)
_T1252_SHEET_LABEL = re.compile(r"^\((\d)\)(\d{4})年\*?$")


def pref_lfp_rows(payload: bytes) -> list[dict[str, object]]:
    """T12-52 sheets (1)…(4) = 1980 / 2000 / 2010 / 2020: ``lfp`` (労働力率 %) by sex x age
    class (total, 15-29, 30-44, 45-59, 60-)."""
    code = "T12-52"
    out: list[dict[str, object]] = []
    for n, want_year in enumerate(_T1252_YEARS, start=1):
        rows = sheet_rows(payload, f"{code}({n})")
        _title(rows, "表12-52都道府県,性,年齢別労働力率", code)
        cell = _norm(rows[1].get(1)) if len(rows) > 1 else ""
        m = _T1252_SHEET_LABEL.match(cell)
        if m is None or int(m.group(1)) != n or int(m.group(2)) != want_year:
            msg = f"{code}({n}): sheet label ({n}) {want_year}年 expected, got {cell!r}"
            raise ValueError(msg)
        h = _header_row(rows, "都道府県", code)
        _check_header(rows[h], {4: "男", 9: "女"}, code)
        sub = {c: label for c, (label, _) in zip(range(2, 7), _T1252_AGES, strict=True)}
        _check_header(rows[h + 1], sub | {c + 5: g for c, g in sub.items()}, code)
        for sex, base in (("M", 2), ("F", 7)):
            for off, (_, ac) in enumerate(_T1252_AGES):
                out += _pref_year_grid(rows, h + 2, code, [(base + off, want_year)], "lfp", sex, ac)
    return out


_T1253_YEARS: tuple[int, ...] = (1980, 1990, 2000, 2010, 2015, 2020)


def pref_unemployment_rows(rows: Rows) -> list[dict[str, object]]:
    """T12-53: ``unemployment_rate`` (完全失業率 %) by sex for 1980…2020."""
    code = "T12-53"
    h = _pref_header(rows, code, "表12-53都道府県別完全失業率")
    _check_header(rows[h], {1: "都道府県", 2: "男", 8: "女"}, code)
    _expect_years(_year_columns(rows[h + 1], range(2, 14), code), _T1253_YEARS * 2, code)
    out: list[dict[str, object]] = []
    for sex, base in (("M", 2), ("F", 8)):
        cols = list(zip(range(base, base + 6), _T1253_YEARS, strict=True))
        out += _pref_year_grid(rows, h + 2, code, cols, "unemployment_rate", sex, None)
    return out


_PARSERS.update(
    {
        "T06-12": mean_marriage_age_rows,
        "T06-23": never_married_at_50_rows,
        "T12-33": pref_tfr_rows,
        "T12-36": pref_never_married_young_rows,
        "T12-53": pref_unemployment_rows,
    }
)
_PAYLOAD_PARSERS: dict[str, Callable[[bytes], list[dict[str, object]]]] = {
    "T06-24": marital_status_share_rows,
    "T12-35": pref_first_marriage_age_rows,
    "T12-37": pref_never_married_at_50_rows,
    "T12-52": pref_lfp_rows,
}


def build_marriage_mart(parts: dict[str, Sequence[dict[str, object]]]) -> list[dict[str, object]]:
    """``marts/jp_marriage_series``: sorted by (year, metric, sex, age_class); duplicate keys
    raise ``ValueError``."""

    def key(r: dict[str, object]) -> tuple[object, ...]:
        ac = r["age_class"]
        return (
            int(str(r["year"])),
            MARRIAGE_METRICS.index(str(r["metric"])),
            str(r["sex"]),
            "" if ac is None else str(ac),
        )

    return _combine(parts, key, "(year, metric, sex, age_class)")


# ============================================================================================
# ---- H12: T06-01★ 初婚・再婚別婚姻数 と 第16回出生動向基本調査 報告書グラフデータ CSV ------------
# ============================================================================================

# ---- T06-01★: 初婚・再婚別婚姻数および婚姻率, every year 1884–2024 -------------------------------

_T0601_FIRST_YEAR = 1884
_T0601_LAST_YEAR = 2024
_T0601_MISSING_YEARS: tuple[int, ...] = tuple(range(1941, 1947))  # no rows for the war years
# (who, first metric, remarriage metric, share metric) checked as 初婚 + 再婚 <= 総数
_T0601_SPLITS: tuple[tuple[str, str, str, str], ...] = (
    (
        "husband",
        "first_marriages_husband",
        "remarriages_husband",
        "first_marriage_share_husband_pct",
    ),
    ("wife", "first_marriages_wife", "remarriages_wife", "first_marriage_share_wife_pct"),
)
# Upstream inconsistencies in the 2026 edition (checked 2026-10-18): 1918 夫 518,228 and 1926 妻
# 538,388 exceed 総数 (500,580 / 502,847) and the printed share does not match either. Those
# split / share cells are dropped (no row); any other year that fails the check is a ValueError.
_T0601_KNOWN_INCONSISTENT: frozenset[tuple[int, str]] = frozenset(
    {(1918, "husband"), (1926, "wife")}
)
# (column, metric, sex). 総数 and 婚姻率 are published every year; the 初婚 / 再婚 split and the
# 初婚の割合 are '…' for 1884–1898 and 1947–1951 (no row); 1941–1946 have no row at all.
_T0601_COLS: tuple[tuple[int, str, str], ...] = (
    (2, "marriages_total", "T"),
    (3, "first_marriages_husband", "M"),
    (4, "remarriages_husband", "M"),
    (5, "first_marriages_wife", "F"),
    (6, "remarriages_wife", "F"),
    (7, "first_marriage_share_husband_pct", "M"),
    (8, "first_marriage_share_wife_pct", "F"),
    (9, "crude_marriage_rate", "T"),
)


def first_marriage_rows(rows: Rows) -> list[dict[str, object]]:
    """T06-01★: marriages by first marriage / remarriage of husband and wife (件), the share of
    first marriages (%) and the crude marriage rate (‰), every year 1884–2024. Title, the two
    header rows, consecutive years and 初婚 + 再婚 <= 総数 are checked (``ValueError``);
    '…' cells produce no row. 1947–72 exclude Okinawa; before 1940 総数 includes 不詳."""
    code = "T06-01"
    _title(rows, "表6-1初婚・再婚別婚姻数および婚姻率", code)
    h = _header_row(rows, "年次", code)
    _check_header(
        rows[h], {1: "年次", 2: "総数", 3: "夫", 5: "妻", 7: "初婚の割合(%)", 9: "婚姻率"}, code
    )
    _check_header(
        rows[h + 1], {3: "初婚", 4: "再婚", 5: "初婚", 6: "再婚", 7: "夫", 8: "妻", 9: "(‰)"}, code
    )
    body: list[tuple[int, dict[int, str]]] = []
    for r in rows[h + 2 :]:
        y = _int(r.get(1))
        if y is None:
            break
        body.append((y, r))
    years = [y for y, _ in body]
    want = [
        y for y in range(_T0601_FIRST_YEAR, _T0601_LAST_YEAR + 1) if y not in _T0601_MISSING_YEARS
    ]
    if years != want:
        msg = (
            f"{code}: years must run {want[0]}…{want[-1]} consecutively (except "
            f"{_T0601_MISSING_YEARS[0]}–{_T0601_MISSING_YEARS[-1]}), got {years[:3]}…{years[-3:]}"
        )
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for year, r in body:
        values: dict[str, float | None] = {}
        for c, metric, _sex in _T0601_COLS:
            where = f"{code} {year} {metric}"
            values[metric] = _num(r.get(c), where) if c in (2, 9) else _opt_num(r.get(c), where)
        total = values["marriages_total"]
        assert total is not None
        for who, first, re_, share in _T0601_SPLITS:
            f, m = values[first], values[re_]
            if (f is None) != (m is None):
                msg = f"{code} {year}: {first} and {re_} must both be published or both '…'"
                raise ValueError(msg)
            if f is not None and m is not None and f + m > total:
                if (year, who) not in _T0601_KNOWN_INCONSISTENT:
                    msg = f"{code} {year}: {first} + {re_} = {f + m:.0f} exceeds 総数 {total:.0f}"
                    raise ValueError(msg)
                values[first] = values[re_] = values[share] = None  # upstream typo: no row
        for _c, metric, sex in _T0601_COLS:
            v = values[metric]
            if v is not None:
                out.append(_marriage_row(year, metric, sex, None, v, code))
    return out


_PARSERS["T06-01"] = first_marriage_rows


# ---- 第16回出生動向基本調査 報告書グラフデータ CSV (CP932, tidy; one file per figure) ----------

GRAPH_BASE_URL = "https://www.ipss.go.jp/ps-doukou/j/db_16/16HoukokuBaseData/"
GRAPH_SOURCE = "ipss_jnfs16_graph"
GRAPH_FILES: tuple[str, ...] = (
    "1_1_1",  # 未婚者の生涯の結婚意思 (第8–16回, CI)
    "1_1_2",  # 同, 年齢別
    "1_2_1",  # 結婚の利点 (第9–16回)
    "1_2_2",  # 独身生活の利点
    "1_3_2",  # 独身でいる理由, 年齢別 (第10–16回)
    "2_1_1",  # 恋人または婚約者がいる割合, 年齢別
    "2_1_2",  # 交際相手なし と 交際希望, 年齢別
    "2_3_1",  # 未婚者の交際相手と知り合ったきっかけ
    "3_2_1",  # 結婚相手の条件 (重視 / 考慮, 第10–16回, 第13回なし)
    "5_2_1",  # 結婚年次別 恋愛 / 見合い (1930–39 … 2019–21年, CI)
    "5_2_2",  # 夫婦の知り合ったきっかけ (第8–16回; 第16回は a / b の 2 期間)
    "12_1_2",  # 結婚・家族に関する考え方 (支持 / 不支持, 第10–16回)
)
GRAPH_ROUND_YEARS: dict[int, int] = {
    8: 1982,
    9: 1987,
    10: 1992,
    11: 1997,
    12: 2002,
    13: 2005,
    14: 2010,
    15: 2015,
    16: 2021,
}
# 第16回(2021)a / b in 5_2_2: couples married 2015/7–2018/6 and 2018/7–2021/6 (b is under COVID).
GRAPH_PERIODS: dict[str, str] = {"a": "2015/7-2018/6", "b": "2018/7-2021/6"}
GRAPH_SEX: dict[str, str] = {
    "男性": "male",
    "女性": "female",
    "計": "total",
    "男性が相手の女性に求める条件": "male",
    "女性が相手の男性に求める条件": "female",
}
GRAPH_CATEGORIES: tuple[str, ...] = (
    "生涯の結婚意思",
    "結婚の利点",
    "独身生活の利点",
    "独身の理由",
    "異性との交際状況",
    "交際希望",
    "知り合ったきっかけ",
    "重視する項目",
    "結婚・家族に関する考え方",
)
GRAPH_SUBS: tuple[str, ...] = ("重視する程度", "旧来的な考え方への支持／不支持")
_GRAPH_DIMS: dict[str, str] = {
    "調査回": "round",
    "結婚年": "marriage_year",
    "性別": "sex",
    "年齢": "age",
}
_GRAPH_NUMERIC: dict[str, str] = {
    "度数": "count",
    "割合": "share_pct",
    "標準誤差": "se",
    "95%信頼区間上限": "ci_high",
    "95%信頼区間下限": "ci_low",
    "総数": "denominator",
}
_CI = ("標準誤差", "95%信頼区間上限", "95%信頼区間下限")
# Expected header (row 2) of every file, closed. Verified against the real files 2026-10-18.
GRAPH_HEADERS: dict[str, tuple[str, ...]] = {
    "1_1_1": ("調査回", "性別", "生涯の結婚意思", "度数", "割合", *_CI),
    "1_1_2": ("調査回", "性別", "年齢", "生涯の結婚意思", "度数", "割合", *_CI),
    "1_2_1": ("調査回", "性別", "結婚の利点", "度数", "割合", "総数"),
    "1_2_2": ("調査回", "性別", "独身生活の利点", "度数", "割合", "総数"),
    "1_3_2": ("調査回", "性別", "年齢", "独身の理由", "度数", "割合", "総数"),
    "2_1_1": ("調査回", "性別", "年齢", "異性との交際状況", "度数", "割合", "総数"),
    "2_1_2": ("調査回", "性別", "年齢", "交際希望", "度数", "割合", "総数"),
    "2_3_1": ("調査回", "性別", "知り合ったきっかけ", "度数", "割合"),
    "3_2_1": ("調査回", "性別", "重視する項目", "重視する程度", "度数", "割合", "総数"),
    "5_2_1": ("結婚年", "知り合ったきっかけ", "度数", "割合", *_CI),
    "5_2_2": ("調査回", "知り合ったきっかけ", "度数", "割合"),
    "12_1_2": (
        "調査回",
        "性別",
        "結婚・家族に関する考え方",
        "旧来的な考え方への支持／不支持",
        "割合",
        "度数",
    ),
}
ATTITUDES_KEY: tuple[str, ...] = (
    "figure",
    "survey_round",
    "period",
    "marriage_year",
    "sex",
    "age",
    "category",
    "item",
    "sub",
)
_GRAPH_ROUND = re.compile(r"^第(\d+)回\((\d{4})\)([ab]?)$")
_GRAPH_NULL = ("", "-", "NA", "…", "...")


def graph_url(figure: str) -> str:
    return f"{GRAPH_BASE_URL}{graph_raw_name(figure)}"


def graph_raw_name(figure: str) -> str:
    return f"houkokuFigure{figure}.csv"


def _graph_num(text: str, where: str) -> float | None:
    s = text.strip()
    if s in _GRAPH_NULL:
        return None
    try:
        return float(s)
    except ValueError:
        msg = f"{where}: non-numeric cell {text!r}"
        raise ValueError(msg) from None


def _graph_round(text: str, where: str) -> tuple[int, int, str]:
    m = _GRAPH_ROUND.match(_norm(text))
    if not m:
        msg = f"{where}: unexpected survey round {text!r}"
        raise ValueError(msg)
    rnd, year, suffix = int(m.group(1)), int(m.group(2)), m.group(3)
    if GRAPH_ROUND_YEARS.get(rnd) != year:
        msg = f"{where}: survey round {text!r} is not one of {GRAPH_ROUND_YEARS}"
        raise ValueError(msg)
    if suffix and rnd != 16:
        msg = f"{where}: survey round {text!r} has a period suffix outside the 16th round"
        raise ValueError(msg)
    return rnd, year, GRAPH_PERIODS[suffix] if suffix else ""


def graph_rows(payload: bytes, figure: str) -> list[dict[str, object]]:
    """One 報告書グラフデータ CSV -> long rows with the common attitude columns. Row 1 is the figure
    title (must name *figure*), row 2 the header (must equal ``GRAPH_HEADERS[figure]``), the rest
    tidy data. 調査回 is mapped to (survey_round, survey_year, period) with the fixed round → year
    table, 性別 through the closed ``GRAPH_SEX``; the question column (``GRAPH_CATEGORIES``)
    becomes category / item and the second split (``GRAPH_SUBS``) ``sub``. Numbers drop the
    leading blanks, '-' / '' / 'NA' are ``None``. Any deviation and a duplicate key raise
    ``ValueError`` (fail closed)."""
    if figure not in GRAPH_HEADERS:
        msg = f"unknown figure {figure!r}"
        raise ValueError(msg)
    where = f"houkokuFigure{figure}"
    try:
        text = payload.decode("cp932")
    except UnicodeDecodeError as e:
        msg = f"{where}: not a cp932 file ({e.reason})"
        raise ValueError(msg) from None
    records = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    if len(records) < 2:
        msg = f"{where}: expected a title row and a header row"
        raise ValueError(msg)
    prefix = "報告書図表" + figure.replace("_", "-")
    if not _norm(records[0][0]).startswith(prefix):
        msg = f"{where}: unexpected title {records[0][0]!r} (expected {prefix!r}…)"
        raise ValueError(msg)
    header = tuple(_norm(c) for c in records[1])
    want = tuple(_norm(c) for c in GRAPH_HEADERS[figure])
    if header != want:
        msg = f"{where}: unexpected header {records[1]} (expected {GRAPH_HEADERS[figure]})"
        raise ValueError(msg)
    body = records[2:]
    if not body:
        msg = f"{where}: empty (no data rows)"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for i, rec in enumerate(body, start=3):
        if len(rec) != len(want):
            msg = f"{where} line {i}: expected {len(want)} columns, got {len(rec)}"
            raise ValueError(msg)
        row: dict[str, object] = {
            "figure": figure,
            "survey_round": None,
            "survey_year": None,
            "period": "",
            "marriage_year": "",
            "sex": "",
            "age": "",
            "category": "",
            "item": "",
            "sub": "",
            "count": None,
            "share_pct": None,
            "se": None,
            "ci_low": None,
            "ci_high": None,
            "denominator": None,
            "source": GRAPH_SOURCE,
        }
        at = f"{where} line {i}"
        for name, cell in zip(GRAPH_HEADERS[figure], rec, strict=True):
            if name == "調査回":
                row["survey_round"], row["survey_year"], row["period"] = _graph_round(cell, at)
            elif name == "性別":
                if cell.strip() not in GRAPH_SEX:
                    msg = f"{at}: unexpected sex label {cell!r}"
                    raise ValueError(msg)
                row["sex"] = GRAPH_SEX[cell.strip()]
            elif name in _GRAPH_DIMS:
                row[_GRAPH_DIMS[name]] = cell.strip()
            elif name in GRAPH_CATEGORIES:
                row["category"] = name
                row["item"] = cell.strip()
            elif name in GRAPH_SUBS:
                row["sub"] = cell.strip()
            else:
                row[_GRAPH_NUMERIC[name]] = _graph_num(cell, f"{at} {name}")
        key = tuple(row[c] for c in ATTITUDES_KEY)
        if key in seen:
            msg = f"{where}: duplicate key {ATTITUDES_KEY} = {key}"
            raise ValueError(msg)
        seen.add(key)
        out.append(row)
    return out


def build_attitudes_mart(parts: dict[str, Sequence[dict[str, object]]]) -> list[dict[str, object]]:
    """``marts/jp_marriage_attitudes``: every staged figure combined, sorted by figure (file
    order), survey_round, period, marriage_year, sex, age, category, item, sub; duplicate keys
    raise ``ValueError``."""

    def key(r: dict[str, object]) -> tuple[object, ...]:
        rnd = r["survey_round"]
        return (
            GRAPH_FILES.index(str(r["figure"])),
            -1 if rnd is None else int(str(rnd)),
            *(str(r[c]) for c in ATTITUDES_KEY[2:]),
        )

    return _combine(parts, key, str(ATTITUDES_KEY))
