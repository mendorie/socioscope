"""シマノ（7309、EDINET E02257）有価証券報告書 PDF → セグメント・地域別売上 行 の純粋変換。

EDINET の「PDF 表示用 URL」`…/searchdocument/pdf/<docID>.pdf` はキー不要で取れる
（2026-10-24 のメンテナンス後に URL 形式が変わる予告あり。raw は manifest 付きで保持）。
各有報は 当連結会計年度 と 前連結会計年度 の両方を載せるので、12 本で FY2013–FY2025 を二重に得る。

抽出するもの（百万円）:
- セグメント情報: 自転車部品／釣具／その他 の 外部顧客に対する売上高 と セグメント利益
- 地域ごとの情報: 日本／北米／ヨーロッパ／アジア／その他の地域 の売上高（顧客所在地ベース）
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from pypdf import PdfReader

SOURCE = "edinet_shimano"
LICENSE = (
    "EDINET（金融庁）開示書類。著作権は提出者（株式会社シマノ）。引用・非商用の研究目的で利用、"
    "raw PDF は非コミット（確認 2026-10-22）。出典: 株式会社シマノ 有価証券報告書（EDINET）"
)
BASE = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf"
# 事業年度（12 月期）→ docID。有報は翌年 3 月提出。
DOCS: dict[int, str] = {
    2025: "S100XQSE",
    2024: "S100VGFP",
    2023: "S100T5J9",
    2022: "S100QH4Z",
    2021: "S100NQC5",
    2020: "S100L203",
    2019: "S100IA93",
    2018: "S100FGAL",
    2017: "S100CMXI",
    2016: "S1009Z4C",
    2015: "S10078MN",
    2014: "S1004EF8",
}
SEGMENTS: tuple[str, ...] = ("bicycle_components", "fishing_tackle", "other")
REGIONS: tuple[str, ...] = ("japan", "north_america", "europe", "asia", "other_regions")


def url(fy: int) -> str:
    return f"{BASE}/{DOCS[fy]}.pdf"


def raw_name(fy: int) -> str:
    return f"shimano_yuho_fy{fy}_{DOCS[fy]}.pdf"


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


_NUM = r"(△\s?)?([\d,]+|－)"


def _to_int(sign: str | None, digits: str) -> int | None:
    if digits == "－":
        return None
    v = int(digits.replace(",", ""))
    return -v if sign else v


def _nums(line: str, n: int) -> list[int | None] | None:
    m = re.findall(_NUM, line)
    if len(m) < n:
        return None
    return [_to_int(s, d) for s, d in m[:n]]


def pdf_text(payload: bytes) -> list[str]:
    """ページごとのテキスト。PDF でなければ ValueError。"""
    try:
        reader = PdfReader(io.BytesIO(payload))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as e:  # pypdf raises several types
        msg = "payload is not a readable PDF"
        raise ValueError(msg) from e


_WAREKI = re.compile(r"平成(\d+)年")


def _fy_of_heading(text: str) -> int | None:
    """「当連結会計年度（自 2024年１月１日 …）」「（自 平成26年１月１日 …）」→ 事業年度。"""
    m = re.search(r"（自\s*(\d{4})年", text)
    if m:
        return int(m.group(1))
    m = _WAREKI.search(text)
    if m:
        return 1988 + int(m.group(1))
    return None


def parse(payload: bytes, fy: int) -> Parsed:
    """有報 PDF → long 行（`parse_pages` を参照）。"""
    return parse_pages(pdf_text(payload), fy)


def parse_pages(pages: list[str], fy: int) -> Parsed:
    """ページテキスト → long 行。当期・前期の両方を返す。表が見つからなければ ValueError。

    行: fy, doc_fy（この PDF の事業年度）, docid, table(segment/region), key, metric(sales/profit),
    value_mn_jpy, source。
    """
    if fy not in DOCS:
        msg = f"no docID registered for FY{fy}"
        raise ValueError(msg)
    text = "\n".join(pages)
    if "シマノ" not in text:
        msg = "PDF does not look like a Shimano filing"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    skipped: list[str] = []
    found_seg = found_reg = 0
    # Split the document into blocks headed by 前連結会計年度／当連結会計年度 and parse each block
    blocks = re.split(r"(?=(?:前|当)連結会計年度（自)", text)
    for block in blocks:
        head = block[:80]
        year = _fy_of_heading(head)
        if year is None:
            continue
        seg_line = re.search(r"外部顧客に対する売上高\s+(.+)", block)
        prof_line = re.search(r"セグメント利益(?:又は損失\(△\))?\s+(.+)", block)
        if seg_line and prof_line and "自転車部品" in block:
            sales = _nums(seg_line.group(1), 3)
            profit = _nums(prof_line.group(1), 3)
            if sales and profit:
                for seg, sv, pv in zip(SEGMENTS, sales, profit, strict=True):
                    rows.append(_row(year, fy, "segment", seg, "sales", sv))
                    rows.append(_row(year, fy, "segment", seg, "profit", pv))
                found_seg += 1
        reg = re.search(
            r"地域ごとの情報[\s\S]{0,400}?\(1\)\s*売上高[\s\S]*?\n((?:[\d,]+\s+){5}[\d,]+)", block
        )
        if reg:
            vals = _nums(reg.group(1), 6)
            if vals:
                for region, v in zip(REGIONS, vals[:5], strict=True):
                    rows.append(_row(year, fy, "region", region, "sales", v))
                rows.append(_row(year, fy, "region", "total", "sales", vals[5]))
                found_reg += 1
    if found_seg == 0 or found_reg == 0:
        msg = f"segment ({found_seg}) or region ({found_reg}) table not found in FY{fy} filing"
        raise ValueError(msg)
    # de-duplicate exact repeats (the same block can appear in 注記 twice)
    seen: set[tuple[object, ...]] = set()
    uniq: list[dict[str, object]] = []
    for r in rows:
        k = (r["fy"], r["table"], r["key"], r["metric"])
        if k in seen:
            if any(
                u["value_mn_jpy"] != r["value_mn_jpy"]
                for u in uniq
                if (u["fy"], u["table"], u["key"], u["metric"]) == k
            ):
                skipped.append(f"FY{fy} doc: conflicting values for {k}")
            continue
        seen.add(k)
        uniq.append(r)
    return Parsed(rows=uniq, skipped=skipped)


def _row(
    year: int, doc_fy: int, table: str, key: str, metric: str, value: int | None
) -> dict[str, object]:
    return {
        "fy": year,
        "doc_fy": doc_fy,
        "docid": DOCS[doc_fy],
        "table": table,
        "key": key,
        "metric": metric,
        "value_mn_jpy": value,
        "source": SOURCE,
    }


MART_KEY: tuple[str, ...] = ("fy", "table", "key", "metric")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    """同じ (fy, table, key, metric) が当期・前期の 2 本あるときは、その年の有報を採る。

    値が食い違えば `restated_next_year` に翌年の有報の値を残す。キー順ソート。"""
    by_key: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for r in staged:
        by_key.setdefault(tuple(r[c] for c in MART_KEY), []).append(r)
    out: list[dict[str, object]] = []
    for rs in by_key.values():
        own = [r for r in rs if r["doc_fy"] == r["fy"]]
        later = [r for r in rs if r["doc_fy"] != r["fy"]]
        chosen = own[0] if own else later[0]
        restated = None
        if own and later and later[0]["value_mn_jpy"] != own[0]["value_mn_jpy"]:
            restated = later[0]["value_mn_jpy"]
        out.append(
            {
                "iso3": "JPN",
                "company": "Shimano",
                "fy": chosen["fy"],
                "table": chosen["table"],
                "key": chosen["key"],
                "metric": chosen["metric"],
                "value_mn_jpy": chosen["value_mn_jpy"],
                "restated_next_year": restated,
                "docid": chosen["docid"],
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: tuple(str(r[c]) for c in MART_KEY))
    return out
