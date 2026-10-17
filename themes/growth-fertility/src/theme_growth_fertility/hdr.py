"""UNDP Human Development Report 2025 composite indices CSV -> long rows (no I/O).

H8d. One static CSV (latin-1, wide: ``iso3, country, hdicode, region, hdi_rank_2023, hdi_1990,
..., gii_1990 ... gii_2023, mmr_YYYY, abr_YYYY, se_f_YYYY, ..., lfpr_m_YYYY, ...``). Only the
nine gender-related :data:`METRICS` are taken (``<metric>_<YYYY>`` columns); other columns
(other prefixes, ``gii_rank_2023``, ``hdicode``, ``region``, ...) are ignored. Aggregate rows
(``iso3`` not three capital letters, e.g. ``ZZK.WORLD``) are dropped and reported. Blank cells
are dropped (never imputed); a non-blank cell that is not a number, a missing ``iso3``/``country``
header or a file with none of the nine metrics is a ``ValueError``.

Output columns: ``iso3, country, year, metric, value, source``.
"""

import csv
import io
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "LICENSE",
    "METRICS",
    "RAW_NAME",
    "SOURCE",
    "URL",
    "Parsed",
    "build_mart",
    "mart_key",
    "parse",
]

URL = (
    "https://hdr.undp.org/sites/default/files/2025_HDR/"
    "HDR25_Composite_indices_complete_time_series.csv"
)
METADATA_URL = (
    "https://hdr.undp.org/sites/default/files/2025_HDR/HDR25_Composite_indices_metadata.xlsx"
)
RAW_NAME = "hdr25_composite_indices.csv"
SOURCE = "undp_hdr"
LICENSE = (
    "CC BY 3.0 IGO (https://hdr.undp.org/terms-use). Cite: UNDP (2025), Human Development "
    "Report 2025, composite indices time series, https://hdr.undp.org (accessed 2026-10-18), "
    "CC BY 3.0 IGO"
)
ENCODING = "latin-1"
METRICS: tuple[str, ...] = ("gii", "mmr", "abr", "se_f", "se_m", "pr_f", "pr_m", "lfpr_f", "lfpr_m")
REQUIRED_COLUMNS = ("iso3", "country")
MART_KEY = ("iso3", "year", "metric")
# Only `<metric>_<YYYY>` cells; `gii_rank_2023`, `hdi_rank_2023`, `hdicode`, ... are left alone.
_METRIC_COLUMN = re.compile(r"^(?P<metric>" + "|".join(METRICS) + r")_(?P<year>\d{4})$")
_ISO3 = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class Parsed:
    rows: list[dict[str, object]]
    dropped_areas: tuple[str, ...]  # "iso3 country" of aggregate rows, sorted
    blank_cells: int  # metric cells left empty upstream (dropped, not imputed)


def _metric_columns(fields: Sequence[str]) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    for col in fields:
        m = _METRIC_COLUMN.match(col)
        if m is None:
            continue
        out.append((col, m["metric"], int(m["year"])))
    if not out:
        msg = f"no HDR metric columns ({', '.join(METRICS)}) in header"
        raise ValueError(msg)
    return out


def parse(payload: bytes) -> Parsed:
    """CSV bytes (latin-1) -> long rows sorted by :data:`MART_KEY`."""
    reader = csv.DictReader(io.StringIO(payload.decode(ENCODING)))
    fields = list(reader.fieldnames or ())
    missing = [c for c in REQUIRED_COLUMNS if c not in fields]
    if missing:
        msg = f"unexpected HDR header: missing {missing}"
        raise ValueError(msg)
    columns = _metric_columns(fields)
    rows: list[dict[str, object]] = []
    dropped: set[str] = set()
    blank = 0
    for raw in reader:
        iso3 = raw["iso3"]
        if not _ISO3.match(iso3):
            dropped.add(f"{iso3} {raw['country']}")
            continue
        for col, metric, year in columns:
            cell = raw[col]
            if cell is None or cell == "":
                blank += 1
                continue
            try:
                value = float(cell)
            except ValueError as e:
                msg = f"non-numeric HDR cell {col}={cell!r} for {iso3}"
                raise ValueError(msg) from e
            rows.append(
                {
                    "iso3": iso3,
                    "country": raw["country"],
                    "year": year,
                    "metric": metric,
                    "value": value,
                    "source": SOURCE,
                }
            )
    rows.sort(key=mart_key)
    return Parsed(rows=rows, dropped_areas=tuple(sorted(dropped)), blank_cells=blank)


def mart_key(row: Mapping[str, object]) -> tuple[str, int, str]:
    return (str(row["iso3"]), int(str(row["year"])), str(row["metric"]))


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Sort the staged rows by :data:`MART_KEY`; duplicate keys fail."""
    rows = [dict(r) for r in staged]
    rows.sort(key=mart_key)
    seen: set[tuple[str, int, str]] = set()
    for r in rows:
        k = mart_key(r)
        if k in seen:
            msg = f"duplicate HDR mart key {k}"
            raise ValueError(msg)
        seen.add(k)
    return rows
