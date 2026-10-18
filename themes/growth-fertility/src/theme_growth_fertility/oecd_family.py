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
}  # fmt: skip
NOT_COUNTRIES: frozenset[str] = frozenset({"England and Wales"})
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


def _sheets(payload: bytes) -> dict[str, Grid]:
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
    for name in (SHEET_A, SHEET_B):
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
