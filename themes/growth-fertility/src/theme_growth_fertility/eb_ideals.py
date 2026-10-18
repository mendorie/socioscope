"""Special Eurobarometer 253 (2006): ideal number of children by country. Pure; no I/O.

Source: the data.europa.eu record ``s406_65_1_ebs253`` (``eurobarometer.SPECIAL_WAVES``) holds
two workbooks with the two ideal-family-size questions (general ideal "for a family" and the
personal ideal "for you personally"):

- **EB65.1 Volume C** (EU-25, fieldwork 02–03/2006): one legacy ``.xls`` per country inside a
  zip, sheets ``QC2`` / ``QC3``. Columns are the national total, then sex (Homme / Femme) and
  age (15-24 / 25-39 / 40-54 / 55+) and further breakdowns we ignore. Sex × age is not crossed,
  so "women 25–39" is not available. The sub-national files (D-E / D-W, GB / NI) are dropped
  and reported; the national DE / UK files are used. The record's EB65.1 "Volume A'" only holds
  trend questions (QC4–QC9a vs EB56.2), so Volume C is the only EU-25 source of QC2 / QC3.
- **EB65.3 Volume A** (candidate countries BG / RO / HR / TR, fieldwork 05–06/2006): one
  ``.xls`` in a zip, sheets ``QE2`` / ``QE3`` with the countries as columns.

Both layouts share the answer block: a ``TOTAL`` row (weighted base) and, per answer, a French
row with weighted counts followed by an English row with rounded shares. Answers are None /
One / Two / Three / Four / Five / Six / More than six / "There is no ideal number, it depends" /
DK. Shares here are recomputed from the counts (% of all respondents); the mean excludes "no
ideal" and DK and takes 5 and 6 at face value with "more than six" as 7 (the published tables
are not top-coded at 4+; the H9 design note's "4+ as 4" would understate the mean by ~0.05).
Sheets are recognised by the question text; anything else in the layout (country header,
TOTAL row, answer rows, counts not summing to the base) fails closed with ``ValueError``.
"""

import re

from theme_growth_fertility import eurobarometer as ebm

QUESTIONS: dict[str, re.Pattern[str]] = {
    "general": re.compile(r"ideal number of children for a family", re.I),
    "personal": re.compile(r"for you personally, what would be the ideal number of children", re.I),
}
# (French label of the count row, English label of the share row, metric suffix, value used in
# the mean; None = excluded from the mean). The pairs appear in this order; "Six" is the same
# word in both languages, so rows are matched as ordered pairs, not by label alone.
ANSWERS: tuple[tuple[str, str, str, int | None], ...] = (
    ("Aucun", "None", "zero", 0),
    ("Un", "One", "one", 1),
    ("Deux", "Two", "two", 2),
    ("Trois", "Three", "three", 3),
    ("Quatre", "Four", "four", 4),
    ("Cinq", "Five", "five", 5),
    ("Six", "Six", "six", 6),
    ("Plus de six", "More than six", "more_than_six", 7),
    (
        "Il n’y a pas de nombre idéal, cela dépend",
        "There is no ideal number, it depends",
        "no_ideal",
        None,
    ),
    ("NSP", "DK", "dk", None),
)
_SHARE_SUFFIXES = ("zero", "one", "two", "three", "four_plus", "no_ideal", "dk")
_PREFIX = {"general": "ideal_general_", "personal": "ideal_"}
_MEAN = {"general": "ideal_general_mean", "personal": "ideal_personal_mean"}
METRICS: tuple[str, ...] = tuple(
    [f"{_PREFIX[k]}{s}_share" for k in ("personal", "general") for s in _SHARE_SUFFIXES]
    + [_MEAN["personal"], _MEAN["general"]]
)
BREAKDOWNS: dict[str, tuple[str, str]] = {
    "Homme": ("M", "total"),
    "Femme": ("F", "total"),
    "15-24": ("T", "15-24"),
    "25-39": ("T", "25-39"),
    "40-54": ("T", "40-54"),
    "55 +": ("T", "55+"),
}
DROPPED_CODES: frozenset[str] = frozenset({"D-E", "D-W", "GB", "NI"})
_SURVEY = re.compile(r"EUROBAROMETER\s+(\d+\.\d)")
_VOLUME = re.compile(r"VOLUME\s+([A-Z]'?)")
_QCODE = re.compile(r"^(Q[A-Z]*\d+[a-z]?)\b")
_SUM_TOLERANCE = 0.02  # weighted counts are rounded; Σ answers vs TOTAL differ by a few

Row = dict[str, object]
Grid = list[list[object]]


def _text(cell: object) -> str:
    return " ".join(str(cell).split()) if cell is not None else ""


def _first_match(rows: Grid, pattern: re.Pattern[str], limit: int) -> str | None:
    for row in rows[:limit]:
        for c in row:
            m = pattern.search(_text(c))
            if m:
                return m.group(1)
    return None


def _question(rows: Grid) -> tuple[str, str] | None:
    """(kind, question code) if the sheet is one of the two ideal-children tables."""
    if len(rows) < 3:
        return None
    for c in rows[2]:
        text = _text(c)
        for kind, pattern in QUESTIONS.items():
            if pattern.search(text):
                m = _QCODE.match(text)
                return (kind, m.group(1)) if m else None
    return None


def _count(cell: object, *, sheet: str, label: str) -> float:
    if isinstance(cell, (int, float)) and not isinstance(cell, bool):
        return float(cell)
    if _text(cell) in ("-", ""):
        return 0.0
    msg = f"{sheet}: {label!r}: expected a count, got {cell!r}"
    raise ValueError(msg)


def _is_fraction(cell: object) -> bool:
    if isinstance(cell, (int, float)) and not isinstance(cell, bool):
        return 0 <= float(cell) <= 1
    return _text(cell) in ("-", "")


def _columns(rows: Grid, sheet: str) -> tuple[dict[int, tuple[str, str, str]], list[str]]:
    """Header row -> {column: (iso3, sex, age_class)}; dropped sub-national codes reported."""
    header = next(
        (
            row
            for row in rows[3:]
            if any(_text(c) in ebm.CODE_TO_ISO3 or _text(c) in DROPPED_CODES for c in row)
            or any(_text(c) in ("Homme", "Femme") for c in row)
        ),
        None,
    )
    if header is None:
        msg = f"{sheet}: country header row not found"
        raise ValueError(msg)
    texts = [_text(c) for c in header]
    breakdown_cols = {i for i, t in enumerate(texts) if t in BREAKDOWNS}
    first_breakdown = min(breakdown_cols, default=len(texts))
    codes = [(i, t) for i, t in enumerate(texts[:first_breakdown]) if t]
    dropped: list[str] = []
    columns: dict[int, tuple[str, str, str]] = {}
    for i, code in codes:
        if code in DROPPED_CODES:
            dropped.append(code)
            continue
        if code not in ebm.CODE_TO_ISO3:
            msg = f"{sheet}: unknown country code {code!r} in the header row"
            raise ValueError(msg)
        columns[i] = (ebm.CODE_TO_ISO3[code], "T", "total")
    if breakdown_cols:
        if len(codes) != 1:
            msg = f"{sheet}: sex/age columns next to {len(codes)} country codes"
            raise ValueError(msg)
        missing = [label for label in BREAKDOWNS if label not in texts]
        if missing:
            msg = f"{sheet}: breakdown column(s) {missing} not found"
            raise ValueError(msg)
        if not dropped:
            iso3 = next(iter(columns.values()))[0]
            for i in sorted(breakdown_cols):
                sex, age = BREAKDOWNS[texts[i]]
                columns[i] = (iso3, sex, age)
    return columns, dropped


def _answer_counts(rows: Grid, sheet: str) -> tuple[list[object], dict[str, list[object]]]:
    """TOTAL row and, per English answer label, the (French) row holding the counts."""
    total = next((row for row in rows if _text(row[1] if len(row) > 1 else None) == "TOTAL"), None)
    if total is None:
        msg = f"{sheet}: TOTAL row not found"
        raise ValueError(msg)
    counts: dict[str, list[object]] = {}
    cursor = rows.index(total) + 1
    for fr, en, _suffix, _value in ANSWERS:
        i = next(
            (
                j
                for j in range(cursor, len(rows) - 1)
                if _text(rows[j][1] if len(rows[j]) > 1 else None) == fr
            ),
            None,
        )
        if i is None or _text(rows[i + 1][1] if len(rows[i + 1]) > 1 else None) != en:
            msg = f"{sheet}: answer row {en!r} not found"
            raise ValueError(msg)
        counts[en] = rows[i]
        counts[f"{en}\0shares"] = rows[i + 1]
        cursor = i + 2
    return total, counts


def _parse_sheet(sheet: str, rows: Grid, kind: str, table: str) -> tuple[list[Row], list[str]]:
    columns, dropped = _columns(rows, sheet)
    total_row, counts = _answer_counts(rows, sheet)
    out: list[Row] = []
    for col, (iso3, sex, age) in columns.items():
        base = _count(total_row[col] if col < len(total_row) else None, sheet=sheet, label="TOTAL")
        if base <= 0:
            msg = f"{sheet}: TOTAL is {base!r} for {iso3} {sex} {age}"
            raise ValueError(msg)
        by_suffix: dict[str, float] = {}
        weighted = 0.0
        valid = 0.0
        for fr_label, label, suffix, score in ANSWERS:
            cells = counts[label]
            share_row = counts[f"{label}\0shares"]
            if not _is_fraction(share_row[col] if col < len(share_row) else None):
                msg = f"{sheet}: {label!r}: share row does not hold a fraction"
                raise ValueError(msg)
            n = _count(cells[col] if col < len(cells) else None, sheet=sheet, label=fr_label)
            by_suffix[suffix] = n
            if score is not None:
                weighted += score * n
                valid += n
        total_answers = sum(by_suffix.values())
        if abs(total_answers - base) > _SUM_TOLERANCE * base + 2:
            msg = (
                f"{sheet}: answers sum to {total_answers:g} but TOTAL is {base:g} "
                f"for {iso3} {sex} {age}"
            )
            raise ValueError(msg)
        four_plus = sum(by_suffix[s] for s in ("four", "five", "six", "more_than_six"))
        shares = {
            "zero": by_suffix["zero"],
            "one": by_suffix["one"],
            "two": by_suffix["two"],
            "three": by_suffix["three"],
            "four_plus": four_plus,
            "no_ideal": by_suffix["no_ideal"],
            "dk": by_suffix["dk"],
        }
        values: list[tuple[str, float | None]] = [
            (f"{_PREFIX[kind]}{s}_share", round(v / base * 100, 2)) for s, v in shares.items()
        ]
        values.append((_MEAN[kind], round(weighted / valid, 3) if valid else None))
        for metric, value in values:
            out.append(
                {
                    "iso3": iso3,
                    "sex": sex,
                    "age_class": age,
                    "metric": metric,
                    "value": value,
                    "n": int(base) if base.is_integer() else base,
                    "table": table,
                }
            )
    return out, dropped


def ideal_rows(payload: bytes, wave: ebm.SpecialWave) -> tuple[list[Row], list[str]]:
    """One zip of workbook(s) -> long rows (iso3 × sex × age_class × metric) + issues.

    Issues list the dropped sub-national files. Empty when no sheet carries the questions.
    """
    out: list[Row] = []
    issues: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()
    for member, sheets in ebm.zip_workbooks(payload):
        for sheet, rows in sheets:
            q = _question(rows)
            if q is None:
                continue
            kind, qcode = q
            survey = _first_match(rows, _SURVEY, 1)
            volume = _first_match(rows, _VOLUME, 2)
            if survey is None or volume is None:
                continue  # the Index sheet repeats the question text without a table
            where = f"{member}/{sheet}"
            table = f"{qcode} (EB{survey} Volume {volume})"
            rows_out, dropped = _parse_sheet(where, rows, kind, table)
            for code in dropped:
                note = f"{member}: {code} dropped (sub-national; the national file is used)"
                if note not in issues:
                    issues.append(note)
            for r in rows_out:
                key = (str(r["iso3"]), str(r["sex"]), str(r["age_class"]), str(r["metric"]))
                if key in seen:
                    msg = f"{where}: duplicate row for {key}"
                    raise ValueError(msg)
                seen.add(key)
                out.append(
                    {
                        "iso3": r["iso3"],
                        "survey_year": wave.survey_year,
                        "sex": r["sex"],
                        "age_class": r["age_class"],
                        "metric": r["metric"],
                        "value": r["value"],
                        "n": r["n"],
                        "table": r["table"],
                        "source": ebm.SPECIAL_SOURCE,
                    }
                )
    return out, issues
