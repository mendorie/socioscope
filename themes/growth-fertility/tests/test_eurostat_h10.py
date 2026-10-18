"""eurostat.py (H10): demo_nind / lfsa_etpgan / une_rt_a / ilc_lvho07a -> one long schema.

Fixtures = the live FI responses (2026-10-18), unchanged (4-9 KB each). ``une_rt_a`` only
returns Y15-24 and ``lfsa_etpgan`` carries ``status: b`` flags that are not kept.
"""

import json
from pathlib import Path

import pytest

from theme_growth_fertility import eurostat as es

FIXTURES = Path(__file__).parent / "fixtures"
BY_DATASET = {
    ds: (FIXTURES / f"eurostat_{ds}_fi.json").read_bytes() for ds in es.FAMILY_FORMATION_DATASETS
}
COLUMNS = {"iso3", "year", "dataset", "indicator", "sex", "age", "unit", "value", "source"}


def test_family_formation_requests_cover_four_datasets_for_sixteen_countries() -> None:
    assert (*es.ORDER_GEOS, "PT", "EL", "AT") == es.H10_GEOS
    assert {es.GEO_TO_ISO3[g] for g in ("PT", "EL", "AT")} == {"PRT", "GRC", "AUT"}
    reqs = es.family_formation_requests()
    assert len(reqs) == 4 * 16
    assert [r.dataset for r in reqs[:16]] == ["demo_nind"] * 16
    by = {(r.dataset, r.geo): r for r in reqs}
    base = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
    assert by["demo_nind", "FI"].url == (
        f"{base}/demo_nind?format=JSON&lang=EN&geo=FI&sinceTimePeriod=1960"
    )
    assert by["lfsa_etpgan", "EL"].url == (
        f"{base}/lfsa_etpgan?format=JSON&lang=EN&geo=EL&sinceTimePeriod=1995"
        "&sex=T&sex=M&sex=F&age=Y15-24&age=Y25-34&citizen=TOTAL"
    )
    assert by["une_rt_a", "PT"].url == (
        f"{base}/une_rt_a?format=JSON&lang=EN&geo=PT&sinceTimePeriod=1990"
        "&sex=T&sex=M&sex=F&age=Y15-24&age=Y25-29&unit=PC_ACT"
    )
    assert by["ilc_lvho07a", "AT"].url == (
        f"{base}/ilc_lvho07a?format=JSON&lang=EN&geo=AT&sinceTimePeriod=2003"
        "&age=Y20-29&age=Y25-29&age=Y16-29&sex=T&rskpovth=TOTAL"
    )
    assert by["demo_nind", "FI"].raw_name == "eurostat_demo_nind_FI.json"
    assert not {r.url for r in reqs} & {r.url for r in (*es.requests(), *es.frate_requests())}


def test_demo_nind_rows_keep_every_indicator_with_empty_sex_age_unit() -> None:
    rows = es.family_formation_rows(BY_DATASET["demo_nind"], "demo_nind")
    assert len(rows) == 388
    assert set(rows[0]) == COLUMNS
    assert rows[0] == {
        "iso3": "FIN",
        "year": 1960,
        "dataset": "demo_nind",
        "indicator": "FMAR1PC",
        "sex": "",
        "age": "",
        "unit": "",
        "value": 91.3,
        "source": "eurostat",
    }
    k = {(r["year"], r["indicator"]): r["value"] for r in rows}
    assert k[2020, "GNUPRT"] == 4.0 and k[1960, "GNUPRT"] == 7.4
    assert k[2020, "FAGEMAR1"] == 32.0 and k[2020, "MAGEMAR1"] == 34.1
    assert k[2024, "MARRIAGE"] == 21420
    assert (1960, "FAGEMAR1") not in k  # sparse value: no row
    assert {r["indicator"] for r in rows} == set(es.NIND_INDICATORS)


def test_lfsa_etpgan_rows_are_temp_share_by_sex_and_age() -> None:
    rows = es.family_formation_rows(BY_DATASET["lfsa_etpgan"], "lfsa_etpgan")
    assert len(rows) == 186
    k = {(r["year"], r["sex"], r["age"]): r for r in rows}
    assert k[2020, "T", "Y15-24"] == {
        "iso3": "FIN",
        "year": 2020,
        "dataset": "lfsa_etpgan",
        "indicator": "temp_share",
        "sex": "T",
        "age": "Y15-24",
        "unit": "PC",
        "value": 40.2,
        "source": "eurostat",
    }
    assert k[2020, "F", "Y25-34"]["value"] == 25.1
    assert {r["sex"] for r in rows} == {"T", "M", "F"}
    assert {r["age"] for r in rows} == {"Y15-24", "Y25-34"}
    assert {int(str(r["year"])) for r in rows} == set(range(1995, 2026))


def test_une_rt_a_rows_are_youth_unemployment_only_for_the_ages_returned() -> None:
    rows = es.family_formation_rows(BY_DATASET["une_rt_a"], "une_rt_a")
    assert len(rows) == 51
    k = {(r["year"], r["sex"], r["age"]): r for r in rows}
    assert k[2020, "T", "Y15-24"]["value"] == 21.0
    assert k[2020, "T", "Y15-24"]["indicator"] == "unemployment_rate"
    assert k[2020, "T", "Y15-24"]["unit"] == "PC_ACT"
    assert {r["age"] for r in rows} == {"Y15-24"}  # Y25-29 was requested but not returned
    assert min(int(str(r["year"])) for r in rows) == 2009  # FI: 2003-2008 cells are absent


def test_ilc_lvho07a_rows_are_housing_cost_overburden_by_age() -> None:
    rows = es.family_formation_rows(BY_DATASET["ilc_lvho07a"], "ilc_lvho07a")
    assert len(rows) == 66
    k = {(r["year"], r["age"]): r for r in rows}
    assert k[2020, "Y25-29"] == {
        "iso3": "FIN",
        "year": 2020,
        "dataset": "ilc_lvho07a",
        "indicator": "housing_cost_overburden",
        "sex": "T",
        "age": "Y25-29",
        "unit": "PC",
        "value": 5.7,
        "source": "eurostat",
    }
    assert k[2020, "Y16-29"]["value"] == 7.7 and k[2020, "Y20-29"]["value"] == 8.8


@pytest.mark.parametrize(
    ("dataset", "dim", "code"),
    [
        ("demo_nind", "indic_de", "DIVORCE"),
        ("lfsa_etpgan", "unit", "THS_PER"),
        ("lfsa_etpgan", "age", "Y15-64"),
        ("lfsa_etpgan", "citizen", "NAT"),
        ("une_rt_a", "unit", "THS_PER"),
        ("une_rt_a", "sex", "X"),
        ("ilc_lvho07a", "rskpovth", "A_MD60"),
        ("ilc_lvho07a", "age", "Y_GE65"),
    ],
)
def test_family_formation_rows_fail_closed_on_codes_outside_the_closed_sets(
    dataset: str, dim: str, code: str
) -> None:
    doc = json.loads(BY_DATASET[dataset])
    cat = doc["dimension"][dim]["category"]
    first = next(iter(cat["index"]))
    cat["index"] = {code if k == first else k: v for k, v in cat["index"].items()}
    with pytest.raises(ValueError, match=dim):
        es.family_formation_rows(json.dumps(doc).encode(), dataset)


def test_family_formation_rows_rejects_unknown_dataset_and_wrong_payload() -> None:
    with pytest.raises(ValueError, match="dataset"):
        es.family_formation_rows(BY_DATASET["demo_nind"], "demo_frate")
    with pytest.raises(ValueError, match="indic_de"):
        es.family_formation_rows(BY_DATASET["une_rt_a"], "demo_nind")  # other dataset's shape


def test_build_family_formation_mart_concatenates_sorts_and_rejects_duplicates() -> None:
    staged = {ds: es.family_formation_rows(p, ds) for ds, p in BY_DATASET.items()}
    mart = es.build_family_formation_mart(staged)
    assert len(mart) == 388 + 186 + 51 + 66
    assert set(mart[0]) == COLUMNS
    keys = [
        (r["iso3"], r["year"], r["dataset"], r["indicator"], r["sex"], r["age"], r["unit"])
        for r in mart
    ]
    assert keys == sorted(keys, key=lambda k: (k[0], int(str(k[1])), *map(str, k[2:])))
    assert len(set(keys)) == len(keys)
    assert mart[0]["year"] == 1960 and mart[0]["dataset"] == "demo_nind"
    assert len(es.build_family_formation_mart({"une_rt_a": staged["une_rt_a"]})) == 51
    with pytest.raises(ValueError, match="duplicate"):
        es.build_family_formation_mart({"une_rt_a": [*staged["une_rt_a"], staged["une_rt_a"][0]]})
