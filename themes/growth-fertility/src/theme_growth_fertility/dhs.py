"""DHS Program Indicator Data API: URL builders and deterministic JSON -> rows (no I/O).

Indicator ``FE_FRTR_W_TFR`` (total fertility rate 15-49, three years before the survey) broken
down by *Wealth quintile* (asset-based within-country rank, not income), every survey type.
ISO3 comes from ``/rest/dhs/countries`` (``ISO3_CountryCode``); records whose DHS country code
has no ISO3 are dropped and reported via ``unmapped_codes``.

H8 (``H8_REQUESTS`` / ``mechanism_rows`` / ``build_mechanisms_mart``): several indicators x
breakdowns (Total / Education / Wealth quintile / Age 5-year groups) in one long table. One
request = one indicator group x one breakdown, each below the 5,000-row page limit.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

BASE = "https://api.dhsprogram.com/rest/dhs"
SOURCE = "dhs_api"
# No API key. Terms (api.dhsprogram.com/#/terms.cfm, checked 2026-10-05) require this citation
# wherever the data are used or redistributed:
LICENSE = (
    "DHS Program API terms: citation required - 'The DHS Program Indicator Data API, "
    "The Demographic and Health Surveys (DHS) Program. ICF. Originally funded by the United "
    "States Agency for International Development (USAID). Available from api.dhsprogram.com. "
    "[Accessed 10-05-2026]' (https://api.dhsprogram.com/#/terms.cfm)"
)
INDICATOR = "FE_FRTR_W_TFR"  # Total fertility rate 15-49
CHARACTERISTIC = "Wealth quintile"
QUINTILES: dict[str, int] = {"Lowest": 1, "Second": 2, "Middle": 3, "Fourth": 4, "Highest": 5}


def data_url(
    *,
    indicator_ids: Sequence[str] = (INDICATOR,),
    category: str | None = CHARACTERISTIC,
    per_page: int = 5000,
) -> str:
    """``category=None`` requests the Total rows only (no ``breakdown``)."""
    url = f"{BASE}/data?indicatorIds={','.join(indicator_ids)}"
    if category is not None:
        url += f"&breakdown=all&characteristicCategory={category.replace(' ', '%20')}"
    return f"{url}&perpage={per_page}&f=json"


def countries_url(*, per_page: int = 300) -> str:
    return f"{BASE}/countries?f=json&perpage={per_page}"


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore")
    TotalPages: int
    RecordCount: int
    Data: list[object]


class _Record(BaseModel):
    model_config = ConfigDict(extra="ignore")
    Value: float | None
    DHS_CountryCode: str
    CountryName: str
    SurveyYear: int
    SurveyId: str
    IndicatorId: str
    CharacteristicCategory: str
    CharacteristicLabel: str
    SurveyType: str
    ByVariableLabel: str = ""  # e.g. U5MR: "Five years preceding the survey" / "Ten years ..."
    IsPreferred: int | None = None  # 1 for the preferred ByVariable variant
    # The API serialises these as strings ("" when absent).
    DenominatorWeighted: float | str | None = None
    CILow: float | str | None = None
    CIHigh: float | str | None = None


class _Country(BaseModel):
    model_config = ConfigDict(extra="ignore")
    DHS_CountryCode: str
    ISO3_CountryCode: str = ""


def _split(payload: bytes) -> list[object]:
    """Validate the envelope; fail closed on pagination/truncation (same policy as worldbank)."""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"DHS response is not JSON: {e}"
        raise ValueError(msg) from None
    if not isinstance(doc, dict):
        msg = "unexpected DHS response shape (expected a JSON object)"
        raise ValueError(msg)
    page = _Page.model_validate(doc)
    if page.TotalPages != 1 or page.RecordCount != len(page.Data):
        msg = (
            f"paginated/truncated DHS response: TotalPages={page.TotalPages} "
            f"RecordCount={page.RecordCount} rows={len(page.Data)}; raise per_page"
        )
        raise ValueError(msg)
    return page.Data


def _num(v: float | str | None) -> float | None:
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    return float(v)


def iso3_map(countries_payload: bytes) -> dict[str, str]:
    """DHS_CountryCode -> ISO3 (entries without an ISO3, e.g. sub-national 'OS', are excluded)."""
    out: dict[str, str] = {}
    for c in (_Country.model_validate(x) for x in _split(countries_payload)):
        iso3 = c.ISO3_CountryCode.strip()
        if iso3:
            out[c.DHS_CountryCode] = iso3
    return out


def _wealth_records(payload: bytes) -> list[_Record]:
    recs = (_Record.model_validate(x) for x in _split(payload))
    return [
        r
        for r in recs
        if r.IndicatorId == INDICATOR
        and r.CharacteristicCategory == CHARACTERISTIC
        and r.CharacteristicLabel in QUINTILES
    ]


def rows_from_response(
    payload: bytes, *, iso3_by_dhs_code: dict[str, str]
) -> list[dict[str, object]]:
    """Long rows (one per survey × quintile). Pure; rows without an ISO3 are dropped."""
    rows: list[dict[str, object]] = []
    for r in _wealth_records(payload):
        iso3 = iso3_by_dhs_code.get(r.DHS_CountryCode)
        if iso3 is None:
            continue
        rows.append(
            {
                "iso3": iso3,
                "country": r.CountryName,
                "dhs_country_code": r.DHS_CountryCode,
                "survey_id": r.SurveyId,
                "survey_year": r.SurveyYear,
                "survey_type": r.SurveyType,
                "quintile": QUINTILES[r.CharacteristicLabel],
                "quintile_label": r.CharacteristicLabel,
                "value": _num(r.Value),
                "ci_low": _num(r.CILow),
                "ci_high": _num(r.CIHigh),
                "denominator_weighted": _num(r.DenominatorWeighted),
                "source": SOURCE,
            }
        )
    rows.sort(
        key=lambda r: (
            int(str(r["survey_year"])),
            str(r["iso3"]),
            str(r["survey_id"]),
            int(str(r["quintile"])),
        )
    )
    return rows


def unmapped_codes(payload: bytes, *, iso3_by_dhs_code: dict[str, str]) -> list[str]:
    """DHS country codes of wealth-quintile rows that got no ISO3 (sorted, distinct)."""
    return sorted(
        {
            r.DHS_CountryCode
            for r in _wealth_records(payload)
            if r.DHS_CountryCode not in iso3_by_dhs_code
        }
    )


# ---- H8: mechanisms (several indicators x breakdowns, one long table) ---------------------

# IndicatorId -> metric name in the mart (closed list; other indicators in a payload are dropped)
METRICS: dict[str, str] = {
    "FE_FRTR_W_TFR": "tfr",
    **{f"FE_FRTR_W_A{a}": f"asfr_{a}" for a in range(15, 50, 5)},
    "PR_WTFR_W_WFR": "wanted_tfr",
    "PR_IDLC_W_MNA": "ideal_children",
    "PR_DESC_W_WNM": "want_no_more",
    "CM_ECMR_C_U5M": "u5mr",
    "MA_AAFM_W_M2B": "age_first_marriage",
    "MA_MBAG_W_NMA": "never_married_25_49",
    "MA_MSTA_W_UNI": "in_union",
    "ED_EDUC_W_SEH": "women_secondary_plus",
    "FP_CUSM_W_MOD": "modern_contraception_married",
}
EDUCATION = "Education"
AGE_5 = "Age (5-year groups)"
_ASFR_IDS = tuple(f"FE_FRTR_W_A{a}" for a in range(15, 50, 5))


@dataclass(frozen=True)
class Request:
    """One API call: an indicator group x one breakdown (``category=None`` = Total only)."""

    raw_name: str
    indicator_ids: tuple[str, ...]
    category: str | None

    @property
    def url(self) -> str:
        return data_url(indicator_ids=self.indicator_ids, category=self.category)

    @property
    def allowed_categories(self) -> frozenset[str]:
        return frozenset() if self.category is None else frozenset({self.category})


def _req(ids: str | tuple[str, ...], category: str | None, *, stem: str | None = None) -> Request:
    indicator_ids = (ids,) if isinstance(ids, str) else ids
    stem = stem or indicator_ids[0]
    suffix = "total" if category is None else category.lower()
    for a, b in ((" ", "_"), ("(", ""), (")", ""), ("-", "_")):
        suffix = suffix.replace(a, b)
    return Request(f"dhs_h8_{stem}_{suffix}.json", indicator_ids, category)


# Deterministic order; every request was checked to return a single page (< 5,000 rows) on
# 2026-10-17. Region and other breakdowns are not requested.
H8_REQUESTS: tuple[Request, ...] = (
    _req("FE_FRTR_W_TFR", None),
    _req("FE_FRTR_W_TFR", EDUCATION),
    _req("FE_FRTR_W_TFR", CHARACTERISTIC),
    _req(_ASFR_IDS, None, stem="FE_FRTR_W_A15_ASFR"),
    _req("PR_WTFR_W_WFR", None),
    _req("PR_WTFR_W_WFR", EDUCATION),
    _req("PR_WTFR_W_WFR", CHARACTERISTIC),
    _req("PR_IDLC_W_MNA", None),
    _req("PR_DESC_W_WNM", None),
    _req("CM_ECMR_C_U5M", None),
    _req("CM_ECMR_C_U5M", EDUCATION),
    _req("CM_ECMR_C_U5M", CHARACTERISTIC),
    _req("MA_AAFM_W_M2B", None),
    _req("MA_AAFM_W_M2B", EDUCATION),
    _req("MA_AAFM_W_M2B", CHARACTERISTIC),
    _req("MA_MBAG_W_NMA", None),
    _req("MA_MBAG_W_NMA", AGE_5),
    _req("MA_MSTA_W_UNI", None),
    _req("MA_MSTA_W_UNI", AGE_5),
    _req("ED_EDUC_W_SEH", None),
    _req("FP_CUSM_W_MOD", None),
    _req("FP_CUSM_W_MOD", EDUCATION),
)
MECHANISM_KEY = (
    "survey_year",
    "iso3",
    "survey_id",
    "metric",
    "characteristic_category",
    "characteristic_label",
    "by_variable",
)


def _is_total(category: str) -> bool:
    # "Total", "Total 15-49", "Total 25-49", ... (varies by indicator)
    return category.startswith("Total")


def _mechanism_records(payload: bytes, *, allowed_categories: frozenset[str]) -> list[_Record]:
    recs = (_Record.model_validate(x) for x in _split(payload))
    return [
        r
        for r in recs
        if r.IndicatorId in METRICS
        and (r.CharacteristicCategory in allowed_categories or _is_total(r.CharacteristicCategory))
    ]


def _mechanism_sort_key(r: dict[str, object]) -> tuple[int, str, str, str, str, str, str]:
    return (
        int(str(r["survey_year"])),
        str(r["iso3"]),
        str(r["survey_id"]),
        str(r["metric"]),
        str(r["characteristic_category"]),
        str(r["characteristic_label"]),
        str(r["by_variable"]),
    )


def mechanism_rows(
    payload: bytes, *, iso3_by_dhs_code: dict[str, str], allowed_categories: frozenset[str]
) -> list[dict[str, object]]:
    """Long rows for the ``dhs_mechanisms`` table (one per survey x indicator x breakdown label
    x by-variable). Only indicators in ``METRICS`` and the requested breakdown (plus Total-type
    rows) pass; rows without an ISO3 are dropped. Pure; input order does not matter."""
    rows: list[dict[str, object]] = []
    for r in _mechanism_records(payload, allowed_categories=allowed_categories):
        iso3 = iso3_by_dhs_code.get(r.DHS_CountryCode)
        if iso3 is None:
            continue
        rows.append(
            {
                "iso3": iso3,
                "country": r.CountryName,
                "dhs_country_code": r.DHS_CountryCode,
                "survey_id": r.SurveyId,
                "survey_year": r.SurveyYear,
                "survey_type": r.SurveyType,
                "indicator_id": r.IndicatorId,
                "metric": METRICS[r.IndicatorId],
                "characteristic_category": r.CharacteristicCategory,
                "characteristic_label": r.CharacteristicLabel,
                "by_variable": r.ByVariableLabel,
                "is_preferred": r.IsPreferred,
                "value": _num(r.Value),
                "ci_low": _num(r.CILow),
                "ci_high": _num(r.CIHigh),
                "denominator_weighted": _num(r.DenominatorWeighted),
                "source": SOURCE,
            }
        )
    rows.sort(key=_mechanism_sort_key)
    return rows


def mechanism_unmapped_codes(payload: bytes, *, iso3_by_dhs_code: dict[str, str]) -> list[str]:
    """DHS country codes (any breakdown, indicators in METRICS) without an ISO3; sorted."""
    return sorted(
        {
            r.DHS_CountryCode
            for r in (_Record.model_validate(x) for x in _split(payload))
            if r.IndicatorId in METRICS and r.DHS_CountryCode not in iso3_by_dhs_code
        }
    )


def build_mechanisms_mart(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Mart = staged rows sorted by ``MECHANISM_KEY``; a duplicate key fails closed. Pure."""
    out = sorted((dict(r) for r in rows), key=_mechanism_sort_key)
    seen: set[tuple[int, str, str, str, str, str, str]] = set()
    for r in out:
        key = _mechanism_sort_key(r)
        if key in seen:
            msg = f"duplicate dhs_mechanisms key {key}"
            raise ValueError(msg)
        seen.add(key)
    return out
