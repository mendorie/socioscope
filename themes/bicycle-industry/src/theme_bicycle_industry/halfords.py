"""Halfords Group plc（英国小売、HFD.L）通期決算発表 PDF → Retail 売上と Cycling 売上（£m）。

`www.halfordscompany.com/investor-hub/results-reports-and-presentations/`（robots: `/` 許可）に
静的リンクされた Preliminary Results の PDF（FY2015–FY2026、FY は 3 月末／4 月初）。
Cycling は FY2025 以降 £m で開示、FY2015–FY2024 は Retail 売上 × Cycling 構成比（%、小数 1 桁）で
導出する（`derived` 列）。
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from pypdf import PdfReader

SOURCE = "halfords_ir"
LICENSE = (
    "Halfords Group plc 決算発表（RNS、公開開示、著作権は会社）。"
    "引用・研究目的で出典表示、raw 非コミット（確認 2026-10-22）"
)
BASE = "https://www.halfordscompany.com"
INDEX_PAGE = f"{BASE}/investor-hub/results-reports-and-presentations/"
DOCS: dict[int, str] = {
    2015: "/media/p2xghc3p/fy15-preliminary-results.pdf",
    2016: "/media/e5nfrllj/prelims-rns-fy16-final.pdf",
    2017: "/media/negl1i1y/halfords-preliminary-results-for-ye-31-march-2017.pdf",
    2018: "/media/q05nodda/halfords-group-plc-fy18-preliminary-results.pdf",
    2019: "/media/qi2d02ea/prelims-rns-fy19-final-210519.pdf",
    2020: "/media/xp2hegm5/halfords-fy20-full-year-preliminary-results-announcement.pdf",
    2021: "/media/avjla0fx/halfords-group-plc-fy21-preliminary-results.pdf",
    2022: "/media/zuda0zzw/halfords-group-plc-fy22-prelims-results-announcement.pdf",
    2023: "/media/sbel0k52/halfords-group-plc-fy23-preliminary-results-announcement.pdf",
    2024: "/media/5zdpst5b/halfords-prelim-results-fy24-final.pdf",
    2025: "/media/eyyo1dgx/halfords-fy25-results_250625_vf-1.pdf",
    2026: "/media/j0zb4xsh/fy26-rns_vfinal.pdf",
}
# FY2015・2020・2026 は 53 週。Retail 行の最初の列（53 週）ではなく 52 週ベースを使う年
WEEK53 = {2015, 2020, 2026}


def url(fy: int) -> str:
    return BASE + DOCS[fy]


def raw_name(fy: int) -> str:
    return f"halfords_prelims_fy{fy}.pdf"


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


def pdf_text(payload: bytes) -> list[str]:
    try:
        reader = PdfReader(io.BytesIO(payload))
        return [p.extract_text() or "" for p in reader.pages]
    except Exception as e:
        msg = "payload is not a readable PDF"
        raise ValueError(msg) from e


_N = r"([\d,]+\.\d)"
_RETAIL = re.compile(rf"^\s*Retail(?: Revenue)?\s+{_N}\s+{_N}(?:\s+{_N})?\s", re.M)
# FY2025/26: Retail 節の 'Revenue a b x%' の直後に '- Motoring' が続く
_RETAIL_SEG = re.compile(rf"^\s*Revenue\s+{_N}\s+{_N}\s+[\d.]+%\d?\s*\n\s*-\s*Motoring", re.M)
# 構成比表: 'Cycling <LFL 1〜2 列> <mix 当期> <mix 前期> [<mix 前々期>]'
_MIX = re.compile(
    r"^\s*Cycling\s+(?:(?:[+(-][\d.]+%?\)?|[\d.]+%)\s+){1,2}(\d{2}\.\d)\s+(\d{2}\.\d)(?:\s+\d{2}\.\d)?\s*$",
    re.M,
)
# FY2015–2017: 'Cycling <mix 当期> <mix 前期> [<LFL>]'
_MIX_EARLY = re.compile(r"^\s*Cycling\s+(\d{2}\.\d)\s+(\d{2}\.\d)(?:\s+[+-][\d.]+)?\s*$", re.M)
_CYC_GBP = re.compile(rf"^-\s*Cycling\s+{_N}\s+{_N}\s+[\d.]+%", re.M)


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def parse(payload: bytes, fy: int) -> Parsed:
    return parse_pages(pdf_text(payload), fy)


def parse_pages(pages: list[str], fy: int) -> Parsed:
    """ページテキスト → long 行 (fy, doc_fy, metric, value, unit, derived, source)。

    metric: retail_revenue（£m、52 週）, cycling_mix（% of Retail revenue）, cycling_revenue（£m）。
    FY2025 以降は cycling_revenue を開示値から、それ以前は retail_revenue × cycling_mix / 100 で導出
    （derived=True）。当期のみ。
    どれも取れなければ ValueError（fail-closed）。
    """
    if fy not in DOCS:
        msg = f"no document registered for FY{fy}"
        raise ValueError(msg)
    text = "\n".join(pages)
    if "Halfords" not in text:
        msg = "PDF does not look like a Halfords release"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []

    def put(year: int, metric: str, value: float, unit: str, derived: bool) -> None:
        rows.append(
            {
                "fy": year,
                "doc_fy": fy,
                "metric": metric,
                "value": value,
                "unit": unit,
                "derived": derived,
                "source": SOURCE,
            }
        )

    if fy >= 2025:
        ms = _RETAIL_SEG.search(text)
        mc = _CYC_GBP.search(text)
        if not ms or not mc:
            msg = f"FY{fy}: Retail or Cycling £m line not found"
            raise ValueError(msg)
        put(fy, "retail_revenue", _f(ms.group(1)), "GBP_m", False)
        put(fy, "cycling_revenue", _f(mc.group(1)), "GBP_m", False)
        return Parsed(rows=rows)

    m = _RETAIL.search(text)
    if not m:
        msg = f"FY{fy}: Retail revenue line not found"
        raise ValueError(msg)
    # 53 週年は (53wk, 52wk, prior) の 3 列、その他は (current, prior)
    retail = _f(m.group(2)) if fy in WEEK53 and m.group(3) else _f(m.group(1))
    put(fy, "retail_revenue", retail, "GBP_m", False)
    mm = _MIX_EARLY.search(text) if fy <= 2017 else _MIX.search(text)
    if not mm:
        msg = f"FY{fy}: Cycling mix line not found"
        raise ValueError(msg)
    mix = float(mm.group(1))
    put(fy, "cycling_mix", mix, "pct_of_retail", False)
    put(fy, "cycling_revenue", round(retail * mix / 100, 1), "GBP_m", True)
    return Parsed(rows=rows)


MART_KEY: tuple[str, ...] = ("fy", "metric")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    out = [{"iso3": "GBR", "company": "Halfords", **r} for r in staged]
    out.sort(key=lambda r: (int(str(r["fy"])), str(r["metric"])))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in MART_KEY)
        if k in seen:
            msg = f"duplicate halfords key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out
