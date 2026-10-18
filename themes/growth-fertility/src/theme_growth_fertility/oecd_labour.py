"""OECD house prices / temporary employment / youth unemployment (SDMX REST) and Family
Database SF3.1 marriage workbook -> one long schema (no I/O).

H10. Three dataflows (URLs verified 2026-10-18, fixed in :data:`DATASETS`) share the
``oecd_eag`` discipline: ``STRUCTURE_ID`` and every all-rows dimension (``fixed``) must hold,
the varying dimensions (``allowed``) must stay inside a closed set, anything else is a
``ValueError``. Only the 19 :data:`H10_COUNTRIES` are kept; other reference areas are dropped
and reported. Blank ``OBS_VALUE`` rows are dropped (never imputed).

The SF3.1 workbook (``MARRIAGE_URL``) is read with openpyxl: ``MarriageRates`` (ISO3 + country
+ note, year columns 1960-, crude marriage rate per 1 000 population) and
``MeanAgeFirstMarriage`` (country name on the Male row only -> forward-filled, Gender column,
year columns 1990-). ``'..'`` and empty cells give no row. Header text, year columns, ISO3 /
country-name agreement and the Gender codes are checked; a mismatch fails closed.

Common columns::

    iso3, year, dataset, measure, sex, age, unit, value, obs_status, source

``dataset`` = house_prices / temp_employment / youth_unemployment / marriage_rate /
mean_age_first_marriage. Dimensions a dataset does not have are ``""``.
"""

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import openpyxl
from pydantic import BaseModel, ConfigDict, field_validator

from theme_growth_fertility.oecd import BASE
from theme_growth_fertility.oecd import LICENSE as OECD_LICENSE

__all__ = [
    "DATASETS",
    "H10_COUNTRIES",
    "LICENSE",
    "MARRIAGE_RAW_NAME",
    "MARRIAGE_URL",
    "SOURCE",
    "Dataset",
    "Parsed",
    "build_mart",
    "mart_key",
    "parse",
    "parse_marriage",
]

SOURCE = "oecd_labour"
LICENSE = (
    f"{OECD_LICENSE}. Cite: OECD (2026), House prices / Temporary employment / LFS indicators "
    "(sdmx.oecd.org) and Family Database SF3.1 (accessed 2026-10-18)."
)
H10_COUNTRIES: tuple[str, ...] = (
    "JPN", "KOR", "ITA", "ESP", "PRT", "GRC", "SWE", "DNK", "FIN", "NOR", "FRA", "DEU", "NLD",
    "GBR", "USA", "AUT", "CZE", "HUN", "POL",
)  # fmt: skip
REQUIRED_COLUMNS = ("STRUCTURE_ID", "REF_AREA", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS")
MART_KEY = ("iso3", "year", "dataset", "measure", "sex", "age", "unit")
SEXES: tuple[str, ...] = ("_T", "M", "F")

MARRIAGE_URL = "https://webfs.oecd.org/Els-com/Family_Database/SF_3_1_Marriage_divorce_rates.xlsx"
MARRIAGE_RAW_NAME = "sf3_1_marriage_divorce_rates.xlsx"
SHEET_RATES = "MarriageRates"
SHEET_MEAN_AGE = "MeanAgeFirstMarriage"
DATASET_RATES = "marriage_rate"
DATASET_MEAN_AGE = "mean_age_first_marriage"
GENDERS: dict[str, str] = {"Male": "M", "Female": "F"}
# Country names used in the SF3.1 workbook for the H10 countries (seen in the 2026-10-18 file).
NAME_TO_ISO3: dict[str, str] = {
    "Japan": "JPN", "Korea": "KOR", "Italy": "ITA", "Spain": "ESP", "Portugal": "PRT",
    "Greece": "GRC", "Sweden": "SWE", "Denmark": "DNK", "Finland": "FIN", "Norway": "NOR",
    "France": "FRA", "Germany": "DEU", "Netherlands": "NLD", "United Kingdom": "GBR",
    "United States": "USA", "Austria": "AUT", "Czechia": "CZE", "Hungary": "HUN",
    "Poland": "POL",
}  # fmt: skip

Row = dict[str, object]
Grid = list[list[object]]


@dataclass(frozen=True)
class Dataset:
    key: str
    flow_ref: str
    sdmx_key: str  # dimensions after REF_AREA, in dataflow order
    structure_id: str
    fixed: tuple[tuple[str, str], ...]
    allowed: tuple[tuple[str, tuple[str, ...]], ...]
    columns: tuple[tuple[str, str], ...]  # output column -> CSV dimension column

    @property
    def raw_name(self) -> str:
        return f"{self.key}.csv"

    @property
    def url(self) -> str:
        ref = "+".join(H10_COUNTRIES)
        return f"{BASE}/{self.flow_ref}/{ref}.{self.sdmx_key}?format=csvfilewithlabels"


DATASETS: tuple[Dataset, ...] = (
    Dataset(
        key="house_prices",
        flow_ref="OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,1.0",
        sdmx_key="A.HPI_YDH+HPI_RPI+RHP.",
        structure_id="OECD.ECO.MPD:DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES(1.0)",
        fixed=(("FREQ", "A"),),
        allowed=(
            ("MEASURE", ("HPI_YDH", "HPI_RPI", "RHP")),
            ("UNIT_MEASURE", ("IX", "PT_AVG_L_TERM")),
        ),
        columns=(("measure", "MEASURE"), ("unit", "UNIT_MEASURE")),
    ),
    Dataset(
        key="temp_employment",
        flow_ref="OECD.ELS.SAE,DSD_TEMP@DF_TEMP_I,1.0",
        sdmx_key="EMP_TEMP.PT_POP_SUB._T+M+F.Y15T24+Y25T54+_T.ICSE93_1.A",
        structure_id="OECD.ELS.SAE:DSD_TEMP@DF_TEMP_I(1.0)",
        fixed=(
            ("MEASURE", "EMP_TEMP"),
            ("UNIT_MEASURE", "PT_POP_SUB"),
            ("WORKER_STATUS", "ICSE93_1"),
            ("FREQ", "A"),
        ),
        allowed=(("SEX", SEXES), ("AGE", ("Y15T24", "Y25T54", "_T"))),
        columns=(
            ("measure", "MEASURE"),
            ("sex", "SEX"),
            ("age", "AGE"),
            ("unit", "UNIT_MEASURE"),
        ),
    ),
    Dataset(
        key="youth_unemployment",
        flow_ref="OECD.ELS.SAE,DSD_LFS@DF_LFS_INDIC,1.1",
        sdmx_key="UNE_RATE.PT_LF_SUB._T+M+F.Y15T24+Y25T34.UNE",
        structure_id="OECD.ELS.SAE:DSD_LFS@DF_LFS_INDIC(1.1)",
        fixed=(
            ("MEASURE", "UNE_RATE"),
            ("UNIT_MEASURE", "PT_LF_SUB"),
            ("LABOUR_FORCE_STATUS", "UNE"),
        ),
        allowed=(("SEX", SEXES), ("AGE", ("Y15T24", "Y25T34"))),
        columns=(
            ("measure", "MEASURE"),
            ("sex", "SEX"),
            ("age", "AGE"),
            ("unit", "UNIT_MEASURE"),
        ),
    ),
)

_DEFAULTS: dict[str, str] = {"measure": "", "sex": "", "age": "", "unit": "", "obs_status": ""}


class _Line(BaseModel):
    model_config = ConfigDict(extra="ignore")
    STRUCTURE_ID: str
    REF_AREA: str
    TIME_PERIOD: int
    OBS_VALUE: float | None
    OBS_STATUS: str

    @field_validator("OBS_VALUE", mode="before")
    @classmethod
    def _blank_is_missing(cls, v: object) -> object:
        return None if v == "" else v


@dataclass(frozen=True)
class Parsed:
    rows: list[Row]
    dropped_ref_areas: tuple[str, ...]  # REF_AREA codes outside H10_COUNTRIES, sorted


def _row(iso3: str, year: int, dataset: str, value: float, **dims: str) -> Row:
    row: Row = {"iso3": iso3, "year": year, "dataset": dataset}
    row.update(_DEFAULTS)
    row.update(dims)
    row["value"] = value
    row.setdefault("obs_status", "")
    row["source"] = SOURCE
    return {k: row[k] for k in (*MART_KEY, "value", "obs_status", "source")}


def parse(payload: bytes, dataset: Dataset) -> Parsed:
    """CSV (``csvfilewithlabels``) -> long rows for *dataset*, sorted by :data:`MART_KEY`."""
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    fields = set(reader.fieldnames or ())
    needed = (
        *REQUIRED_COLUMNS,
        *(d for d, _ in dataset.fixed),
        *(d for d, _ in dataset.allowed),
        *(c for _, c in dataset.columns),
    )
    missing = [c for c in needed if c not in fields]
    if missing:
        msg = f"unexpected OECD header for {dataset.key}: missing {missing}"
        raise ValueError(msg)
    out: list[Row] = []
    dropped: set[str] = set()
    for raw in reader:
        if None in raw or any(v is None for v in raw.values()):
            msg = f"ragged OECD row: {raw}"
            raise ValueError(msg)
        line = _Line.model_validate(raw)
        if dataset.structure_id != line.STRUCTURE_ID:
            msg = f"OECD STRUCTURE_ID {line.STRUCTURE_ID!r}, expected {dataset.structure_id!r}"
            raise ValueError(msg)
        for dim, code in dataset.fixed:
            if raw[dim] != code:
                msg = f"OECD {dataset.key} dimension {dim}={raw[dim]!r}, expected {code!r}"
                raise ValueError(msg)
        for dim, codes in dataset.allowed:
            if raw[dim] not in codes:
                msg = f"OECD {dataset.key} dimension {dim}={raw[dim]!r} not in {codes}"
                raise ValueError(msg)
        if line.REF_AREA not in H10_COUNTRIES:
            dropped.add(line.REF_AREA)
            continue
        if line.OBS_VALUE is None:
            continue
        dims = {col: raw[dim] for col, dim in dataset.columns}
        out.append(
            _row(
                line.REF_AREA,
                line.TIME_PERIOD,
                dataset.key,
                line.OBS_VALUE,
                obs_status=line.OBS_STATUS,
                **dims,
            )
        )
    out.sort(key=mart_key)
    return Parsed(rows=out, dropped_ref_areas=tuple(sorted(dropped)))


# ---------------------------------------------------------------- SF3.1 workbook


def _text(cell: object) -> str:
    return " ".join(str(cell).split()) if cell is not None else ""


def _is_year(cell: object) -> bool:
    return isinstance(cell, int) and not isinstance(cell, bool) and 1900 <= cell <= 2100


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
    for name in (SHEET_RATES, SHEET_MEAN_AGE):
        if name not in grids:
            msg = f"sheet {name!r} not found (sheets: {sorted(grids)})"
            raise ValueError(msg)
    return grids


def _header(rows: Grid, *, sheet: str, labels: tuple[str, ...]) -> tuple[int, dict[int, int]]:
    """(header row index, {column -> year}); the labels must precede the first year column."""
    for i, row in enumerate(rows):
        years = {j: int(str(c)) for j, c in enumerate(row) if _is_year(c)}
        if len(years) < 5:
            continue
        first = min(years)
        found = tuple(_text(c) for c in row[first - len(labels) : first])
        if found != labels:
            msg = f"{sheet}: unexpected header {found!r}, expected {labels!r}"
            raise ValueError(msg)
        if any(j != first + n for n, j in enumerate(sorted(years))):
            msg = f"{sheet}: year columns are not contiguous"
            raise ValueError(msg)
        return i, years
    msg = f"{sheet}: header row with year columns not found (years must be integer cells)"
    raise ValueError(msg)


def _value(cell: object, *, where: str) -> float | None:
    """A number, or None for an empty / '..' cell. Any other text fails closed."""
    if cell is None or _text(cell) in ("", ".."):
        return None
    if isinstance(cell, (int, float)) and not isinstance(cell, bool):
        return float(cell)
    msg = f"{where}: expected a number or '..', got {cell!r}"
    raise ValueError(msg)


def _marriage_rates(rows: Grid) -> tuple[list[Row], list[str]]:
    header_idx, years = _header(rows, sheet=SHEET_RATES, labels=("Country", "Note"))
    code_col = min(years) - 3
    out: list[Row] = []
    dropped: list[str] = []
    for row in rows[header_idx + 1 :]:
        code = _text(row[code_col] if len(row) > code_col else None)
        name = _text(row[code_col + 1] if len(row) > code_col + 1 else None)
        if not code:
            continue  # notes / sources below the table carry no code
        if len(code) != 3 or not code.isalpha() or not code.isupper():
            msg = f"{SHEET_RATES}: {code!r} is not an ISO3 code (row {name!r})"
            raise ValueError(msg)
        if code not in H10_COUNTRIES:
            dropped.append(f"{SHEET_RATES}: {name} ({code}) dropped: not an H10 country")
            continue
        if NAME_TO_ISO3.get(name) != code:
            msg = f"{SHEET_RATES}: {code} is labelled {name!r}, expected the known country name"
            raise ValueError(msg)
        for col, year in years.items():
            value = _value(row[col] if col < len(row) else None, where=f"{SHEET_RATES}: {name}")
            if value is None:
                continue
            out.append(_row(code, year, DATASET_RATES, value, measure="CMR", unit="PER_1000_POP"))
    return out, dropped


def _mean_age(rows: Grid) -> tuple[list[Row], list[str]]:
    header_idx, years = _header(rows, sheet=SHEET_MEAN_AGE, labels=("Country", "Note", "Gender"))
    name_col, gender_col = min(years) - 3, min(years) - 1
    out: list[Row] = []
    dropped: list[str] = []
    current: str | None = None  # the country name is written on the first (Male) row only
    for row in rows[header_idx + 1 :]:
        name = _text(row[name_col] if len(row) > name_col else None)
        gender = _text(row[gender_col] if len(row) > gender_col else None)
        if name and not gender:
            break  # ".. Not available" / the notes block below the table
        if not gender:
            continue  # blank spacer row
        if name:
            current = name
        if current is None:
            msg = f"{SHEET_MEAN_AGE}: Gender row before any country name"
            raise ValueError(msg)
        if gender not in GENDERS:
            msg = f"{SHEET_MEAN_AGE}: unexpected Gender {gender!r} for {current}"
            raise ValueError(msg)
        iso3 = NAME_TO_ISO3.get(current)
        if iso3 is None:
            if current in _KNOWN_OTHER_NAMES:
                if gender == "Male":
                    dropped.append(f"{SHEET_MEAN_AGE}: {current} dropped: not an H10 country")
                continue
            msg = f"{SHEET_MEAN_AGE}: unknown country name {current!r}"
            raise ValueError(msg)
        for col, year in years.items():
            where = f"{SHEET_MEAN_AGE}: {current} {gender}"
            value = _value(row[col] if col < len(row) else None, where=where)
            if value is None:
                continue
            sex = GENDERS[gender]
            out.append(
                _row(iso3, year, DATASET_MEAN_AGE, value, measure="MAFM", sex=sex, unit="YR")
            )
    return out, dropped


# Other country names present in the 2026-10-18 workbook (not H10): dropped, not an error.
_KNOWN_OTHER_NAMES: frozenset[str] = frozenset(
    {
        "Australia", "Belgium", "Canada", "Chile", "Colombia", "Costa Rica", "Estonia",
        "Iceland", "Ireland", "Israel", "Latvia", "Lithuania", "Luxembourg", "Mexico",
        "New Zealand", "Slovak Republic", "Slovakia", "Slovenia", "Switzerland", "Turkey",
        "Türkiye", "Bulgaria", "Croatia", "Cyprus", "Malta", "Romania", "Brazil", "China",
        "India", "Indonesia", "Russian Fed.", "South Africa", "Argentina", "Saudi Arabia",
    }
)  # fmt: skip


def parse_marriage(payload: bytes) -> tuple[list[Row], list[str]]:
    """SF3.1 xlsx -> (rows for marriage_rate + mean_age_first_marriage, dropped notes).

    Sorted by :data:`MART_KEY`; a duplicate key within the workbook is a ``ValueError``.
    """
    grids = _sheets(payload)
    rates, dropped_a = _marriage_rates(grids[SHEET_RATES])
    ages, dropped_b = _mean_age(grids[SHEET_MEAN_AGE])
    rows = _sorted_unique(rates + ages, where="SF3.1")
    return rows, dropped_a + dropped_b


def mart_key(row: Mapping[str, object]) -> tuple[str, int, str, str, str, str, str]:
    return (
        str(row["iso3"]),
        int(str(row["year"])),
        str(row["dataset"]),
        str(row["measure"]),
        str(row["sex"]),
        str(row["age"]),
        str(row["unit"]),
    )


def _sorted_unique(rows: list[Row], *, where: str) -> list[Row]:
    rows.sort(key=mart_key)
    seen: set[tuple[object, ...]] = set()
    for r in rows:
        k = mart_key(r)
        if k in seen:
            msg = f"duplicate {where} mart key {k}"
            raise ValueError(msg)
        seen.add(k)
    return rows


def build_mart(staged: Mapping[str, Sequence[Mapping[str, object]]]) -> list[Row]:
    """Concatenate the staged tables, sort by :data:`MART_KEY`; duplicate keys fail."""
    rows = [dict(r) for key in sorted(staged) for r in staged[key]]
    return _sorted_unique(rows, where="OECD labour")
