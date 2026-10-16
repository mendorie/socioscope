"""H8: 仕組みの分解・判定（a20261017_h8_mechanisms）の純粋ヘルパのテスト。"""

import math
from typing import Any

import polars as pl
import pytest

from theme_growth_fertility.analysis import a20261017_h8_mechanisms as h8


# ---------------------------------------------------------------- Cm / ASFR
def test_tfr_from_asfr_is_five_times_sum_per_thousand() -> None:
    assert h8.tfr_from_asfr([100, 200, 200, 150, 100, 40, 10]) == pytest.approx(4.0)


def test_cm_is_asfr_weighted_mean_of_union_share() -> None:
    m = [10.0, 50.0, 80.0, 90.0, 90.0, 85.0, 80.0]
    f = [100.0, 200.0, 200.0, 150.0, 100.0, 40.0, 10.0]
    expected = sum(a / 100 * b for a, b in zip(m, f, strict=True)) / sum(f)
    assert h8.bongaarts_cm(m, f) == pytest.approx(expected)


def test_cm_is_one_when_everyone_is_in_union() -> None:
    assert h8.bongaarts_cm([100.0] * 7, [50.0, 60, 70, 60, 50, 20, 5]) == pytest.approx(1.0)


def test_cm_requires_all_seven_groups() -> None:
    assert h8.bongaarts_cm([10.0, 50, 80, 90, 90, 85, None], [1.0] * 7) is None
    assert h8.bongaarts_cm([10.0] * 7, [1.0, 1, 1, 1, 1, 1, None]) is None
    assert h8.bongaarts_cm([10.0] * 6, [1.0] * 6) is None
    assert h8.bongaarts_cm([10.0] * 7, [0.0] * 7) is None


def test_survey_table_computes_cm_and_logs() -> None:
    rows: list[dict[str, Any]] = []

    def add(metric: str, cat: str, label: str, value: float, by: str = "") -> None:
        rows.append(
            {
                "iso3": "AAA",
                "country": "A",
                "survey_id": "AA2000DHS",
                "survey_year": 2000,
                "survey_type": "DHS",
                "metric": metric,
                "characteristic_category": cat,
                "characteristic_label": label,
                "by_variable": by,
                "value": value,
            }
        )

    add("tfr", "Total", "Total", 4.0)
    add("ideal_children", "Total", "Total", 5.0)
    add("women_secondary_plus", "Total 15-49", "Total", 30.0)
    add("u5mr", "Total", "Total", 100.0, "Five years preceding the survey")
    add("u5mr", "Total", "Total", 120.0, "Ten years preceding the survey")
    for a, f in zip(h8.AGES, [100, 200, 200, 150, 100, 40, 10], strict=True):
        add(f"asfr_{a}", "Total", "Total", float(f))
        add("in_union", "Age (5-year groups)", f"{a}-{a + 4}", 50.0)
    panel = pl.DataFrame({"iso3": ["AAA"], "region": ["R"]})
    st = h8.survey_table(pl.DataFrame(rows), panel)
    r = st.row(0, named=True)
    assert r["cm"] == pytest.approx(0.5)
    assert r["ln_u5"] == pytest.approx(math.log(100))
    assert r["ln_u5_10"] == pytest.approx(math.log(120))
    assert r["tfr_minus_ideal"] == pytest.approx(-1.0)
    assert r["sec"] == 30.0


# ---------------------------------------------------------------- decomposition shares
def test_ratio_of_sums_pooled_share() -> None:
    assert h8.ratio_of_sums([-1.0, -0.5], [-2.0, -1.0]) == pytest.approx(0.5)


def test_ratio_of_sums_with_weights() -> None:
    # country-equal weights: second pair weighted 2x
    assert h8.ratio_of_sums([-1.0, -1.0], [-2.0, -1.0], [1.0, 2.0]) == pytest.approx(3.0 / 4.0)


def test_ratio_of_sums_zero_denominator_raises() -> None:
    with pytest.raises(ValueError):
        h8.ratio_of_sums([1.0], [0.0])


def test_log_decomposition_identity() -> None:
    tfr0, tfr1, cm0, cm1 = 6.0, 3.0, 0.8, 0.6
    d_ln_tfr = math.log(tfr1) - math.log(tfr0)
    d_ln_cm = math.log(cm1) - math.log(cm0)
    d_rest = math.log(tfr1 / cm1) - math.log(tfr0 / cm0)
    assert d_ln_cm + d_rest == pytest.approx(d_ln_tfr)
    assert h8.ratio_of_sums([d_ln_cm], [d_ln_tfr]) == pytest.approx(math.log(0.75) / math.log(0.5))


# ---------------------------------------------------------------- pairs
def test_chain_pairs_skips_short_gaps_and_does_not_overlap() -> None:
    assert h8.chain_pairs([1990, 1992, 1995, 1999, 2000], 3) == [(0, 2), (2, 3)]


def test_chain_pairs_empty_when_no_gap_is_long_enough() -> None:
    assert h8.chain_pairs([2000, 2001], 3) == []


def _st() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "iso3": ["A", "A", "A", "B", "B"],
            "survey_id": ["a1", "a2", "a3", "b1", "b2"],
            "survey_year": [1990, 1995, 2005, 2000, 2002],
            "region": ["R"] * 5,
            "tfr": [6.0, 5.0, 4.0, 3.0, 2.0],
            "wanted_tfr": [5.0, 4.5, 3.0, 2.5, None],
        }
    )


def test_pair_frame_chain_and_first_last() -> None:
    ch = h8.pair_frame(_st(), ("tfr", "wanted_tfr"), min_gap=3, mode="chain")
    assert ch["d_tfr"].to_list() == [-1.0, -1.0]
    assert ch["d_wanted_tfr"].to_list() == [-0.5, -1.5]
    fl = h8.pair_frame(_st(), ("tfr", "wanted_tfr"), min_gap=8, mode="first_last")
    assert fl.height == 1  # B has only one survey with both
    assert fl.row(0, named=True)["d_tfr"] == -2.0


# ---------------------------------------------------------------- SMAM cleaning
def test_trim_smam_drops_outliers_only_with_three_or_more_obs() -> None:
    rows = pl.DataFrame(
        {
            "iso3": ["F"] * 4 + ["G"] * 2,
            "year": [2000, 2005, 2008, 2012, 2000, 2010],
            "smam_fe": [31.0, 31.0, 22.7, 32.0, 20.0, 30.0],
        }
    )
    out, n = h8.trim_smam(rows)
    assert n == 1
    f = out.filter(pl.col("iso3") == "F").sort("year")["smam_fe"].to_list()
    assert f == [31.0, 31.0, None, 32.0]
    assert out.filter(pl.col("iso3") == "G")["smam_fe"].to_list() == [20.0, 30.0]


def test_trim_smam_threshold_is_inclusive_at_four_years() -> None:
    rows = pl.DataFrame({"iso3": ["H"] * 3, "year": [1, 2, 3], "smam_fe": [20.0, 24.0, 24.0]})
    _, n = h8.trim_smam(rows)
    assert n == 1  # 20 is exactly 4 years from the median 24


# ---------------------------------------------------------------- long differences
def test_nearest_value_prefers_exact_then_earlier() -> None:
    obs = {1979: 1.0, 1981: 2.0}
    assert h8.nearest_value(obs, 1980, 2) == 1.0
    assert h8.nearest_value({1980: 5.0, 1979: 1.0}, 1980, 2) == 5.0
    assert h8.nearest_value(obs, 1990, 2) is None


def test_long_diff_nearest() -> None:
    panel = pl.DataFrame(
        {
            "iso3": ["A"] * 4,
            "year": [1970, 1971, 1980, 1992],
            "tfr": [6.0, None, 5.0, None],
            "smam": [None, 18.0, None, 20.0],
        }
    )
    ld = h8.long_diff_nearest(panel, ("tfr", "smam"), width=10, start=1970, end=1990)
    assert ld.height == 2
    r = ld.filter(pl.col("period") == 1970).row(0, named=True)
    assert r["d_tfr"] == pytest.approx(-1.0)
    assert r["d_smam"] is None  # no SMAM within ±2 of 1980
    r2 = ld.filter(pl.col("period") == 1980).row(0, named=True)
    assert r2["tfr_0"] == 5.0
    assert r2["d_tfr"] is None


# ---------------------------------------------------------------- verdicts
@pytest.mark.parametrize(
    ("s_w", "expected"), [(0.6, "wanted"), (0.75, "wanted"), (0.5, "mixed"), (0.4, "m5")]
)
def test_verdict_t1(s_w: float, expected: str) -> None:
    assert h8.verdict_t1(s_w) == expected


def test_verdict_m1() -> None:
    assert h8.verdict_m1(0.30, 0.05, 0.6) == "support"
    assert h8.verdict_m1(0.20, 0.05, 0.4) == "partial"
    assert h8.verdict_m1(0.30, -0.1, 0.6) == "no"
    assert h8.verdict_m1(0.05, 0.01, 0.1) == "no"


def test_verdict_m2() -> None:
    assert h8.verdict_m2(0.8, 0.3) == "support"
    assert h8.verdict_m2(0.6, 0.3) == "partial"
    assert h8.verdict_m2(0.8, 0.15) == "partial"
    assert h8.verdict_m2(0.8, 0.05) == "no"
    assert h8.verdict_m2(0.4, 0.5) == "no"


def test_verdict_m3() -> None:
    assert h8.verdict_m3(-1.5, -1.2, -0.5) == ("support", False)
    assert h8.verdict_m3(-1.5, -1.2, -0.9) == ("partial", False)  # |g_w| < 2|g_u|
    assert h8.verdict_m3(-0.7, -0.2, -0.3) == ("partial", False)
    assert h8.verdict_m3(-0.4, -0.1, -0.1) == ("no", False)
    assert h8.verdict_m3(-0.5, -0.1, -0.6) == ("no", True)


def test_widening_sign_and_size() -> None:
    assert h8.widening(1.0) == pytest.approx(math.log(5))
    assert h8.widening(-0.5) < 0


def test_verdict_m4() -> None:
    assert h8.verdict_m4(0.3, 0.1, 0.5) == "support"  # widening 0.48
    assert h8.verdict_m4(0.3, -0.1, 0.7) == "partial"  # CI includes 0
    assert h8.verdict_m4(0.1, 0.05, 0.15) == "partial"  # widening 0.16
    assert h8.verdict_m4(-1.0, -1.3, -0.8) == "no"


def test_verdict_m5() -> None:
    assert h8.verdict_m5("m5", True) == "support"
    assert h8.verdict_m5("m5", False) == "partial"
    assert h8.verdict_m5("wanted", True) == "partial"
    assert h8.verdict_m5("mixed", False) == "partial"
    assert h8.verdict_m5("wanted", False) == "no"


def test_score_mechanisms() -> None:
    sc = h8.score_mechanisms(
        s_w=0.75,
        t2c=(0.2, -0.2, 0.6),
        share_ge2=0.81,
        s_m=0.33,
        g_w=(-1.5, -1.26),
        g_u=-0.52,
        gamma=(-1.07, -1.29, -0.85),
    )
    assert sc == {"M1": "no", "M2": "support", "M3": "support", "M4": "no", "M5": "no"}


# ---------------------------------------------------------------- stage 2 / final sentence
def test_stage2_leader_picks_largest_significant() -> None:
    coefs = {
        "d_ln_u5": (-0.30, 0.2, -0.7, 0.1),  # largest but CI includes 0
        "d_sec": (-0.12, 0.04, -0.2, -0.03),
        "d_smam": (-0.04, 0.08, -0.2, 0.1),
        "d_ln_gdp": (0.14, 0.1, -0.1, 0.4),
    }
    leader, share = h8.stage2_leader(coefs)
    assert leader == "d_sec"
    assert share == pytest.approx(0.12 / 0.60)


def test_stage2_leader_none_when_all_cis_include_zero() -> None:
    coefs = {"d_sec": (-0.1, 0.1, -0.3, 0.1), "d_smam": (0.1, math.nan, math.nan, math.nan)}
    assert h8.stage2_leader(coefs) == (None, 0.0)


def test_stage1_actors() -> None:
    assert h8.stage1_actors({"M1": "no", "M3": "support"}, -0.5, -0.1) == ("M3", None)
    assert h8.stage1_actors({"M1": "support", "M3": "support"}, -0.5, -0.1) == ("M1", "M3")
    assert h8.stage1_actors({"M1": "partial", "M3": "support"}, -0.5, -0.1) == ("M3", "M1")


def test_final_hypothesis_wanted_branch() -> None:
    s = h8.final_hypothesis(
        s_w=0.75,
        m1_contrib=-0.16,
        m3_contrib=-0.36,
        s_m=0.33,
        leader2="d_smam",
        share2=0.45,
        u5_sig2=False,
        verdicts={"M1": "support", "M3": "support"},
    )
    assert s.startswith(
        "出生率が 6 人から 3 人前後へ下がる段階は、女子教育による『望む数』の低下（M3）が主に担い"
    )
    assert "（25%）にとどまる" in s
    assert "結婚が遅れること（M2" in s
    assert "（45%）を担い" in s
    assert "死亡率はもう効いていない" in s
    assert "約 3 割（33%）" in s


def test_final_hypothesis_m1_not_supported_is_named_as_not_associated() -> None:
    s = h8.final_hypothesis(
        s_w=0.75,
        m1_contrib=-0.5,
        m3_contrib=-0.36,
        s_m=0.33,
        leader2="d_sec",
        share2=0.32,
        u5_sig2=False,
        verdicts={"M1": "no", "M3": "support"},
    )
    assert "（M3）が担い" in s
    assert "TFR との関連が確かめられず" in s


def test_final_hypothesis_m5_and_unexplained_branch() -> None:
    s = h8.final_hypothesis(
        s_w=0.3,
        m1_contrib=0.0,
        m3_contrib=0.0,
        s_m=0.05,
        leader2=None,
        share2=0.0,
        u5_sig2=False,
        verdicts={},
    )
    assert "望まない出生の減少（M5、家族計画）が約 7 割（70%）を担い" in s
    assert "どれでも説明できない" in s
