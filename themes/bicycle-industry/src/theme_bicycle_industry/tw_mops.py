"""台湾 MOPS（公開資訊觀測站）月次売上 JSON API → long 行の純粋変換。

`POST https://mops.twse.com.tw/mops/api/t05st10_ifrs`、本文 `{"companyId": "9921", "dataType": "2",
"subsidiaryCompanyId": "", "year": "<民國年>", "month": "<1–12>"}`（キー不要、robots.txt なし）。
`dataType` は "2"（自訂）でないと最新月しか返らない。収録は民國 103 年（2014 年）1 月から。
応答 `result.data`（配列）の `本月`（当月売上、NT$ 千、カンマ区切り文字列）等を使う。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

SOURCE = "tw_mops"
LICENSE = (
    "臺灣證券交易所 公開資訊觀測站（MOPS）の公開開示データ。"
    "政府資料開放授權條款 v1 準拠の公開情報として"
    "出典表示で利用、raw 非コミット（確認 2026-10-22）"
)
URL = "https://mops.twse.com.tw/mops/api/t05st10_ifrs"
COMPANIES: dict[str, str] = {
    "9921": "giant",
    "9914": "merida",
    "5306": "kmc",
    "8933": "ideal_bike",
}
START_YEAR, END_YEAR = 2014, 2026


def roc_year(year: int) -> int:
    return year - 1911


def body(company_id: str, year: int, month: int) -> dict[str, object]:
    return {
        "companyId": company_id,
        "dataType": "2",
        "subsidiaryCompanyId": "",
        "year": str(roc_year(year)),
        "month": str(month),
    }


def raw_name(company_id: str, year: int, month: int) -> str:
    return f"mops_{company_id}_{year}_{month:02d}.json"


def requests() -> list[tuple[str, int, int]]:
    return [
        (cid, y, m)
        for cid in COMPANIES
        for y in range(START_YEAR, END_YEAR + 1)
        for m in range(1, 13)
    ]


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


def _num(v: object) -> float | None:
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    if s in {"", "-", "N/A"}:
        return None
    return float(s)


def parse(payload: bytes, company_id: str, year: int, month: int) -> Parsed:
    """1 リクエスト分の JSON → 0 または 1 行 (company_id, company, year, month, period,
    revenue_ntd_k, revenue_prev_year_ntd_k, ytd_ntd_k, source)。

    `code` が 200 でも `data` が無い（未収録月）なら行なし＋skipped。
    JSON でない・会社不一致は ValueError。
    """
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = "payload is not JSON"
        raise ValueError(msg) from e
    if not isinstance(doc, dict) or "code" not in doc:
        msg = "unexpected MOPS payload"
        raise ValueError(msg)
    result = doc.get("result") or {}
    data = result.get("data") if isinstance(result, dict) else None
    if doc.get("code") != 200 or not data:
        return Parsed(rows=[], skipped=[f"{company_id} {year}-{month:02d}: {doc.get('message')}"])
    # `data` is a list of [label, value] pairs (labels in `titles`); accept a dict too
    fields: dict[str, object] = {}
    if isinstance(data, dict):
        fields = dict(data)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, list | tuple) and len(item) == 2:
                fields[str(item[0])] = item[1]
            elif isinstance(item, dict):
                fields.update(item)
    if "本月" not in fields:
        msg = f"MOPS data has no 本月 field: {str(data)[:120]!r}"
        raise ValueError(msg)
    yymm = str(result.get("yymm", "")).strip()
    expected = f"{roc_year(year)}{month:02d}"
    if yymm and yymm != expected:
        msg = f"MOPS yymm {yymm} does not match request {expected}"
        raise ValueError(msg)
    if company_id not in COMPANIES:
        msg = f"unknown company {company_id}"
        raise ValueError(msg)
    row = fields
    return Parsed(
        rows=[
            {
                "company_id": company_id,
                "company": COMPANIES[company_id],
                "year": year,
                "month": month,
                "period": f"{year}-{month:02d}",
                "revenue_ntd_k": _num(row.get("本月")),
                "revenue_prev_year_ntd_k": _num(row.get("去年同期")),
                "ytd_ntd_k": _num(row.get("本年累計")),
                "source": SOURCE,
            }
        ]
    )


MART_KEY: tuple[str, ...] = ("company_id", "period")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    out = [{"iso3": "TWN", **r} for r in staged]
    out.sort(key=lambda r: tuple(str(r[c]) for c in MART_KEY))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in MART_KEY)
        if k in seen:
            msg = f"duplicate mops key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out
