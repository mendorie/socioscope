import json

import pytest

from theme_public_debt import oecd


def sdmx(obs: dict[str, list[float | None]], areas: list[str], years: list[str]) -> bytes:
    """Minimal SDMX-JSON with dimensions REF_AREA, MEASURE, UNIT_MEASURE, FREQ, TIME_PERIOD."""
    doc: dict = {
        "data": {
            "structure": {
                "dimensions": {
                    "observation": [
                        {"id": "REF_AREA", "values": [{"id": a} for a in areas]},
                        {"id": "MEASURE", "values": [{"id": m} for m in oecd.MEASURES]},
                        {"id": "UNIT_MEASURE", "values": [{"id": "XDC"}, {"id": "PC_GDP"}]},
                        {"id": "FREQ", "values": [{"id": "A"}]},
                        {"id": "TIME_PERIOD", "values": [{"id": y} for y in years]},
                    ]
                }
            },
            "dataSets": [{"observations": obs}],
        }
    }
    return json.dumps(doc).encode()


def test_url_lists_the_18_countries_and_measures() -> None:
    assert "JPN+NLD" in oecd.URL and "GGINTP+GGINTR+GNINTP+GDP.A" in oecd.URL
    assert "dimensionAtObservation=AllDimensions" in oecd.URL


def test_parse_keeps_xdc_actual_years_for_adopted_countries() -> None:
    # areas JPN(0) OECD(1); measures GGINTP(0) GGINTR(1) GNINTP(2) GDP(3); years 2024(0) 2026(1)
    obs = {
        "0:0:0:0:0": [8.0e12],  # JPN GGINTP XDC 2024
        "0:3:0:0:0": [6.0e14],  # JPN GDP 2024
        "0:0:1:0:0": [1.3],  # JPN GGINTP PC_GDP -> dropped (unit)
        "0:0:0:0:1": [9.0e12],  # JPN 2026 -> projection, dropped
        "1:0:0:0:0": [1.0],  # OECD aggregate -> dropped
        "0:2:0:0:0": [None],  # missing value -> dropped
    }
    out = oecd.parse(sdmx(obs, ["JPN", "OECD"], ["2024", "2026"]))

    assert [(r["iso3"], r["metric"], r["year"], r["value"]) for r in out] == [
        ("JPN", "interest_paid_lcu", 2024, 8.0e12),
        ("JPN", "ngdp_lcu", 2024, 6.0e14),
    ]
    assert all(r["source"] == "oecd_eo" for r in out)


def test_parse_reads_unit_from_observation_attribute_like_the_real_dataflow() -> None:
    # dims REF_AREA(JPN) MEASURE(4) FREQ TIME_PERIOD(2024); UNIT_MEASURE is attribute index 1
    doc = {
        "data": {
            "structures": [
                {
                    "dimensions": {
                        "observation": [
                            {"id": "REF_AREA", "values": [{"id": "JPN"}]},
                            {"id": "MEASURE", "values": [{"id": m} for m in oecd.MEASURES]},
                            {"id": "FREQ", "values": [{"id": "A"}]},
                            {"id": "TIME_PERIOD", "values": [{"id": "2024"}]},
                        ]
                    },
                    "attributes": {
                        "observation": [
                            {"id": "OBS_STATUS", "values": []},
                            {"id": "UNIT_MEASURE", "values": [{"id": "XDC"}, {"id": "PC"}]},
                        ]
                    },
                }
            ],
            "dataSets": [
                {
                    "observations": {
                        "0:0:0:0": [8.0e12, None, 0],  # XDC
                        "0:3:0:0": [6.0e14, None, 0],
                        "0:1:0:0": [1.0, None, 1],  # PC -> dropped
                        "0:2:0:0": [2.0, None, None],  # no unit -> dropped
                    }
                }
            ],
        }
    }
    out = oecd.parse(json.dumps(doc).encode())
    assert [(r["metric"], r["value"]) for r in out] == [
        ("interest_paid_lcu", 8.0e12),
        ("ngdp_lcu", 6.0e14),
    ]


def test_parse_fails_closed() -> None:
    with pytest.raises(ValueError, match="not JSON"):
        oecd.parse(b"<html>")
    with pytest.raises(ValueError, match="no 'data'"):
        oecd.parse(b"{}")
    with pytest.raises(ValueError, match="no observations"):
        oecd.parse(sdmx({}, ["JPN"], ["2024"]))
    with pytest.raises(ValueError, match="UNIT_MEASURE is neither"):
        doc = json.loads(sdmx({"0:0:0:0": [1.0]}, ["JPN"], ["2024"]))
        del doc["data"]["structure"]["dimensions"]["observation"][2]
        oecd.parse(json.dumps(doc).encode())
    with pytest.raises(ValueError, match="conflicting duplicate"):
        payload = sdmx({"0:0:0:0:0": [1.0]}, ["JPN"], ["2024"])
        doc = json.loads(payload)
        doc["data"]["dataSets"][0]["observations"] = {"0:0:0:0:0": [1.0]}
        # same key twice cannot exist in JSON; simulate via two datasets merged by hand
        doc["data"]["structure"]["dimensions"]["observation"][0]["values"].append({"id": "JPN"})
        doc["data"]["dataSets"][0]["observations"]["1:0:0:0:0"] = [2.0]
        oecd.parse(json.dumps(doc).encode())


def test_build_mart_divides_by_same_year_gdp() -> None:
    staged = [
        {"iso3": "JPN", "year": 2024, "metric": "interest_paid_lcu", "value": 8.0e12},
        {"iso3": "JPN", "year": 2024, "metric": "interest_received_lcu", "value": 7.0e12},
        {"iso3": "JPN", "year": 2024, "metric": "net_interest_lcu", "value": 1.0e12},
        {"iso3": "JPN", "year": 2024, "metric": "ngdp_lcu", "value": 6.0e14},
        {"iso3": "JPN", "year": 2025, "metric": "interest_paid_lcu", "value": 9.0e12},  # no GDP
    ]
    out = oecd.build_mart(staged)
    got = {(r["year"], r["metric"]): r["value"] for r in out}

    assert got[(2024, "gross_interest_gdp")] == pytest.approx(1.3333, abs=1e-3)
    assert got[(2024, "interest_received_gdp")] == pytest.approx(1.1667, abs=1e-3)
    assert got[(2024, "net_interest_gdp")] == pytest.approx(0.1667, abs=1e-3)
    assert (2025, "gross_interest_gdp") not in got
    assert all(r["unit"] == "general_gov_gross" and r["source"] == "oecd_eo" for r in out)
