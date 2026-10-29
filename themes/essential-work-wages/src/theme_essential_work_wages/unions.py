"""労働組合基礎調査 (厚生労働省) 概況 / 調査結果の概要 第 3 表「産業別労働組合員数及び推定組織率
（単位労働組合）」, 2012-2025 (each year's 6 月 30 日現在)
-> 産業大分類 × 組合員数・雇用者数・推定組織率.

Why PDF: e-Stat publishes the 産業別 **推定組織率** (= 組合員数 ÷ 労働力調査 6 月の雇用者数) only in
the 概況 (2023-) / 報告書「調査結果の概要」(-2022) PDFs (fileKind=2); the xlsx 時系列 / 総括表 carry
組合数・組合員数 but not 雇用者数 or 組織率. One PDF per year (``FILES``; toukei=00450101,
tstat=000001015698). Each PDF's 第 3 表 is parsed from pypdf text (``pdf_pages`` gives the
layout-mode and the plain rendering of every page; the first complete table wins — layout mode
is needed for the character-spaced 2015 / 2022 files, plain mode for 2013 / 2014 / 2023 whose
table body layout mode drops); only the survey-year columns are used (2024- PDFs also print the
previous year, ignored).

Page shape (checked 2026-10-29 on all 14 files): a units line made only of
人 / 千人 / 万人 / ％ / ポイント, then one line per industry: name (characters spaced out by the
layout), then numbers in the units' order; women's figures in parentheses (2013-2022) share the
units line; 2012 prints them on separate lines starting with ``(``. ``members`` is the first 人 or
千人 column (scaled to persons), ``employees`` the first 万人 column (scaled to persons),
``union_density_pct`` the ％ column right after it; ``…`` -> None (分類不能の産業 has no 雇用者数).
Industry names are normalised (whitespace removed, NFKC, ，/, -> 、, note markers ``2)`` dropped)
and must match the 20 rows of ``INDUSTRY_CODES`` (総計 + 19 industries; 農業、林業、漁業 is one row
= JSIC A+B, so its code is ``A-B``). Check: the 19 industries' members sum to the 総計 within
``TOLERANCE`` (0.5 %; 2024- figures are rounded to thousands), else ``ValueError``.
Notes from the PDFs: from 2024 the survey classifies by JSIC 第 14 回改定 while 労働力調査
雇用者数 is still 第 13 回; 労働力調査 benchmark switches (2022-01) are not back-cast; the 総計
row's 推定組織率 is printed as ``…`` in the 2012-2018 tables (the headline rate is elsewhere in
those PDFs), so ``union_density_pct`` of ``ALL`` is None for those years.

License: 政府標準利用規約（第 2.0 版、CC BY 4.0 互換）.
出典「政府統計の総合窓口(e-Stat)、労働組合基礎調査（厚生労働省）を加工」.
"""

from __future__ import annotations

import io
import re
import unicodedata
from collections.abc import Sequence

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.pipeline import THEME

SOURCE = "mhlw_unions"
LICENSE = (
    "政府標準利用規約（第2.0版、CC BY 4.0 互換）。出典: 政府統計の総合窓口(e-Stat)、"
    "労働組合基礎調査 概況 第3表（厚生労働省）を加工"
)
BASE = "https://www.e-stat.go.jp/stat-search/file-download"
FILE_KIND = 2  # PDF
MAGIC = b"%PDF"
STAGED_PREFIX = f"staged/{SOURCE}/industry_"
MART_TABLE = "marts/jp_union_density_by_industry"
TOLERANCE = 0.005

# year -> statInfId of the PDF carrying 第 3 表 (概況 for 2023-2025, 調査結果の概要 for 2012-2022).
FILES: dict[int, str] = {
    2012: "000023609833",
    2013: "000023621335",
    2014: "000028064105",
    2015: "000031376074",
    2016: "000031545510",
    2017: "000031675564",
    2018: "000031792619",
    2019: "000031913806",
    2020: "000032062625",
    2021: "000032173533",
    2022: "000040010743",
    2023: "000040128847",
    2024: "000040232141",
    2025: "000040389648",
}

# normalised industry name -> code (JSIC 大分類 letters; 総計 = ALL; 農業、林業、漁業 = A+B)
INDUSTRY_CODES: dict[str, str] = {
    "総計": "ALL",
    "農業、林業、漁業": "A-B",
    "鉱業、採石業、砂利採取業": "C",
    "建設業": "D",
    "製造業": "E",
    "電気・ガス・熱供給・水道業": "F",
    "情報通信業": "G",
    "運輸業、郵便業": "H",
    "卸売業、小売業": "I",
    "金融業、保険業": "J",
    "不動産業、物品賃貸業": "K",
    "学術研究、専門・技術サービス業": "L",
    "宿泊業、飲食サービス業": "M",
    "生活関連サービス業、娯楽業": "N",
    "教育、学習支援業": "O",
    "医療、福祉": "P",
    "複合サービス事業": "Q",
    "サービス業(他に分類されないもの)": "R",
    "公務(他に分類されるものを除く)": "S",
    "分類不能の産業": "T",
}
TOTAL_CODE = "ALL"
UNIT_SCALE = {"人": 1.0, "千人": 1_000.0, "万人": 10_000.0}
UNITS = {*UNIT_SCALE, "％", "ポイント"}
MART_COLUMNS = (
    "iso3",
    "year",
    "industry_code",
    "industry",
    "members",
    "employees",
    "union_density_pct",
    "source",
)

Row = dict[str, object]
_NUM = re.compile(r"^[+-]?\d[\d,]*(?:\.\d+)?$")
_PAREN = re.compile(r"^\(.*\)$")
_NOTE = re.compile(r"^\d\)$")
_MISSING = {"…", "-", "ｰ", "X", "x"}


def url(year: int) -> str:
    return f"{BASE}?statInfId={FILES[year]}&fileKind={FILE_KIND}"


def raw_name(year: int) -> str:
    return f"unions_{year}_overview.pdf"


def staged_table(year: int) -> str:
    return f"{STAGED_PREFIX}{year}"


def pdf_pages(payload: bytes) -> list[str]:
    """PDF -> two texts per page: layout mode (column gaps kept) then plain mode.

    Layout mode is the one that separates the character-spaced 2015 / 2022 tables, but it drops
    the table body of the 2013 / 2014 / 2023 PDFs, where plain mode is fine; ``parse`` takes the
    first rendering that yields a complete 第 3 表.
    """
    import pypdf

    try:
        reader = pypdf.PdfReader(io.BytesIO(payload))
        out: list[str] = []
        for p in reader.pages:
            out.append(p.extract_text(extraction_mode="layout"))
            out.append(p.extract_text())
    except Exception as e:
        msg = "payload is not a readable pdf"
        raise ValueError(msg) from e
    return out


def normalise_industry(tokens: Sequence[str]) -> str:
    s = unicodedata.normalize("NFKC", "".join(tokens))
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"\d\)$", "", s)  # note marker glued to the name (分類不能の産業2))
    return s.replace("，", "、").replace(",", "、").replace("･", "・")


def _value(token: str) -> float | None:
    if token in _MISSING:
        return None
    return float(token.replace(",", "").replace("+", "")) if _NUM.match(token) else None


def _is_value(token: str) -> bool:
    return token in _MISSING or bool(_NUM.match(token)) or bool(_PAREN.match(token))


_GLUED = re.compile(r"^([^\d(+\-.]+?)(\d\)|[+-]?\d[\d,]*(?:\.\d+)?)$")


def _tokens(line: str) -> list[str]:
    """Whitespace split; a name glued to its first number (``漁業10``, ``産業2)``) is split."""
    out: list[str] = []
    for t in line.split():
        m = _GLUED.match(t)
        out.extend([m.group(1), m.group(2)] if m else [t])
    return [t for t in out if not _NOTE.match(t)]


def _split_line(line: str) -> tuple[list[str], list[str]]:
    """-> (name tokens, value tokens). Values start at the first numeric / '(…)' / '…' token."""
    tokens = _tokens(line)
    for i, t in enumerate(tokens):
        if _is_value(t):
            return tokens[:i], tokens[i:]
    return tokens, []


def _units(line: str) -> list[str] | None:
    units = line.split()
    return units if len(units) >= 3 and all(u in UNITS for u in units) else None


def _parse_page(text: str, year: int) -> dict[str, Row]:
    """One page text -> {code: row} for the industry rows found under a 人/万人/％ units line.

    Several tables may share a page (each with its own units line); the scan of one table stops at
    the next units line, and the table with the most industry rows wins.
    """
    lines = text.splitlines()
    best: dict[str, Row] = {}
    for start, line in enumerate(lines):
        units = _units(line)
        if units is None:
            continue
        i_members = next((i for i, u in enumerate(units) if u in ("人", "千人")), None)
        i_emp = next((i for i, u in enumerate(units) if u == "万人"), None)
        i_dens = (
            next((i for i in range(i_emp + 1, len(units)) if units[i] == "％"), None)
            if i_emp is not None
            else None
        )
        if i_members is None or i_emp is None or i_dens is None:
            continue
        rows: dict[str, Row] = {}
        for raw in lines[start + 1 :]:
            if _units(raw) is not None:
                break  # next table
            name_tokens, values = _split_line(raw)
            if not name_tokens or not values:
                continue
            name = normalise_industry(name_tokens)
            code = INDUSTRY_CODES.get(name)
            if code is None:
                if rows:
                    break  # past the table (notes)
                continue
            if len(values) <= max(i_members, i_emp, i_dens):
                msg = f"unions {year}: {name} has {len(values)} values for {len(units)} units"
                raise ValueError(msg)
            members = _value(values[i_members])
            emp = _value(values[i_emp])
            rows[code] = {
                "year": year,
                "industry_code": code,
                "industry": name,
                "members": None if members is None else members * UNIT_SCALE[units[i_members]],
                "employees": None if emp is None else emp * UNIT_SCALE["万人"],
                "union_density_pct": _value(values[i_dens]),
            }
        if len(rows) > len(best):
            best = rows
    return best


def parse(pages: Sequence[str], year: int) -> list[Row]:
    """Page texts (see ``pdf_pages``) -> 20 rows (総計 + 19 industries) for ``year``; fail-closed.

    The first page rendering holding all 20 rows is used; otherwise the error names the
    industries missing from the most complete candidate.
    """
    best: dict[str, Row] = {}
    for page in pages:
        found = _parse_page(page, year)
        if len(found) == len(INDUSTRY_CODES):
            best = found
            break
        if len(found) > len(best):
            best = found
    if not best:
        msg = f"unions {year}: no page with a 人/万人/％ units line followed by industry rows"
        raise ValueError(msg)
    missing = [name for name, code in INDUSTRY_CODES.items() if code not in best]
    if missing:
        msg = f"unions {year}: industries missing from 第3表: {missing}"
        raise ValueError(msg)
    rows = list(best.values())
    total = next(r for r in rows if r["industry_code"] == TOTAL_CODE)
    t = total["members"]
    s = sum(
        float(str(r["members"]))
        for r in rows
        if r["industry_code"] != TOTAL_CODE and r["members"] is not None
    )
    if t is None or abs(float(str(t)) - s) / float(str(t)) > TOLERANCE:
        msg = f"unions {year}: sum of industries {s} != 総計 {t}"
        raise ValueError(msg)
    rows.sort(key=lambda r: list(INDUSTRY_CODES.values()).index(str(r["industry_code"])))
    return rows


def build_mart(staged: Sequence[Row]) -> list[Row]:
    out: list[Row] = [
        {
            "iso3": "JPN",
            "year": int(str(r["year"])),
            "industry_code": r["industry_code"],
            "industry": r["industry"],
            "members": r.get("members"),
            "employees": r.get("employees"),
            "union_density_pct": r.get("union_density_pct"),
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: (int(str(r["year"])), str(r["industry_code"])))
    seen: set[tuple[int, str]] = set()
    for r in out:
        k = (int(str(r["year"])), str(r["industry_code"]))
        if k in seen:
            msg = f"unions mart: duplicate year/industry {k}"
            raise ValueError(msg)
        seen.add(k)
    return out


# ---- stages (I/O through ports)


def fetch(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for year in sorted(FILES):
        name, u = raw_name(year), url(year)
        try:
            payload = ctx.fetcher.fetch(u)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.startswith(MAGIC):
            skipped.append(f"{name}: non-pdf payload")
            continue
        rec = ctx.raw.put(
            theme=THEME, source=SOURCE, name=name, url=u, license=LICENSE, payload=payload
        )
        written.append(rec.relative_path)
    return written, skipped


def stage(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    for year in sorted(FILES):
        payload = ctx.raw.get(theme=THEME, source=SOURCE, name=raw_name(year))
        if payload is None:
            skipped.append(f"{raw_name(year)}: no raw")
            continue
        ctx.tables.write_table(staged_table(year), parse(pdf_pages(payload), year))
        written.append(staged_table(year))
    return written, skipped


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    staged: list[Row] = []
    for year in sorted(FILES):
        try:
            staged.extend(ctx.tables.read_table(staged_table(year)))
        except FileNotFoundError:
            continue
    if not staged:
        skipped.append(f"{SOURCE}: no staged table")
        return written, skipped
    ctx.tables.write_table(MART_TABLE, build_mart(staged))
    written.append(MART_TABLE)
    return written, skipped
