"""総務省 消費者物価指数（CPI）2025 年基準 品目別 長期時系列 CSV（e-Stat、appId 不要）→ long 行。

ファイル: 年平均 `zni2025a.csv`（1970–）と 月次 `zmi2025a.csv`（1970-01–）。CP932。
行 0 類・品目名、1 英語名、2 類・品目符号、3 含類総連番、4 ウエイト、5 ウエイト 1 万分比、
6 行目から期間 × 品目。
期間キーは `YYYYMM`（月次）または `YYYY  `（年、末尾空白 2 つ）。空セルは未収集。
対象品目は符号で選ぶ（列位置は基準改定で動く）: 自転車 0115（類）、自転車Ａ 7201、
自転車Ｂ 7202（2015-01–）、
軽乗用車 7105、小型乗用車 7106、普通乗用車Ａ 7113、普通乗用車Ｂ 7115、総合 0001。2025 年 = 100。
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

SOURCE = "estat_cpi"
LICENSE = (
    "政府標準利用規約（第2.0版）＝CC BY 4.0 互換。出典: 政府統計の総合窓口(e-Stat)、"
    "消費者物価指数（総務省）2025年基準 を加工（確認 2026-10-22）"
)
BASE = "https://www.e-stat.go.jp/stat-search/file-download"
FILES: dict[str, str] = {
    # key → statInfId（2025 年基準 品目別 長期時系列 全国）
    "annual": "000040482831",  # zni2025a.csv
    "monthly": "000040482945",  # zmi2025a.csv
}
ITEMS: dict[str, str] = {
    "0001": "all_items",
    "0115": "bicycles",
    "7201": "bicycle_a",
    "7202": "bicycle_b",
    "7105": "car_kei",
    "7106": "car_small",
    "7113": "car_standard_a",
    "7115": "car_standard_b",
}
BASE_YEAR = "2025=100"
HEADER_ROWS = 6


def url(key: str) -> str:
    return f"{BASE}?statInfId={FILES[key]}&fileKind=1"


def raw_name(key: str) -> str:
    return f"cpi_2025base_{key}.csv"


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


_MONTH = re.compile(r"^(\d{4})(\d{2})$")
_YEAR = re.compile(r"^(\d{4})\s*$")


def parse(payload: bytes, key: str) -> Parsed:
    """CSV → 行 (item_code, item, period(YYYY or YYYY-MM), freq(annual/monthly), year, month,
    value, base, source)。ヘッダ不一致・対象品目欠落は ValueError。"""
    if key not in FILES:
        msg = f"unknown CPI file key {key!r}"
        raise ValueError(msg)
    try:
        text = payload.decode("cp932")
    except UnicodeDecodeError as e:
        msg = "payload is not CP932 text (HTML error page?)"
        raise ValueError(msg) from e
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < HEADER_ROWS + 1 or not rows[0] or rows[0][0] != "類・品目":
        msg = f"unexpected header: {rows[0][:3] if rows else rows}"
        raise ValueError(msg)
    if not rows[2][0].startswith("類・品目符号"):
        msg = "item-code row (類・品目符号) not at line 3"
        raise ValueError(msg)
    codes = rows[2]
    col_of: dict[str, int] = {}
    for j, c in enumerate(codes):
        if c in ITEMS:
            col_of[c] = j
    missing = set(ITEMS) - set(col_of)
    if missing:
        msg = f"item codes missing from file: {sorted(missing)}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    skipped: list[str] = []
    for r in rows[HEADER_ROWS:]:
        if not r or not r[0].strip():
            continue
        head = r[0]
        m_month, m_year = _MONTH.match(head.strip()), _YEAR.match(head)
        if key == "monthly" and m_month:
            year, month = int(m_month.group(1)), int(m_month.group(2))
            period, freq = f"{year}-{month:02d}", "monthly"
        elif key == "annual" and m_year:
            year, month = int(m_year.group(1)), None
            period, freq = f"{year}", "annual"
        else:
            skipped.append(f"{key}: unrecognised period {head!r}")
            continue
        for code, j in col_of.items():
            cell = r[j].strip() if j < len(r) else ""
            if cell == "":
                continue
            try:
                value = float(cell)
            except ValueError as e:
                msg = f"non-numeric value {cell!r} for item {code} at {period}"
                raise ValueError(msg) from e
            out.append(
                {
                    "item_code": code,
                    "item": ITEMS[code],
                    "period": period,
                    "freq": freq,
                    "year": year,
                    "month": month,
                    "value": value,
                    "base": BASE_YEAR,
                    "source": SOURCE,
                }
            )
    return Parsed(rows=out, skipped=skipped)


MART_KEY: tuple[str, ...] = ("item_code", "freq", "period")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    out = [{"iso3": "JPN", **r} for r in staged]
    out.sort(key=lambda r: tuple(str(r[c]) for c in MART_KEY))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in MART_KEY)
        if k in seen:
            msg = f"duplicate cpi key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out
