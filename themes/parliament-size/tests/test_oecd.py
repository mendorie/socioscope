"""OECD SDMX-JSON（AllDimensions）の純粋変換。実 API の形を縮約（2026-10-29 確認）。"""

import json

import pytest

from theme_parliament_size import oecd


def doc(observations: dict[str, list[object]]) -> bytes:
    dims = [
        ("FREQ", ["A"]),
        ("REF_AREA", ["OECD", "JPN", "USA"]),
        ("MEASURE", ["GE", "GR"]),
        ("UNIT_MEASURE", ["USD_PPP", "PT_B1GQ"]),
        ("SECTOR", ["S13"]),
        ("EDITION", ["2025"]),
        ("CATEGORY", ["PF"]),
        ("TIME_PERIOD", ["2019", "2020"]),
    ]
    structure = {
        "dimensions": {
            "observation": [{"id": i, "values": [{"id": v} for v in vs]} for i, vs in dims]
        }
    }
    return json.dumps(
        {"data": {"structures": [structure], "dataSets": [{"observations": observations}]}}
    ).encode()


def test_parse_maps_keys_to_dimension_values_and_keeps_pct_gdp_countries() -> None:
    payload = doc(
        {
            "0:1:0:1:0:0:0:0": [38.9, 0, 0, 0],  # JPN GE % GDP 2019
            "0:1:0:1:0:0:0:1": [47.3, 0, 0, 0],  # JPN GE % GDP 2020
            "0:1:1:1:0:0:0:0": [34.9, 0, 0, 0],  # JPN GR % GDP 2019
            "0:1:0:0:0:0:0:0": [2.0e12, 0, 0, 0],  # USD PPP → 除外
            "0:0:0:1:0:0:0:0": [40.0, 0, 0, 0],  # OECD 集計 → 除外
            "0:2:0:1:0:0:0:0": [None, 0, 0, 0],  # 欠損 → 除外
        }
    )
    rows = oecd.parse(payload)
    assert [(r["iso3"], r["metric"], r["year"], r["value"]) for r in rows] == [
        ("JPN", "gov_expenditure_pct_gdp", 2019, 38.9),
        ("JPN", "gov_expenditure_pct_gdp", 2020, 47.3),
        ("JPN", "gov_revenue_pct_gdp", 2019, 34.9),
    ]
    mart = oecd.build_mart(rows)
    assert mart[0]["source"] == "oecd_gov_glance" and len(mart) == 3
    assert "A..GE+GR...." in oecd.URL and "dimensionAtObservation=AllDimensions" in oecd.URL


def test_parse_and_mart_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="not JSON"):
        oecd.parse(b"<html>")
    with pytest.raises(ValueError, match="no 'data'"):
        oecd.parse(b'{"x": 1}')
    with pytest.raises(ValueError, match="no observations"):
        oecd.parse(doc({}))
    with pytest.raises(ValueError, match="does not match"):
        oecd.parse(doc({"0:1:0": [1.0]}))
    rows = oecd.parse(doc({"0:1:0:1:0:0:0:0": [1.0]}))
    with pytest.raises(ValueError, match="duplicate"):
        oecd.build_mart(rows + rows)
