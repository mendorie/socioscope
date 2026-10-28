"""ParlGov 2024 Release（Harvard Dataverse）`view_election.tab`: 選挙ごとの総議席数。

H6b（定数履歴）に使う。

Pure transforms only (no I/O). Dataverse の API（`/api/access/datafile/<id>`）で tab 区切りを取る。
`parse` は parliament 選挙だけを残し、選挙 × 国 で 1 行（seats_total は全党で同じ値）にする。
列が無い・値が数値でない場合は ValueError（fail-closed）。

License: Dataverse 上の ParlGov 2024 Release は CC0 1.0（2026-10-28 確認）。parlgov.org 本体は
CC BY 4.0。
出典: Döring, Holger and Philip Manow. 2024. Parliaments and governments database (ParlGov).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence

SOURCE = "parlgov"
LICENSE = (
    "CC0 1.0 (ParlGov 2024 Release on Harvard Dataverse, doi:10.7910/DVN/2VZ5ZC; "
    "cite Döring & Manow 2024, parlgov.org)"
)
FILE_ID = 10437092  # view_election.tab in the 2024 release (doi:10.7910/DVN/2VZ5ZC)
URL = f"https://dataverse.harvard.edu/api/access/datafile/{FILE_ID}"
RAW_NAME = "parlgov2024_view_election.tab"
MAGIC = b"country_name_short"
REQUIRED = ("country_name_short", "election_type", "election_date", "seats_total", "election_id")


def parse(payload: bytes) -> list[dict[str, object]]:
    """tab → [{iso3, election_date, election_id, seats_total}]。

    parliament 選挙のみ、国 × 選挙で 1 行。"""
    text = payload.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t", quotechar='"')
    cols = reader.fieldnames or []
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        msg = f"parlgov: missing columns {missing}"
        raise ValueError(msg)
    seen: dict[tuple[str, str], dict[str, object]] = {}
    for row in reader:
        if row["election_type"] != "parliament":
            continue
        key = (row["country_name_short"], row["election_date"])
        try:
            seats = int(row["seats_total"])
            eid = int(row["election_id"])
        except (TypeError, ValueError) as e:
            msg = f"parlgov: non-numeric seats_total/election_id in {key}"
            raise ValueError(msg) from e
        prev = seen.get(key)
        if prev is not None and prev["seats_total"] != seats:
            msg = f"parlgov: seats_total differs within election {key}"
            raise ValueError(msg)
        seen[key] = {
            "iso3": key[0],
            "election_date": key[1],
            "election_id": eid,
            "seats_total": seats,
        }
    out = list(seen.values())
    out.sort(key=lambda r: (str(r["iso3"]), str(r["election_date"])))
    return out


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    out = [
        {
            "iso3": r["iso3"],
            "year": int(str(r["election_date"])[:4]),
            "election_date": r["election_date"],
            "election_id": r["election_id"],
            "seats_total": r["seats_total"],
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: (str(r["iso3"]), str(r["election_date"])))
    return out
