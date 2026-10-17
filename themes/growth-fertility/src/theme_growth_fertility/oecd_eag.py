"""OECD Education at a Glance (SDMX REST): three dataflows -> one long schema (no I/O).

H8c. Each :class:`Dataset` fixes the URL (verified 2026-10-17), the ``STRUCTURE_ID`` and every
dimension code that must hold for all rows (``fixed``) or may vary within a closed set
(``allowed``). Dimensions a dataflow does not have are filled with ``_Z`` (or ``""`` for
``base_per``) so the three parse into the same columns:

``iso3, year, dataset, measure, education_level, exp_source, sex, work_time, price_base, unit,
base_per, value, obs_status, source``

Blank ``OBS_VALUE`` rows are dropped (never imputed, whatever their ``OBS_STATUS``); only the 38
OECD members are kept and the other reference areas (OECD / EU25 / G20 aggregates, non-members)
are reported so stage can list them. Anything else unexpected is a ``ValueError``.
"""

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, field_validator

from theme_growth_fertility.oecd import BASE, LICENSE, OECD_MEMBERS

__all__ = ["BASE", "DATASETS", "LICENSE", "SOURCE", "Dataset", "Parsed", "build_mart", "parse"]

SOURCE = "oecd_eag"
NA = "_Z"
REQUIRED_COLUMNS = ("STRUCTURE_ID", "REF_AREA", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS")
MART_KEY = (
    "iso3",
    "year",
    "dataset",
    "measure",
    "education_level",
    "exp_source",
    "sex",
    "work_time",
    "price_base",
    "unit",
)
EDUCATION_LEVELS: tuple[str, ...] = ("ISCED11_1T8", "ISCED11_1T4", "ISCED11_5T8", "ISCED11_02")
ATTAINMENT_LEVELS: tuple[str, ...] = (
    "ISCED11A_0T2",
    "ISCED11A_5T8",
    "ISCED11A_5",
    "ISCED11A_6",
    "ISCED11A_7_8",
)


@dataclass(frozen=True)
class Dataset:
    key: str
    flow_ref: str
    sdmx_key: str
    start_period: int
    structure_id: str
    fixed: tuple[tuple[str, str], ...]
    allowed: tuple[tuple[str, tuple[str, ...]], ...]
    # output column -> CSV dimension column (missing dimensions are filled with NA / "")
    columns: tuple[tuple[str, str], ...]

    @property
    def raw_name(self) -> str:
        return f"eag_{self.key}.csv"

    @property
    def url(self) -> str:
        return (
            f"{BASE}/{self.flow_ref}/{self.sdmx_key}"
            f"?startPeriod={self.start_period}&format=csvfilewithlabels"
        )


_UOE_FIXED_COMMON: tuple[tuple[str, str], ...] = (
    ("EXP_DESTINATION", "INST_EDU"),
    ("EXPENDITURE_TYPE", "DIR_EXP"),
    ("Q_SHEET", "SOURCE"),
)

DATASETS: tuple[Dataset, ...] = (
    Dataset(
        key="fin_source",
        flow_ref="OECD.EDU.IMEP,DSD_EAG_UOE_FIN@DF_UOE_FIN_SOURCE_GV_PR_NDOM,3.2",
        sdmx_key=(
            ".EXP.ISCED11_1T8+ISCED11_1T4+ISCED11_5T8+ISCED11_02.S13+S1D_NON_EDU+S2+_T"
            ".INST_EDU.DIR_EXP..PT_EXP+PT_B1GQ.SOURCE"
        ),
        start_period=1995,
        structure_id="OECD.EDU.IMEP:DSD_EAG_UOE_FIN@DF_UOE_FIN_SOURCE_GV_PR_NDOM(3.2)",
        fixed=(("MEASURE", "EXP"), *_UOE_FIXED_COMMON, ("PRICE_BASE", NA)),
        allowed=(
            ("EDUCATION_LEV", EDUCATION_LEVELS),
            ("EXP_SOURCE", ("S13", "S1D_NON_EDU", "S2", "_T")),
            ("UNIT_MEASURE", ("PT_EXP", "PT_B1GQ")),
        ),
        columns=(
            ("measure", "MEASURE"),
            ("education_level", "EDUCATION_LEV"),
            ("exp_source", "EXP_SOURCE"),
            ("price_base", "PRICE_BASE"),
            ("unit", "UNIT_MEASURE"),
            ("base_per", "BASE_PER"),
        ),
    ),
    Dataset(
        key="earn_rel",
        flow_ref="OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_EARN_REL_UPPER,1.0",
        sdmx_key=(
            "..Y25T64.ISCED11A_0T2+ISCED11A_5T8+ISCED11A_5+ISCED11A_6+ISCED11A_7_8._T"
            ".EARN_RELATIVE._Z._T._Z.ED_NED.EMP._Z.PT_EARN_WR_ISCED11A_3.OBS..EARNINGS.A"
        ),
        start_period=2000,
        structure_id="OECD.EDU.IMEP:DSD_EAG_LSO_EA@DF_LSO_EARN_REL_UPPER(1.0)",
        fixed=(
            ("AGE", "Y25T64"),
            ("EDUCATION_FIELD", "_T"),
            ("MEASURE", "EARN_RELATIVE"),
            ("INCOME", NA),
            ("BIRTH_PLACE", "_T"),
            ("MIGRATION_AGE", NA),
            ("EDU_STATUS", "ED_NED"),
            ("LABOUR_FORCE_STATUS", "EMP"),
            ("DURATION_UNEMP", NA),
            ("UNIT_MEASURE", "PT_EARN_WR_ISCED11A_3"),
            ("STATISTICAL_OPERATION", "OBS"),
            ("QUESTIONNAIRE", "EARNINGS"),
            ("FREQ", "A"),
        ),
        allowed=(
            ("SEX", ("_T", "F", "M")),
            ("ATTAINMENT_LEV", ATTAINMENT_LEVELS),
            ("WORK_TIME_ARNGMNT", ("_T", "FT", "_O")),
        ),
        columns=(
            ("measure", "MEASURE"),
            ("education_level", "ATTAINMENT_LEV"),
            ("sex", "SEX"),
            ("work_time", "WORK_TIME_ARNGMNT"),
            ("unit", "UNIT_MEASURE"),
        ),
    ),
    Dataset(
        key="fin_perstud",
        flow_ref="OECD.EDU.IMEP,DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_PERSTUD,3.2",
        sdmx_key=(
            ".FIN_PERSTUD.ISCED11_1T8+ISCED11_1T4+ISCED11_5T8+ISCED11_02._T"
            ".INST_EDU.DIR_EXP.Q+V.USD_PPP_ST.SOURCE"
        ),
        start_period=1995,
        structure_id="OECD.EDU.IMEP:DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_PERSTUD(3.2)",
        fixed=(
            ("MEASURE", "FIN_PERSTUD"),
            ("EXP_SOURCE", "_T"),
            *_UOE_FIXED_COMMON,
            ("UNIT_MEASURE", "USD_PPP_ST"),
        ),
        allowed=(("EDUCATION_LEV", EDUCATION_LEVELS), ("PRICE_BASE", ("Q", "V"))),
        columns=(
            ("measure", "MEASURE"),
            ("education_level", "EDUCATION_LEV"),
            ("exp_source", "EXP_SOURCE"),
            ("price_base", "PRICE_BASE"),
            ("unit", "UNIT_MEASURE"),
            ("base_per", "BASE_PER"),
        ),
    ),
)

_DEFAULTS: dict[str, str] = {
    "measure": NA,
    "education_level": NA,
    "exp_source": NA,
    "sex": NA,
    "work_time": NA,
    "price_base": NA,
    "unit": NA,
    "base_per": "",
}


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
    rows: list[dict[str, object]]
    dropped_ref_areas: tuple[str, ...]  # non-member / aggregate REF_AREA codes, sorted


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
        msg = f"unexpected OECD EAG header for {dataset.key}: missing {missing}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    dropped: set[str] = set()
    for raw in reader:
        if None in raw or any(v is None for v in raw.values()):
            msg = f"ragged OECD EAG row: {raw}"
            raise ValueError(msg)
        line = _Line.model_validate(raw)
        if dataset.structure_id != line.STRUCTURE_ID:
            msg = f"OECD STRUCTURE_ID {line.STRUCTURE_ID!r}, expected {dataset.structure_id!r}"
            raise ValueError(msg)
        for dim, code in dataset.fixed:
            if raw[dim] != code:
                msg = f"OECD EAG {dataset.key} dimension {dim}={raw[dim]!r}, expected {code!r}"
                raise ValueError(msg)
        for dim, codes in dataset.allowed:
            if raw[dim] not in codes:
                msg = f"OECD EAG {dataset.key} dimension {dim}={raw[dim]!r} not in {codes}"
                raise ValueError(msg)
        if line.REF_AREA not in OECD_MEMBERS:
            dropped.add(line.REF_AREA)
            continue
        if line.OBS_VALUE is None:
            continue
        row: dict[str, object] = {"iso3": line.REF_AREA, "year": line.TIME_PERIOD}
        row["dataset"] = dataset.key
        row.update(_DEFAULTS)
        row.update({col: raw[dim] for col, dim in dataset.columns})
        row["value"] = line.OBS_VALUE
        row["obs_status"] = line.OBS_STATUS
        row["source"] = SOURCE
        out.append(row)
    out.sort(key=mart_key)
    return Parsed(rows=out, dropped_ref_areas=tuple(sorted(dropped)))


def mart_key(row: Mapping[str, object]) -> tuple[str, int, str, str, str, str, str, str, str, str]:
    return (
        str(row["iso3"]),
        int(str(row["year"])),
        *(str(row[c]) for c in MART_KEY[2:]),
    )  # type: ignore[return-value]


def build_mart(staged: Mapping[str, Sequence[Mapping[str, object]]]) -> list[dict[str, object]]:
    """Concatenate the staged dataset tables, sort by :data:`MART_KEY`; duplicate keys fail."""
    rows = [dict(r) for key in sorted(staged) for r in staged[key]]
    rows.sort(key=mart_key)
    seen: set[tuple[object, ...]] = set()
    for r in rows:
        k = mart_key(r)
        if k in seen:
            msg = f"duplicate OECD EAG mart key {k}"
            raise ValueError(msg)
        seen.add(k)
    return rows
