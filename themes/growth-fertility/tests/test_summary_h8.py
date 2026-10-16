import pytest

from theme_growth_fertility.analysis import s20261017_h8_summary as s


def test_split_share_returns_part_and_rest() -> None:
    a, b = s.split_share(-65.7, -87.0)
    assert a == pytest.approx(0.7552, abs=1e-4)
    assert a + b == pytest.approx(1.0)


def test_split_share_rejects_zero_total() -> None:
    with pytest.raises(ValueError):
        s.split_share(1.0, 0.0)


def test_median_by_index_is_elementwise() -> None:
    rows = [{"d": [-1.0, 0.0]}, {"d": [-0.5, -0.2]}, {"d": [-0.7, 0.4]}]
    assert s.median_by_index(rows, "d") == [-0.7, 0.0]
    assert s.median_by_index([], "d") == []


def test_scorecard_rows_orders_and_translates() -> None:
    rows = s.scorecard_rows({"M3": "support", "M1": "no", "M2": "partial"})
    assert [r[0] for r in rows] == ["M1", "M2", "M3"]
    assert [r[2] for r in rows] == ["不支持", "部分的支持", "支持"]


def test_spec_rows_flags_ci_excluding_zero() -> None:
    rows = s.spec_rows([("a", (0.2, 0.1, -0.19, 0.6)), ("b", (0.56, 0.1, 0.21, 0.91))])
    assert rows[0] == ("a", 0.2, -0.19, 0.6, False)
    assert rows[1][4] is True
    assert s.spec_rows([("c", (-0.3, 0.1, -0.5, -0.1))])[0][4] is True
