"""イタリア下院 open data（dati.camera.it SPARQL、鍵不要）: 年別の成立法律数と本会議回数（H7）。

Pure transforms only (no I/O). SPARQL の集計クエリ 2 本（`ocd:legge` を公布日の年で、
`ocd:seduta` のうち `ocd:rif_assemblea` を持つ本会議を日付の年で数える）の JSON 結果をそのまま
raw にする。
`parse` は `results.bindings` の (y, n) を {year, metric, value} にする（fail-closed）。

License: dati.camera.it のデータは CC BY 4.0（https://dati.camera.it/it/note-legali/、
2026-10-29 確認）。
出典表記「Camera dei deputati, dati.camera.it (accessed 2026-10-29)」。
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping, Sequence

SOURCE = "camera_it"
LICENSE = "CC BY 4.0 (Camera dei deputati, dati.camera.it)"
ENDPOINT = "https://dati.camera.it/sparql"
_PREFIX = "PREFIX dc:<http://purl.org/dc/elements/1.1/> PREFIX ocd:<http://dati.camera.it/ocd/> "
LAWS_QUERY = (
    _PREFIX + "SELECT (SUBSTR(STR(?d),1,4) AS ?y) (COUNT(DISTINCT ?s) AS ?n) "
    "WHERE {?s a ocd:legge; dc:date ?d} GROUP BY (SUBSTR(STR(?d),1,4)) ORDER BY ?y"
)
SITTINGS_QUERY = (
    _PREFIX + "SELECT (SUBSTR(STR(?d),1,4) AS ?y) (COUNT(DISTINCT ?s) AS ?n) "
    "WHERE {?s a ocd:seduta; ocd:rif_assemblea ?a; dc:date ?d} "
    "GROUP BY (SUBSTR(STR(?d),1,4)) ORDER BY ?y"
)
MAGIC = b"{"


def url(query: str) -> str:
    return (
        ENDPOINT
        + "?"
        + urllib.parse.urlencode({"query": query, "format": "application/sparql-results+json"})
    )


LAWS_URL = url(LAWS_QUERY)
SITTINGS_URL = url(SITTINGS_QUERY)
LAWS_RAW_NAME = "camera_leggi_by_year.json"
SITTINGS_RAW_NAME = "camera_sedute_assemblea_by_year.json"


def parse(payload: bytes, metric: str) -> list[dict[str, object]]:
    """SPARQL JSON（y, n）→ [{iso3, year, metric, value}]。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"camera: not JSON ({e})"
        raise ValueError(msg) from e
    bindings = (doc.get("results") or {}).get("bindings") if isinstance(doc, dict) else None
    if not isinstance(bindings, list) or not bindings:
        msg = "camera: no results.bindings"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for b in bindings:
        try:
            y = int(b["y"]["value"])
            n = int(b["n"]["value"])
        except (KeyError, TypeError, ValueError) as e:
            msg = "camera: binding without numeric y/n"
            raise ValueError(msg) from e
        rows.append({"iso3": "ITA", "year": y, "metric": metric, "value": n})
    rows.sort(key=lambda r: int(str(r["year"])))
    return rows


def parse_laws(payload: bytes) -> list[dict[str, object]]:
    return parse(payload, "laws_promulgated")


def parse_sittings(payload: bytes) -> list[dict[str, object]]:
    return parse(payload, "plenary_sittings")


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    out = [
        {
            "iso3": "ITA",
            "year": int(str(r["year"])),
            "metric": r["metric"],
            "value": int(str(r["value"])),
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: (str(r["metric"]), int(str(r["year"]))))
    return out
