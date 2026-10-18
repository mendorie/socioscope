"""kostat.py (H9): 「2025년 출생 통계」 press-release PDF -> long rows (pure, fail-closed).

Fixture = pypdf text of the statistics-table contents page (TOC, must not match) and the pages
of 통계표 2 (모의 연령별 출산율) and 통계표 3 (출산 순위별 출생아 수), form-feed separated.
"""

from pathlib import Path

import pytest

from theme_growth_fertility import kostat

FIXTURES = Path(__file__).parent / "fixtures"


def births_pages() -> list[str]:
    return (FIXTURES / "kostat_births_2025.txt").read_text(encoding="utf-8").split("\f")


def births_keyed() -> dict[tuple[int, str, str], float]:
    rows = kostat.births_rows_from_pages(births_pages())
    keyed = {
        (int(str(r["year"])), str(r["metric"]), str(r["group"])): float(str(r["value"]))
        for r in rows
    }
    assert len(keyed) == len(rows)
    return keyed


def test_births_rows_cover_1981_to_2025_with_17_rows_per_year() -> None:
    rows = kostat.births_rows_from_pages(births_pages())
    assert set(rows[0]) == {"year", "metric", "group", "value", "release_year", "source"}
    assert sorted({int(str(r["year"])) for r in rows}) == list(range(1981, 2026))
    assert len(rows) == 45 * (5 + 4 + 7 + 1)
    assert all(r["source"] == "kostat_births" and r["release_year"] == 2026 for r in rows)
    assert {str(r["group"]) for r in rows if r["metric"] == "births"} == set(kostat.BIRTH_ORDERS)
    assert {str(r["group"]) for r in rows if r["metric"] == "asfr"} == set(kostat.ASFR_AGES)
    assert {str(r["group"]) for r in rows if r["metric"] == "tfr"} == {"계"}


def test_births_rows_match_published_values() -> None:
    k = births_keyed()
    assert k[(2025, "births", "계")] == 254341
    assert k[(2025, "births", "첫째아")] == 158684
    assert k[(2025, "births", "넷째아 이상")] == 2831
    assert k[(2025, "births_share", "첫째아")] == pytest.approx(158684 / 254341)
    assert k[(1981, "births", "계")] == 867409 and k[(1981, "births", "셋째아")] == 142161
    assert k[(1990, "births_share", "첫째아")] == pytest.approx(348703 / 649738)
    assert k[(2010, "births_share", "첫째아")] == pytest.approx(235473 / 470171)
    assert k[(2025, "asfr", "30-34")] == 73.1 and k[(2025, "asfr", "45-49")] == 0.3
    assert k[(1981, "asfr", "25-29")] == 224.3
    assert k[(2025, "tfr", "계")] == 0.80 and k[(1981, "tfr", "계")] == 2.57
    # 2022-2024 rows are printed with irregular spacing in the PDF text
    assert k[(2023, "births", "둘째아")] == 74361 and k[(2024, "births", "계")] == 238317


def _tamper(pages: list[str], old: str, new: str) -> list[str]:
    assert any(old in p for p in pages), old
    return [p.replace(old, new) for p in pages]


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ("3. 출산 순위별 출생아 수, 1981-2025", "3. 출산 순위별 출생아, 1981-2025", "not found"),
        ("연도 계* 첫째아 둘째아 셋째아 넷째아 이상", "연도 계* 첫째아 둘째아 셋째아", "header"),
        ("\n1999 620,668 310,405 247,476 54,589 6,562", "", "consecutive"),
        (
            "2025 254,341 158,684 79,199 13,499 2,831",
            "2025 254,341 158,684 79,199 13,499",
            "values",
        ),
        (
            "2025 254,341 158,684 79,199 13,499 2,831",
            "2025 254,341 158,684 79,199 13,499 9,831",
            "add up",
        ),
        ("연도 합계출산율 15-19세 20-24세", "연도 합계출산율 15-19세 20-25세", "header"),
        (
            "2025 0.80 0.4 3.8 21.2 73.1 52.1 8.5 0.3",
            "2025 0.80 0.4 3.8 21.2 73.1 52.1 8.5",
            "values",
        ),
    ],
)
def test_births_rows_fail_closed(old: str, new: str, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        kostat.births_rows_from_pages(_tamper(births_pages(), old, new))


def test_births_tables_must_cover_the_same_years() -> None:
    pages = _tamper(births_pages(), "\n2025 0.80 0.4 3.8 21.2 73.1 52.1 8.5 0.3", "")
    with pytest.raises(ValueError, match="years"):
        kostat.births_rows_from_pages(pages)


def test_build_births_mart_sorts_by_year_metric_group_and_rejects_duplicates() -> None:
    rows = kostat.births_rows_from_pages(births_pages())
    mart = kostat.build_births_mart(list(reversed(rows)))
    assert len(mart) == len(rows)
    assert [(r["year"], r["metric"], r["group"]) for r in mart[:6]] == [
        (1981, "births", "계"),
        (1981, "births", "첫째아"),
        (1981, "births", "둘째아"),
        (1981, "births", "셋째아"),
        (1981, "births", "넷째아 이상"),
        (1981, "births_share", "첫째아"),
    ]
    assert (mart[9]["metric"], mart[9]["group"]) == ("asfr", "15-19")
    assert (mart[16]["metric"], mart[16]["group"]) == ("tfr", "계")
    with pytest.raises(ValueError, match="duplicate"):
        kostat.build_births_mart([*rows, dict(rows[0])])
