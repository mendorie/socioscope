"""H9 記事用図（s20261018_h9_summary）の純粋ヘルパのテスト。"""

from dataclasses import dataclass

from theme_growth_fertility.analysis import s20261018_h9_summary as s


@dataclass(frozen=True)
class _Row:
    iso3: str
    v: int


def test_kind_ja_covers_v1_and_v2_types() -> None:
    assert s.kind_ja("N") == "規範型"
    assert s.kind_ja("C") == "阻害型"
    assert s.kind_ja("mixed") == "どちらでもない"
    assert s.kind_ja("childlessness") == "無子化型"
    assert s.kind_ja("one_child") == "1 人止まり型"


def test_pick_keeps_requested_order_and_skips_missing() -> None:
    rows = [_Row("A", 1), _Row("B", 2), _Row("C", 3)]
    assert [r.iso3 for r in s.pick(rows, ["C", "X", "A"])] == ["C", "A"]


def test_by_year_filters_country_and_range_sorted() -> None:
    tfr = {("A", 2001): 1.5, ("A", 1999): 1.6, ("B", 2000): 2.0, ("A", 2030): 1.0}
    assert s.by_year(tfr, "A", 1990, 2025) == [(1999, 1.6), (2001, 1.5)]


def test_cohort_points_shift_cohorts_to_plot_year() -> None:
    assert s.cohort_points({1975: 1.45, 1960: 1.85, 1930: 2.5}, 1940, 1979, 30) == [
        (1990, 1.85),
        (2005, 1.45),
    ]
