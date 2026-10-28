import pytest

from theme_parliament_size.analysis.a20261028_r7_roles_gdp import budget_to_gdp, per_member

GDP = {("JPN", 2025): 6.6e14, ("JPN", 2024): 6.3e14, ("XXX", 2025): 1.0e12}


def _ch(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "iso3": "JPN",
        "chamber_budget": 6.8e10,
        "budget_currency": "JPY",
        "budget_year": 2025,
        "budget_combined_parl": False,
    }
    base.update(over)
    return base


def test_budget_to_gdp_sums_both_chambers_in_the_budget_year() -> None:
    out = budget_to_gdp([_ch(), _ch(chamber_budget=4.2e10)], GDP, "JPY")
    assert out is not None
    assert out[0] == pytest.approx(100 * (6.8e10 + 4.2e10) / 6.6e14)
    assert out[1:] == (2025, "両院合計")


def test_budget_to_gdp_notes_year_mismatch_and_single_chamber_cases() -> None:
    out = budget_to_gdp([_ch(), _ch(chamber_budget=4.2e10, budget_year=2024)], GDP, "JPY")
    assert out is not None
    assert out[0] == pytest.approx(100 * 6.8e10 / 6.6e14 + 100 * 4.2e10 / 6.3e14)
    assert out[1:] == (2025, "両院合計（予算年 2024／2025）")
    one = budget_to_gdp([_ch()], GDP, "JPY")
    assert one is not None and one[2] == "一院"
    combined = budget_to_gdp([_ch(budget_combined_parl=True), _ch(chamber_budget=None)], GDP, "JPY")
    assert combined is not None and combined[2] == "両院合計（1 議院の申告）"


def test_budget_to_gdp_is_none_when_incomplete_or_currency_mismatch() -> None:
    assert budget_to_gdp([_ch(chamber_budget=None)], GDP, "JPY") is None
    assert budget_to_gdp([_ch(budget_currency="USD")], GDP, "JPY") is None
    assert (
        budget_to_gdp([_ch(), _ch(chamber_budget=None)], GDP, "JPY") is None
    )  # 片方欠損、合計申告なし
    assert budget_to_gdp([_ch(budget_year=2010)], GDP, "JPY") is None  # その年の GDP が無い


def test_per_member() -> None:
    assert per_member(930.0, 465.0) == 2.0
    assert per_member(None, 465.0) is None and per_member(1.0, 0.0) is None
