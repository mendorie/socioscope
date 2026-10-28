"""国会会議録検索システム API（kokkai.ndl.go.jp、鍵不要）: 衆議院の会議の一覧（H13）。

本会議・委員会等を年ごとに取る。

Pure transforms only (no I/O). `meeting_list` を年ごと・100 件ずつ（`maximumRecords=100`、
`startRecord`）で取り、会議 1 件 1 行（date, name_of_meeting, session）にする。`numberOfRecords` と
`nextRecordPosition` で終端を判断。fail-closed（JSON でない・必須キーが無い）。

License: 国会会議録検索システムの API は出典を明示して利用できる（国立国会図書館、
https://kokkai.ndl.go.jp/api.html、2026-10-29 確認）。
出典表記「国立国会図書館 国会会議録検索システム」。
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Mapping, Sequence

SOURCE = "kokkai_ndl"
LICENSE = "出典明示で利用可（国立国会図書館 国会会議録検索システム API、https://kokkai.ndl.go.jp/api.html）"
BASE = "https://kokkai.ndl.go.jp/api/meeting_list"
HOUSE = "衆議院"
YEARS: tuple[int, ...] = tuple(range(2013, 2026))  # 内閣法制局の集計（R5）と同じ 2013 年から
PAGE_SIZE = 100
MAX_PAGES = 12  # 1 年の会議は 600〜900 件 → 最大 9 ページ。安全側の上限
MAGIC = b"{"
PLENARY = "本会議"


def url(year: int, page: int) -> str:
    q = {
        "nameOfHouse": HOUSE,
        "from": f"{year}-01-01",
        "until": f"{year}-12-31",
        "maximumRecords": PAGE_SIZE,
        "startRecord": (page - 1) * PAGE_SIZE + 1,
        "recordPacking": "json",
    }
    return BASE + "?" + urllib.parse.urlencode(q)


def raw_name(year: int, page: int) -> str:
    return f"meetings_{year}_p{page}.json"


def has_next(payload: bytes) -> bool:
    doc = json.loads(payload)
    return doc.get("nextRecordPosition") is not None


def parse(payload: bytes, year: int, page: int) -> list[dict[str, object]]:
    """1 ページ → 会議 1 行: issue_id, date, name_of_meeting, session, is_plenary。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"kokkai {year} p{page}: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, dict) or not isinstance(doc.get("meetingRecord"), list):
        msg = f"kokkai {year} p{page}: missing meetingRecord"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for m in doc["meetingRecord"]:
        if not isinstance(m, dict) or not all(k in m for k in ("issueID", "date", "nameOfMeeting")):
            msg = f"kokkai {year} p{page}: record without issueID/date/nameOfMeeting"
            raise ValueError(msg)
        if str(m.get("nameOfHouse") or HOUSE) != HOUSE:
            continue
        name = str(m["nameOfMeeting"])
        rows.append(
            {
                "issue_id": str(m["issueID"]),
                "date": str(m["date"])[:10],
                "name_of_meeting": name,
                "session": int(m["session"]) if m.get("session") is not None else None,
                "is_plenary": name == PLENARY,
            }
        )
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """年 × 指標: plenary_days（本会議の開会日数）, committee_meetings（本会議以外の会議数）,
    committee_days（本会議以外の会議があった日数）, sitting_days（いずれかの会議があった日数）。"""
    by_year: dict[int, dict[str, set[str]]] = {}
    seen: set[str] = set()
    for r in staged:
        iid = str(r["issue_id"])
        if iid in seen:
            msg = f"kokkai: duplicate issue_id {iid}"
            raise ValueError(msg)
        seen.add(iid)
        y = int(str(r["date"])[:4])
        d = by_year.setdefault(y, {"plenary": set(), "committee": set(), "committee_ids": set()})
        if r["is_plenary"]:
            d["plenary"].add(str(r["date"]))
        else:
            d["committee"].add(str(r["date"]))
            d["committee_ids"].add(iid)
    out: list[dict[str, object]] = []
    for y in sorted(by_year):
        d = by_year[y]
        metrics = {
            "plenary_days": len(d["plenary"]),
            "committee_meetings": len(d["committee_ids"]),
            "committee_days": len(d["committee"]),
            "sitting_days": len(d["plenary"] | d["committee"]),
        }
        for k, v in metrics.items():
            out.append({"iso3": "JPN", "year": y, "metric": k, "value": v, "source": SOURCE})
    return out
