"""World Bank WDI v2 API（鍵不要）: 保健支出 3 指標（2010〜2024、全経済体）。

介護・医療の賃金が「公定価格」で決まる国の財政余地を国際比較する分母に使う。
parliament-size の `worldbank.py` と同じ URL 規約だが、テーマ間 import はしない（ADR 0001）
ので必要な部分だけ複製。

指標ごとに 1 リクエスト（`[meta, data]` の JSON 配列。1 ページ 3,990 点、2026-10-30 時点）:
- `SH.XPD.GHED.CH.ZS` 国内一般政府保健支出（経常保健支出に占める %）→ `gov_share_pct`
- `SH.XPD.CHEX.GD.ZS` 経常保健支出（対 GDP %）→ `chex_gdp_pct`
- `SH.XPD.CHEX.PC.CD` 1 人当たり経常保健支出（現在 US ドル）→ `chex_pc_usd`

`parse` は `countryiso3code` が空（所得グループなどの集計）か `value` が null の点を落とす。
地域集計でも ISO3 風のコードを持つもの（AFE・WLD・EUU など）は残る（parliament-size と同じ）。
ページ分割・total 不一致・点の形が違う・指標 ID が違うときは ValueError（fail-closed）。

License: CC BY 4.0（https://datacatalog.worldbank.org/public-licenses、2026-10-30 確認）。
出典表記「World Bank, World Development Indicators (accessed 2026-10-30)」。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, ValidationError

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.pipeline import THEME

SOURCE = "wdi_health"
LICENSE = "CC BY 4.0 (World Bank WDI, https://datacatalog.worldbank.org/public-licenses)"
BASE = "https://api.worldbank.org/v2/country/all/indicator"
DATE_RANGE = "2010:2024"
MAGIC = b"["
MART_TABLE = "marts/wdi_health_expenditure"
MART_SOURCE = "worldbank_wdi"
# indicator id -> mart column（辞書の順＝リクエスト順＝mart の列順）
INDICATORS: dict[str, str] = {
    "SH.XPD.GHED.CH.ZS": "gov_share_pct",
    "SH.XPD.CHEX.GD.ZS": "chex_gdp_pct",
    "SH.XPD.CHEX.PC.CD": "chex_pc_usd",
}
MART_COLUMNS: tuple[str, ...] = ("iso3", "year", *INDICATORS.values(), "source")


def url(indicator: str) -> str:
    return f"{BASE}/{indicator}?format=json&per_page=20000&date={DATE_RANGE}"


def _slug(indicator: str) -> str:
    return indicator.lower().replace(".", "_")


def raw_name(indicator: str) -> str:
    return f"{_slug(indicator)}_{DATE_RANGE.replace(':', '_')}.json"


def staged_table(indicator: str) -> str:
    return f"staged/{SOURCE}/{_slug(indicator)}"


class _Ref(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str


class _Point(BaseModel):
    model_config = ConfigDict(extra="ignore")
    indicator: _Ref
    countryiso3code: str
    date: str
    value: float | None


class _Meta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    page: int
    pages: int
    total: int


def _key(r: Mapping[str, object]) -> tuple[str, int]:
    return (str(r["iso3"]), int(str(r["year"])))


def parse(payload: bytes, indicator: str) -> list[dict[str, object]]:
    """[meta, data] → [{iso3, year, indicator, value}]（値のある ISO3 のみ、iso3・年でソート）。"""
    if indicator not in INDICATORS:
        msg = f"wdi_health: unknown indicator {indicator!r}"
        raise ValueError(msg)
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"wdi_health: not JSON ({e})"
        raise ValueError(msg) from e
    if not (isinstance(doc, list) and len(doc) == 2 and isinstance(doc[1], list)):
        msg = "wdi_health: unexpected response shape (expected [meta, data])"
        raise ValueError(msg)
    try:
        meta = _Meta.model_validate(doc[0])
    except ValidationError as e:
        msg = f"wdi_health: malformed page meta ({e.error_count()} errors)"
        raise ValueError(msg) from e
    if meta.pages != 1 or meta.total != len(doc[1]):
        msg = f"wdi_health: paginated/truncated response (pages={meta.pages}, total={meta.total})"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for item in doc[1]:
        try:
            p = _Point.model_validate(item)
        except ValidationError as e:
            msg = f"wdi_health: malformed point ({e.error_count()} errors)"
            raise ValueError(msg) from e
        if p.indicator.id != indicator:
            msg = f"wdi_health: payload indicator {p.indicator.id!r} != {indicator!r}"
            raise ValueError(msg)
        if p.value is None or len(p.countryiso3code) != 3:
            continue
        rows.append(
            {
                "iso3": p.countryiso3code,
                "year": int(p.date),
                "indicator": indicator,
                "value": p.value,
            }
        )
    rows.sort(key=_key)
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """iso3 × year の wide mart（列は INDICATORS の順、欠測は None、source='worldbank_wdi'）。

    同じ (iso3, year, indicator) が 2 行あれば ValueError。"""
    wide: dict[tuple[str, int], dict[str, object]] = {}
    for r in staged:
        indicator = str(r["indicator"])
        if indicator not in INDICATORS:
            msg = f"wdi_health: unknown indicator {indicator!r} in staged rows"
            raise ValueError(msg)
        key = _key(r)
        row = wide.setdefault(
            key,
            {"iso3": key[0], "year": key[1], **dict.fromkeys(INDICATORS.values())},
        )
        col = INDICATORS[indicator]
        if row[col] is not None:
            msg = f"wdi_health: duplicate {(*key, indicator)}"
            raise ValueError(msg)
        row[col] = r["value"]
    return [{**wide[k], "source": MART_SOURCE} for k in sorted(wide)]


# ---- stage functions (I/O through ports only)


def fetch(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for indicator in INDICATORS:
        name, u = raw_name(indicator), url(indicator)
        try:
            payload = ctx.fetcher.fetch(u)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.startswith(MAGIC):
            skipped.append(f"{name}: non-JSON payload")
            continue
        rec = ctx.raw.put(
            theme=THEME, source=SOURCE, name=name, url=u, license=LICENSE, payload=payload
        )
        written.append(rec.relative_path)
    return written, skipped


def stage(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for indicator in INDICATORS:
        name = raw_name(indicator)
        payload = ctx.raw.get(theme=THEME, source=SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: no raw")
            continue
        table = staged_table(indicator)
        ctx.tables.write_table(table, parse(payload, indicator))
        written.append(table)
    return written, skipped


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    staged: list[dict[str, object]] = []
    for indicator in INDICATORS:
        try:
            staged.extend(ctx.tables.read_table(staged_table(indicator)))
        except FileNotFoundError:
            continue
    if not staged:
        skipped.append(f"{MART_TABLE}: no staged table")
        return written, skipped
    ctx.tables.write_table(MART_TABLE, build_mart(staged))
    written.append(MART_TABLE)
    return written, skipped
