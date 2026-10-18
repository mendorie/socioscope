"""eurostat.py (H9): demo_frate single-age rates -> staged rows -> cohort cumulative fertility.

Fixture = the live FI response (2026-10-18) trimmed to 1990-2024 (35 ages x 35 years).
"""

import json
from pathlib import Path

import pytest

from theme_growth_fertility import eurostat as es

FIXTURES = Path(__file__).parent / "fixtures"
FRATE = (FIXTURES / "eurostat_frate_fi.json").read_bytes()


def test_frate_rows_are_single_age_rates_per_woman() -> None:
    rows = es.frate_rows(FRATE)
    assert len(rows) == 35 * 35
    assert set(rows[0]) == {"iso3", "year", "age", "rate", "source"}
    assert rows[0] == {
        "iso3": "FIN",
        "year": 1990,
        "age": 15,
        "rate": 0.00061,
        "source": "eurostat",
    }
    assert [(r["year"], r["age"]) for r in rows[:3]] == [(1990, 15), (1990, 16), (1990, 17)]
    assert all(isinstance(r["age"], int) and 15 <= r["age"] <= 49 for r in rows)
    assert {int(str(r["year"])) for r in rows} == set(range(1990, 2025))


@pytest.mark.parametrize(
    ("dim", "code"),
    [("agedef", "REACH"), ("unit", "PC"), ("age", "Y_LT15"), ("age", "TOTAL")],
)
def test_frate_rows_fail_closed_on_codes_outside_the_request(dim: str, code: str) -> None:
    doc = json.loads(FRATE)
    cat = doc["dimension"][dim]["category"]
    first = next(iter(cat["index"]))
    cat["index"] = {code if k == first else k: v for k, v in cat["index"].items()}
    with pytest.raises(ValueError, match=dim):
        es.frate_rows(json.dumps(doc).encode())


def _rate(year: int, age: int, rate: float, iso3: str = "XXX") -> dict[str, object]:
    return {"iso3": iso3, "year": year, "age": age, "rate": rate, "source": "eurostat"}


def test_cohort_cumulative_sums_from_the_first_age_and_censors_short_cohorts() -> None:
    rows = [
        _rate(y, a, 0.1 * (a - 14) + 0.01 * (y - 2000))
        for y in (2000, 2001, 2002)
        for a in (15, 16, 17)
    ]
    out, skipped = es.cohort_cumulative(rows, first_age=15, completed_age=17, censor_min_age=16)
    assert skipped == []
    cum = {
        (r["iso3"], r["cohort"], r["age"]): r["value"] for r in out if r["metric"] == "cohort_cum"
    }
    # cohort 1985: age 15 in 2000 (0.10), 16 in 2001 (0.21), 17 in 2002 (0.32)
    assert cum[("XXX", 1985, 15)] == pytest.approx(0.10)
    assert cum[("XXX", 1985, 16)] == pytest.approx(0.31)
    assert cum[("XXX", 1985, 17)] == pytest.approx(0.63)
    # cohort 1986: age 15 in 2001, 16 in 2002; cohort 1987: age 15 in 2002
    assert cum[("XXX", 1986, 16)] == pytest.approx(0.11 + 0.22)
    assert cum[("XXX", 1987, 15)] == pytest.approx(0.12)
    # cohorts 1983/1984 never observed at age 15 -> no rows at all
    assert {r["cohort"] for r in out} == {1985, 1986, 1987}
    completed = {r["cohort"]: r for r in out if r["metric"] == "completed"}
    assert completed[1985]["age"] == 17 and completed[1985]["censored_at"] is None
    assert completed[1985]["value"] == pytest.approx(0.63)
    assert completed[1986]["age"] == 16 and completed[1986]["censored_at"] == 16
    assert 1987 not in completed  # censored below censor_min_age
    assert all(r["year"] is None and r["source"] == "eurostat" for r in out)


def test_cohort_cumulative_drops_cohorts_with_a_gap_and_reports_them() -> None:
    rows = [_rate(y, a, 0.1) for y in (2000, 2001, 2002) for a in (15, 16, 17)]
    rows = [r for r in rows if not (r["year"] == 2001 and r["age"] == 16)]  # cohort 1985 gap
    out, skipped = es.cohort_cumulative(rows, first_age=15, completed_age=17, censor_min_age=16)
    assert {r["cohort"] for r in out} == {1986, 1987}
    assert skipped == ["XXX cohort 1985: rate missing at age 16 (gap)"]


def test_build_cohort_mart_combines_asfr_and_cohorts_sorted_with_unique_keys() -> None:
    staged = es.frate_rows(FRATE)
    mart, skipped = es.build_cohort_mart(staged)
    assert skipped == []
    assert set(mart[0]) == {
        "iso3", "metric", "year", "cohort", "age", "value", "censored_at", "source",
    }  # fmt: skip
    metrics = [str(r["metric"]) for r in mart]
    assert metrics == sorted(metrics, key=es.COHORT_METRICS.index)
    asfr = [r for r in mart if r["metric"] == "asfr"]
    assert len(asfr) == 35 * 35 and asfr[0]["year"] == 1990 and asfr[0]["cohort"] is None
    cum = {(r["cohort"], r["age"]): r["value"] for r in mart if r["metric"] == "cohort_cum"}
    # cohort 1975: age 15 in 1990 ... age 45 in 2020 ... age 49 in 2024 (full chain)
    assert cum[(1975, 15)] == pytest.approx(0.00061)
    assert (1975, 49) in cum and (1974, 15) not in cum
    completed = {r["cohort"]: r for r in mart if r["metric"] == "completed"}
    assert completed[1975]["age"] == 45 and completed[1975]["censored_at"] is None
    assert completed[1975]["value"] == pytest.approx(cum[(1975, 45)])
    assert completed[1984]["age"] == 40 and completed[1984]["censored_at"] == 40
    assert 1985 not in completed
    keys = [(r["iso3"], r["metric"], r["year"], r["cohort"], r["age"]) for r in mart]
    assert len(keys) == len(set(keys))
    with pytest.raises(ValueError, match="duplicate"):
        es.build_cohort_mart([*staged, dict(staged[0])])
