"""自転車産業振興協会（JBPI）統計 PDF → 国内向自転車生産輸入統計（車種別・年）と
POS 販売統計（車種別・月）。

1. 国内向自転車生産輸入統計 12 月分（`DOMESTIC_DOCS`: 版の最終年 → URL。各版に 3 年分）。
   生産動態統計（国内生産）と貿易統計（輸入、CIF）の合算で、品目は 軽快車（生産／輸入）、
   マウンテンバイク（MTB・クロスバイク、輸入）、ミニサイクル、幼児車、子供車、
   その他（**スポーツ車・外装変速機付軽快車**、輸入）、電動アシスト車（生産）、その他（生産）。
   「スポーツ車」の単独行は 2025 年までの表に無い。
2. POS 販売統計 年間総括（`POS_DOCS`: 年 → URL）。2024 年 7 月開始、11 社約 2,300 店、税込。
   分類は 軽快車／スポーツ車／幼児車／子ども車／電動アシスト自転車／その他自転車（6 分類）。

利用規約の記載なし。出典「(一財)自転車産業振興協会」を明記して引用、raw 非コミット。
URL は percent-encode して取る。
"""

from __future__ import annotations

import io
import re
import urllib.parse
from dataclasses import dataclass, field

from pypdf import PdfReader

SOURCE_DOMESTIC = "jbpi_domestic"
SOURCE_POS = "jbpi_pos"
LICENSE = (
    "（一財）自転車産業振興協会の公表統計（利用規約の記載なし）。"
    "出典明記で引用、raw 非コミット（確認 2026-10-22）"
)
_UP = "https://jbpi.or.jp/wp-content/uploads"
DOMESTIC_DOCS: dict[int, str] = {
    2023: f"{_UP}/2024/02/2021-2023国内向自転車生産輸入統計12月分.pdf",
    2024: f"{_UP}/2025/02/2022-2024国内向自転車生産輸入統計12月分.pdf",
    2025: f"{_UP}/2026/02/2023-2025国内向自転車生産輸入統計12月分.pdf",
}
POS_DOCS: dict[int, str] = {
    2025: f"{_UP}/2026/04/POS販売統計2025年年間総括.pdf",
}


def domestic_url(edition: int) -> str:
    return urllib.parse.quote(DOMESTIC_DOCS[edition], safe=":/")


def domestic_raw_name(edition: int) -> str:
    return f"jbpi_domestic_{edition - 2}_{edition}_dec.pdf"


def pos_url(year: int) -> str:
    return urllib.parse.quote(POS_DOCS[year], safe=":/")


def pos_raw_name(year: int) -> str:
    return f"jbpi_pos_annual_{year}.pdf"


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


# ---- 国内向自転車生産輸入統計 ------------------------------------------------------------

# 表の行順（ラベル → (category, flow)）。「軽快車」「その他」は 2 回出るので順番で割り当てる
_DOMESTIC_ORDER: list[tuple[str, str, str]] = [
    ("完成自転車 合計", "total", "production"),
    ("軽快車", "light", "production"),
    ("軽快車", "light", "import"),
    ("マウンテンバイク", "mtb_cross", "import"),
    ("ミニサイクル", "mini", "import"),
    ("幼児車", "infant", "import"),
    ("子供車", "kids", "import"),
    ("その他", "other_sports_geared", "import"),
    ("電動アシスト車", "eassist", "production"),
    ("その他", "other", "production"),
]
_LABEL = (
    r"(完成自転車\s*合計|軽快車|マウンテンバイク|ミニサイクル|幼児車|子供車|その他|電動アシスト車)"
)
_ROW = re.compile(_LABEL + r"\s+((?:[\d,]+\s+){5}[\d,]+)")
_YEARS = re.compile(r"(20\d\d)年\s+(20\d\d)年\s+(20\d\d)年1月-12月\s*累計")


def parse_domestic(payload: bytes, edition: int) -> Parsed:
    return parse_domestic_pages(pdf_text(payload), edition)


def parse_domestic_pages(pages: list[str], edition: int) -> Parsed:
    """→ long 行 (year, edition, category, flow, qty, value_k_jpy, source)。3 年 × 10 行。
    年の見出しが版と合わない・行が足りない・合計が合わないときは ValueError。"""
    if edition not in DOMESTIC_DOCS:
        msg = f"no document registered for edition {edition}"
        raise ValueError(msg)
    text = re.sub(r"\s+", " ", "\n".join(pages))
    if "国内向自転車流通" not in text:
        msg = "PDF does not look like a JBPI domestic statistics sheet"
        raise ValueError(msg)
    ym = _YEARS.search(text)
    if not ym or int(ym.group(3)) != edition:
        msg = f"edition {edition}: year header not found or mismatched"
        raise ValueError(msg)
    years = [int(ym.group(i)) for i in (1, 2, 3)]
    matches = _ROW.findall(text)
    labels = [re.sub(r"\s+", " ", m[0]) for m in matches]
    expected = [lab for lab, _, _ in _DOMESTIC_ORDER]
    if labels[: len(expected)] != expected:
        msg = f"edition {edition}: row labels {labels} != {expected}"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for (_, category, flow), (_, nums) in zip(_DOMESTIC_ORDER, matches, strict=False):
        vals = [int(v.replace(",", "")) for v in nums.split()]
        for i, year in enumerate(years):
            rows.append(
                {
                    "year": year,
                    "edition": edition,
                    "category": category,
                    "flow": flow,
                    "qty": vals[2 * i],
                    "value_k_jpy": vals[2 * i + 1],
                    "source": SOURCE_DOMESTIC,
                }
            )
    # 合計 = 生産の品目合計（軽快車 ＋ 電動アシスト車 ＋ その他）で検算
    for year in years:
        by = {r["category"]: r for r in rows if r["year"] == year and r["flow"] == "production"}
        parts = sum(int(str(by[c]["qty"])) for c in ("light", "eassist", "other"))
        if parts != int(str(by["total"]["qty"])):
            msg = f"edition {edition} {year}: production total {by['total']['qty']} != {parts}"
            raise ValueError(msg)
    return Parsed(rows=rows)


DOMESTIC_MART_KEY: tuple[str, ...] = ("year", "category", "flow")


def build_domestic_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    """(year, category, flow) で一意化。重なる年は新しい版を採り、古い版と違えば旧値を残す。
    単価 unit_price_jpy = 金額（千円）× 1000 ÷ 台数。"""
    by: dict[tuple[int, str, str], dict[str, object]] = {}
    for r in sorted(staged, key=lambda r: int(str(r["edition"]))):
        k = (int(str(r["year"])), str(r["category"]), str(r["flow"]))
        prev = by.get(k)
        row = {**r, "restated_from": None}
        if prev is not None and prev["qty"] != r["qty"]:
            row["restated_from"] = prev["qty"]
        by[k] = row
    out = []
    for _, r in sorted(by.items()):
        qty = int(str(r["qty"]))
        price = int(str(r["value_k_jpy"])) * 1000 / qty if qty else None
        out.append({"iso3": "JPN", **r, "unit_price_jpy": price})
    return out


# ---- POS 販売統計 ------------------------------------------------------------------------

# 行は 合計／その他／電動アシスト／子ども車／幼児車／スポーツ車／軽快車 の順に
# (金額, 数量) が並び、末尾が「N月」
_POS_CATS = ["total", "other", "eassist", "kids", "infant", "sports", "light"]
_POS_ROW = re.compile(r"((?:[\d,]+\s+){14})(\d{1,2})月")
_POS_YEAR = re.compile(r"(20\d\d)年\s*$", re.M)


def parse_pos(payload: bytes, year: int) -> Parsed:
    return parse_pos_pages(pdf_text(payload), year)


def parse_pos_pages(pages: list[str], year: int) -> Parsed:
    """年間総括の時系列表（当年 ＋ 前年 7–12 月）→ long 行
    (period, year, month, category, qty, value_jpy, source)。合計 = 6 分類の和で検算。"""
    if year not in POS_DOCS:
        msg = f"no document registered for {year}"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for page in pages:
        if "POS販売統計時系列表" not in page:
            continue
        ym = re.search(r"\n(20\d\d)年\n", page)
        if not ym:
            continue
        py = int(ym.group(1))
        for m in _POS_ROW.finditer(page):
            vals = [int(v.replace(",", "")) for v in m.group(1).split()]
            month = int(m.group(2))
            amounts, qtys = vals[0::2], vals[1::2]
            # 金額は税込の端数処理で数円ずれることがある
            if sum(qtys[1:]) != qtys[0] or abs(sum(amounts[1:]) - amounts[0]) > 10:
                msg = f"POS {py}-{month:02d}: category sum != total"
                raise ValueError(msg)
            for cat, q, a in zip(_POS_CATS, qtys, amounts, strict=True):
                rows.append(
                    {
                        "period": f"{py}-{month:02d}",
                        "year": py,
                        "month": month,
                        "category": cat,
                        "qty": q,
                        "value_jpy": a,
                        "source": SOURCE_POS,
                    }
                )
    if not any(r["year"] == year for r in rows):
        msg = f"POS {year}: time-series table not found"
        raise ValueError(msg)
    return Parsed(rows=rows)


POS_MART_KEY: tuple[str, ...] = ("period", "category")


def build_pos_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    seen: set[tuple[object, ...]] = set()
    for r in sorted(staged, key=lambda r: (str(r["period"]), str(r["category"]))):
        k = tuple(r[c] for c in POS_MART_KEY)
        if k in seen:
            msg = f"duplicate pos key {k}"
            raise ValueError(msg)
        seen.add(k)
        qty = int(str(r["qty"]))
        out.append(
            {"iso3": "JPN", **r, "avg_price_jpy": int(str(r["value_jpy"])) / qty if qty else None}
        )
    return out
