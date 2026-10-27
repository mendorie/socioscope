"""e-Stat 令和 2 年国勢調査 人口等基本集計 表 2-1（国籍総数か日本人別人口、全国・都道府県）。

衆議院議員選挙区画定審議会設置法は、小選挙区の都道府県別定数と比例ブロック定数を国勢調査の
「日本国民の人口」でアダムズ方式により配分する。その人口（2020 年、日本人）を都道府県別に取る。
Pure transforms only (no I/O)。

License: 政府標準利用規約（第 2.0 版、CC BY 4.0 互換）。
出典「政府統計の総合窓口(e-Stat)、国勢調査（総務省）を加工」。
"""

from __future__ import annotations

import io
import re
from collections.abc import Sequence

SOURCE = "estat_census"
LICENSE = (
    "政府標準利用規約（第2.0版、CC BY 4.0 互換）。出典: 政府統計の総合窓口(e-Stat)、"
    "令和2年国勢調査 人口等基本集計（総務省統計局）を加工"
)
STAT_INF_ID = "000032142404"  # 表 2-1、Excel（fileKind=0）
URL = f"https://www.e-stat.go.jp/stat-search/file-download?statInfId={STAT_INF_ID}&fileKind=0"
RAW_NAME = "census2020_table2-1.xlsx"
MAGIC = b"PK"
CENSUS_YEAR = 2020
N_PREFS = 47

Rows = list[list[object]]

# レイアウト（2026-10-27 に確認）: 行 = 国籍区分 × 男女 × 地域。
#   列 0 国籍区分（'0_国籍総数' / '1_うち日本人'）、列 1 男女（'0_総数' / '1_男' / '2_女'）、
#   列 2 地域識別コード（'a' = 都道府県。'00000_全国' も 'a'）、列 3 地域名（'01000_北海道'）、
#   列 4 総数（人）。
COL_NATIONALITY, COL_SEX, COL_LEVEL, COL_AREA, COL_TOTAL = 0, 1, 2, 3, 4
NATIONALITY = {"0_国籍総数": "total", "1_うち日本人": "japanese"}
_AREA = re.compile(r"^(\d{5})_(.+)$")


def workbook_rows(payload: bytes) -> list[tuple[str, Rows]]:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as e:
        msg = "payload is not a readable xlsx"
        raise ValueError(msg) from e
    return [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)]) for ws in wb.worksheets]


def _text(v: object) -> str:
    return "" if v is None else str(v).replace("　", " ").strip()


def _num(v: object) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int | float):
        return float(v)
    s = _text(v).replace(",", "")
    return float(s) if re.match(r"^\d+(\.\d+)?$", s) else None


def parse(sheets: Sequence[tuple[str, Rows]]) -> list[dict[str, object]]:
    """→ [{pref_code, pref, population_total, population_japanese}] 47 行。全国行で検算。"""
    if not sheets:
        msg = "workbook has no sheet"
        raise ValueError(msg)
    rows = sheets[0][1]
    got: dict[tuple[str, str], float] = {}  # (nationality, area) -> population
    national: dict[str, float] = {}
    for row in rows:
        if len(row) <= COL_TOTAL:
            continue
        nat = NATIONALITY.get(_text(row[COL_NATIONALITY]))
        if nat is None or _text(row[COL_SEX]) != "0_総数" or _text(row[COL_LEVEL]) != "a":
            continue
        m = _AREA.match(_text(row[COL_AREA]))
        value = _num(row[COL_TOTAL])
        if not m or value is None:
            continue
        code, name = m.group(1), m.group(2)
        if code == "00000":
            national[nat] = value
        else:
            got[(nat, f"{code}_{name}")] = value
    areas = sorted({a for _, a in got})
    if len(areas) != N_PREFS:
        msg = f"census: expected {N_PREFS} prefectures, got {len(areas)}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for area in areas:
        code, name = area.split("_", 1)
        try:
            total, jp = got[("total", area)], got[("japanese", area)]
        except KeyError as e:
            msg = f"census: {area} lacks total or japanese population"
            raise ValueError(msg) from e
        out.append(
            {
                "pref_code": code[:2],
                "pref": name,
                "population_total": total,
                "population_japanese": jp,
            }
        )
    for nat, col in (("total", "population_total"), ("japanese", "population_japanese")):
        if nat not in national:
            msg = f"census: national row for {nat} missing"
            raise ValueError(msg)
        s = sum(float(str(r[col])) for r in out)
        if abs(s - national[nat]) > 0.5:
            msg = f"census {nat}: prefectures sum {s} != national {national[nat]}"
            raise ValueError(msg)
    return out


def build_mart(staged: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    out = [
        {
            "iso3": "JPN",
            "year": CENSUS_YEAR,
            "pref_code": r["pref_code"],
            "pref": r["pref"],
            "population_total": r["population_total"],
            "population_japanese": r["population_japanese"],
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: str(r["pref_code"]))
    if len(out) != N_PREFS or len({r["pref_code"] for r in out}) != N_PREFS:
        msg = f"census mart: expected {N_PREFS} distinct prefectures"
        raise ValueError(msg)
    return out
