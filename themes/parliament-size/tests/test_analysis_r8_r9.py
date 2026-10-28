import math

import pytest

from theme_parliament_size.analysis.a20261028_r8_member_bills import (
    member_share,
    rank_consistent,
    totals,
    yearly,
)
from theme_parliament_size.analysis.a20261028_r9_seats_history import (
    changes,
    jp_lower_house,
    judge_h6b,
    pearson,
    pop_change,
    statutory_at,
)


def test_member_share_ignores_other_and_handles_empty() -> None:
    assert member_share({"member": 1, "government": 3, "other": 10}) == pytest.approx(25.0)
    assert member_share({"other": 2}) is None


def test_rank_consistent_judges_by_order() -> None:
    per_m = {"JPN": 3.7, "FRA": 8.7, "GBR": 9.5}
    assert rank_consistent({"JPN": 20.0, "FRA": 40.0, "GBR": 60.0}, per_m) == "整合"
    assert rank_consistent({"JPN": 20.0, "FRA": 60.0, "GBR": 40.0}, per_m) == "中間"
    assert rank_consistent({"JPN": 30.0, "FRA": 60.0, "GBR": 10.0}, per_m) == "不支持"


def test_yearly_and_totals() -> None:
    rows = [
        {"year": 2008, "origin": "member"},
        {"year": 2008, "origin": "government"},
        {"year": 2009, "origin": "member"},
        {"year": 2030, "origin": "member"},
    ]
    by = yearly(rows, (2008, 2025))
    assert by == {2008: {"member": 1, "government": 1}, 2009: {"member": 1}}
    assert totals(by) == {"member": 2, "government": 1}


def test_statutory_at_and_jp_lower_house() -> None:
    table = [(1990, 656), (2002, 598), (2025, 630)]
    assert statutory_at(table, 1989) is None
    assert statutory_at(table, 2002) == 598 and statutory_at(table, 2021) == 598
    assert statutory_at(table, 2025) == 630
    rows = [
        {"chamber": "lower", "effective_year": "2017", "seats": "465"},
        {"chamber": "upper", "effective_year": "2022", "seats": "248"},
        {"chamber": "lower", "effective_year": "2000", "seats": "480"},
    ]
    assert jp_lower_house(rows) == [(2000, 480), (2017, 465)]


def test_changes_pop_change_pearson_and_judge() -> None:
    el = [
        (1986, "1986-07-06", 512),
        (1996, "1996-10-20", 500),
        (2000, "2000-06-25", 480),
        (2003, "2003-11-09", 480),
    ]
    ch = changes(el)
    assert [(c["year"], c["before"], c["after"]) for c in ch] == [
        (1996, 512, 500),
        (2000, 500, 480),
    ]
    assert ch[0]["change_pct"] == pytest.approx(100 * (500 - 512) / 512)
    pop = {1990: 100.0, 2000: 110.0}
    assert pop_change(pop, 2000) == pytest.approx(10.0)
    assert pop_change(pop, 2001) is None
    assert pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert math.isnan(pearson([1, 1, 1], [1, 2, 3]))
    assert (
        judge_h6b(0.2) == "整合"
        and judge_h6b(-0.3) == "不支持"
        and judge_h6b(math.nan) == "判定不能"
    )
