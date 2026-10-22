"""自動車・二輪の協会統計 xls → 年次 long 行（H6 対比）。3 ソースを 1 モジュールにまとめる。

- 全国軽自動車協会連合会（`zenkeijikyo`）: 軽四輪 新車販売 年別・車種別推移
  （`hanbai4-<年>kaku.xls`）と 軽二輪（126–250cc）・小型二輪（251cc–）新車販売 年別推移
  （`hanbai2-<年>.xls`）。1967 年〜。
- 日本自動車販売協会連合会（`jada`）: 登録車＋軽自動車 販売台数（月次・年計、2022 年〜）と
  新車車種別登録台数 年計（普通／小型乗用車など、5 年分）。URL は不透明 ID
  （ページから取得、manifest で固定）。
- 日本自動車輸入組合（`jaia`）: 車両本体価格帯別 輸入乗用車 新規登録台数（2003 年〜、
  固定名・上書き更新）。robots.txt は `Crawl-delay: 10`（1 ファイルのみ取得）。

xls は xlrd で読み、純粋変換 `parse_*_rows(rows)` はシート 0 の行リストを受ける
（テストはその JSON）。
利用規約の記載なし。出典明記で引用、raw 非コミット。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import xlrd

LICENSE_ZENKEI = "全国軽自動車協会連合会調べ（利用規約の記載なし。出典明記で引用、raw 非コミット、確認 2026-10-22）"  # noqa: E501
LICENSE_JADA = "日本自動車販売協会連合会調べ（利用規約の記載なし。出典明記で引用、raw 非コミット、確認 2026-10-22）"  # noqa: E501
LICENSE_JAIA = (
    "日本自動車輸入組合調べ（利用規約の記載なし、robots.txt Crawl-delay 10 を遵守。"
    "出典明記で引用、raw 非コミット、確認 2026-10-22）"
)
SOURCE_ZENKEI = "zenkeijikyo"
SOURCE_JADA = "jada"
SOURCE_JAIA = "jaia"

_ZK = "https://www.zenkeijikyo.or.jp/zenkei17/zen/wp-content/uploads/2026/01"
ZENKEI_DOCS: dict[str, str] = {
    "kei4": f"{_ZK}/hanbai4-2025kaku.xls",
    "moto2": f"{_ZK}/hanbai2-2025.xls",
}
JADA_DOCS: dict[str, str] = {
    "total": "https://www.jada.or.jp/files/libs/7735/202610051047554825.xls",
    "bytype": "https://www.jada.or.jp/files/libs/7344/202607011044295277.xls",
}
JAIA_DOCS: dict[str, str] = {
    "pricerange": "https://www.jaia-jp.org/cms/wp-content/uploads/stats_ja/PriceRange_year.xls",
}
XLS_MAGIC = b"\xd0\xcf\x11\xe0"


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


Rows = list[list[object]]


def xls_rows(payload: bytes, sheet: int = 0) -> Rows:
    try:
        sh = xlrd.open_workbook(file_contents=payload).sheets()[sheet]
    except Exception as e:
        msg = "payload is not a readable xls"
        raise ValueError(msg) from e
    return [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]


def _num(v: object) -> float | None:
    if isinstance(v, int | float) and not isinstance(v, bool):
        return float(v)
    return None


# ---- 全軽自協 ----------------------------------------------------------------------------------

_YY = re.compile(r"\((\d{2})\)")


def _zenkei_year(label: object) -> int | None:
    m = _YY.search(str(label))
    if not m:
        return None
    yy = int(m.group(1))
    return 1900 + yy if yy >= 67 else 2000 + yy


def parse_zenkei_rows(rows: Rows, key: str) -> Parsed:
    """kei4: (year, segment ∈ kei4_total / kei4_passenger_group, units)。
    moto2: (year, segment ∈ moto_126_250 / moto_gt250, units)。見出しが合わなければ ValueError。"""
    if key == "kei4":
        head = " ".join(str(c) for r in rows[:5] for c in r)
        if "軽四輪車新車販売台数" not in head or "乗用車群計" not in head:
            msg = "kei4: header not recognised"
            raise ValueError(msg)
        cols = {"kei4_total": 2, "kei4_passenger_group": 8}
        label_col = 1
    elif key == "moto2":
        head = " ".join(str(c) for r in rows[:6] for c in r)
        if "軽二輪車・小型二輪車" not in head:
            msg = "moto2: header not recognised"
            raise ValueError(msg)
        cols = {"moto_126_250": 1, "moto_gt250": 3}
        label_col = 0
    else:
        msg = f"unknown zenkei key {key}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for r in rows:
        if len(r) <= max(cols.values()):
            continue
        y = _zenkei_year(r[label_col])
        if y is None:
            continue
        for seg, c in cols.items():
            v = _num(r[c])
            if v is not None:
                out.append({"year": y, "segment": seg, "units": int(v), "source": SOURCE_ZENKEI})
    if not out:
        msg = f"{key}: no year rows"
        raise ValueError(msg)
    return Parsed(rows=out)


def parse_zenkei(payload: bytes, key: str) -> Parsed:
    return parse_zenkei_rows(xls_rows(payload), key)


# ---- 自販連 ------------------------------------------------------------------------------------

_JADA_TYPES = [
    ("普通乗用車", "standard_passenger"),
    ("小型乗用車", "small_passenger"),
    ("小計", "passenger_subtotal"),
    ("普通貨物車", "standard_truck"),
    ("小型貨物車", "small_truck"),
    ("小計", "truck_subtotal"),
    ("バス", "bus"),
    ("合計", "registered_total"),
]
_YEAR = re.compile(r"^(20\d\d)年$")


def parse_jada_rows(rows: Rows, key: str) -> Parsed:
    """total: 「1～12月」列の年計 → (year, segment=registered_plus_kei_total, units)。
    bytype: 年計シートの車種別 → (year, segment, units)。"""
    out: list[dict[str, object]] = []
    if key == "total":
        if "登録車＋軽自動車販売台数" not in str(rows[0][0]):
            msg = "total: header not recognised"
            raise ValueError(msg)
        col = None
        for r in rows:
            if str(r[0]) == "西暦":
                col = next((i for i, c in enumerate(r) if "1～12月" in str(c)), None)
                continue
            if col is None:
                continue
            m = _YEAR.match(str(r[0]).strip())
            v = _num(r[col]) if m else None
            if m and v is not None:
                out.append(
                    {
                        "year": int(m.group(1)),
                        "segment": "registered_plus_kei_total",
                        "units": int(v),
                        "source": SOURCE_JADA,
                    }
                )
    elif key == "bytype":
        if "新車車種別登録台数" not in str(rows[0][0]):
            msg = "bytype: header not recognised"
            raise ValueError(msg)
        header = next(
            (r for r in rows if _YEAR.match(str(r[2]).strip() if len(r) > 2 else "")), None
        )
        if header is None:
            msg = "bytype: year header not found"
            raise ValueError(msg)
        years = {
            i: int(str(c).strip()[:4]) for i, c in enumerate(header) if _YEAR.match(str(c).strip())
        }
        body = [
            r
            for r in rows
            if len(r) > 2 and re.sub(r"\s", "", str(r[1])) in {t for t, _ in _JADA_TYPES}
        ]
        labels = [re.sub(r"\s", "", str(r[1])) for r in body]
        if labels != [t for t, _ in _JADA_TYPES]:
            msg = f"bytype: row labels {labels} unexpected"
            raise ValueError(msg)
        for (_, seg), r in zip(_JADA_TYPES, body, strict=True):
            for i, y in years.items():
                v = _num(r[i])
                if v is not None:
                    out.append({"year": y, "segment": seg, "units": int(v), "source": SOURCE_JADA})
    else:
        msg = f"unknown jada key {key}"
        raise ValueError(msg)
    if not out:
        msg = f"{key}: no year rows"
        raise ValueError(msg)
    return Parsed(rows=out)


def parse_jada(payload: bytes, key: str) -> Parsed:
    return parse_jada_rows(xls_rows(payload), key)


# ---- JAIA --------------------------------------------------------------------------------------

JAIA_BANDS = [
    "ge_2000",
    "1000_1999",
    "900_999",
    "800_899",
    "700_799",
    "600_699",
    "500_599",
    "400_499",
    "300_399",
    "200_299",
    "le_199",
    "unknown",
    "total",
]


def parse_jaia_rows(rows: Rows, key: str = "pricerange") -> Parsed:
    """(year, band, units)。見出しの帯が `JAIA_BANDS` の順でなければ ValueError。合計を検算。"""
    if key != "pricerange":
        msg = f"unknown jaia key {key}"
        raise ValueError(msg)
    header = next((r for r in rows if "2,000以上" in [str(c) for c in r]), None)
    if header is None or "Total" not in [str(c) for c in header]:
        msg = "pricerange: band header not found"
        raise ValueError(msg)
    first = [str(c) for c in header].index("2,000以上")
    out: list[dict[str, object]] = []
    for r in rows:
        if len(r) <= first + 12 or str(r[2]) != "台数":
            continue
        m = _YEAR.match(str(r[1]).strip())
        if not m:
            continue
        vals = [_num(v) for v in r[first : first + 13]]
        if any(v is None for v in vals):
            continue
        ints = [int(v) for v in vals if v is not None]
        if sum(ints[:-1]) != ints[-1]:
            msg = f"pricerange {m.group(1)}: bands do not sum to total"
            raise ValueError(msg)
        for band, v in zip(JAIA_BANDS, ints, strict=True):
            out.append({"year": int(m.group(1)), "band": band, "units": v, "source": SOURCE_JAIA})
    if not out:
        msg = "pricerange: no year rows"
        raise ValueError(msg)
    return Parsed(rows=out)


def parse_jaia(payload: bytes, key: str) -> Parsed:
    return parse_jaia_rows(xls_rows(payload), key)


# ---- marts -------------------------------------------------------------------------------------


def _unique(
    rows: list[dict[str, object]], keys: tuple[str, ...], what: str
) -> list[dict[str, object]]:
    out = [{"iso3": "JPN", **r} for r in rows]
    out.sort(key=lambda r: tuple(str(r[k]) for k in keys))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in keys)
        if k in seen:
            msg = f"duplicate {what} key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out


def build_zenkei_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    return _unique(staged, ("year", "segment"), "zenkei")


def build_jada_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    return _unique(staged, ("year", "segment"), "jada")


def build_jaia_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = _unique(staged, ("year", "band"), "jaia")
    totals = {r["year"]: int(str(r["units"])) for r in rows if r["band"] == "total"}
    for r in rows:
        t = totals.get(r["year"])
        r["share"] = int(str(r["units"])) / t if t else None
    return rows


ParseFn = Callable[[bytes, str], Parsed]
