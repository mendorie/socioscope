"""ILOSTAT（rplumber.ilo.org、鍵不要）: 産業別（ISIC Rev.4 大分類）労働争議。
H4（倫理的人質）の国際比較に使う。

指標ごとに 1 リクエスト（全世界、`timefrom=2010`、JSON レコード配列）:
- `STR_TSTR_ECO_NB_A` 争議件数（件）→ `strikes_n`
- `STR_DAYS_ECO_NB_A` 労働損失日数（日。JPN 2023 の総数 3,652 は厚労省公表値と一致）
  → `days_not_worked`
- `STR_WORK_ECO_NB_A` 争議参加人員（千人）→ `workers_involved_thousands`
- `STR_DAYS_ECO_RT_A` 雇用者 1,000 人当たり労働損失日数（率）
  → `days_not_worked_per_1000_workers`
（`STR_TSTR_ECO_RT_A`（争議率）は 2026-10-29 時点で API が 400 を返す＝未提供。）

`classif1` には `ECO_ISIC4_*`（Rev.4 大分類 A〜U・TOTAL・X）のほか `ECO_ISIC3_*`、
`ECO_AGGREGATE_*`、`ECO_SECTOR_*` が混在する。`parse` は **ISIC Rev.4 の大分類 A〜U と TOTAL**
だけを採る（X＝分類不能、ISIC3 系、集約系は落とす）。`obs_value` が無い／null のレコード
（`obs_status` のみ）は欠測として落とす。
配列でない・必須キー（ref_area / classif1 / time）欠落は ValueError（fail-closed）。

2026-10-29 時点: 件数 72 か国・損失日数 73 か国・参加人員 68 か国・損失日数率 49 か国
（2010〜2024）。JPN は件数・日数・参加人員のみ（率は無し）。

License: CC BY 4.0（https://ilostat.ilo.org/about/terms-of-use/、2026-10-29 確認）。
出典表記「ILOSTAT, Strikes and lockouts by economic activity (accessed 2026-10-29)」。
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.pipeline import THEME

SOURCE = "ilo_strikes"
LICENSE = "CC BY 4.0 (ILOSTAT, International Labour Organization, https://ilostat.ilo.org)"
BASE = "https://rplumber.ilo.org/data/indicator/"
TIME_FROM = 2010
MAGIC = b"["
MART_TABLE = "marts/ilo_strikes_by_industry"
# metric -> ILOSTAT indicator id（辞書の順＝リクエスト順）
INDICATORS: dict[str, str] = {
    "strikes_n": "STR_TSTR_ECO_NB_A",
    "days_not_worked": "STR_DAYS_ECO_NB_A",
    "workers_involved_thousands": "STR_WORK_ECO_NB_A",
    "days_not_worked_per_1000_workers": "STR_DAYS_ECO_RT_A",
}
_ISIC4 = re.compile(r"^ECO_ISIC4_([A-U]|TOTAL)$")
REQUIRED = ("ref_area", "classif1", "time")
COLUMNS: tuple[str, ...] = ("iso3", "year", "classif1", "industry", "metric", "value", "note")


def url(metric: str) -> str:
    return f"{BASE}?id={INDICATORS[metric]}&timefrom={TIME_FROM}&format=.json"


def raw_name(metric: str) -> str:
    return f"{INDICATORS[metric].lower()}.json"


def staged_table(metric: str) -> str:
    return f"staged/{SOURCE}/{INDICATORS[metric].lower()}"


def parse(payload: bytes, metric: str) -> list[dict[str, object]]:
    """JSON 配列 → [{iso3, year, classif1, industry, metric, value, note}]。

    ISIC Rev.4 大分類（A〜U）と TOTAL のみ。"""
    if metric not in INDICATORS:
        msg = f"ilo_strikes: unknown metric {metric!r}"
        raise ValueError(msg)
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"ilo_strikes: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, list):
        msg = "ilo_strikes: expected a JSON array of records"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for rec in doc:
        if not isinstance(rec, dict) or any(k not in rec for k in REQUIRED):
            msg = f"ilo_strikes: record without {REQUIRED}"
            raise ValueError(msg)
        m = _ISIC4.match(str(rec["classif1"]))
        if m is None or rec.get("obs_value") is None:
            continue
        rows.append(
            {
                "iso3": str(rec["ref_area"]),
                "year": int(str(rec["time"])),
                "classif1": str(rec["classif1"]),
                "industry": m.group(1),
                "metric": metric,
                "value": float(rec["obs_value"]),
                "note": str(rec.get("note_indicator") or ""),
            }
        )
    rows.sort(key=_key)
    return rows


def _key(r: Mapping[str, object]) -> tuple[str, str, int, str]:
    return (str(r["iso3"]), str(r["metric"]), int(str(r["year"])), str(r["classif1"]))


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """国 × 年 × 産業 × 指標 の long mart（source='ilostat'）。同じキーが 2 行あれば ValueError。"""
    seen: set[tuple[str, str, int, str]] = set()
    out: list[dict[str, object]] = []
    for r in staged:
        key = _key(r)
        if key in seen:
            msg = f"ilo_strikes: duplicate {key}"
            raise ValueError(msg)
        seen.add(key)
        out.append({**{c: r[c] for c in COLUMNS}, "source": "ilostat"})
    out.sort(key=_key)
    return out


# ---- stage functions (I/O through ports only)


def fetch(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for metric in INDICATORS:
        name, u = raw_name(metric), url(metric)
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
    for metric in INDICATORS:
        name = raw_name(metric)
        payload = ctx.raw.get(theme=THEME, source=SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: no raw")
            continue
        table = staged_table(metric)
        ctx.tables.write_table(table, parse(payload, metric))
        written.append(table)
    return written, skipped


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    staged: list[dict[str, object]] = []
    for metric in INDICATORS:
        try:
            staged.extend(ctx.tables.read_table(staged_table(metric)))
        except FileNotFoundError:
            continue
    if not staged:
        skipped.append(f"{MART_TABLE}: no staged table")
        return written, skipped
    ctx.tables.write_table(MART_TABLE, build_mart(staged))
    written.append(MART_TABLE)
    return written, skipped
