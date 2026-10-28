"""World Bank WDI v2 API: GDP（現地通貨、名目）`NY.GDP.MKTP.CN`。

議会予算（IPU、現地通貨）の対 GDP 比に使う。Pure transforms only (no I/O). growth-fertility の
`worldbank.py` と同じ URL 規約だが、テーマ間 import はしない（ADR 0001）ので必要な部分だけを複製。
1 指標 1 リクエスト（全経済体 × 2005–2025 年、
約 5,600 点、1 ページ）。ページが分かれたら ValueError（fail-closed）。

License: CC BY 4.0 (https://datacatalog.worldbank.org/public-licenses).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, ValidationError

SOURCE = "worldbank_wdi"
LICENSE = "CC BY 4.0 (World Bank WDI, https://datacatalog.worldbank.org/public-licenses)"
INDICATOR = "NY.GDP.MKTP.CN"  # GDP (current LCU)
DATE_RANGE = "2005:2025"
URL = (
    f"https://api.worldbank.org/v2/country/all/indicator/{INDICATOR}"
    f"?format=json&per_page=20000&date={DATE_RANGE}"
)
RAW_NAME = "gdp_lcu_2005_2025.json"
MAGIC = b"["


class _Ref(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    value: str


class _Point(BaseModel):
    model_config = ConfigDict(extra="ignore")
    country: _Ref
    countryiso3code: str
    date: str
    value: float | None


class _Meta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    page: int
    pages: int
    total: int


def parse(payload: bytes) -> list[dict[str, object]]:
    """[meta, data] → [{iso3, country, year, gdp_lcu}]（値のある国のみ、iso3・年でソート）。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"worldbank: not JSON ({e})"
        raise ValueError(msg) from e
    if not (isinstance(doc, list) and len(doc) == 2 and isinstance(doc[1], list)):
        msg = "worldbank: unexpected response shape (expected [meta, data])"
        raise ValueError(msg)
    meta = _Meta.model_validate(doc[0])
    if meta.pages != 1 or meta.total != len(doc[1]):
        msg = f"worldbank: paginated/truncated response (pages={meta.pages}, total={meta.total})"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for item in doc[1]:
        try:
            p = _Point.model_validate(item)
        except ValidationError as e:
            msg = f"worldbank: malformed point ({e.error_count()} errors)"
            raise ValueError(msg) from e
        if p.value is None or len(p.countryiso3code) != 3:
            continue
        rows.append(
            {
                "iso3": p.countryiso3code,
                "country": p.country.value,
                "year": int(p.date),
                "gdp_lcu": p.value,
            }
        )
    rows.sort(key=lambda r: (str(r["iso3"]), int(str(r["year"]))))
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    out = [
        {
            "iso3": r["iso3"],
            "year": int(str(r["year"])),
            "country": r["country"],
            "gdp_lcu": r["gdp_lcu"],
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: (str(r["iso3"]), int(str(r["year"]))))
    return out
