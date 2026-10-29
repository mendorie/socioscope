"""Eurostat national accounts by industry (NACE Rev. 2 A*64): gross value added and employment.

Numerator and denominator of the rent indicator R (value added per person employed by the
employer's industry; design/themes/essential-work-wages.md, H6 / H0).

Dissemination API, JSON-stat 2.0, no key. Both datasets share the dimension order
``freq.unit.nace_r2.na_item.geo.time`` (DSD NAMA_10_A64 v135.0 / NAMA_10_A64_E, verified on the
live responses on 2026-10-29):
  nama_10_a64    na_item=B1G (gross value added), unit=CP_MEUR (current prices, million EUR)
  nama_10_a64_e  na_item=EMP_DC (total employment, domestic concept) + SAL_DC (employees),
                 unit=THS_PER (thousand persons)
One request per dataset for 2015-2023 (0.5 MB / 1.0 MB) returns every geo: EU27_2020 and
euro-area aggregates, the 27 member states, IS, LI, NO, CH and the candidates (BA, ME, MK, AL,
RS, TR, UA, XK, not all in both tables). **UK is not in these tables** (dropped after 2020).
nace_r2 has 96 codes: TOTAL, the 21 sections A..U, the A*64 2-digit groups (``C10-C12``,
``J59_J60``, ...) and the multi-section aggregates B-E, G-I, M_N, O-Q, R-U. ``L68A`` is imputed
rents of owner-occupied dwellings (part of L; employment 0 or missing).

Pure transforms (``parse`` / ``build_mart``) have no I/O and fail closed (ValueError) on any
other shape. Cells absent from the sparse ``value`` are not emitted (never imputed); per-person
value added is None when employment is missing or zero. ``flags`` is the JSON-stat ``status``
(e.g. ``p`` provisional, ``e`` estimated); confidential cells (``C``) have no value.

License: Eurostat copyright notice. Reuse (incl. commercial) allowed with source acknowledgement
("Source: Eurostat, nama_10_a64 / nama_10_a64_e (accessed 2026-10-29)").
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from pydantic import BaseModel, ConfigDict

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.pipeline import THEME

SOURCE = "eurostat_nama"
LICENSE = (
    "Eurostat copyright notice (checked 2026-10-29): reuse, including commercial, allowed with "
    "source acknowledgement ('Source: Eurostat'); "
    "https://ec.europa.eu/eurostat/web/main/help/copyright-notice"
)
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
MAGIC = b"{"
MART_TABLE = "marts/nama_industry_value_added_employment"

YEARS: tuple[int, ...] = tuple(range(2015, 2024))
DIMENSIONS: frozenset[str] = frozenset({"freq", "unit", "nace_r2", "na_item", "geo", "time"})

# Eurostat geo code -> ISO 3166-1 alpha-3. EU27 + EFTA + UK + candidates. Aggregates
# (EU27_2020, EA21, EA20, EA19, EA12) are absent on purpose -> None.
GEO_TO_ISO3: dict[str, str] = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "HR": "HRV", "CY": "CYP", "CZ": "CZE", "DK": "DNK",
    "EE": "EST", "FI": "FIN", "FR": "FRA", "DE": "DEU", "EL": "GRC", "HU": "HUN", "IE": "IRL",
    "IT": "ITA", "LV": "LVA", "LT": "LTU", "LU": "LUX", "MT": "MLT", "NL": "NLD", "PL": "POL",
    "PT": "PRT", "RO": "ROU", "SK": "SVK", "SI": "SVN", "ES": "ESP", "SE": "SWE",
    "IS": "ISL", "NO": "NOR", "CH": "CHE", "LI": "LIE", "UK": "GBR",
    "BA": "BIH", "ME": "MNE", "MK": "MKD", "AL": "ALB", "RS": "SRB", "TR": "TUR",
    "UA": "UKR", "XK": "XKX",
}  # fmt: skip


def iso3_of(geo: str) -> str | None:
    return GEO_TO_ISO3.get(geo)


def nace_section(code: str) -> str | None:
    """NACE section letter (A..U) of an A*64 code; None for TOTAL and multi-section aggregates.

    ``C10-C12`` -> ``C``, ``L68A`` -> ``L``, ``K`` -> ``K``; ``B-E`` / ``M_N`` / ``TOTAL`` -> None.
    """
    if not code or not ("A" <= code[0] <= "U"):
        return None
    if len(code) > 1 and not code[1].isdigit():
        return None
    return code[0]


@dataclass(frozen=True)
class Dataset:
    """One Eurostat dataset = one request = one raw file = one staged table."""

    name: str
    tag: str  # short label used in the raw file name
    na_items: tuple[str, ...]
    unit: str

    @property
    def raw_name(self) -> str:
        return f"{self.name}_{self.tag}_{YEARS[0]}_{YEARS[-1]}.json"

    @property
    def staged_table(self) -> str:
        return f"staged/nama/{self.name}"

    @property
    def url(self) -> str:
        query = "".join(f"&na_item={c}" for c in self.na_items)
        query += f"&unit={self.unit}"
        query += "".join(f"&time={y}" for y in YEARS)
        return f"{BASE}/{self.name}?format=JSON&lang=EN{query}"


DATASETS: tuple[Dataset, ...] = (
    Dataset("nama_10_a64", "b1g", ("B1G",), "CP_MEUR"),
    Dataset("nama_10_a64_e", "emp", ("EMP_DC", "SAL_DC"), "THS_PER"),
)

STAGED_COLUMNS: tuple[str, ...] = (
    "geo",
    "year",
    "nace_r2",
    "nace_r2_label",
    "na_item",
    "unit",
    "value",
    "flags",
)
MART_COLUMNS: tuple[str, ...] = (
    "iso3",
    "geo",
    "year",
    "nace_r2",
    "nace_r2_label",
    "nace_section",
    "value_added_meur",
    "employment_ths",
    "employees_ths",
    "value_added_per_person_keur",
    "flags",
    "source",
)
MART_KEY: tuple[str, ...] = ("geo", "year", "nace_r2")
ITEM_COLUMN: dict[str, str] = {
    "B1G": "value_added_meur",
    "EMP_DC": "employment_ths",
    "SAL_DC": "employees_ths",
}


# ---------------------------------------------------------------- JSON-stat 2.0 (pure)


class _Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    index: dict[str, int] | list[str]
    label: dict[str, str] = {}


class _Dimension(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: _Category


class _Doc(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: list[str]
    size: list[int]
    dimension: dict[str, _Dimension]
    value: dict[str, float | None] | list[float | None]
    status: dict[str, str] | list[str | None] | str | None = None


def _codes(cat: _Category, size: int, dim: str) -> list[str]:
    index = cat.index
    codes = list(index) if isinstance(index, list) else sorted(index, key=index.__getitem__)
    if len(codes) != size:
        msg = f"JSON-stat size mismatch for {dim!r}: {len(codes)} categories, size {size}"
        raise ValueError(msg)
    return codes


def _load(payload: bytes) -> _Doc:
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"Eurostat response is not JSON: {e}"
        raise ValueError(msg) from None
    if not isinstance(doc, dict):
        msg = "Eurostat response is not a JSON object"
        raise ValueError(msg)
    if "error" in doc:
        msg = f"Eurostat API error: {doc['error']}"
        raise ValueError(msg)
    if doc.get("class") != "dataset":
        msg = f"JSON-stat class {doc.get('class')!r}, expected 'dataset'"
        raise ValueError(msg)
    ds = _Doc.model_validate(doc)
    if len(ds.id) != len(ds.size) or any(d not in ds.dimension for d in ds.id):
        msg = f"JSON-stat id/size/dimension mismatch: id={ds.id} size={ds.size}"
        raise ValueError(msg)
    return ds


def _status_map(ds: _Doc) -> dict[str, str]:
    st = ds.status
    if isinstance(st, dict):
        return st
    if isinstance(st, list):
        return {str(i): s for i, s in enumerate(st) if s}
    return {}  # one flag for every cell (str) or none: not informative per row


def _check_axes(spec: Dataset, axes: dict[str, list[str]]) -> None:
    if axes["freq"] != ["A"]:
        msg = f"{spec.name}: dimension freq is {axes['freq']}, expected ['A']"
        raise ValueError(msg)
    if axes["unit"] != [spec.unit]:
        msg = f"{spec.name}: dimension unit is {axes['unit']}, expected [{spec.unit!r}]"
        raise ValueError(msg)
    if set(axes["na_item"]) - set(spec.na_items):
        msg = f"{spec.name}: na_item {axes['na_item']} outside {list(spec.na_items)}"
        raise ValueError(msg)
    bad = [t for t in axes["time"] if not (t.isdigit() and int(t) in YEARS)]
    if bad:
        msg = f"{spec.name}: time {bad} outside {YEARS[0]}-{YEARS[-1]}"
        raise ValueError(msg)


def staged_key(r: dict[str, object]) -> tuple[str, int, str, str]:
    return (str(r["geo"]), int(str(r["year"])), str(r["nace_r2"]), str(r["na_item"]))


def parse(payload: bytes, spec: Dataset) -> list[dict[str, object]]:
    """JSON-stat -> staged rows (STAGED_COLUMNS), sorted by staged_key. Pure, fail closed."""
    ds = _load(payload)
    if set(ds.id) != DIMENSIONS:
        msg = f"{spec.name}: dimensions {sorted(ds.id)} differ from {sorted(DIMENSIONS)}"
        raise ValueError(msg)
    axes = {d: _codes(ds.dimension[d].category, n, d) for d, n in zip(ds.id, ds.size, strict=True)}
    _check_axes(spec, axes)
    nace_labels = ds.dimension["nace_r2"].category.label
    values = {str(i): v for i, v in enumerate(ds.value)} if isinstance(ds.value, list) else ds.value
    status = _status_map(ds)
    out: list[dict[str, object]] = []
    for i, combo in enumerate(product(*(axes[d] for d in ds.id))):
        v = values.get(str(i))
        if v is None:
            continue
        cell = dict(zip(ds.id, combo, strict=True))
        out.append(
            {
                "geo": cell["geo"],
                "year": int(cell["time"]),
                "nace_r2": cell["nace_r2"],
                "nace_r2_label": nace_labels.get(cell["nace_r2"], ""),
                "na_item": cell["na_item"],
                "unit": cell["unit"],
                "value": float(v),
                "flags": status.get(str(i)),
            }
        )
    out.sort(key=staged_key)
    return out


# ---------------------------------------------------------------- mart (pure)


def _mart_key(r: dict[str, object]) -> tuple[str, int, str]:
    return (str(r["geo"]), int(str(r["year"])), str(r["nace_r2"]))


def _per_person(va: object, emp: object) -> float | None:
    if va is None or emp is None or float(str(emp)) == 0.0:
        return None
    return float(str(va)) / float(str(emp))  # MEUR / thousand persons = thousand EUR per person


def build_mart(staged: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """``marts/nama_industry_value_added_employment``: one row per (geo, year, nace_r2) with
    value added (B1G), employment (EMP_DC), employees (SAL_DC) side by side, iso3 (None for
    aggregates), ``nace_section`` and value added per person employed (thousand EUR; None when
    employment is missing or 0). Duplicate staged keys or unknown na_item raise ValueError."""
    wide: dict[tuple[str, int, str], dict[str, object]] = {}
    seen: set[tuple[str, int, str, str]] = set()
    for r in staged:
        item = str(r["na_item"])
        if item not in ITEM_COLUMN:
            msg = f"nama: na_item {item!r} outside {sorted(ITEM_COLUMN)}"
            raise ValueError(msg)
        sk = staged_key(r)
        if sk in seen:
            msg = f"nama: duplicate key (geo, year, nace_r2, na_item) = {sk}"
            raise ValueError(msg)
        seen.add(sk)
        k = _mart_key(r)
        row = wide.setdefault(
            k,
            {
                "iso3": iso3_of(k[0]),
                "geo": k[0],
                "year": k[1],
                "nace_r2": k[2],
                "nace_r2_label": r["nace_r2_label"],
                "nace_section": nace_section(k[2]),
                "value_added_meur": None,
                "employment_ths": None,
                "employees_ths": None,
                "value_added_per_person_keur": None,
                "flags": None,
                "source": SOURCE,
            },
        )
        row[ITEM_COLUMN[item]] = float(str(r["value"]))
        if r.get("flags"):
            row["flags"] = r["flags"]
    out: list[dict[str, object]] = []
    for k in sorted(wide):
        row = wide[k]
        row["value_added_per_person_keur"] = _per_person(
            row["value_added_meur"], row["employment_ths"]
        )
        out.append({c: row[c] for c in MART_COLUMNS})
    return out


# ---------------------------------------------------------------- stages (I/O via ports)


def fetch(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for d in DATASETS:
        try:
            payload = ctx.fetcher.fetch(d.url)
        except FetchError as e:
            skipped.append(f"{d.raw_name}: {e}")
            continue
        if not payload.startswith(MAGIC):
            skipped.append(f"{d.raw_name}: non-JSON payload")
            continue
        rec = ctx.raw.put(
            theme=THEME, source=SOURCE, name=d.raw_name, url=d.url, license=LICENSE, payload=payload
        )
        written.append(rec.relative_path)
    return written, skipped


def stage(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for d in DATASETS:
        payload = ctx.raw.get(theme=THEME, source=SOURCE, name=d.raw_name)
        if payload is None:
            skipped.append(f"{d.raw_name}: no raw")
            continue
        try:
            rows = parse(payload, d)
        except ValueError as e:
            skipped.append(f"{d.raw_name}: {e}")
            continue
        ctx.tables.write_table(d.staged_table, rows)
        written.append(d.staged_table)
    return written, skipped


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    staged: list[dict[str, object]] = []
    found = False
    for d in DATASETS:
        try:
            staged.extend(ctx.tables.read_table(d.staged_table))
            found = True
        except FileNotFoundError:
            skipped.append(f"{d.staged_table}: no staged table")
    if not found:
        return written, skipped
    ctx.tables.write_table(MART_TABLE, build_mart(staged))
    written.append(MART_TABLE)
    return written, skipped
