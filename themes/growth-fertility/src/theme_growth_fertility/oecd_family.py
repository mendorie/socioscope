"""OECD Family Database SF2.5 "Childlessness" workbook -> long rows. Pure; no I/O.

One static xlsx (``URL``), two chart-data sheets read with openpyxl:

- ``Chart SF2.5.A`` "Definitive childlessness": country rows × birth-cohort columns (1935 …
  1975; the header row holds the cohort years as integers), value = % of women of the cohort
  who remained childless. Empty cells are missing (no row). Some cells stand for neighbouring
  cohorts (the sheet's notes 1–4, e.g. Korea 1975 = the 1970 cohort); the values are kept as
  published and the caveats live in ``design/data-sources.md``.
- ``Chart SF2.5.B`` "Definitive childlessness and completed fertility rates": one cohort (the
  year is read from the subtitle "women born in YYYY"), rows of country name, ISO3 code,
  permanent childlessness % and completed fertility rate. Poland is listed twice with identical
  values (kept once, reported); a conflicting repeat fails closed.

Country names are mapped with the fixed ``NAME_TO_ISO3`` (names seen in the 2026-10-18 file);
an unknown name, a code that disagrees with the name, a text where a number is expected, a
missing sheet or header fails closed with ``ValueError``. Non-OECD members (China, Bulgaria)
and "England and Wales" (not a country) are dropped and reported.

Licence: OECD Terms & Conditions (``oecd.LICENSE``). Cite: OECD Family Database, SF2.5
Childlessness (accessed 2026-10-18).
"""

import io
import re
from collections.abc import Iterable

import openpyxl

from theme_growth_fertility import oecd

SOURCE = "oecd_family"
URL = "https://webfs.oecd.org/Els-com/Family_Database/SF_2-5-Childlessness.xlsx"
RAW_NAME = "sf2_5_childlessness.xlsx"
LICENSE = (
    f"{oecd.LICENSE}. Cite: OECD Family Database, SF2.5 Childlessness "
    "(https://www.oecd.org/en/data/datasets/oecd-family-database.html, accessed 2026-10-18)."
)
SHEET_A = "Chart SF2.5.A"
SHEET_B = "Chart SF2.5.B"
CHART_A = "SF2.5.A"
CHART_B = "SF2.5.B"
METRIC_CHILDLESS = "childless_share_pct"
METRIC_CFR = "completed_fertility"
NAME_TO_ISO3: dict[str, str] = {
    "Austria": "AUT", "Bulgaria": "BGR", "Canada": "CAN", "China": "CHN", "Czechia": "CZE",
    "Denmark": "DNK", "Estonia": "EST", "Finland": "FIN", "France": "FRA", "Germany": "DEU",
    "Hungary": "HUN", "Iceland": "ISL", "Ireland": "IRL", "Italy": "ITA", "Japan": "JPN",
    "Korea": "KOR", "Lithuania": "LTU", "Mexico": "MEX", "Netherlands": "NLD", "Norway": "NOR",
    "Poland": "POL", "Portugal": "PRT", "Slovakia": "SVK", "Slovenia": "SVN", "Spain": "ESP",
    "Sweden": "SWE", "United States": "USA",
    # names that appear only in SF2.4 (H11; "Czech Republic" / "Slovak Republic" are the older
    # spellings of CZE / SVK, HRV / CYP / MLT / ROU are non-members and get dropped)
    "Australia": "AUS", "Belgium": "BEL", "Chile": "CHL", "Colombia": "COL", "Costa Rica": "CRI",
    "Czech Republic": "CZE", "Greece": "GRC", "Israel": "ISR", "Latvia": "LVA",
    "Luxembourg": "LUX", "New Zealand": "NZL", "Slovak Republic": "SVK", "Switzerland": "CHE",
    "Türkiye": "TUR", "United Kingdom": "GBR", "Croatia": "HRV", "Cyprus": "CYP", "Malta": "MLT",
    "Romania": "ROU",
}  # fmt: skip
NOT_COUNTRIES: frozenset[str] = frozenset({"England and Wales"})
# ---- H11: SF2.4 Share of births outside of marriage (annual sheet, country x year 1960–) -----
BOM_URL = "https://webfs.oecd.org/Els-com/Family_Database/SF_2_4_Share_births_outside_marriage.xlsx"
BOM_RAW_NAME = "sf2_4_births_outside_marriage.xlsx"
BOM_LICENSE = (
    f"{oecd.LICENSE}. Cite: OECD Family Database, SF2.4 Share of births outside of marriage "
    "(https://www.oecd.org/en/data/datasets/oecd-family-database.html, accessed 2026-10-18)."
)
BOM_SHEET = "Births_outside_marriage"
BOM_METRIC = "births_outside_marriage_pct"
BOM_NOT_AVAILABLE = ".."
_BOM_HEADER = ("Country", "Note")
_COHORT_YEAR = re.compile(r"women born in (\d{4})", re.I)
_HEADER_B = ("Permanent childles", "Completed fertility")

Row = dict[str, object]
Grid = list[list[object]]


def _text(cell: object) -> str:
    return " ".join(str(cell).split()) if cell is not None else ""


def _is_year(cell: object) -> bool:
    return isinstance(cell, int) and not isinstance(cell, bool) and 1900 <= cell <= 2100


def _number(cell: object, *, where: str) -> float:
    if isinstance(cell, (int, float)) and not isinstance(cell, bool):
        return float(cell)
    msg = f"{where}: expected a number, got {cell!r}"
    raise ValueError(msg)


def _sheets(payload: bytes, required: tuple[str, ...] = (SHEET_A, SHEET_B)) -> dict[str, Grid]:
    try:
        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception:  # openpyxl raises several unrelated types for non-xlsx bytes
        msg = "payload is not an xlsx workbook"
        raise ValueError(msg) from None
    try:
        grids = {
            ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets
        }
    finally:
        wb.close()
    for name in required:
        if name not in grids:
            msg = f"sheet {name!r} not found (sheets: {sorted(grids)})"
            raise ValueError(msg)
    return grids


def _resolve(name: str, *, where: str) -> tuple[str | None, str | None]:
    """(iso3 to keep, reason dropped). Unknown names fail closed."""
    if name in NOT_COUNTRIES:
        return None, f"{where}: {name} dropped: not a country"
    iso3 = NAME_TO_ISO3.get(name)
    if iso3 is None:
        msg = f"{where}: unknown country name {name!r}"
        raise ValueError(msg)
    if iso3 not in oecd.OECD_MEMBERS:
        return None, f"{where}: {name} ({iso3}) dropped: not an OECD member"
    return iso3, None


def _chart_a(rows: Grid) -> tuple[list[Row], list[str]]:
    header_idx = next((i for i, row in enumerate(rows) if sum(_is_year(c) for c in row) >= 5), None)
    if header_idx is None:
        msg = f"{SHEET_A}: cohort header row (years) not found"
        raise ValueError(msg)
    cohorts = {i: int(str(c)) for i, c in enumerate(rows[header_idx]) if _is_year(c)}
    name_col = min(cohorts) - 1
    out: list[Row] = []
    dropped: list[str] = []
    for row in rows[header_idx + 1 :]:
        name = _text(row[name_col] if len(row) > name_col else None)
        if not name:
            continue
        iso3, reason = _resolve(name, where=SHEET_A)
        if iso3 is None:
            dropped.append(str(reason))
            continue
        for col, cohort in cohorts.items():
            cell = row[col] if col < len(row) else None
            if cell is None or _text(cell) == "":
                continue
            value = _number(cell, where=f"{SHEET_A}: {name} {cohort}")
            out.append(_row(iso3, cohort, METRIC_CHILDLESS, value, CHART_A))
    return out, dropped


def _chart_b(rows: Grid) -> tuple[list[Row], list[str]]:
    cohort = next(
        (int(m.group(1)) for row in rows[:3] for c in row if (m := _COHORT_YEAR.search(_text(c)))),
        None,
    )
    if cohort is None:
        msg = f"{SHEET_B}: cohort year ('women born in YYYY') not found in the subtitle"
        raise ValueError(msg)
    header = next(
        (row for row in rows if all(any(_text(c).startswith(h) for c in row) for h in _HEADER_B)),
        None,
    )
    if header is None:
        msg = f"{SHEET_B}: header row ({' / '.join(_HEADER_B)}) not found"
        raise ValueError(msg)
    childless_col = next(i for i, c in enumerate(header) if _text(c).startswith(_HEADER_B[0]))
    cfr_col = next(i for i, c in enumerate(header) if _text(c).startswith(_HEADER_B[1]))
    name_col, code_col = childless_col - 2, childless_col - 1
    out: list[Row] = []
    dropped: list[str] = []
    seen: dict[str, tuple[float, float]] = {}
    for row in rows:
        name = _text(row[name_col] if len(row) > name_col else None)
        if not name or row is header:
            continue
        code = _text(row[code_col] if len(row) > code_col else None)
        expected = NAME_TO_ISO3.get(name)
        if expected is not None and code != expected:
            msg = f"{SHEET_B}: {name} is coded {code!r}, expected {expected!r}"
            raise ValueError(msg)
        iso3, reason = _resolve(name, where=SHEET_B)
        if iso3 is None:
            dropped.append(str(reason))
            continue
        where = f"{SHEET_B}: {name}"
        values = (
            _number(row[childless_col] if len(row) > childless_col else None, where=where),
            _number(row[cfr_col] if len(row) > cfr_col else None, where=where),
        )
        if iso3 in seen:
            if seen[iso3] != values:
                msg = f"{SHEET_B}: {name} repeated with different values {seen[iso3]} / {values}"
                raise ValueError(msg)
            dropped.append(f"{SHEET_B}: {name} repeated with identical values (kept once)")
            continue
        seen[iso3] = values
        out.append(_row(iso3, cohort, METRIC_CHILDLESS, values[0], CHART_B))
        out.append(_row(iso3, cohort, METRIC_CFR, values[1], CHART_B))
    return out, dropped


def _row(iso3: str, cohort: int, metric: str, value: float, chart: str) -> Row:
    return {
        "iso3": iso3,
        "cohort": cohort,
        "metric": metric,
        "value": value,
        "chart": chart,
        "source": SOURCE,
    }


def parse(payload: bytes) -> tuple[list[Row], list[str]]:
    """xlsx bytes -> (long rows, dropped/notes). Fails closed on layout changes."""
    grids = _sheets(payload)
    rows_a, dropped_a = _chart_a(grids[SHEET_A])
    rows_b, dropped_b = _chart_b(grids[SHEET_B])
    return rows_a + rows_b, dropped_a + dropped_b


def build_mart(rows: Iterable[Row]) -> list[Row]:
    """Sorted by (iso3, cohort, chart, metric); a duplicate key is an error. Pure."""
    out = [dict(r) for r in rows]
    out.sort(
        key=lambda r: (str(r["iso3"]), int(str(r["cohort"])), str(r["chart"]), str(r["metric"]))
    )
    seen: set[tuple[str, int, str, str]] = set()
    for r in out:
        key = (str(r["iso3"]), int(str(r["cohort"])), str(r["chart"]), str(r["metric"]))
        if key in seen:
            msg = f"duplicate key {key}"
            raise ValueError(msg)
        seen.add(key)
    return out


# ---- H11: SF2.4 "Share of births outside of marriage", sheet Births_outside_marriage ----------
# Header row = 'Country' | 'Note' | consecutive integer years (1960 … in the 2026-10-18 file);
# one row per country, '..' = not available (no row). The two chart sheets (latest year, three
# points in time) are derived from this table and are not read. Rows below the data (the '..'
# legend, notes, sources) have nothing in the year columns and are ignored.


def _bom_row(iso3: str, year: int, value: float) -> Row:
    return {
        "iso3": iso3,
        "year": year,
        "metric": BOM_METRIC,
        "value": value,
        "chart": BOM_SHEET,
        "source": SOURCE,
    }


def _bom_header(grid: Grid) -> tuple[int, dict[int, int]]:
    """(header row index, {column: year}); fails closed on a missing or gappy header."""
    for i, row in enumerate(grid):
        if tuple(_text(c) for c in row[:2]) == _BOM_HEADER:
            years = {col: int(str(c)) for col, c in enumerate(row) if col >= 2 and _is_year(c)}
            cols = sorted(years)
            ys = [years[c] for c in cols]
            if len(ys) < 5:
                msg = f"{BOM_SHEET}: header row has {len(ys)} year columns (need 5 or more)"
                raise ValueError(msg)
            if cols != list(range(2, 2 + len(cols))) or ys != list(range(ys[0], ys[0] + len(ys))):
                msg = f"{BOM_SHEET}: year columns must be consecutive from column C, got {ys}"
                raise ValueError(msg)
            return i, years
    msg = f"{BOM_SHEET}: header row ({' | '.join(_BOM_HEADER)} | years) not found"
    raise ValueError(msg)


def parse_births_outside_marriage(payload: bytes) -> tuple[list[Row], list[str]]:
    """SF2.4 xlsx bytes -> (country x year long rows, dropped notes). Fails closed on a missing
    sheet or header, non-consecutive years, an unknown country name, a text where a number is
    expected, or a country listed twice. Non-member rows are dropped and reported."""
    grid = _sheets(payload, required=(BOM_SHEET,))[BOM_SHEET]
    header_idx, years = _bom_header(grid)
    out: list[Row] = []
    dropped: list[str] = []
    seen: set[str] = set()
    for row in grid[header_idx + 1 :]:
        name = _text(row[0] if row else None)
        if not name or all(c is None for c in row[2:]):
            continue  # blank line, the '..' legend, notes and sources
        iso3, reason = _resolve(name, where=BOM_SHEET)
        if iso3 is None:
            dropped.append(str(reason))
            continue
        if iso3 in seen:
            msg = f"{BOM_SHEET}: duplicate country row {name!r} ({iso3})"
            raise ValueError(msg)
        seen.add(iso3)
        for col, year in years.items():
            cell = row[col] if col < len(row) else None
            if cell is None or _text(cell) in ("", BOM_NOT_AVAILABLE):
                continue
            out.append(_bom_row(iso3, year, _number(cell, where=f"{BOM_SHEET}: {name} {year}")))
    return out, dropped


def build_births_outside_marriage_mart(rows: Iterable[Row]) -> list[Row]:
    """Sorted by (iso3, year, chart, metric); a duplicate key is an error. Pure."""
    out = [dict(r) for r in rows]

    def key(r: Row) -> tuple[str, int, str, str]:
        return (str(r["iso3"]), int(str(r["year"])), str(r["chart"]), str(r["metric"]))

    out.sort(key=key)
    seen: set[tuple[str, int, str, str]] = set()
    for r in out:
        k = key(r)
        if k in seen:
            msg = f"duplicate key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out
