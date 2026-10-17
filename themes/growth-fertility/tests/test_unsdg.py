import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from theme_growth_fertility import unsdg

FIXTURES = Path(__file__).parent / "fixtures"
TSPD = (FIXTURES / "unsdg_sl_dom_tspd.json").read_bytes()
MGTL = (FIXTURES / "unsdg_ic_gen_mgtl.json").read_bytes()
BY_KEY = {"sl_dom_tspd": TSPD, "ic_gen_mgtl": MGTL}
COLUMNS = {
    "iso3", "country", "year", "series", "sex", "age", "location", "value", "nature", "source",
}  # fmt: skip


def test_two_series_with_fixed_urls_raw_names_and_license() -> None:
    assert [s.key for s in unsdg.SERIES] == ["sl_dom_tspd", "ic_gen_mgtl"]
    by_key = {s.key: s for s in unsdg.SERIES}
    assert by_key["sl_dom_tspd"].url == (
        "https://unstats.un.org/sdgapi/v1/sdg/Series/Data?seriesCode=SL_DOM_TSPD&pageSize=5000"
    )
    assert by_key["ic_gen_mgtl"].url == (
        "https://unstats.un.org/sdgapi/v1/sdg/Series/Data?seriesCode=IC_GEN_MGTL&pageSize=10000"
    )
    assert [s.raw_name for s in unsdg.SERIES] == ["sl_dom_tspd.json", "ic_gen_mgtl.json"]
    assert unsdg.SOURCE == "unsdg"
    assert "https://www.un.org/en/about-us/terms-of-use" in unsdg.LICENSE
    assert "https://data.un.org/Host.aspx?Content=UNdataUse" in unsdg.LICENSE


def test_m49_dictionary_maps_numeric_codes_to_unique_iso3() -> None:
    assert all(re.fullmatch(r"[1-9]\d{0,2}", k) for k in unsdg.M49_TO_ISO3)
    assert all(re.fullmatch(r"[A-Z]{3}", v) for v in unsdg.M49_TO_ISO3.values())
    assert len(set(unsdg.M49_TO_ISO3.values())) == len(unsdg.M49_TO_ISO3)
    assert unsdg.M49_TO_ISO3["392"] == "JPN" and unsdg.M49_TO_ISO3["410"] == "KOR"
    assert unsdg.M49_TO_ISO3["826"] == "GBR" and unsdg.M49_TO_ISO3["840"] == "USA"
    # aggregates (World, regions, LDC groups) are deliberately absent
    assert not {"1", "2", "9", "62", "202", "419", "513", "747", "753"} & set(unsdg.M49_TO_ISO3)


def test_unpaid_work_rows_carry_sex_age_location_and_drop_aggregates() -> None:
    parsed = unsdg.parse(TSPD, unsdg.SERIES[0])
    rows = parsed.rows
    assert parsed.dropped_areas == ("9 Oceania",)
    assert parsed.skipped == ("392 Japan 1999 15+ FEMALE: non-numeric value 'N/A'",)
    assert len(rows) == 32  # JPN 12 + KOR 12 + SWE 2 + USA 6
    assert set(rows[0]) == COLUMNS
    assert rows[0] == {
        "iso3": "JPN",
        "country": "Japan",
        "year": 2011,
        "series": "SL_DOM_TSPD",
        "sex": "F",
        "age": "10+",
        "location": "ALLAREA",
        "value": 14.93056,
        "nature": "C",
        "source": "unsdg",
    }
    jpn_15 = [
        (r["year"], r["sex"], r["value"]) for r in rows if r["iso3"] == "JPN" and r["age"] == "15+"
    ]
    assert jpn_15 == [
        (2011, "F", 15.625),
        (2011, "M", 2.98611),
        (2016, "F", 15.13889),
        (2016, "M", 3.125),
        (2021, "F", 14.70833),
        (2021, "M", 3.75),
    ]
    assert {r["age"] for r in rows if r["iso3"] == "KOR"} == {"10+", "15+"}
    assert {r["age"] for r in rows if r["iso3"] == "SWE"} == {"15+"}
    assert [r["year"] for r in rows if r["iso3"] == "USA" and r["sex"] == "F"] == [
        2010,
        2015,
        2021,
    ]
    keys = [unsdg.mart_key(r) for r in rows]
    assert keys == sorted(keys)
    assert {r["location"] for r in rows} == {"ALLAREA"}
    assert {r["nature"] for r in rows} == {"C"}


def test_women_managers_rows_fill_location_with_allarea() -> None:
    parsed = unsdg.parse(MGTL, unsdg.SERIES[1])
    rows = parsed.rows
    assert parsed.dropped_areas == ("9 Oceania",)
    assert parsed.skipped == ()
    assert len(rows) == 8
    assert rows[0] == {
        "iso3": "JPN",
        "country": "Japan",
        "year": 2010,
        "series": "IC_GEN_MGTL",
        "sex": "F",
        "age": "15+",
        "location": "ALLAREA",
        "value": 10.41,
        "nature": "C",
        "source": "unsdg",
    }
    assert [(r["iso3"], r["year"], r["value"]) for r in rows if r["iso3"] == "SWE"] == [
        ("SWE", 2010, 31.36),
        ("SWE", 2020, 42.29),
    ]


def _with(payload: bytes, **changes: object) -> bytes:
    doc = json.loads(payload)
    doc.update(changes)
    return json.dumps(doc).encode()


def _edit_first(payload: bytes, edit: Callable[[dict[str, object]], None]) -> bytes:
    doc = json.loads(payload)
    edit(doc["data"][0])
    return json.dumps(doc).encode()


def test_parse_fails_closed_on_pagination_other_series_or_unknown_codes() -> None:
    ds = unsdg.SERIES[0]
    with pytest.raises(ValueError, match="paginated"):
        unsdg.parse(_with(TSPD, totalElements=4000), ds)
    with pytest.raises(ValueError, match="paginated"):
        unsdg.parse(_with(TSPD, totalPages=2), ds)
    with pytest.raises(ValueError, match="series"):
        unsdg.parse(MGTL, ds)  # the other series parsed as SL_DOM_TSPD
    with pytest.raises(ValueError, match="shape"):
        unsdg.parse(b'{"message": "error"}', ds)
    with pytest.raises(ValueError, match="shape"):
        unsdg.parse(b"[]", ds)

    def bad_sex(r: dict[str, object]) -> None:
        r["dimensions"]["Sex"] = "OTHER"  # type: ignore[index]

    with pytest.raises(ValueError, match="Sex"):
        unsdg.parse(_edit_first(TSPD, bad_sex), ds)

    def bad_location(r: dict[str, object]) -> None:
        r["dimensions"]["Location"] = "COASTAL"  # type: ignore[index]

    with pytest.raises(ValueError, match="Location"):
        unsdg.parse(_edit_first(TSPD, bad_location), ds)

    def bad_year(r: dict[str, object]) -> None:
        r["timePeriodStart"] = 2011.5

    with pytest.raises(ValueError, match="year"):
        unsdg.parse(_edit_first(TSPD, bad_year), ds)

    def bad_unit(r: dict[str, object]) -> None:
        r["attributes"]["Units"] = "HOURS"  # type: ignore[index]

    with pytest.raises(ValueError, match="Units"):
        unsdg.parse(_edit_first(TSPD, bad_unit), ds)


def test_build_mart_concatenates_sorts_and_rejects_duplicate_keys() -> None:
    staged = {s.key: unsdg.parse(BY_KEY[s.key], s).rows for s in unsdg.SERIES}
    mart = unsdg.build_mart(staged)
    assert len(mart) == 40
    assert set(mart[0]) == COLUMNS
    keys = [unsdg.mart_key(r) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert [(r["iso3"], r["year"], r["series"], r["sex"], r["age"]) for r in mart[:3]] == [
        ("JPN", 2010, "IC_GEN_MGTL", "F", "15+"),
        ("JPN", 2011, "SL_DOM_TSPD", "F", "10+"),
        ("JPN", 2011, "SL_DOM_TSPD", "F", "15+"),
    ]
    assert len(unsdg.build_mart({"ic_gen_mgtl": staged["ic_gen_mgtl"]})) == 8
    dup = staged["sl_dom_tspd"] + [dict(staged["sl_dom_tspd"][0])]
    with pytest.raises(ValueError, match="duplicate"):
        unsdg.build_mart({"sl_dom_tspd": dup})
