"""H10-JP: 就業構造基本調査 雇用形態 × 配偶関係 × 年齢 × 性, four waves (2007/2012/2017/2022).

Fixtures are the real e-Stat files cut down (rows / columns dropped, positions kept):
2022 tidy xlsx, 2017 tidy xlsx with J/E rows and English dimension columns, 2012 / 2007 wide
xls (raw BIFF8 streams written from the real workbooks; xlrd reads them like the originals).
"""

import io
from pathlib import Path

import openpyxl
import pytest

from theme_growth_fertility import estat

FIXTURES = Path(__file__).parent / "fixtures"


def table(key: str) -> estat.Table:
    return next(t for t in estat.MARITAL_EMPLOYMENT_TABLES if t.key == key)


def payload(t: estat.Table) -> bytes:
    return (FIXTURES / f"estat_{t.key}.{t.raw_name.rsplit('.', 1)[1]}").read_bytes()


EMP_2022, NE_2022 = table("shugyo_employment_2022"), table("shugyo_not_employed_2022")
EMP_2017, NE_2017 = table("shugyo_employment_2017"), table("shugyo_not_employed_2017")
EMP_2012, NE_2012 = table("shugyo_employment_2012"), table("shugyo_not_employed_2012")
EMP_2007, NE_2007 = table("shugyo_employment_2007"), table("shugyo_not_employed_2007")
AGES = ("total", *(f"{lo}-{lo + 4}" for lo in range(15, 85, 5)), "85-")


def by_key(rows: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    out = {(r["sex"], r["marital"], r["age_class"], r["employment"]): r["persons"] for r in rows}
    assert len(out) == len(rows)
    return out


# ---------------------------------------------------------------------------- registry


def test_registry_has_two_tables_per_wave_with_the_right_layout_and_extension() -> None:
    tables = estat.MARITAL_EMPLOYMENT_TABLES
    assert len(tables) == 8
    assert len({t.key for t in tables}) == 8 and len({t.stat_inf_id for t in tables}) == 8
    assert {t.stat_inf_id for t in tables}.isdisjoint({t.stat_inf_id for t in estat.TABLES})
    assert sorted(t.survey_year for t in tables) == [2007, 2007, 2012, 2012, 2017, 2017, 2022, 2022]
    assert {t.kind for t in tables} == {
        estat.TableKind.MARITAL_EMPLOYMENT,
        estat.TableKind.MARITAL_NOT_EMPLOYED,
    }
    assert (
        EMP_2022.layout is estat.Layout.TIDY and EMP_2022.raw_name == "shugyo_employment_2022.xlsx"
    )
    assert EMP_2017.layout is estat.Layout.TIDY_JE
    assert EMP_2012.layout is estat.Layout.WIDE_XLS and EMP_2012.raw_name.endswith(".xls")
    assert (
        NE_2007.layout is estat.Layout.WIDE_XLS
        and NE_2007.raw_name == "shugyo_not_employed_2007.xls"
    )
    assert all(t.source == "estat_shugyo" and t.url.endswith("fileKind=0") for t in tables)
    assert EMP_2022.url == (
        "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040077274&fileKind=0"
    )
    assert NE_2022.stat_inf_id == "000040077389"
    assert EMP_2017.stat_inf_id == "000031738323" and NE_2017.stat_inf_id == "000031729447"
    assert EMP_2012.stat_inf_id == "000021291492" and NE_2012.stat_inf_id == "000021291719"
    assert EMP_2007.stat_inf_id == "000001234529" and NE_2007.stat_inf_id == "000001234601"
    # the existing tables are untouched
    assert all(t.layout is estat.Layout.TIDY for t in estat.TABLES)


@pytest.mark.parametrize(
    ("label", "code", "lower", "upper"),
    [
        ("20～24", "20-24", 20, 25),  # wide-xls age headers carry no 歳
        ("　15 ～ 19 歳 1)", "15-19", 15, 20),  # footnote marker
        ("85 歳 以 上", "85-", 85, None),
        ("総数　1)", "total", None, None),
    ],
)
def test_parse_age_class_accepts_wide_xls_labels(
    label: str, code: str, lower: int | None, upper: int | None
) -> None:
    ac = estat.parse_age_class(label)
    assert ac is not None
    assert (ac.code, ac.lower, ac.upper) == (code, lower, upper)
    assert estat.parse_age_class("卒業者") is None
    assert estat.parse_age_class("1人") is None


# ---------------------------------------------------------------------------- xls reader


def test_xls_sheets_reads_every_sheet_with_integral_floats_as_integers() -> None:
    sheets = estat.xls_sheets(payload(EMP_2012))
    assert [name for name, _ in sheets] == [f"B016 ({i})" if i > 1 else "B016" for i in range(1, 7)]
    rows = sheets[0][1]
    assert rows[3][8] == "第 16 表"
    assert rows[15][8].startswith("総数") and rows[15][10] == "64420700"
    with pytest.raises(ValueError, match="not an xls"):
        estat.xls_sheets(payload(EMP_2022))
    with pytest.raises(ValueError, match="not an xls"):
        estat.xls_sheets(b"not a workbook")


# ---------------------------------------------------------------------------- tidy (2022)


def test_tidy_employment_2022_keeps_education_and_size_totals_only() -> None:
    rows = estat.marital_employment_rows(payload(EMP_2022), EMP_2022)
    # 3 sexes x 2 marital x 16 ages x 8 employment items (起業者 is dropped)
    assert len(rows) == 3 * 2 * 16 * 8
    assert {r["sex"] for r in rows} == {"total", "male", "female"}
    assert {r["marital"] for r in rows} == {"total", "never_married"}
    assert {r["age_class"] for r in rows} == set(AGES)
    assert {r["employment"] for r in rows} == {
        "employed",
        "employee",
        "regular",
        "nonregular",
        "part_time",
        "arbeit",
        "dispatched",
        "contract",
    }
    assert all(
        r["survey_year"] == 2022
        and r["source"] == "estat_shugyo"
        and r["stat_inf_id"] == "000040077274"
        for r in rows
    )
    by = by_key(rows)
    assert by[("total", "total", "total", "employed")] == 67_060_400
    assert by[("male", "total", "30-34", "employed")] == 3_007_300
    assert by[("male", "total", "30-34", "employee")] == 2_884_100
    assert by[("male", "total", "30-34", "regular")] == 2_496_900
    assert by[("male", "total", "30-34", "nonregular")] == 327_100
    assert by[("male", "never_married", "30-34", "regular")] == 1_094_300
    assert by[("female", "never_married", "25-29", "contract")] == 96_100
    r = next(r for r in rows if r["age_class"] == "30-34")
    assert (r["age_lower"], r["age_upper"]) == (30, 35)
    r = next(r for r in rows if r["age_class"] == "85-")
    assert (r["age_lower"], r["age_upper"]) == (85, None)
    assert rows == estat.marital_employment_rows(payload(EMP_2022), EMP_2022)


def test_tidy_not_employed_2022_keeps_the_total_column_only() -> None:
    rows = estat.marital_employment_rows(payload(NE_2022), NE_2022)
    assert len(rows) == 3 * 2 * 16
    assert {r["employment"] for r in rows} == {"not_employed"}
    assert all(r["stat_inf_id"] == "000040077389" and r["survey_year"] == 2022 for r in rows)
    by = by_key(rows)
    assert by[("total", "total", "total", "not_employed")] == 43_134_800
    assert by[("male", "total", "30-34", "not_employed")] == 265_800
    assert by[("male", "never_married", "30-34", "not_employed")] == 236_500
    assert by[("female", "never_married", "25-29", "not_employed")] == 247_800


# ---------------------------------------------------------------------------- tidy J/E (2017)


def test_tidy_je_2017_reads_dimensions_by_japanese_header_names() -> None:
    rows = estat.marital_employment_rows(payload(EMP_2017), EMP_2017)
    assert len(rows) == 3 * 2 * 16 * 8
    by = by_key(rows)
    assert by[("total", "total", "total", "employed")] == 66_213_000
    assert by[("male", "total", "30-34", "regular")] == 2_721_100
    assert by[("male", "never_married", "30-34", "nonregular")] == 306_700
    assert by[("female", "never_married", "25-29", "dispatched")] == 77_600
    ne = by_key(estat.marital_employment_rows(payload(NE_2017), NE_2017))
    assert len(ne) == 96
    assert ne[("total", "total", "total", "not_employed")] == 44_763_700
    assert ne[("male", "never_married", "30-34", "not_employed")] == 217_600


# ---------------------------------------------------------------------------- wide xls


def test_wide_xls_employment_2012_reads_six_sex_x_marital_panels() -> None:
    rows = estat.marital_employment_rows(payload(EMP_2012), EMP_2012)
    assert len(rows) == 3 * 2 * 16 * 8
    by = by_key(rows)
    assert by[("total", "total", "total", "employed")] == 64_420_700
    assert by[("total", "total", "total", "nonregular")] == 20_427_100
    assert by[("male", "total", "30-34", "employed")] == 3_649_500
    assert by[("male", "total", "30-34", "employee")] == 3_451_200
    assert by[("male", "total", "30-34", "regular")] == 2_875_600
    assert by[("male", "total", "30-34", "nonregular")] == 497_100
    assert by[("male", "never_married", "30-34", "regular")] == 1_148_300
    assert by[("female", "never_married", "25-29", "nonregular")] == 640_600
    assert all(r["survey_year"] == 2012 and r["stat_inf_id"] == "000021291492" for r in rows)


def test_wide_xls_employment_2007_has_no_nonregular_column() -> None:
    rows = estat.marital_employment_rows(payload(EMP_2007), EMP_2007)
    assert {r["employment"] for r in rows} == {
        "employed",
        "employee",
        "regular",
        "part_time",
        "arbeit",
        "dispatched",
        "contract",
    }
    assert len(rows) == 3 * 2 * 16 * 7
    by = by_key(rows)
    assert by[("male", "total", "30-34", "employed")] == 4_415_900
    assert by[("male", "total", "30-34", "employee")] == 4_154_700
    assert by[("male", "total", "30-34", "regular")] == 3_568_200
    assert by[("male", "total", "30-34", "part_time")] == 44_500
    assert by[("male", "total", "30-34", "arbeit")] == 129_700
    assert by[("male", "total", "30-34", "dispatched")] == 91_300
    assert by[("male", "total", "30-34", "contract")] == 133_800
    assert by[("male", "never_married", "30-34", "regular")] == 1_450_600


def test_wide_xls_not_employed_derives_both_sexes_never_married_from_male_plus_female() -> None:
    by = by_key(estat.marital_employment_rows(payload(NE_2012), NE_2012))
    assert len(by) == 96
    assert by[("total", "total", "total", "not_employed")] == 46_394_400
    assert by[("male", "total", "total", "not_employed")] == 16_668_700
    assert by[("male", "never_married", "total", "not_employed")] == 5_981_800
    assert by[("female", "never_married", "total", "not_employed")] == 5_043_300
    assert by[("total", "never_married", "total", "not_employed")] == 5_981_800 + 5_043_300
    by07 = by_key(estat.marital_employment_rows(payload(NE_2007), NE_2007))
    assert by07[("total", "total", "total", "not_employed")] == 44_324_000
    assert by07[("total", "never_married", "total", "not_employed")] == 5_666_600 + 4_949_100
    assert by07[("male", "total", "30-34", "not_employed")] == 310_600


# ---------------------------------------------------------------------------- fail closed


def tidy_xlsx(rows: list[dict[int, object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for i, r in enumerate(rows, start=1):
        for c, v in r.items():
            ws.cell(row=i, column=c, value=v)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def minimal_tidy(*, item: str = "0_総数", dim: str = "教育", age: str = "00_総数") -> bytes:
    """A one-row 2022-style 無業者 table."""
    return tidy_xlsx(
        [
            {1: "第１１８表　男女、配偶関係、年齢、教育、就業希望の有無別人口（無業者）"},
            {5: "項目名", 6: item},
            {1: "地域区分", 2: "男女", 3: "配偶関係", 4: "年齢", 5: dim, 6: " "},
            {1: "00_全国", 2: "0_総数", 3: "0_総数", 4: age, 5: "0_総数", 6: 5},
        ]
    )


def test_wrong_table_or_layout_fails_closed() -> None:
    with pytest.raises(ValueError, match="title"):
        estat.marital_employment_rows(payload(NE_2022), EMP_2022)
    with pytest.raises(ValueError, match="title"):
        estat.marital_employment_rows(payload(EMP_2012), NE_2012)
    with pytest.raises(ValueError, match="not an xls"):
        estat.marital_employment_rows(payload(EMP_2022), EMP_2012)
    with pytest.raises(ValueError, match="not an xlsx"):
        estat.marital_employment_rows(payload(EMP_2012), EMP_2022)
    with pytest.raises(ValueError, match="not a 就業構造基本調査"):
        estat.marital_employment_rows(payload(EMP_2022), estat.TABLES[0])
    with pytest.raises(ValueError, match="unknown dimension"):
        estat.marital_employment_rows(minimal_tidy(dim="産業"), NE_2022)
    with pytest.raises(ValueError, match="unexpected .*item"):
        estat.marital_employment_rows(minimal_tidy(item="9_不詳"), NE_2022)
    with pytest.raises(ValueError, match="年齢"):
        estat.marital_employment_rows(minimal_tidy(age="99_不詳"), NE_2022)
    with pytest.raises(ValueError, match="header"):
        estat.marital_employment_rows(
            tidy_xlsx([{1: "第１１８表 配偶関係 就業希望（無業者）"}]), NE_2022
        )


# ---------------------------------------------------------------------------- wave checks


def row(
    sex: str, marital: str, age: str, employment: str, persons: float | None, year: int = 2022
) -> dict[str, object]:
    lo = None if age == "total" else int(age.split("-")[0])
    return {
        "survey_year": year,
        "sex": sex,
        "marital": marital,
        "age_class": age,
        "age_lower": lo,
        "age_upper": None if lo is None or age.endswith("-") else lo + 5,
        "employment": employment,
        "persons": persons,
        "source": "estat_shugyo",
        "stat_inf_id": "000000000000",
    }


K = 10_000  # scale so the rounding-aware tolerance (100 persons per cell) does not mask errors


def small_wave(**override: float) -> list[dict[str, object]]:
    """Consistent 2-age world: male/female x total/never_married x employed-side items."""
    base: dict[tuple[str, str, str, str], float] = {}
    for sex, mult in (("male", 1.0), ("female", 2.0)):
        for marital, m in (("total", 1.0), ("never_married", 0.5)):
            for age, a in (("25-29", 1.0), ("30-34", 3.0)):
                k = mult * m * a * K
                base[(sex, marital, age, "employed")] = 100 * k
                base[(sex, marital, age, "employee")] = 80 * k
                base[(sex, marital, age, "regular")] = 50 * k
                base[(sex, marital, age, "nonregular")] = 20 * k
                base[(sex, marital, age, "not_employed")] = 10 * k
    # totals over sexes and ages
    out: dict[tuple[str, str, str, str], float] = dict(base)
    for (_sex, marital, age, emp), v in base.items():
        out[("total", marital, age, emp)] = out.get(("total", marital, age, emp), 0) + v
    for (sex, marital, age, emp), v in list(out.items()):
        if age != "total":
            out[(sex, marital, "total", emp)] = out.get((sex, marital, "total", emp), 0) + v
    for key, v in override.items():
        sex, marital, age, emp = key.split("__")
        out[(sex, marital, age.replace("_", "-"), emp)] = v
    return [row(*k, v) for k, v in out.items()]


def test_with_total_pop_adds_employed_plus_not_employed() -> None:
    rows = estat.with_total_pop(small_wave())
    by = by_key(rows)
    assert by[("male", "total", "25-29", "total_pop")] == 110 * K
    assert (
        by[("total", "never_married", "total", "total_pop")] == (100 + 10) * 0.5 * (1 + 3) * 3 * K
    )
    assert len(rows) == len(small_wave()) + 3 * 2 * 3
    estat.check_marital_wave(rows)  # consistent -> no error


def test_check_marital_wave_rejects_each_inconsistency() -> None:
    with pytest.raises(ValueError, match="うち未婚"):
        estat.check_marital_wave(small_wave(male__never_married__25_29__employed=101 * K))
    with pytest.raises(ValueError, match="雇用者"):
        estat.check_marital_wave(small_wave(male__total__25_29__regular=61 * K))
    with pytest.raises(ValueError, match="age classes"):
        estat.check_marital_wave(small_wave(male__total__total__employed=410 * K))
    with pytest.raises(ValueError, match="male \\+ female"):
        estat.check_marital_wave(
            small_wave(male__total__25_29__employee=100 * K, male__total__total__employee=340 * K)
        )
    with pytest.raises(ValueError, match="age class"):
        estat.check_marital_wave([r for r in small_wave() if r["age_class"] != "30-34"])
    # within 0.5 % is accepted (published cells are rounded to 100 persons)
    estat.check_marital_wave(small_wave(male__total__total__employed=400.4 * K))
    # None (not published) is skipped, not an error
    estat.check_marital_wave(small_wave(male__total__25_29__nonregular=None))


def test_marital_wave_rows_combines_both_tables_and_checks_them() -> None:
    rows = estat.marital_wave_rows(payload(EMP_2022), EMP_2022, payload(NE_2022), NE_2022)
    by = by_key(rows)
    assert len(rows) == 3 * 2 * 16 * (8 + 1 + 1)
    assert by[("male", "total", "30-34", "total_pop")] == 3_007_300 + 265_800
    assert by[("male", "never_married", "30-34", "total_pop")] == 1_447_600 + 236_500
    tp = next(r for r in rows if r["employment"] == "total_pop")
    assert tp["stat_inf_id"] == "000040077274" and tp["source"] == "estat_shugyo"
    with pytest.raises(ValueError, match="title"):
        estat.marital_wave_rows(payload(NE_2022), EMP_2022, payload(NE_2022), NE_2022)
    with pytest.raises(ValueError, match="survey_year"):
        estat.marital_wave_rows(payload(EMP_2022), EMP_2022, payload(NE_2017), NE_2017)
    for emp, ne in ((EMP_2017, NE_2017), (EMP_2012, NE_2012), (EMP_2007, NE_2007)):
        assert len(estat.marital_wave_rows(payload(emp), emp, payload(ne), ne)) > 0


# ---------------------------------------------------------------------------- mart


def test_build_marital_employment_mart_sorts_by_declared_order_and_rejects_duplicates() -> None:
    rows = estat.with_total_pop(small_wave()) + [
        r | {"survey_year": 2007} for r in estat.with_total_pop(small_wave())
    ]
    mart = estat.build_marital_employment_mart(reversed(rows))
    assert len(mart) == len(rows)
    assert [r["survey_year"] for r in mart] == sorted(r["survey_year"] for r in mart)
    first = mart[0]
    assert (first["survey_year"], first["sex"], first["age_class"], first["employment"]) == (
        2007,
        "total",
        "total",
        "total_pop",
    )
    assert [r["marital"] for r in mart[:2]] == ["total", "never_married"]
    assert [r["employment"] for r in mart[:12:2]] == [
        "total_pop",
        "employed",
        "employee",
        "regular",
        "nonregular",
        "not_employed",
    ]
    assert [r["sex"] for r in mart if r["age_class"] == "total" and r["survey_year"] == 2007][
        ::12
    ] == ["total", "male", "female"]
    with pytest.raises(ValueError, match="duplicate"):
        estat.build_marital_employment_mart(rows + rows[:1])
