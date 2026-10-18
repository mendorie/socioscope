"""ipss.py: IPSS 人口統計資料集 2026 (7 xlsx tables) and 第16回出生動向基本調査
結果の概要 PDF (figure data labels) -> long rows (pure, fail-closed).

xlsx fixtures are the real workbooks re-saved with only the worksheet the parser reads (the ★
sheet carries every year); the PDF fixture is the pypdf text of the two figure pages.
"""

from pathlib import Path

import pytest

from theme_growth_fertility import ipss

FIXTURES = Path(__file__).parent / "fixtures"
Rows = list[dict[int, str]]


def table(code: str) -> ipss.Table:
    return next(t for t in ipss.TABLES if t.code == code)


def payload(code: str) -> bytes:
    return (FIXTURES / f"ipss_{code}.xlsx").read_bytes()


def sheet(code: str) -> Rows:
    return ipss.sheet_rows(payload(code), table(code).sheet)


def pdf_pages() -> list[str]:
    return (FIXTURES / "ipss_jnfs16_gaiyo.txt").read_text(encoding="utf-8").split("\f")


def survey_keyed(rs: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    out = {(r["survey_year"], r["metric"], r["group"], r["birth_cohort"]): r["value"] for r in rs}
    assert len(out) == len(rs)
    return out


def births_keyed(rs: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    out = {(r["year"], r["metric"], r["group"], r["cohort"]): r["value"] for r in rs}
    assert len(out) == len(rs)
    return out


# ---- registry ------------------------------------------------------------------------------


def test_tables_registry_urls_sheets_and_marts() -> None:
    assert ipss.SOURCE == "ipss"
    assert [t.code for t in ipss.TABLES] == [
        "T04-25",
        "T04-24",
        "T04-23",
        "T04-15",
        "T04-16",
        "T04-09",
        "T04-11",
    ]
    t = table("T04-25")
    assert t.key == "t04_25"
    assert t.url == "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/T04-25.xlsx"
    assert t.raw_name == "T04-25.xlsx"
    assert t.sheet == "T04-25" and t.mart == "survey"
    assert table("T04-09").sheet == "T04-09★" and table("T04-09").mart == "births"
    assert table("T04-11").sheet == "T04-11★" and table("T04-16").sheet == "T04-16★"
    assert {t.mart for t in ipss.TABLES} == {"survey", "births"}
    assert ipss.PDF_URL == "https://www.ipss.go.jp/ps-doukou/j/doukou16/JNFS16gaiyo.pdf"
    assert ipss.PDF_RAW_NAME == "JNFS16gaiyo.pdf"
    assert "PDL" in ipss.LICENSE and "人口統計資料集" in ipss.LICENSE
    assert ipss.SURVEY_YEARS == (1977, 1982, 1987, 1992, 1997, 2002, 2005, 2010, 2015, 2021)


def test_sheet_rows_reads_the_named_sheet_and_fails_on_unknown_sheet_or_non_xlsx() -> None:
    rows = ipss.sheet_rows(payload("T04-09"), "T04-09★")
    assert rows[2][1] == "年齢" and rows[2][2] == "1925年"
    with pytest.raises(ValueError, match="sheet"):
        ipss.sheet_rows(payload("T04-09"), "T04-09")
    with pytest.raises(ValueError, match="xlsx"):
        ipss.sheet_rows(b"not a workbook", "T04-09")


# ---- survey tables (T04-25 / T04-24 / T04-23) ----------------------------------------------


def test_planned_children_by_wife_age_1977_to_2021() -> None:
    rs = ipss.planned_children_rows(sheet("T04-25"))
    k = survey_keyed(rs)
    assert len(rs) == 10 * 7
    assert all(r["metric"] == "planned_children" and r["table"] == "T04-25" for r in rs)
    assert all(r["birth_cohort"] is None and r["source"] == "ipss" for r in rs)
    assert sorted({r["survey_year"] for r in rs}) == list(ipss.SURVEY_YEARS)
    assert k[(1977, "planned_children", "総数", None)] == 2.17
    assert k[(2021, "planned_children", "総数", None)] == 1.95
    assert k[(2021, "planned_children", "妻 20-24", None)] == 1.78
    assert k[(2021, "planned_children", "妻 45-49", None)] == 1.74
    assert k[(2010, "planned_children", "妻 25-29", None)] == 2.38


def test_children_born_by_wife_age_1977_to_2021() -> None:
    rs = ipss.children_born_rows(sheet("T04-24"))
    k = survey_keyed(rs)
    assert len(rs) == 10 * 7
    assert all(r["metric"] == "children_born" and r["table"] == "T04-24" for r in rs)
    assert k[(1977, "children_born", "総数", None)] == 1.89
    assert k[(2021, "children_born", "総数", None)] == 1.73
    assert k[(2021, "children_born", "妻 45-49", None)] == 1.81
    assert k[(2005, "children_born", "妻 40-44", None)] == 2.0


def test_completed_fertility_by_wife_birth_cohort() -> None:
    rs = ipss.completed_fertility_rows(sheet("T04-23"))
    k = survey_keyed(rs)
    assert len(rs) == 15 * 6
    assert all(r["table"] == "T04-23" for r in rs)
    assert {r["metric"] for r in rs} == {"completed_fertility", "completed_parity_share"}
    assert k[(2021, "completed_fertility", "妻の生まれ年 1971-1976", 1971)] == 1.81
    assert k[(1950, "completed_fertility", "妻の生まれ年 1890-1895", 1890)] == 4.8
    assert k[(1950, "completed_fertility", "妻の生まれ年 1900-1905", 1900)] == 4.8
    assert k[(2015, "completed_fertility", "妻の生まれ年 1965-1970", 1965)] == 1.86
    assert k[(2021, "completed_parity_share", "無子", 1971)] == 9.9
    assert k[(2021, "completed_parity_share", "1人", 1971)] == 19.4
    assert k[(2021, "completed_parity_share", "2人", 1971)] == 52.8
    assert k[(2021, "completed_parity_share", "3人", 1971)] == 16.0
    assert k[(2021, "completed_parity_share", "4人以上", 1971)] == 1.9
    assert k[(1970, "completed_parity_share", "4人以上", 1920)] == 28.5


def test_survey_tables_fail_closed_on_header_year_or_round_changes() -> None:
    rows = sheet("T04-25")
    broken = [dict(r) for r in rows]
    broken[2][4] = "20～25歳"
    with pytest.raises(ValueError, match="header"):
        ipss.planned_children_rows(broken)
    broken = [dict(r) for r in rows]
    broken[12][1] = "2022"
    with pytest.raises(ValueError, match="survey years"):
        ipss.planned_children_rows(broken)
    broken = [dict(r) for r in rows]
    broken[12][2] = "（第17回）"
    with pytest.raises(ValueError, match="round"):
        ipss.planned_children_rows(broken)
    broken = [dict(r) for r in rows]
    del broken[12][9]
    with pytest.raises(ValueError, match="2021"):
        ipss.planned_children_rows(broken)
    # the two age tables share one parser; the title must match the table
    with pytest.raises(ValueError, match="title"):
        ipss.children_born_rows(rows)
    with pytest.raises(ValueError, match="title"):
        ipss.planned_children_rows(sheet("T04-24"))


def test_completed_fertility_fails_closed_on_shares_cohort_label_or_header() -> None:
    rows = sheet("T04-23")
    broken = [dict(r) for r in rows]
    broken[17][4] = "19.9"  # shares no longer sum to 100
    with pytest.raises(ValueError, match="100"):
        ipss.completed_fertility_rows(broken)
    broken = [dict(r) for r in rows]
    broken[17][1] = "1971年生まれ"
    with pytest.raises(ValueError, match="cohort"):
        ipss.completed_fertility_rows(broken)
    broken = [dict(r) for r in rows]
    broken[2][5] = "２人"
    with pytest.raises(ValueError, match="header"):
        ipss.completed_fertility_rows(broken)
    broken = [dict(r) for r in rows]
    broken[16][3] = "2022"  # survey years must not go backwards
    with pytest.raises(ValueError, match="survey year"):
        ipss.completed_fertility_rows(broken)
    broken = [r for r in rows if r.get(1) != "1971～1976"]
    with pytest.raises(ValueError, match="1971"):
        ipss.completed_fertility_rows(broken)


# ---- births tables (T04-15 / T04-16 / T04-09 / T04-11) --------------------------------------


def test_births_by_order_counts_and_shares() -> None:
    rs = ipss.births_order_rows(sheet("T04-15"))
    k = births_keyed(rs)
    assert all(r["table"] == "T04-15" and r["cohort"] is None and r["source"] == "ipss" for r in rs)
    counts = [r for r in rs if r["metric"] == "births"]
    shares = [r for r in rs if r["metric"] == "births_share"]
    assert len(counts) == 23 * 6 and len(shares) == 9 * 6 and len(rs) == len(counts) + len(shares)
    assert k[(1950, "births", "総数", None)] == 2_337_507
    assert k[(1950, "births", "第1子", None)] == 634_324  # float noise in the cell is rounded
    assert isinstance(k[(1950, "births", "第1子", None)], int)
    assert k[(2024, "births", "総数", None)] == 686_173
    assert k[(2024, "births", "第5子以上", None)] == 8_449
    assert k[(2024, "births_share", "第1子", None)] == 47.0
    assert k[(2024, "births_share", "総数", None)] == 100.0
    assert k[(1950, "births_share", "第5子以上", None)] == 17.8
    assert {r["group"] for r in rs} == set(ipss.ORDER_GROUPS)


def test_births_by_order_fails_closed_on_header_total_or_year_order() -> None:
    rows = sheet("T04-15")
    broken = [dict(r) for r in rows]
    broken[1][8] = "第５子"
    with pytest.raises(ValueError, match="header"):
        ipss.births_order_rows(broken)
    broken = [dict(r) for r in rows]
    broken[3][3] = "1000"  # total smaller than the sum of orders
    with pytest.raises(ValueError, match="total"):
        ipss.births_order_rows(broken)
    broken = [dict(r) for r in rows]
    broken[35][3] = "99"  # share total must be 100
    with pytest.raises(ValueError, match="100"):
        ipss.births_order_rows(broken)
    broken = [dict(r) for r in rows]
    broken[25][1] = "2030"
    with pytest.raises(ValueError, match="2024"):
        ipss.births_order_rows(broken)
    broken = [r for r in rows if r.get(3) != "割  合(％)"]
    with pytest.raises(ValueError, match="share"):
        ipss.births_order_rows(broken)


def test_tfr_and_mean_age_by_order_1950_to_2024() -> None:
    rs = ipss.tfr_order_rows(sheet("T04-16"))
    k = births_keyed(rs)
    assert all(r["table"] == "T04-16" and r["cohort"] is None for r in rs)
    tfr = [r for r in rs if r["metric"] == "tfr_order"]
    age = [r for r in rs if r["metric"] == "mean_age_order"]
    # 75 years x 6 groups, minus 1951-1953 where the orders are '…' (no row)
    assert len(tfr) == 75 * 6 - 3 * 5 and len(age) == len(tfr) and len(rs) == 2 * len(tfr)
    assert k[(2024, "tfr_order", "第1子", None)] == 0.55
    assert k[(2024, "tfr_order", "総数", None)] == 1.15
    assert k[(1950, "tfr_order", "第5子以上", None)] == 0.78
    assert k[(1951, "tfr_order", "総数", None)] == 3.26
    assert (1951, "tfr_order", "第1子", None) not in k
    assert k[(2024, "mean_age_order", "第1子", None)] == 30.76
    assert k[(1950, "mean_age_order", "総数", None)] == 29.62


def test_tfr_by_order_fails_closed_on_header_years_or_sum() -> None:
    rows = sheet("T04-16")
    broken = [dict(r) for r in rows]
    broken[2][3] = "第１子以上"
    with pytest.raises(ValueError, match="header"):
        ipss.tfr_order_rows(broken)
    broken = [dict(r) for r in rows if r.get(1) != "2000"]
    with pytest.raises(ValueError, match="consecutive"):
        ipss.tfr_order_rows(broken)
    broken = [dict(r) for r in rows]
    broken[77][3] = "0.95"  # orders no longer add up to the total TFR
    with pytest.raises(ValueError, match="sum"):
        ipss.tfr_order_rows(broken)
    broken = [dict(r) for r in rows]
    broken[77][13] = "n/a"
    with pytest.raises(ValueError, match="2024"):
        ipss.tfr_order_rows(broken)


def test_asfr_by_single_year_of_age_and_calendar_year() -> None:
    rs = ipss.asfr_rows(sheet("T04-09"))
    k = births_keyed(rs)
    assert all(r["metric"] == "asfr" and r["table"] == "T04-09" and r["cohort"] is None for r in rs)
    assert len(rs) == 81 * 35
    years = sorted({r["year"] for r in rs})
    assert years[:4] == [1925, 1930, 1940, 1947] and years[-1] == 2024 and len(years) == 81
    assert {r["group"] for r in rs} == {f"age {a}" for a in range(15, 50)}
    assert k[(1925, "asfr", "age 15", None)] == 0.0063
    assert k[(1947, "asfr", "age 25", None)] == 0.26404
    assert k[(2024, "asfr", "age 30", None)] == 0.09137
    assert abs(sum(v for (y, _, _, _), v in k.items() if y == 2024) - 1.14751) < 5e-4


def test_asfr_fails_closed_on_header_ages_or_total_row() -> None:
    rows = sheet("T04-09")
    broken = [dict(r) for r in rows]
    broken[2][5] = "1946年"
    with pytest.raises(ValueError, match="consecutive"):
        ipss.asfr_rows(broken)
    broken = [dict(r) for r in rows]
    broken[18][1] = "31"
    with pytest.raises(ValueError, match="age"):
        ipss.asfr_rows(broken)
    broken = [dict(r) for r in rows]
    broken[38][82] = "1.5"  # 合計 must equal the column sum
    with pytest.raises(ValueError, match="合計"):
        ipss.asfr_rows(broken)
    broken = [dict(r) for r in rows]
    broken[18][82] = "…"
    with pytest.raises(ValueError, match="2024"):
        ipss.asfr_rows(broken)


def test_cohort_cumulative_fertility_labels_are_year_at_age_15() -> None:
    rs = ipss.cohort_rows(sheet("T04-11"))
    k = births_keyed(rs)
    assert all(r["metric"] == "cohort_cum_fertility" and r["table"] == "T04-11" for r in rs)
    assert len(rs) == 2020  # non-blank cells of the 71 columns x 35 ages
    # column '1950年' = women who were 15 in 1950 -> birth cohort 1935; year = cohort + age
    assert k[(1984, "cohort_cum_fertility", "age 49", 1935)] == 2.00864
    assert k[(2024, "cohort_cum_fertility", "age 49", 1975)] == 1.4557
    assert k[(2005, "cohort_cum_fertility", "age 30", 1975)] == 0.78002
    assert k[(2020, "cohort_cum_fertility", "age 15", 2005)] == 0.00022
    cohorts = sorted({r["cohort"] for r in rs})
    assert cohorts[0] == 1935 and cohorts[-1] == 2005
    assert sum(1 for r in rs if r["cohort"] == 2005) == 5
    assert all(r["year"] == int(str(r["cohort"])) + int(str(r["group"])[4:]) for r in rs)


def test_cohort_table_fails_closed_on_header_or_non_monotone_column() -> None:
    rows = sheet("T04-11")
    broken = [dict(r) for r in rows]
    broken[2][72] = "2021年"
    with pytest.raises(ValueError, match="consecutive"):
        ipss.cohort_rows(broken)
    broken = [dict(r) for r in rows]
    broken[18][2] = "0.1"  # cumulative rate must not decrease with age
    with pytest.raises(ValueError, match="cumulative"):
        ipss.cohort_rows(broken)
    broken = [dict(r) for r in rows]
    broken[3][72] = "x"
    with pytest.raises(ValueError, match="2020"):
        ipss.cohort_rows(broken)


def test_parse_table_dispatches_by_table() -> None:
    for t in ipss.TABLES:
        rs = ipss.parse_table(payload(t.code), t)
        assert rs and all(r["table"] == t.code for r in rs)
    with pytest.raises(ValueError, match="sheet"):
        ipss.parse_table(payload("T04-24"), table("T04-25"))


# ---- 第16回出生動向基本調査 結果の概要 PDF (figures 7-1 and 3-3) ---------------------------------


def test_pdf_figure_labels_ideal_planned_and_single_desired() -> None:
    rs = ipss.survey_pdf_rows_from_pages(pdf_pages())
    k = survey_keyed(rs)
    assert len(rs) == 10 + 10 + 9 + 9 + 10 + 10
    assert all(r["birth_cohort"] is None and r["source"] == "ipss" for r in rs)
    assert {r["table"] for r in rs} == {"JNFS16-7-1", "JNFS16-3-3"}
    ideal = [k[(y, "ideal_children", "夫婦", None)] for y in ipss.SURVEY_YEARS]
    assert ideal == [2.61, 2.62, 2.67, 2.64, 2.53, 2.56, 2.48, 2.42, 2.32, 2.25]
    planned = [k[(y, "planned_children_pdf", "夫婦", None)] for y in ipss.SURVEY_YEARS]
    assert planned == [2.17, 2.20, 2.23, 2.18, 2.16, 2.13, 2.11, 2.07, 2.01, 2.01]
    single_years = (1982, 1987, 1992, 1997, 2002, 2005, 2010, 2015, 2021)
    men = [k[(y, "desired_children_single", "未婚男性", None)] for y in single_years]
    assert men == [2.33, 2.30, 2.23, 2.15, 2.05, 2.07, 2.04, 1.91, 1.82]
    women = [k[(y, "desired_children_single", "未婚女性", None)] for y in single_years]
    assert women == [2.28, 2.23, 2.17, 2.13, 2.03, 2.10, 2.12, 2.02, 1.79]
    # wife under 35 (note under figure 7-1): robustness series for H9 V1
    u35 = [k[(y, "ideal_children", "夫婦（妻35歳未満）", None)] for y in ipss.SURVEY_YEARS]
    assert u35 == [2.52, 2.59, 2.61, 2.54, 2.43, 2.43, 2.40, 2.41, 2.43, 2.29]
    u35p = [k[(y, "planned_children_pdf", "夫婦（妻35歳未満）", None)] for y in ipss.SURVEY_YEARS]
    assert u35p == [2.18, 2.25, 2.31, 2.21, 2.18, 2.11, 2.15, 2.24, 2.28, 2.17]


def test_pdf_table_of_contents_line_is_not_the_figure() -> None:
    toc = (
        "3 \n図表 7-1 調査別にみた、夫婦の平均理想子ども数と平均予定子ども数 ........ 54\n"
        "図表 3-3 調査別にみた、未婚者の平均希望子ども数 ........ 34\n0\n"
    )
    rs = ipss.survey_pdf_rows_from_pages([toc, *pdf_pages()])
    assert len(rs) == 58
    with pytest.raises(ValueError, match="7-1 not found"):
        ipss.survey_pdf_rows_from_pages([toc])


def test_pdf_fails_closed_when_label_count_or_endpoints_differ() -> None:
    pages = pdf_pages()
    with pytest.raises(ValueError, match="7-1"):
        ipss.survey_pdf_rows_from_pages([p for p in pages if "図表 7-1" not in p])
    with pytest.raises(ValueError, match="3-3"):
        ipss.survey_pdf_rows_from_pages([p for p in pages if "図表 3-3" not in p])
    # one label lost -> 19 tokens
    broken = [p.replace("2.48 2.42", "2.42") for p in pages]
    with pytest.raises(ValueError, match="20"):
        ipss.survey_pdf_rows_from_pages(broken)
    # series swapped: the 7th-round ideal (2.61) and 16th-round planned (2.01) no longer match
    broken = [
        p.replace(
            "2.61 2.62 2.67 2.64 2.53 2.56 2.48 2.42 2.32 2.25"
            "2.17 2.20 2.23 2.18 2.16 2.13 2.11 2.07 2.01 2.01",
            "2.17 2.20 2.23 2.18 2.16 2.13 2.11 2.07 2.01 2.01"
            "2.61 2.62 2.67 2.64 2.53 2.56 2.48 2.42 2.32 2.25",
        )
        for p in pages
    ]
    with pytest.raises(ValueError, match="第7回"):
        ipss.survey_pdf_rows_from_pages(broken)
    broken = [p.replace("2.32 2.252.17", "2.32 2.262.17") for p in pages]
    with pytest.raises(ValueError, match="第16回"):
        ipss.survey_pdf_rows_from_pages(broken)
    # figure 3-3: a swapped sex order is caught by the 2021 endpoints (1.82 men / 1.79 women)
    broken = [
        p.replace("1.82\n2.28", "1.79\n2.28").replace("2.02\n1.79", "2.02\n1.82") for p in pages
    ]
    with pytest.raises(ValueError, match="第16回"):
        ipss.survey_pdf_rows_from_pages(broken)
    broken = [p.replace("2.032.10 2.12", "2.032.10") for p in pages]
    with pytest.raises(ValueError, match="18"):
        ipss.survey_pdf_rows_from_pages(broken)
    # note series: ten rounds 7..16 are required
    broken = [p.replace("第13回（2005）2.40、", "") for p in pages]
    with pytest.raises(ValueError, match="35歳未満"):
        ipss.survey_pdf_rows_from_pages(broken)


def test_pdf_rows_end_to_end_from_pdf_bytes(pdf_from_pages) -> None:  # type: ignore[no-untyped-def]
    rs = ipss.survey_pdf_rows(pdf_from_pages(pdf_pages()))
    assert survey_keyed(rs)[(2021, "ideal_children", "夫婦", None)] == 2.25
    with pytest.raises(ValueError, match="PDF"):
        ipss.survey_pdf_rows(b"<html>not a pdf</html>")


# ---- marts ---------------------------------------------------------------------------------


def test_build_survey_mart_combines_sorts_and_rejects_duplicates() -> None:
    parts = {
        "t04_25": ipss.planned_children_rows(sheet("T04-25")),
        "t04_24": ipss.children_born_rows(sheet("T04-24")),
        "t04_23": ipss.completed_fertility_rows(sheet("T04-23")),
        "jnfs16": ipss.survey_pdf_rows_from_pages(pdf_pages()),
    }
    mart = ipss.build_survey_mart(parts)
    assert len(mart) == 70 + 70 + 90 + 58
    assert set(mart[0]) == {
        "survey_year",
        "metric",
        "group",
        "birth_cohort",
        "value",
        "table",
        "source",
    }
    keys = [(r["survey_year"], r["metric"], r["group"], r["birth_cohort"]) for r in mart]
    assert len(set(keys)) == len(keys)
    assert keys == sorted(
        keys,
        key=lambda k: (
            int(str(k[0])),
            ipss.SURVEY_METRICS.index(str(k[1])),
            str(k[2]),
            -1 if k[3] is None else int(str(k[3])),
        ),
    )
    assert mart[0]["survey_year"] == 1950
    assert {r["metric"] for r in mart} == set(ipss.SURVEY_METRICS)
    # one table is enough; a duplicated key fails closed
    assert len(ipss.build_survey_mart({"t04_25": parts["t04_25"]})) == 70
    with pytest.raises(ValueError, match="duplicate"):
        ipss.build_survey_mart({"a": parts["t04_25"], "b": parts["t04_25"][:1]})


def test_build_births_mart_combines_sorts_and_rejects_duplicates() -> None:
    parts = {
        "t04_15": ipss.births_order_rows(sheet("T04-15")),
        "t04_16": ipss.tfr_order_rows(sheet("T04-16")),
        "t04_09": ipss.asfr_rows(sheet("T04-09")),
        "t04_11": ipss.cohort_rows(sheet("T04-11")),
    }
    mart = ipss.build_births_mart(parts)
    assert len(mart) == 192 + 870 + 2835 + 2020
    assert set(mart[0]) == {"year", "metric", "group", "cohort", "value", "table", "source"}
    keys = [(r["year"], r["metric"], r["group"], r["cohort"]) for r in mart]
    assert len(set(keys)) == len(keys)
    assert keys == sorted(
        keys,
        key=lambda k: (
            int(str(k[0])),
            ipss.BIRTHS_METRICS.index(str(k[1])),
            ipss.group_order(str(k[2])),
            -1 if k[3] is None else int(str(k[3])),
        ),
    )
    assert mart[0]["year"] == 1925 and mart[0]["metric"] == "asfr"
    assert {r["metric"] for r in mart} == set(ipss.BIRTHS_METRICS)
    with pytest.raises(ValueError, match="duplicate"):
        ipss.build_births_mart({"a": parts["t04_15"], "b": parts["t04_15"][:1]})
