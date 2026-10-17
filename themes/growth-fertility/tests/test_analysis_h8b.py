"""H8b: 学歴群内の望む数の低下の候補比較（a20261018_h8b_within_group）の純粋ヘルパのテスト。"""

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h8b_within_group as h8b

SIG_NEG = (-0.5, 0.1, -0.7, -0.3)
SIG_POS = (0.8, 0.2, 0.4, 1.2)
NS_BIG = (-0.9, 0.6, -2.1, 0.3)


# ---------------------------------------------------------------- derived columns
def test_cash_employed_is_employed_times_cash_share() -> None:
    assert h8b.cash_employed(60.0, 30.0, 20.0) == pytest.approx(30.0)


def test_cash_employed_none_propagates() -> None:
    assert h8b.cash_employed(None, 30.0, 20.0) is None
    assert h8b.cash_employed(60.0, None, 20.0) is None
    assert h8b.cash_employed(60.0, 30.0, None) is None


def test_add_derived_matches_scalar_and_splits_noncash() -> None:
    st = pl.DataFrame(
        {
            "married_employed": [60.0, 40.0, None],
            "married_cash_only": [30.0, 50.0, 10.0],
            "married_cash_inkind": [20.0, None, 10.0],
        }
    )
    out = h8b.add_derived(st)
    assert out["married_cash_employed"].to_list()[0] == pytest.approx(30.0)
    assert out["married_noncash_employed"].to_list()[0] == pytest.approx(30.0)
    assert out["married_cash_employed"].to_list()[1:] == [None, None]
    assert out["married_noncash_employed"].to_list()[1:] == [None, None]


# ---------------------------------------------------------------- standardisation
def test_standardize_gives_mean_zero_sd_one() -> None:
    f = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [0.0, 0.0, 1.0, 1.0]})
    out, sds = h8b.standardize(f, ["x"])
    assert sds["x"] == pytest.approx(f["x"].std())
    assert out["x"].mean() == pytest.approx(0.0)
    assert out["x"].std() == pytest.approx(1.0)
    assert out["y"].to_list() == f["y"].to_list()


def test_standardize_within_uses_deviation_from_group_mean() -> None:
    f = pl.DataFrame({"g": ["a", "a", "b", "b"], "x": [0.0, 2.0, 10.0, 12.0]})
    _, sds = h8b.standardize(f, ["x"], within="g")
    # deviations: -1, 1, -1, 1 -> sample SD = sqrt(4/3)
    assert sds["x"] == pytest.approx((4 / 3) ** 0.5)


def test_standardize_rejects_constant_column() -> None:
    with pytest.raises(ValueError, match="SD"):
        h8b.standardize(pl.DataFrame({"x": [1.0, 1.0, 1.0]}), ["x"])


# ---------------------------------------------------------------- leader / candidate
def test_leader_is_largest_abs_among_ci_excluding_zero() -> None:
    coefs = {"emp": SIG_NEG, "mcpr": SIG_POS, "ln_u5": NS_BIG}
    assert h8b.leader(coefs) == "mcpr"


def test_leader_none_when_all_cis_cover_zero() -> None:
    assert h8b.leader({"emp": NS_BIG, "mcpr": (0.1, 0.1, -0.1, 0.3)}) is None


def test_leader_respects_allowed_set() -> None:
    coefs = {"sec": (-2.0, 0.1, -2.2, -1.8), "emp": SIG_NEG}
    assert h8b.leader(coefs, allowed=("emp",)) == "emp"


def test_candidate_mapping_is_closed() -> None:
    assert h8b.candidate_of("emp") == "W"
    assert h8b.candidate_of("cash_emp") == "W"
    assert h8b.candidate_of("att_pri") == "S"
    assert h8b.candidate_of("att_sec") == "S"
    assert h8b.candidate_of("mcpr") == "C"
    assert h8b.candidate_of("ln_u5") == "U"
    assert h8b.candidate_of(None) is None
    with pytest.raises(KeyError):
        h8b.candidate_of("sec")


# ---------------------------------------------------------------- decision rule
def test_decide_none_when_x1_selects_nothing() -> None:
    d = h8b.decide(None, x5_median=5.0, checks={"X2": "W"}, x4_supports_w=True)
    assert d.code == "none"
    assert "どの候補も確かめられない" in d.sentence


def test_decide_w_requires_rising_employment() -> None:
    d = h8b.decide("W", x5_median=-1.0, checks={}, x4_supports_w=True)
    assert d.code == "W_fails"
    assert "W は成り立たない" in d.sentence
    assert h8b.decide("W", x5_median=0.0, checks={}, x4_supports_w=True).code == "W_fails"
    assert h8b.decide("W", x5_median=None, checks={}, x4_supports_w=True).code == "W_fails"


def test_decide_selects_when_checks_agree_or_are_silent() -> None:
    d = h8b.decide("C", x5_median=-3.0, checks={"X2": "C", "X3": None}, x4_supports_w=False)
    assert d.code == "C"
    assert "最も強く並走する候補は C" in d.sentence


def test_decide_conflict_when_a_check_picks_another_candidate() -> None:
    d = h8b.decide("C", x5_median=1.0, checks={"X2": "S", "X3": "C"}, x4_supports_w=None)
    assert d.code == "undetermined"
    assert d.conflicts == ("X2=S",)
    assert "候補は絞れない" in d.sentence


def test_decide_x4_only_matters_for_w() -> None:
    assert h8b.decide("W", x5_median=2.0, checks={}, x4_supports_w=False).code == "undetermined"
    assert h8b.decide("W", x5_median=2.0, checks={}, x4_supports_w=True).code == "W"
    assert h8b.decide("S", x5_median=2.0, checks={}, x4_supports_w=False).code == "S"
