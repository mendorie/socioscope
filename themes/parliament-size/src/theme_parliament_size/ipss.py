"""IPSS 日本の地域別将来推計人口（令和 5 年推計）結果表 1: 都道府県別 総人口 2020–2050。

H11 に使う。

Pure transforms only (no I/O). xlsx 1 シート。4 行目が年の見出し（2020年…2050年、5 年刻み）、
「市などの別」列が 'a' の行が都道府県（47 行）。全国行は無いので 47 県の和で 2020 年の国勢調査
総人口（126,146,099 人）と照合する（fail-closed、±0.1%）。推計は総人口（外国人を含む）。

License: 国立社会保障・人口問題研究所の公表資料は出典を明示すれば自由に利用できる
（https://www.ipss.go.jp/、2026-10-29 確認）。出典表記「国立社会保障・人口問題研究所
『日本の地域別将来推計人口（令和 5 年推計）』」。
"""

from __future__ import annotations

import io
import re
from collections.abc import Mapping, Sequence

SOURCE = "ipss_regional"
LICENSE = (
    "出典明示で利用可（国立社会保障・人口問題研究所『日本の地域別将来推計人口（令和 5 年推計）』、"
    "https://www.ipss.go.jp/pp-shicyoson/j/shicyoson23/t-page.asp）"
)
URL = "https://www.ipss.go.jp/pp-shicyoson/j/shicyoson23/2gaiyo_hyo/kekkahyo1.xlsx"
RAW_NAME = "ipss2023_kekkahyo1_prefecture_population.xlsx"
MAGIC = b"PK"
N_PREFS = 47
CENSUS_2020_TOTAL = 126_146_099  # 令和 2 年国勢調査 総人口（人）
_YEAR = re.compile(r"^(\d{4})年$")


def workbook_rows(payload: bytes) -> list[list[object]]:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as e:
        msg = "ipss: payload is not a readable xlsx"
        raise ValueError(msg) from e
    return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]


def parse(rows: Sequence[Sequence[object]]) -> list[dict[str, object]]:
    """→ [{pref_code, pref, year, population}]（47 都道府県 × 7 年、long）。"""
    years: dict[int, int] = {}
    start = None
    for i, row in enumerate(rows[:12]):
        for j, c in enumerate(row):
            m = _YEAR.match(str(c or "").strip())
            if m:
                y = int(m.group(1))
                if y not in years.values():
                    years[j] = y
        if years:
            start = i + 1
            break
    if start is None or not years:
        msg = "ipss: year header row not found"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    for row in rows[start:]:
        if len(row) < 5 or str(row[1] or "").strip() != "a":
            continue
        pref = str(row[2] or "").strip()
        code = str(row[0] or "").strip()
        for j, y in years.items():
            v = row[j] if j < len(row) else None
            if v is None:
                msg = f"ipss: missing population for {pref} {y}"
                raise ValueError(msg)
            out.append(
                {"pref_code": code, "pref": pref, "year": y, "population": int(float(str(v)))}
            )
    prefs = {str(r["pref"]) for r in out}
    if len(prefs) != N_PREFS:
        msg = f"ipss: expected {N_PREFS} prefectures, got {len(prefs)}"
        raise ValueError(msg)
    total_2020 = sum(int(str(r["population"])) for r in out if r["year"] == 2020)
    if abs(total_2020 - CENSUS_2020_TOTAL) > CENSUS_2020_TOTAL * 0.001:
        msg = f"ipss: 2020 total {total_2020} != census {CENSUS_2020_TOTAL}"
        raise ValueError(msg)
    out.sort(key=lambda r: (str(r["pref_code"]), int(str(r["year"]))))
    return out


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    out = [
        {
            "iso3": "JPN",
            "year": int(str(r["year"])),
            "pref_code": r["pref_code"],
            "pref": r["pref"],
            "population": r["population"],
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: (str(r["pref_code"]), int(str(r["year"]))))
    return out
