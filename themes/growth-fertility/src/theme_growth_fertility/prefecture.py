"""H10: Japanese prefecture panel — prefecture codes, two e-Stat time-series workbooks and the
``marts/jp_prefecture_panel`` builder. Pure; no I/O.

- ``PREF_CODES``: 47 prefectures (short names as IPSS prints them) -> JIS 2-digit code; 全国 is
  ``"00"``. ``pref_code`` normalises the labels every source uses (``北 海 道``, ``青森県``,
  ``東京都``, ``京都府``, ``全県計``) and returns ``None`` for cities / regional blocks.
- 就業構造基本調査 時系列統計表 第18表 (``employment_rows``): 男女 x 従業上の地位・雇用形態 x
  調査年 (1977–2022, 10 surveys) in one wide sheet ``Z018`` (18 blocks of 10 year columns).
  Metrics kept: employed (有業者 総数), employees (雇用者), regular_employees, nonregular_employees;
  the 非正規比率 is computed downstream. 政令指定都市 rows are dropped.
- 住宅・土地統計調査 時系列 第34-2表 (``rent_rows``): one sheet per survey (1993–2023), layouts
  differ per sheet (``RENT_SHEETS``). Metrics: rent (総数), rent_private (民営借家 total,
  2018–), rent_private_wood (2003–), rent_private_nonwood (every year). Yen per month.

Every parser fails closed (title / header / year / prefecture-order mismatch -> ``ValueError``).
"""

import re
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from theme_growth_fertility.estat import LICENSE as _ESTAT_LICENSE
from theme_growth_fertility.estat import file_download_url, xlsx_rows

LICENSE = _ESTAT_LICENSE
PREF_NAMES: tuple[str, ...] = (
    "北海道",
    "青森",
    "岩手",
    "宮城",
    "秋田",
    "山形",
    "福島",
    "茨城",
    "栃木",
    "群馬",
    "埼玉",
    "千葉",
    "東京",
    "神奈川",
    "新潟",
    "富山",
    "石川",
    "福井",
    "山梨",
    "長野",
    "岐阜",
    "静岡",
    "愛知",
    "三重",
    "滋賀",
    "京都",
    "大阪",
    "兵庫",
    "奈良",
    "和歌山",
    "鳥取",
    "島根",
    "岡山",
    "広島",
    "山口",
    "徳島",
    "香川",
    "愛媛",
    "高知",
    "福岡",
    "佐賀",
    "長崎",
    "熊本",
    "大分",
    "宮崎",
    "鹿児島",
    "沖縄",
)
PREF_CODES: dict[str, str] = {n: f"{i:02d}" for i, n in enumerate(PREF_NAMES, start=1)}
NATIONAL_CODE = "00"
NATIONAL_NAME = "全国"
_NATIONAL_LABELS = frozenset({"全国", "全県計"})
_CODE_TO_NAME: dict[str, str] = {c: n for n, c in PREF_CODES.items()} | {
    NATIONAL_CODE: NATIONAL_NAME
}
REGION_CODES: tuple[str, ...] = (NATIONAL_CODE, *PREF_CODES.values())

PANEL_METRICS: tuple[str, ...] = (
    "tfr",
    "mean_age_first_marriage",
    "never_married_m30_34",
    "never_married_f25_29",
    "never_married_at_50",
    "lfp",
    "unemployment_rate",
    "employed",
    "employees",
    "regular_employees",
    "nonregular_employees",
    "rent",
    "rent_private",
    "rent_private_wood",
    "rent_private_nonwood",
    "income_per_capita",
)

SHUGYO_TS18_STAT_INF_ID = "000031732282"
SHUGYO_TS18_URL = file_download_url(SHUGYO_TS18_STAT_INF_ID, file_kind=4)
SHUGYO_TS18_RAW_NAME = "shugyo_ts18_employment.xlsx"
SHUGYO_TS18_SOURCE = "estat_shugyo"
SHUGYO_TS18_TABLE = "時系列18"
SHUGYO_TS18_SHEET = "Z018"
SHUGYO_YEARS: tuple[int, ...] = (1977, 1982, 1987, 1992, 1997, 2002, 2007, 2012, 2017, 2022)

JUTAKU_STAT_INF_ID = "000040354073"
JUTAKU_URL = file_download_url(JUTAKU_STAT_INF_ID, file_kind=4)
JUTAKU_RAW_NAME = "jutaku_34_2_rent.xlsx"
JUTAKU_SOURCE = "estat_jutaku"
JUTAKU_TABLE = "時系列34-2"

Rows = Sequence[dict[int, str]]
Row = dict[str, object]
_MISSING = frozenset({"…", "...", "-"})


# ---- helpers ---------------------------------------------------------------------------------


def _norm(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).replace("〜", "~")


def sheet_rows(payload: bytes, sheet: str | None = None) -> list[dict[int, str]]:
    """``estat.xlsx_rows`` (``ValueError`` when not an xlsx or the sheet is missing)."""
    return xlsx_rows(payload, sheet)


def pref_code(label: str) -> str | None:
    """JIS code of a prefecture label (``北 海 道``, ``青森県``, ``東京都``, ``京都府``, ``沖縄``),
    ``"00"`` for 全国 / 全県計, ``None`` for anything else (cities, blocks)."""
    s = _norm(label)
    if s in _NATIONAL_LABELS:
        return NATIONAL_CODE
    if s in PREF_CODES:
        return PREF_CODES[s]
    if s[-1:] in {"都", "府", "県"} and s[:-1] in PREF_CODES:
        return PREF_CODES[s[:-1]]
    return None


def pref_name(code: str) -> str:
    return _CODE_TO_NAME[code]


def panel_row(
    code: str,
    year: int,
    metric: str,
    sex: str,
    age_class: str | None,
    value: float | int,
    table: str,
    source: str,
) -> Row:
    return {
        "pref_code": code,
        "pref_name": pref_name(code),
        "year": year,
        "metric": metric,
        "sex": sex,
        "age_class": age_class,
        "value": value,
        "table": table,
        "source": source,
    }


def regions(
    rows: Rows,
    start: int,
    code: str,
    label_of: Callable[[dict[int, str]], str | None],
    *,
    national_first: bool = True,
    national_label: str = NATIONAL_NAME,
) -> list[tuple[str, dict[int, str]]]:
    """The 48 region rows (全国 + 47 prefectures in JIS order; 全国 last when *national_first*
    is false) from *start*. Rows whose label is ``None`` / empty are skipped (notes, unnamed
    sub-rows); a label out of order, or fewer than 48 rows, raises ``ValueError``."""
    expected = list(REGION_CODES) if national_first else [*REGION_CODES[1:], NATIONAL_CODE]

    def name(c: str) -> str:
        return national_label if c == NATIONAL_CODE else pref_name(c)

    out: list[tuple[str, dict[int, str]]] = []
    for i in range(start, len(rows)):
        label = label_of(rows[i])
        if not label:
            continue
        want = expected[len(out)]
        got = pref_code(label)
        if got != want:
            msg = (
                f"{code}: prefecture row {i} is {label!r} ({got}), expected {name(want)!r} ({want})"
            )
            raise ValueError(msg)
        out.append((got, rows[i]))
        if len(out) == len(expected):
            return out
    msg = (
        f"{code}: prefecture rows incomplete ({len(out)} of {len(expected)}; next expected "
        f"{name(expected[len(out)])!r})"
    )
    raise ValueError(msg)


def first_region_row(
    rows: Rows, start: int, code: str, label_of: Callable[[dict[int, str]], str | None]
) -> int:
    """Index of the first row at/after *start* whose label is 全国 (``ValueError`` if none)."""
    for i in range(start, len(rows)):
        label = label_of(rows[i])
        if label and pref_code(label) == NATIONAL_CODE:
            return i
    msg = f"{code}: {NATIONAL_NAME} row not found"
    raise ValueError(msg)


def num(text: str | None, where: str) -> float | None:
    """Float of a cell; ``None`` for the not-published marks ('…', '...', '-')."""
    s = _norm(text)
    if s in _MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        msg = f"{where}: non-numeric cell {text!r}"
        raise ValueError(msg) from None


def _find_cell(rows: Rows, lo: int, hi: int, pred: Callable[[str], bool]) -> bool:
    return any(pred(_norm(v)) for r in rows[lo:hi] for v in r.values())


# ---- 就業構造基本調査 時系列統計表 第18表 -----------------------------------------------------

_SHUGYO_FIRST_COL = 12
_FOOTNOTE = re.compile(r"\d\)$")
_SHUGYO_SEX_BASE: tuple[tuple[str, int], ...] = (("T", 12), ("M", 72), ("F", 132))
# status block offset from the sex base -> metric (自営業主 +10 and 家族従業者 +20 are not kept)
_SHUGYO_STATUS: tuple[tuple[int, str], ...] = (
    (0, "employed"),
    (30, "employees"),
    (40, "regular_employees"),
    (50, "nonregular_employees"),
)


def employment_rows_from_sheet(rows: Rows) -> list[Row]:
    """Sheet ``Z018`` -> long rows (pref_code x sex x survey year x metric, persons)."""
    code = SHUGYO_TS18_TABLE
    if not _find_cell(rows, 0, 11, lambda s: s.startswith("第18表")):
        msg = f"{code}: title cell starting with 第18表 not found"
        raise ValueError(msg)
    try:
        sex_row = next(r for r in rows[:12] if _norm(r.get(9)) == "男女")
        status_row = next(r for r in rows[:12] if _norm(r.get(9)) == "従業上の地位")
        type_row = next(r for r in rows[:12] if _norm(r.get(9)) == "雇用形態")
        h = next(i for i, r in enumerate(rows[:14]) if _norm(r.get(8)) == "都道府県")
    except StopIteration:
        msg = f"{code}: header rows (男女 / 従業上の地位 / 雇用形態 / 都道府県) not found"
        raise ValueError(msg) from None
    expect: list[tuple[dict[int, str], int, str]] = [
        (sex_row, 13, "総数"),
        (sex_row, 73, "男"),
        (sex_row, 133, "女"),
    ]
    for _sex, base in _SHUGYO_SEX_BASE:
        expect += [
            (status_row, base, "総数"),
            (status_row, base + 30, "雇用者"),
            (type_row, base + 40, "正規の職員・従業員"),
            (type_row, base + 50, "非正規の職員・従業員"),
        ]
    for row, col, label in expect:
        if _norm(row.get(col)) != label:
            msg = f"{code}: header column {col} is {row.get(col)!r}, expected {label!r}"
            raise ValueError(msg)
    # '19921)': the 1992 非正規 column carries a footnote mark (パート・アルバイトの合計)
    years = [
        _FOOTNOTE.sub("", _norm(rows[h].get(c)))
        for c in range(_SHUGYO_FIRST_COL, _SHUGYO_FIRST_COL + 180)
    ]
    if years != [str(y) for y in SHUGYO_YEARS] * 18:
        msg = f"{code}: year columns must be {SHUGYO_YEARS} x 18 blocks, got {years[:12]}…"
        raise ValueError(msg)
    out: list[Row] = []

    def label_of(r: dict[int, str]) -> str | None:
        return r.get(8) or r.get(9)

    first = first_region_row(rows, h + 1, code, label_of)
    for pc, r in regions(rows, first, code, label_of):
        for sex, base in _SHUGYO_SEX_BASE:
            for yi, year in enumerate(SHUGYO_YEARS):
                where = f"{code} {pref_name(pc)} {sex} {year}"
                vals: dict[str, int | None] = {}
                for off, metric in _SHUGYO_STATUS:
                    v = num(r.get(base + off + yi), where)
                    vals[metric] = None if v is None else round(v)
                emp, reg, non = (
                    vals["employees"],
                    vals["regular_employees"],
                    vals["nonregular_employees"],
                )
                if emp is not None and reg is not None and non is not None and emp < reg + non:
                    msg = f"{where}: employees {emp} < regular {reg} + nonregular {non}"
                    raise ValueError(msg)
                if vals["employed"] is not None and emp is not None and vals["employed"] < emp:
                    msg = f"{where}: employed {vals['employed']} < employees {emp}"
                    raise ValueError(msg)
                for metric, v in vals.items():
                    if v is not None:
                        out.append(
                            panel_row(pc, year, metric, sex, None, v, code, SHUGYO_TS18_SOURCE)
                        )
    return out


def employment_rows(payload: bytes) -> list[Row]:
    return employment_rows_from_sheet(sheet_rows(payload, SHUGYO_TS18_SHEET))


# ---- 住宅・土地統計調査 時系列 第34-2表 ---------------------------------------------------------


@dataclass(frozen=True)
class RentLayout:
    year: int
    total_col: int
    nonwood_col: int
    wood_col: int | None = None  # 1993/1998 split wooden rentals by facilities: not comparable
    private_col: int | None = None  # 民営借家 total column exists from 2018
    name_col: int | None = None  # 2018-: code in column 2, name in column 3


RENT_SHEETS: dict[str, RentLayout] = {
    "平成5年": RentLayout(1993, 4, 10),
    "平成10年": RentLayout(1998, 4, 10),
    "平成15年": RentLayout(2003, 4, 9, wood_col=8),
    "平成20年": RentLayout(2008, 4, 9, wood_col=8),
    "平成25年": RentLayout(2013, 4, 9, wood_col=8),
    "平成30年": RentLayout(2018, 5, 11, wood_col=10, private_col=9, name_col=3),
    "令和５年": RentLayout(2023, 5, 11, wood_col=10, private_col=9, name_col=3),
}
_RENT_LABEL_COL = 2
_RENT_HEADER = re.compile(r"^(住宅の)?1か月当たり家賃")
_RENT_PREF = re.compile(r"^(\d{2})(\D*)$")
_RENT_CITY = re.compile(r"^\d{5}")


def _rent_label(layout: RentLayout) -> Callable[[dict[int, str]], str | None]:
    def label_of(r: dict[int, str]) -> str | None:
        s = _norm(r.get(_RENT_LABEL_COL))
        if layout.name_col is not None:
            s += _norm(r.get(layout.name_col))
        if not s or _RENT_CITY.match(s):
            return None
        if s in _NATIONAL_LABELS or s == "00全国":
            return NATIONAL_NAME
        m = _RENT_PREF.match(s)
        if m and m.group(2):
            if pref_code(m.group(2)) != m.group(1):
                msg = f"{JUTAKU_TABLE}: code {m.group(1)} does not match name {m.group(2)!r}"
                raise ValueError(msg)
            return m.group(2)
        return s

    return label_of


def _column_has(rows: Rows, lo: int, hi: int, col: int, pred: Callable[[str], bool]) -> bool:
    return any(pred(_norm(r.get(col))) for r in rows[lo:hi])


def _rent_sheet_rows(sheet: str, rows: Rows, layout: RentLayout) -> list[Row]:
    code = f"{JUTAKU_TABLE} {sheet}"
    label_of = _rent_label(layout)
    try:
        # the column-group header (the title row also mentions 1か月当たり家賃, so anchor on
        # a cell that starts with it: '１か月当たり家賃(・間代)' / '住宅の１か月当たり家賃(円)')
        h = next(
            i
            for i, r in enumerate(rows[:12])
            if _find_cell([r], 0, 1, lambda s: _RENT_HEADER.match(s) is not None)
        )
    except StopIteration:
        msg = f"{code}: header cell 1か月当たり家賃 not found"
        raise ValueError(msg) from None
    first = first_region_row(rows, h + 1, code, label_of)
    checks: list[tuple[int, Callable[[str], bool], str]] = [
        (layout.total_col, lambda s: s == "総数", "総数"),
        (layout.nonwood_col, lambda s: "非木造" in s, "非木造"),
    ]
    if layout.wood_col is not None:
        checks.append((layout.wood_col, lambda s: s in {"木造", "(木造)"}, "木造"))
    if layout.private_col is not None:
        checks.append((layout.private_col, lambda s: s == "民営借家", "民営借家"))
    for col, pred, label in checks:
        if not _column_has(rows, h, first, col, pred):
            msg = f"{code}: header of column {col} lacks {label!r}"
            raise ValueError(msg)
    out: list[Row] = []
    metrics: list[tuple[str, int | None]] = [
        ("rent", layout.total_col),
        ("rent_private", layout.private_col),
        ("rent_private_wood", layout.wood_col),
        ("rent_private_nonwood", layout.nonwood_col),
    ]
    for pc, r in regions(rows, first, code, label_of):
        for metric, mcol in metrics:
            if mcol is None:
                continue
            v = num(r.get(mcol), f"{code} {pref_name(pc)} {metric}")
            if v is not None:
                out.append(
                    panel_row(
                        pc, layout.year, metric, "T", None, round(v), JUTAKU_TABLE, JUTAKU_SOURCE
                    )
                )
    return out


def rent_rows_from_sheets(sheets: dict[str, Rows]) -> list[Row]:
    """{sheet title: rows} for every sheet in ``RENT_SHEETS`` -> long rows."""
    out: list[Row] = []
    for name, layout in RENT_SHEETS.items():
        if name not in sheets:
            msg = f"{JUTAKU_TABLE}: sheet {name!r} missing"
            raise ValueError(msg)
        out.extend(_rent_sheet_rows(name, sheets[name], layout))
    return out


def rent_rows(payload: bytes) -> list[Row]:
    return rent_rows_from_sheets({name: sheet_rows(payload, name) for name in RENT_SHEETS})


# ---- mart --------------------------------------------------------------------------------------


def build_prefecture_mart(parts: dict[str, Sequence[Row]]) -> list[Row]:
    """``marts/jp_prefecture_panel``: every staged part combined, ``value`` as float, sorted by
    (pref_code, year, metric order, sex, age_class); unknown metric or duplicate key raises
    ``ValueError``. Pure and deterministic."""
    out: list[Row] = []
    for rows in parts.values():
        for r in rows:
            if r["metric"] not in PANEL_METRICS:
                msg = f"unknown prefecture-panel metric {r['metric']!r}"
                raise ValueError(msg)
            out.append({**r, "value": float(str(r["value"]))})

    def key(r: Row) -> tuple[object, ...]:
        ac = r["age_class"]
        return (
            str(r["pref_code"]),
            int(str(r["year"])),
            PANEL_METRICS.index(str(r["metric"])),
            str(r["sex"]),
            "" if ac is None else str(ac),
        )

    out.sort(key=key)
    keys = [key(r) for r in out]
    if len(keys) != len(set(keys)):
        dup = next(k for i, k in enumerate(keys) if k in keys[:i])
        msg = f"duplicate key (pref_code, year, metric, sex, age_class) = {dup}"
        raise ValueError(msg)
    return out
