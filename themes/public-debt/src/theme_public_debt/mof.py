"""財務省「国債等の保有者別内訳」PDF（1 ページ、最新時点のみ。出所は日本銀行「資金循環統計」）。

Pure transforms only (no I/O). PDF は AES 暗号化だが空パスワードで開ける（pypdf）。テキストは
「国債（合計 N 億円）」「国庫短期証券（T-Bill）」「国債及び国庫短期証券」の 3 ブロックと、
保有者ごとに「名前 / 金額（億円）/ 比率（%）」の 3 行が並ぶ。本テーマで使うのは**国債（T-Bill を
除く、財投債を含む）**の 日本銀行 の比率で、H13（日銀を除いた市中保有）の近似に使う。

保有者の 1 つ目のブロック（国債）は「一般政府（除く公的年金）」で始まり「その他」で終わる。
2 つ目（T-Bill）は再び「一般政府」で始まる。合計の検算（各保有者の金額の和 ≒ 合計、±0.5%）に
失敗したら ValueError（fail-closed）。

License: 政府標準利用規約（第 2.0 版、CC BY 4.0 互換）。出典「財務省「国債等の保有者別内訳」
（日本銀行「資金循環統計」より作成）」。
"""

from __future__ import annotations

import io
import re

SOURCE = "mof_holdings"
LICENSE = (
    "政府標準利用規約 第 2.0 版 (CC BY 4.0 compatible; 財務省「国債等の保有者別内訳」, "
    "source 日本銀行「資金循環統計」)"
)
URL = "https://www.mof.go.jp/jgbs/reference/appendix/holdings01.pdf"
RAW_NAME = "holdings01.pdf"
MAGIC = b"%PDF"
STAGED_TABLE = "staged/mof/jgb_holders"
MART_TABLE = "marts/mof_jgb_holders"

HOLDERS: tuple[str, ...] = (
    "一般政府（除く公的年金）",
    "日本銀行",
    "銀行等",
    "生損保等",
    "公的年金",
    "年金基金",
    "海外",
    "家計",
    "その他",
    "財政融資資金",
)
_ERA = {"令和": 2018, "平成": 1988}
_ASOF = re.compile(r"（(令和|平成)\s*(\d+|元)\s*年\s*(\d+)\s*月末")
_TOTAL = re.compile(r"合計\s*([\d,]+)兆\s*([\d,]+)億円")
_AMOUNT = re.compile(r"^[\d,]+$")
_SHARE = re.compile(r"^(\d+(?:\.\d+)?)%$")


def pdf_pages(payload: bytes) -> list[str]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(payload))
        if reader.is_encrypted:
            reader.decrypt("")
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        msg = "mof: payload is not a readable PDF"
        raise ValueError(msg) from e


def _asof(text: str) -> tuple[int, int]:
    m = _ASOF.search(text)
    if not m:
        msg = "mof: as-of date (令和 N 年 M 月末) not found"
        raise ValueError(msg)
    y = 1 if m.group(2) == "元" else int(m.group(2))
    return _ERA[m.group(1)] + y, int(m.group(3))


def _total_oku(text: str) -> float:
    """「国債\\n合計 1,006兆5,235億円」の最初の合計（国債、T-Bill を除く）を億円で。"""
    m = _TOTAL.search(text)
    if not m:
        msg = "mof: total (合計 N兆M億円) not found"
        raise ValueError(msg)
    return float(m.group(1).replace(",", "")) * 10_000 + float(m.group(2).replace(",", ""))


def parse(pages: list[str]) -> list[dict[str, object]]:
    """→ [{asof_year, asof_month, instrument='jgb', holder, amount_oku_yen, share_pct, source}]
    for the first (国債, excl. T-Bill) holder block. Shares and amounts are checked against the
    block total."""
    if not pages:
        msg = "mof: PDF has no page"
        raise ValueError(msg)
    text = pages[0]
    year, month = _asof(text)
    total = _total_oku(text)
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines: list[str] = []
    for ln in raw_lines:  # pypdf splits 「一般政府」「（除く公的年金）」 over two lines
        if ln.startswith("（除く") and lines and lines[-1].replace(" ", "") == "一般政府":
            lines[-1] = "一般政府" + ln
        else:
            lines.append(ln)
    rows: list[dict[str, object]] = []
    i = 0
    started = False
    while i < len(lines) - 2:
        name = lines[i].replace(" ", "")
        if name in HOLDERS and _AMOUNT.match(lines[i + 1].replace(" ", "")):
            m = _SHARE.match(lines[i + 2].replace(" ", ""))
            if m:
                if started and name == HOLDERS[0]:
                    break  # second block (T-Bill) starts
                started = True
                rows.append(
                    {
                        "asof_year": year,
                        "asof_month": month,
                        "instrument": "jgb",
                        "holder": name,
                        "amount_oku_yen": float(lines[i + 1].replace(",", "").replace(" ", "")),
                        "share_pct": float(m.group(1)),
                        "source": SOURCE,
                    }
                )
                i += 3
                continue
        i += 1
    if not rows or not any(r["holder"] == "日本銀行" for r in rows):
        msg = "mof: holder block (with 日本銀行) not found"
        raise ValueError(msg)
    amount_sum = sum(float(str(r["amount_oku_yen"])) for r in rows)
    share_sum = sum(float(str(r["share_pct"])) for r in rows)
    if abs(amount_sum / total - 1.0) > 0.005 or abs(share_sum - 100.0) > 0.5:
        msg = (
            f"mof: holders do not add up (amount {amount_sum:.0f} vs total {total:.0f}, "
            f"shares {share_sum:.1f}%)"
        )
        raise ValueError(msg)
    return rows


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    """→ long panel rows for Japan: unit=jgb_holders, metric=share_<holder key>, value %, plus
    metric=boj_share_pct (same value as 日本銀行) for the H13 computation. year = as-of year."""
    keys = {
        "一般政府（除く公的年金）": "general_gov_ex_pension",
        "日本銀行": "boj",
        "銀行等": "banks",
        "生損保等": "insurers",
        "公的年金": "public_pension",
        "年金基金": "pension_funds",
        "海外": "foreign",
        "家計": "households",
        "その他": "other",
        "財政融資資金": "filp",
    }
    out: list[dict[str, object]] = []
    for r in staged:
        out.append(
            {
                "iso3": "JPN",
                "year": int(str(r["asof_year"])),
                "unit": "jgb_holders",
                "metric": f"share_{keys[str(r['holder'])]}",
                "value": r["share_pct"],
                "source": SOURCE,
            }
        )
    out.sort(key=lambda x: (int(str(x["year"])), str(x["metric"])))
    return out
