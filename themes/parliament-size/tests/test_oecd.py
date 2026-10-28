"""OECD SDMX-JSON（AllDimensions）の純粋変換。実 API の形を縮約（2026-10-29 確認）。"""

import json

import pytest

from theme_parliament_size import oecd


def doc(
    observations: dict[str, list[object]], dims: list[tuple[str, list[str]]] | None = None
) -> bytes:
    dims = dims or [
        ("FREQ", ["A"]),
        ("REF_AREA", ["OECD", "JPN", "USA"]),
        ("MEASURE", ["GE", "GR", "GE_POP"]),
        ("UNIT_MEASURE", ["USD_PPP", "PT_B1GQ", "USD_PPP_PS"]),
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


def test_parse_maps_keys_to_dimension_values_and_keeps_adopted_units() -> None:
    payload = doc(
        {
            "0:1:0:1:0:0:0:0": [38.9, 0, 0, 0],  # JPN GE % GDP 2019
            "0:1:0:1:0:0:0:1": [47.3, 0, 0, 0],  # JPN GE % GDP 2020
            "0:1:1:1:0:0:0:0": [34.9, 0, 0, 0],  # JPN GR % GDP 2019
            "0:1:2:2:0:0:0:0": [17000.0, 0, 0, 0],  # JPN GE_POP USD PPP per person
            "0:1:2:1:0:0:0:0": [1.0, 0, 0, 0],  # GE_POP in % GDP → 単位不一致で除外
            "0:1:0:0:0:0:0:0": [2.0e12, 0, 0, 0],  # GE in USD PPP → 除外
            "0:0:0:1:0:0:0:0": [40.0, 0, 0, 0],  # OECD 集計 → 除外
            "0:2:0:1:0:0:0:0": [None, 0, 0, 0],  # 欠損 → 除外
        }
    )
    rows = oecd.parse(payload)
    assert [(r["iso3"], r["metric"], r["year"], r["value"]) for r in rows] == [
        ("JPN", "gov_expenditure_pcap_usd_ppp", 2019, 17000.0),
        ("JPN", "gov_expenditure_pct_gdp", 2019, 38.9),
        ("JPN", "gov_expenditure_pct_gdp", 2020, 47.3),
        ("JPN", "gov_revenue_pct_gdp", 2019, 34.9),
    ]
    mart = oecd.build_mart(rows)
    assert mart[0]["source"] == "oecd_gov_glance" and len(mart) == 4
    assert "A..GE+GR+GE_POP...." in oecd.URL and "format=jsondata" in oecd.URL


def test_parse_trust_filters_on_scale_and_requires_the_dimension() -> None:
    dims = [
        ("FREQ", ["A"]),
        ("REF_AREA", ["JPN", "OECD"]),
        ("MEASURE", ["TRUST_LE", "TRUST_NG", "TRUST_COMM", "TRUST_PVGA"]),
        ("UNIT_MEASURE", ["PT_RESP"]),
        ("SECTOR", ["_Z"]),
        ("EDITION", ["2025"]),
        ("SCALE", ["HMH", "L", "LIK"]),
        ("CATEGORY", ["TDG"]),
        ("TIME_PERIOD", ["2023", "2021"]),
    ]
    payload = doc(
        {
            "0:0:0:0:0:0:0:0:0": [30.2],  # JPN TRUST_LE HMH 2023
            "0:0:0:0:0:0:1:0:0": [50.1],  # 尺度 L → 除外
            "0:0:1:0:0:0:0:0:1": [28.0],  # JPN TRUST_NG HMH 2021
            "0:0:2:0:0:0:0:0:0": [10.0],  # 採用外の指標
            "0:1:0:0:0:0:0:0:0": [40.0],  # OECD 集計
            "0:0:3:0:0:0:2:0:0": [45.5],  # JPN TRUST_PVGA LIK 2023（指標別の尺度）
            "0:0:3:0:0:0:0:0:0": [1.0],  # TRUST_PVGA HMH → 除外
        },
        dims,
    )
    rows = oecd.parse_trust(payload)
    assert [(r["iso3"], r["metric"], r["year"], r["value"]) for r in rows] == [
        ("JPN", "parliament_holds_gov_accountable_pct", 2023, 45.5),
        ("JPN", "trust_legislature_pct", 2023, 30.2),
        ("JPN", "trust_national_government_pct", 2021, 28.0),
    ]
    with pytest.raises(ValueError, match="required"):
        oecd.parse_trust(doc({"0:1:0:1:0:0:0:0": [1.0]}))  # SCALE 次元が無い
    assert "TRUST_LE+TRUST_PVGA+TRUST_NG" in oecd.TRUST_URL


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
