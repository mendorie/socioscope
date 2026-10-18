"""H10: 家族形成の制約（a20261018_h10_family_formation）の純粋ヘルパのテスト。"""

import math

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h10_family_formation as h10


# ---------------------------------------------------------------- sign tests
def test_passes_needs_predicted_sign_and_ci_excluding_zero() -> None:
    assert h10.passes((0.5, 0.1, 0.1, 0.9), 1)
    assert not h10.passes((0.5, 0.3, -0.1, 1.1), 1)
    assert h10.passes((-0.5, 0.1, -0.9, -0.1), -1)
    assert not h10.passes((0.5, 0.1, 0.1, 0.9), -1)
    assert not h10.passes(None, 1)


def test_passes_treats_nan_ci_as_not_passing() -> None:
    assert not h10.passes((0.5, math.nan, math.nan, math.nan), 1)


def _fit(**coefs: tuple[float, float, float, float]) -> h10.Fit:
    return h10.Fit(dict(coefs), 50, 10, (1990, 1995))


def test_a_test_majority_of_estimated_outcomes() -> None:
    ok = (1.0, 0.1, 0.5, 1.5)
    neg = (-1.0, 0.1, -1.5, -0.5)
    zero = (0.0, 1.0, -1.0, 1.0)
    fits = {"fagem": _fit(x=ok), "cmr": _fit(x=neg), "tfr1": _fit(x=zero)}
    assert h10.a_test(fits, "x")  # fagem + and cmr − pass: 2 of 3
    fits2 = {"fagem": _fit(x=ok), "cmr": _fit(x=zero), "tfr1": None}
    assert not h10.a_test(fits2, "x")  # 1 of 2 estimated is not a majority
    fits3 = {"fagem": _fit(x=ok), "cmr": None, "tfr1": None}
    assert h10.a_test(fits3, "x")
    assert not h10.a_test({"fagem": None, "cmr": None, "tfr1": None}, "x")


def test_c_y_test_either_passes_and_none_wrong_way() -> None:
    inc_ok = (-1.0, 0.1, -1.5, -0.5)
    un_ok = (1.0, 0.1, 0.5, 1.5)
    null = (0.0, 1.0, -1.0, 1.0)
    assert h10.c_y_test(inc_ok, null)
    assert h10.c_y_test(null, un_ok)
    assert not h10.c_y_test(null, null)
    assert not h10.c_y_test(inc_ok, (-1.0, 0.1, -1.5, -0.5))  # unemployment significant wrong way
    assert h10.c_y_test((1.0, 0.1, 0.5, 1.5), (-1.0, 0.1, -1.5, -0.5), flip=True)


# ---------------------------------------------------------------- verdict
def test_support_is_strict_majority() -> None:
    assert h10.support([True, True, False])
    assert not h10.support([True, False])
    assert h10.support([True])
    assert not h10.support([])


def test_leader_none_when_nothing_supported() -> None:
    tests = {"E": [False, False, False], "H": [True, False], "Y": [True, False], "W": [False]}
    assert h10.leader(tests, b_passed=False) is None


def test_leader_most_passes_then_b_then_ratio_then_order() -> None:
    tests = {"E": [True, True, False], "H": [True, True], "Y": [False, False], "W": [True]}
    # E and H both pass 2; E passed B -> E
    assert h10.leader(tests, b_passed=True) == "E"
    # without B: ratio H 2/2 > E 2/3 -> H
    assert h10.leader(tests, b_passed=False) == "H"
    t2 = {"E": [False, False, False], "H": [False, False], "Y": [True, True], "W": [True]}
    assert h10.leader(t2, b_passed=False) == "Y"  # 2 passes beats 1
    t3 = {"E": [False, False, False], "H": [False, False], "Y": [True, False], "W": [True]}
    assert h10.leader(t3, b_passed=False) == "W"


def test_final_stance_pattern() -> None:
    assert h10.final_stance(None, 0.1).startswith("測れた制約では確かめられず")
    s = h10.final_stance("E", 0.34)
    assert "主要な制約は若年層の雇用の不安定さ（非正規化）" in s
    assert "未婚化の3割" in s and "残る7割" in s


def test_comp_clause_wording_follows_sign() -> None:
    assert "非正規に寄った分は 34%" in h10.comp_clause(0.34, 0.2)
    assert "むしろ正規に寄り" in h10.comp_clause(-0.17, -0.05)


def test_framed_stance_lists_passes_and_changes() -> None:
    s = h10.framed_stance(
        lead=None,
        comp_share=-0.17,
        comp_lower=-0.05,
        rate_share=0.95,
        gap=-36.1,
        passed={"E": [], "Y": ["A 若年失業"]},
        robust_changes=["C outcome nm50 で Y が支持"],
    )
    assert s.startswith("測れた制約では確かめられず")
    assert "Y（A 若年失業）" in s and "36.1 ポイント" in s and "C outcome nm50" in s


# ---------------------------------------------------------------- decomposition
def test_nonreg_share() -> None:
    assert h10.nonreg_share(75.0, 25.0) == pytest.approx(25.0)
    assert h10.nonreg_share(None, 1.0) is None
    assert h10.nonreg_share(0.0, 0.0) is None


def _emp_rows(year: int, age: str, vals: dict[str, tuple[float, float]]) -> list[dict[str, object]]:
    return [
        {
            "survey_year": year,
            "sex": "male",
            "age_class": age,
            "employment": e,
            "marital": m,
            "persons": v[i],
        }
        for e, v in vals.items()
        for i, m in enumerate(("total", "never_married"))
    ]


def test_b_cells_other_is_residual_and_sum4_option() -> None:
    vals = {
        "total_pop": (100.0, 50.0),
        "regular": (60.0, 20.0),
        "nonregular": (25.0, 20.0),
        "part_time": (5.0, 4.0),
        "arbeit": (5.0, 4.0),
        "dispatched": (5.0, 4.0),
        "contract": (5.0, 4.0),
    }
    df = pl.DataFrame(_emp_rows(2012, "30-34", vals))
    c = h10.b_cells(df, 2012, "male", ("30-34",))
    assert c[("30-34", "other")] == (15.0, 10.0)
    c4 = h10.b_cells(df, 2012, "male", ("30-34",), sum4=True)
    assert c4[("30-34", "nonregular")] == (20.0, 16.0)
    assert c4[("30-34", "other")] == (20.0, 14.0)


def test_kitagawa_age_is_exact_and_separates_composition() -> None:
    c0 = {
        ("a", "regular"): (80.0, 32.0),
        ("a", "nonregular"): (10.0, 7.0),
        ("a", "other"): (10.0, 6.0),
        ("b", "regular"): (70.0, 14.0),
        ("b", "nonregular"): (20.0, 12.0),
        ("b", "other"): (10.0, 4.0),
    }
    c1 = {
        ("a", "regular"): (60.0, 30.0),
        ("a", "nonregular"): (30.0, 24.0),
        ("a", "other"): (10.0, 7.0),
        ("b", "regular"): (100.0, 25.0),
        ("b", "nonregular"): (40.0, 28.0),
        ("b", "other"): (60.0, 30.0),
    }
    d = h10.kitagawa_age(c0, c1)
    r0 = (32 + 7 + 6 + 14 + 12 + 4) / 200
    r1 = (30 + 24 + 7 + 25 + 28 + 30) / 300
    assert d.r0 == pytest.approx(r0)
    assert d.r1 == pytest.approx(r1)
    assert d.rate + d.emp_comp + d.age_comp == pytest.approx(r1 - r0)
    assert d.emp_comp > 0  # shift toward non-regular (higher rate) in both ages


def test_kitagawa_age_pure_rate_change_has_no_composition() -> None:
    c0 = {
        ("a", "regular"): (50.0, 10.0),
        ("a", "nonregular"): (50.0, 20.0),
        ("a", "other"): (0.0, 0.0),
    }
    c0[("a", "other")] = (10.0, 5.0)
    c1 = {k: (n, m * 1.5) for k, (n, m) in c0.items()}
    d = h10.kitagawa_age(c0, c1)
    assert d.emp_comp == pytest.approx(0.0)
    assert d.age_comp == pytest.approx(0.0)
    assert d.rate_share == pytest.approx(1.0)


# ---------------------------------------------------------------- panels
def test_nearest_panel_window_and_tie_to_earlier() -> None:
    obs = {"x": {"01": {2007: 1.0, 2012: 2.0}, "02": {1980: 5.0}}}
    f = h10.nearest_panel(obs, ["01", "02"], [2010, 1990], 5)
    v = {(r["unit"], r["year"]): r["x"] for r in f.iter_rows(named=True)}
    assert v[("01", 2010)] == 2.0  # 2012 (2 years) beats 2007 (3)
    assert v[("01", 1990)] is None
    assert v[("02", 1990)] is None  # 10 years away > window
    obs2 = {"x": {"01": {2010: 1.0, 2020: 2.0}}}
    f2 = h10.nearest_panel(obs2, ["01"], [2015], 5)
    assert f2["x"].to_list() == [1.0]


def test_fit_std_recovers_standardised_slope_with_fe() -> None:
    rows = []
    for u in range(8):
        for t in range(4):
            x = float((u * 3 + t * 5) % 7)
            rows.append({"unit": f"u{u}", "year": t, "x": x, "y": 2.0 * x + u + 0.5 * t})
    f = pl.DataFrame(rows)
    est = h10.fit_std(f, "y", ["x"], unit="unit", time="year")
    assert est is not None
    sd = float(f["x"].std() or 0)
    assert est.coefs["x"][0] == pytest.approx(2.0 * sd)
    assert est.n == 32 and est.groups == 8 and est.times == (0, 1, 2, 3)


def test_fit_std_returns_none_when_too_small() -> None:
    f = pl.DataFrame({"unit": ["a", "b"], "year": [1, 1], "x": [1.0, 2.0], "y": [1.0, 2.0]})
    assert h10.fit_std(f, "y", ["x"], unit="unit", time="year") is None


def test_fit_std_returns_none_when_regressor_has_no_within_variation() -> None:
    rows = [
        {"unit": f"u{u}", "year": t, "x": float(u), "y": float(u + t * (u % 3))}
        for u in range(30)
        for t in range(2)
    ]
    f = pl.DataFrame(rows)
    assert h10.fit_std(f, "y", ["x"], unit="unit", time="year") is None


def test_wari_rounds_to_tenths() -> None:
    assert h10.wari(0.34) == "3"
    assert h10.wari(0.66) == "7"
