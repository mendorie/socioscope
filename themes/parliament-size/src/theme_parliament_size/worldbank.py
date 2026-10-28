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
BASE = "https://api.worldbank.org/v2/country/all/indicator"


def indicator_url(indicator: str, date_range: str) -> str:
    return f"{BASE}/{indicator}?format=json&per_page=20000&date={date_range}"


URL = indicator_url(INDICATOR, DATE_RANGE)
RAW_NAME = "gdp_lcu_2005_2025.json"
MAGIC = b"["
# 人口（H6b: 定数変更の直前 10 年の人口変化率）。別 raw・別 mart（`value` 列名は population）
POP_INDICATOR = "SP.POP.TOTL"
POP_DATE_RANGE = "1980:2025"
POP_URL = indicator_url(POP_INDICATOR, POP_DATE_RANGE)
POP_RAW_NAME = "population_1980_2025.json"
# 1 人当たり名目 GDP（現地通貨。H12: 議員基本給の相対水準の分母）
GDP_PCAP_INDICATOR = "NY.GDP.PCAP.CN"
GDP_PCAP_URL = indicator_url(GDP_PCAP_INDICATOR, DATE_RANGE)
GDP_PCAP_RAW_NAME = "gdp_pcap_lcu_2005_2025.json"


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


def parse(payload: bytes, value_col: str = "gdp_lcu") -> list[dict[str, object]]:
    """[meta, data] → [{iso3, country, year, <value_col>}]（値のある国のみ、iso3・年でソート）。"""
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
                value_col: p.value,
            }
        )
    rows.sort(key=lambda r: (str(r["iso3"]), int(str(r["year"]))))
    return rows


def parse_population(payload: bytes) -> list[dict[str, object]]:
    return parse(payload, value_col="population")


def build_mart(
    staged: Sequence[Mapping[str, object]], value_col: str = "gdp_lcu"
) -> list[dict[str, object]]:
    out = [
        {
            "iso3": r["iso3"],
            "year": int(str(r["year"])),
            "country": r["country"],
            value_col: r[value_col],
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: (str(r["iso3"]), int(str(r["year"]))))
    return out


def build_population_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    return build_mart(staged, value_col="population")


def parse_gdp_pcap(payload: bytes) -> list[dict[str, object]]:
    return parse(payload, value_col="gdp_pcap_lcu")


def build_gdp_pcap_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    return build_mart(staged, value_col="gdp_pcap_lcu")
