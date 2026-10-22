"""価格指数: Eurostat HICP（JSON-stat 2.0）と US BLS CPI（v2 GET、キー不要）→ long 行の純粋変換。

- HICP `prc_hicp_midx`（2015=100、月次 1996–）。COICOP CP0711 自動車 / CP0712 二輪 / CP0713 自転車。
  このデータセットは「廃止・`prc_hicp_minr` に置換」と表示されるが 2026-10-22 時点で配信中。
  `prc_hicp_minr` は次元名が違い（COICOP 2018）、構造確認後に切り替える。
- BLS `CUUR0000SERC01`（Sports vehicles including bicycles、1982-84=100）と
  `CUUR0000SETA01`（New vehicles）。
  v2 GET は鍵なしで 10 年/リクエスト、25 リクエスト/日。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

HICP_SOURCE = "eurostat_hicp"
HICP_LICENSE = (
    "Eurostat copyright notice: 出典表示で商用含め再利用可（確認 2026-10-22）。"
    "出典: Eurostat, prc_hicp_midx"
)
HICP_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_midx"
HICP_COICOP: dict[str, str] = {"CP0711": "cars", "CP0712": "motorcycles", "CP0713": "bicycles"}
HICP_GEOS: tuple[str, ...] = (
    "EU27_2020",
    "EA20",
    "DE",
    "FR",
    "NL",
    "IT",
    "ES",
    "BE",
    "AT",
    "DK",
    "SE",
    "PL",
    "UK",
    "CH",
    "US",
)
# Eurostat geo → ISO3（EU/ユーロ圏の集計は疑似コード）
GEO_TO_ISO3: dict[str, str] = {
    "EU27_2020": "EU27",
    "EA20": "EA20",
    "DE": "DEU",
    "FR": "FRA",
    "NL": "NLD",
    "IT": "ITA",
    "ES": "ESP",
    "BE": "BEL",
    "AT": "AUT",
    "DK": "DNK",
    "SE": "SWE",
    "PL": "POL",
    "UK": "GBR",
    "CH": "CHE",
    "US": "USA",
}
HICP_SINCE = "2005-01"
HICP_RAW_NAME = "hicp_midx_cp071x.json"


def hicp_url() -> str:
    coicop = "".join(f"&coicop={c}" for c in HICP_COICOP)
    geo = "".join(f"&geo={g}" for g in HICP_GEOS)
    return f"{HICP_BASE}?format=JSON&lang=EN&unit=I15{coicop}{geo}&sinceTimePeriod={HICP_SINCE}"


BLS_SOURCE = "bls_cpi"
BLS_LICENSE = (
    "US BLS: パブリックドメイン（確認 2026-10-22）。出典: U.S. Bureau of Labor Statistics, CPI-U"
)
BLS_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data"
BLS_SERIES: dict[str, str] = {
    "CUUR0000SERC01": "sports_vehicles_incl_bicycles",
    "CUUR0000SETA01": "new_vehicles",
}
BLS_RANGES: tuple[tuple[int, int], ...] = ((2006, 2015), (2016, 2025), (2026, 2026))


def bls_url(series_id: str, start: int, end: int) -> str:
    return f"{BLS_BASE}/{series_id}?startyear={start}&endyear={end}"


def bls_raw_name(series_id: str, start: int, end: int) -> str:
    return f"bls_{series_id}_{start}_{end}.json"


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


def _load(payload: bytes) -> dict[str, object]:
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = "payload is not JSON"
        raise ValueError(msg) from e
    if not isinstance(doc, dict):
        msg = "payload is not a JSON object"
        raise ValueError(msg)
    return doc


def parse_hicp(payload: bytes) -> Parsed:
    """JSON-stat 2.0 → 行 (iso3, geo, series(cars/motorcycles/bicycles), coicop, period YYYY-MM,
    year, month, value, base("2015=100"), source)。疎な value は欠損として落とす。"""
    doc = _load(payload)
    if doc.get("class") != "dataset" or "dimension" not in doc or "value" not in doc:
        msg = "payload is not a JSON-stat dataset"
        raise ValueError(msg)
    ids = list(cast("list[str]", doc["id"]))
    size = list(cast("list[int]", doc["size"]))
    if ids != ["freq", "unit", "coicop", "geo", "time"]:
        msg = f"unexpected dimension order {ids}"
        raise ValueError(msg)
    dim = doc["dimension"]
    assert isinstance(dim, dict)
    unit_idx = dim["unit"]["category"]["index"]
    if list(unit_idx) != ["I15"]:
        msg = f"expected unit I15, got {list(unit_idx)}"
        raise ValueError(msg)
    coicop_idx = dim["coicop"]["category"]["index"]
    geo_idx = dim["geo"]["category"]["index"]
    time_idx = dim["time"]["category"]["index"]
    coicops = sorted(coicop_idx, key=lambda k: coicop_idx[k])
    geos = sorted(geo_idx, key=lambda k: geo_idx[k])
    times = sorted(time_idx, key=lambda k: time_idx[k])
    values = doc["value"]
    assert isinstance(values, dict)
    n_geo, n_time = size[3], size[4]
    out: list[dict[str, object]] = []
    skipped: list[str] = []
    for ci, c in enumerate(coicops):
        if c not in HICP_COICOP:
            skipped.append(f"unexpected coicop {c}")
            continue
        for gi, g in enumerate(geos):
            if g not in GEO_TO_ISO3:
                skipped.append(f"unexpected geo {g}")
                continue
            for ti, t in enumerate(times):
                flat = (ci * n_geo + gi) * n_time + ti
                v = values.get(str(flat))
                if v is None:
                    continue
                year, month = t.split("-")
                out.append(
                    {
                        "iso3": GEO_TO_ISO3[g],
                        "geo": g,
                        "series": HICP_COICOP[c],
                        "series_id": c,
                        "period": t,
                        "year": int(year),
                        "month": int(month),
                        "value": float(v),
                        "base": "2015=100",
                        "source": HICP_SOURCE,
                    }
                )
    return Parsed(rows=out, skipped=skipped)


def parse_bls(payload: bytes, series_id: str) -> Parsed:
    """BLS v2 JSON → 行（同じ列。iso3=USA、base="1982-84=100"）。

    REQUEST_SUCCEEDED 以外は ValueError。値 "-"（未公表）は落として skipped に出す。"""
    doc = _load(payload)
    if doc.get("status") != "REQUEST_SUCCEEDED":
        msg = f"BLS status {doc.get('status')!r}: {doc.get('message')}"
        raise ValueError(msg)
    results = doc.get("Results")
    assert isinstance(results, dict)
    series = [s for s in results.get("series", []) if s.get("seriesID") == series_id]
    if len(series) != 1:
        msg = f"series {series_id} not found exactly once in payload"
        raise ValueError(msg)
    if series_id not in BLS_SERIES:
        msg = f"unknown BLS series {series_id}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    skipped: list[str] = []
    for d in series[0]["data"]:
        p = str(d["period"])
        if not (p.startswith("M") and p != "M13"):
            skipped.append(f"{series_id}: non-monthly period {p} {d['year']}")
            continue
        month = int(p[1:])
        if str(d["value"]).strip() in {"-", ""}:
            skipped.append(f"{series_id}: value not published for {d['year']}-{month:02d}")
            continue
        out.append(
            {
                "iso3": "USA",
                "geo": "US",
                "series": BLS_SERIES[series_id],
                "series_id": series_id,
                "period": f"{d['year']}-{month:02d}",
                "year": int(d["year"]),
                "month": month,
                "value": float(d["value"]),
                "base": "1982-84=100",
                "source": BLS_SOURCE,
            }
        )
    return Parsed(rows=out, skipped=skipped)


MART_KEY: tuple[str, ...] = ("source", "geo", "series_id", "period")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    """HICP と BLS を 1 つの long 表に。キー順ソート、重複は ValueError。"""
    out = [dict(r) for r in staged]
    out.sort(key=lambda r: tuple(str(r[c]) for c in MART_KEY))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in MART_KEY)
        if k in seen:
            msg = f"duplicate price key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out
