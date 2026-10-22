import json
from pathlib import Path

import pytest

from theme_bicycle_industry import comtrade, prices

FIXTURES = Path(__file__).parent / "fixtures"
COMTRADE = (FIXTURES / "comtrade_2023_sample.json").read_bytes()
HICP = (FIXTURES / "hicp_midx_sample.json").read_bytes()
BLS = (FIXTURES / "bls_serc01_sample.json").read_bytes()


# ---- Comtrade


def test_comtrade_url_is_one_period_all_reporters_world_partner() -> None:
    u = comtrade.url(2023)
    assert "period=2023" in u and "partnerCode=0" in u and "flowCode=M,X" in u
    assert "reporterCode=392,842,276,528,250,826,380,156,490" in u
    assert "cmdCode=8712,871160,8714" in u
    assert comtrade.raw_name(2023) == "comtrade_2023.json"


def test_comtrade_parse_maps_reporters_commodities_and_flows() -> None:
    parsed = comtrade.parse(COMTRADE, year=2023)
    rows = parsed.rows
    assert {r["iso3"] for r in rows} == {"JPN", "DEU", "TWN"}
    assert {r["product"] for r in rows} == set(comtrade.COMMODITIES.values())
    jp = next(r for r in rows if r["iso3"] == "JPN" and r["flow"] == "import" and r["hs"] == "8712")
    assert jp["qty"] == 4361973.0 and round(jp["value_usd"]) == 553177133
    assert jp["year"] == 2023 and jp["source"] == "un_comtrade"
    parts = next(
        r for r in rows if r["iso3"] == "JPN" and r["flow"] == "export" and r["hs"] == "8714"
    )
    assert parts["qty"] is None and parts["net_wgt_kg"] is not None  # parts have no unit count
    assert parsed.skipped == []


def test_comtrade_parse_fails_closed_on_wrong_period_or_shape() -> None:
    doc = json.loads(COMTRADE)
    with pytest.raises(ValueError, match="period mismatch"):
        comtrade.parse(json.dumps(doc).encode(), year=2022)
    with pytest.raises(ValueError, match="not JSON"):
        comtrade.parse(b"<html>", year=2023)
    with pytest.raises(ValueError, match="unexpected Comtrade payload"):
        comtrade.parse(b'{"error": "x"}', year=2023)


def test_comtrade_parse_drops_unknown_rows_into_skipped() -> None:
    doc = json.loads(COMTRADE)
    doc["data"][0]["reporterCode"] = 999
    parsed = comtrade.parse(json.dumps(doc).encode(), year=2023)
    assert any("reporter=999" in s for s in parsed.skipped)


def test_comtrade_build_mart_sorts_and_rejects_duplicates() -> None:
    rows = comtrade.parse(COMTRADE, year=2023).rows
    mart = comtrade.build_mart(rows)
    keys = [tuple(r[c] for c in comtrade.MART_KEY) for r in mart]
    assert keys == sorted(keys)
    with pytest.raises(ValueError, match="duplicate trade key"):
        comtrade.build_mart([*rows, dict(rows[0])])


# ---- HICP


def test_hicp_url_lists_coicops_and_geos() -> None:
    u = prices.hicp_url()
    assert "prc_hicp_midx" in u and "unit=I15" in u
    assert all(f"coicop={c}" in u for c in prices.HICP_COICOP)
    assert all(f"geo={g}" in u for g in prices.HICP_GEOS)


def test_hicp_parse_expands_jsonstat_to_long_rows() -> None:
    parsed = prices.parse_hicp(HICP)
    rows = parsed.rows
    # US has no CP071x values for these months (sparse JSON-stat); it is simply absent
    assert {r["geo"] for r in rows} == {"EU27_2020", "DE"}
    assert {r["series"] for r in rows} == {"cars", "motorcycles", "bicycles"}
    assert {r["period"] for r in rows} == {"2025-10", "2025-11", "2025-12"}
    eu_bikes = {
        r["period"]: r["value"]
        for r in rows
        if r["geo"] == "EU27_2020" and r["series"] == "bicycles"
    }
    doc = json.loads(HICP)
    # EU27 bicycles 2025-12 sits at flat index (coicop 2, geo 0, time 2) = (2*3+0)*3+2 = 20
    assert eu_bikes["2025-12"] == doc["value"]["20"]
    r0 = next(r for r in rows if r["geo"] == "DE")
    assert r0["iso3"] == "DEU" and r0["base"] == "2015=100" and r0["source"] == "eurostat_hicp"


def test_hicp_parse_fails_closed_on_non_jsonstat() -> None:
    with pytest.raises(ValueError, match="not a JSON-stat dataset"):
        prices.parse_hicp(b'{"error": [{"status": 400}]}')


# ---- BLS


def test_bls_url_and_raw_name() -> None:
    assert prices.bls_url("CUUR0000SERC01", 2006, 2015).endswith(
        "/CUUR0000SERC01?startyear=2006&endyear=2015"
    )
    assert prices.bls_raw_name("CUUR0000SERC01", 2006, 2015) == "bls_CUUR0000SERC01_2006_2015.json"


def test_bls_parse_monthly_rows() -> None:
    parsed = prices.parse_bls(BLS, "CUUR0000SERC01")
    rows = parsed.rows
    assert rows and all(r["iso3"] == "USA" and r["source"] == "bls_cpi" for r in rows)
    dec = next(r for r in rows if r["period"] == "2025-12")
    assert dec["value"] == 170.585 and dec["series"] == "sports_vehicles_incl_bicycles"
    assert all(1 <= int(r["month"]) <= 12 for r in rows)


def test_bls_parse_fails_closed_on_error_status_or_missing_series() -> None:
    with pytest.raises(ValueError, match="BLS status"):
        prices.parse_bls(b'{"status": "REQUEST_NOT_PROCESSED", "message": ["x"]}', "CUUR0000SERC01")
    with pytest.raises(ValueError, match="not found exactly once"):
        prices.parse_bls(BLS, "CUUR0000SETA01")


def test_prices_build_mart_merges_sources_and_rejects_duplicates() -> None:
    rows = prices.parse_hicp(HICP).rows + prices.parse_bls(BLS, "CUUR0000SERC01").rows
    mart = prices.build_mart(rows)
    assert {r["source"] for r in mart} == {"eurostat_hicp", "bls_cpi"}
    keys = [tuple(r[c] for c in prices.MART_KEY) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    with pytest.raises(ValueError, match="duplicate price key"):
        prices.build_mart([*rows, dict(rows[0])])


def test_comtrade_origin_parse_and_mart_add_world_and_other_rows() -> None:
    doc = json.loads(COMTRADE)
    # turn the fixture into an origin file: JPN rows for CHN/TWN imports of 8712 only
    jp = [
        dict(x)
        for x in doc["data"]
        if x["reporterCode"] == 392 and x["flowCode"] == "M" and x["cmdCode"] == "8712"
    ]
    assert len(jp) == 1
    chn = {**jp[0], "partnerCode": 156, "qty": 4000000.0, "primaryValue": 450e6}
    twn = {**jp[0], "partnerCode": 490, "qty": 70000.0, "primaryValue": 60e6}
    origin_payload = json.dumps({"data": [chn, twn, {**chn, "partnerCode": 999}]}).encode()
    parsed = comtrade.parse(origin_payload, year=2023, partners=True)
    assert {r["partner"] for r in parsed.rows} == {"CHN", "TWN"}
    assert any("unexpected partner 999" in s for s in parsed.skipped)
    with pytest.raises(ValueError, match="partner mismatch"):
        comtrade.parse(origin_payload, year=2023)  # world-partner parser rejects partner rows
    assert comtrade.origin_url(2023).endswith("flowCode=M&partnerCode=156,490")

    world = comtrade.parse(COMTRADE, year=2023).rows
    mart = comtrade.build_origin_mart(parsed.rows, world)
    jp8712 = {r["partner"]: r for r in mart if r["iso3"] == "JPN" and r["hs"] == "8712"}
    assert set(jp8712) == {"CHN", "TWN", "WLD", "OTH"}
    assert jp8712["OTH"]["qty"] == jp8712["WLD"]["qty"] - 4070000.0
    assert jp8712["OTH"]["value_usd"] == pytest.approx(jp8712["WLD"]["value_usd"] - 510e6)
    # a series with only one partner present gets WLD but OTH is undefined
    only_chn = [r for r in parsed.rows if r["partner"] == "CHN"]
    mart2 = comtrade.build_origin_mart(only_chn, world)
    oth = next(r for r in mart2 if r["partner"] == "OTH")
    assert oth["qty"] is None and oth["value_usd"] is None
