"""職業安定業務統計（一般職業紹介状況, 厚生労働省）職業別労働市場関係指標: e-Stat long time
series workbooks -> monthly long rows -> monthly / calendar-year marts (I/O through ports only).

Source tables (e-Stat toukei=00450222, tstat=000001020327, monthly tree ``cycle=1``; both are
``stat-search/file-download?statInfId=<id>&fileKind=0``):

- ``FILE_2012`` statInfId 000031942508
  「職業別労働市場関係指標（実数）（平成23年改定）（平成24年3月～）」 .xls (BIFF).
  Months 2012-03 .. 2020-03 (the branch 「月次 ～令和2年3月【旧様式】」 was frozen when the
  long-series layout changed in 2020-04). Classification: 平成23年改定 厚生労働省編職業分類
  (``jp_mhlw2011``).
- ``FILE_2022`` statInfId 000040505332
  「職業別労働市場関係指標（実数）（平成21年改定）（令和4年4月～）」 .xlsx.
  Months 2022-04 .. latest (2026-08 when checked 2026-10-29; the file grows every month, so
  re-fetching changes the sha256 recorded in the manifest). Classification: 平成21年12月改定
  日本標準職業分類 (``jp_jsoc2009``).

Classification history (e-Stat note 「令和5年4月分以降の職業分類について」, statInfId
000040505339, 2023-05-30): Hello Work switched to the 第5回改訂厚生労働省編職業分類 on
2023-03-20, and from the 2023-04 figures the statistics are tabulated by the 平成21年改定
日本標準職業分類 (日標) instead of the 第4回改訂 (平成23年改定) 厚労分類. For the long series
the ministry retabulated 2022-04 onward by 日標, which is ``FILE_2022``. The 厚労分類 series
for 2020-04 .. 2022-03 (第21表 of the 2020-04 layout) is no longer published on e-Stat (the
intermediate branches 「～令和5年3月【旧様式】」 / 「～令和6年3月【旧様式】」 carry only
errata), so this module has a gap of 24 months between the two files.
Both files have 69 occupation rows (職業計, 11 major groups, 55 middle groups, 分類不能の職業,
介護関係職種 = an MHLW aggregate footnoted in each file). Names differ between the two
classifications (e.g. 「介護サービスの職業」 vs 「介護サービス職業従事者」); only 7 names
match exactly, so linking is left to a hand-made correspondence table (CLAUDE.md
「職業分類の断絶を隠さない」). Also note (statInfId 000040505338): from 2021-09
online-registered job seekers are included in 求職者数 / 就職件数, which lowers 有効求人倍率
relative to earlier months.

Workbook structure (identical for both files apart from the header rows): 21 sheets =
3 employment types x 7 metrics, in the order 新規求人数, 有効求人数, 新規求職申込件数,
有効求職者数, 就職件数, 新規求人倍率, 有効求人倍率 for 「パートタイムを含む常用」, then
「パートタイムを除く常用」, then 「常用的パートタイム」. Each sheet is occupations (rows) x
columns [calendar-year averages, fiscal-year averages, months]. Row 0 carries the title
「職業別<指標>（<区分>）」 which this module uses to identify metric and employment type
(sheet names differ between the files). ``FILE_2022``: row 1 = 西暦 (``2023年`` /
``2022年度`` / ``2022年`` per month column), row 3 = ``4月`` for month columns, row 4 = unit,
data from row 5. ``FILE_2012``: row 2 = 和暦 headers (``25年計`` / ``24年度計`` / ``24年3月``,
``4月`` ... with the year token carried forward; 平成31年4月 is followed by ``元年5月`` =
令和元年), col 1 empty, data from row 3. Counts are persons (原数値, not seasonally
adjusted), ratios are rounded to 2 decimals in the source. 就職件数 is not loaded (not needed
by the theme).

Only month columns are kept; the year / fiscal-year averages in the files are recomputed here
(``build_annual``) so that partial years are visible through ``n_months``.
"""

import io
import re
import unicodedata
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from statistics import fmean

import openpyxl
import xlrd
from xlrd.biffh import XLRDError

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.pipeline import THEME

SOURCE = "mhlw_jobs"
LICENSE = (
    "政府標準利用規約（第2.0版）/ CC BY 4.0 compatible "
    "(https://www.e-stat.go.jp/terms-of-use, checked 2026-10-29; "
    "出典：厚生労働省「一般職業紹介状況（職業安定業務統計）」, 政府統計の総合窓口(e-Stat))"
)
BASE = "https://www.e-stat.go.jp/stat-search/file-download"
FILE_KIND_EXCEL = 0
MAGIC_XLS = b"\xd0\xcf\x11\xe0"
MAGIC_XLSX = b"PK\x03\x04"
MAGIC: tuple[bytes, ...] = (MAGIC_XLS, MAGIC_XLSX)
ISO3 = "JPN"

MONTHLY_TABLE = "marts/jobs_occupation_monthly"
ANNUAL_TABLE = "marts/jobs_occupation_annual"

TOTAL = "職業計"
RATIO_TOLERANCE = 1e-6


class Layout(StrEnum):
    WAREKI_XLS = "wareki_xls"  # FILE_2012: BIFF, 和暦 headers in row 2, data from row 3
    SEIREKI_XLSX = "seireki_xlsx"  # FILE_2022: OOXML, 西暦 row 1 + month row 3, data from row 5


class EmploymentType(StrEnum):
    REGULAR_INCL_PARTTIME = "regular_incl_parttime"  # パートタイムを含む常用
    REGULAR_EXCL_PARTTIME = "regular_excl_parttime"  # パートタイムを除く常用
    PARTTIME = "parttime"  # 常用的パートタイム


class Metric(StrEnum):
    JOB_OPENINGS = "job_openings"  # 月間有効求人数（人）
    JOB_SEEKERS = "job_seekers"  # 月間有効求職者数（人）
    OPENINGS_TO_SEEKERS = "openings_to_seekers"  # 有効求人倍率
    NEW_OPENINGS = "new_openings"  # 新規求人数（人）
    NEW_SEEKERS = "new_seekers"  # 新規求職申込件数（件）
    NEW_OPENINGS_TO_SEEKERS = "new_openings_to_seekers"  # 新規求人倍率


# Title keywords -> metric. Longer keys first so 有効求人倍率 is not read as 有効求人数.
_METRIC_BY_TITLE: tuple[tuple[str, Metric | None], ...] = (
    ("有効求人倍率", Metric.OPENINGS_TO_SEEKERS),
    ("新規求人倍率", Metric.NEW_OPENINGS_TO_SEEKERS),
    ("有効求人数", Metric.JOB_OPENINGS),
    ("有効求職者数", Metric.JOB_SEEKERS),
    ("新規求人数", Metric.NEW_OPENINGS),
    ("新規求職申込件数", Metric.NEW_SEEKERS),
    ("就職件数", None),  # not loaded
)
_EMPLOYMENT_BY_TITLE: tuple[tuple[str, EmploymentType], ...] = (
    ("パートタイムを含む常用", EmploymentType.REGULAR_INCL_PARTTIME),
    ("パートタイムを除く常用", EmploymentType.REGULAR_EXCL_PARTTIME),
    ("常用的パートタイム", EmploymentType.PARTTIME),
)
_EXPECTED_SHEETS = {(e, m) for _, e in _EMPLOYMENT_BY_TITLE for _, m in _METRIC_BY_TITLE if m}

STAGED_COLUMNS: tuple[str, ...] = (
    "year",
    "month",
    "classification",
    "occupation",
    "employment_type",
    "metric",
    "value",
)
MONTHLY_COLUMNS: tuple[str, ...] = ("iso3", *STAGED_COLUMNS, "source")
MONTHLY_KEY: tuple[str, ...] = (
    "year",
    "month",
    "classification",
    "occupation",
    "employment_type",
    "metric",
)
ANNUAL_COLUMNS: tuple[str, ...] = (
    "iso3",
    "year",
    "classification",
    "occupation",
    "employment_type",
    "openings_to_seekers_mean",
    "job_openings_mean",
    "job_seekers_mean",
    "n_months",
    "source",
)

Grid = list[list[object]]
Row = dict[str, object]


@dataclass(frozen=True)
class SourceFile:
    key: str  # period label used in raw / staged names
    stat_inf_id: str
    classification: str
    layout: Layout
    period: str  # documentation only
    file_kind: int = FILE_KIND_EXCEL

    @property
    def url(self) -> str:
        return f"{BASE}?statInfId={self.stat_inf_id}&fileKind={self.file_kind}"

    @property
    def extension(self) -> str:
        return "xls" if self.layout is Layout.WAREKI_XLS else "xlsx"

    @property
    def magic(self) -> bytes:
        return MAGIC_XLS if self.layout is Layout.WAREKI_XLS else MAGIC_XLSX

    @property
    def raw_name(self) -> str:
        return f"occupation_indicators_{self.classification}_{self.key}.{self.extension}"

    @property
    def staged_table(self) -> str:
        return f"staged/jobs/occupation_indicators_{self.key}"


FILE_2012 = SourceFile(
    key="from2012_03",
    stat_inf_id="000031942508",
    classification="jp_mhlw2011",
    layout=Layout.WAREKI_XLS,
    period="2012-03 .. 2020-03",
)
FILE_2022 = SourceFile(
    key="from2022_04",
    stat_inf_id="000040505332",
    classification="jp_jsoc2009",
    layout=Layout.SEIREKI_XLSX,
    period="2022-04 .. latest",
)
FILES: tuple[SourceFile, ...] = (FILE_2012, FILE_2022)


# ---- workbook -> grids (bytes parsing only, no I/O)


def read_grids(payload: bytes, layout: Layout) -> list[Grid]:
    """Every sheet of the workbook as a list of rows (cell values as the reader gives them)."""
    try:
        if layout is Layout.WAREKI_XLS:
            book = xlrd.open_workbook(file_contents=payload)
            return [[sh.row_values(i) for i in range(sh.nrows)] for sh in book.sheets()]
        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
        return [[list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets]
    except (XLRDError, zipfile.BadZipFile, KeyError, OSError) as e:
        msg = f"not a readable {layout} workbook: {type(e).__name__}"
        raise ValueError(msg) from e


# ---- grids -> long rows (pure)


def normalize_name(raw: object) -> str:
    """Occupation label as in the source (full-width punctuation kept) with every whitespace
    (incl. 全角空白 / newlines) removed and the footnote mark on the MHLW aggregate
    (「介護関係職種（※）」 / 「介護関係職種（注２）」) dropped."""
    s = re.sub(r"\s+", "", "" if raw is None else str(raw))
    return re.sub(r"^(介護関係職種)[（(].*[）)]$", r"\1", s)


def _is_note(label: str) -> bool:
    return label.startswith(("（注", "(注", "※", "注"))


def _value(cell: object, where: str) -> float | None:
    if cell is None or cell in ("", "-"):
        return None
    if isinstance(cell, bool) or not isinstance(cell, int | float):
        msg = f"unexpected cell {cell!r} at {where}"
        raise ValueError(msg)
    return float(cell)


def wareki_months(headers: Sequence[object]) -> list[tuple[int, int] | None]:
    """和暦 month headers (``24年3月``, ``4月``, ``元年5月``, ``2年1月``) -> (year, month) per cell.

    The year token carries forward across cells. The era starts as 平成 (year + 1988); the
    first ``元年`` switches to 令和 (year + 2018). Non-month cells (``25年計``, ``24年度計``,
    blanks) -> None.
    """
    out: list[tuple[int, int] | None] = []
    year: int | None = None
    reiwa = False
    for h in headers:
        m = re.fullmatch(r"(?:(\d+|元)年)?(\d{1,2})月", str(h).strip())
        if not m:
            out.append(None)
            continue
        if m.group(1) == "元":
            reiwa, year = True, 2019
        elif m.group(1):
            n = int(m.group(1))
            year = (2018 if reiwa else 1988) + n
        if year is None:
            msg = f"month header {h!r} before any year token"
            raise ValueError(msg)
        out.append((year, int(m.group(2))))
    return out


def seireki_months(
    year_row: Sequence[object], month_row: Sequence[object]
) -> list[tuple[int, int] | None]:
    """西暦 header pair (``2022年`` over ``4月``) -> (year, month) per column; ``2022年度`` and year
    averages have no month cell and give None."""
    out: list[tuple[int, int] | None] = []
    for y, m in zip(year_row, month_row, strict=True):
        ym = re.fullmatch(r"(\d{4})年", str(y).strip())
        mm = re.fullmatch(r"(\d{1,2})月", str(m).strip()) if m is not None else None
        out.append((int(ym.group(1)), int(mm.group(1))) if ym and mm else None)
    return out


def _sheet_title(grid: Grid) -> str:
    for cell in grid[0] if grid else []:
        if isinstance(cell, str) and "職業別" in cell:
            return unicodedata.normalize("NFKC", cell)
    msg = "sheet without a 職業別 title in row 0"
    raise ValueError(msg)


def _classify_sheet(title: str) -> tuple[EmploymentType, Metric | None]:
    emp = next((e for k, e in _EMPLOYMENT_BY_TITLE if k in title), None)
    hit = next(((k, m) for k, m in _METRIC_BY_TITLE if k in title), None)
    if emp is None or hit is None:
        msg = f"unrecognised sheet title {title!r}"
        raise ValueError(msg)
    return emp, hit[1]


def _month_columns(grid: Grid, layout: Layout) -> tuple[list[tuple[int, int] | None], int]:
    """(per-column (year, month) or None, index of the first data row)."""
    if layout is Layout.WAREKI_XLS:
        months = wareki_months(grid[2])
        first = 3
    else:
        months = seireki_months(grid[1], grid[3])
        first = 5
    seq = [m for m in months if m is not None]
    if not seq:
        msg = "no month columns found"
        raise ValueError(msg)
    if any(b <= a for a, b in pairwise(seq)):
        msg = f"month columns are not monotonic: {seq}"
        raise ValueError(msg)
    return months, first


def _sheet_values(
    grid: Grid, layout: Layout, where: str
) -> dict[tuple[str, int, int], float | None]:
    months, first = _month_columns(grid, layout)
    out: dict[tuple[str, int, int], float | None] = {}
    for i, row in enumerate(grid[first:], start=first):
        label = normalize_name(row[0] if row else "")
        if not label or _is_note(label):
            continue
        for j, ym in enumerate(months):
            if ym is None:
                continue
            key = (label, *ym)
            if key in out:
                msg = f"duplicate occupation/month {key} in {where}"
                raise ValueError(msg)
            out[key] = _value(row[j] if j < len(row) else None, f"{where} r{i} c{j}")
    if not any(k[0] == TOTAL for k in out):
        msg = f"no {TOTAL} row in {where}"
        raise ValueError(msg)
    return out


def _check_total_ratio(
    values: dict[tuple[EmploymentType, Metric], dict[tuple[str, int, int], float | None]],
) -> None:
    """有効求人倍率 of 職業計 must equal round(有効求人数 / 有効求職者数, 2) in every month (guards
    against seasonally adjusted or shifted columns)."""
    for _, emp in _EMPLOYMENT_BY_TITLE:
        ratios = values[(emp, Metric.OPENINGS_TO_SEEKERS)]
        openings = values[(emp, Metric.JOB_OPENINGS)]
        seekers = values[(emp, Metric.JOB_SEEKERS)]
        for key, ratio in ratios.items():
            if key[0] != TOTAL:
                continue
            o, s = openings.get(key), seekers.get(key)
            if o is None or s is None or ratio is None or s == 0:
                msg = f"{TOTAL} {key[1]}-{key[2]:02d} {emp}: missing openings/seekers/ratio"
                raise ValueError(msg)
            if abs(round(o / s, 2) - ratio) > RATIO_TOLERANCE:
                msg = (
                    f"{TOTAL} {key[1]}-{key[2]:02d} {emp}: ratio {ratio} != "
                    f"{o} / {s} = {round(o / s, 2)}"
                )
                raise ValueError(msg)


def grids_to_rows(grids: Sequence[Grid], file: SourceFile) -> list[Row]:
    """All sheets of one workbook -> long rows (``STAGED_COLUMNS``), sorted, cross-checked."""
    values: dict[tuple[EmploymentType, Metric], dict[tuple[str, int, int], float | None]] = {}
    for n, grid in enumerate(grids):
        title = _sheet_title(grid)
        emp, metric = _classify_sheet(title)
        if metric is None:
            continue
        if (emp, metric) in values:
            msg = f"sheet {n} repeats {emp}/{metric}: {title!r}"
            raise ValueError(msg)
        values[(emp, metric)] = _sheet_values(grid, file.layout, f"sheet {n} {title!r}")
    if set(values) != _EXPECTED_SHEETS:
        msg = f"expected {len(_EXPECTED_SHEETS)} metric sheets, found {sorted(values)}"
        raise ValueError(msg)
    _check_total_ratio(values)
    rows: list[Row] = [
        {
            "year": year,
            "month": month,
            "classification": file.classification,
            "occupation": occ,
            "employment_type": str(emp),
            "metric": str(metric),
            "value": v,
        }
        for (emp, metric), cells in values.items()
        for (occ, year, month), v in cells.items()
    ]
    rows.sort(
        key=lambda r: (
            int(str(r["year"])),
            int(str(r["month"])),
            str(r["employment_type"]),
            str(r["occupation"]),
            str(r["metric"]),
        )
    )
    return rows


def parse(payload: bytes, file: SourceFile) -> list[Row]:
    """Workbook bytes -> long rows. Deterministic; raises ValueError on any layout surprise."""
    return grids_to_rows(read_grids(payload, file.layout), file)


# ---- marts (pure)


def build_monthly(staged: Iterable[Sequence[Row]]) -> list[Row]:
    """Concatenate the staged files into one monthly table; reject duplicate keys."""
    out: list[Row] = [
        {"iso3": ISO3, **{c: r.get(c) for c in STAGED_COLUMNS}, "source": SOURCE}
        for rows in staged
        for r in rows
    ]
    out.sort(
        key=lambda r: tuple(
            str(r[k]) if k != "year" and k != "month" else int(str(r[k])) for k in MONTHLY_KEY
        )
    )
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in MONTHLY_KEY)
        if k in seen:
            msg = f"duplicate monthly key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out


def build_annual(monthly: Sequence[Row]) -> list[Row]:
    """Calendar-year means per (year, classification, occupation, employment_type).

    Means ignore None cells; ``n_months`` counts months with a non-null 有効求人倍率 so that
    partial years (first / last year of a file) stay in the table but are recognisable.
    """
    groups: dict[tuple[int, str, str, str], dict[str, dict[int, float]]] = {}
    for r in monthly:
        metric = str(r["metric"])
        if metric not in (Metric.OPENINGS_TO_SEEKERS, Metric.JOB_OPENINGS, Metric.JOB_SEEKERS):
            continue
        key = (
            int(str(r["year"])),
            str(r["classification"]),
            str(r["occupation"]),
            str(r["employment_type"]),
        )
        g = groups.setdefault(key, {})
        v = r["value"]
        if v is None:
            continue
        if not isinstance(v, int | float):
            msg = f"non-numeric value {v!r} for {key} {metric}"
            raise ValueError(msg)
        month = int(str(r["month"]))
        cells = g.setdefault(metric, {})
        if month in cells:
            msg = f"duplicate month {month} for {key} {metric}"
            raise ValueError(msg)
        cells[month] = float(v)

    def mean(g: dict[str, dict[int, float]], metric: Metric) -> float | None:
        vals = list(g.get(metric, {}).values())
        return fmean(vals) if vals else None

    out: list[Row] = []
    for (year, cls, occ, emp), g in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][3], kv[0][2])
    ):
        out.append(
            {
                "iso3": ISO3,
                "year": year,
                "classification": cls,
                "occupation": occ,
                "employment_type": emp,
                "openings_to_seekers_mean": mean(g, Metric.OPENINGS_TO_SEEKERS),
                "job_openings_mean": mean(g, Metric.JOB_OPENINGS),
                "job_seekers_mean": mean(g, Metric.JOB_SEEKERS),
                "n_months": len(g.get(Metric.OPENINGS_TO_SEEKERS, {})),
                "source": SOURCE,
            }
        )
    return out


# ---- stages (I/O through ports)


def fetch(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for f in FILES:
        try:
            payload = ctx.fetcher.fetch(f.url)
        except FetchError as e:
            skipped.append(f"{f.raw_name}: {e}")
            continue
        if not payload.startswith(f.magic):
            skipped.append(f"{f.raw_name}: non-excel payload")
            continue
        rec = ctx.raw.put(
            theme=THEME, source=SOURCE, name=f.raw_name, url=f.url, license=LICENSE, payload=payload
        )
        written.append(rec.relative_path)
    return written, skipped


def stage(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for f in FILES:
        payload = ctx.raw.get(theme=THEME, source=SOURCE, name=f.raw_name)
        if payload is None:
            skipped.append(f"{f.raw_name}: no raw")
            continue
        ctx.tables.write_table(f.staged_table, parse(payload, f))
        written.append(f.staged_table)
    return written, skipped


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    staged: list[list[Row]] = []
    for f in FILES:
        try:
            staged.append(ctx.tables.read_table(f.staged_table))
        except FileNotFoundError:
            skipped.append(f"{f.staged_table}: no staged table")
    if not staged:
        return written, skipped
    monthly = build_monthly(staged)
    ctx.tables.write_table(MONTHLY_TABLE, monthly)
    written.append(MONTHLY_TABLE)
    ctx.tables.write_table(ANNUAL_TABLE, build_annual(monthly))
    written.append(ANNUAL_TABLE)
    return written, skipped
