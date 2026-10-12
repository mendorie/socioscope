import pytest

from theme_growth_fertility.analysis import s20261013_h7_summary as s


def test_scorecard_table_counts_points_and_selects_answer() -> None:
    tests = [
        ("T1", "S = 0.80", {"B", "C"}),
        ("T2", "+0.02", {"B", "C"}),
        ("T3", "21.6", {"B"}),
        ("T4", "42%", set()),
        ("T5", "66 / 30", {"B"}),
    ]
    rows, totals, answer = s.scorecard_table(tests)
    assert rows[0] == ("T1", "S = 0.80", (0, 1, 1))
    assert rows[3] == ("T4", "42%", (0, 0, 0))
    assert totals == {"A": 0, "B": 4, "C": 2}
    assert answer == "B (4 points)"


def test_scorecard_table_empty_is_none() -> None:
    _, totals, answer = s.scorecard_table([("T1", "x", set())])
    assert totals == {"A": 0, "B": 0, "C": 0}
    assert answer.startswith("none")


def test_pick_examples_orders_by_key_then_iso3_and_skips_missing() -> None:
    rows = [
        {"iso3": "BBB", "quadrant": "q", "v": 2.0},
        {"iso3": "AAA", "quadrant": "q", "v": 2.0},
        {"iso3": "CCC", "quadrant": "q", "v": 3.0},
        {"iso3": "DDD", "quadrant": "q", "v": None},
        {"iso3": "EEE", "quadrant": "other", "v": 9.0},
    ]
    assert s.pick_examples(rows, "q", "v", k=2) == ["CCC", "AAA"]
    assert s.pick_examples(rows, "q", "v", k=5, descending=False) == ["AAA", "BBB", "CCC"]


def test_ja_name_falls_back_to_country() -> None:
    assert s.ja_name("JPN", "Japan") == "日本"
    assert s.ja_name("ZZZ", "Zedland") == "Zedland"


def test_stack_segments_accumulate_left_edges() -> None:
    segs = s.stack_segments({"a": -0.5, "b": 0.1}, -0.2)
    assert [x[0] for x in segs] == ["a", "b", "remaining"]
    assert segs[1][2] == pytest.approx(-0.5)
    assert segs[2][2] == pytest.approx(-0.4)
    assert sum(x[1] for x in segs) == pytest.approx(-0.6)
