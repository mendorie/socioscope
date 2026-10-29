"""Eurostat Structure of Earnings Survey (SES) 2018 / 2022: mean hourly earnings (EUR) by
occupation (ISCO-08 major groups) x economic activity (NACE Rev. 2 sections) x sex.

Dissemination API, JSON-stat 2.0, no key. Datasets (dimension codes verified on 2026-10-29):
  earn_ses22_47 / earn_ses18_47  freq.sex.indic_se.isco08.sizeclas.nace_r2.unit.geo.time
                                 (2018: freq.indic_se.isco08.nace_r2.sex.sizeclas.unit.geo.time)
  earn_ses22_14 / earn_ses18_14  freq.sex.indic_se.age.sizeclas.isco08.unit.geo.time
                                 ("NACE B-S excluding O"; occupation totals, age=TOTAL)
Fixed filters: unit=EUR, indic_se=ERN (gross earnings = the mean hourly earnings of the table),
sizeclas=TOTAL, sex=T/M/F (and age=TOTAL for *_14). One request per dataset returns every geo
(37 in 2022, 41 in 2018; ~230 KB), so no per-country split.

isco08 has 14 codes: TOTAL, OC1..OC9 (1-digit major groups), OC0 (armed forces) and the
aggregates OC1-5 / OC6-8 / OC7-9. **No 2-digit ISCO**, so nurses (ISCO 22/32) cannot be
separated from care workers (ISCO 53) here. nace_r2 has 29 codes: sections B..S (no A, T, U)
plus aggregates B-S, B-S_X_O, B-N, B-F, B-E, G-S, G-S_X_O, G-J, K-N, O-S, P-S.

Pure transforms (``parse`` / ``build_*_mart``) have no I/O and fail closed (ValueError) when
the payload is not the expected JSON-stat shape. Cells absent from the sparse ``value`` are
not emitted (never imputed). ``flags`` comes from JSON-stat ``status`` when present (the live
responses carry none).

License: Eurostat copyright notice. Reuse (incl. commercial) allowed with source
acknowledgement ("Source: Eurostat, earn_ses22_47 (accessed 2026-10-29)").
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from pydantic import BaseModel, ConfigDict

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.pipeline import THEME

SOURCE = "eurostat_ses"
LICENSE = (
    "Eurostat copyright notice (checked 2026-10-29): reuse, including commercial, allowed with "
    "source acknowledgement ('Source: Eurostat'); "
    "https://ec.europa.eu/eurostat/web/main/help/copyright-notice"
)
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
MAGIC = b"{"

INDUSTRY_MART = "marts/ses_occupation_industry_earnings"
OCCUPATION_MART = "marts/ses_occupation_earnings"

# Scope of the *_14 tables (no nace_r2 dimension); the code is the one earn_ses*_47 uses.
NACE_B_S_X_O = "B-S_X_O"
NACE_B_S_X_O_LABEL = (
    "Industry, construction and services (except public administration, defense, "
    "compulsory social security)"
)

# Eurostat geo code -> ISO 3166-1 alpha-3. EU27 + EFTA + UK + candidates present in SES.
# Aggregates (EU27_2020, EU28, EU27_2007, EA20, EA19, EA18, EA17) are absent on purpose -> None.
GEO_TO_ISO3: dict[str, str] = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "HR": "HRV", "CY": "CYP", "CZ": "CZE", "DK": "DNK",
    "EE": "EST", "FI": "FIN", "FR": "FRA", "DE": "DEU", "EL": "GRC", "HU": "HUN", "IE": "IRL",
    "IT": "ITA", "LV": "LVA", "LT": "LTU", "LU": "LUX", "MT": "MLT", "NL": "NLD", "PL": "POL",
    "PT": "PRT", "RO": "ROU", "SK": "SVK", "SI": "SVN", "ES": "ESP", "SE": "SWE",
    "IS": "ISL", "NO": "NOR", "CH": "CHE", "LI": "LIE", "UK": "GBR",
    "BA": "BIH", "MK": "MKD", "AL": "ALB", "RS": "SRB", "TR": "TUR",
}  # fmt: skip


def iso3_of(geo: str) -> str | None:
    return GEO_TO_ISO3.get(geo)


@dataclass(frozen=True)
class Dataset:
    """One Eurostat dataset = one request = one raw file = one staged table."""

    name: str  # e.g. earn_ses22_47
    year: int
    kind: str  # "47" (occupation x industry) or "14" (occupation totals)

    @property
    def tag(self) -> str:
        return f"ses{self.year % 100}_{self.kind}"

    @property
    def raw_name(self) -> str:
        return f"{self.tag}.json"

    @property
    def staged_table(self) -> str:
        return f"staged/ses/{self.name}"

    @property
    def fixed(self) -> dict[str, str]:
        """Dimensions that must have exactly this single code in the response."""
        f = {"freq": "A", "unit": "EUR", "indic_se": "ERN", "sizeclas": "TOTAL"}
        if self.kind == "14":
            f["age"] = "TOTAL"
        return f

    @property
    def dimensions(self) -> frozenset[str]:
        extra = {"nace_r2"} if self.kind == "47" else {"age"}
        return frozenset(
            {"freq", "sex", "indic_se", "isco08", "sizeclas", "unit", "geo", "time"} | extra
        )

    @property
    def url(self) -> str:
        params = [(k, v) for k, v in self.fixed.items() if k != "freq"]
        params += [("sex", s) for s in ("T", "M", "F")]
        query = "".join(f"&{k}={v}" for k, v in params)
        return f"{BASE}/{self.name}?format=JSON&lang=EN{query}"


DATASETS: tuple[Dataset, ...] = (
    Dataset("earn_ses22_47", 2022, "47"),
    Dataset("earn_ses22_14", 2022, "14"),
    Dataset("earn_ses18_47", 2018, "47"),
    Dataset("earn_ses18_14", 2018, "14"),
)

STAGED_COLUMNS: tuple[str, ...] = (
    "geo",
    "year",
    "isco08",
    "isco08_label",
    "nace_r2",
    "nace_r2_label",
    "sex",
    "hourly_earnings_eur",
    "flags",
)
INDUSTRY_KEY: tuple[str, ...] = ("geo", "year", "isco08", "nace_r2", "sex")
OCCUPATION_KEY: tuple[str, ...] = ("geo", "year", "isco08", "sex")


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
    if isinstance(st, str):
        return {}  # one flag for every cell: not informative per row; ignored
    return {}


def _check_fixed(ds: _Doc, spec: Dataset, axes: dict[str, list[str]]) -> None:
    for dim, code in spec.fixed.items():
        if axes[dim] != [code]:
            msg = f"{spec.name}: dimension {dim} is {axes[dim]}, expected [{code!r}]"
            raise ValueError(msg)


def parse(payload: bytes, spec: Dataset) -> list[dict[str, object]]:
    """JSON-stat -> staged rows (STAGED_COLUMNS), sorted by INDUSTRY_KEY. Pure, fail closed."""
    ds = _load(payload)
    if set(ds.id) != set(spec.dimensions):
        msg = f"{spec.name}: dimensions {sorted(ds.id)} differ from {sorted(spec.dimensions)}"
        raise ValueError(msg)
    axes = {d: _codes(ds.dimension[d].category, n, d) for d, n in zip(ds.id, ds.size, strict=True)}
    _check_fixed(ds, spec, axes)
    labels = {d: ds.dimension[d].category.label for d in ds.id}
    values = {str(i): v for i, v in enumerate(ds.value)} if isinstance(ds.value, list) else ds.value
    status = _status_map(ds)
    out: list[dict[str, object]] = []
    for i, combo in enumerate(product(*(axes[d] for d in ds.id))):
        v = values.get(str(i))
        if v is None:
            continue
        cell = dict(zip(ds.id, combo, strict=True))
        year = int(cell["time"])
        if year != spec.year:
            msg = f"{spec.name}: time {year} differs from dataset year {spec.year}"
            raise ValueError(msg)
        if spec.kind == "47":
            nace, nace_label = cell["nace_r2"], labels["nace_r2"].get(cell["nace_r2"], "")
        else:
            nace, nace_label = NACE_B_S_X_O, NACE_B_S_X_O_LABEL
        out.append(
            {
                "geo": cell["geo"],
                "year": year,
                "isco08": cell["isco08"],
                "isco08_label": labels["isco08"].get(cell["isco08"], ""),
                "nace_r2": nace,
                "nace_r2_label": nace_label,
                "sex": cell["sex"],
                "hourly_earnings_eur": float(v),
                "flags": status.get(str(i)),
            }
        )
    out.sort(key=_industry_key)
    return out


# ---------------------------------------------------------------- marts (pure)


def _industry_key(r: dict[str, object]) -> tuple[str, int, str, str, str]:
    return (
        str(r["geo"]),
        int(str(r["year"])),
        str(r["isco08"]),
        str(r["nace_r2"]),
        str(r["sex"]),
    )


def _occupation_key(r: dict[str, object]) -> tuple[str, int, str, str]:
    return (str(r["geo"]), int(str(r["year"])), str(r["isco08"]), str(r["sex"]))


def _finish(
    rows: list[dict[str, object]], key: tuple[str, ...], keyfn: object
) -> list[dict[str, object]]:
    rows.sort(key=keyfn)  # type: ignore[arg-type]
    seen: set[tuple[object, ...]] = set()
    for r in rows:
        k = tuple(r[c] for c in key)
        if k in seen:
            msg = f"duplicate key {key} = {k}"
            raise ValueError(msg)
        seen.add(k)
    return rows


def build_industry_mart(staged: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """``marts/ses_occupation_industry_earnings``: iso3 (None for aggregates) + staged columns +
    source, sorted by (geo, year, isco08, nace_r2, sex); duplicate keys raise ValueError."""
    out: list[dict[str, object]] = [
        {"iso3": iso3_of(str(r["geo"])), **{c: r[c] for c in STAGED_COLUMNS}, "source": SOURCE}
        for r in staged
    ]
    return _finish(out, INDUSTRY_KEY, _industry_key)


def build_occupation_mart(staged: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """``marts/ses_occupation_earnings`` (earn_ses*_14, age=TOTAL): occupation x sex x year,
    ``nace_r2`` = B-S_X_O scope column; duplicate (geo, year, isco08, sex) raise ValueError."""
    cols = tuple(c for c in STAGED_COLUMNS if c != "nace_r2_label")
    out: list[dict[str, object]] = [
        {"iso3": iso3_of(str(r["geo"])), **{c: r[c] for c in cols}, "source": SOURCE}
        for r in staged
    ]
    return _finish(out, OCCUPATION_KEY, _occupation_key)


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


def _read_staged(ctx: Context, kind: str, skipped: list[str]) -> list[dict[str, object]] | None:
    rows: list[dict[str, object]] = []
    found = False
    for d in DATASETS:
        if d.kind != kind:
            continue
        try:
            rows.extend(ctx.tables.read_table(d.staged_table))
            found = True
        except FileNotFoundError:
            skipped.append(f"{d.staged_table}: no staged table")
    return rows if found else None


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    industry = _read_staged(ctx, "47", skipped)
    if industry is not None:
        ctx.tables.write_table(INDUSTRY_MART, build_industry_mart(industry))
        written.append(INDUSTRY_MART)
    occupation = _read_staged(ctx, "14", skipped)
    if occupation is not None:
        ctx.tables.write_table(OCCUPATION_MART, build_occupation_mart(occupation))
        written.append(OCCUPATION_MART)
    return written, skipped
