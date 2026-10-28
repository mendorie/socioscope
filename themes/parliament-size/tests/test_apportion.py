import pytest

from theme_parliament_size.apportion import (
    adams,
    dhondt,
    gallagher,
    sainte_lague,
    threshold_share,
)


def test_dhondt_textbook_example() -> None:
    # Wikipedia の例: A 100,000 / B 80,000 / C 30,000 / D 20,000 を 8 議席
    out = dhondt({"A": 100_000, "B": 80_000, "C": 30_000, "D": 20_000}, 8)
    assert out == {"A": 4, "B": 3, "C": 1, "D": 0}


def test_dhondt_reproduces_hokkaido_2024_pr_block() -> None:
    # 第 50 回 北海道ブロック（8 議席）: 立憲 3、自民 3、公明 1、国民 1（総務省 議席配分表）
    votes = {
        "立憲民主党": 694_578.943,
        "自由民主党": 641_127,
        "公明党": 253_344,
        "国民民主党": 192_303.871,
        "れいわ新選組": 177_620,
        "日本共産党": 169_799,
        "日本維新の会": 96_954,
        "日本保守党": 61_903,
        "参政党": 57_002,
        "社会民主党": 31_134,
        "安楽死制度を考える会": 18_455,
    }
    out = dhondt(votes, 8)
    assert {p: s for p, s in out.items() if s} == {
        "立憲民主党": 3,
        "自由民主党": 3,
        "公明党": 1,
        "国民民主党": 1,
    }


def test_sainte_lague_and_modified_first_divisor() -> None:
    votes = {"A": 100_000, "B": 80_000, "C": 30_000, "D": 20_000}
    assert sainte_lague(votes, 8) == {"A": 3, "B": 3, "C": 1, "D": 1}
    # 修正サンラグ（1.4）は小政党の 1 議席目を取りにくくする
    assert sainte_lague(votes, 8, first_divisor=1.4) == {"A": 4, "B": 3, "C": 1, "D": 0}


def test_dhondt_zero_seats_and_empty() -> None:
    assert dhondt({"A": 1.0}, 0) == {"A": 0}
    assert dhondt({}, 3) == {}
    with pytest.raises(ValueError):
        dhondt({"A": 1.0}, -1)


def test_adams_gives_every_unit_a_seat_and_sums_to_total() -> None:
    pops = {"大": 1000.0, "中": 300.0, "小": 10.0}
    out = adams(pops, 10)
    assert sum(out.values()) == 10 and min(out.values()) >= 1
    assert out == {"大": 7, "中": 2, "小": 1}
    with pytest.raises(ValueError, match="at least one seat"):
        adams(pops, 2)


def test_adams_matches_hand_computation_on_four_units() -> None:
    # 人口 100/50/50 を 4 議席: 除数 50 超〜100 未満で ceil → 2,1,1。
    out = adams({"a": 100.0, "b": 50.0, "c": 50.0}, 4)
    assert out == {"a": 2, "b": 1, "c": 1}


def test_gallagher_zero_when_proportional() -> None:
    assert gallagher({"A": 60.0, "B": 40.0}, {"A": 60.0, "B": 40.0}) == 0.0
    assert gallagher({"A": 60.0, "B": 40.0}, {"A": 70.0, "B": 30.0}) == pytest.approx(10.0)
    assert gallagher({"A": 60.0, "B": 40.0}, {"A": 100.0}) == pytest.approx(40.0)


def test_threshold_share_is_the_last_quotient() -> None:
    votes = {"A": 100.0, "B": 60.0, "X": 0.0}
    # 4 議席: 他党の商 100, 60, 50, 33.3, 30, 25 … 4 番目 = 33.3 → X は 33.3 票超で 1 議席
    assert threshold_share(votes, 4, "X") == pytest.approx(100 * (100 / 3) / (160 + 100 / 3))
    # 議席が多いほど閾値は下がる
    assert threshold_share(votes, 8, "X") < threshold_share(votes, 4, "X")
