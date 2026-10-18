"""H11: 結婚の減少と出生率（a20261018_h11_marriage_share）の純粋ヘルパのテスト。"""

import math

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h11_marriage_share as h11


# ---------------------------------------------------------------- J1 building blocks
def test_asfr_5yr_sums_single_years_and_refuses_gaps() -> None:
    asfr = {a: 0.01 * (a - 14) for a in range(15, 50)}
    out = h11.asfr_5yr(asfr)
    assert out is not None
    assert out["15-19"] == pytest.approx(0.01 * (1 + 2 + 3 + 4 + 5))
    assert sum(out.values()) == pytest.approx(sum(asfr.values()))
    del asfr[37]
    assert h11.asfr_5yr(asfr) is None


def test_cm_index_is_fertility_weighted_married_share() -> None:
    ages = ("a", "b")
    m = {"a": 0.5, "b": 1.0}
    f = {"a": 1.0, "b": 3.0}
    assert h11.cm_index(m, f, ages) == pytest.approx((0.5 * 1 + 1.0 * 3) / 4)
    # everyone married -> Cm = 1
    assert h11.cm_index({"a": 1.0, "b": 1.0}, f, ages) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        h11.cm_index(m, {"a": 0.0, "b": 0.0}, ages)


def test_cm_standard_is_tfr_over_marital_tfr() -> None:
    ages = ("a", "b")
    m = {"a": 0.5, "b": 1.0}
    f = {"a": 1.0, "b": 3.0}
    tm = 1.0 / 0.5 + 3.0 / 1.0
    assert h11.cm_standard(m, f, ages) == pytest.approx(4.0 / tm)


def test_decomposition_identity_on_synthetic_data() -> None:
    ages = ("a", "b", "c")
    f0 = {"a": 0.3, "b": 0.9, "c": 0.4}
    m0 = {"a": 0.4, "b": 0.8, "c": 0.9}
    f1 = {"a": 0.1, "b": 0.5, "c": 0.5}
    m1 = {"a": 0.1, "b": 0.4, "c": 0.7}
    tfr = {0: sum(f0.values()), 1: sum(f1.values())}
    cm = {0: h11.cm_index(m0, f0, ages), 1: h11.cm_index(m1, f1, ages)}
    dc = h11.decompose(0, 1, tfr, cm)
    assert dc.d_ln_cm + dc.d_ln_rest == pytest.approx(dc.d_ln_tfr, abs=1e-12)
    assert dc.s_m == pytest.approx(dc.d_ln_cm / dc.d_ln_tfr)


def test_marriage_only_change_gives_s_m_one() -> None:
    # Marital fertility g_a fixed, only married shares fall uniformly: TFR and Cm scale together.
    ages = ("a", "b")
    g = {"a": 2.0, "b": 1.0}
    m0 = {"a": 0.8, "b": 0.8}
    m1 = {"a": 0.4, "b": 0.4}
    f0 = {a: g[a] * m0[a] for a in ages}
    f1 = {a: g[a] * m1[a] for a in ages}
    tfr = {0: sum(f0.values()), 1: sum(f1.values())}
    cm = {0: h11.cm_index(m0, f0, ages), 1: h11.cm_index(m1, f1, ages)}
    dc = h11.decompose(0, 1, tfr, cm)
    assert dc.s_m == pytest.approx(1.0)


def test_marital_fertility_only_change_gives_s_m_zero() -> None:
    ages = ("a", "b")
    m = {"a": 0.5, "b": 0.9}
    f0 = {"a": 0.4, "b": 1.8}
    f1 = {a: 0.6 * v for a, v in f0.items()}  # proportional fall within marriage
    tfr = {0: sum(f0.values()), 1: sum(f1.values())}
    cm = {0: h11.cm_index(m, f0, ages), 1: h11.cm_index(m, f1, ages)}
    assert h11.decompose(0, 1, tfr, cm).s_m == pytest.approx(0.0, abs=1e-12)


def test_cohort_share_identity() -> None:
    c0 = h11.CohortPoint(1950, 2.0, 0.95)
    c1 = h11.CohortPoint(1970, 1.5, 0.80)
    assert h11.cohort_share(c0, c1) == pytest.approx(math.log(0.80 / 0.95) / math.log(1.5 / 2.0))


# ---------------------------------------------------------------- verdict and stance
def test_verdict_thresholds() -> None:
    assert h11.verdict(0.70, True) == "main"
    assert h11.verdict(2 / 3, True) == "main"
    assert h11.verdict(1.2, False) == "main_unconfirmed"
    assert h11.verdict(0.5, True) == "both"
    assert h11.verdict(1 / 3, False) == "both"
    assert h11.verdict(0.2, True) == "couple"
    assert h11.verdict(-0.1, True) == "couple"


def test_final_stance_fills_pattern() -> None:
    s = h11.final_stance(1980, 0.7, True)
    assert s.startswith("日本の出生率低下（1980→2020）の 7 割は結婚の減少")
    assert "夫婦の出生数の低下は 3 割" in s
    assert "北欧では切り離されている" in s
    s2 = h11.final_stance(1980, 1.13, False)
    assert "11 割" in s2 and "-1 割" in s2
    assert "確かめられなかった" in s2 and "北欧では切り離されている" not in s2


def test_framed_stance_adds_qualifications() -> None:
    main = h11.J1Decomp(1980, 2020, 1.75, 1.33, 0.655, 0.482)
    seg = [h11.J1Decomp(1980, 2000, 1.75, 1.36, 0.655, 0.515)]
    s = h11.framed_stance(
        main=main,
        code="main_unconfirmed",
        segments=seg,
        std_s_m=2.0,
        completed=(1982, 2.21, 2021, 1.81),
        j2_main=(0.005, 0.02, -0.04, 0.05),
        j3_ok=False,
        robust_changes=[],
    )
    assert s.startswith("期間の分解では 1980→2020 年の低下のほぼ全部")
    assert "11 割" not in s
    assert "J1 のみ成立、J2 不成立" in s and "主経路」の帯" in s
    assert "1 を超える" in s
    assert "2.21" in s and "1.81" in s
    assert "判定は変わらない" in s
    assert "因果ではなく" in s


def test_framed_stance_reports_j3_high_group_against_prediction() -> None:
    main = h11.J1Decomp(1980, 2020, 1.75, 1.33, 0.655, 0.482)

    def framed(high: tuple[float, float, float, float]) -> str:
        return h11.framed_stance(
            main=main,
            code="main",
            segments=[],
            std_s_m=2.0,
            completed=None,
            j2_main=None,
            j3_ok=False,
            robust_changes=["x"],
            j3_low=(0.05, 0.02, -0.01, 0.1),
            j3_high=high,
        )

    assert "予測と逆" in framed((0.1, 0.03, 0.05, 0.16))
    s2 = framed((0.0, 0.03, -0.05, 0.05))
    assert "（CI∋0）" in s2 and "予測と逆" not in s2
    assert "判定が変わるものがある（x）" in s2


# ---------------------------------------------------------------- J3 helpers
def test_bom_group_boundaries() -> None:
    assert h11.bom_group(24.9) == "low"
    assert h11.bom_group(25.0) == "mid"
    assert h11.bom_group(40.0) == "high"
    assert h11.bom_group(24.0, low=20.0) == "mid"


def test_j3_consistent_needs_low_positive_and_high_null() -> None:
    pos = (0.1, 0.02, 0.05, 0.15)
    null = (0.05, 0.05, -0.05, 0.15)
    assert h11.j3_consistent(pos, null)
    assert not h11.j3_consistent(null, null)
    assert not h11.j3_consistent(pos, pos)
    assert not h11.j3_consistent(None, null)


def test_first_diff_consecutive_within_unit() -> None:
    df = pl.DataFrame(
        {
            "unit": ["a", "a", "a", "b", "b"],
            "year": [2010, 1990, 2015, 1990, 2010],
            "x": [3.0, 1.0, 6.0, 10.0, None],
        }
    )
    out = h11.first_diff(df, "unit", "year", ["x"]).sort("unit", "year")
    assert out.select("unit", "year", "t0").rows() == [
        ("a", 2010, 1990),
        ("a", 2015, 2010),
        ("b", 2010, 1990),
    ]
    assert out["d_x"].to_list() == [2.0, 3.0, None]


def test_final_stance_records_reversed_j3() -> None:
    s = h11.final_stance(1980, 1.13, False, True)
    assert "逆の結果" in s and "確かめられなかった" not in s


def test_wari_approx() -> None:
    assert h11.wari_approx(0.42) == "4 割強"
    assert h11.wari_approx(0.47) == "5 割弱"
    assert h11.wari_approx(0.40) == "4 割"
