"""IMF DataMapper API v1: WEO / Fiscal Monitor / Global Debt Database indicators (% of GDP).

One request per indicator: ``https://www.imf.org/external/datamapper/api/v1/<code>`` →
``{"values": {"<code>": {"<ISO3 or aggregate>": {"<year>": value}}}, "api": {...}}``. The
``periods`` query parameter is ignored by the server (all years come back), so it is not sent.
Pure transforms only (no I/O).

WEO / FM series run past the current year as projections (to 2031 in the October 2026 vintage)
and the API does not flag them, so every row after ``LAST_ACTUAL_YEAR`` is dropped at parse time
and the cut is documented in the report. Aggregates (ADVEC, EURO, FM_* …) are dropped: only
3-letter upper-case codes are kept.

License: IMF Copyright and Usage (https://www.imf.org/en/About/copyright-and-terms, confirmed
2026-11-03): data may be downloaded, copied, redistributed and used in derivative works with
attribution "Source: International Monetary Fund, <Database>, <link>"; commercial reuse needs
prior permission; bulk automated download needs permission (this adapter sends 13 requests).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, RootModel, ValidationError

SOURCE = "imf"
LICENSE = (
    "IMF Copyright and Usage (https://www.imf.org/en/About/copyright-and-terms): attribution "
    "required, commercial reuse needs permission"
)
BASE = "https://www.imf.org/external/datamapper/api/v1"
MAGIC = b"{"
LAST_ACTUAL_YEAR = 2025  # WEO October 2026 vintage: later years are projections

# code -> (dataset, unit, metric)
INDICATORS: dict[str, tuple[str, str, str]] = {
    "GGXWDG_NGDP": ("weo", "general_gov_gross", "debt_gdp"),
    "GGXCNL_NGDP": ("weo", "general_gov_gross", "fiscal_balance_gdp"),
    "GGXWDN_G01_GDP_PT": ("fm", "general_gov_net", "debt_gdp"),
    "GGXCNL_G01_GDP_PT": ("fm", "general_gov_gross", "fiscal_balance_gdp"),
    "GGXONLB_G01_GDP_PT": ("fm", "general_gov_gross", "primary_balance_gdp"),
    "GGR_G01_GDP_PT": ("fm", "general_gov_gross", "revenue_gdp"),
    "NGDP_RPCH": ("weo", "macro", "rgdp_growth"),
    "PCPIPCH": ("weo", "macro", "cpi_inflation"),
    "GG_DEBT_GDP": ("gdd", "general_gov_gross", "debt_gdp"),
    "CG_DEBT_GDP": ("gdd", "central_gov_gross", "debt_gdp"),
    "HH_LS": ("gdd", "households", "debt_gdp"),
    "NFC_LS": ("gdd", "nfc", "debt_gdp"),
    "PVD_LS": ("gdd", "private_nonfin", "debt_gdp"),
}
STAGED_TABLE = "staged/imf/datamapper"
MART_TABLE = "marts/imf_debt_panel"
_ISO3 = re.compile(r"^[A-Z]{3}$")
_YEAR = re.compile(r"^\d{4}$")


def url(code: str) -> str:
    return f"{BASE}/{code}"


def raw_name(code: str) -> str:
    return f"{code}.json"


class _Series(RootModel[dict[str, dict[str, float | None]]]):
    pass


class _Doc(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # WEO payloads carry a stray empty-named key with a null value next to the indicator.
    values: dict[str, _Series | None] = {}


def parse(payload: bytes, code: str) -> list[dict[str, object]]:
    """→ [{iso3, year, dataset, code, value, source}] for one indicator, actual years only,
    sorted by (iso3, year). Empty ``values`` (unknown code) is a ValueError."""
    if code not in INDICATORS:
        msg = f"imf: unknown indicator {code}"
        raise ValueError(msg)
    try:
        doc = _Doc.model_validate(json.loads(payload))
    except (ValueError, ValidationError) as e:
        msg = f"imf: unexpected response for {code} ({type(e).__name__})"
        raise ValueError(msg) from e
    series = doc.values.get(code)
    if series is None or not series.root:
        msg = f"imf: no values for {code} (unknown indicator or empty response)"
        raise ValueError(msg)
    dataset = INDICATORS[code][0]
    out: list[dict[str, object]] = []
    for area, by_year in series.root.items():
        if not _ISO3.match(area):
            continue
        for y, v in by_year.items():
            if v is None or not _YEAR.match(y) or int(y) > LAST_ACTUAL_YEAR:
                continue
            out.append(
                {
                    "iso3": area,
                    "year": int(y),
                    "dataset": dataset,
                    "code": code,
                    "value": float(v),
                    "source": SOURCE,
                }
            )
    out.sort(key=lambda r: (str(r["iso3"]), int(str(r["year"]))))
    return out


def build_mart(staged: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Staged rows (all indicators) → long panel rows (iso3, year, unit, metric, value, source)
    with ``source`` = ``imf_<dataset>``. Adds ``interest_gdp`` = primary − overall balance
    (net interest: paid minus received) for (iso3, year) where both come from the Fiscal
    Monitor (unrounded; the WEO overall balance is rounded to 0.1 and is not used here)."""
    out: list[dict[str, object]] = []
    overall: dict[tuple[str, int], float] = {}
    primary: dict[tuple[str, int], float] = {}
    for r in staged:
        code = str(r["code"])
        dataset, unit, metric = INDICATORS[code]
        key = (str(r["iso3"]), int(str(r["year"])))
        value = float(str(r["value"]))
        out.append(
            {
                "iso3": key[0],
                "year": key[1],
                "unit": unit,
                "metric": metric,
                "value": value,
                "source": f"{SOURCE}_{dataset}",
            }
        )
        if code == "GGXCNL_G01_GDP_PT":
            overall[key] = value
        elif code == "GGXONLB_G01_GDP_PT":
            primary[key] = value
    for key in sorted(set(overall) & set(primary)):
        out.append(
            {
                "iso3": key[0],
                "year": key[1],
                "unit": "general_gov_gross",
                "metric": "interest_gdp",
                "value": primary[key] - overall[key],
                "source": f"{SOURCE}_fm",
            }
        )
    out.sort(
        key=lambda x: (
            str(x["iso3"]),
            int(str(x["year"])),
            str(x["unit"]),
            str(x["metric"]),
            str(x["source"]),
        )
    )
    return out
