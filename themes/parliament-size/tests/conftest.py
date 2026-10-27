"""Synthetic IPU Parline pages shaped like the live JSON:API responses (checked 2026-10-27).

Values for Japan are the ones the API returned; the structure (meta / links / data[].attributes,
each attribute a list of time-bounded records, a single object with ``value`` or a bare scalar)
mirrors the live API so that the parser's shape checks are exercised.
"""

import json
from collections.abc import Callable

import pytest

from theme_parliament_size import ipu

Builder = Callable[..., dict[str, object]]
PageBuilder = Callable[[str, list[dict[str, object]], bool], bytes]


def rec(value: object, date_from: str = "", date_to: str = "") -> dict[str, object]:
    return {
        "value": value,
        "date_from": date_from,
        "date_to": date_to,
        "date_valid_until": "",
        "next_check_date": "",
        "missing_reason": "",
        "annotation": {"notes": {"en": "", "fr": ""}, "source": {"en": "", "fr": ""}},
    }


def chamber(cid: str, cc: str, name: str, **over: object) -> dict[str, object]:
    attrs: dict[str, object] = {
        "chamber_name": [rec(name, "2005-01-01")],
        "parliament": {"value": cc, "missing_reason": "", "annotation": {}},
        "statutory_members_number": [rec(465, "2005-09-01")],
        "current_members_number": [rec(480, "2012-12-26", "2014-12-23"), rec(465, "2025-12-31")],
        "directly_elected_number": [rec(465, "2018-01-01")],
        "designation_mode": [rec("directly_elected", "2018-01-01")],
        "electoral_system": [rec("mixed_system", "2005-09-01")],
        "electoral_subsystem": [rec("parallel_systems", "2005-09-01")],
        "permanent_staff_number": [
            rec(1694, "2013-01-01", "2013-12-31"),
            rec(1814, "2025-01-01", "2025-12-31"),
        ],
        "major_sys_elect_mems": {"value": 289, "missing_reason": "", "annotation": {}},
        "mixed_sys_elect_mems": {"value": 176, "missing_reason": "", "annotation": {}},
        "is_staff_combined_parl": [rec(False, "2013-01-01")],
        "chamber_budget": [
            rec({"type": "JPY", "value": 71975000000}, "2013-01-01", "2013-12-31"),
            rec({"type": "JPY", "value": 68113000000}, "2025-01-01", "2025-12-31"),
        ],
        "chamber_budget_ppp": [
            rec({"type": "PPP", "value": 710492285.5}, "2025-01-01", "2025-12-31")
        ],
        "is_budget_combined_parl": [rec(True, "2013-01-01", "2013-12-31")],
        "basic_salary": [rec({"type": "JPY", "value": 21063085}, "2025-01-01", "2025-12-31")],
        "basic_salary_ppp": [rec({"type": "PPP", "value": 204392.78}, "2025-01-01", "2025-12-31")],
        "last_election": {"value": {"from": "2026-02-08T00:00:00.000Z"}, "annotation": None},
        "num_days_parl_plen": [rec(58, "2008-01-01", "2008-12-31"), rec(47, "2025-01-01")],
        "num_cham_perm_committees": [rec(17, "2026-02-18")],
        "age_average": [rec(55.1, "2026-02-18")],  # not of interest, must be dropped
    }
    attrs.update(over)
    return {"type": "Chamber", "id": cid, "attributes": attrs}


def country(cc: str, iso3: str, name: str, pop: int, members: int, oecd: bool) -> dict[str, object]:
    groups = [{"term": "oecd_members"}] if oecd else []
    return {
        "type": "Country",
        "id": cc,
        "attributes": {
            "country_name": {"value": {"en": name, "fr": name}},
            "iso_alpha3": iso3,
            "region": [rec("asia", "2005-01-01")],
            "political_system": [rec("parliamentary_system", "2005-01-01")],
            "members_per_country": [
                rec(707, "2005-09-01", "2019-06-30"),
                rec(members, "2019-07-01"),
            ],
            "population_in_thousands": [
                rec(128567, "2009-01-01", "2009-12-31"),
                rec(pop, "2023-01-01", "2023-12-31"),
            ],
            "inhabitants_per_parliament": [rec(174433.38, "2023-01-01")],
            "parliament_devoted_budget_perc": [rec(0.0963, "2025-01-01")],
            "other_groupings": {"value": groups, "missing_reason": "", "annotation": {}},
            "subregion": [rec("east_asia", "2005-01-01")],
            "local_currency": [rec("JPY", "2005-01-01")],
            "ppp_conversion_factor": [rec(104.274, "2012-01-01", "2012-12-31")],
            "parliament_structure": None,
            "telephone_calling_code": 81,
        },
    }


def page(kind: str, items: list[dict[str, object]], next_page: bool) -> bytes:
    k: ipu.Kind = "chambers" if kind == "chambers" else "countries"
    links = {"self": ipu.url(k, 1)}
    if next_page:
        links["next"] = ipu.url(k, 2)
    doc = {
        "meta": {"total": len(items), "row_count": 100, "license": "CC BY-NC-SA 4.0"},
        "links": links,
        "data": items,
    }
    return json.dumps(doc).encode()


@pytest.fixture
def jp_lc() -> dict[str, object]:
    return chamber("JP-LC01", "JP", "House of Representatives")


@pytest.fixture
def chambers_page(jp_lc: dict[str, object]) -> bytes:
    jp_uc = chamber(
        "JP-UC01",
        "JP",
        "House of Councillors",
        statutory_members_number=[rec(248, "2022-07-01")],
        current_members_number=[rec(248, "2025-07-28")],
    )
    return page("chambers", [jp_lc, jp_uc], False)


@pytest.fixture
def countries_page() -> bytes:
    return page("countries", [country("JP", "JPN", "Japan", 124371, 713, True)], False)


@pytest.fixture
def make_page() -> PageBuilder:
    return page


@pytest.fixture
def make_country() -> Builder:
    return country
