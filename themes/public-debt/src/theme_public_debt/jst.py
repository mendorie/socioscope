"""Jordà–Schularick–Taylor Macrohistory Database R6 (macrohistory.net): one xlsx, 18 advanced
economies × 1870–2020. Pure transforms only (no I/O).

Columns used (R6 codes): iso, year, country, pop, gdp (nominal, LCU), cpi (1990 = 100), stir,
ltrate (% p.a.), debtgdp (public debt ÷ GDP, fraction), revenue / expenditure (nominal, LCU),
tloans / thh / tbus (loans to non-financial private sector / households / business, LCU),
crisisJST (0/1). Any missing column is a ValueError (fail-closed): the mart is built from
exactly these series and a renamed column must not silently drop a hypothesis.

License: CC BY-NC-SA 4.0 (https://www.macrohistory.net/database/, confirmed 2026-11-03).
Citation: Jordà, Schularick & Taylor (2017), NBER Macroeconomics Annual 2016.
"""

from __future__ import annotations

import io
import re
from collections.abc import Sequence

SOURCE = "jst"
LICENSE = (
    "CC BY-NC-SA 4.0 (Jordà-Schularick-Taylor Macrohistory Database R6, "
    "https://www.macrohistory.net/database/, non-commercial, cite JST 2017)"
)
URL = "https://www.macrohistory.net/app/download/9834512569/JSTdatasetR6.xlsx"
RAW_NAME = "JSTdatasetR6.xlsx"
MAGIC = b"PK"  # xlsx is a zip

# source column -> staged column
COLUMNS: dict[str, str] = {
    "iso": "iso3",
    "year": "year",
    "country": "country",
    "pop": "pop",
    "gdp": "gdp",
    "cpi": "cpi",
    "stir": "stir",
    "ltrate": "ltrate",
    "debtgdp": "debtgdp",
    "revenue": "revenue",
    "expenditure": "expenditure",
    "tloans": "tloans",
    "thh": "thh",
    "tbus": "tbus",
    "crisisJST": "crisis_jst",
}
_ISO3 = re.compile(r"^[A-Z]{3}$")
MIN_COUNTRIES = 17  # R5 had 17, R6 added Ireland; fewer means a truncated file
STAGED_TABLE = "staged/jst/macrohistory"
MART_TABLE = "marts/jst_debt_panel"

Rows = list[list[object]]


def workbook_rows(payload: bytes) -> list[tuple[str, Rows]]:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as e:
        msg = "jst: payload is not a readable xlsx"
        raise ValueError(msg) from e
    return [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)]) for ws in wb.worksheets]


def _num(v: object) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int | float):
        return float(v)
    s = str(v).strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse(sheets: Sequence[tuple[str, Rows]]) -> list[dict[str, object]]:
    """→ staged rows [{iso3, year, country, pop, gdp, cpi, stir, ltrate, debtgdp, revenue,
    expenditure, tloans, thh, tbus, crisis_jst, source}], sorted by (iso3, year).

    The data sheet is the first one whose header row holds every column in ``COLUMNS``.
    """
    header: list[str] | None = None
    body: Rows = []
    for _title, rows in sheets:
        if not rows:
            continue
        hdr = [str(c).strip() if c is not None else "" for c in rows[0]]
        if all(c in hdr for c in COLUMNS):
            header, body = hdr, rows[1:]
            break
    if header is None:
        missing = sorted(
            set(COLUMNS) - {str(c).strip() for _t, rows in sheets if rows for c in rows[0] if c}
        )
        msg = f"jst: no sheet with the expected header (missing {missing})"
        raise ValueError(msg)
    idx = {src: header.index(src) for src in COLUMNS}
    out: list[dict[str, object]] = []
    for row in body:
        if len(row) <= max(idx.values()):
            continue
        iso = str(row[idx["iso"]] or "").strip()
        year = _num(row[idx["year"]])
        if not _ISO3.match(iso) or year is None:
            continue
        rec: dict[str, object] = {"iso3": iso, "year": int(year)}
        rec["country"] = str(row[idx["country"]] or "").strip()
        for src, dst in COLUMNS.items():
            if src in ("iso", "year", "country"):
                continue
            rec[dst] = _num(row[idx[src]])
        rec["source"] = SOURCE
        out.append(rec)
    countries = {r["iso3"] for r in out}
    if len(countries) < MIN_COUNTRIES:
        msg = f"jst: only {len(countries)} countries parsed (expected >= {MIN_COUNTRIES})"
        raise ValueError(msg)
    out.sort(key=lambda r: (str(r["iso3"]), int(str(r["year"]))))
    return out


# ---- mart: long panel (iso3, year, unit, metric, value, source) ---------------------------------
# unit tells which debt definition a value belongs to so that different definitions are never
# compared by accident (design/themes/public-debt.md 既知の落とし穴). JST public debt is general
# government gross debt for most country-years (central government in some early years; the
# documentation lists the breaks), so the unit is ``general_gov_gross`` with that caveat.

UNIT_PUBLIC = "general_gov_gross"
UNIT_HH = "households"
UNIT_NFC = "nfc"
UNIT_PRIVATE = "private_nonfin"
UNIT_TOTAL = "total_nonfin"
UNIT_MACRO = "macro"


def _ratio_pct(num: object, den: object) -> float | None:
    if isinstance(num, int | float) and isinstance(den, int | float) and den != 0:
        return 100.0 * float(num) / float(den)
    return None


def _growth_pct(cur: object, prev: object) -> float | None:
    if isinstance(cur, int | float) and isinstance(prev, int | float) and prev > 0:
        return 100.0 * (float(cur) / float(prev) - 1.0)
    return None


def build_mart(staged: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Staged rows → long panel rows. Metrics per (iso3, year):

    - unit=general_gov_gross: debt_gdp (%), fiscal_balance_gdp (% = (revenue − expenditure)/gdp;
      this is the *overall* balance, interest included, not the primary balance)
    - unit=households / nfc / private_nonfin: debt_gdp (% of GDP)
    - unit=total_nonfin: debt_gdp = public + private_nonfin
    - unit=macro: ltrate, stir (% p.a.), ngdp_growth, cpi_inflation (% vs previous year),
      crisis_jst (0/1), pop
    Years without a previous observation have no growth metric. Rows with a None value are not
    emitted. Sorted by (iso3, year, unit, metric).
    """
    rows = sorted(staged, key=lambda r: (str(r["iso3"]), int(str(r["year"]))))
    prev: dict[str, dict[str, object]] = {}
    out: list[dict[str, object]] = []

    def emit(r: dict[str, object], unit: str, metric: str, value: float | None) -> None:
        if value is None:
            return
        out.append(
            {
                "iso3": r["iso3"],
                "year": r["year"],
                "unit": unit,
                "metric": metric,
                "value": value,
                "source": SOURCE,
            }
        )

    for r in rows:
        iso = str(r["iso3"])
        p = prev.get(iso)
        contiguous = p is not None and int(str(p["year"])) == int(str(r["year"])) - 1
        debt = r.get("debtgdp")
        public = 100.0 * float(debt) if isinstance(debt, int | float) else None
        emit(r, UNIT_PUBLIC, "debt_gdp", public)
        bal = r.get("revenue"), r.get("expenditure")
        if isinstance(bal[0], int | float) and isinstance(bal[1], int | float):
            emit(r, UNIT_PUBLIC, "fiscal_balance_gdp", _ratio_pct(bal[0] - bal[1], r.get("gdp")))
        emit(r, UNIT_HH, "debt_gdp", _ratio_pct(r.get("thh"), r.get("gdp")))
        emit(r, UNIT_NFC, "debt_gdp", _ratio_pct(r.get("tbus"), r.get("gdp")))
        private = _ratio_pct(r.get("tloans"), r.get("gdp"))
        emit(r, UNIT_PRIVATE, "debt_gdp", private)
        if public is not None and private is not None:
            emit(r, UNIT_TOTAL, "debt_gdp", public + private)
        emit(r, UNIT_MACRO, "ltrate", _num(r.get("ltrate")))
        emit(r, UNIT_MACRO, "stir", _num(r.get("stir")))
        emit(r, UNIT_MACRO, "pop", _num(r.get("pop")))
        emit(r, UNIT_MACRO, "crisis_jst", _num(r.get("crisis_jst")))
        if contiguous and p is not None:
            emit(r, UNIT_MACRO, "ngdp_growth", _growth_pct(r.get("gdp"), p.get("gdp")))
            emit(r, UNIT_MACRO, "cpi_inflation", _growth_pct(r.get("cpi"), p.get("cpi")))
        prev[iso] = r
    out.sort(key=lambda x: (str(x["iso3"]), int(str(x["year"])), str(x["unit"]), str(x["metric"])))
    return out
