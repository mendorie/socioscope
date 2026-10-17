"""H8c: 教育投資・学歴社会の圧力（a20261018_h8c_education_cost）の純粋ヘルパのテスト。"""

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h8c_education_cost as h8c

SIG_NEG = (-0.5, 0.1, -0.7, -0.3)
SIG_POS = (0.4, 0.1, 0.2, 0.6)
NS_NEG = (-0.9, 0.6, -2.1, 0.3)
NS_POS = (0.2, 0.2, -0.2, 0.6)
SMALL_NEG = (-0.1, 0.02, -0.14, -0.06)
INCOME = (0.3, 0.1, 0.1, 0.5)


# ---------------------------------------------------------------- OECD long -> wide
def _long() -> pl.DataFrame:
    cols = [
        "iso3", "year", "dataset", "education_level", "exp_source", "unit", "sex", "work_time",
        "price_base", "value",
    ]  # fmt: skip
    rows = [
        ("JPN", 2020, "fin_source", "ISCED11_1T8", "S1D_NON_EDU", "PT_EXP", "_Z", "_Z", "_Z", 30.0),
        ("JPN", 2020, "fin_source", "ISCED11_1T8", "S13", "PT_EXP", "_Z", "_Z", "_Z", 68.0),
        ("JPN", 2020, "fin_source", "ISCED11_1T8", "S1D_NON_EDU", "PT_B1GQ", "_Z", "_Z", "_Z", 1.2),
        ("SWE", 2020, "fin_source", "ISCED11_1T8", "S1D_NON_EDU", "PT_EXP", "_Z", "_Z", "_Z", 3.0),
        ("SWE", 2021, "fin_source", "ISCED11_1T8", "S1D_NON_EDU", "PT_EXP", "_Z", "_Z", "_Z", 3.5),
        ("SWE", 2020, "earn_rel", "ISCED11A_5T8", "_Z", "PT_E", "_T", "_T", "_Z", 120.0),
        ("SWE", 2020, "earn_rel", "ISCED11A_5T8", "_Z", "PT_E", "F", "_T", "_Z", 125.0),
    ]
    return pl.DataFrame(rows, schema=cols, orient="row")


def test_extract_filters_to_one_series() -> None:
    out = h8c.extract(_long(), "priv", h8c.OECD_SPEC["priv"])
    assert out.columns == ["iso3", "year", "priv"]
    assert out.rows() == [("JPN", 2020, 30.0), ("SWE", 2020, 3.0), ("SWE", 2021, 3.5)]


def test_extract_rejects_duplicate_country_year() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        h8c.extract(_long(), "x", {"dataset": "earn_rel"})


def test_extract_rejects_unknown_filter_column() -> None:
    with pytest.raises(ValueError, match="column"):
        h8c.extract(_long(), "x", {"nope": "a"})


def test_oecd_wide_outer_joins_series() -> None:
    spec = {"priv": h8c.OECD_SPEC["priv"], "rel": h8c.OECD_SPEC["rel"]}
    w = h8c.oecd_wide(_long(), spec)
    assert w.columns == ["iso3", "year", "priv", "rel"]
    assert w.rows() == [
        ("JPN", 2020, 30.0, None),
        ("SWE", 2020, 3.0, 120.0),
        ("SWE", 2021, 3.5, None),
    ]


def test_variant_spec_replaces_only_named_fields() -> None:
    s = h8c.variant_spec({"rel": {"sex": "F"}})
    assert s["rel"]["sex"] == "F"
    assert s["rel"]["education_level"] == "ISCED11A_5T8"
    assert s["priv"] == h8c.OECD_SPEC["priv"]
    assert h8c.OECD_SPEC["rel"]["sex"] == "_T"  # base not mutated


# ---------------------------------------------------------------- latest common year
def test_latest_common_year_picks_last_complete_row_per_country() -> None:
    f = pl.DataFrame(
        {
            "iso3": ["A", "A", "A", "B", "B", "C"],
            "year": [2012, 2018, 2020, 2015, 2019, 2010],
            "x": [1.0, 2.0, 3.0, 4.0, None, 5.0],
            "y": [1.0, 2.0, None, 4.0, 5.0, 5.0],
        }
    )
    out = h8c.latest_common_year(f, ["x", "y"], min_year=2012)
    assert out.select("iso3", "year").rows() == [("A", 2018), ("B", 2015)]


def test_endpoints_pairs_start_near_target_and_latest() -> None:
    f = pl.DataFrame(
        {
            "iso3": ["A", "A", "A", "B", "B", "C", "C"],
            "year": [2011, 2013, 2021, 2012, 2015, 2012, 2019],
            "x": [1.0, 2.0, 4.0, 1.0, 2.0, 1.0, 3.0],
        }
    )
    out = h8c.endpoints(f, ["x"], start=2012, window=2, min_gap=5)
    # A: 2011 and 2013 equally near -> earlier (2011); B: gap 3 < 5 -> dropped
    assert out.select("iso3", "y0", "y1", "d_x").rows() == [
        ("A", 2011, 2021, 3.0),
        ("C", 2012, 2019, 2.0),
    ]


# ---------------------------------------------------------------- judgement rules
def test_global_side_needs_negative_significant_and_largest() -> None:
    co = {"d_tert": SIG_NEG, "d_sle": NS_POS, "d_ln_gdp": INCOME}
    assert h8c.global_side(co) == ("d_tert", True)
    co2 = {"d_tert": SMALL_NEG, "d_sle": NS_POS, "d_ln_gdp": INCOME}
    assert h8c.global_side(co2) == ("d_tert", False)  # significant but smaller than income
    co3 = {"d_tert": NS_NEG, "d_sle": NS_POS, "d_sec": SIG_NEG}
    assert h8c.global_side(co3) == (None, False)


def test_global_side_largest_compares_against_non_significant_too() -> None:
    co = {"d_sle": SIG_NEG, "d_eexp": NS_NEG}  # |-0.9| > |-0.5| although its CI includes 0
    assert h8c.global_side(co) == ("d_sle", False)


def test_oecd_side_either_test_and_sign_conflict() -> None:
    y2 = {"priv": SIG_NEG, "rel": NS_POS}
    assert h8c.oecd_side(y2, {"priv": NS_NEG, "rel": NS_POS}) == (True, ("priv",), ())
    # significant in Y3 only, Y2 same sign -> holds
    assert h8c.oecd_side({"priv": NS_NEG, "rel": NS_NEG}, {"priv": NS_POS, "rel": SIG_NEG})[0]
    # significant negative in Y2 but Y3 point estimate positive -> sign conflict, fails
    out = h8c.oecd_side(y2, {"priv": NS_POS, "rel": NS_POS})
    assert out == (False, (), ("priv",))


def test_oecd_side_missing_test_does_not_conflict() -> None:
    assert h8c.oecd_side({"priv": SIG_NEG}, None) == (True, ("priv",), ())


def test_reverse_flags_lists_positive_significant_targets() -> None:
    co = {"priv": SIG_POS, "rel": SIG_NEG, "ln_gdp": SIG_POS}
    assert h8c.reverse_flags(co, ("priv", "rel")) == ["priv"]


def test_verdict_q_combines_two_sides() -> None:
    assert h8c.verdict_q(True, True) == "support"
    assert h8c.verdict_q(True, False) == "partial_global"
    assert h8c.verdict_q(False, True) == "partial_oecd"
    assert h8c.verdict_q(False, False) == "no"


def test_final_stance_uses_preregistered_sentence_forms() -> None:
    s = h8c.final_stance("support", global_var=None, oecd_vars=(), reverse=[])
    assert "その費用を家計が負う社会ほど進んでいる（学歴社会の副作用）" in s
    n = h8c.final_stance("no", global_var=None, oecd_vars=(), reverse=[])
    assert "学歴社会の圧力でも説明できない" in n
    assert "本シリーズの変数では特定できない" in n
    p = h8c.final_stance("partial_oecd", global_var=None, oecd_vars=("priv",), reverse=[])
    assert "私的負担" in p and "全世界" in p
    g = h8c.final_stance("partial_global", global_var="d_tert", oecd_vars=(), reverse=[])
    assert "高等教育進学率" in g
    r = h8c.final_stance("no", global_var=None, oecd_vars=(), reverse=["d_tert"])
    assert "逆向き" in r and "高等教育進学率" in r


def test_final_stance_rejects_unknown_verdict() -> None:
    with pytest.raises(ValueError):
        h8c.final_stance("maybe", global_var=None, oecd_vars=(), reverse=[])


# ---------------------------------------------------------------- nearest attach
def test_attach_nearest_uses_window_and_earlier_tie() -> None:
    frame = pl.DataFrame({"iso3": ["A", "A", "B"], "survey_year": [2000, 2010, 2000]})
    panel = pl.DataFrame(
        {"iso3": ["A", "A", "A", "B"], "year": [1999, 2001, 2013, 1990], "v": [1.0, 2.0, 3.0, 9.0]}
    )
    out = h8c.attach_nearest(frame, panel, ["v"], window=2)
    assert out["v"].to_list() == [1.0, None, None]
