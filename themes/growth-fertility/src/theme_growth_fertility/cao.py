"""H10: 内閣府 経済社会総合研究所 県民経済計算（2022 年度版）総括表 7「1 人当たり県民所得」xlsx
-> long rows for ``marts/jp_prefecture_panel``. Pure; no I/O.

The workbook has two sheets (実数 / 増加率); only 実数 is read: rows = 47 prefectures (code +
name) followed by 全県計 (-> ``pref_code`` "00"), 地域ブロック and 政令指定都市 (dropped); columns =
fiscal years 2011–2022 in thousand yen (nominal). Title, unit, year row, code/name pairs and the
47 + 全県計 rows are checked; any mismatch raises ``ValueError`` (fail closed)."""

import re
import unicodedata
from collections.abc import Sequence

from theme_growth_fertility.prefecture import Row, num, panel_row, pref_code, regions, sheet_rows

URL = (
    "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2022/"
    "soukatu7.xlsx"
)
RAW_NAME = "kenmin_soukatu7.xlsx"
SOURCE = "cao_kenmin"
TABLE = "総括表7"
SHEET = "実数"
METRIC = "income_per_capita"
YEARS: tuple[int, ...] = tuple(range(2011, 2023))
# 内閣府サイトの利用規約 = 政府標準利用規約（第2.0版）（CC BY 4.0 互換、出典表示。確認 2026-10-18）
LICENSE = (
    "政府標準利用規約（第2.0版）/ CC BY 4.0 compatible "
    "(https://www.cao.go.jp/notice/notice.html, checked 2026-10-18; "
    "出典：内閣府「県民経済計算（2022 年度）」総括表 7)"
)
_TITLE = "7.1人当たり県民所得"
_UNIT = "(単位:千円)"
_FIRST_YEAR_COL = 4
_CODE_COL = 1
_NAME_COL = 2

Rows = Sequence[dict[int, str]]


def _norm(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def _label(r: dict[int, str]) -> str | None:
    code, name = _norm(r.get(_CODE_COL)), _norm(r.get(_NAME_COL))
    if name == "全県計":
        return name
    if re.fullmatch(r"\d{2}", code) and name:
        if pref_code(name) != code:
            msg = f"{TABLE}: prefecture code {code} does not match name {name!r}"
            raise ValueError(msg)
        return name
    return None


def income_rows_from_sheet(rows: Rows) -> list[Row]:
    """実数 sheet -> rows (pref_code x fiscal year, metric ``income_per_capita``, 千円)."""
    if not rows or not any(_norm(v).startswith(_TITLE) for v in rows[0].values()):
        msg = f"{TABLE}: title {_TITLE!r} not found in the first row"
        raise ValueError(msg)
    if not any(_norm(v) == _UNIT for r in rows[:6] for v in r.values()):
        msg = f"{TABLE}: unit cell {_UNIT!r} not found"
        raise ValueError(msg)
    try:
        h = next(i for i, r in enumerate(rows[:8]) if _norm(r.get(_FIRST_YEAR_COL)) == "2011")
    except StopIteration:
        msg = f"{TABLE}: year row starting with 2011 not found"
        raise ValueError(msg) from None
    years = [_norm(rows[h].get(c)) for c in range(_FIRST_YEAR_COL, _FIRST_YEAR_COL + len(YEARS))]
    if years != [str(y) for y in YEARS]:
        msg = f"{TABLE}: year columns must be {YEARS}, got {years}"
        raise ValueError(msg)
    out: list[Row] = []
    for pc, r in regions(rows, h + 1, TABLE, _label, national_first=False, national_label="全県計"):
        for i, year in enumerate(YEARS):
            v = num(r.get(_FIRST_YEAR_COL + i), f"{TABLE} {pc} {year}")
            if v is None:
                msg = f"{TABLE} {pc} {year}: value missing"
                raise ValueError(msg)
            out.append(panel_row(pc, year, METRIC, "T", None, round(v), TABLE, SOURCE))
    return out


def income_rows(payload: bytes) -> list[Row]:
    return income_rows_from_sheet(sheet_rows(payload, SHEET))


__all__ = [
    "LICENSE",
    "METRIC",
    "RAW_NAME",
    "SOURCE",
    "TABLE",
    "URL",
    "YEARS",
    "income_rows",
    "income_rows_from_sheet",
    "sheet_rows",
]
