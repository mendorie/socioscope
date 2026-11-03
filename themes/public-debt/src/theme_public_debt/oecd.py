"""OECD Economic Outlook (sdmx.oecd.org, no key): gross / net general government interest and
nominal GDP for the 18 JST countries, 1990–. Pure transforms only (no I/O).

Dataflow ``OECD.ECO.MAD,DSD_EO@DF_EO`` (Economic Outlook 119). Measures used:
``GGINTP`` gross interest payments, ``GGINTR`` gross interest receipts, ``GNINTP`` net interest
payments, ``GDP`` nominal GDP — all in national currency (UNIT_MEASURE ``XDC``). The mart
divides each interest series by GDP of the same year (% of GDP). Years after
``LAST_ACTUAL_YEAR`` are projections in the EO and are dropped at parse time.

``parse`` reads ``dimensionAtObservation=AllDimensions`` observation keys (``i:j:k…``) back
to dimension values. In this dataflow UNIT_MEASURE is an *observation attribute* (the n-th
entry after the value indexes ``attributes.observation[n].values``), so it is read from there;
if it is a dimension instead, it is read from the key. Missing dimensions, no unit at all,
non-JSON, or no observations → ValueError.

License: OECD Terms & Conditions (2024-07-01; free use incl. commercial with attribution,
https://www.oecd.org/en/about/terms-conditions.html, confirmed 2026-11-03). Cite as
"OECD (2026), OECD Economic Outlook 119, https://sdmx.oecd.org (accessed 2026-11-03)".
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

SOURCE = "oecd_eo"
LICENSE = (
    "OECD Terms & Conditions 2024-07-01 (free use with attribution, "
    "https://www.oecd.org/en/about/terms-conditions.html)"
)
BASE = "https://sdmx.oecd.org/public/rest/data"
FLOW = "OECD.ECO.MAD,DSD_EO@DF_EO,"
MAGIC = b"{"
LAST_ACTUAL_YEAR = 2025
COUNTRIES: tuple[str, ...] = (
    "AUS",
    "BEL",
    "CAN",
    "CHE",
    "DEU",
    "DNK",
    "ESP",
    "FIN",
    "FRA",
    "GBR",
    "IRL",
    "ITA",
    "JPN",
    "NLD",
    "NOR",
    "PRT",
    "SWE",
    "USA",
)
# MEASURE -> staged metric name (all national currency, current prices)
MEASURES: dict[str, str] = {
    "GGINTP": "interest_paid_lcu",
    "GGINTR": "interest_received_lcu",
    "GNINTP": "net_interest_lcu",
    "GDP": "ngdp_lcu",
}
UNIT = "XDC"
URL = (
    f"{BASE}/{FLOW}/{'+'.join(COUNTRIES)}.{'+'.join(MEASURES)}.A"
    "?startPeriod=1990&dimensionAtObservation=AllDimensions&format=jsondata"
)
RAW_NAME = "eo_interest_gdp_1990.json"
STAGED_TABLE = "staged/oecd/eo_interest"
MART_TABLE = "marts/oecd_interest_panel"


def _structure(doc: Mapping[str, Any]) -> Mapping[str, Any]:
    data = doc.get("data")
    if not isinstance(data, dict):
        msg = "oecd: no 'data' object"
        raise ValueError(msg)
    structure = data.get("structures", [None])[0] if "structures" in data else data.get("structure")
    if not isinstance(structure, dict):
        msg = "oecd: no structure"
        raise ValueError(msg)
    return structure


def _dimensions(structure: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    dims = structure.get("dimensions", {}).get("observation")
    if not isinstance(dims, list) or not dims:
        msg = "oecd: no observation dimensions (use dimensionAtObservation=AllDimensions)"
        raise ValueError(msg)
    return [(str(d["id"]), [str(v["id"]) for v in d["values"]]) for d in dims]


def _obs_attributes(structure: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    attrs = structure.get("attributes", {}).get("observation") or []
    return [(str(a["id"]), [str(v.get("id")) for v in a.get("values", [])]) for a in attrs]


def parse(payload: bytes) -> list[dict[str, object]]:
    """SDMX-JSON → [{iso3, year, metric, value, source}] for the adopted measures, unit XDC,
    actual years only, sorted by (iso3, metric, year). Duplicate (iso3, metric, year) with a
    different value is a ValueError."""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"oecd: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, dict):
        msg = "oecd: expected a JSON object"
        raise ValueError(msg)
    structure = _structure(doc)
    dims = _dimensions(structure)
    ids = [d[0] for d in dims]
    needed = ("REF_AREA", "MEASURE", "TIME_PERIOD")
    if any(k not in ids for k in needed):
        msg = f"oecd: dimensions {needed} required, got {ids}"
        raise ValueError(msg)
    attrs = _obs_attributes(structure)
    unit_attr = next((n for n, (aid, _v) in enumerate(attrs) if aid == "UNIT_MEASURE"), None)
    if "UNIT_MEASURE" not in ids and unit_attr is None:
        msg = "oecd: UNIT_MEASURE is neither a dimension nor an observation attribute"
        raise ValueError(msg)
    datasets = doc["data"].get("dataSets") or []
    obs = datasets[0].get("observations") if datasets else None
    if not isinstance(obs, dict) or not obs:
        msg = "oecd: no observations"
        raise ValueError(msg)
    seen: dict[tuple[str, str, int], float] = {}
    for key, vals in obs.items():
        idx = [int(i) for i in key.split(":")]
        if len(idx) != len(dims):
            msg = f"oecd: key {key!r} does not match {len(dims)} dimensions"
            raise ValueError(msg)
        at = {ids[n]: dims[n][1][i] for n, i in enumerate(idx)}
        metric = MEASURES.get(at["MEASURE"])
        value = vals[0] if isinstance(vals, list) and vals else None
        unit = at.get("UNIT_MEASURE")
        if unit is None and unit_attr is not None:
            a = (
                vals[1 + unit_attr]
                if isinstance(vals, list) and len(vals) > 1 + unit_attr
                else None
            )
            unit = attrs[unit_attr][1][int(a)] if isinstance(a, int) else None
        if metric is None or unit != UNIT or at["REF_AREA"] not in COUNTRIES or value is None:
            continue
        year = int(at["TIME_PERIOD"])
        if year > LAST_ACTUAL_YEAR:
            continue
        k = (at["REF_AREA"], metric, year)
        if k in seen and seen[k] != float(value):
            msg = f"oecd: conflicting duplicate observation {k}"
            raise ValueError(msg)
        seen[k] = float(value)
    rows = [
        {"iso3": k[0], "year": k[2], "metric": k[1], "value": v, "source": SOURCE}
        for k, v in seen.items()
    ]
    rows.sort(key=lambda r: (str(r["iso3"]), str(r["metric"]), int(str(r["year"]))))
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """→ long panel rows: unit general_gov_gross, metrics gross_interest_gdp /
    interest_received_gdp / net_interest_gdp (% of GDP, same-year nominal GDP), source oecd_eo.
    Rows without GDP for that (iso3, year) are dropped."""
    gdp: dict[tuple[str, int], float] = {}
    by_key: dict[tuple[str, int, str], float] = {}
    for r in staged:
        key = (str(r["iso3"]), int(str(r["year"])))
        metric = str(r["metric"])
        value = float(str(r["value"]))
        if metric == "ngdp_lcu":
            gdp[key] = value
        else:
            by_key[(*key, metric)] = value
    names = {
        "interest_paid_lcu": "gross_interest_gdp",
        "interest_received_lcu": "interest_received_gdp",
        "net_interest_lcu": "net_interest_gdp",
    }
    out: list[dict[str, object]] = []
    for (iso3, year, metric), value in by_key.items():
        g = gdp.get((iso3, year))
        if g is None or g == 0:
            continue
        out.append(
            {
                "iso3": iso3,
                "year": year,
                "unit": "general_gov_gross",
                "metric": names[metric],
                "value": 100.0 * value / g,
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: (str(r["iso3"]), int(str(r["year"])), str(r["metric"])))
    return out
