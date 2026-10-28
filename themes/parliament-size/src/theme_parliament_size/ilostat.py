"""ILOSTAT（rplumber.ilo.org、鍵不要）: 公務就業者（ISIC Rev.4 大分類 O）と公的部門就業者。

H2e に使う。Pure transforms only (no I/O). `EMP_TEMP_SEX_ECO_NB_A`（経済活動別、ISIC O と
総数）と `EMP_TEMP_SEX_INS_NB_A`（公的／民間部門）を 1 リクエストずつ JSON（レコードの配列）で
取る。
`parse` は国 × 年 × 指標 の long 行にし、配列でない・必須キーが無い場合は ValueError
（fail-closed）。

License: ILOSTAT のデータは CC BY 4.0（https://ilostat.ilo.org/about/terms-of-use/、
2026-10-28 確認）。
出典表記「ILOSTAT, ILO modelled estimates / labour force surveys (accessed 2026-10-28)」。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

SOURCE = "ilostat"
LICENSE = "CC BY 4.0 (ILOSTAT, International Labour Organization, https://ilostat.ilo.org)"
BASE = "https://rplumber.ilo.org/data/indicator/"
TIME_FROM = 2015
MAGIC = b"["
# (indicator id, classif1 filter, raw name, classif1 code -> metric)
ECO_URL = (
    f"{BASE}?id=EMP_TEMP_SEX_ECO_NB_A&sex=SEX_T&classif1=ECO_ISIC4_O+ECO_ISIC4_TOTAL"
    f"&timefrom={TIME_FROM}&format=.json"
)
ECO_RAW_NAME = "emp_eco_isic4_o_total.json"
INS_URL = (
    f"{BASE}?id=EMP_TEMP_SEX_INS_NB_A&sex=SEX_T&classif1=INS_SECTOR_PUB&timefrom={TIME_FROM}"
    "&format=.json"
)
INS_RAW_NAME = "emp_public_sector.json"
METRICS: dict[str, str] = {
    "ECO_ISIC4_O": "emp_public_admin",  # 公務・防衛・社会保障（千人）
    "ECO_ISIC4_TOTAL": "emp_total",  # 総就業者（千人）
    "INS_SECTOR_PUB": "emp_public_sector",  # 公的部門（千人）
}
REQUIRED = ("ref_area", "classif1", "time", "obs_value")


def parse(payload: bytes) -> list[dict[str, object]]:
    """JSON 配列 → [{iso3, year, metric, value_thousands, source_note}]（採用 classif1 のみ）。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"ilostat: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, list):
        msg = "ilostat: expected a JSON array of records"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for rec in doc:
        if not isinstance(rec, dict) or any(k not in rec for k in REQUIRED):
            msg = f"ilostat: record without {REQUIRED}"
            raise ValueError(msg)
        metric = METRICS.get(str(rec["classif1"]))
        if metric is None or rec["obs_value"] is None:
            continue
        rows.append(
            {
                "iso3": str(rec["ref_area"]),
                "year": int(str(rec["time"])),
                "metric": metric,
                "value_thousands": float(rec["obs_value"]),
                "source_note": str(rec.get("source") or ""),
            }
        )
    rows.sort(key=lambda r: (str(r["iso3"]), str(r["metric"]), int(str(r["year"]))))
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """国 × 年 × 指標 の long mart。同じキーが 2 行あれば ValueError。"""
    seen: set[tuple[str, int, str]] = set()
    out: list[dict[str, object]] = []
    for r in staged:
        key = (str(r["iso3"]), int(str(r["year"])), str(r["metric"]))
        if key in seen:
            msg = f"ilostat: duplicate {key}"
            raise ValueError(msg)
        seen.add(key)
        out.append(
            {
                "iso3": key[0],
                "year": key[1],
                "metric": key[2],
                "value_thousands": r["value_thousands"],
                "source_note": r.get("source_note", ""),
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: (str(r["iso3"]), str(r["metric"]), int(str(r["year"]))))
    return out
