"""moekr.py: 교육부 초중고 사교육비조사 press-release PDF -> long rows (pure, fail-closed).

The fixture is the pypdf text of the pages carrying <표1>/<표2>/<표4> (by school level), the
statistics-table contents page, statistics tables 10–11 (by number of children) and 21 (annual
series), separated by form feed. The PDF itself is not committed.
"""

from pathlib import Path

import pytest

from theme_growth_fertility import moekr

FIXTURES = Path(__file__).parent / "fixtures"


def pages() -> list[str]:
    return (FIXTURES / "moe_kr_private_tutoring_2025.txt").read_text(encoding="utf-8").split("\f")


def rows() -> list[dict[str, object]]:
    return moekr.private_tutoring_rows_from_pages(pages())


def keyed(rs: list[dict[str, object]]) -> dict[tuple[int, str, str, str], object]:
    return {
        (int(str(r["year"])), str(r["table"]), str(r["group"]), str(r["metric"])): r["value"]
        for r in rs
    }


def test_release_constants() -> None:
    assert moekr.SOURCE == "moe_kr"
    assert moekr.RELEASE_YEAR == 2026
    assert moekr.SURVEY_YEAR == 2025
    assert moekr.RAW_NAME == "private_tutoring_2025.pdf"
    assert moekr.URL == (
        "https://www.moe.go.kr/boardCnts/fileDown.do?m=020402&s=moe"
        "&fileSeq=7562a697bdba006065fa92054b1d634e"
    )
    assert "KOGL" in moekr.LICENSE and "kogl.or.kr" in moekr.LICENSE and "교육부" in moekr.LICENSE


def test_annual_table_covers_2007_to_2025_with_published_values() -> None:
    rs = moekr.annual_rows(pages())
    years = sorted({int(str(r["year"])) for r in rs})
    assert years == list(range(2007, 2026))
    k = keyed(rs)
    assert all(r["table"] == "annual" and r["group"] == "총계" for r in rs)
    assert k[(2007, "annual", "총계", "total_100m_krw")] == 200_400
    assert k[(2007, "annual", "총계", "participation_rate_pct")] == 77.0
    assert k[(2007, "annual", "총계", "hours_per_week")] == 7.8
    assert k[(2007, "annual", "총계", "spend_per_student_10k_krw")] == 22.2
    assert (2007, "annual", "총계", "spend_per_participant_10k_krw") not in k  # "-" -> no row
    assert (2016, "annual", "총계", "spend_per_participant_10k_krw") not in k
    assert k[(2017, "annual", "총계", "spend_per_participant_10k_krw")] == 38.2
    assert k[(2015, "annual", "총계", "spend_per_student_10k_krw")] == 24.4
    assert k[(2024, "annual", "총계", "total_100m_krw")] == 291_919
    assert k[(2025, "annual", "총계", "total_100m_krw")] == 275_351
    assert k[(2025, "annual", "총계", "participation_rate_pct")] == 75.7
    assert k[(2025, "annual", "총계", "hours_per_week")] == 7.1
    assert k[(2025, "annual", "총계", "spend_per_student_10k_krw")] == 45.8
    assert k[(2025, "annual", "총계", "spend_per_participant_10k_krw")] == 60.4
    # 2007–2016: 4 metrics, 2017–2025: 5 metrics
    assert len(rs) == 10 * 4 + 9 * 5
    assert all(r["release_year"] == 2026 and r["source"] == "moe_kr" for r in rs)


def test_by_children_tables_give_spend_and_participation_for_2024_and_2025() -> None:
    rs = moekr.by_children_rows(pages())
    k = keyed(rs)
    assert all(r["table"] == "by_children" for r in rs)
    assert {str(r["group"]) for r in rs} == {"총계", "자녀 1명", "자녀 2명", "자녀 3명 이상"}
    assert sorted({int(str(r["year"])) for r in rs}) == [2024, 2025]
    assert k[(2025, "by_children", "자녀 1명", "spend_per_student_10k_krw")] == 51.8
    assert k[(2025, "by_children", "자녀 2명", "spend_per_student_10k_krw")] == 47.4
    assert k[(2025, "by_children", "자녀 3명 이상", "spend_per_student_10k_krw")] == 35.8
    assert k[(2025, "by_children", "총계", "spend_per_student_10k_krw")] == 45.8
    assert k[(2024, "by_children", "자녀 1명", "spend_per_student_10k_krw")] == 53.6
    assert k[(2024, "by_children", "자녀 3명 이상", "participation_rate_pct")] == 71.6
    assert k[(2025, "by_children", "자녀 1명", "participation_rate_pct")] == 79.6
    assert k[(2025, "by_children", "자녀 2명", "participation_rate_pct")] == 77.4
    assert k[(2025, "by_children", "자녀 3명 이상", "participation_rate_pct")] == 67.7
    assert len(rs) == 2 * 4 * 2


def test_by_level_tables_give_five_metrics_for_2024_and_2025() -> None:
    rs = moekr.by_level_rows(pages())
    k = keyed(rs)
    assert all(r["table"] == "by_level" for r in rs)
    assert {str(r["group"]) for r in rs} == {"초등학교", "중학교", "고등학교"}
    assert sorted({int(str(r["year"])) for r in rs}) == [2024, 2025]
    assert k[(2025, "by_level", "초등학교", "total_100m_krw")] == 121_744
    assert k[(2024, "by_level", "고등학교", "total_100m_krw")] == 81_324
    assert k[(2025, "by_level", "초등학교", "participation_rate_pct")] == 84.4
    assert k[(2025, "by_level", "고등학교", "participation_rate_pct")] == 63.0
    assert k[(2024, "by_level", "중학교", "hours_per_week")] == 7.8
    assert k[(2025, "by_level", "고등학교", "hours_per_week")] == 6.6
    assert k[(2025, "by_level", "초등학교", "spend_per_student_10k_krw")] == 43.3
    assert k[(2025, "by_level", "고등학교", "spend_per_student_10k_krw")] == 49.9
    assert k[(2025, "by_level", "고등학교", "spend_per_participant_10k_krw")] == 79.3
    assert k[(2024, "by_level", "초등학교", "spend_per_participant_10k_krw")] == 50.4
    assert len(rs) == 2 * 3 * 5


def test_all_rows_have_closed_columns_and_unique_keys() -> None:
    rs = rows()
    assert set(rs[0]) == {"year", "table", "group", "metric", "value", "release_year", "source"}
    assert len(rs) == (10 * 4 + 9 * 5) + 16 + 30
    keys = [(r["year"], r["table"], r["group"], r["metric"]) for r in rs]
    assert len(keys) == len(set(keys))
    assert {str(r["metric"]) for r in rs} <= set(moekr.METRICS)


def test_fails_closed_when_annual_table_missing() -> None:
    with pytest.raises(ValueError, match="annual"):
        moekr.annual_rows(["- 1 -\n사교육비 총액\n2025 275,351"])


def test_contents_line_does_not_count_as_the_annual_table() -> None:
    toc_only = [p for p in pages() if "통   계   표" in p]
    assert toc_only
    with pytest.raises(ValueError, match="annual"):
        moekr.annual_rows(toc_only)


def test_fails_closed_when_annual_years_are_not_consecutive() -> None:
    broken = [p.replace("2013 185,960", "2031 185,960") for p in pages()]
    with pytest.raises(ValueError, match="2007"):
        moekr.annual_rows(broken)


def test_fails_closed_when_annual_header_differs() -> None:
    broken = [p.replace("참여시간\n(시간)", "참여일수\n(일)") for p in pages()]
    with pytest.raises(ValueError, match="header"):
        moekr.annual_rows(broken)


def test_fails_closed_when_an_annual_row_has_wrong_column_count() -> None:
    broken = [
        p.replace("2024 291,919 80.0 7.6 47.4 59.2", "2024 291,919 80.0 7.6 47.4") for p in pages()
    ]
    with pytest.raises(ValueError, match="2024"):
        moekr.annual_rows(broken)


def test_fails_closed_when_children_header_differs() -> None:
    broken = [p.replace("전체 1명 2명 3명 이상", "전체 1명 2명 3명") for p in pages()]
    with pytest.raises(ValueError, match="header"):
        moekr.by_children_rows(broken)


def test_fails_closed_when_children_table_missing() -> None:
    with pytest.raises(ValueError, match="자녀수별"):
        moekr.by_children_rows([p for p in pages() if "자녀수별 사교육 참여율" not in p])


def test_fails_closed_when_level_table_missing() -> None:
    with pytest.raises(ValueError, match="표4"):
        moekr.by_level_rows([p for p in pages() if "<표4>" not in p])


def test_fails_closed_when_total_column_disagrees_with_annual_table() -> None:
    # by_children 전체 for 2025 (45.8) must equal the annual spend_per_student
    broken = [
        p.replace("< 2025 > 45.8 51.8 47.4 35.8", "< 2025 > 44.8 51.8 47.4 35.8") for p in pages()
    ]
    with pytest.raises(ValueError, match="annual"):
        moekr.private_tutoring_rows_from_pages(broken)
    broken = [p.replace("2025년 275,351 121,744", "2025년 275,350 121,744") for p in pages()]
    with pytest.raises(ValueError, match="annual"):
        moekr.private_tutoring_rows_from_pages(broken)


def test_build_mart_sorts_by_year_table_group_metric_and_rejects_duplicates() -> None:
    rs = rows()
    mart = moekr.build_mart(list(reversed(rs)))
    assert len(mart) == len(rs)
    first = mart[0]
    assert (first["year"], first["table"], first["group"]) == (2007, "annual", "총계")
    order = [(r["year"], r["table"], r["group"], r["metric"]) for r in mart]
    assert order == sorted(
        order,
        key=lambda k: (
            k[0],
            moekr.TABLES.index(str(k[1])),
            moekr.GROUPS.index(str(k[2])),
            moekr.METRICS.index(str(k[3])),
        ),
    )
    assert mart[-1]["year"] == 2025 and mart[-1]["table"] == "by_level"
    with pytest.raises(ValueError, match="duplicate"):
        moekr.build_mart([*rs, rs[0]])


def test_rows_end_to_end_from_pdf_bytes(pdf_from_pages) -> None:  # type: ignore[no-untyped-def]
    payload = pdf_from_pages(pages())
    rs = moekr.private_tutoring_rows(payload)
    assert keyed(rs)[(2025, "annual", "총계", "spend_per_student_10k_krw")] == 45.8
    with pytest.raises(ValueError, match="PDF"):
        moekr.private_tutoring_rows(b"<html>not a pdf</html>")
