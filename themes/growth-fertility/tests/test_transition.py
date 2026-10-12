"""H7: 人口転換開始年（transition.py）の純粋関数テスト。"""

from pathlib import Path
from statistics import median

import pytest

from theme_growth_fertility.transition import onset_table, transition_onset

MART = Path(__file__).resolve().parents[3] / "data" / "marts" / "growth_fertility_panel.parquet"


def _series(start: int, values: list[float | None]) -> dict[int, float | None]:
    return {start + i: v for i, v in enumerate(values)}


def test_monotone_decline_finds_first_year_below_threshold() -> None:
    # peak 6.0 in 1960-1975 -> threshold 5.4; first year <= 5.4 is 1972
    values = [6.0, 6.0, 5.9, 5.9, 5.8, 5.8, 5.7, 5.7, 5.6, 5.6, 5.5, 5.5, 5.4, 5.2, 5.0, 4.8]
    assert transition_onset(_series(1960, values)) == 1972


def test_temporary_rebound_moves_onset_to_later_year() -> None:
    # peak 6.0 -> threshold 5.4. Below in 1965, rebounds to 5.6 in 1968, then never returns
    s = _series(1960, [6.0, 5.9, 5.8, 5.6, 5.5, 5.3, 5.2, 5.3, 5.6, 5.3, 5.1, 4.9, 4.7])
    assert transition_onset(s) == 1969


def test_peak_below_min_peak_is_not_eligible() -> None:
    s = _series(1960, [4.4, 4.0, 3.5, 3.0, 2.5, 2.0])
    assert transition_onset(s) is None
    assert transition_onset(s, min_peak=4.0) == 1962  # threshold 3.96


def test_never_dropping_below_threshold_returns_none() -> None:
    s = _series(1960, [6.0, 5.9, 5.8, 5.7, 5.6, 5.5, 5.5, 5.5])
    assert transition_onset(s) is None


def test_peak_uses_only_pre_window_years() -> None:
    # default window: peak 5.0 (-> 4.5); 1978 is below but 1980 (7.0) rebounds -> 1981
    s = _series(1960, [5.0] * 16 + [4.9, 4.6, 4.4, 4.3, 7.0, 4.4, 4.0, 3.5])
    assert transition_onset(s) == 1981
    # window extended to 1980: peak 7.0 (-> 6.3); first year after which it stays <= 6.3 is 1981
    assert transition_onset(s, pre_window=(1960, 1980)) == 1981


def test_missing_years_are_skipped_not_interpolated() -> None:
    s = _series(1960, [6.0, None, None, 5.8, None, 5.2, None, 5.0, 4.8])
    assert transition_onset(s) == 1965
    # no observation inside the pre_window -> not eligible
    assert transition_onset({1990: 7.0, 1991: 6.0, 1992: 5.0}) is None
    assert transition_onset({}) is None


def test_smooth_window_damps_single_year_dip() -> None:
    raw = [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 5.0, 6.0, 6.0, 6.0, 6.0, 6.0, 5.3, 5.2, 5.1, 5.0, 4.8, 4.5]
    s = _series(1960, raw)
    # raw: dip to 5.0 in 1966 is followed by 6.0 -> onset is the sustained decline from 1972
    assert transition_onset(s, smooth=1) == 1972
    # 5-year centered mean: 1973 = mean(6.0, 5.3, 5.2, 5.1, 5.0) = 5.32 <= 5.4 (1972 = 5.52)
    assert transition_onset(s, smooth=5) == 1973


def test_smooth_skips_missing_years_in_the_window() -> None:
    # 3-year window over observed neighbours only; 1962 missing
    s = {1960: 6.0, 1961: 6.0, 1963: 5.2, 1964: 5.0, 1965: 4.8}
    # smoothed 1963 = mean(6.0, 5.2, 5.0) = 5.4 <= 5.4 -> onset 1963
    assert transition_onset(s, smooth=3) == 1963


def test_smooth_must_be_odd_positive() -> None:
    with pytest.raises(ValueError):
        transition_onset(_series(1960, [6.0, 5.0]), smooth=2)
    with pytest.raises(ValueError):
        transition_onset(_series(1960, [6.0, 5.0]), smooth=0)


def test_drop_and_min_peak_variants() -> None:
    s = _series(1960, [6.0, 5.8, 5.6, 5.4, 5.2, 5.0, 4.8, 4.6])
    assert transition_onset(s, drop=0.10) == 1963  # <= 5.4
    assert transition_onset(s, drop=0.15) == 1965  # <= 5.1
    assert transition_onset(s, min_peak=5.0) == 1963
    assert transition_onset(s, min_peak=6.5) is None


def test_onset_table_is_sorted_and_deterministic() -> None:
    rows = [
        {"iso3": "BBB", "year": 1960, "tfr": 4.0},
        {"iso3": "BBB", "year": 1961, "tfr": 3.0},
        {"iso3": "AAA", "year": 1961, "tfr": 6.0},
        {"iso3": "AAA", "year": 1960, "tfr": 5.0},
        {"iso3": "AAA", "year": 1962, "tfr": 5.0},
        {"iso3": "AAA", "year": 1963, "tfr": None},
        {"iso3": "AAA", "year": 1964, "tfr": 4.0},
        {"iso3": "CCC", "year": 1960, "tfr": None},
    ]
    table = onset_table(rows)
    assert table == [
        {"iso3": "AAA", "peak": 6.0, "peak_year": 1961, "onset_year": 1962, "eligible": True},
        {"iso3": "BBB", "peak": 4.0, "peak_year": 1960, "onset_year": None, "eligible": False},
        {"iso3": "CCC", "peak": None, "peak_year": None, "onset_year": None, "eligible": False},
    ]
    assert onset_table(list(reversed(rows))) == table


def test_onset_table_forwards_parameters() -> None:
    rows = [{"iso3": "AAA", "year": 1960 + i, "tfr": v} for i, v in enumerate([4.4, 4.0, 3.5])]
    assert onset_table(rows, min_peak=4.0)[0]["onset_year"] == 1962


@pytest.mark.skipif(not MART.exists(), reason="mart not built")
def test_real_mart_onset_count_and_median() -> None:
    import polars as pl

    df = pl.read_parquet(MART).select("iso3", "year", "tfr")
    table = onset_table(df.to_dicts())
    onsets = [r["onset_year"] for r in table if r["onset_year"] is not None]
    assert 150 <= len(onsets) <= 160
    assert 1972 <= median(onsets) <= 1978
