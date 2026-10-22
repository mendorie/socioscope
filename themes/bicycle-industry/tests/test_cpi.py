from pathlib import Path

import pytest

from theme_bicycle_industry import cpi

FIXTURES = Path(__file__).parent / "fixtures"
ANNUAL = (FIXTURES / "cpi_zni2025a.csv").read_bytes()
MONTHLY = (FIXTURES / "cpi_zmi2025a.csv").read_bytes()


def test_urls_use_statinfid_and_csv_kind() -> None:
    assert cpi.url("annual").endswith("statInfId=000040482831&fileKind=1")
    assert cpi.raw_name("monthly") == "cpi_2025base_monthly.csv"


def test_annual_parse_selects_items_by_code_and_handles_sparse_starts() -> None:
    parsed = cpi.parse(ANNUAL, "annual")
    rows = parsed.rows
    assert {r["item"] for r in rows} == set(cpi.ITEMS.values())
    first = {it: min(r["year"] for r in rows if r["item"] == it) for it in cpi.ITEMS.values()}
    assert first["bicycle_a"] == 1970 and first["bicycle_b"] == 2015
    assert first["car_kei"] == 1980 and first["car_standard_a"] == 1995
    r2025 = {r["item"]: r["value"] for r in rows if r["year"] == 2025}
    assert all(v == 100.0 for v in r2025.values())  # 2025 = 100
    assert rows[0]["freq"] == "annual" and rows[0]["period"] == "1970" and rows[0]["month"] is None
    assert rows[0]["base"] == "2025=100" and rows[0]["source"] == "estat_cpi"
    assert parsed.skipped == []


def test_monthly_parse_yields_year_month_periods() -> None:
    rows = cpi.parse(MONTHLY, "monthly").rows
    aug = {r["item"]: r["value"] for r in rows if r["period"] == "2026-08"}
    assert aug["bicycle_a"] == 99.4 and aug["bicycle_b"] == 99.1 and aug["car_kei"] == 101.3
    assert all(r["freq"] == "monthly" and 1 <= int(r["month"]) <= 12 for r in rows)


def test_parse_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown CPI file key"):
        cpi.parse(ANNUAL, "weekly")
    with pytest.raises(ValueError, match="unexpected header"):
        cpi.parse("<html>404</html>\n\n\n\n\n\n\n".encode("cp932"), "annual")
    broken = ANNUAL.decode("cp932").replace(",7202", ",9999").encode("cp932")
    with pytest.raises(ValueError, match="item codes missing"):
        cpi.parse(broken, "annual")


def test_build_mart_sorts_and_rejects_duplicates() -> None:
    rows = cpi.parse(ANNUAL, "annual").rows + cpi.parse(MONTHLY, "monthly").rows
    mart = cpi.build_mart(rows)
    assert all(r["iso3"] == "JPN" for r in mart)
    keys = [tuple(r[c] for c in cpi.MART_KEY) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    with pytest.raises(ValueError, match="duplicate cpi key"):
        cpi.build_mart([*rows, dict(rows[0])])
