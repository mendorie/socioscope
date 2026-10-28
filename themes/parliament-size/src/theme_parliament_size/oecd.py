"""OECD Data Explorer SDMX-JSON（sdmx.oecd.org、鍵不要）: Government at a Glance 2025 の公的財政。

番外編 R16（H15a〜d）に使う。一般政府（S13）の支出 `GE` と収入 `GR` の対 GDP 比（`PT_B1GQ`）、
2007〜2024 年を 1 リクエストで取る（`format=jsondata` で Accept ヘッダなしでも SDMX-JSON）。
Pure transforms only (no I/O)。`parse` は
dimensionAtObservation=AllDimensions の観測キー（`i:j:k:...`）を次元の値に戻し、
国 × 年 × 指標 の long 行にする。構造が無い・次元が足りない・単位が % GDP 以外の行は捨て、
JSON でない・観測が無い場合は ValueError（fail-closed）。

License: OECD Terms & Conditions（2024-07-01 改定。出典表示で商用含め自由利用。
https://www.oecd.org/en/about/terms-conditions.html、2026-10-29 確認）。
出典表記「OECD (2025), Government at a Glance 2025, https://sdmx.oecd.org (accessed 2026-10-29)」。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

SOURCE = "oecd_gov_glance"
LICENSE = (
    "OECD Terms & Conditions 2024-07-01 (free use with attribution, "
    "https://www.oecd.org/en/about/terms-conditions.html)"
)
FLOW = "OECD.GOV.GIP,DSD_GOV@DF_GOV_PF_2025,1.0"
URL = (
    f"https://sdmx.oecd.org/public/rest/data/{FLOW}/A..GE+GR....?startPeriod=2007&endPeriod=2024"
    "&dimensionAtObservation=AllDimensions&format=jsondata"
)
RAW_NAME = "gov_pf_2025_ge_gr.json"
MAGIC = b"{"
UNIT = "PT_B1GQ"  # % of GDP
SECTOR = "S13"  # general government
METRICS: dict[str, str] = {
    "GE": "gov_expenditure_pct_gdp",
    "GR": "gov_revenue_pct_gdp",
}


def _dimensions(doc: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    data = doc.get("data")
    if not isinstance(data, dict):
        msg = "oecd: no 'data' object"
        raise ValueError(msg)
    structure = data.get("structures", [None])[0] if "structures" in data else data.get("structure")
    if not isinstance(structure, dict):
        msg = "oecd: no structure"
        raise ValueError(msg)
    dims = structure.get("dimensions", {}).get("observation")
    if not isinstance(dims, list) or not dims:
        msg = "oecd: no observation dimensions (use dimensionAtObservation=AllDimensions)"
        raise ValueError(msg)
    return [(str(d["id"]), [str(v["id"]) for v in d["values"]]) for d in dims]


def parse(payload: bytes) -> list[dict[str, object]]:
    """SDMX-JSON → [{iso3, year, metric, value}]（% GDP・一般政府・ISO3 の国のみ）。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"oecd: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, dict):
        msg = "oecd: expected a JSON object"
        raise ValueError(msg)
    dims = _dimensions(doc)
    ids = [d[0] for d in dims]
    needed = ("REF_AREA", "MEASURE", "UNIT_MEASURE", "SECTOR", "TIME_PERIOD")
    if any(k not in ids for k in needed):
        msg = f"oecd: dimensions {needed} required, got {ids}"
        raise ValueError(msg)
    datasets = doc["data"].get("dataSets") or []
    obs = datasets[0].get("observations") if datasets else None
    if not isinstance(obs, dict) or not obs:
        msg = "oecd: no observations"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for key, vals in obs.items():
        idx = [int(i) for i in key.split(":")]
        if len(idx) != len(dims):
            msg = f"oecd: key {key!r} does not match {len(dims)} dimensions"
            raise ValueError(msg)
        at = {ids[n]: dims[n][1][i] for n, i in enumerate(idx)}
        metric = METRICS.get(at["MEASURE"])
        value = vals[0] if isinstance(vals, list) and vals else None
        if (
            metric is None
            or at["UNIT_MEASURE"] != UNIT
            or at["SECTOR"] != SECTOR
            or len(at["REF_AREA"]) != 3
            or value is None
        ):
            continue
        rows.append(
            {
                "iso3": at["REF_AREA"],
                "year": int(at["TIME_PERIOD"]),
                "metric": metric,
                "value": float(value),
            }
        )
    rows.sort(key=lambda r: (str(r["iso3"]), str(r["metric"]), int(str(r["year"]))))
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """国 × 年 × 指標 の long mart。同じキーが 2 行あれば ValueError。"""
    seen: set[tuple[str, int, str]] = set()
    out: list[dict[str, object]] = []
    for r in staged:
        key = (str(r["iso3"]), int(str(r["year"])), str(r["metric"]))
        if key in seen:
            msg = f"oecd: duplicate {key}"
            raise ValueError(msg)
        seen.add(key)
        out.append(
            {
                "iso3": key[0],
                "year": key[1],
                "metric": key[2],
                "value": r["value"],
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: (str(r["iso3"]), str(r["metric"]), int(str(r["year"]))))
    return out
