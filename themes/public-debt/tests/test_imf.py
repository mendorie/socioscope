import json

import pytest

from theme_public_debt import imf


def payload(code: str, values: dict[str, dict[str, float | None]]) -> bytes:
    return json.dumps({"values": {code: values}, "api": {"version": "1"}}).encode()


def test_url_and_raw_name() -> None:
    assert imf.url("GGXWDG_NGDP") == "https://www.imf.org/external/datamapper/api/v1/GGXWDG_NGDP"
    assert imf.raw_name("GGXWDG_NGDP") == "GGXWDG_NGDP.json"


def test_parse_keeps_iso3_actual_years_and_drops_aggregates_and_projections() -> None:
    body = payload(
        "GGXWDG_NGDP",
        {
            "JPN": {"2019": 236.1, "2024": 236.7, "2025": 230.0, "2026": 228.0, "2031": 220.0},
            "ADVEC": {"2019": 104.0},
            "FM_ADV": {"2019": 1.0},
            "USA": {"2019": 108.0, "2020": None},
        },
    )
    out = imf.parse(body, "GGXWDG_NGDP")

    assert [(r["iso3"], r["year"], r["value"]) for r in out] == [
        ("JPN", 2019, 236.1),
        ("JPN", 2024, 236.7),
        ("JPN", 2025, 230.0),
        ("USA", 2019, 108.0),
    ]
    assert out[0]["dataset"] == "weo" and out[0]["code"] == "GGXWDG_NGDP"
    assert out[0]["source"] == "imf"


def test_parse_tolerates_the_null_sibling_key_weo_returns() -> None:
    body = json.dumps({"values": {"GGXWDG_NGDP": {"JPN": {"2019": 236.1}}, "": None}}).encode()
    assert [r["value"] for r in imf.parse(body, "GGXWDG_NGDP")] == [236.1]


def test_parse_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown indicator"):
        imf.parse(payload("GG_DEBT_GDP", {"JPN": {"2000": 1.0}}), "NOPE")
    with pytest.raises(ValueError, match="no values"):
        imf.parse(b'{"api":{"version":"1"}}', "GG_DEBT_GDP")
    with pytest.raises(ValueError, match="no values"):
        imf.parse(payload("GG_DEBT_GDP", {}), "GG_DEBT_GDP")
    with pytest.raises(ValueError, match="unexpected response"):
        imf.parse(b"<html>", "GG_DEBT_GDP")
    with pytest.raises(ValueError, match="unexpected response"):
        imf.parse(payload("GG_DEBT_GDP", {"JPN": {"2000": "x"}}), "GG_DEBT_GDP")  # type: ignore[dict-item]


def test_build_mart_maps_units_and_derives_interest() -> None:
    staged = [
        *imf.parse(payload("GGXCNL_NGDP", {"JPN": {"2019": -3.0, "2024": -2.5}}), "GGXCNL_NGDP"),
        *imf.parse(payload("GGXONLB_G01_GDP_PT", {"JPN": {"2019": -2.5}}), "GGXONLB_G01_GDP_PT"),
        *imf.parse(payload("GGXWDN_G01_GDP_PT", {"JPN": {"2019": 150.0}}), "GGXWDN_G01_GDP_PT"),
        *imf.parse(payload("CG_DEBT_GDP", {"JPN": {"2019": 200.0}}), "CG_DEBT_GDP"),
        *imf.parse(payload("HH_LS", {"JPN": {"2019": 60.0}}), "HH_LS"),
    ]
    out = imf.build_mart(staged)
    got = {(r["year"], r["unit"], r["metric"], r["source"]): r["value"] for r in out}

    assert got[(2019, "general_gov_gross", "fiscal_balance_gdp", "imf_weo")] == -3.0
    assert got[(2019, "general_gov_gross", "primary_balance_gdp", "imf_fm")] == -2.5
    assert got[(2019, "general_gov_gross", "interest_gdp", "imf_fm")] == pytest.approx(0.5)
    assert (2024, "general_gov_gross", "interest_gdp", "imf_fm") not in got  # no primary
    assert got[(2019, "general_gov_net", "debt_gdp", "imf_fm")] == 150.0
    assert got[(2019, "central_gov_gross", "debt_gdp", "imf_gdd")] == 200.0
    assert got[(2019, "households", "debt_gdp", "imf_gdd")] == 60.0
    assert [tuple(r) for r in out[:1]] == [("iso3", "year", "unit", "metric", "value", "source")]
