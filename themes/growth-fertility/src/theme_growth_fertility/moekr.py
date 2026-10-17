"""교육부 (Ministry of Education, Korea) 초중고 사교육비조사 press-release PDF -> long rows.
Pure; no I/O (H8d-K, hypothesis K: private tutoring spending as an add-on cost of children).

Source: 「2025년 초중고 사교육비 조사 결과」 보도자료 (published 2026-03-12, KOGL type 1), a 51-page
PDF on the MOE board. Three tables are read from the pypdf text (anything else raises
``ValueError`` = fail closed; nothing is imputed):

- ``annual``      statistics table 21 「연도별 초중고사교육비조사 주요 결과 및 증감률」 (p. 44 of
                  the document): one row per survey year 2007–2025 with 총액(억원), 참여율(%),
                  참여시간(시간/주), 전체학생 1인당 월평균 사교육비(만원) and, from 2017 on,
                  참여학생 1인당(만원) (printed as ``-`` before 2017 -> no row).
- ``by_children`` statistics tables 10–11 「자녀수별 …」: 전체 / 1명 / 2명 / 3명 이상 for the two
                  years printed (2024, 2025): 1인당 월평균 사교육비 and 참여율.
- ``by_level``    body tables <표1> (총액), <표2> (참여율・주당 참여시간), <표4> (1인당 월평균,
                  전체학생 and 참여학생) by 초등학교 / 중학교 / 고등학교 for 2024 and 2025. The
                  PDF carries no per-level time series, so by_level covers two years only.

The 전체 column of the by_children and by_level tables must equal the annual table for the same
year (cross-check), otherwise ``ValueError``.

Values are as printed: 억원 (100 million KRW), 만원 (10 thousand KRW, monthly), %, hours per
week. Nominal (no price adjustment).
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from theme_growth_fertility.kostat import pdf_text

SOURCE = "moe_kr"
SURVEY_YEAR = 2025
RELEASE_YEAR = 2026
FIRST_YEAR = 2007
URL = (
    "https://www.moe.go.kr/boardCnts/fileDown.do?m=020402&s=moe"
    "&fileSeq=7562a697bdba006065fa92054b1d634e"
)
BOARD_URL = (
    "https://www.moe.go.kr/boardCnts/listRenew.do?boardID=294&m=020402&s=moe"
    "&searchType=S&searchStr=%EC%82%AC%EA%B5%90%EC%9C%A1%EB%B9%84"
)
RAW_NAME = f"private_tutoring_{SURVEY_YEAR}.pdf"
# 교육부 press releases are 공공누리 (KOGL) 제1유형 — attribution only (checked 2026-10-17).
LICENSE = (
    "KOGL Type 1 (공공누리 제1유형: 출처표시; https://www.kogl.or.kr/info/license.do). "
    "Attribution: 교육부, 2025년 초중고 사교육비 조사 결과 보도자료 (2026-03-12), moe.go.kr "
    "(KOGL 제1유형)"
)

TABLES: tuple[str, ...] = ("annual", "by_children", "by_level")
TOTAL = "총계"
CHILDREN_GROUPS: tuple[str, ...] = (TOTAL, "자녀 1명", "자녀 2명", "자녀 3명 이상")
LEVEL_GROUPS: tuple[str, ...] = ("초등학교", "중학교", "고등학교")
GROUPS: tuple[str, ...] = CHILDREN_GROUPS + LEVEL_GROUPS
M_TOTAL = "total_100m_krw"
M_PART = "participation_rate_pct"
M_HOURS = "hours_per_week"
M_SPEND = "spend_per_student_10k_krw"
M_SPEND_P = "spend_per_participant_10k_krw"
METRICS: tuple[str, ...] = (M_TOTAL, M_PART, M_HOURS, M_SPEND, M_SPEND_P)

_INT = r"\d{1,3}(?:,\d{3})*|\d+"
_DEC = r"-?\d+\.\d"


def _normalise(page: str) -> list[str]:
    """NFKC (full-width spaces/digits), collapse inner whitespace, drop blank lines."""
    out: list[str] = []
    for raw in unicodedata.normalize("NFKC", page).splitlines():
        line = " ".join(raw.split())
        if line:
            out.append(line)
    return out


def _num(token: str) -> float:
    return float(token.replace(",", ""))


def _row(year: int, table: str, group: str, metric: str, value: float) -> dict[str, object]:
    return {
        "year": year,
        "table": table,
        "group": group,
        "metric": metric,
        "value": value,
        "release_year": RELEASE_YEAR,
        "source": SOURCE,
    }


def _find(pages: Sequence[str], title: re.Pattern[str], what: str) -> tuple[list[str], int]:
    """Normalised lines of the first page with a line matching *title* (anchored at both ends,
    so table-of-contents entries with leaders and page numbers do not match) and the index of
    that line."""
    for page in pages:
        lines = _normalise(page)
        for i, line in enumerate(lines):
            if title.match(line):
                return lines, i
    msg = f"{what} not found in any page"
    raise ValueError(msg)


def _header(lines: list[str], start: int, first_row: re.Pattern[str]) -> tuple[str, int]:
    """Whitespace-free text between *start* and the first line matching *first_row*."""
    i = start
    while i < len(lines) and not first_row.match(lines[i]):
        i += 1
    return re.sub(r"\s+", "", "".join(lines[start:i])), i


# ---- annual (statistics table 21) ---------------------------------------------------------

_ANNUAL_TITLE = re.compile(
    r"^\d+\.\s*연도별\s*초중고\s*사교육비\s*조사\s*주요\s*결과\s*및\s*증감률$"
)
_ANNUAL_HEADER = (
    "연도총액(억원)참여율(%)참여시간(시간)학생1인당월평균사교육비(만원)전체학생참여학생"
)
_YEAR_START = re.compile(r"^\d{4}\b")
_ANNUAL_ROW = re.compile(rf"^(\d{{4}}) ({_INT}) ({_DEC}) ({_DEC}) ({_DEC}) ({_DEC}|-)$")


def annual_rows(pages: Sequence[str]) -> list[dict[str, object]]:
    """``annual`` rows (group 총계) for every survey year FIRST_YEAR..SURVEY_YEAR."""
    lines, start = _find(pages, _ANNUAL_TITLE, "annual table (연도별 주요 결과)")
    header, i = _header(lines, start + 1, _YEAR_START)
    if header != _ANNUAL_HEADER:
        msg = f"unexpected annual table header: {header!r}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    years: list[int] = []
    while i < len(lines) and _YEAR_START.match(lines[i]):
        m = _ANNUAL_ROW.match(lines[i])
        if m is None:
            msg = f"annual row {lines[i][:4]}: expected 5 values, got {lines[i]!r}"
            raise ValueError(msg)
        year = int(m.group(1))
        years.append(year)
        out.append(_row(year, "annual", TOTAL, M_TOTAL, _num(m.group(2))))
        out.append(_row(year, "annual", TOTAL, M_PART, _num(m.group(3))))
        out.append(_row(year, "annual", TOTAL, M_HOURS, _num(m.group(4))))
        out.append(_row(year, "annual", TOTAL, M_SPEND, _num(m.group(5))))
        if m.group(6) != "-":
            out.append(_row(year, "annual", TOTAL, M_SPEND_P, _num(m.group(6))))
        i += 1
    expected = list(range(FIRST_YEAR, SURVEY_YEAR + 1))
    if years != expected:
        msg = f"annual years must be {FIRST_YEAR}-{SURVEY_YEAR} consecutive, got {years}"
        raise ValueError(msg)
    return out


# ---- by number of children (statistics tables 10 / 11) ------------------------------------


@dataclass(frozen=True)
class _ChildrenTable:
    label: str
    title: re.Pattern[str]
    metric: str


_CHILDREN_TABLES: tuple[_ChildrenTable, ...] = (
    _ChildrenTable(
        "10. 자녀수별 전체학생 1인당 월평균 사교육비",
        re.compile(r"^\d+\.\s*자녀수별\s*전체학생\s*1인당\s*월평균\s*사교육비$"),
        M_SPEND,
    ),
    _ChildrenTable(
        "11. 자녀수별 사교육 참여율",
        re.compile(r"^\d+\.\s*자녀수별\s*사교육\s*참여율$"),
        M_PART,
    ),
)
_CHILDREN_HEADER = "전체 1명 2명 3명 이상"
_CHILDREN_YEAR_START = re.compile(r"^<\s*\d{4}\s*>")
_CHILDREN_ROW = re.compile(rf"^< (\d{{4}}) > ({_DEC}) ({_DEC}) ({_DEC}) ({_DEC})$")


def by_children_rows(pages: Sequence[str]) -> list[dict[str, object]]:
    """``by_children`` rows: 총계 / 자녀 1명 / 2명 / 3명 이상 x (1인당 월평균, 참여율) per year."""
    out: list[dict[str, object]] = []
    seen_years: dict[str, list[int]] = {}
    for t in _CHILDREN_TABLES:
        lines, start = _find(pages, t.title, f"by-children table '{t.label}'")
        header, i = _header(lines, start + 1, _CHILDREN_YEAR_START)
        if _CHILDREN_HEADER.replace(" ", "") not in header:
            msg = f"{t.label}: unexpected header {header!r}"
            raise ValueError(msg)
        years: list[int] = []
        for line in lines[i:]:
            if not _CHILDREN_YEAR_START.match(line):
                continue
            m = _CHILDREN_ROW.match(line)
            if m is None:
                msg = f"{t.label}: expected 4 values in {line!r}"
                raise ValueError(msg)
            year = int(m.group(1))
            years.append(year)
            for group, tok in zip(CHILDREN_GROUPS, m.groups()[1:], strict=True):
                out.append(_row(year, "by_children", group, t.metric, _num(tok)))
        if not years:
            msg = f"{t.label}: no year row"
            raise ValueError(msg)
        seen_years[t.label] = years
    if len({tuple(v) for v in seen_years.values()}) != 1:
        msg = f"by-children tables cover different years: {seen_years}"
        raise ValueError(msg)
    return out


# ---- by school level (body tables <표1>, <표2>, <표4>) --------------------------------------


@dataclass(frozen=True)
class _LevelTable:
    label: str
    title: re.Pattern[str]
    header_suffix: str
    # value index -> (group, metric); TOTAL entries are cross-checked, not emitted
    columns: tuple[tuple[str, str], ...]


def _level_cols(*metrics: str) -> tuple[tuple[str, str], ...]:
    return tuple((g, m) for m in metrics for g in (TOTAL, *LEVEL_GROUPS))


_LEVELS = "초등학교중학교고등학교"
_LEVEL_TABLES: tuple[_LevelTable, ...] = (
    _LevelTable(
        "표1",
        re.compile(r"^<표\d+>\s*초중고\s*학생\s*사교육비\s*총액$"),
        "구분전체" + _LEVELS,
        _level_cols(M_TOTAL),
    ),
    _LevelTable(
        "표2",
        re.compile(r"^<표\d+>\s*학교급별\s*사교육\s*참여율\s*및\s*주당\s*참여시간$"),
        "사교육참여율주당참여시간" + _LEVELS * 2,
        _level_cols(M_PART, M_HOURS),
    ),
    _LevelTable(
        "표4",
        re.compile(r"^<표\d+>\s*학교급별\s*학생\s*1인당\s*월평균\s*사교육비$"),
        "전체학생참여학생" + _LEVELS * 2,
        _level_cols(M_SPEND, M_SPEND_P),
    ),
)
_LEVEL_YEAR_START = re.compile(r"^\d{4}년\b")


def by_level_rows(pages: Sequence[str]) -> list[dict[str, object]]:
    """``by_level`` rows: 초등학교 / 중학교 / 고등학교 x five metrics per year."""
    return [r for r in _level_rows_with_totals(pages) if r["group"] != TOTAL]


def _level_rows_with_totals(pages: Sequence[str]) -> list[dict[str, object]]:
    """As ``by_level_rows`` plus the 전체 columns (group 총계) for the annual cross-check."""
    out: list[dict[str, object]] = []
    for t in _LEVEL_TABLES:
        lines, start = _find(pages, t.title, f"by-level table <{t.label}>")
        header, i = _header(lines, start + 1, _LEVEL_YEAR_START)
        if not header.endswith(t.header_suffix):
            msg = f"<{t.label}>: unexpected header {header!r}"
            raise ValueError(msg)
        n = len(t.columns)
        value_re = _INT if t.columns[0][1] == M_TOTAL else _DEC
        row_re = re.compile(rf"^(\d{{4}})년 ((?:{value_re})(?: (?:{value_re})){{{n - 1}}})$")
        years = 0
        while i < len(lines) and _LEVEL_YEAR_START.match(lines[i]):
            m = row_re.match(lines[i])
            if m is None:
                msg = f"<{t.label}>: expected {n} values in {lines[i]!r}"
                raise ValueError(msg)
            year = int(m.group(1))
            for (group, metric), tok in zip(t.columns, m.group(2).split(), strict=True):
                out.append(_row(year, "by_level", group, metric, _num(tok)))
            years += 1
            i += 1
        if not years:
            msg = f"<{t.label}>: no year row"
            raise ValueError(msg)
    return out


# ---- assembly + mart -----------------------------------------------------------------------


def _check_totals(annual: list[dict[str, object]], rows: list[dict[str, object]]) -> None:
    """Every 총계 value of a sub-table must equal the annual table for that year and metric."""
    ref = {(r["year"], r["metric"]): r["value"] for r in annual}
    for r in rows:
        if r["group"] != TOTAL:
            continue
        key = (r["year"], r["metric"])
        if key not in ref:
            msg = f"{r['table']} {r['year']} {r['metric']}: year missing from the annual table"
            raise ValueError(msg)
        if ref[key] != r["value"]:
            msg = (
                f"{r['table']} {r['year']} {r['metric']}: 전체 {r['value']} differs from the "
                f"annual table ({ref[key]})"
            )
            raise ValueError(msg)


def private_tutoring_rows_from_pages(pages: Sequence[str]) -> list[dict[str, object]]:
    """All three tables as one long list (annual, by_children incl. 총계, by_level without the
    전체 columns). ``ValueError`` on any layout, column-count, year-range or total mismatch."""
    annual = annual_rows(pages)
    children = by_children_rows(pages)
    level = _level_rows_with_totals(pages)
    _check_totals(annual, children)
    _check_totals(annual, level)
    return annual + children + [r for r in level if r["group"] != TOTAL]


def private_tutoring_rows(payload: bytes) -> list[dict[str, object]]:
    return private_tutoring_rows_from_pages(pdf_text(payload))


def build_mart(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Long mart sorted by (year, table, group, metric) in the declared orders; duplicate keys
    raise ``ValueError``. Pure and deterministic."""

    def key(r: dict[str, object]) -> tuple[int, int, int, int]:
        return (
            int(str(r["year"])),
            TABLES.index(str(r["table"])),
            GROUPS.index(str(r["group"])),
            METRICS.index(str(r["metric"])),
        )

    out = sorted((dict(r) for r in rows), key=key)
    keys = [key(r) for r in out]
    if len(keys) != len(set(keys)):
        dup = next(k for i, k in enumerate(keys) if k in keys[:i])
        msg = f"duplicate key (year, table, group, metric) = {dup}"
        raise ValueError(msg)
    return out
