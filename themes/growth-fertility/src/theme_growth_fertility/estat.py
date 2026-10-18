"""e-Stat (政府統計の総合窓口) file downloads: URL builders and deterministic file -> rows (no I/O).

Sources, both fetched through the public ``stat-search/file-download`` endpoint (no
application ID needed):

- 国民生活基礎調査（厚生労働省）所得票 statistical tables: one CSV each (``fileKind=1``;
  CP932, a few preamble lines, multi-row headers, full-width digits).
- 就業構造基本調査（総務省）令和4年 全国編 第40表 (男女×配偶関係×年齢×所得, 有業者): published as
  an Excel workbook only (``fileKind=0``; CSV returns 404). It is read with the standard
  library (zipfile + ElementTree), so no spreadsheet dependency is added.

Parsing is fail-closed: an unexpected layout raises ``ValueError`` instead of producing a
partial table.
"""

import csv
import io
import re
import unicodedata
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum
from xml.etree import ElementTree as ET

import xlrd
from pydantic import BaseModel, ConfigDict
from xlrd.biffh import XLRDError

BASE = "https://www.e-stat.go.jp/stat-search/file-download"
LICENSE = (
    "政府標準利用規約（第2.0版）/ CC BY 4.0 compatible "
    "(https://www.e-stat.go.jp/terms-of-use, checked 2026-10-04; 出典：政府統計の総合窓口(e-Stat))"
)
SOURCE = "estat_kiso"  # 国民生活基礎調査 (Comprehensive Survey of Living Conditions)
SURVEY = "国民生活基礎調査"
SOURCE_SHUGYO = "estat_shugyo"  # 就業構造基本調査 (Employment Status Survey)
SURVEY_SHUGYO = "就業構造基本調査"
ENCODING = "cp932"
MAN_YEN = 10_000
FILE_KIND_CSV = 1
FILE_KIND_EXCEL = 0


class TableKind(StrEnum):
    INCOME_DIST_TS = "income_dist_ts"  # 世帯数の相対度数分布，年次・所得金額階級別 (%)
    WORKERS_MARITAL = (
        "workers_marital_income"  # 有業人員，配偶者の有無・性・所得金額階級別 (per 100k)
    )
    HH_TYPE = "hh_type_income"  # 世帯数，世帯類型・所得金額階級別 (per 10k)
    SHUGYO_MARITAL_AGE_INCOME = (
        "shugyo_marital_age_income"  # 有業者数，男女・配偶関係・年齢・所得別 (persons, xlsx)
    )
    MARITAL_EMPLOYMENT = (
        "marital_employment"  # H10: 有業者数，男女・配偶関係・年齢・雇用形態別 (persons)
    )
    MARITAL_NOT_EMPLOYED = "marital_not_employed"  # H10: 無業者数，男女・配偶関係・年齢別 (persons)


_SHUGYO_KINDS = frozenset(
    {
        TableKind.SHUGYO_MARITAL_AGE_INCOME,
        TableKind.MARITAL_EMPLOYMENT,
        TableKind.MARITAL_NOT_EMPLOYED,
    }
)


class Layout(StrEnum):
    """Physical layout of a 就業構造基本調査 workbook (the survey changed exports twice)."""

    TIDY = "tidy"  # 2022: one dimension-header row (階層レベル columns), item row above it
    TIDY_JE = "tidy_je"  # 2017: as TIDY plus row numbers / J-E flags and English dimension columns
    WIDE_XLS = "wide_xls"  # 2012 / 2007 .xls: one sheet per panel, value groups across columns


@dataclass(frozen=True)
class Table:
    key: str
    stat_inf_id: str
    kind: TableKind
    survey_year: int
    population: str | None = None  # INCOME_DIST_TS only: "all" | "with_children"
    file_kind: int = FILE_KIND_CSV
    layout: Layout = Layout.TIDY

    @property
    def raw_name(self) -> str:
        if self.file_kind == FILE_KIND_CSV:
            ext = "csv"
        else:
            ext = "xls" if self.layout is Layout.WIDE_XLS else "xlsx"
        return f"{self.key}.{ext}"

    @property
    def source(self) -> str:
        return SOURCE_SHUGYO if self.kind in _SHUGYO_KINDS else SOURCE

    @property
    def url(self) -> str:
        return file_download_url(self.stat_inf_id, file_kind=self.file_kind)


# 大規模調査年 (every 3 years) carry the 所得票 cross tables. 年次推移 tables are taken from the
# latest wave only (they restate 1985- in one file). statInfIds are stable per published table.
TABLES: tuple[Table, ...] = (
    Table("hh_income_dist_ts", "000040473361", TableKind.INCOME_DIST_TS, 2025, "all"),
    Table(
        "children_hh_income_dist_ts",
        "000040473376",
        TableKind.INCOME_DIST_TS,
        2025,
        "with_children",
    ),
    Table("workers_marital_income_2013", "000026222087", TableKind.WORKERS_MARITAL, 2013),
    Table("workers_marital_income_2016", "000031734158", TableKind.WORKERS_MARITAL, 2016),
    Table("workers_marital_income_2019", "000031957928", TableKind.WORKERS_MARITAL, 2019),
    Table("workers_marital_income_2022", "000040076501", TableKind.WORKERS_MARITAL, 2022),
    Table("workers_marital_income_2025", "000040473461", TableKind.WORKERS_MARITAL, 2025),
    Table("hh_type_income_2013", "000026222010", TableKind.HH_TYPE, 2013),
    Table("hh_type_income_2016", "000031734081", TableKind.HH_TYPE, 2016),
    Table("hh_type_income_2019", "000031957851", TableKind.HH_TYPE, 2019),
    Table("hh_type_income_2022", "000040076424", TableKind.HH_TYPE, 2022),
    Table("hh_type_income_2025", "000040473384", TableKind.HH_TYPE, 2025),
    # 就業構造基本調査 令和4年 全国編 第40表 (Excel only). No equivalent 配偶関係×年齢×所得 table
    # for 有業者 exists in the 2017 / 2012 全国編 (checked 2026-10-04), so this is a single wave.
    Table(
        "shugyo_marital_age_income_2022",
        "000040077301",
        TableKind.SHUGYO_MARITAL_AGE_INCOME,
        2022,
        file_kind=FILE_KIND_EXCEL,
    ),
)


def file_download_url(stat_inf_id: str, *, file_kind: int = FILE_KIND_CSV) -> str:
    """fileKind=1 is CSV, fileKind=0 Excel. The 国民生活基礎調査 tables publish CSV only, the
    就業構造基本調査 table Excel only (the other kind returns 404)."""
    if not re.fullmatch(r"\d{12}", stat_inf_id):
        msg = f"statInfId must be 12 digits: {stat_inf_id!r}"
        raise ValueError(msg)
    return f"{BASE}?statInfId={stat_inf_id}&fileKind={file_kind}"


# ---------------------------------------------------------------- shared parsing helpers


def _norm(cell: str) -> str:
    """NFKC (full-width digits/tilde -> ASCII), drop all whitespace incl. U+3000."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", cell))


def _rows(payload: bytes) -> list[list[str]]:
    try:
        text = payload.decode(ENCODING)
    except UnicodeDecodeError as e:
        msg = f"e-Stat CSV is not {ENCODING}"
        raise ValueError(msg) from e
    return [list(r) for r in csv.reader(io.StringIO(text))]


def _cell(row: list[str], i: int) -> str:
    return row[i] if i < len(row) else ""


def _number(cell: str) -> float | None:
    """e-Stat markers: '-' = none (0); '…' not surveyed, '・' not applicable, '' -> None."""
    c = _norm(cell)
    if c == "-":
        return 0.0
    if c in {"", "…", "・", "...", "x", "X"}:
        return None
    try:
        return float(c.replace(",", ""))
    except ValueError as e:
        msg = f"unexpected numeric cell {cell!r}"
        raise ValueError(msg) from e


class IncomeClass(BaseModel):
    """One 所得金額階級 row label. Bounds in yen; both None for 'total' and 'none'."""

    model_config = ConfigDict(frozen=True)
    code: str  # "total" | "none" | "<lower>-<upper>" | "<lower>-" (open top), in 万円
    lower_yen: int | None
    upper_yen: int | None


_RE_UNDER = re.compile(r"^(\d+)万円未満$")
_RE_RANGE = re.compile(r"^(\d+)[~〜-](\d+)(万円)?$")
_RE_OVER = re.compile(r"^(\d+)万円以上$")


def parse_income_class(label: str) -> IncomeClass | None:
    """Return None when *label* is not an income-class label (e.g. a block title)."""
    c = _norm(label)
    if c in {"総数", "合計"}:
        return IncomeClass(code="total", lower_yen=None, upper_yen=None)
    if c == "所得なし":
        return IncomeClass(code="none", lower_yen=None, upper_yen=None)
    if m := _RE_UNDER.match(c):
        hi = int(m.group(1))
        return IncomeClass(code=f"0-{hi}", lower_yen=0, upper_yen=hi * MAN_YEN)
    if m := _RE_RANGE.match(c):
        lo, hi = int(m.group(1)), int(m.group(2))
        if hi <= lo:
            msg = f"income class upper <= lower: {label!r}"
            raise ValueError(msg)
        return IncomeClass(code=f"{lo}-{hi}", lower_yen=lo * MAN_YEN, upper_yen=hi * MAN_YEN)
    if m := _RE_OVER.match(c):
        lo = int(m.group(1))
        return IncomeClass(code=f"{lo}-", lower_yen=lo * MAN_YEN, upper_yen=None)
    return None


def _find_header(rows: list[list[str]], startswith: str) -> int:
    for i, r in enumerate(rows):
        if _norm(_cell(r, 0)).startswith(startswith):
            return i
    msg = f"header row starting with {startswith!r} not found"
    raise ValueError(msg)


def _check_title(rows: list[list[str]], *must_contain: str) -> None:
    head = _norm("".join("".join(r) for r in rows[:3]))
    for s in must_contain:
        if _norm(s) not in head:
            msg = f"table title does not mention {s!r}; wrong table?"
            raise ValueError(msg)


# ---------------------------------------------------------------- 年次・所得金額階級別 (時系列)


class IncomeDistRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    population: str
    year: int  # income reference year (the survey is conducted the following year)
    income_class: IncomeClass
    share_pct: float | None


_RE_YEAR = re.compile(r"^(\d{4})")


def parse_income_dist_ts(payload: bytes, *, population: str) -> list[IncomeDistRow]:
    rows = _rows(payload)
    _check_title(rows, "相対度数分布", "年次・所得金額階級別")
    h = _find_header(rows, "所得金額階級")
    years: list[tuple[int, int]] = []
    for j, cell in enumerate(rows[h][1:], start=1):
        if m := _RE_YEAR.match(_norm(cell)):
            years.append((j, int(m.group(1))))
    if len(years) < 2 or len({y for _, y in years}) != len(years):
        msg = "year header missing or duplicated"
        raise ValueError(msg)
    out: list[IncomeDistRow] = []
    in_block = False
    for r in rows[h + 1 :]:
        label = _norm(_cell(r, 0))
        if label == "相対度数分布":
            in_block = True
            continue
        if label == "累積度数分布":
            break
        if not in_block or not label:
            continue
        ic = parse_income_class(label)
        if ic is None:
            msg = f"unexpected row label in 相対度数分布 block: {label!r}"
            raise ValueError(msg)
        if ic.code == "total":
            continue
        for j, y in years:
            out.append(
                IncomeDistRow(
                    population=population, year=y, income_class=ic, share_pct=_number(_cell(r, j))
                )
            )
    if not out:
        msg = "no 相対度数分布 rows parsed"
        raise ValueError(msg)
    return out


# ------------------------------------------------ 有業人員，配偶者の有無・性・所得金額階級別


class WorkersMaritalRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    marital: str  # "total" | "married" | "unmarried"
    sex: str  # "total" | "male" | "female"
    income_class: IncomeClass
    workers_per_100k: float | None  # 総数 column (all 勤めか自営かの別)


_MARITAL = {"総数": "total", "配偶者あり": "married", "配偶者なし": "unmarried"}
_SEX = {"男": "male", "女": "female"}


def parse_workers_marital(payload: bytes) -> list[WorkersMaritalRow]:
    rows = _rows(payload)
    _check_title(rows, "有業人員", "配偶者の有無・性・所得金額階級別")
    h = _find_header(rows, "配偶者の有無")
    if _norm(_cell(rows[h], 3)) != "総数":
        msg = "expected 総数 as the 4th column"
        raise ValueError(msg)
    out: list[WorkersMaritalRow] = []
    marital: str | None = None
    sex = "total"
    for r in rows[h + 1 :]:
        c0, c1, c2 = (_norm(_cell(r, i)) for i in range(3))
        if c0:
            if c0 not in _MARITAL:
                msg = f"unexpected 配偶者の有無 label {c0!r}"
                raise ValueError(msg)
            marital, sex = _MARITAL[c0], "total"
            label = "総数"
        elif c1:
            if c1 not in _SEX:
                msg = f"unexpected 性 label {c1!r}"
                raise ValueError(msg)
            sex = _SEX[c1]
            label = "総数"
        elif c2:
            label = c2
        else:
            continue
        if marital is None:
            msg = "income rows before any 配偶者の有無 block"
            raise ValueError(msg)
        ic = parse_income_class(label)
        if ic is None:
            msg = f"unexpected income label {label!r}"
            raise ValueError(msg)
        out.append(
            WorkersMaritalRow(
                marital=marital, sex=sex, income_class=ic, workers_per_100k=_number(_cell(r, 3))
            )
        )
    keys = {(o.marital, o.sex) for o in out}
    if keys != {(m, s) for m in _MARITAL.values() for s in ("total", "male", "female")}:
        msg = f"incomplete 配偶者の有無×性 blocks: {sorted(keys)}"
        raise ValueError(msg)
    return out


# ---------------------------------------------------------------- 世帯数，世帯類型・所得金額階級別


class HouseholdTypeRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    income_class: IncomeClass
    households_per_10k: float | None  # 総数
    with_children_per_10k: float | None  # （再掲）児童のいる世帯
    single_mother_per_10k: float | None  # 母子世帯


def _joined_headers(rows: list[list[str]], h: int) -> list[str]:
    """Join the multi-row header (from row *h* up to the first data row) column-wise."""
    end = h + 1
    while end < len(rows) and parse_income_class(_cell(rows[end], 0)) is None:
        end += 1
    width = max(len(r) for r in rows[h:end])
    return ["".join(_norm(_cell(r, j)) for r in rows[h:end]) for j in range(width)]


def _col(headers: list[str], contains: str, *, exclude: str = "") -> int:
    hits = [j for j, t in enumerate(headers) if contains in t and (not exclude or exclude not in t)]
    if len(hits) != 1:
        msg = f"column {contains!r} not uniquely found: {hits}"
        raise ValueError(msg)
    return hits[0]


def parse_hh_type(payload: bytes) -> list[HouseholdTypeRow]:
    rows = _rows(payload)
    _check_title(rows, "世帯類型", "所得金額階級別")
    h = _find_header(rows, "所得金額階級")
    headers = _joined_headers(rows, h)
    j_total = _col(headers, "総数")
    j_children = _col(headers, "児童のいる世帯", exclude="65歳")
    j_single_mother = _col(headers, "母子世帯")
    out: list[HouseholdTypeRow] = []
    for r in rows[h + 1 :]:
        label = _norm(_cell(r, 0))
        if not label:
            continue
        ic = parse_income_class(label)
        if ic is None:
            msg = f"unexpected income label {label!r}"
            raise ValueError(msg)
        out.append(
            HouseholdTypeRow(
                income_class=ic,
                households_per_10k=_number(_cell(r, j_total)),
                with_children_per_10k=_number(_cell(r, j_children)),
                single_mother_per_10k=_number(_cell(r, j_single_mother)),
            )
        )
    if not any(o.income_class.code == "total" for o in out) or len(out) < 3:
        msg = "household-type table has no 総数 row or too few classes"
        raise ValueError(msg)
    return out


# ---------------------------------------------------------------- staged row builders (dicts)


def _class_cols(ic: IncomeClass) -> dict[str, object]:
    return {
        "income_class": ic.code,
        "income_class_lower_yen": ic.lower_yen,
        "income_class_upper_yen": ic.upper_yen,
    }


def _common(table: Table, year: int) -> dict[str, object]:
    return {
        "survey_year": table.survey_year,
        "year": year,
        "source": SOURCE,
        "stat_inf_id": table.stat_inf_id,
    }


def income_dist_rows(payload: bytes, table: Table) -> list[dict[str, object]]:
    if table.kind is not TableKind.INCOME_DIST_TS or table.population is None:
        msg = f"{table.key} is not an income-distribution time series"
        raise ValueError(msg)
    return [
        {
            "population": r.population,
            **_common(table, r.year),
            **_class_cols(r.income_class),
            "share_pct": r.share_pct,
        }
        for r in parse_income_dist_ts(payload, population=table.population)
    ]


def workers_marital_rows(payload: bytes, table: Table) -> list[dict[str, object]]:
    if table.kind is not TableKind.WORKERS_MARITAL:
        msg = f"{table.key} is not a workers×marital table"
        raise ValueError(msg)
    return [
        {
            **_common(table, table.survey_year - 1),
            "marital": r.marital,
            "sex": r.sex,
            **_class_cols(r.income_class),
            "workers_per_100k": r.workers_per_100k,
        }
        for r in parse_workers_marital(payload)
    ]


def hh_type_rows(payload: bytes, table: Table) -> list[dict[str, object]]:
    if table.kind is not TableKind.HH_TYPE:
        msg = f"{table.key} is not a household-type table"
        raise ValueError(msg)
    return [
        {
            **_common(table, table.survey_year - 1),
            **_class_cols(r.income_class),
            "households_per_10k": r.households_per_10k,
            "with_children_per_10k": r.with_children_per_10k,
            "single_mother_per_10k": r.single_mother_per_10k,
        }
        for r in parse_hh_type(payload)
    ]


def tables_of(kind: TableKind) -> Iterator[Table]:
    return (t for t in TABLES if t.kind is kind)


# ---------------------------- 就業構造基本調査 第40表 (xlsx): 男女×配偶関係×年齢×所得, 有業者

_XML_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_SHEET = "xl/worksheets/sheet1.xml"
_SHARED = "xl/sharedStrings.xml"


def _col_index(ref: str) -> int:
    """'A1' -> 1, 'AA3' -> 27 (1-based)."""
    m = re.match(r"[A-Z]+", ref)
    if m is None:
        msg = f"bad cell reference {ref!r}"
        raise ValueError(msg)
    n = 0
    for ch in m.group(0):
        n = n * 26 + ord(ch) - 64
    return n


_WORKBOOK = "xl/workbook.xml"
_WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
_XML_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_XML_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _sheet_path(z: zipfile.ZipFile, name: str) -> str:
    """Zip member of the worksheet titled *name* (workbook.xml -> rels); ``ValueError`` if none."""
    wb = ET.fromstring(z.read(_WORKBOOK))  # noqa: S314 - trusted public file, stdlib
    rels = {
        r.get("Id"): r.get("Target") or ""
        for r in ET.fromstring(z.read(_WORKBOOK_RELS)).iter(f"{_XML_PKG_REL}Relationship")  # noqa: S314
    }
    for s in wb.iter(f"{_XML_MAIN}sheet"):
        if s.get("name") == name:
            target = rels.get(s.get(f"{_XML_REL}id"), "")
            if target.startswith("/"):
                return target[1:]
            return target if target.startswith("xl/") else "xl/" + target
    msg = f"xlsx has no worksheet named {name!r}"
    raise ValueError(msg)


def _shared_text(si: ET.Element) -> str:
    """Text of one shared string: plain <t> and rich runs <r><t>, without phonetic <rPh> runs."""
    out: list[str] = []
    for child in si:
        if child.tag == f"{_XML_MAIN}t":
            out.append(child.text or "")
        elif child.tag == f"{_XML_MAIN}r":
            out.extend(t.text or "" for t in child.iter(f"{_XML_MAIN}t"))
    return "".join(out)


def xlsx_rows(payload: bytes, sheet: str | None = None) -> list[dict[int, str]]:
    """One worksheet of an xlsx as a list of {1-based column: text}. Standard library only.

    *sheet* is the worksheet title (``None`` = the first worksheet). Handles shared strings
    (``t="s"``), inline strings (``t="inlineStr"``) and plain values. Empty cells are absent
    from the dict. Raises ``ValueError`` when *payload* is not an xlsx or the sheet is missing.
    """
    try:
        z = zipfile.ZipFile(io.BytesIO(payload))
        names = set(z.namelist())
        path = _SHEET if sheet is None else _sheet_path(z, sheet)
        if path not in names:
            msg = (
                "xlsx has no first worksheet" if sheet is None else f"xlsx sheet {sheet!r} missing"
            )
            raise ValueError(msg)
        shared: list[str] = []
        if _SHARED in names:
            shared = [
                _shared_text(si)
                for si in ET.fromstring(z.read(_SHARED))  # noqa: S314 - trusted public file, stdlib
            ]
        sheet_xml = ET.fromstring(z.read(path))  # noqa: S314
    except (zipfile.BadZipFile, ET.ParseError, KeyError) as e:
        msg = "payload is not an xlsx workbook"
        raise ValueError(msg) from e
    data = sheet_xml.find(f"{_XML_MAIN}sheetData")
    if data is None:
        msg = "xlsx worksheet has no sheetData"
        raise ValueError(msg)
    out: list[dict[int, str]] = []
    for row in data:
        cells: dict[int, str] = {}
        for c in row:
            ref = c.get("r")
            if ref is None:
                continue
            kind = c.get("t")
            if kind == "inlineStr":
                text = "".join(t.text or "" for t in c.iter(f"{_XML_MAIN}t"))
            else:
                v = c.find(f"{_XML_MAIN}v")
                if v is None or v.text is None:
                    continue
                text = shared[int(v.text)] if kind == "s" else v.text
            cells[_col_index(ref)] = text
        out.append(cells)
    return out


class AgeClass(BaseModel):
    """One 年齢 row label. ``upper`` is exclusive (15～19歳 -> 15, 20); both None for 'total'."""

    model_config = ConfigDict(frozen=True)
    code: str  # "total" | "<lower>-<upper>" | "<lower>-" (open top)
    lower: int | None
    upper: int | None


_RE_CODE_PREFIX = re.compile(r"^\d+_")
_RE_FOOTNOTE = re.compile(r"\d\)")
_RE_AGE_RANGE = re.compile(r"^(\d+)[~〜-](\d+)歳?$")
_RE_AGE_OVER = re.compile(r"^(\d+)歳以上$")
_RE_SHUGYO_RANGE = re.compile(r"^(\d+)[~〜-](\d+)万円$")


def _strip_code(label: str) -> str:
    """'03_25～29歳' -> '25～29歳' (e-Stat DB-style labels carry a numeric code prefix)."""
    return _RE_CODE_PREFIX.sub("", _norm(label))


def parse_age_class(label: str) -> AgeClass | None:
    """'03_25～29歳', '20～24' (wide-xls column headers) and '15 ～ 19 歳 1)' (footnote marker)
    all parse; education or size labels return None."""
    c = _RE_FOOTNOTE.sub("", _strip_code(label))
    if c in {"総数", "合計"}:
        return AgeClass(code="total", lower=None, upper=None)
    if m := _RE_AGE_RANGE.match(c):
        lo, hi = int(m.group(1)), int(m.group(2))
        if hi < lo:
            msg = f"age class upper < lower: {label!r}"
            raise ValueError(msg)
        return AgeClass(code=f"{lo}-{hi}", lower=lo, upper=hi + 1)
    if m := _RE_AGE_OVER.match(c):
        lo = int(m.group(1))
        return AgeClass(code=f"{lo}-", lower=lo, upper=None)
    return None


def parse_income_class_shugyo(label: str) -> IncomeClass | None:
    """就業構造基本調査 labels: '02_50～99万円' means 50 <= income < 100 万円, so the upper bound
    is *hi + 1* (the 国民生活基礎調査 labels '50～100' already carry the exclusive bound)."""
    c = _strip_code(label)
    if m := _RE_SHUGYO_RANGE.match(c):
        lo, hi = int(m.group(1)), int(m.group(2)) + 1
        if hi <= lo:
            msg = f"income class upper <= lower: {label!r}"
            raise ValueError(msg)
        return IncomeClass(code=f"{lo}-{hi}", lower_yen=lo * MAN_YEN, upper_yen=hi * MAN_YEN)
    return parse_income_class(c)


class ShugyoRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    sex: str  # "total" | "male" | "female"
    marital: str  # "total" | "never_married" (the table publishes 総数 and うち未婚 only)
    age_class: AgeClass
    income_class: IncomeClass
    persons: float | None  # 教育 総数 column, persons (sample-weighted estimate)


_SHUGYO_SEX = {"総数": "total", "男": "male", "女": "female"}
_SHUGYO_MARITAL = {"総数": "total", "うち未婚": "never_married"}
_SHUGYO_HEADER = {
    1: "階層レベル",
    2: "地域区分",
    4: "男女",
    6: "配偶関係",
    8: "年齢",
    10: "従業上の地位・雇用形態・起業の有無",
    12: "所得（主な仕事からの年間収入・収益）",
}
_C_REGION, _C_SEX, _C_MARITAL, _C_AGE, _C_STATUS, _C_INCOME, _C_VALUE = 2, 4, 6, 8, 10, 12, 13


def parse_shugyo_marital_age_income(payload: bytes) -> list[ShugyoRow]:
    """第40表 (全国): keep 従業上の地位 = 総数 and the 教育 = 総数 column; every
    男女×配偶関係×年齢×所得 cell becomes one row. Fails closed on title / header / label
    surprises."""
    rows = xlsx_rows(payload)
    title = _norm("".join(c for r in rows[:3] for c in r.values()))
    for must in ("就業構造基本調査", "配偶関係、年齢", "所得", "有業者"):
        if _norm(must) not in title:
            msg = f"table title does not mention {must!r}; wrong table?"
            raise ValueError(msg)
    header = next(
        (
            i
            for i, r in enumerate(rows)
            if all(_norm(r.get(j, "")) == _norm(v) for j, v in _SHUGYO_HEADER.items())
        ),
        None,
    )
    if header is None:
        msg = "dimension header row (階層レベル/地域区分/男女/配偶関係/年齢/.../所得) not found"
        raise ValueError(msg)
    item_rows = [r for r in rows[:header] if _norm(r.get(_C_INCOME, "")) in {"事項名", "項目名"}]
    if [_norm(r.get(_C_VALUE, "")) for r in item_rows] != ["教育", "0_総数"]:
        msg = "expected the first value column to be 教育 = 0_総数"
        raise ValueError(msg)
    out: list[ShugyoRow] = []
    for r in rows[header + 1 :]:
        if _norm(r.get(_C_REGION, "")) != "00_全国":
            continue
        if _strip_code(r.get(_C_STATUS, "")) != "総数":
            continue
        sex, marital = _strip_code(r.get(_C_SEX, "")), _strip_code(r.get(_C_MARITAL, ""))
        if sex not in _SHUGYO_SEX or marital not in _SHUGYO_MARITAL:
            msg = f"unexpected 男女/配偶関係 labels {sex!r}/{marital!r}"
            raise ValueError(msg)
        age = parse_age_class(r.get(_C_AGE, ""))
        ic = parse_income_class_shugyo(r.get(_C_INCOME, ""))
        if age is None or ic is None:
            msg = f"unexpected 年齢/所得 labels {r.get(_C_AGE)!r}/{r.get(_C_INCOME)!r}"
            raise ValueError(msg)
        out.append(
            ShugyoRow(
                sex=_SHUGYO_SEX[sex],
                marital=_SHUGYO_MARITAL[marital],
                age_class=age,
                income_class=ic,
                persons=_number(r.get(_C_VALUE, "")),
            )
        )
    if {o.marital for o in out} != set(_SHUGYO_MARITAL.values()):
        msg = "incomplete 配偶関係 blocks (need 総数 and うち未婚)"
        raise ValueError(msg)
    if not any(o.age_class.code == "total" for o in out) or not any(
        o.income_class.code == "total" for o in out
    ):
        msg = "no 総数 age or income rows parsed"
        raise ValueError(msg)
    return out


def shugyo_marital_age_income_rows(payload: bytes, table: Table) -> list[dict[str, object]]:
    """Staged rows. ``year`` is the survey year: the 所得 item covers the 12 months before the
    survey date (2021-10 to 2022-09 for the 2022 survey), not a calendar year."""
    if table.kind is not TableKind.SHUGYO_MARITAL_AGE_INCOME:
        msg = f"{table.key} is not a 就業構造基本調査 marital×age×income table"
        raise ValueError(msg)
    return [
        {
            "survey_year": table.survey_year,
            "year": table.survey_year,
            "source": table.source,
            "stat_inf_id": table.stat_inf_id,
            "sex": r.sex,
            "marital": r.marital,
            "age_class": r.age_class.code,
            "age_lower": r.age_class.lower,
            "age_upper": r.age_class.upper,
            **_class_cols(r.income_class),
            "persons": r.persons,
        }
        for r in parse_shugyo_marital_age_income(payload)
    ]


# ------------------ H10: 就業構造基本調査 雇用形態×配偶関係×年齢×性, four waves, three layouts
#
# Two tables per wave: 有業者 by 従業上の地位・雇用形態 (第16表 2022/2017/2012, 第14表 2007) and
# 無業者 (第118表 2022, 第99表 2017, 第93表 2012, 第86表 2007), both by 男女 × 配偶関係 (総数 /
# うち未婚) × 年齢 (5-year classes). The 15 歳以上人口 denominator is 有業者 + 無業者
# (``total_pop``): the 第1-1表 配偶関係 columns only cover one-person-household heads, so they
# are not used. 教育 / 従業者規模 / 就業希望 / 前職 are kept at 総数 only.

EMPLOYMENT_ORDER: tuple[str, ...] = (
    "total_pop",  # 有業者 + 無業者 (derived)
    "employed",  # 有業者 総数
    "employee",  # うち雇用者 (会社などの役員を含む)
    "regular",  # うち正規の職員・従業員
    "nonregular",  # うち非正規の職員・従業員 (not published in the 2007 table)
    "part_time",
    "arbeit",
    "dispatched",
    "contract",
    "not_employed",  # 無業者
)
_EMPLOYMENT_ITEMS: dict[str, str | None] = {
    "総数": "employed",
    "うち雇用者": "employee",
    "うち雇用者総数": "employee",  # 2007 wide header: うち雇用者 over a 総数 sub-header
    "うち起業者": None,  # 起業の有無 is orthogonal to 雇用形態; dropped
    "うち正規の職員・従業員": "regular",
    "うち非正規の職員・従業員": "nonregular",
    "うちパート": "part_time",
    "うちアルバイト": "arbeit",
    "うち労働者派遣事業所の派遣社員": "dispatched",
    "うち労働派遣事業所の派遣社員": "dispatched",  # 2007 spelling
    "うち契約社員": "contract",
}
_NOT_EMPLOYED_ITEMS: dict[str, str | None] = {
    "総数": "not_employed",
    "家事をしている者": None,
    "通学している者": None,
    "その他": None,
}
_SEX_ORDER: tuple[str, ...] = ("total", "male", "female")
_MARITAL_ORDER: tuple[str, ...] = ("total", "never_married")
_AGE_CODES: tuple[str, ...] = ("total", *(f"{lo}-{lo + 4}" for lo in range(15, 85, 5)), "85-")
_TOLERANCE = 0.005  # relative; plus 100 persons per summed cell (cells are rounded to 100)
_ROUNDING = 100.0
_RE_ASCII = re.compile(r"[A-Za-z(),.'/-]+")
_TITLE_MUSTS: dict[TableKind, tuple[str, str]] = {
    TableKind.MARITAL_EMPLOYMENT: ("配偶関係", "雇用形態"),
    TableKind.MARITAL_NOT_EMPLOYED: ("配偶関係", "就業希望"),
}


def _h10(key: str, stat_inf_id: str, kind: TableKind, year: int, layout: Layout) -> Table:
    return Table(key, stat_inf_id, kind, year, file_kind=FILE_KIND_EXCEL, layout=layout)


MARITAL_EMPLOYMENT_TABLES: tuple[Table, ...] = (
    _h10("shugyo_employment_2022", "000040077274", TableKind.MARITAL_EMPLOYMENT, 2022, Layout.TIDY),
    _h10(
        "shugyo_not_employed_2022",
        "000040077389",
        TableKind.MARITAL_NOT_EMPLOYED,
        2022,
        Layout.TIDY,
    ),
    _h10(
        "shugyo_employment_2017", "000031738323", TableKind.MARITAL_EMPLOYMENT, 2017, Layout.TIDY_JE
    ),
    _h10(
        "shugyo_not_employed_2017",
        "000031729447",
        TableKind.MARITAL_NOT_EMPLOYED,
        2017,
        Layout.TIDY_JE,
    ),
    _h10(
        "shugyo_employment_2012",
        "000021291492",
        TableKind.MARITAL_EMPLOYMENT,
        2012,
        Layout.WIDE_XLS,
    ),
    _h10(
        "shugyo_not_employed_2012",
        "000021291719",
        TableKind.MARITAL_NOT_EMPLOYED,
        2012,
        Layout.WIDE_XLS,
    ),
    _h10(
        "shugyo_employment_2007",
        "000001234529",
        TableKind.MARITAL_EMPLOYMENT,
        2007,
        Layout.WIDE_XLS,
    ),
    _h10(
        "shugyo_not_employed_2007",
        "000001234601",
        TableKind.MARITAL_NOT_EMPLOYED,
        2007,
        Layout.WIDE_XLS,
    ),
)


class MaritalRow(BaseModel):
    model_config = ConfigDict(frozen=True)
    sex: str  # "total" | "male" | "female"
    marital: str  # "total" | "never_married"
    age_class: AgeClass
    employment: str  # one of EMPLOYMENT_ORDER except total_pop
    persons: float | None


def _label(cell: str) -> str:
    """NFKC, no whitespace, no DB code prefix, no footnote markers ('うち雇用者 3)')."""
    return _RE_FOOTNOTE.sub("", _strip_code(cell))


def _jp_label(cell: str) -> str:
    """_label without the English fragments the wide .xls headers interleave."""
    return _RE_ASCII.sub("", _label(cell))


def _items_of(kind: TableKind) -> dict[str, str | None]:
    return _EMPLOYMENT_ITEMS if kind is TableKind.MARITAL_EMPLOYMENT else _NOT_EMPLOYED_ITEMS


def _employment_of(label: str, kind: TableKind) -> str | None:
    items = _items_of(kind)
    if label not in items:
        msg = f"unexpected employment item {label!r}"
        raise ValueError(msg)
    return items[label]


def _check_h10_title(rows: Sequence[dict[int, str]], kind: TableKind) -> None:
    head = _norm("".join(c for r in rows[:8] for c in r.values()))
    for must in _TITLE_MUSTS[kind]:
        if must not in head:
            msg = f"table title does not mention {must!r}; wrong table?"
            raise ValueError(msg)


def _check_panels(rows: Sequence[MaritalRow]) -> None:
    """Every (sex, marital, employment) must carry the 16 age classes exactly once."""
    seen: dict[tuple[str, str, str], list[str]] = {}
    for r in rows:
        seen.setdefault((r.sex, r.marital, r.employment), []).append(r.age_class.code)
    panels = {(s, m) for s, m, _ in seen}
    if panels != {(s, m) for s in _SEX_ORDER for m in _MARITAL_ORDER}:
        msg = f"incomplete 男女×配偶関係 panels: {sorted(panels)}"
        raise ValueError(msg)
    for key, codes in seen.items():
        if sorted(codes) != sorted(_AGE_CODES):
            msg = f"age classes incomplete or duplicated for {key}: {sorted(codes)}"
            raise ValueError(msg)


# ---------------------------------------------------------------- tidy (2022) / tidy J-E (2017)

_TIDY_DIMS = {"男女": "sex", "配偶関係": "marital", "年齢": "age", "地域区分": "region"}
_TIDY_FILTER_DIMS = frozenset(
    {"教育", "従業者規模", "就業希望の有無・求職活動の有無", "前職の有無・離職期間"}
)
_RE_ITEM = re.compile(r"^\d+_")


def _tidy_header(rows: Sequence[dict[int, str]]) -> tuple[int, dict[str, int], list[int], int]:
    """(header row index, role -> column, filter columns, first value column)."""
    for i, r in enumerate(rows):
        texts = {c: _norm(v) for c, v in r.items()}
        if not {"男女", "配偶関係", "年齢"} <= set(texts.values()):
            continue
        roles: dict[str, int] = {}
        filters: list[int] = []
        first_value: int | None = None
        for c, t in sorted(texts.items()):
            if t in _TIDY_DIMS:
                roles.setdefault(_TIDY_DIMS[t], c)
            elif t in _TIDY_FILTER_DIMS:
                filters.append(c)
            elif not t:
                first_value = c if first_value is None else first_value
            elif t == "階層レベル" or t.isascii():
                continue
            else:
                msg = f"unknown dimension column {t!r}"
                raise ValueError(msg)
        if "region" not in roles:
            msg = "地域区分 column missing from the dimension header"
            raise ValueError(msg)
        if first_value is None:
            first_value = max(texts) + 1
        return i, roles, filters, first_value
    msg = "dimension header row (男女/配偶関係/年齢) not found"
    raise ValueError(msg)


def _tidy_items(
    rows: Sequence[dict[int, str]], header: int, first_value: int, kind: TableKind
) -> dict[int, str]:
    """Value column -> employment code, from the 項目名 row above the header."""
    for i in range(header - 1, -1, -1):
        if _RE_ITEM.match(_norm(rows[i].get(first_value, ""))):
            out: dict[int, str] = {}
            for c, v in rows[i].items():
                if c >= first_value and _RE_ITEM.match(_norm(v)):
                    emp = _employment_of(_label(v), kind)
                    if emp is not None:
                        out[c] = emp
            if not out:
                msg = "item row carries no usable column"
                raise ValueError(msg)
            return out
    msg = "item row (項目名: 0_総数 ...) not found above the dimension header"
    raise ValueError(msg)


def _parse_tidy(payload: bytes, table: Table) -> list[MaritalRow]:
    rows = xlsx_rows(payload)
    _check_h10_title(rows, table.kind)
    header, roles, filters, first_value = _tidy_header(rows)
    items = _tidy_items(rows, header, first_value, table.kind)
    out: list[MaritalRow] = []
    for r in rows[header + 1 :]:
        if _strip_code(r.get(roles["region"], "")) != "全国":
            continue
        if any(_strip_code(r.get(c, "")) != "総数" for c in filters):
            continue
        sex, marital = (
            _strip_code(r.get(roles["sex"], "")),
            _strip_code(r.get(roles["marital"], "")),
        )
        if sex not in _SHUGYO_SEX or marital not in _SHUGYO_MARITAL:
            msg = f"unexpected 男女/配偶関係 labels {sex!r}/{marital!r}"
            raise ValueError(msg)
        age = parse_age_class(r.get(roles["age"], ""))
        if age is None:
            msg = f"unexpected 年齢 label {r.get(roles['age'])!r}"
            raise ValueError(msg)
        out.extend(
            MaritalRow(
                sex=_SHUGYO_SEX[sex],
                marital=_SHUGYO_MARITAL[marital],
                age_class=age,
                employment=emp,
                persons=_number(r.get(c, "")),
            )
            for c, emp in items.items()
        )
    return out


# ---------------------------------------------------------------- wide .xls (2012 / 2007)


def xls_sheets(payload: bytes) -> list[tuple[str, list[dict[int, str]]]]:
    """Every worksheet of a legacy .xls as (name, rows of {1-based column: text}) via xlrd.

    Integral floats come back as integer text ('64420700'), other cells as their text; empty
    cells are absent. ``ValueError`` when *payload* is not a BIFF workbook.
    """
    try:
        book = xlrd.open_workbook(file_contents=payload)
    except XLRDError as e:
        msg = "payload is not an xls workbook"
        raise ValueError(msg) from e
    out: list[tuple[str, list[dict[int, str]]]] = []
    for sheet in book.sheets():
        rows: list[dict[int, str]] = []
        for r in range(sheet.nrows):
            cells: dict[int, str] = {}
            for c in range(sheet.ncols):
                v = sheet.cell_value(r, c)
                if v == "" or v is None:
                    continue
                if isinstance(v, float):
                    cells[c + 1] = str(int(v)) if v.is_integer() else repr(v)
                else:
                    cells[c + 1] = str(v)
            rows.append(cells)
        out.append((sheet.name, rows))
    return out


_C_LABEL = 8  # row labels live in column H of every wide sheet
_RE_PANEL = re.compile(r"^(総数|男|女)(総数|うち未婚)$")


def _wide_panel(rows: Sequence[dict[int, str]], header: int) -> tuple[str, str]:
    """(sex, marital) of one 第16表/第14表 sheet from the labels above the header."""
    parts = [
        t
        for r in rows[:header]
        if re.fullmatch(r"(総数|男|女|うち未婚)+", t := _jp_label(r.get(_C_LABEL, "")))
    ]
    m = _RE_PANEL.match("".join(parts))
    if m is None:
        msg = f"panel label (男女 × 配偶関係) not recognised: {parts}"
        raise ValueError(msg)
    return _SHUGYO_SEX[m.group(1)], _SHUGYO_MARITAL[m.group(2)]


def _wide_group_columns(
    rows: Sequence[dict[int, str]], header: int, label_start: int, kind: TableKind
) -> dict[int, str]:
    """Value column (従業者規模 = 総数 of each group) -> employment code.

    The group label is the Japanese text of the header rows over the group's column span
    (English fragments and footnotes dropped), which also absorbs the 2007 '総数' sub-header.
    """
    starts = sorted(c for c, v in rows[header].items() if _norm(v) == "総数")
    if not starts:
        msg = "従業者規模 header row has no 総数 column"
        raise ValueError(msg)
    out: dict[int, str] = {}
    for n, c in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else c + 14
        label = "".join(
            _jp_label(rows[r].get(k, "")) for r in range(label_start, header) for k in range(c, end)
        )
        emp = _employment_of(label, kind)
        if emp is not None:
            out[c] = emp
    return out


def _parse_wide_employment(payload: bytes, table: Table) -> list[MaritalRow]:
    out: list[MaritalRow] = []
    for _name, rows in xls_sheets(payload):
        _check_h10_title(rows, table.kind)
        header = next(
            (
                i
                for i, r in enumerate(rows)
                if _norm(r.get(10, "")) == "総数" and _norm(r.get(11, "")) == "1人"
            ),
            None,
        )
        label_start = next(
            (i for i, r in enumerate(rows) if "従業上の地位" in _norm(r.get(_C_LABEL, ""))), None
        )
        if header is None or label_start is None or label_start >= header:
            msg = "従業者規模 header row or 従業上の地位 label row not found"
            raise ValueError(msg)
        sex, marital = _wide_panel(rows, header)
        columns = _wide_group_columns(rows, header, label_start, table.kind)
        for r in rows[header + 1 :]:
            label = r.get(_C_LABEL, "")
            if not _norm(label):
                continue
            age = parse_age_class(label)
            if age is None:  # 教育 sub-rows under each age
                continue
            out.extend(
                MaritalRow(
                    sex=sex,
                    marital=marital,
                    age_class=age,
                    employment=emp,
                    persons=_number(r.get(c, "")),
                )
                for c, emp in columns.items()
            )
    return out


def _parse_wide_not_employed(payload: bytes, table: Table) -> list[MaritalRow]:
    """第93表 / 第86表: first sheet (就業状態 総数); 男女 blocks across columns, each with a
    配偶関係 うち未婚 sub-block except 総数 (both sexes), which is derived as male + female."""
    _name, rows = xls_sheets(payload)[0]
    _check_h10_title(rows, table.kind)
    header = next(
        (
            i
            for i, r in enumerate(rows)
            if {"男女", "配偶関係"} <= set(re.findall(r"男女|配偶関係", _norm(r.get(_C_LABEL, ""))))
        ),
        None,
    )
    if header is None:
        msg = "header row (男女 / 配偶関係 / 前職の有無) not found"
        raise ValueError(msg)
    if not any(_jp_label(r.get(_C_LABEL, "")) == "総数" for r in rows[:header]):
        msg = "first sheet is not the 就業状態 総数 panel"
        raise ValueError(msg)
    starts = {
        c: _SHUGYO_SEX[t]
        for c, v in rows[header].items()
        if c >= 10 and (t := _jp_label(v)) in _SHUGYO_SEX
    }
    if sorted(starts.values()) != sorted(_SEX_ORDER):
        msg = f"男女 blocks not found: {starts}"
        raise ValueError(msg)
    never = sorted(c for c, v in rows[header + 1].items() if _jp_label(v) == "うち未婚")
    columns: dict[tuple[str, str], int] = {}
    ordered = sorted(starts)
    for n, s in enumerate(ordered):
        end = ordered[n + 1] if n + 1 < len(ordered) else 10**6
        if not any(
            _jp_label(r.get(s, "")) == "総数" and _jp_label(r.get(s + 1, "")) == "前職あり"
            for r in rows[header + 1 : header + 6]
        ):
            msg = f"前職の有無 総数 column not found at column {s}"
            raise ValueError(msg)
        columns[(starts[s], "total")] = s
        hits = [c for c in never if s < c < end]
        if len(hits) == 1:
            columns[(starts[s], "never_married")] = hits[0]
        elif hits or starts[s] != "total":
            msg = f"うち未婚 block for {starts[s]} not found uniquely: {hits}"
            raise ValueError(msg)
    out: list[MaritalRow] = []
    started = False
    for r in rows[header + 1 :]:
        label = r.get(_C_LABEL, "")
        if not _norm(label):
            continue
        age = parse_age_class(label)
        if age is None:
            if started:
                break  # the next 就業希望 / 教育 block repeats the ages
            continue
        started = True
        values = {key: _number(r.get(c, "")) for key, c in columns.items()}
        m, f = values.get(("male", "never_married")), values.get(("female", "never_married"))
        values[("total", "never_married")] = None if m is None or f is None else m + f
        out.extend(
            MaritalRow(sex=s, marital=mar, age_class=age, employment="not_employed", persons=v)
            for (s, mar), v in values.items()
        )
    return out


# ---------------------------------------------------------------- dispatch, wave checks, mart


def parse_marital_employment(payload: bytes, table: Table) -> list[MaritalRow]:
    if table.kind not in (TableKind.MARITAL_EMPLOYMENT, TableKind.MARITAL_NOT_EMPLOYED):
        msg = f"{table.key} is not a 就業構造基本調査 marital×employment table"
        raise ValueError(msg)
    if table.layout is Layout.WIDE_XLS:
        rows = (
            _parse_wide_employment(payload, table)
            if table.kind is TableKind.MARITAL_EMPLOYMENT
            else _parse_wide_not_employed(payload, table)
        )
    else:
        rows = _parse_tidy(payload, table)
    _check_panels(rows)
    return rows


def _marital_dict(r: MaritalRow, table: Table) -> dict[str, object]:
    return {
        "survey_year": table.survey_year,
        "sex": r.sex,
        "marital": r.marital,
        "age_class": r.age_class.code,
        "age_lower": r.age_class.lower,
        "age_upper": r.age_class.upper,
        "employment": r.employment,
        "persons": r.persons,
        "source": table.source,
        "stat_inf_id": table.stat_inf_id,
    }


def marital_employment_rows(payload: bytes, table: Table) -> list[dict[str, object]]:
    """Staged rows of one table (survey year, sex, marital, age class, employment, persons)."""
    return [_marital_dict(r, table) for r in parse_marital_employment(payload, table)]


_Key = tuple[str, str, str, str]


def _wave_index(rows: Iterable[dict[str, object]]) -> dict[_Key, float | None]:
    by: dict[_Key, float | None] = {}
    for r in rows:
        key = (str(r["sex"]), str(r["marital"]), str(r["age_class"]), str(r["employment"]))
        if key in by:
            msg = f"duplicate key {key}"
            raise ValueError(msg)
        v = r["persons"]
        by[key] = None if v is None else float(str(v))
    return by


def with_total_pop(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Append ``total_pop`` = employed + not_employed per (sex, marital, age); None if either
    side is unpublished. The row inherits the employed row's provenance columns."""
    by = _wave_index(rows)
    out = list(rows)
    for r in rows:
        if r["employment"] != "employed":
            continue
        ne = by.get((str(r["sex"]), str(r["marital"]), str(r["age_class"]), "not_employed"))
        emp = by[(str(r["sex"]), str(r["marital"]), str(r["age_class"]), "employed")]
        total = None if emp is None or ne is None else emp + ne
        out.append({**r, "employment": "total_pop", "persons": total})
    return out


def _close(a: float, b: float, terms: int) -> bool:
    return abs(a - b) <= max(_TOLERANCE * max(abs(a), abs(b)), _ROUNDING * terms)


def check_marital_wave(rows: Iterable[dict[str, object]]) -> None:
    """Internal consistency of one survey wave; ``ValueError`` on the first violation.

    (a) うち未婚 ≤ 総数, (b) 正規 + 非正規 (or the published sub-types when 非正規 is absent)
    ≤ 雇用者, (c) Σ age classes = 総数 within 0.5 %, (d) male + female = 総数 within 0.5 %.
    Unpublished (None) cells are skipped.
    """
    by = _wave_index(rows)
    for (sex, marital, age, emp), v in by.items():
        if marital != "total" or v is None:
            continue
        nm = by.get((sex, "never_married", age, emp))
        if nm is not None and nm > v:
            msg = f"うち未婚 exceeds 総数 for {sex}/{age}/{emp}: {nm} > {v}"
            raise ValueError(msg)
    cells = {(s, m, a) for s, m, a, _ in by}
    for sex, marital, age in sorted(cells):
        employee = by.get((sex, marital, age, "employee"))
        parts = (
            ["regular", "nonregular"]
            if (sex, marital, age, "nonregular") in by
            else ["regular", "part_time", "arbeit", "dispatched", "contract"]
        )
        values = [by.get((sex, marital, age, p)) for p in parts]
        if employee is None or any(x is None for x in values):
            continue
        total = sum(x for x in values if x is not None)
        if total > employee * (1 + _TOLERANCE):
            msg = f"正規+非正規 exceeds 雇用者 for {sex}/{marital}/{age}: {total} > {employee}"
            raise ValueError(msg)
    series = {(s, m, e) for s, m, _, e in by}
    for sex, marital, emp in sorted(series):
        age_total = by.get((sex, marital, "total", emp))
        classes = [
            v for (s, m, a, e), v in by.items() if (s, m, e) == (sex, marital, emp) and a != "total"
        ]
        if age_total is None or not classes or any(v is None for v in classes):
            continue
        s = sum(v for v in classes if v is not None)
        if not _close(s, age_total, len(classes)):
            msg = f"sum of age classes != 総数 for {sex}/{marital}/{emp}: {s} vs {age_total}"
            raise ValueError(msg)
    for marital, age, emp in sorted({(m, a, e) for _, m, a, e in by}):
        t, m, f = (by.get((sx, marital, age, emp)) for sx in _SEX_ORDER)
        if t is None or m is None or f is None:
            continue
        if not _close(m + f, t, 2):
            msg = f"male + female != total for {marital}/{age}/{emp}: {m} + {f} vs {t}"
            raise ValueError(msg)


def marital_wave_rows(
    employment_payload: bytes,
    employment_table: Table,
    not_employed_payload: bytes,
    not_employed_table: Table,
) -> list[dict[str, object]]:
    """One wave: both tables parsed, ``total_pop`` added, consistency checked (fail-closed)."""
    if employment_table.kind is not TableKind.MARITAL_EMPLOYMENT:
        msg = f"{employment_table.key} is not the 有業者 table"
        raise ValueError(msg)
    if not_employed_table.kind is not TableKind.MARITAL_NOT_EMPLOYED:
        msg = f"{not_employed_table.key} is not the 無業者 table"
        raise ValueError(msg)
    if employment_table.survey_year != not_employed_table.survey_year:
        msg = (
            f"survey_year mismatch: {employment_table.survey_year} vs "
            f"{not_employed_table.survey_year}"
        )
        raise ValueError(msg)
    rows = marital_employment_rows(employment_payload, employment_table)
    rows += marital_employment_rows(not_employed_payload, not_employed_table)
    rows = with_total_pop(rows)
    check_marital_wave(rows)
    return rows


def _mart_sort_key(r: dict[str, object]) -> tuple[int, int, int, int, int]:
    sex, emp, marital = str(r["sex"]), str(r["employment"]), str(r["marital"])
    if sex not in _SEX_ORDER or emp not in EMPLOYMENT_ORDER or marital not in _MARITAL_ORDER:
        msg = f"unexpected sex/employment/marital {sex!r}/{emp!r}/{marital!r}"
        raise ValueError(msg)
    lower = r["age_lower"]
    return (
        int(str(r["survey_year"])),
        _SEX_ORDER.index(sex),
        -1 if lower is None else int(str(lower)),
        EMPLOYMENT_ORDER.index(emp),
        _MARITAL_ORDER.index(marital),
    )


def build_marital_employment_mart(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    """``marts/jp_marital_by_employment``: staged rows sorted by survey year, sex, age,
    employment, marital; the key must be unique (``ValueError`` otherwise)."""
    out = sorted((dict(r) for r in rows), key=_mart_sort_key)
    seen: set[tuple[object, ...]] = set()
    for r in out:
        key = (r["survey_year"], r["sex"], r["age_class"], r["employment"], r["marital"])
        if key in seen:
            msg = f"duplicate key in jp_marital_by_employment: {key}"
            raise ValueError(msg)
        seen.add(key)
    return out
