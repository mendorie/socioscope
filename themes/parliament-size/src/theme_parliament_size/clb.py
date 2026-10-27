"""内閣法制局「過去の法律案の提出・成立件数一覧」HTML: 国会回次別の 閣法／議員立法 提出・成立件数。

Pure transforms only (no I/O)。第 183 回（2013 年）以降を 1 ページに掲載。各セルは
「（継続 n 件） m 件」の形で、継続審査分は外数。`parse` は行ごとに 回次・会期種別・会期・
閣法提出／成立・議員立法提出／成立・計 を取り、
計 = 閣法 ＋ 議員立法 で検算する（fail-closed）。

License: 内閣法制局ホームページは政府標準利用規約（第 2.0 版、CC BY 4.0 互換）。出典表示で利用可。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

SOURCE = "clb_bills"
LICENSE = (
    "政府標準利用規約（第2.0版、CC BY 4.0 互換）。"
    "出典: 内閣法制局「過去の法律案の提出・成立件数一覧」"
    "（https://www.clb.go.jp/recent-laws/number/）"
)
URL = "https://www.clb.go.jp/recent-laws/number/"
RAW_NAME = "clb_bill_counts.html"

_SESSION = re.compile(r"第(\d+)回（(.+?)）")
_CELL = re.compile(r"（継続\s*(\d+)\s*件）\s*(\d+)\s*件")
_ERA = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}
_DATE = re.compile(r"(明治|大正|昭和|平成|令和)\s*(\d+|元)年\s*(\d+)月\s*(\d+)日")


class _Tables(HTMLParser):
    """全 <table> を [[[cell text]]] に落とす最小のパーサ。"""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None and self.tables:
            self.tables[-1].append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def _wareki(text: str) -> str:
    """「令和8年2月18日」→ "2026-02-18"（最初の日付）。見つからなければ ""。"""
    m = _DATE.search(text)
    if not m:
        return ""
    y = 1 if m.group(2) == "元" else int(m.group(2))
    return f"{_ERA[m.group(1)] + y:04d}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"


def parse(payload: bytes) -> list[dict[str, object]]:
    """HTML → [{session, kind, period, start_date, cabinet_submitted, cabinet_enacted,
    member_submitted, member_enacted, total_submitted, total_enacted, ...carried}]。"""
    html = payload.decode("utf-8", errors="replace")
    p = _Tables()
    p.feed(html)
    out: list[dict[str, object]] = []
    for table in p.tables:
        for row in table:
            if len(row) < 7:
                continue
            ms = _SESSION.search(row[0])
            cells = [_CELL.search(c) for c in row[1:7]]
            if not ms or any(c is None for c in cells):
                continue
            vals = [(int(c.group(1)), int(c.group(2))) for c in cells if c]
            (cs, ce, ms_, me, ts, te) = vals
            if ts[1] != cs[1] + ms_[1] or te[1] != ce[1] + me[1]:
                msg = f"session {ms.group(1)}: totals do not add up ({row})"
                raise ValueError(msg)
            out.append(
                {
                    "session": int(ms.group(1)),
                    "kind": ms.group(2),
                    "period": row[0].replace(ms.group(0), "").strip(),
                    "start_date": _wareki(row[0]),
                    "cabinet_submitted": cs[1],
                    "cabinet_enacted": ce[1],
                    "member_submitted": ms_[1],
                    "member_enacted": me[1],
                    "total_submitted": ts[1],
                    "total_enacted": te[1],
                    "cabinet_carried": cs[0],
                    "member_carried": ms_[0],
                }
            )
    if len(out) < 10:
        msg = f"expected the session table (>= 10 rows), got {len(out)}"
        raise ValueError(msg)
    out.sort(key=lambda r: int(str(r["session"])))
    sessions = [int(str(r["session"])) for r in out]
    if len(set(sessions)) != len(sessions):
        msg = "duplicate session rows"
        raise ValueError(msg)
    return out


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for r in staged:
        ce, me = int(str(r["cabinet_enacted"])), int(str(r["member_enacted"]))
        out.append(
            {
                "iso3": "JPN",
                "session": r["session"],
                "kind": r["kind"],
                "start_date": r["start_date"],
                "year": int(str(r["start_date"])[:4]) if r["start_date"] else None,
                "cabinet_submitted": r["cabinet_submitted"],
                "cabinet_enacted": ce,
                "member_submitted": r["member_submitted"],
                "member_enacted": me,
                "member_share_of_enacted": (me / (ce + me)) if ce + me else None,
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: int(str(r["session"])))
    return out
