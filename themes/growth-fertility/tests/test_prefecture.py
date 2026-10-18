"""prefecture.py (H10): prefecture codes, 就業構造基本調査 時系列統計表 第18表 (雇用形態別
有業者数, 1977–2022) and 住宅・土地統計調査 時系列 第34-2表 (1 か月当たり家賃, 1993–2023)
-> long rows (pure, fail-closed), and the prefecture panel mart. Fixtures are the real e-Stat
workbooks with the 政令指定都市 rows dropped."""

from pathlib import Path

import pytest

from theme_growth_fertility import cao, ipss, prefecture

FIXTURES = Path(__file__).parent / "fixtures"


def keyed(rs: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    out = {
        (r["pref_code"], r["year"], r["metric"], r["sex"], r["age_class"]): r["value"] for r in rs
    }
    assert len(out) == len(rs)
    return out


# ---- codes -------------------------------------------------------------------------------------


def test_pref_codes_are_the_47_jis_codes_in_order() -> None:
    assert len(prefecture.PREF_CODES) == 47
    assert list(prefecture.PREF_CODES.items())[:3] == [
        ("北海道", "01"),
        ("青森", "02"),
        ("岩手", "03"),
    ]
    assert prefecture.PREF_CODES["東京"] == "13"
    assert prefecture.PREF_CODES["京都"] == "26"
    assert prefecture.PREF_CODES["沖縄"] == "47"
    assert prefecture.PREF_NAMES[12] == "東京" and len(prefecture.PREF_NAMES) == 47
    assert prefecture.NATIONAL_CODE == "00" and prefecture.NATIONAL_NAME == "全国"


def test_pref_code_normalises_suffixes_spaces_and_national_labels() -> None:
    assert prefecture.pref_code("北 海 道") == "01"
    assert prefecture.pref_code("青 森 県") == "02"
    assert prefecture.pref_code("東京都") == "13"
    assert prefecture.pref_code("京都府") == "26"
    assert prefecture.pref_code("大阪府") == "27"
    assert prefecture.pref_code("沖縄") == "47"
    assert prefecture.pref_code("全     国") == "00"
    assert prefecture.pref_code("全県計") == "00"
    assert prefecture.pref_code("京都市") is None
    assert prefecture.pref_code("関東") is None
    assert prefecture.pref_name("13") == "東京" and prefecture.pref_name("00") == "全国"


# ---- 就業構造基本調査 時系列 第18表 -----------------------------------------------------------


def test_employment_table_url_and_raw_name() -> None:
    assert prefecture.SHUGYO_TS18_URL == (
        "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031732282&fileKind=4"
    )
    assert prefecture.SHUGYO_TS18_RAW_NAME == "shugyo_ts18_employment.xlsx"
    assert prefecture.SHUGYO_TS18_SOURCE == "estat_shugyo"
    assert prefecture.JUTAKU_URL == (
        "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040354073&fileKind=4"
    )
    assert prefecture.JUTAKU_RAW_NAME == "jutaku_34_2_rent.xlsx"
    assert prefecture.JUTAKU_SOURCE == "estat_jutaku"
    assert "政府標準利用規約" in prefecture.LICENSE


def test_employment_rows_long_by_prefecture_sex_year_and_status() -> None:
    rows = prefecture.employment_rows((FIXTURES / "estat_shugyo_ts18.xlsx").read_bytes())
    assert set(rows[0]) == {
        "pref_code",
        "pref_name",
        "year",
        "metric",
        "sex",
        "age_class",
        "value",
        "table",
        "source",
    }
    # 48 regions x 3 sexes x 10 surveys x 4 metrics, minus 1977 正規/非正規 (not surveyed)
    assert len(rows) == 48 * 3 * 10 * 4 - 48 * 3 * 2
    k = keyed(rows)
    assert k[("00", 1977, "employed", "T", None)] == 53649000
    assert k[("00", 2022, "employed", "T", None)] == 67060400
    assert k[("00", 2022, "regular_employees", "T", None)] == 36114600
    assert k[("00", 2022, "nonregular_employees", "T", None)] == 21110300
    assert k[("00", 2022, "nonregular_employees", "M", None)] == 6642400
    assert k[("00", 2022, "nonregular_employees", "F", None)] == 14467900
    assert k[("01", 2022, "employed", "T", None)] == 2629600
    assert k[("47", 1977, "employed", "T", None)] == 389000
    assert ("00", 1977, "regular_employees", "T", None) not in k
    assert sorted({r["year"] for r in rows}) == [
        1977,
        1982,
        1987,
        1992,
        1997,
        2002,
        2007,
        2012,
        2017,
        2022,
    ]
    assert {r["pref_code"] for r in rows} == {"00", *prefecture.PREF_CODES.values()}
    assert all(r["table"] == "時系列18" and r["source"] == "estat_shugyo" for r in rows)
    assert all(isinstance(r["value"], int) for r in rows)
    # employees >= regular + nonregular in every cell that has both
    for code in ("00", "13", "47"):
        for sex in ("T", "M", "F"):
            emp = k[(code, 2022, "employees", sex, None)]
            reg = k[(code, 2022, "regular_employees", sex, None)]
            non = k[(code, 2022, "nonregular_employees", sex, None)]
            assert isinstance(emp, int) and isinstance(reg, int) and isinstance(non, int)
            assert emp >= reg + non


def test_employment_rows_fail_closed_on_title_years_or_prefecture_list() -> None:
    raw = (FIXTURES / "estat_shugyo_ts18.xlsx").read_bytes()
    rows = prefecture.sheet_rows(raw, "Z018")
    with pytest.raises(ValueError, match="title"):
        prefecture.employment_rows_from_sheet([*rows[:3], {**rows[3], 24: "第 19 表"}, *rows[4:]])
    with pytest.raises(ValueError, match="year"):
        prefecture.employment_rows_from_sheet([*rows[:11], {**rows[11], 21: "2023"}, *rows[12:]])
    with pytest.raises(ValueError, match="prefecture"):
        prefecture.employment_rows_from_sheet(rows[:40])
    with pytest.raises(ValueError, match="employees"):
        prefecture.employment_rows_from_sheet([*rows[:13], {**rows[13], 51: "1"}, *rows[14:]])
    with pytest.raises(ValueError, match="xlsx"):
        prefecture.employment_rows(b"not an xlsx")


# ---- 住宅・土地統計調査 時系列 第34-2表 -------------------------------------------------------


def test_rent_rows_one_sheet_per_survey_year_with_layout_specific_columns() -> None:
    rows = prefecture.rent_rows((FIXTURES / "estat_jutaku_34_2.xlsx").read_bytes())
    k = keyed(rows)
    # rent every year; 民営借家 total only 2018/2023; wood 2003-; non-wood every year
    assert len(rows) == 48 * (7 + 2 + 5 + 7)
    assert k[("00", 1993, "rent", "T", None)] == 44763
    assert k[("00", 1993, "rent_private_nonwood", "T", None)] == 65309
    assert ("00", 1993, "rent_private", "T", None) not in k
    assert ("00", 1993, "rent_private_wood", "T", None) not in k
    assert k[("00", 2013, "rent", "T", None)] == 54040
    assert k[("00", 2013, "rent_private_wood", "T", None)] == 51030
    assert k[("00", 2013, "rent_private_nonwood", "T", None)] == 63005
    assert k[("01", 2018, "rent", "T", None)] == 41700
    assert k[("00", 2023, "rent", "T", None)] == 59643
    assert k[("00", 2023, "rent_private", "T", None)] == 64819
    assert k[("00", 2023, "rent_private_wood", "T", None)] == 54409
    assert k[("00", 2023, "rent_private_nonwood", "T", None)] == 68548
    assert k[("13", 1993, "rent", "T", None)] == 66708
    assert k[("47", 2023, "rent", "T", None)] == 49400
    assert sorted({r["year"] for r in rows}) == [1993, 1998, 2003, 2008, 2013, 2018, 2023]
    assert {r["pref_code"] for r in rows} == {"00", *prefecture.PREF_CODES.values()}
    assert all(r["table"] == "時系列34-2" and r["source"] == "estat_jutaku" for r in rows)
    assert all(isinstance(r["value"], int) for r in rows)


def test_rent_rows_fail_closed_on_missing_sheet_header_or_prefecture_count() -> None:
    raw = (FIXTURES / "estat_jutaku_34_2.xlsx").read_bytes()
    sheets = {s: prefecture.sheet_rows(raw, s) for s in prefecture.RENT_SHEETS}
    with pytest.raises(ValueError, match="header"):
        bad = dict(sheets)
        bad["令和５年"] = [*sheets["令和５年"][:8], {**sheets["令和５年"][8], 5: "平均"}]
        bad["令和５年"] += sheets["令和５年"][9:]
        prefecture.rent_rows_from_sheets(bad)
    with pytest.raises(ValueError, match="prefecture"):
        bad = dict(sheets)
        bad["平成5年"] = sheets["平成5年"][:60]
        prefecture.rent_rows_from_sheets(bad)
    with pytest.raises(ValueError, match="sheet"):
        prefecture.rent_rows_from_sheets({s: r for s, r in sheets.items() if s != "平成5年"})
    with pytest.raises(ValueError, match="xlsx"):
        prefecture.rent_rows(b"not an xlsx")


# ---- mart ------------------------------------------------------------------------------------


def test_build_prefecture_mart_combines_every_source_sorts_and_rejects_duplicates() -> None:
    ipss_payload = (FIXTURES / "ipss_T12-36.xlsx").read_bytes()
    t12_36 = next(t for t in ipss.TABLES if t.code == "T12-36")
    parts = {
        "t12_36": ipss.parse_table(ipss_payload, t12_36),
        "shugyo": prefecture.employment_rows((FIXTURES / "estat_shugyo_ts18.xlsx").read_bytes()),
        "rent": prefecture.rent_rows((FIXTURES / "estat_jutaku_34_2.xlsx").read_bytes()),
        "income": cao.income_rows((FIXTURES / "cao_soukatu7.xlsx").read_bytes()),
    }
    mart = prefecture.build_prefecture_mart(parts)
    assert len(mart) == sum(len(v) for v in parts.values())
    assert set(mart[0]) == {
        "pref_code",
        "pref_name",
        "year",
        "metric",
        "sex",
        "age_class",
        "value",
        "table",
        "source",
    }
    keys = [(r["pref_code"], r["year"], r["metric"], r["sex"], r["age_class"]) for r in mart]
    assert len(set(keys)) == len(keys)
    assert keys == sorted(
        keys,
        key=lambda k: (
            str(k[0]),
            int(str(k[1])),
            prefecture.PANEL_METRICS.index(str(k[2])),
            str(k[3]),
            "" if k[4] is None else str(k[4]),
        ),
    )
    assert mart[0]["pref_code"] == "00" and mart[0]["year"] == 1970
    assert {r["metric"] for r in mart} <= set(prefecture.PANEL_METRICS)
    # every source agrees on the prefecture name for a code
    names = {(r["pref_code"], r["pref_name"]) for r in mart}
    assert len(names) == 48 and ("13", "東京") in names and ("00", "全国") in names
    assert all(isinstance(r["value"], float) for r in mart)  # one Parquet type for the column
    with pytest.raises(ValueError, match="duplicate"):
        prefecture.build_prefecture_mart({"a": parts["income"], "b": parts["income"][:1]})
    with pytest.raises(ValueError, match="metric"):
        prefecture.build_prefecture_mart({"a": [{**parts["income"][0], "metric": "gdp"}]})
