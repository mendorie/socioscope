import io

import pytest

from theme_public_debt import jst

HEADER = [
    "year",
    "country",
    "iso",
    "ifs",
    "pop",
    "gdp",
    "cpi",
    "stir",
    "ltrate",
    "debtgdp",
    "revenue",
    "expenditure",
    "tloans",
    "thh",
    "tbus",
    "crisisJST",
    "unrelated",
]


def _row(iso: str, year: int, **kw: object) -> list[object]:
    base: dict[str, object] = {
        "year": year,
        "country": {"JPN": "Japan", "DEU": "Germany"}.get(iso, iso),
        "iso": iso,
        "ifs": 0,
        "pop": 100.0,
        "gdp": 1000.0,
        "cpi": 100.0,
        "stir": 1.0,
        "ltrate": 2.0,
        "debtgdp": 0.5,
        "revenue": 300.0,
        "expenditure": 320.0,
        "tloans": 800.0,
        "thh": 500.0,
        "tbus": 300.0,
        "crisisJST": 0,
        "unrelated": "x",
    }
    base.update(kw)
    return [base[c] for c in HEADER]


def _sheets(rows: list[list[object]], header: list[object] | None = None) -> list[tuple[str, list]]:
    return [("Data", [list(header or HEADER), *rows])]


def _many_countries(n: int = 18) -> list[list[object]]:
    isos = [f"{chr(65 + i)}AA" for i in range(n)]
    return [_row(iso, 2000) for iso in isos]


def test_workbook_rows_reads_real_xlsx_bytes() -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Data"
    ws.append(HEADER)
    ws.append(_row("JPN", 1990))
    buf = io.BytesIO()
    wb.save(buf)

    sheets = jst.workbook_rows(buf.getvalue())

    assert sheets[0][0] == "Data"
    assert sheets[0][1][0][:3] == ["year", "country", "iso"]
    assert sheets[0][1][1][2] == "JPN"


def test_workbook_rows_rejects_non_xlsx() -> None:
    with pytest.raises(ValueError, match="not a readable xlsx"):
        jst.workbook_rows(b"<html>blocked</html>")


def test_parse_maps_columns_and_sorts_by_iso_year() -> None:
    rows = [*_many_countries(), _row("JPN", 1991, debtgdp=0.6), _row("JPN", 1990)]
    out = jst.parse(_sheets(rows))

    jp = [r for r in out if r["iso3"] == "JPN"]
    assert [r["year"] for r in jp] == [1990, 1991]
    assert jp[1]["debtgdp"] == 0.6
    assert jp[0]["country"] == "Japan" and jp[0]["source"] == "jst"
    assert jp[0]["crisis_jst"] == 0.0 and "unrelated" not in jp[0]


def test_parse_fails_closed_on_missing_column() -> None:
    header = [c for c in HEADER if c != "debtgdp"]
    rows = [
        [v for c, v in zip(HEADER, r, strict=True) if c != "debtgdp"] for r in _many_countries()
    ]
    with pytest.raises(ValueError, match="debtgdp"):
        jst.parse(_sheets(rows, header))


def test_parse_fails_closed_on_too_few_countries() -> None:
    with pytest.raises(ValueError, match="only 2 countries"):
        jst.parse(_sheets([_row("JPN", 1990), _row("DEU", 1990)]))


def test_parse_skips_rows_without_iso_or_year() -> None:
    rows = [*_many_countries(), _row("", 1990), _row("JPN", "n/a")]
    out = jst.parse(_sheets(rows))
    assert {r["iso3"] for r in out} == {f"{chr(65 + i)}AA" for i in range(18)}


def test_build_mart_emits_each_definition_as_its_own_unit() -> None:
    staged = jst.parse(_sheets([*_many_countries(), _row("JPN", 1990)]))
    out = [r for r in jst.build_mart(staged) if r["iso3"] == "JPN"]
    got = {(r["unit"], r["metric"]): r["value"] for r in out}

    assert got[("general_gov_gross", "debt_gdp")] == 50.0
    assert got[("general_gov_gross", "fiscal_balance_gdp")] == pytest.approx(-2.0)
    assert got[("households", "debt_gdp")] == 50.0
    assert got[("nfc", "debt_gdp")] == 30.0
    assert got[("private_nonfin", "debt_gdp")] == 80.0
    assert got[("total_nonfin", "debt_gdp")] == 130.0
    assert got[("macro", "ltrate")] == 2.0 and got[("macro", "stir")] == 1.0
    assert got[("macro", "pop")] == 100.0 and got[("macro", "crisis_jst")] == 0.0
    assert ("macro", "ngdp_growth") not in got  # no previous year
    assert all(r["source"] == "jst" for r in out)


def test_build_mart_growth_needs_contiguous_previous_year() -> None:
    staged = jst.parse(
        _sheets(
            [
                *_many_countries(),
                _row("JPN", 1990, gdp=1000.0, cpi=100.0),
                _row("JPN", 1991, gdp=1050.0, cpi=103.0),
                _row("JPN", 1993, gdp=1100.0, cpi=105.0),
            ]
        )
    )
    out = {
        (r["year"], r["metric"]): r["value"]
        for r in jst.build_mart(staged)
        if r["iso3"] == "JPN" and r["unit"] == "macro"
    }
    assert out[(1991, "ngdp_growth")] == pytest.approx(5.0)
    assert out[(1991, "cpi_inflation")] == pytest.approx(3.0)
    assert (1993, "ngdp_growth") not in out


def test_build_mart_drops_missing_values_instead_of_emitting_none() -> None:
    staged = jst.parse(_sheets([*_many_countries(), _row("JPN", 1990, debtgdp=None, tloans=None)]))
    out = [r for r in jst.build_mart(staged) if r["iso3"] == "JPN"]
    units = {(r["unit"], r["metric"]) for r in out}
    assert ("general_gov_gross", "debt_gdp") not in units
    assert ("private_nonfin", "debt_gdp") not in units
    assert ("total_nonfin", "debt_gdp") not in units
    assert ("households", "debt_gdp") in units
    assert all(r["value"] is not None for r in out)
