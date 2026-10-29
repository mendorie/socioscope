"""OECD Health Statistics: Remuneration of health professionals (SDMX CSV, no key).

Dataflow ``OECD.ELS.HD,DSD_HEALTH_REAC_EMP@DF_REMUN`` (version 1.1 on 2026-10-29), one request
(``csvfilewithlabels``, startPeriod=2010, ~3.7 MB, 11,703 rows, 41 countries, 2010-2025).

Dimensions and codes seen in the live file:
  MEASURE        AI only (Annual income)
  UNIT_MEASURE   XDC national currency / USD_PPP / USD_EXC / FCTR_B1GQ_POP (factor of GDP per
                 capita) / **FCTR_WG_A_SAL_A (factor of average annual wage)** = the "ratio to
                 average wage" of Health at a Glance
  HEALTH_PROF    RINF hospital nurses / EMPLGENP general practitioners / EMPLSPMP specialists
  WORKER_STATUS  ICSE93_1 employees / ICSE93_2T5 self-employed
  SEX            _T / M / F   (part of the key; AGE and HEALTH_PROF_ACTIVITY_STATUS are _Z)
  PRICE_BASE     V current prices

For the theme (H3c / H4b) the nurse-to-average-wage ratio is
``health_prof='RINF', unit='FCTR_WG_A_SAL_A', worker_status='ICSE93_1', sex='_T'``; the GP and
specialist ratios use the same unit with ``EMPLGENP`` / ``EMPLSPMP`` (employees or self-employed).

License: OECD Terms & Conditions (2024-07-01, free use with attribution,
https://www.oecd.org/en/about/terms-conditions.html). Citation: "OECD (2026), Health
Statistics: Remuneration of health professionals, https://sdmx.oecd.org (accessed 2026-10-29)".
"""

import csv
import io
from collections.abc import Sequence

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.pipeline import THEME

SOURCE = "oecd_health_remun"
LICENSE = (
    "OECD Terms & Conditions 2024-07-01 (free use with attribution, "
    "https://www.oecd.org/en/about/terms-conditions.html)"
)
URL = (
    "https://sdmx.oecd.org/public/rest/data/OECD.ELS.HD,DSD_HEALTH_REAC_EMP@DF_REMUN,/all"
    "?format=csvfilewithlabels&startPeriod=2010"
)
RAW_NAME = "remuneration.csv"
MAGIC = b"STRUCTURE,"
STAGED_TABLE = "staged/oecd_health_remun/remuneration"
MART_TABLE = "marts/oecd_health_remuneration"

STRUCTURE_PREFIX = "OECD.ELS.HD:DSD_HEALTH_REAC_EMP@DF_REMUN"
MEASURES = frozenset({"AI"})
UNITS = frozenset({"XDC", "USD_PPP", "USD_EXC", "FCTR_B1GQ_POP", "FCTR_WG_A_SAL_A"})
HEALTH_PROFS = frozenset({"RINF", "EMPLGENP", "EMPLSPMP"})
WORKER_STATUSES = frozenset({"ICSE93_1", "ICSE93_2T5"})
SEXES = frozenset({"_T", "M", "F"})

REQUIRED_COLUMNS: tuple[str, ...] = (
    "STRUCTURE_ID",
    "REF_AREA",
    "MEASURE",
    "UNIT_MEASURE",
    "HEALTH_PROF",
    "Health profession",
    "WORKER_STATUS",
    "SEX",
    "PRICE_BASE",
    "TIME_PERIOD",
    "OBS_VALUE",
    "OBS_STATUS",
)
KEY: tuple[str, ...] = (
    "iso3",
    "year",
    "measure",
    "unit",
    "health_prof",
    "worker_status",
    "sex",
    "price_base",
)


def key_of(r: dict[str, object]) -> tuple[str, int, str, str, str, str, str, str]:
    return (
        str(r["iso3"]),
        int(str(r["year"])),
        str(r["measure"]),
        str(r["unit"]),
        str(r["health_prof"]),
        str(r["worker_status"]),
        str(r["sex"]),
        str(r["price_base"]),
    )


def _allowed(row: dict[str, str], col: str, allowed: frozenset[str]) -> str:
    v = row[col]
    if v not in allowed:
        msg = f"oecd_remun: {col} {v!r} outside {sorted(allowed)}"
        raise ValueError(msg)
    return v


def _check_duplicates(rows: list[dict[str, object]]) -> None:
    seen: set[tuple[object, ...]] = set()
    for r in rows:
        k = key_of(r)
        if k in seen:
            msg = f"oecd_remun: duplicate key {KEY} = {k}"
            raise ValueError(msg)
        seen.add(k)


def parse(payload: bytes) -> list[dict[str, object]]:
    """CSV (csvfilewithlabels) -> staged long rows, sorted by KEY. Pure, fail closed.

    Empty OBS_VALUE rows are dropped (nothing imputed); any code outside the closed sets, a
    different STRUCTURE_ID, a non-annual TIME_PERIOD, a non-numeric OBS_VALUE or a duplicate key
    raises ValueError.
    """
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    header = reader.fieldnames or []
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        msg = f"oecd_remun: missing columns {missing}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for row in reader:
        if not row["STRUCTURE_ID"].startswith(STRUCTURE_PREFIX):
            msg = f"oecd_remun: unexpected STRUCTURE_ID {row['STRUCTURE_ID']!r}"
            raise ValueError(msg)
        if row["OBS_VALUE"] == "":
            continue
        try:
            value = float(row["OBS_VALUE"])
        except ValueError:
            msg = f"oecd_remun: non-numeric OBS_VALUE {row['OBS_VALUE']!r}"
            raise ValueError(msg) from None
        period = row["TIME_PERIOD"]
        if not (len(period) == 4 and period.isdigit()):
            msg = f"oecd_remun: TIME_PERIOD {period!r} is not a year"
            raise ValueError(msg)
        iso3 = row["REF_AREA"]
        if len(iso3) != 3 or not iso3.isalpha():
            msg = f"oecd_remun: REF_AREA {iso3!r} is not ISO3"
            raise ValueError(msg)
        out.append(
            {
                "iso3": iso3,
                "year": int(period),
                "measure": _allowed(row, "MEASURE", MEASURES),
                "unit": _allowed(row, "UNIT_MEASURE", UNITS),
                "health_prof": _allowed(row, "HEALTH_PROF", HEALTH_PROFS),
                "health_prof_label": row["Health profession"],
                "worker_status": _allowed(row, "WORKER_STATUS", WORKER_STATUSES),
                "sex": _allowed(row, "SEX", SEXES),
                "price_base": row["PRICE_BASE"],
                "value": value,
                "obs_status": row["OBS_STATUS"],
            }
        )
    out.sort(key=key_of)
    _check_duplicates(out)
    return out


def build_mart(staged: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """``marts/oecd_health_remuneration``: every staged row + source, sorted by KEY, keys unique."""
    out = [{**r, "source": SOURCE} for r in staged]
    out.sort(key=key_of)
    _check_duplicates(out)
    return out


# ---------------------------------------------------------------- stages (I/O via ports)


def fetch(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    try:
        payload = ctx.fetcher.fetch(URL)
    except FetchError as e:
        skipped.append(f"{RAW_NAME}: {e}")
        return written, skipped
    if not payload.startswith(MAGIC):
        skipped.append(f"{RAW_NAME}: non-CSV payload")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME, source=SOURCE, name=RAW_NAME, url=URL, license=LICENSE, payload=payload
    )
    written.append(rec.relative_path)
    return written, skipped


def stage(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    payload = ctx.raw.get(theme=THEME, source=SOURCE, name=RAW_NAME)
    if payload is None:
        skipped.append(f"{RAW_NAME}: no raw")
        return written, skipped
    try:
        rows = parse(payload)
    except ValueError as e:
        skipped.append(f"{RAW_NAME}: {e}")
        return written, skipped
    ctx.tables.write_table(STAGED_TABLE, rows)
    written.append(STAGED_TABLE)
    return written, skipped


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(STAGED_TABLE)
    except FileNotFoundError:
        skipped.append(f"{STAGED_TABLE}: no staged table")
        return written, skipped
    ctx.tables.write_table(MART_TABLE, build_mart(staged))
    written.append(MART_TABLE)
    return written, skipped
