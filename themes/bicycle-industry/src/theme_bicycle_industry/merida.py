"""Merida（美利達、9914.TW）連結財務報告 PDF（Q4＝通期）→ Specialized 持分法・関連当事者売上。

自社 IR ページ（`INVESTOR_PAGE`、robots 許可）からリンクされた `merida-cdn.m-c-g.net` の PDF を
取る（CDN の robots.txt は全面 Disallow だが ADR 0006 の例外: 公開開示文書・開示主体のページから
直接リンク・少数・低頻度）。各報告は当期と前期を載せるので FY2022–2025 を 3 本で得る。

抽出（NT$ 千）:
- 營業收入淨額（損益表 4000 行、当期・前期）
- 採用權益法認列之關聯企業損益之份額（損益表 7370/7770 行、当期・前期。
  SBC を含む関連企業全体の持分）
- 採用權益法之投資 注記の SBC（Specialized Bicycle Components Holding Company, Inc.）
  帳簿価額（期末・前期末）
- 採用權益法之投資 注記の関連企業合計（帳簿価額、期末・前期末。SBC の比重の確認用）
- 關係人交易の「SBC 集團」への売上（当期・前期。最初に現れる 2 値の行＝銷貨）
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from pypdf import PdfReader

SOURCE = "merida_ir"
LICENSE = (
    "Merida Industry 連結財務報告（公開開示、著作権は会社）。"
    "自社 IR ページからのリンクを ADR 0006 の例外で取得。"
    "引用・研究目的で利用、raw 非コミット（確認 2026-10-22）"
)
BASE = "https://merida-cdn.m-c-g.net/merida-v2/media-raw/countries/zh-tw/financial-report"
# 事業年度 → ファイル名（通期の連結財務報告）
DOCS: dict[int, str] = {
    2023: "112q4.pdf",
    2024: "2024he-bing-cai-bao.pdf",
    2025: "merida114q4-fsc.pdf",
}
INVESTOR_PAGE = (
    "https://www.merida-bikes.com/zh-tw/p/tou-zi-ren-zi-xuninvestors/tou-zi-ren-zi-xun-352.html"
)


def url(fy: int) -> str:
    return f"{BASE}/{DOCS[fy]}?p1"


def raw_name(fy: int) -> str:
    return f"merida_consolidated_fy{fy}_q4.pdf"


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


_NUM = r"(\(\s*)?\$?\s*([\d,]+)\s*(\))?"


def _vals(text: str, n: int) -> list[int] | None:
    """テキスト先頭から n 個の金額を読む。括弧は負。パーセント列（1〜2 桁）は飛ばす。"""
    out: list[int] = []
    for m in re.finditer(_NUM, text):
        digits = m.group(2)
        if "," not in digits and len(digits) <= 3:
            continue  # 構成比 % 列や単独の小さな数
        v = int(digits.replace(",", ""))
        if m.group(1) and m.group(3):
            v = -v
        out.append(v)
        if len(out) == n:
            return out
    return None


def pdf_text(payload: bytes) -> list[str]:
    try:
        reader = PdfReader(io.BytesIO(payload))
        return [p.extract_text() or "" for p in reader.pages]
    except Exception as e:
        msg = "payload is not a readable PDF"
        raise ValueError(msg) from e


METRICS = (
    "revenue",
    "equity_method_share",
    "sbc_carrying_amount",
    "associates_carrying_total",
    "sbc_group_sales",
)


def _flat(pages: list[str]) -> str:
    return re.sub(r"\s+", " ", "\n".join(pages))


def parse(payload: bytes, fy: int) -> Parsed:
    return parse_pages(pdf_text(payload), fy)


def parse_pages(pages: list[str], fy: int) -> Parsed:
    """ページテキスト → long 行 (fy, doc_fy, metric, value_ntd_k, source)。当期と前期。

    metric: `METRICS`（revenue / equity_method_share / sbc_carrying_amount /
    associates_carrying_total / sbc_group_sales）。
    どれか 1 つでも見つからなければ ValueError（fail-closed）。
    """
    if fy not in DOCS:
        msg = f"no document registered for FY{fy}"
        raise ValueError(msg)
    text = _flat(pages)
    if "美利達" not in text:
        msg = "PDF does not look like a Merida filing"
        raise ValueError(msg)
    found: dict[str, list[int]] = {}
    m = re.search(r"4000 營業收入淨額[^$]*?(\$.{0,80})", text)
    if m:
        v = _vals(m.group(1), 2)
        if v:
            found["revenue"] = v
    m = re.search(r"7[37]70 採用權益法認列之關聯\s*企業損益之份額\s*（[^）]*）\s*(.{0,80})", text)
    if m:
        v = _vals(m.group(1), 2)
        if v:
            found["equity_method_share"] = v
    m = re.search(r"Inc\.（SBC）\s*(\$.{0,60})", text)
    if m:
        v = _vals(m.group(1), 2)
        if v:
            found["sbc_carrying_amount"] = v
    m = re.search(r"（SBC）.{0,900}?(\$\s*[\d,]+\s*\$\s*[\d,]+)\s*合 ?併 ?公 ?司 ?對 ?關 ?聯", text)
    if m:
        v = _vals(m.group(1), 2)
        if v:
            found["associates_carrying_total"] = v
    m = re.search(r"SBC 集團\s*(\$\s*[\d,]+\s*\$\s*[\d,]+)", text)
    if m:
        v = _vals(m.group(1), 2)
        if v and min(v) > 1_000_000:  # 銷貨（NT$ 十億規模）。小さい行（応収・費用）なら様式違い
            found["sbc_group_sales"] = v
    missing = set(METRICS) - set(found)
    if missing:
        msg = f"items not found in FY{fy} filing: {sorted(missing)}"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for metric, (cur, prev) in found.items():
        for year, val in ((fy, cur), (fy - 1, prev)):
            rows.append(
                {"fy": year, "doc_fy": fy, "metric": metric, "value_ntd_k": val, "source": SOURCE}
            )
    return Parsed(rows=rows)


MART_KEY: tuple[str, ...] = ("fy", "metric")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    """同じ (fy, metric) が 2 本あれば doc_fy == fy の報告を採り、翌年と違えば restated に残す。"""
    by: dict[tuple[object, object], list[dict[str, object]]] = {}
    for r in staged:
        by.setdefault((r["fy"], r["metric"]), []).append(r)
    out: list[dict[str, object]] = []
    for (fy, metric), rs in by.items():
        own = [r for r in rs if r["doc_fy"] == r["fy"]]
        later = [r for r in rs if r["doc_fy"] != r["fy"]]
        chosen = own[0] if own else later[0]
        restated = None
        if own and later and later[0]["value_ntd_k"] != own[0]["value_ntd_k"]:
            restated = later[0]["value_ntd_k"]
        out.append(
            {
                "iso3": "TWN",
                "company": "Merida",
                "fy": fy,
                "metric": metric,
                "value_ntd_k": chosen["value_ntd_k"],
                "restated_next_year": restated,
                "doc_fy": chosen["doc_fy"],
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: tuple(str(r[c]) for c in MART_KEY))
    return out
