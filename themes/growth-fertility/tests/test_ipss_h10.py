"""ipss.py (H10): 人口統計資料集 2026 の婚姻時系列 3 表（T06-24 / T06-12 / T06-23）と
都道府県表 6 表（T12-33★ / T12-35 / T12-36 / T12-37 / T12-52 / T12-53）-> long rows (pure,
fail-closed), plus the two marts. Fixtures are the real workbooks re-saved with only the sheets
the parsers read (every row kept; the tables are 54 rows at most)."""

from pathlib import Path

import pytest

from theme_growth_fertility import ipss, prefecture

FIXTURES = Path(__file__).parent / "fixtures"
Rows = list[dict[int, str]]


def table(code: str) -> ipss.Table:
    return next(t for t in ipss.TABLES if t.code == code)


def payload(code: str) -> bytes:
    return (FIXTURES / f"ipss_{code}.xlsx").read_bytes()


def sheet(code: str) -> Rows:
    return ipss.sheet_rows(payload(code), table(code).sheet)


def marriage_keyed(rs: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    out = {(r["year"], r["metric"], r["sex"], r["age_class"]): r["value"] for r in rs}
    assert len(out) == len(rs)
    return out


def panel_keyed(rs: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    out = {
        (r["pref_code"], r["year"], r["metric"], r["sex"], r["age_class"]): r["value"] for r in rs
    }
    assert len(out) == len(rs)
    return out


# ---- registry ------------------------------------------------------------------------------


def test_h10_tables_are_appended_after_the_h9_tables_with_their_sheets_and_marts() -> None:
    codes = [t.code for t in ipss.TABLES]
    assert codes[:7] == ["T04-25", "T04-24", "T04-23", "T04-15", "T04-16", "T04-09", "T04-11"]
    assert codes[7:] == [
        "T06-24",
        "T06-12",
        "T06-23",
        "T12-33",
        "T12-35",
        "T12-36",
        "T12-37",
        "T12-52",
        "T12-53",
    ]
    assert table("T06-24").sheet == "T06-24(1)" and table("T06-24").mart == "marriage"
    assert table("T06-12").key == "t06_12" and table("T06-12").mart == "marriage"
    assert table("T12-33").sheet == "T12-33★" and table("T12-33").mart == "prefecture"
    assert table("T12-35").sheet == "T12-35(1)"
    assert table("T12-52").sheet == "T12-52(1)"
    assert table("T12-53").url == (
        "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/T12-53.xlsx"
    )
    assert {t.mart for t in ipss.TABLES} == {"survey", "births", "marriage", "prefecture"}
    assert ipss.MARRIAGE_METRICS == (
        "never_married_share",
        "mean_age_marriage_all",
        "mean_age_first_marriage",
        "never_married_at_50",
    )


# ---- T06-24(1): 性・年齢（5 歳階級）別 未婚割合 --------------------------------------------


def test_never_married_share_rows_cover_11_census_years_x_2_sexes_x_16_age_classes() -> None:
    rows = ipss.never_married_share_rows(sheet("T06-24"))
    assert len(rows) == 11 * 2 * 16
    assert set(rows[0]) == {"year", "metric", "sex", "age_class", "value", "table", "source"}
    assert all(r["metric"] == "never_married_share" and r["table"] == "T06-24" for r in rows)
    assert all(r["source"] == "ipss" for r in rows)
    k = marriage_keyed(rows)
    assert k[(1920, "never_married_share", "M", "total")] == 29.3
    assert k[(2020, "never_married_share", "M", "30-34")] == 51.8
    assert k[(2020, "never_married_share", "F", "25-29")] == 65.8
    assert k[(1950, "never_married_share", "F", "85-")] == 0.0
    assert sorted({r["year"] for r in rows}) == [
        1920,
        1930,
        1950,
        1960,
        1970,
        1980,
        1990,
        2000,
        2010,
        2015,
        2020,
    ]
    assert list(dict.fromkeys(r["age_class"] for r in rows)) == [
        "total",
        "15-19",
        "20-24",
        "25-29",
        "30-34",
        "35-39",
        "40-44",
        "45-49",
        "50-54",
        "55-59",
        "60-64",
        "65-69",
        "70-74",
        "75-79",
        "80-84",
        "85-",
    ]


def test_never_married_share_rows_fail_closed_on_title_sheet_or_age_order() -> None:
    rows = sheet("T06-24")
    with pytest.raises(ValueError, match="title"):
        ipss.never_married_share_rows([{1: "表６－２５ 別の表"}, *rows[1:]])
    with pytest.raises(ValueError, match="未婚"):
        ipss.never_married_share_rows([rows[0], {1: "(2) 有配偶 "}, *rows[2:]])
    broken = [dict(r) for r in rows]
    broken[5], broken[6] = broken[6], broken[5]  # 15-19 and 20-24 swapped
    with pytest.raises(ValueError, match="age"):
        ipss.never_married_share_rows(broken)
    with pytest.raises(ValueError, match="year"):
        ipss.never_married_share_rows([*rows[:2], {**rows[2], 12: "2021年"}, *rows[3:]])


# ---- T06-12: 全婚姻・初婚の平均婚姻年齢 (two column blocks) ----------------------------------


def test_mean_marriage_age_rows_join_the_two_column_blocks_and_skip_dots() -> None:
    rows = ipss.mean_marriage_age_rows(sheet("T06-12"))
    k = marriage_keyed(rows)
    assert len(rows) == 70 * 4 - 3 * 2 - 2 * 2  # 初婚 '…' 1899-1905, 全婚姻 '…' 1947/1950
    assert all(r["age_class"] is None and r["table"] == "T06-12" for r in rows)
    assert k[(1899, "mean_age_marriage_all", "M", None)] == 27.6
    assert k[(1899, "mean_age_marriage_all", "F", None)] == 23.0
    assert (1899, "mean_age_first_marriage", "M", None) not in k
    assert (1947, "mean_age_marriage_all", "M", None) not in k
    assert k[(1947, "mean_age_first_marriage", "F", None)] == 22.9
    assert k[(1989, "mean_age_first_marriage", "M", None)] == 28.5
    assert k[(1990, "mean_age_first_marriage", "M", None)] == 28.4  # first row of the right block
    assert k[(2024, "mean_age_first_marriage", "F", None)] == 29.8
    assert k[(2024, "mean_age_marriage_all", "M", None)] == 33.8
    years = sorted({r["year"] for r in rows})
    assert years[0] == 1899 and years[-1] == 2024 and years[-35:] == list(range(1990, 2025))


def test_mean_marriage_age_rows_fail_closed_on_header_or_year_gap() -> None:
    rows = sheet("T06-12")
    with pytest.raises(ValueError, match="header"):
        ipss.mean_marriage_age_rows([*rows[:3], {**rows[3], 6: "夫"}, *rows[4:]])
    # the right block must continue from the left block's last year
    with pytest.raises(ValueError, match="1990"):
        ipss.mean_marriage_age_rows([*rows[:4], {**rows[4], 8: "1991"}, *rows[5:]])
    with pytest.raises(ValueError, match="non-numeric"):
        ipss.mean_marriage_age_rows([*rows[:10], {**rows[10], 2: "n/a"}, *rows[11:]])


# ---- T06-23: 性別 50 歳時未婚割合 ----------------------------------------------------------


def test_never_married_at_50_rows_are_12_years_x_2_sexes() -> None:
    rows = ipss.never_married_at_50_rows(sheet("T06-23"))
    assert len(rows) == 12 * 2
    k = marriage_keyed(rows)
    assert k[(1920, "never_married_at_50", "M", None)] == 2.17
    assert k[(2015, "never_married_at_50", "M", None)] == 24.77
    assert k[(2020, "never_married_at_50", "F", None)] == 17.81
    assert all(r["table"] == "T06-23" for r in rows)
    with pytest.raises(ValueError, match="years"):
        ipss.never_married_at_50_rows(sheet("T06-23")[:-3])


# ---- T12-33★: 都道府県別 TFR, every year ----------------------------------------------------


def test_pref_tfr_rows_keep_published_years_only_and_code_the_prefectures() -> None:
    rows = ipss.pref_tfr_rows(sheet("T12-33"))
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
    assert all(r["metric"] == "tfr" and r["sex"] == "T" and r["age_class"] is None for r in rows)
    k = panel_keyed(rows)
    assert k[("00", 1925, "tfr", "T", None)] == 5.1
    assert k[("00", 2024, "tfr", "T", None)] == 1.15
    assert k[("01", 1950, "tfr", "T", None)] == 4.59
    assert ("01", 1951, "tfr", "T", None) not in k  # '…'
    assert k[("13", 1925, "tfr", "T", None)] == 4.08
    assert k[("47", 1930, "tfr", "T", None)] == 3.69
    assert ("47", 1950, "tfr", "T", None) not in k
    assert {r["pref_code"] for r in rows} == {"00", *prefecture.PREF_CODES.values()}
    assert {r["pref_name"] for r in rows if r["pref_code"] == "47"} == {"沖縄"}
    assert len([r for r in rows if r["pref_code"] == "00"]) == 77  # 1925, 1930, 1950-2024
    # the unnamed 全国 (5-year-class) row right under 全国 is not a prefecture: skipped
    assert len([r for r in rows if r["pref_code"] == "00" and r["year"] == 1925]) == 1


def test_pref_tfr_rows_fail_closed_on_prefecture_order_or_missing_prefecture() -> None:
    rows = sheet("T12-33")
    with pytest.raises(ValueError, match="prefecture"):
        ipss.pref_tfr_rows([*rows[:5], {**rows[5], 1: "青森"}, *rows[6:]])
    with pytest.raises(ValueError, match="prefecture"):
        ipss.pref_tfr_rows(rows[:-6])
    with pytest.raises(ValueError, match="header"):
        ipss.pref_tfr_rows([rows[0], {**rows[1], 2: "1920年"}, *rows[2:]])


# ---- T12-35 / T12-37 / T12-52: two or four sheets per workbook -----------------------------


def test_pref_first_marriage_age_rows_read_both_sex_sheets() -> None:
    rows = ipss.pref_first_marriage_age_rows(payload("T12-35"))
    assert len(rows) == 9 * 48 * 2 - 3 * 2  # 沖縄 1950/1960/1970 are '...'
    k = panel_keyed(rows)
    assert k[("00", 1950, "mean_age_first_marriage", "M", None)] == 25.9
    assert k[("13", 2024, "mean_age_first_marriage", "M", None)] == 32.2
    assert k[("13", 2020, "mean_age_first_marriage", "F", None)] == 30.4
    assert k[("47", 1980, "mean_age_first_marriage", "F", None)] == 25.2
    assert ("47", 1950, "mean_age_first_marriage", "F", None) not in k
    assert all(r["table"] == "T12-35" for r in rows)


def test_pref_never_married_young_rows_use_the_spec_metric_names() -> None:
    rows = ipss.pref_never_married_young_rows(sheet("T12-36"))
    assert len(rows) == 5 * 48 * 2
    k = panel_keyed(rows)
    assert k[("00", 2020, "never_married_m30_34", "M", "30-34")] == 51.8
    assert k[("13", 2020, "never_married_m30_34", "M", "30-34")] == 58.8
    assert k[("47", 2020, "never_married_m30_34", "M", "30-34")] == 48.5
    assert k[("05", 2020, "never_married_m30_34", "M", "30-34")] == 53.7
    assert k[("13", 2020, "never_married_f25_29", "F", "25-29")] == 75.5
    assert k[("47", 1970, "never_married_f25_29", "F", "25-29")] == 28.7
    assert sorted({r["year"] for r in rows}) == [1970, 1990, 2010, 2015, 2020]
    with pytest.raises(ValueError, match="header"):
        ipss.pref_never_married_young_rows(
            [*sheet("T12-36")[:3], {**sheet("T12-36")[3], 6: "2021年"}, *sheet("T12-36")[4:]]
        )


def test_pref_never_married_at_50_rows_read_both_sex_sheets() -> None:
    rows = ipss.pref_never_married_at_50_rows(payload("T12-37"))
    k = panel_keyed(rows)
    assert k[("00", 2020, "never_married_at_50", "M", None)] == 28.25
    assert k[("00", 1920, "never_married_at_50", "F", None)] == 1.8
    assert k[("01", 2020, "never_married_at_50", "F", None)] == 20.36
    assert sorted({r["year"] for r in rows}) == [
        1920,
        1930,
        1940,
        1950,
        1970,
        1990,
        2000,
        2005,
        2010,
        2015,
        2020,
    ]
    assert len([r for r in rows if r["pref_code"] == "00"]) == 22
    assert len(rows) <= 11 * 48 * 2
    assert all(r["table"] == "T12-37" for r in rows)


def test_pref_lfp_rows_read_the_four_year_sheets_x_sex_x_age_class() -> None:
    rows = ipss.pref_lfp_rows(payload("T12-52"))
    assert len(rows) == 4 * 48 * 2 * 5
    k = panel_keyed(rows)
    assert k[("00", 1980, "lfp", "M", "total")] == 82.2
    assert k[("00", 2020, "lfp", "F", "30-44")] == 79.6
    assert k[("01", 2000, "lfp", "F", "60-")] == 17.0
    assert k[("03", 2010, "lfp", "M", "15-29")] == 60.6
    assert sorted({r["year"] for r in rows}) == [1980, 2000, 2010, 2020]
    assert {r["age_class"] for r in rows} == {"total", "15-29", "30-44", "45-59", "60-"}
    assert all(r["table"] == "T12-52" for r in rows)


def test_pref_unemployment_rows_are_6_years_x_2_sexes_x_48() -> None:
    rows = ipss.pref_unemployment_rows(sheet("T12-53"))
    assert len(rows) == 6 * 48 * 2
    k = panel_keyed(rows)
    assert k[("00", 2010, "unemployment_rate", "M", None)] == 7.4
    assert k[("02", 2010, "unemployment_rate", "M", None)] == 10.6
    assert k[("00", 2020, "unemployment_rate", "F", None)] == 3.3
    assert sorted({r["year"] for r in rows}) == [1980, 1990, 2000, 2010, 2015, 2020]


# ---- dispatch -------------------------------------------------------------------------------


def test_parse_table_dispatches_every_h10_table_including_multi_sheet_ones() -> None:
    counts = {t.code: len(ipss.parse_table(payload(t.code), t)) for t in ipss.TABLES[7:]}
    assert counts["T06-24"] == 352 and counts["T06-23"] == 24
    assert counts["T12-35"] == 858 and counts["T12-36"] == 480
    assert counts["T12-52"] == 1920 and counts["T12-53"] == 576
    with pytest.raises(ValueError):
        ipss.parse_table(payload("T06-23"), table("T06-24"))  # wrong workbook -> no such sheet


# ---- marts -----------------------------------------------------------------------------------


def test_build_marriage_mart_combines_sorts_and_rejects_duplicates() -> None:
    parts = {
        "t06_24": ipss.never_married_share_rows(sheet("T06-24")),
        "t06_12": ipss.mean_marriage_age_rows(sheet("T06-12")),
        "t06_23": ipss.never_married_at_50_rows(sheet("T06-23")),
    }
    mart = ipss.build_marriage_mart(parts)
    assert len(mart) == 352 + 270 + 24
    assert set(mart[0]) == {"year", "metric", "sex", "age_class", "value", "table", "source"}
    keys = [(r["year"], r["metric"], r["sex"], r["age_class"]) for r in mart]
    assert len(set(keys)) == len(keys)
    assert keys == sorted(
        keys,
        key=lambda k: (
            int(str(k[0])),
            ipss.MARRIAGE_METRICS.index(str(k[1])),
            str(k[2]),
            "" if k[3] is None else str(k[3]),
        ),
    )
    assert mart[0]["year"] == 1899 and mart[0]["metric"] == "mean_age_marriage_all"
    assert {r["metric"] for r in mart} == set(ipss.MARRIAGE_METRICS)
    with pytest.raises(ValueError, match="duplicate"):
        ipss.build_marriage_mart({"a": parts["t06_23"], "b": parts["t06_23"][:1]})
