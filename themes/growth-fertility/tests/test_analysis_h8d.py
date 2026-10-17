"""H8d: 家庭内の男女分業（a20261018_h8d_gender_equity）の純粋ヘルパのテスト。"""

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261018_h8d_gender_equity as h8d

SIG_NEG = (-0.5, 0.1, -0.7, -0.3)
SIG_POS = (0.4, 0.1, 0.2, 0.6)
NS_NEG = (-0.2, 0.2, -0.6, 0.2)
NS_POS = (0.2, 0.2, -0.2, 0.6)
COLS = ["iso3", "year", "series", "sex", "age", "location", "value"]


def _long(rows: list[tuple[str, int, str, str, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        [(i, y, "SL_DOM_TSPD", s, a, "ALLAREA", v) for i, y, s, a, v in rows],
        schema=COLS,
        orient="row",
    )


# ---------------------------------------------------------------- shares and age bands
def test_female_share_is_ratio_of_female_to_total() -> None:
    assert h8d.female_share(15.0, 5.0) == pytest.approx(0.75)
    assert h8d.female_share(0.0, 0.0) is None


def test_band_bounds_parses_open_closed_and_all() -> None:
    assert h8d.band_bounds("15+") == (15, None)
    assert h8d.band_bounds("20-74") == (20, 74)
    assert h8d.band_bounds("ALLAGE") == (0, None)
    with pytest.raises(ValueError):
        h8d.band_bounds("teen")


def test_nearest_band_prefers_lower_bound_near_15_then_wider() -> None:
    assert h8d.nearest_band(["20-74", "25-44"]) == "20-74"
    assert h8d.nearest_band(["12+", "20-74"]) == "12+"
    assert h8d.nearest_band(["15-64", "15-49"]) == "15-64"
    assert h8d.nearest_band(["15-64", "15+"]) == "15+"


def test_unpaid_wide_keeps_rows_with_both_sexes_in_allarea() -> None:
    g = _long(
        [
            ("AAA", 2010, "F", "15+", 15.0),
            ("AAA", 2010, "M", "15+", 5.0),
            ("AAA", 2010, "F", "10+", 14.0),  # no male value -> dropped
        ]
    ).vstack(
        pl.DataFrame(
            [
                ("AAA", 2010, "SL_DOM_TSPD", "M", "10+", "URBAN", 9.0),
                ("AAA", 2010, "IC_GEN_MGTL", "M", "10+", "ALLAREA", 9.0),
            ],
            schema=COLS,
            orient="row",
        )
    )
    w = h8d.unpaid_wide(g)
    assert w.rows() == [("AAA", 2010, "15+", 15.0, 5.0)]


def test_select_band_follows_priority_and_records_age() -> None:
    g = _long(
        [
            ("AAA", 2010, "F", "10+", 14.0),
            ("AAA", 2010, "M", "10+", 6.0),
            ("AAA", 2010, "F", "15+", 15.0),
            ("AAA", 2010, "M", "15+", 5.0),
            ("BBB", 2012, "F", "20+", 12.0),
            ("BBB", 2012, "M", "20+", 12.0),
            ("BBB", 2012, "F", "ALLAGE", 10.0),
            ("BBB", 2012, "M", "ALLAGE", 10.0),
            ("ESP", 2010, "F", "20-74", 19.0),
            ("ESP", 2010, "M", "20-74", 9.0),
        ]
    )
    w = h8d.unpaid_wide(g)
    s = h8d.select_band(w)
    assert s.select("iso3", "year", "age").rows() == [("AAA", 2010, "15+"), ("BBB", 2012, "20+")]
    assert s["female_share"].to_list() == [pytest.approx(0.75), pytest.approx(0.5)]
    fb = h8d.select_band(w, fallback=True)
    assert fb.select("iso3", "age").rows() == [("AAA", "15+"), ("BBB", "20+"), ("ESP", "20-74")]
    only10 = h8d.select_band(w, priority=("10+",))
    assert only10.select("iso3", "age").rows() == [("AAA", "10+")]


def test_latest_per_country_from_min_year() -> None:
    f = pl.DataFrame({"iso3": ["A", "A", "B"], "year": [2005, 2015, 1998], "v": [1.0, 2.0, 3.0]})
    assert h8d.latest_per_country(f, min_year=2000).rows() == [("A", 2015, 2.0)]


def test_within_pairs_uses_one_band_first_and_last_years() -> None:
    g = _long(
        [
            ("AAA", 2001, "F", "15+", 15.0),
            ("AAA", 2001, "M", "15+", 5.0),
            ("AAA", 2004, "F", "15+", 14.0),
            ("AAA", 2004, "M", "15+", 6.0),
            ("AAA", 2011, "F", "15+", 12.0),
            ("AAA", 2011, "M", "15+", 8.0),
            ("BBB", 2001, "F", "15+", 15.0),  # 15+ only once, 10+ twice -> 10+ pair
            ("BBB", 2001, "M", "15+", 5.0),
            ("BBB", 2001, "F", "10+", 15.0),
            ("BBB", 2001, "M", "10+", 5.0),
            ("BBB", 2009, "F", "10+", 10.0),
            ("BBB", 2009, "M", "10+", 10.0),
            ("CCC", 2001, "F", "15+", 15.0),  # gap 3 < 5 -> dropped
            ("CCC", 2001, "M", "15+", 5.0),
            ("CCC", 2004, "F", "15+", 15.0),
            ("CCC", 2004, "M", "15+", 5.0),
        ]
    )
    p = h8d.within_pairs(h8d.unpaid_wide(g), min_gap=5)
    assert p.select("iso3", "age", "y0", "y1").rows() == [
        ("AAA", "15+", 2001, 2011),
        ("BBB", "10+", 2001, 2009),
    ]
    assert p["d_share"].to_list() == [pytest.approx(-0.15), pytest.approx(-0.25)]


# ---------------------------------------------------------------- verdict
def test_alt_hits_respect_predicted_signs() -> None:
    alt = {"mgr": SIG_POS, "parl": NS_POS, "lfp_ratio": SIG_NEG, "gii": SIG_NEG}
    assert h8d.alt_hits(alt) == ["mgr", "gii"]


def test_verdict_support_via_z1() -> None:
    assert h8d.verdict_g(SIG_NEG, NS_NEG, NS_NEG, {}) == "support"


def test_verdict_support_via_z2_needs_upper_half_slope() -> None:
    assert h8d.verdict_g(NS_POS, SIG_NEG, SIG_NEG, {}) == "support"
    assert h8d.verdict_g(NS_POS, SIG_NEG, NS_NEG, {}) == "no"
    assert h8d.verdict_g(NS_POS, SIG_NEG, None, {}) == "no"


def test_verdict_partial_needs_negative_point_and_two_alt_hits() -> None:
    two = {"mgr": SIG_POS, "parl": SIG_POS, "lfp_ratio": NS_POS, "gii": NS_NEG}
    one = {"mgr": SIG_POS, "parl": NS_POS, "lfp_ratio": NS_POS, "gii": NS_NEG}
    assert h8d.verdict_g(NS_NEG, NS_NEG, NS_NEG, two) == "partial"
    assert h8d.verdict_g(NS_NEG, NS_NEG, NS_NEG, one) == "no"
    assert h8d.verdict_g(NS_POS, NS_NEG, NS_NEG, two) == "no"


def test_reverse_flags_positive_significant_z1_or_z2() -> None:
    assert h8d.reverse_g(SIG_POS, NS_NEG, NS_NEG) == ["z1"]
    assert h8d.reverse_g(NS_NEG, SIG_POS, SIG_POS) == ["z2_interaction", "z2_upper"]
    assert h8d.reverse_g(SIG_NEG, NS_POS, None) == []


def test_final_stance_forms() -> None:
    s = h8d.final_stance_g("support", hits=[], reverse=[])
    assert s.startswith("2 人未満への低下の深さは、女性の就業が進んだのに")
    p = h8d.final_stance_g("partial", hits=["mgr", "gii"], reverse=[])
    assert "女性管理職割合" in p and "ジェンダー不平等指数" in p and "部分的支持" in p
    n = h8d.final_stance_g("no", hits=[], reverse=["z1"])
    assert "家庭内の男女分業でも深さは説明できない" in n and "規範の拡散" in n and "逆向き" in n
    with pytest.raises(ValueError):
        h8d.final_stance_g("maybe", hits=[], reverse=[])


def test_z4_note_flags_disagreement() -> None:
    assert h8d.z4_note("support", NS_NEG) == "国の中の変化では確かめられない"
    assert h8d.z4_note("support", SIG_NEG) == ""
    assert h8d.z4_note("no", SIG_NEG) == "国の中の変化では負の関連が見られる（主判定と食い違う）"
    assert h8d.z4_note("no", NS_NEG) == ""
    assert h8d.z4_note("support", None) == "国の中の変化では確かめられない"


def test_framed_stance_quotes_template_and_qualifies() -> None:
    s = h8d.framed_stance(
        "no",
        hits=[],
        reverse=[],
        n=53,
        cut=2.5,
        flips=[("TFR < 2.1", "support"), ("10+ band only", "partial")],
        depends_on=["KOR"],
    )
    assert s.startswith("事前の規則では不支持である。TFR < 2.5 の広い標本（53 か国）")
    assert "事前の文型では「家庭内の男女分業でも深さは説明できない。" in s
    assert "TFR < 2.1では支持、10+ 年齢層のみでは部分的支持になり、判定は仕様に左右される" in s
    assert "OECD の支持は韓国 1 か国に依存する" in s
    assert "規範の拡散そのものは測っていない" in s


def test_framed_stance_without_flips_has_no_qualifier() -> None:
    s = h8d.framed_stance("support", hits=[], reverse=[], n=40, cut=2.5, flips=[])
    assert s.startswith("事前の規則では支持である。事前の文型では「2 人未満への低下の深さは")
    assert "左右される" not in s and "規範の拡散" not in s
