"""H9: 規範の崩れ vs 実現の阻害（a20261018_h9_norms_vs_constraints）の純粋ヘルパのテスト。"""

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h9_norms_vs_constraints as h9


# ---------------------------------------------------------------- V1 classification
def test_classify_v1_norm_when_latest_below_2_1_and_fell_0_2() -> None:
    # Japan, planned (xlsx): 2.17 -> 1.95
    assert h9.classify_v1(2.17, 1.95, 0.37, 0.65) == "N"


def test_classify_v1_drop_of_exactly_0_2_counts_despite_float_noise() -> None:
    assert h9.classify_v1(2.25, 2.05, 0.5, 0.5) == "N"


def test_classify_v1_latest_equal_to_2_1_is_not_norm() -> None:
    # Finland 2.478 -> 2.10: not strictly below 2.1
    assert h9.classify_v1(2.478, 2.10, 0.638, 0.64) == "mixed"


def test_classify_v1_constraint_needs_level_gap_and_widening() -> None:
    assert h9.classify_v1(2.61, 2.25, 0.81, 0.95) == "C"
    assert h9.classify_v1(2.4, 2.21, 1.0, 0.81) == "mixed"  # gap narrowed
    assert h9.classify_v1(2.27, 2.32, 0.47, 0.51) == "mixed"  # gap < 0.6
    assert h9.classify_v1(2.0, 2.19, 0.6, 0.9) == "mixed"  # level < 2.2


def test_classify_v1_gap_of_exactly_0_6_counts() -> None:
    assert h9.classify_v1(2.3, 2.2, 0.5, 2.2 - 1.6) == "C"


def test_classify_v1_thresholds_are_parameters() -> None:
    assert h9.classify_v1(2.4, 2.15, 0.6, 0.7, n_max=2.2) == "N"
    assert h9.classify_v1(2.3, 2.25, 0.5, 0.7, gap=0.8) == "mixed"


def test_majority_requires_more_than_half() -> None:
    assert h9.majority(["N", "N", "C"], "N", "C") == "N"
    assert h9.majority(["C", "C", "N", "mixed"], "N", "C") == "differs"  # exactly half
    assert h9.majority(["C", "C", "C", "mixed"], "N", "C") == "C"
    assert h9.majority([], "N", "C") == "undetermined"


# ---------------------------------------------------------------- V2 decomposition
def test_order_decline_share_of_first_order() -> None:
    start = {"1": 0.68, "2": 0.50, "3": 0.17, "4": 0.04}
    end = {"1": 0.55, "2": 0.41, "3": 0.14, "4": 0.04}
    total, share = h9.order_decline(start, end, "1")
    assert total == pytest.approx(-0.25)
    assert share == pytest.approx(0.13 / 0.25)


def test_order_decline_uses_only_orders_in_both_years() -> None:
    total, share = h9.order_decline({"1": 1.0, "2": 1.0, "x": 5.0}, {"1": 0.5, "2": 1.0}, "1")
    assert total == pytest.approx(-0.5)
    assert share == pytest.approx(1.0)


def test_order_decline_returns_none_share_when_no_decline() -> None:
    total, share = h9.order_decline({"1": 0.6, "2": 0.5}, {"1": 0.62, "2": 0.5}, "1")
    assert total > 0
    assert share is None


def test_order_decline_rejects_missing_first_order() -> None:
    with pytest.raises(ValueError):
        h9.order_decline({"2": 1.0}, {"2": 0.5}, "1")


@pytest.mark.parametrize(
    ("share", "kind"),
    [
        (0.5, "childlessness"),
        (1.26, "childlessness"),
        (0.4, "one_child"),
        (0.28, "one_child"),
        (0.45, "mixed"),
        (None, "no_decline"),
    ],
)
def test_classify_v2(share: float | None, kind: str) -> None:
    assert h9.classify_v2(share) == kind


def test_approx_order_tfr_scales_tfr_by_known_order_shares() -> None:
    out = h9.approx_order_tfr(0.8, {"a": 60.0, "b": 30.0, "c": 10.0})
    assert out["a"] == pytest.approx(0.48)
    assert sum(out.values()) == pytest.approx(0.8)
    with pytest.raises(ValueError):
        h9.approx_order_tfr(1.0, {"a": 0.0})


def test_lead_order_uses_median_share() -> None:
    assert h9.lead_order([0.3, 0.6, 0.55]) == "first"
    assert h9.lead_order([0.3, 0.498, 0.6]) == "later"
    with pytest.raises(ValueError):
        h9.lead_order([])


def test_eu_complete_years_requires_all_four_orders() -> None:
    eu = pl.DataFrame(
        {
            "iso3": ["X"] * 7,
            "year": [2010, 2010, 2010, 2010, 2011, 2011, 2011],
            "order": ["1", "2", "3", "GE4", "1", "2", "TOTAL"],
            "tfr": [0.7, 0.5, 0.2, 0.1, 0.7, 0.5, 1.5],
        }
    )
    assert h9.eu_complete_years(eu, "X") == [2010]


# ---------------------------------------------------------------- V3 cohorts
def test_classify_v3_recovery_and_quantitative() -> None:
    assert h9.classify_v3(1.79, 2.03, 1.13) == "recovery"
    assert h9.classify_v3(1.455, 1.845, 1.26) == "quantitative"
    assert h9.classify_v3(1.43, 1.69, 1.19) == "neither"  # drop 0.26 < 0.3
    assert h9.classify_v3(1.6, 2.0, 1.2) == "both"


def test_classify_v3_quantitative_needs_the_reference_cohort() -> None:
    assert h9.classify_v3(1.4, None, 1.3) == "neither"


def test_classify_v3_quantitative_needs_level_below_1_7() -> None:
    assert h9.classify_v3(1.72, 2.1, 1.6) == "neither"


def test_period_min_picks_lowest_and_earliest_on_ties() -> None:
    assert h9.period_min({1990: 1.5, 1995: 1.2, 2000: 1.2}, [1990, 1995, 2000]) == (1995, 1.2)
    assert h9.period_min({1990: 1.5}, [2000]) is None


def test_v3_row_uses_1980_2005_window_and_reference_cohorts() -> None:
    tfr = {("X", y): 2.0 for y in range(1980, 2006)}
    tfr[("X", 1999)] = 1.1
    tfr[("X", 2010)] = 0.5  # outside the window
    row = h9.v3_row("X", {1950: 2.1, 1960: 2.0, 1975: 1.5}, tfr, 45)
    assert row is not None
    assert (row.min_year, row.min_tfr) == (1999, 1.1)
    assert row.kind == "both"
    assert h9.v3_row("X", {1960: 2.0}, tfr, 45) is None


# ---------------------------------------------------------------- V4 and stance
def test_v4_verdict_rules() -> None:
    assert h9.v4_verdict("N", "childlessness") == "support"
    assert h9.v4_verdict("N", "one_child") == "partial"
    assert h9.v4_verdict("C", "childlessness") == "not_supported"
    assert h9.v4_verdict("differs", "childlessness") == "differs"


def test_final_stance_follows_the_preregistered_pattern() -> None:
    s = h9.final_stance("C", n_names=[], c_names=["日本"], lead="first", recovered=False)
    assert s == (
        "2 人未満への低下は実現の阻害であり、低下の主役は第 1 子の減少である。"
        "コーホートで見ると回復していない。"
    )
    s = h9.final_stance(
        "differs", n_names=["日本"], c_names=["英国", "デンマーク"], lead="later", recovered=True
    )
    assert s.startswith(
        "2 人未満への低下は国で異なり、日本は規範型・英国・デンマークは阻害型であり"
    )
    assert "第 2 子以降の減少" in s
    assert s.endswith("回復している。")


# ---------------------------------------------------------------- V1 rows
def test_v1_rows_selects_low_tfr_countries_with_two_points() -> None:
    pts = {
        "A": [("w1", 2006, 2.4), ("w2", 2011, 2.3)],
        "B": [("w1", 2006, 2.4)],  # one point
        "C": [("w1", 2006, 2.4), ("w2", 2011, 2.3)],  # TFR too high
        "D": [("w1", 2006, 2.4), ("w2", 2030, 2.0)],  # 2030 has no TFR
    }
    tfr = {("A", 2006): 1.8, ("A", 2011): 1.5, ("C", 2006): 1.9, ("C", 2011): 1.9}
    tfr |= {("D", 2006): 1.5}
    latest = {"A": (2024, 1.3), "B": (2024, 1.2), "C": (2024, 1.7), "D": (2024, 1.2)}
    rows = h9.v1_rows(pts, tfr, latest)
    assert [r.iso3 for r in rows] == ["A"]
    r = rows[0]
    assert r.first_gap == pytest.approx(0.6)
    assert r.last_gap == pytest.approx(0.8)
    assert r.kind == "C"
