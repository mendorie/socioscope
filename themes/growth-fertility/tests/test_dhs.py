import json
from pathlib import Path

import pytest

from theme_growth_fertility import dhs

FIXTURES = Path(__file__).parent / "fixtures"
DATA = (FIXTURES / "dhs_tfr_wealth_page.json").read_bytes()
COUNTRIES = (FIXTURES / "dhs_countries_page.json").read_bytes()


def test_urls_request_single_page_json_for_tfr_by_wealth_quintile() -> None:
    url = dhs.data_url()
    assert url.startswith("https://api.dhsprogram.com/rest/dhs/data?")
    assert "indicatorIds=FE_FRTR_W_TFR" in url
    assert "characteristicCategory=Wealth%20quintile" in url
    assert "breakdown=all" in url and "perpage=5000" in url and "f=json" in url
    assert "perpage=10" in dhs.data_url(per_page=10)
    assert dhs.countries_url() == "https://api.dhsprogram.com/rest/dhs/countries?f=json&perpage=300"
    assert "perpage=5" in dhs.countries_url(per_page=5)


def test_license_states_citation_requirement_and_source_name() -> None:
    assert dhs.SOURCE == "dhs_api"
    assert "The DHS Program Indicator Data API" in dhs.LICENSE
    assert "api.dhsprogram.com" in dhs.LICENSE


def test_iso3_map_drops_codes_without_iso3() -> None:
    assert dhs.iso3_map(COUNTRIES) == {"AF": "AFG", "AL": "ALB", "KE": "KEN"}


def test_rows_from_response_maps_quintiles_and_drops_other_breakdowns() -> None:
    rows = dhs.rows_from_response(DATA, iso3_by_dhs_code=dhs.iso3_map(COUNTRIES))
    # AF2015DHS x 5 quintiles + AL2008DHS x 2; the "Residence" row and the unmapped "OS" row drop
    assert len(rows) == 7
    assert rows[0] == {
        "iso3": "ALB",
        "country": "Albania",
        "dhs_country_code": "AL",
        "survey_id": "AL2008DHS",
        "survey_year": 2008,
        "survey_type": "DHS",
        "quintile": 1,
        "quintile_label": "Lowest",
        "value": 1.9,
        "ci_low": None,
        "ci_high": None,
        "denominator_weighted": None,
        "source": "dhs_api",
    }
    af = [r for r in rows if r["survey_id"] == "AF2015DHS"]
    assert [(r["quintile"], r["quintile_label"], r["value"]) for r in af] == [
        (1, "Lowest", 5.3),
        (2, "Second", 5.4),
        (3, "Middle", 5.8),
        (4, "Fourth", 5.3),
        (5, "Highest", 4.6),
    ]
    assert all(isinstance(r["value"], float) for r in rows)
    # sorted by survey_year, iso3, survey_id, quintile
    assert [(r["survey_year"], r["iso3"], r["quintile"]) for r in rows] == sorted(
        (r["survey_year"], r["iso3"], r["quintile"]) for r in rows
    )


def test_rows_from_response_drops_unknown_quintile_label_and_other_indicator() -> None:
    doc = json.loads(DATA)
    base = doc["Data"][0]
    doc["Data"] = [
        base,
        {**base, "DataId": 1, "CharacteristicLabel": "Richest"},
        {**base, "DataId": 2, "IndicatorId": "FE_FRTR_W_GFR"},
    ]
    doc["RecordCount"] = doc["RecordsReturned"] = 3
    rows = dhs.rows_from_response(json.dumps(doc).encode(), iso3_by_dhs_code={"AF": "AFG"})
    assert [(r["survey_id"], r["quintile"]) for r in rows] == [("AF2015DHS", 1)]


def test_numeric_strings_in_ci_and_denominator_are_parsed() -> None:
    doc = json.loads(DATA)
    base = doc["Data"][0]
    doc["Data"] = [
        {**base, "CILow": "5.1", "CIHigh": "5.5", "DenominatorWeighted": "1234", "Value": 5}
    ]
    doc["RecordCount"] = doc["RecordsReturned"] = 1
    (row,) = dhs.rows_from_response(json.dumps(doc).encode(), iso3_by_dhs_code={"AF": "AFG"})
    assert (row["value"], row["ci_low"], row["ci_high"], row["denominator_weighted"]) == (
        5.0,
        5.1,
        5.5,
        1234.0,
    )


def test_unmapped_codes_lists_wealth_quintile_rows_without_iso3() -> None:
    assert dhs.unmapped_codes(DATA, iso3_by_dhs_code=dhs.iso3_map(COUNTRIES)) == ["OS"]
    assert dhs.unmapped_codes(DATA, iso3_by_dhs_code={}) == ["AF", "AL", "OS"]


@pytest.mark.parametrize(
    "patch",
    [{"TotalPages": 2}, {"RecordCount": 99}],
    ids=["paginated", "truncated"],
)
def test_pagination_or_truncation_fails_closed(patch: dict[str, int]) -> None:
    doc = {**json.loads(DATA), **patch}
    with pytest.raises(ValueError, match="DHS"):
        dhs.rows_from_response(json.dumps(doc).encode(), iso3_by_dhs_code={})
    with pytest.raises(ValueError, match="DHS"):
        dhs.iso3_map(json.dumps({**json.loads(COUNTRIES), **patch}).encode())


def test_non_object_payload_is_rejected() -> None:
    with pytest.raises(ValueError, match="DHS"):
        dhs.rows_from_response(b"[]", iso3_by_dhs_code={})
    with pytest.raises(ValueError, match="DHS"):
        dhs.iso3_map(b"<html>maintenance</html>")


# ---------------------------------------------------------------- H8: mechanisms (multi-indicator)


def _h8(name: str) -> bytes:
    return (FIXTURES / f"dhs_h8_{name}.json").read_bytes()


def test_data_url_generalises_to_indicator_groups_and_total_only() -> None:
    assert dhs.data_url(indicator_ids=("PR_IDLC_W_MNA",), category=None) == (
        "https://api.dhsprogram.com/rest/dhs/data?indicatorIds=PR_IDLC_W_MNA&perpage=5000&f=json"
    )
    url = dhs.data_url(indicator_ids=("FE_FRTR_W_A15", "FE_FRTR_W_A20"), category="Education")
    assert "indicatorIds=FE_FRTR_W_A15,FE_FRTR_W_A20&breakdown=all" in url
    assert "characteristicCategory=Education&perpage=5000&f=json" in url
    # the H4 request is unchanged
    assert dhs.data_url(indicator_ids=(dhs.INDICATOR,), category=dhs.CHARACTERISTIC) == (
        dhs.data_url()
    )


def test_h8_requests_cover_spec_table_with_distinct_names_and_urls() -> None:
    reqs = dhs.H8_REQUESTS
    assert len(reqs) == 22
    assert len({r.raw_name for r in reqs}) == len(reqs) == len({r.url for r in reqs})
    assert all(r.raw_name.startswith("dhs_h8_") and r.raw_name.endswith(".json") for r in reqs)
    by_name = {r.raw_name: r for r in reqs}
    assert by_name["dhs_h8_FE_FRTR_W_TFR_education.json"].category == "Education"
    assert by_name["dhs_h8_FE_FRTR_W_TFR_total.json"].category is None
    asfr = by_name["dhs_h8_FE_FRTR_W_A15_ASFR_total.json"]
    assert asfr.indicator_ids == tuple(f"FE_FRTR_W_A{a}" for a in range(15, 50, 5))
    assert by_name["dhs_h8_MA_MBAG_W_NMA_age_5_year_groups.json"].url.endswith(
        "characteristicCategory=Age%20(5-year%20groups)&perpage=5000&f=json"
    )
    # every indicator requested has a metric name
    assert {i for r in reqs for i in r.indicator_ids} == set(dhs.METRICS)
    assert dhs.METRICS["CM_ECMR_C_U5M"] == "u5mr"
    assert dhs.METRICS["FE_FRTR_W_A45"] == "asfr_45"
    assert len(dhs.METRICS) == 17
    # order is deterministic: TFR first, Total before breakdowns
    assert [r.raw_name for r in reqs[:3]] == [
        "dhs_h8_FE_FRTR_W_TFR_total.json",
        "dhs_h8_FE_FRTR_W_TFR_education.json",
        "dhs_h8_FE_FRTR_W_TFR_wealth_quintile.json",
    ]


ISO3 = {"AF": "AFG", "KE": "KEN"}


def test_mechanism_rows_total_request_keeps_total_rows_and_drops_unmapped() -> None:
    rows = dhs.mechanism_rows(
        _h8("FE_FRTR_W_TFR_total"), iso3_by_dhs_code=ISO3, allowed_categories=frozenset()
    )
    assert [r["survey_id"] for r in rows] == ["AF2015DHS", "KE2022DHS"]  # OS1986DHS dropped
    assert rows[0] == {
        "iso3": "AFG",
        "country": "Afghanistan",
        "dhs_country_code": "AF",
        "survey_id": "AF2015DHS",
        "survey_year": 2015,
        "survey_type": "DHS",
        "indicator_id": "FE_FRTR_W_TFR",
        "metric": "tfr",
        "characteristic_category": "Total",
        "characteristic_label": "Total",
        "by_variable": "",
        "is_preferred": 1,
        "value": 5.3,
        "ci_low": None,
        "ci_high": None,
        "denominator_weighted": None,
        "source": "dhs_api",
    }
    assert dhs.mechanism_unmapped_codes(_h8("FE_FRTR_W_TFR_total"), iso3_by_dhs_code=ISO3) == ["OS"]


def test_mechanism_rows_u5mr_keeps_both_by_variables_with_is_preferred() -> None:
    rows = dhs.mechanism_rows(
        _h8("CM_ECMR_C_U5M_total"), iso3_by_dhs_code=ISO3, allowed_categories=frozenset()
    )
    af = [(r["by_variable"], r["is_preferred"], r["value"], r["ci_low"]) for r in rows[:2]]
    assert af == [
        ("Five years preceding the survey", 1, 55.0, 49.0),
        ("Ten years preceding the survey", 0, 62.0, 56.0),
    ]
    assert all(r["metric"] == "u5mr" for r in rows)


def test_mechanism_rows_breakdown_request_passes_requested_category_only() -> None:
    payload = _h8("FE_FRTR_W_TFR_education")
    rows = dhs.mechanism_rows(
        payload, iso3_by_dhs_code=ISO3, allowed_categories=frozenset({"Education"})
    )
    assert {r["characteristic_label"]: r["value"] for r in rows if r["iso3"] == "AFG"} == {
        "No education": 5.5,
        "Primary": 4.7,
        "Secondary": 4.3,
        "Higher": 3.6,
    }
    assert all(r["characteristic_category"] == "Education" for r in rows)
    # a category that was not requested (e.g. Region) is dropped, but Total-type rows pass
    doc = json.loads(payload)
    base = doc["Data"][0]
    doc["Data"] = [
        base,
        {**base, "DataId": 1, "CharacteristicCategory": "Region", "CharacteristicLabel": "Kabul"},
        {**base, "DataId": 2, "CharacteristicCategory": "Total 15-49", "CharacteristicLabel": "x"},
        {**base, "DataId": 3, "IndicatorId": "FE_FRTR_W_GFR"},
    ]
    doc["RecordCount"] = doc["RecordsReturned"] = 4
    rows = dhs.mechanism_rows(
        json.dumps(doc).encode(), iso3_by_dhs_code=ISO3, allowed_categories=frozenset({"Education"})
    )
    assert [r["characteristic_category"] for r in rows] == ["Education", "Total 15-49"]
    # without any allowed category only Total-type rows pass
    rows = dhs.mechanism_rows(
        json.dumps(doc).encode(), iso3_by_dhs_code=ISO3, allowed_categories=frozenset()
    )
    assert [r["characteristic_category"] for r in rows] == ["Total 15-49"]


def test_mechanism_rows_asfr_group_maps_each_indicator_to_its_metric() -> None:
    rows = dhs.mechanism_rows(
        _h8("FE_FRTR_W_A15_ASFR_total"), iso3_by_dhs_code=ISO3, allowed_categories=frozenset()
    )
    af = [r for r in rows if r["iso3"] == "AFG"]
    assert [r["metric"] for r in af] == [f"asfr_{a}" for a in range(15, 50, 5)]
    assert [r["indicator_id"] for r in af] == [f"FE_FRTR_W_A{a}" for a in range(15, 50, 5)]
    assert all(isinstance(r["value"], float) for r in af)


def test_mechanism_rows_parse_denominator_and_age_groups() -> None:
    rows = dhs.mechanism_rows(
        _h8("MA_MSTA_W_UNI_age_5_year_groups"),
        iso3_by_dhs_code=ISO3,
        allowed_categories=frozenset({"Age (5-year groups)"}),
    )
    first = rows[0]
    assert (first["metric"], first["characteristic_label"], first["value"]) == (
        "in_union",
        "15-19",
        16.9,
    )
    assert first["denominator_weighted"] == 10747.0


def test_mechanism_rows_fail_closed_on_pagination() -> None:
    doc = {**json.loads(_h8("PR_IDLC_W_MNA_total")), "TotalPages": 2}
    with pytest.raises(ValueError, match="DHS"):
        dhs.mechanism_rows(
            json.dumps(doc).encode(), iso3_by_dhs_code=ISO3, allowed_categories=frozenset()
        )


def test_build_mechanisms_mart_sorts_by_key_and_rejects_duplicates() -> None:
    def row(**kw: object) -> dict[str, object]:
        base: dict[str, object] = {
            "survey_year": 2015,
            "iso3": "AFG",
            "survey_id": "AF2015DHS",
            "metric": "tfr",
            "characteristic_category": "Total",
            "characteristic_label": "Total",
            "by_variable": "",
            "value": 1.0,
        }
        return {**base, **kw}

    a = row(metric="u5mr", by_variable="Ten years preceding the survey")
    b = row(metric="u5mr", by_variable="Five years preceding the survey")
    c = row(survey_year=2008, iso3="ALB", survey_id="AL2008DHS")
    d = row(characteristic_category="Education", characteristic_label="Primary")
    assert dhs.build_mechanisms_mart([a, b, c, d]) == [c, d, b, a]
    with pytest.raises(ValueError, match="duplicate"):
        dhs.build_mechanisms_mart([a, dict(a)])
