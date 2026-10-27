"""IPU Parline: pure transforms (synthetic pages from conftest.py)."""

import json

import pytest

from theme_parliament_size import ipu


def test_url_and_raw_name_follow_the_json_api_paging() -> None:
    assert (
        ipu.url("chambers", 2)
        == "https://api.data.ipu.org/v1/chambers?page[size]=100&page[number]=2"
    )
    assert ipu.raw_name("countries", 1) == "countries_p1.json"


def test_parse_keeps_only_attributes_of_interest_as_long_records(chambers_page: bytes) -> None:
    rows = ipu.parse(chambers_page, "chambers", 1)

    assert all(tuple(r) == ipu.STAGED_COLUMNS for r in rows)
    assert {r["attribute"] for r in rows} == set(ipu.CHAMBER_ATTRS)
    staff = [
        r
        for r in rows
        if r["entity_id"] == "JP-LC01" and r["attribute"] == "permanent_staff_number"
    ]
    assert [(r["seq"], r["value_num"], r["date_from"], r["date_to"]) for r in staff] == [
        (0, 1694.0, "2013-01-01", "2013-12-31"),
        (1, 1814.0, "2025-01-01", "2025-12-31"),
    ]
    budget = next(r for r in rows if r["attribute"] == "chamber_budget" and r["seq"] == 1)
    assert (budget["value"], budget["value_num"], budget["unit"]) == (
        "68113000000",
        68_113_000_000.0,
        "JPY",
    )
    pr = next(
        r for r in rows if r["entity_id"] == "JP-LC01" and r["attribute"] == "mixed_sys_elect_mems"
    )
    assert (pr["value_num"], pr["unit"]) == (176.0, "")
    assert "last_election" not in {r["attribute"] for r in rows}
    parl = next(r for r in rows if r["entity_id"] == "JP-UC01" and r["attribute"] == "parliament")
    assert (parl["value"], parl["value_num"], parl["date_from"]) == ("JP", None, "")


def test_parse_countries_flattens_dict_and_list_values(countries_page: bytes) -> None:
    rows = ipu.parse(countries_page, "countries", 1)
    by = {r["attribute"]: r for r in rows if r["seq"] == 0}

    assert str(by["country_name"]["value"]).startswith("{")
    assert "Japan" in str(by["country_name"]["value"])
    assert by["iso_alpha3"]["value"] == "JPN"
    assert by["other_groupings"]["value"] == "oecd_members"
    assert by["population_in_thousands"]["value_num"] == 128567.0
    assert "telephone_calling_code" not in {r["attribute"] for r in rows}


def _doc(items: list[dict[str, object]]) -> bytes:
    return json.dumps({"data": items}).encode()


@pytest.mark.parametrize(
    ("payload", "msg"),
    [
        (b"<html>", "not JSON"),
        (b'{"meta": {}}', "missing 'data' list"),
        (_doc([{"type": "Country", "id": "JP", "attributes": {}}]), "not of type Chamber"),
        (_doc([{"type": "Chamber", "attributes": {}}]), "without id"),
        (
            _doc([{"type": "Chamber", "id": "X-LC01", "attributes": {"age_average": 1}}]),
            "no attribute of interest",
        ),
        (
            _doc(
                [
                    {
                        "type": "Chamber",
                        "id": "X-LC01",
                        "attributes": {"chamber_name": [{"date_from": "x"}]},
                    }
                ]
            ),
            "without 'value'",
        ),
    ],
)
def test_parse_is_fail_closed(payload: bytes, msg: str) -> None:
    with pytest.raises(ValueError, match=msg):
        ipu.parse(payload, "chambers", 1)


def test_has_next_reads_the_links_object(
    chambers_page: bytes, jp_lc: dict[str, object], make_page: object
) -> None:
    assert callable(make_page)
    assert ipu.has_next(make_page("chambers", [jp_lc], True))
    assert not ipu.has_next(chambers_page)


def test_build_mart_takes_the_latest_record_per_attribute_and_joins_the_country(
    chambers_page: bytes, countries_page: bytes
) -> None:
    mart = ipu.build_mart(
        ipu.parse(chambers_page, "chambers", 1), ipu.parse(countries_page, "countries", 1)
    )

    assert [r["chamber_id"] for r in mart] == ["JP-LC01", "JP-UC01"]
    assert all(tuple(r) == ipu.MART_COLUMNS for r in mart)
    lc = mart[0]
    assert (lc["iso3"], lc["chamber_type"], lc["oecd_member"], lc["region"]) == (
        "JPN",
        "lower",
        True,
        "asia",
    )
    assert (lc["statutory_seats"], lc["statutory_seats_since"]) == (465.0, 2005)
    assert lc["current_members"] == 465.0  # latest by date_from, not first
    assert (lc["permanent_staff"], lc["staff_year"]) == (1814.0, 2025)
    assert (lc["chamber_budget"], lc["budget_currency"], lc["budget_year"]) == (
        68_113_000_000.0,
        "JPY",
        2025,
    )
    assert (lc["chamber_budget_ppp"], lc["basic_salary_ppp"], lc["salary_year"]) == (
        710492285.5,
        204392.78,
        2025,
    )
    assert (lc["majoritarian_tier_seats"], lc["proportional_tier_seats"]) == (289.0, 176.0)
    assert (lc["staff_combined_parl"], lc["budget_combined_parl"]) == (False, True)
    assert (lc["country"], lc["subregion"], lc["parliament_budget_pct_gov"]) == (
        "Japan",
        "east_asia",
        0.0963,
    )
    assert (lc["plenary_days"], lc["plenary_year"], lc["committees"]) == (47.0, 2025, 17.0)
    assert (lc["population_thousands"], lc["population_year"]) == (124371.0, 2023)
    assert lc["members_per_country"] == 713.0
    assert lc["electoral_system"] == "mixed_system" and lc["source"] == ipu.SOURCE
    uc = mart[1]
    assert (uc["chamber_type"], uc["statutory_seats"], uc["current_members"]) == (
        "upper",
        248.0,
        248.0,
    )


def test_build_mart_rejects_a_chamber_whose_country_is_missing(chambers_page: bytes) -> None:
    with pytest.raises(ValueError, match="country JP not in countries"):
        ipu.build_mart(ipu.parse(chambers_page, "chambers", 1), [])


def test_num_parses_numbers_and_currency_strings_only() -> None:
    assert ipu._num(465) == 465.0
    assert ipu._num("1,234.5") == 1234.5
    assert ipu._num("EUR 12,000") == 12000.0
    assert ipu._num({"type": "PPP", "value": 1.5}) == 1.5
    assert ipu._num("mixed_system") is None
    assert ipu._num(True) is None
    assert ipu._num(None) is None
