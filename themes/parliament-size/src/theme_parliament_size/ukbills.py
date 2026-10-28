"""UK Parliament Bills API（https://bills-api.parliament.uk/api/v1/Bills、鍵不要）: 法案 1 件 1 行。

H2d（議員立法の成立シェア）に使う。

Pure transforms only (no I/O). `Take=100&Skip=N` でページを辿る（`totalResults` で終端）。
`isAct` が真の法案は `currentStage` が Royal Assent（stageId 11）で、その `stageSittings[].date` が
成立日。`billTypeId` の 5・7・8・2 が Private Members' Bill（議員提出）、1 が Government Bill。
`IsAct` クエリは API 側で効かないので、絞り込みは parse 側で行う。

License: Open Parliament Licence v3.0（出典表示で利用可。
https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

SOURCE = "uk_bills"
LICENSE = "Open Parliament Licence v3.0 (UK Parliament, https://bills-api.parliament.uk)"
BASE = "https://bills-api.parliament.uk/api/v1/Bills"
PAGE_SIZE = 100
MAX_PAGES = 80  # 4,065 bills in 2026-10 → 41 pages; hard stop for safety
ROYAL_ASSENT_STAGE = 11
PRIVATE_MEMBER_TYPES: frozenset[int] = frozenset({2, 5, 7, 8})
GOVERNMENT_TYPES: frozenset[int] = frozenset({1, 10})  # Government Bill, Supply and Appropriation
TYPE_NAMES: dict[int, str] = {
    1: "Government Bill",
    2: "Private Members' Bill (Starting in the House of Lords)",
    3: "Consolidation Bill",
    4: "Hybrid Bill",
    5: "Private Members' Bill (under the Ten Minute Rule)",
    6: "Private Bill",
    7: "Private Members' Bill (Ballot Bill)",
    8: "Private Members' Bill (Presentation Bill)",
    9: "Draft Bill",
    10: "Supply and Appropriation Bill",
}


def url(page: int) -> str:
    return f"{BASE}?Take={PAGE_SIZE}&Skip={(page - 1) * PAGE_SIZE}"


def raw_name(page: int) -> str:
    return f"bills_p{page}.json"


def has_next(payload: bytes, page: int) -> bool:
    doc = json.loads(payload)
    total = int(doc.get("totalResults", 0))
    return page * PAGE_SIZE < total


def origin_of(bill_type_id: int) -> str:
    if bill_type_id in PRIVATE_MEMBER_TYPES:
        return "member"
    if bill_type_id in GOVERNMENT_TYPES:
        return "government"
    return "other"


def parse(payload: bytes, page: int) -> list[dict[str, object]]:
    """1 ページ → 法案 1 行: bill_id, title, bill_type_id, bill_type, origin, is_act,
    royal_assent_date, introduced_session_id。Fail-closed。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"uk_bills page {page}: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list):
        msg = f"uk_bills page {page}: missing 'items' list"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for item in doc["items"]:
        if not isinstance(item, dict) or "billId" not in item or "billTypeId" not in item:
            msg = f"uk_bills page {page}: item without billId/billTypeId"
            raise ValueError(msg)
        is_act = bool(item.get("isAct"))
        assent: str | None = None
        stage = item.get("currentStage") or {}
        if is_act:
            if stage.get("stageId") != ROYAL_ASSENT_STAGE:
                msg = f"uk_bills page {page}: act {item['billId']} not at Royal Assent stage"
                raise ValueError(msg)
            dates = [str(s.get("date") or "")[:10] for s in stage.get("stageSittings") or []]
            dates = [d for d in dates if d]
            if not dates:
                msg = f"uk_bills page {page}: act {item['billId']} without Royal Assent date"
                raise ValueError(msg)
            assent = max(dates)
        t = int(item["billTypeId"])
        rows.append(
            {
                "bill_id": int(item["billId"]),
                "title": str(item.get("shortTitle") or ""),
                "bill_type_id": t,
                "bill_type": TYPE_NAMES.get(t, "unknown"),
                "origin": origin_of(t),
                "is_act": is_act,
                "royal_assent_date": assent,
                "introduced_session_id": item.get("introducedSessionId"),
            }
        )
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """成立法案（is_act）だけを 1 行ずつ: iso3, year（Royal Assent の年）, bill_id, origin,
    bill_type。"""
    out: list[dict[str, object]] = []
    seen: set[int] = set()
    for r in staged:
        if not r.get("is_act"):
            continue
        bid = int(str(r["bill_id"]))
        if bid in seen:
            msg = f"uk_bills: duplicate bill_id {bid}"
            raise ValueError(msg)
        seen.add(bid)
        out.append(
            {
                "iso3": "GBR",
                "year": int(str(r["royal_assent_date"])[:4]),
                "royal_assent_date": r["royal_assent_date"],
                "bill_id": bid,
                "title": r["title"],
                "bill_type_id": r["bill_type_id"],
                "bill_type": r["bill_type"],
                "origin": r["origin"],
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: (str(r["royal_assent_date"]), int(str(r["bill_id"]))))
    return out
