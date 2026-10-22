from pathlib import Path

import pytest

from theme_bicycle_industry import meti

FIXTURES = Path(__file__).parent / "fixtures"
F2025 = (FIXTURES / "meti_h2daa2025k_sample.xlsx").read_bytes()
F2021 = (FIXTURES / "meti_h2daa2021k_sample.xlsx").read_bytes()


def test_urls_and_names_follow_the_meti_layout() -> None:
    assert meti.annual_url(2025).endswith("/08_seidou/nenpo/2025/h2daa2025k.xlsx")
    assert meti.raw_name(2021) == "h2daa2021k.xlsx"


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("2025000101", ("month", "2025-01", 2025)),
        (2021001212, ("month", "2021-12", 2021)),
        (2017000000, ("cy", "2017", 2017)),
        (2020100000, ("fy", "FY2020", 2020)),
        (2021000406, ("quarter", "2021Q2", 2021)),
    ],
)
def test_parse_time_code(code: object, expected: tuple[str, str, int]) -> None:
    p = meti.parse_time_code(code)
    assert (p.period_type, p.period, p.year) == expected


def test_parse_time_code_rejects_unknown_layouts() -> None:
    with pytest.raises(ValueError, match="unknown layout"):
        meti.parse_time_code("2021000207")
    with pytest.raises(ValueError, match="not 10 digits"):
        meti.parse_time_code("abc")


def test_normalize_absorbs_year_to_year_spelling_changes() -> None:
    a = meti.normalize("軽自動車（気筒容積６６０ｍｌ以下）")
    b = meti.normalize("軽自動車・気筒容積６６０ｍｌ以下")
    assert a == b == "軽自動車気筒容積660ml以下"


def test_parse_2025_yields_monthly_rows_for_bicycles_and_motor_vehicles() -> None:
    parsed = meti.parse(F2025, report_year=2025)
    rows = parsed.rows
    assert {r["period_type"] for r in rows} == {"month"}
    e = [r for r in rows if r["product"] == "bicycle_e_assist" and r["measure"] == "production_qty"]
    assert len(e) == 12 and e[0]["period"] == "2025-01" and e[0]["value"] == 49451.0
    assert (
        e[0]["unit"] == "台" and e[0]["industry"] == "bicycle" and e[0]["source"] == "meti_seidou"
    )
    kei = next(r for r in rows if r["product"] == "car_kei" and r["measure"] == "sales_qty")
    assert kei["value"] == 115474.0 and kei["industry"] == "motor_vehicle"
    moto = {r["product"] for r in rows if r["product"] and r["product"].startswith("moto_")}
    assert moto == {"moto_le50", "moto_51_125", "moto_126_250", "moto_gt250"}
    # unmapped items (buses, trucks, labour) stay in staged with product=None and are reported
    assert any(r["product"] is None for r in rows)
    assert any("unmapped product" in s for s in parsed.skipped)
    # 「その他」 only maps inside the bicycle survey
    assert all(r["survey_no"] == "2430" for r in rows if r["product"] == "bicycle_other")


def test_parse_2021_includes_calendar_year_fy_and_quarter_columns() -> None:
    rows = meti.parse(F2021, report_year=2021).rows
    light = {
        (r["period_type"], r["period"]): r["value"]
        for r in rows
        if r["product"] == "bicycle_light" and r["measure"] == "production_qty"
    }
    assert ("cy", "2017") in light and ("fy", "FY2020") in light and ("quarter", "2021Q1") in light
    assert sum(1 for k in light if k[0] == "month") == 12
    assert all(r["report_year"] == 2021 for r in rows)


def test_parse_handles_secret_and_unknown_markers() -> None:
    assert meti.parse_value("X") == (None, "X")
    assert meti.parse_value("***") == (None, "***")
    assert meti.parse_value(None) == (None, "missing")
    assert meti.parse_value("1,234") == (1234.0, "")
    with pytest.raises(ValueError, match="unparseable"):
        meti.parse_value("n/a")


def test_parse_fails_closed_on_non_xlsx_and_wrong_header() -> None:
    with pytest.raises(ValueError, match="not an xlsx"):
        meti.parse(b"<html>blocked</html>", report_year=2025)


def test_build_mart_prefers_latest_report_year_and_adds_annual_totals() -> None:
    staged = meti.parse(F2021, report_year=2021).rows + meti.parse(F2025, report_year=2025).rows
    # simulate a revision of CY 2017 published in a later report
    revised = dict(
        next(
            r
            for r in staged
            if r["product"] == "bicycle_light"
            and r["measure"] == "production_qty"
            and r["period"] == "2017"
        )
    )
    revised["report_year"] = 2022
    revised["value"] = 999.0
    mart = meti.build_mart([*staged, revised])
    assert all(r["product"] is not None and r["measure"] is not None for r in mart)
    cy2017 = next(
        r
        for r in mart
        if r["product"] == "bicycle_light"
        and r["measure"] == "production_qty"
        and r["period_type"] == "cy"
        and r["period"] == "2017"
    )
    assert cy2017["value"] == 999.0 and cy2017["report_year"] == 2022
    tot = next(
        r
        for r in mart
        if r["product"] == "bicycle_e_assist"
        and r["measure"] == "production_qty"
        and r["period_type"] == "cy_from_months"
        and r["year"] == 2025
    )
    monthly = [
        r["value"]
        for r in mart
        if r["product"] == "bicycle_e_assist"
        and r["measure"] == "production_qty"
        and r["period_type"] == "month"
        and r["year"] == 2025
    ]
    assert tot["value"] == sum(monthly) and tot["iso3"] == "JPN"
    # stocks are not summed
    assert not any(
        r["period_type"] == "cy_from_months" and r["measure"] == "inventory_qty" for r in mart
    )
    keys = [tuple(r[c] for c in meti.MART_KEY) for r in mart]
    assert keys == sorted(keys) and len(keys) == len(set(keys))
