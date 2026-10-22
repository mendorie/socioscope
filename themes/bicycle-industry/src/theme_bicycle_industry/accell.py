"""Accell Group N.V.（欧州 e-bike メーカー、2022 年に非上場化）年報 PDF → グループ売上（€m）。

本体サイトに年報は残っておらず、Wayback Machine の完全なキャプチャ
（`web.archive.org/web/<ts>id_/<URL>`、`id_` は原本のまま返すフラグ）を使う。
2017 年報（EN）の 8 年表（2010–2017）と 2021 年報（EN）の 5 年表（2017–2021）で
2010–2021 のグループ売上を得る。重なる 2017 年は 2017 年報（小数 1 桁）を優先。
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from pypdf import PdfReader

SOURCE = "accell_ar"
LICENSE = (
    "Accell Group N.V. 年次報告書（公開開示、著作権は会社）。"
    "Internet Archive Wayback Machine 経由。"
    "引用・研究目的で出典表示、raw 非コミット（確認 2026-10-22）"
)
DOCS: dict[int, tuple[str, str]] = {
    2017: (
        "20181112021717",
        "http://annualreport2017.accell-group.com/docs/Accell_AR_2017/pdfs/"
        "Accell%20Group%20Jaarverslag%202017%20EN%20Full%20version.pdf",
    ),
    2021: (
        "20240104114552",
        "https://annualreport2021.accell-group.com/docs/Accell_AR_2021/"
        "Accell_Group_Annual_Report_2021.pdf",
    ),
}


def url(report_year: int) -> str:
    ts, original = DOCS[report_year]
    return f"https://web.archive.org/web/{ts}id_/{original}"


def raw_name(report_year: int) -> str:
    return f"accell_annual_report_{report_year}.pdf"


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


# 2017 年報: 'Net turnover 1,068.5 1,048.2 986.4 882.4 849.0 772.5 628.5 577.2'（2017 → 2010）
_T2017 = re.compile(r"^Net turnover((?:\s+[\d,]+\.\d){8})\s*$", re.M)
# 2021 年報: 'Net turnover 1,069 1,094 1,111 1,296 1,377 in millions of euro'（2017 → 2021）
_T2021 = re.compile(r"^Net turnover((?:\s+[\d,]{3,5}){5}) in millions of euro", re.M)


def parse(payload: bytes, report_year: int) -> Parsed:
    return parse_pages(pdf_text(payload), report_year)


def parse_pages(pages: list[str], report_year: int) -> Parsed:
    """ページテキスト → long 行 (year, report_year, metric=net_turnover, value_eur_m, source)。
    表が見つからなければ ValueError（fail-closed）。"""
    if report_year not in DOCS:
        msg = f"no document registered for {report_year}"
        raise ValueError(msg)
    text = "\n".join(pages)
    if "Accell" not in text:
        msg = "PDF does not look like an Accell annual report"
        raise ValueError(msg)
    if report_year == 2017:
        m = _T2017.search(text)
        years = range(2017, 2009, -1)
    else:
        m = _T2021.search(text)
        years = range(2017, 2022)
    if not m:
        msg = f"{report_year}: net turnover multi-year table not found"
        raise ValueError(msg)
    vals = [float(v.replace(",", "")) for v in m.group(1).split()]
    rows: list[dict[str, object]] = [
        {
            "year": y,
            "report_year": report_year,
            "metric": "net_turnover",
            "value_eur_m": v,
            "source": SOURCE,
        }
        for y, v in zip(years, vals, strict=True)
    ]
    return Parsed(rows=rows)


MART_KEY: tuple[str, ...] = ("year", "metric")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    """year で一意化。重なる年は古い年報を優先し、新しい年報の値を `restated_later` に残す。"""
    by: dict[tuple[int, str], dict[str, object]] = {}
    for r in sorted(staged, key=lambda r: int(str(r["report_year"]))):
        k = (int(str(r["year"])), str(r["metric"]))
        if k in by:
            by[k]["restated_later"] = r["value_eur_m"]
            continue
        by[k] = {**r, "restated_later": None}
    return [{"iso3": "NLD", "company": "Accell", **r} for _, r in sorted(by.items())]
