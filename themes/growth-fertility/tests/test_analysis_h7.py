"""H7: 国間の所得勾配の分解・段階・順序（a20261013_h7_between_gradient）の純粋ヘルパのテスト。"""

import math

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261013_h7_between_gradient as h7


# ---------------------------------------------------------------- T1 Gelbach
def _synthetic_frame() -> pl.DataFrame:
    rows = []
    for i in range(12):
        for year in (2000, 2010):
            x = 7.0 + 0.3 * i + (0.1 if year == 2010 else 0.0)
            m1 = 100.0 - 8.0 * x + ((i * 7) % 5)
            m2 = 2.0 * x + ((i * 3) % 4) * 0.5
            y = 8.0 - 0.2 * x + 0.03 * m1 - 0.1 * m2 + ((i * 11) % 3) * 0.1
            rows.append(
                {"iso3": f"C{i:02d}", "year": year, "tfr": y, "ln_gdp": x, "m1": m1, "m2": m2}
            )
    return pl.DataFrame(rows)


def test_gelbach_contributions_sum_to_base_minus_full() -> None:
    g = h7.gelbach(_synthetic_frame(), mediators=("m1", "m2"))
    assert sum(g.deltas.values()) == pytest.approx(g.beta0 - g.beta_full, abs=1e-9)
    assert set(g.deltas) == {"m1", "m2"}


def test_gelbach_share_is_explained_over_base() -> None:
    g = h7.gelbach(_synthetic_frame(), mediators=("m1", "m2"))
    assert g.share == pytest.approx((g.beta0 - g.beta_full) / g.beta0)


def test_gelbach_is_order_independent() -> None:
    a = h7.gelbach(_synthetic_frame(), mediators=("m1", "m2"))
    b = h7.gelbach(_synthetic_frame(), mediators=("m2", "m1"))
    for k in ("m1", "m2"):
        assert a.deltas[k] == pytest.approx(b.deltas[k])


# ---------------------------------------------------------------- decision rules
@pytest.mark.parametrize(
    ("s", "expected"),
    [(0.8, {"B", "C"}), (0.6, {"B", "C"}), (0.5, set()), (0.39, {"A"})],
)
def test_t1_points(s: float, expected: set[str]) -> None:
    assert h7.t1_points(s) == expected


def test_t2_points() -> None:
    assert h7.t2_points(0.1, -0.1, 0.3) == {"B", "C"}
    assert h7.t2_points(-0.25, -0.5, 0.01) == set()  # CI covers 0 but |b| > 0.20
    assert h7.t2_points(-0.35, -0.6, -0.1) == {"A"}
    assert h7.t2_points(-0.25, -0.4, -0.1) == set()


def test_t3_points() -> None:
    assert h7.t3_points(6.0) == {"B"}
    assert h7.t3_points(2.0) == {"C"}
    assert h7.t3_points(3.5) == set()


def test_t4_points() -> None:
    assert h7.t4_points(0.4, stage_dominates=True, lagged_income_only=False) == {"B"}
    assert h7.t4_points(0.4, stage_dominates=False, lagged_income_only=True) == set()
    assert h7.t4_points(0.75, stage_dominates=True, lagged_income_only=True) == {"C"}
    assert h7.t4_points(0.6, stage_dominates=True, lagged_income_only=True) == set()


def test_t5_points() -> None:
    assert h7.t5_points(n_poor_fell=12, n_rich_not=10, poor_fell_u5_ok=True) == {"B"}
    assert h7.t5_points(n_poor_fell=12, n_rich_not=9, poor_fell_u5_ok=True) == set()
    assert h7.t5_points(n_poor_fell=4, n_rich_not=20, poor_fell_u5_ok=False) == {"C"}


def test_select_answer_clear_winner() -> None:
    assert h7.select_answer({"A": 0, "B": 4, "C": 2}).startswith("B")


def test_select_answer_one_point_gap_is_mixture() -> None:
    out = h7.select_answer({"A": 1, "B": 3, "C": 2})
    assert out.startswith("mixture: mainly B")
    assert "C" in out


def test_select_answer_tie_is_mixture() -> None:
    assert h7.select_answer({"A": 0, "B": 2, "C": 2}).startswith("mixture: B and C tied")


def test_select_answer_none_reaches_two() -> None:
    assert h7.select_answer({"A": 1, "B": 1, "C": 0}).startswith("none")


# ---------------------------------------------------------------- T5 quadrants
@pytest.mark.parametrize(
    ("ratio", "drop", "expected"),
    [
        (3.0, 2.0, "richer_fell"),
        (5.0, 0.5, "richer_not_fell"),
        (1.5, 3.0, "not_richer_fell"),
        (2.99, 1.99, "not_richer_not_fell"),
        (None, 3.0, None),
        (2.0, None, None),
    ],
)
def test_quadrant(ratio: float | None, drop: float | None, expected: str | None) -> None:
    assert h7.quadrant(ratio, drop) == expected


# ---------------------------------------------------------------- T4 event time
def test_event_time_aligns_on_onset_and_deviates_from_year_zero() -> None:
    panel = pl.DataFrame(
        {
            "iso3": ["A"] * 4 + ["B"] * 3,
            "year": [1970, 1975, 1980, 1985, 1990, 1995, 2000],
            "v": [1.0, 2.0, 4.0, None, 10.0, 11.0, 13.0],
        }
    )
    out = h7.event_time(panel, {"A": 1975, "B": 1995, "C": 1980}, "v", window=(-5, 5))
    a = {r["event_time"]: r["dev"] for r in out.filter(pl.col("iso3") == "A").to_dicts()}
    assert a == {-5: -1.0, 0: 0.0, 5: 2.0}  # 1985 missing -> absent, not imputed
    b = {r["event_time"]: r["dev"] for r in out.filter(pl.col("iso3") == "B").to_dicts()}
    assert b == {-5: -1.0, 0: 0.0, 5: 2.0}
    assert "C" not in out["iso3"].to_list()


def test_event_time_drops_country_without_year_zero_value() -> None:
    panel = pl.DataFrame({"iso3": ["A", "A"], "year": [1970, 1980], "v": [1.0, 2.0]})
    assert h7.event_time(panel, {"A": 1975}, "v", window=(-5, 5)).height == 0


# ---------------------------------------------------------------- T4 long differences
def test_long_differences_non_overlapping_with_lag() -> None:
    panel = pl.DataFrame(
        {"iso3": ["A"] * 4, "year": [1960, 1970, 1980, 1990], "x": [1.0, 3.0, 6.0, 10.0]}
    )
    out = h7.long_differences(panel, ("x",), width=10, start=1960, end=1990)
    rows = out.sort("period").to_dicts()
    assert [r["period"] for r in rows] == [1960, 1970, 1980]
    assert [r["d_x"] for r in rows] == [2.0, 3.0, 4.0]
    assert [r["lag_d_x"] for r in rows] == [None, 2.0, 3.0]


def test_long_differences_missing_endpoint_is_null() -> None:
    panel = pl.DataFrame({"iso3": ["A", "A"], "year": [1960, 1980], "x": [1.0, 5.0]})
    out = h7.long_differences(panel, ("x",), width=10, start=1960, end=1980)
    assert out.sort("period")["d_x"].to_list() == [None, None]


# ---------------------------------------------------------------- T2 composite index
def test_pc1_index_sign_points_to_advanced_stage() -> None:
    frame = pl.DataFrame(
        {
            "ln_u5": [5.0, 4.0, 3.0, 2.0, 1.0],
            "life_exp": [45.0, 55.0, 62.0, 70.0, 80.0],
            "enrol": [10.0, 30.0, 60.0, 80.0, 100.0],
        }
    )
    scores, loadings = h7.pc1_index(frame, ("ln_u5", "life_exp", "enrol"), anchor="life_exp")
    assert loadings["life_exp"] > 0 and loadings["ln_u5"] < 0
    assert list(scores) == sorted(scores)


def test_quintile_of_uses_fixed_cutpoints() -> None:
    assert h7.quintile_of([float(i) for i in range(10)]) == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_p90_p10_ratio() -> None:
    assert h7.p90_p10([float(v) for v in range(1, 12)]) == pytest.approx(10.0 / 2.0)
    assert math.isnan(h7.p90_p10([]))
