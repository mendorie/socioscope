import polars as pl
import pytest

from theme_parliament_size.analysis.a20261027_r1_ratio import (
    Country,
    cube_ratio,
    judge_h1,
    judge_h1b,
    judge_h1c,
    judgements,
    load_countries,
    per_million,
    rank_of,
    with_reduction,
)


def test_per_million_and_cube_ratio() -> None:
    assert per_million(465, 124_371) == pytest.approx(3.7388, abs=1e-3)
    assert cube_ratio(465, 124_371) == pytest.approx(0.9316, abs=1e-3)
    assert cube_ratio(1000, 1_000_000) == pytest.approx(1.0)  # 1e9^(1/3) = 1000


def test_rank_counts_strictly_smaller_values() -> None:
    assert rank_of({"A": 1.0, "B": 2.0, "C": 3.0}, "A") == 1
    assert rank_of({"A": 1.0, "B": 2.0, "C": 3.0}, "C") == 3
    assert rank_of({"A": 2.0, "B": 2.0, "C": 3.0}, "B") == 1  # tie -> same rank


def test_judges_follow_the_preregistered_thresholds() -> None:
    assert judge_h1(3, 4) == "整合"
    assert judge_h1(5, 5) == "整合"
    assert judge_h1(6, 4) == "中間"
    assert judge_h1(10, 4) == "不支持"
    assert judge_h1(3, 12) == "不支持"
    assert judge_h1b(13) == "整合" and judge_h1b(26) == "整合"
    assert judge_h1b(12) == "不支持" and judge_h1b(27) == "不支持"
    assert judge_h1b(4, n=10) == "整合" and judge_h1b(3, n=10) == "不支持"
    assert judge_h1c(("整合", "整合"), [("整合", "整合"), ("整合", "整合")]) == "整合"
    assert judge_h1c(("整合", "整合"), [("整合", "不支持")]) == "不支持"


def _countries() -> list[Country]:
    return [
        Country("JPN", "Japan", 465, 713, 124_371, "directly_elected"),
        Country("USA", "USA", 435, 535, 343_477, "directly_elected"),
        Country("GBR", "UK", 650, 1450, 68_682, "appointed"),
        Country("ISL", "Iceland", 63, 63, 388),
        Country("DEU", "Germany", 630, 699, 84_548, "indirectly_elected"),
        Country("KOR", "Korea", 300, 300, 51_749),
    ]


def test_with_reduction_changes_only_the_lower_house_of_one_country() -> None:
    out = with_reduction(_countries(), "JPN", 420)
    jp = next(c for c in out if c.iso3 == "JPN")
    assert (jp.lower_seats, jp.total_seats) == (420, 668)
    assert [c for c in out if c.iso3 != "JPN"] == [c for c in _countries() if c.iso3 != "JPN"]


def test_judgements_rank_japan_within_the_sample() -> None:
    h1, h1b, ranks = judgements(_countries())
    assert ranks == {"per_m_lower": 2, "per_m_total": 2, "cube": 4}
    assert h1 == "整合"
    assert h1b == "整合"  # n = 6 -> 3..6


def test_load_countries_reads_oecd_lower_and_upper_chambers() -> None:
    mart = pl.DataFrame(
        {
            "iso3": ["JPN", "JPN", "KOR", "XXX"],
            "country": ["Japan", "Japan", "Korea", "Nowhere"],
            "oecd_member": [True, True, True, False],
            "chamber_type": ["lower", "upper", "lower", "lower"],
            "statutory_seats": [465.0, 248.0, 300.0, 10.0],
            "population_thousands": [124_371.0, 124_371.0, 51_749.0, 1.0],
            "designation_mode": ["directly_elected", "directly_elected", "directly_elected", ""],
        }
    )
    out = load_countries(mart)
    assert [c.iso3 for c in out] == ["JPN", "KOR"]
    assert out[0] == Country("JPN", "Japan", 465.0, 713.0, 124_371.0, "directly_elected")
    assert out[1].upper_designation == "" and out[1].total_seats == 300.0


def test_load_countries_fails_closed_on_missing_seats_or_population() -> None:
    mart = pl.DataFrame(
        {
            "iso3": ["JPN"],
            "country": ["Japan"],
            "oecd_member": [True],
            "chamber_type": ["lower"],
            "statutory_seats": [None],
            "population_thousands": [124_371.0],
            "designation_mode": [""],
        },
        schema_overrides={"statutory_seats": pl.Float64},
    )
    with pytest.raises(ValueError, match="missing"):
        load_countries(mart)
