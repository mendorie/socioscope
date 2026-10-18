"""oecd_labour.py (H10): three OECD SDMX CSVs + Family Database SF3.1 xlsx -> one long schema.

Fixtures = the live 2026-10-18 responses reduced to a few countries / years, cell positions and
columns unchanged: house prices (JPN/ITA/SWE 2019-2021, JPN 1960, USA 2024-2025 where the
price-to-rent 2025 cell is absent), temporary employment (JPN/ITA/SWE 2019-2020, KOR 2004),
youth unemployment (JPN/ITA/SWE 2019-2020, AUT 2023-2024 whose OBS_STATUS is empty) and the
SF3.1 workbook (MarriageRates: ITA JPN KOR ESP SWE GBR CHN; MeanAgeFirstMarriage: Italy Japan
Korea Portugal Spain Sweden Bulgaria).
"""

import io
from pathlib import Path

import openpyxl
import pytest

from theme_growth_fertility import oecd, oecd_labour

FIXTURES = Path(__file__).parent / "fixtures"
HOUSE = (FIXTURES / "oecd_labour_house_prices.csv").read_bytes()
TEMP = (FIXTURES / "oecd_labour_temp.csv").read_bytes()
UNE = (FIXTURES / "oecd_labour_une.csv").read_bytes()
SF31 = (FIXTURES / "oecd_sf3_1_marriage.xlsx").read_bytes()
BY_KEY = {"house_prices": HOUSE, "temp_employment": TEMP, "youth_unemployment": UNE}

COLUMNS = {
    "iso3", "year", "dataset", "measure", "sex", "age", "unit", "value", "obs_status", "source",
}  # fmt: skip
REF_AREAS = "JPN+KOR+ITA+ESP+PRT+GRC+SWE+DNK+FIN+NOR+FRA+DEU+NLD+GBR+USA+AUT+CZE+HUN+POL"


def test_countries_urls_raw_names_and_license_are_fixed() -> None:
    assert "+".join(oecd_labour.H10_COUNTRIES) == REF_AREAS
    assert set(oecd_labour.H10_COUNTRIES) <= set(oecd.OECD_MEMBERS)
    assert [d.key for d in oecd_labour.DATASETS] == [
        "house_prices",
        "temp_employment",
        "youth_unemployment",
    ]
    by_key = {d.key: d for d in oecd_labour.DATASETS}
    assert by_key["house_prices"].url == (
        "https://sdmx.oecd.org/public/rest/data/OECD.ECO.MPD,DSD_AN_HOUSE_PRICES@DF_HOUSE_PRICES,1.0/"
        f"{REF_AREAS}.A.HPI_YDH+HPI_RPI+RHP.?format=csvfilewithlabels"
    )
    assert by_key["temp_employment"].url == (
        "https://sdmx.oecd.org/public/rest/data/OECD.ELS.SAE,DSD_TEMP@DF_TEMP_I,1.0/"
        f"{REF_AREAS}.EMP_TEMP.PT_POP_SUB._T+M+F.Y15T24+Y25T54+_T.ICSE93_1.A?format=csvfilewithlabels"
    )
    assert by_key["youth_unemployment"].url == (
        "https://sdmx.oecd.org/public/rest/data/OECD.ELS.SAE,DSD_LFS@DF_LFS_INDIC,1.1/"
        f"{REF_AREAS}.UNE_RATE.PT_LF_SUB._T+M+F.Y15T24+Y25T34.UNE?format=csvfilewithlabels"
    )
    assert [d.raw_name for d in oecd_labour.DATASETS] == [
        "house_prices.csv",
        "temp_employment.csv",
        "youth_unemployment.csv",
    ]
    assert oecd_labour.MARRIAGE_URL == (
        "https://webfs.oecd.org/Els-com/Family_Database/SF_3_1_Marriage_divorce_rates.xlsx"
    )
    assert oecd_labour.MARRIAGE_RAW_NAME == "sf3_1_marriage_divorce_rates.xlsx"
    assert oecd_labour.SOURCE == "oecd_labour"
    assert oecd.LICENSE in oecd_labour.LICENSE and "SF3.1" in oecd_labour.LICENSE


def test_house_prices_rows_carry_measure_unit_and_base_period_as_index() -> None:
    parsed = oecd_labour.parse(HOUSE, oecd_labour.DATASETS[0])
    rows = parsed.rows
    assert parsed.dropped_ref_areas == ()
    assert len(rows) == 34
    assert set(rows[0]) == COLUMNS
    assert rows[0] == {
        "iso3": "ITA",
        "year": 2019,
        "dataset": "house_prices",
        "measure": "HPI_RPI",
        "sex": "",
        "age": "",
        "unit": "IX",
        "value": 97.3899283498844,
        "obs_status": "A",
        "source": "oecd_labour",
    }
    k = {(r["iso3"], r["year"], r["measure"]): r["value"] for r in rows}
    assert k["JPN", 2020, "HPI_YDH"] == 99.383330118448
    assert k["JPN", 2020, "RHP"] == 105.850094403957
    assert k["JPN", 1960, "HPI_YDH"] == 140.885276958717  # JPN starts in 1960 (2015 = 100)
    assert ("JPN", 1960, "HPI_RPI") not in k  # price-to-rent starts in 1970: no row, no fill
    assert ("USA", 2025, "HPI_RPI") not in k and ("USA", 2025, "RHP") in k
    assert {r["unit"] for r in rows} == {"IX"}
    keys = [oecd_labour.mart_key(r) for r in rows]
    assert keys == sorted(keys)


def test_temp_employment_rows_carry_sex_and_age() -> None:
    parsed = oecd_labour.parse(TEMP, oecd_labour.DATASETS[1])
    rows = parsed.rows
    assert len(rows) == 63  # 3 countries x 2 years x 9 cells + KOR 2004 x 9
    k = {(r["iso3"], r["year"], r["sex"], r["age"]): r for r in rows}
    jpn = k["JPN", 2020, "_T", "Y15T24"]
    assert jpn == {
        "iso3": "JPN",
        "year": 2020,
        "dataset": "temp_employment",
        "measure": "EMP_TEMP",
        "sex": "_T",
        "age": "Y15T24",
        "unit": "PT_POP_SUB",
        "value": 16.291,
        "obs_status": "A",
        "source": "oecd_labour",
    }
    assert k["JPN", 2020, "F", "_T"]["value"] == 21.263
    assert {r["sex"] for r in rows} == {"_T", "M", "F"}
    assert {r["age"] for r in rows} == {"Y15T24", "Y25T54", "_T"}
    assert [r["year"] for r in rows if r["iso3"] == "KOR"] == [2004] * 9


def test_youth_unemployment_rows_keep_empty_obs_status() -> None:
    parsed = oecd_labour.parse(UNE, oecd_labour.DATASETS[2])
    rows = parsed.rows
    assert len(rows) == 48  # 3 countries x 2 years x 6 + AUT 2 years x 6
    k = {(r["iso3"], r["year"], r["sex"], r["age"]): r for r in rows}
    assert k["JPN", 2020, "_T", "Y15T24"]["value"] == 4.576
    assert k["JPN", 2020, "_T", "Y15T24"]["unit"] == "PT_LF_SUB"
    assert k["JPN", 2020, "_T", "Y15T24"]["measure"] == "UNE_RATE"
    assert k["AUT", 2024, "_T", "Y15T24"] == {
        "iso3": "AUT",
        "year": 2024,
        "dataset": "youth_unemployment",
        "measure": "UNE_RATE",
        "sex": "_T",
        "age": "Y15T24",
        "unit": "PT_LF_SUB",
        "value": 10.254,
        "obs_status": "",
        "source": "oecd_labour",
    }
    assert {r["age"] for r in rows} == {"Y15T24", "Y25T34"}


def test_parse_drops_blank_values_and_non_target_areas_and_reports_them() -> None:
    ds = oecd_labour.DATASETS[1]
    blank = TEMP.replace(b"2020,,16.291,,A,", b"2020,,,,O,")
    assert blank != TEMP
    rows = oecd_labour.parse(blank, ds).rows
    assert len(rows) == 62
    assert ("JPN", 2020, "_T", "Y15T24") not in {
        (r["iso3"], r["year"], r["sex"], r["age"]) for r in rows
    }
    other = TEMP.replace(b",KOR,Korea,", b",OECD,OECD,")
    parsed = oecd_labour.parse(other, ds)
    assert parsed.dropped_ref_areas == ("OECD",)
    assert len(parsed.rows) == 54 and "KOR" not in {r["iso3"] for r in parsed.rows}


def test_parse_fails_closed_on_other_dataflow_dimension_or_header() -> None:
    ds = oecd_labour.DATASETS[0]
    with pytest.raises(ValueError, match="STRUCTURE_ID"):
        oecd_labour.parse(HOUSE.replace(b"DF_HOUSE_PRICES(1.0)", b"DF_X(2.0)"), ds)
    with pytest.raises(ValueError, match="FREQ"):
        oecd_labour.parse(HOUSE.replace(b",A,Annual,", b",Q,Quarterly,"), ds)
    with pytest.raises(ValueError, match="MEASURE"):
        oecd_labour.parse(HOUSE.replace(b",RHP,", b",NHP,"), ds)
    with pytest.raises(ValueError, match="UNIT_MEASURE"):
        oecd_labour.parse(HOUSE.replace(b",IX,Index,", b",PC,Percent,"), ds)
    with pytest.raises(ValueError, match="header"):
        oecd_labour.parse(b"a,b,c\n1,2,3\n", ds)
    with pytest.raises(ValueError, match="STRUCTURE_ID"):
        oecd_labour.parse(TEMP, ds)  # same column family, other dataflow
    with pytest.raises(ValueError, match="header"):
        oecd_labour.parse(HOUSE, oecd_labour.DATASETS[1])  # house CSV lacks SEX / AGE
    temp = oecd_labour.DATASETS[1]
    with pytest.raises(ValueError, match="WORKER_STATUS"):
        oecd_labour.parse(TEMP.replace(b",ICSE93_1,", b",ICSE93_5,"), temp)
    with pytest.raises(ValueError, match="AGE"):
        oecd_labour.parse(TEMP.replace(b",Y25T54,", b",Y55T64,"), temp)
    une = oecd_labour.DATASETS[2]
    with pytest.raises(ValueError, match="LABOUR_FORCE_STATUS"):
        oecd_labour.parse(UNE.replace(b",UNE,Unemployment,", b",EMP,Employment,"), une)
    with pytest.raises(ValueError, match="SEX"):
        oecd_labour.parse(UNE.replace(b",_T,Total,", b",_Z,Nil,"), une)


# ---------------------------------------------------------------- SF3.1 workbook


def by_key(rows: list[dict[str, object]]) -> dict[tuple[str, int, str, str], float]:
    return {
        (str(r["iso3"]), int(str(r["year"])), str(r["dataset"]), str(r["sex"])): float(
            str(r["value"])
        )
        for r in rows
    }


def test_marriage_rates_sheet_gives_crude_marriage_rate_per_country_year() -> None:
    rows, dropped = oecd_labour.parse_marriage(SF31)
    assert set(rows[0]) == COLUMNS
    mr = [r for r in rows if r["dataset"] == "marriage_rate"]
    assert {r["iso3"] for r in mr} == {"ITA", "JPN", "KOR", "ESP", "SWE", "GBR"}
    assert {(r["measure"], r["sex"], r["age"], r["unit"], r["obs_status"]) for r in mr} == {
        ("CMR", "", "", "PER_1000_POP", "")
    }
    k = by_key(mr)
    assert k["JPN", 2020, "marriage_rate", ""] == 4.3
    assert k["ITA", 2020, "marriage_rate", ""] == 1.6
    assert k["ESP", 2020, "marriage_rate", ""] == 1.9
    assert k["SWE", 2020, "marriage_rate", ""] == 3.6
    assert k["JPN", 1960, "marriage_rate", ""] == 9.3
    assert k["ITA", 2022, "marriage_rate", ""] == 3.2
    assert ("JPN", 1961, "marriage_rate", "") not in k  # '..' -> no row
    assert ("GBR", 2022, "marriage_rate", "") not in k  # empty cell -> no row
    assert len([r for r in mr if r["iso3"] == "JPN"]) == 61
    assert len([r for r in mr if r["iso3"] == "KOR"]) == 53
    assert sorted(dropped) == [
        "MarriageRates: China (CHN) dropped: not an H10 country",
        "MeanAgeFirstMarriage: Bulgaria dropped: not an H10 country",
    ]


def test_mean_age_sheet_forward_fills_country_and_carries_sex() -> None:
    rows, _ = oecd_labour.parse_marriage(SF31)
    ma = [r for r in rows if r["dataset"] == "mean_age_first_marriage"]
    assert {r["iso3"] for r in ma} == {"ITA", "JPN", "KOR", "PRT", "ESP", "SWE"}
    assert {(r["measure"], r["age"], r["unit"], r["obs_status"]) for r in ma} == {
        ("MAFM", "", "YR", "")
    }
    assert {r["sex"] for r in ma} == {"M", "F"}
    k = by_key(ma)
    assert k["JPN", 2020, "mean_age_first_marriage", "F"] == 29.4
    assert k["JPN", 2020, "mean_age_first_marriage", "M"] == 31
    assert k["ITA", 2020, "mean_age_first_marriage", "F"] == 33.6
    assert k["KOR", 2020, "mean_age_first_marriage", "F"] == 30.78
    assert k["PRT", 1991, "mean_age_first_marriage", "M"] == 26.4
    assert ("PRT", 1990, "mean_age_first_marriage", "M") not in k  # '..'
    assert ("JPN", 2021, "mean_age_first_marriage", "F") not in k  # empty 2021 cell
    assert len([r for r in ma if r["iso3"] == "JPN"]) == 62
    assert min(int(str(r["year"])) for r in ma) == 1990


def _edit(mutate) -> bytes:  # type: ignore[no-untyped-def]
    wb = openpyxl.load_workbook(io.BytesIO(SF31))
    mutate(wb)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _set(sheet: str, cell: str, value: object):  # type: ignore[no-untyped-def]
    def mutate(wb: openpyxl.Workbook) -> None:
        wb[sheet][cell] = value

    return mutate


def _rename(sheet: str, title: str):  # type: ignore[no-untyped-def]
    def mutate(wb: openpyxl.Workbook) -> None:
        wb[sheet].title = title

    return mutate


def _years_as_text(sheet: str):  # type: ignore[no-untyped-def]
    def mutate(wb: openpyxl.Workbook) -> None:
        for cell in wb[sheet][4]:
            if isinstance(cell.value, int):
                cell.value = str(cell.value)

    return mutate


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (_rename("MarriageRates", "Rates"), "MarriageRates"),
        (_rename("MeanAgeFirstMarriage", "MeanAge"), "MeanAgeFirstMarriage"),
        (_set("MarriageRates", "B4", "Nation"), "header"),
        (_years_as_text("MarriageRates"), "year"),
        (_set("MarriageRates", "A6", "JP"), "JP"),
        (_set("MarriageRates", "B6", "Nippon"), "Nippon"),
        (_set("MarriageRates", "D6", "n.a."), "n.a."),
        (_set("MeanAgeFirstMarriage", "C4", "Sex"), "header"),
        (_set("MeanAgeFirstMarriage", "C7", "Other"), "Other"),
        (_set("MeanAgeFirstMarriage", "A7", "Nippon"), "Nippon"),
        (_set("MeanAgeFirstMarriage", "D7", "n.a."), "n.a."),
        (_set("MeanAgeFirstMarriage", "C8", "Male"), "duplicate"),
    ],
    ids=[
        "sheet-rates", "sheet-mean-age", "rates-header", "rates-years-as-text",
        "rates-bad-code", "rates-code-name-mismatch", "rates-text-value",
        "mean-age-header", "mean-age-unknown-gender", "mean-age-unknown-name",
        "mean-age-text-value", "mean-age-duplicate-key",
    ],
)  # fmt: skip
def test_marriage_layout_changes_fail_closed(mutate, match) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=match):
        oecd_labour.parse_marriage(_edit(mutate))


def test_marriage_non_workbook_fails_closed() -> None:
    with pytest.raises(ValueError, match="workbook"):
        oecd_labour.parse_marriage(b"<html>maintenance</html>")


# ---------------------------------------------------------------- mart


def test_build_mart_concatenates_sorts_and_rejects_duplicate_keys() -> None:
    staged = {d.key: oecd_labour.parse(BY_KEY[d.key], d).rows for d in oecd_labour.DATASETS}
    staged["marriage"] = oecd_labour.parse_marriage(SF31)[0]
    mart = oecd_labour.build_mart(staged)
    assert len(mart) == 34 + 63 + 48 + len(staged["marriage"])
    assert set(mart[0]) == COLUMNS
    keys = [oecd_labour.mart_key(r) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert {r["dataset"] for r in mart} == {
        "house_prices",
        "temp_employment",
        "youth_unemployment",
        "marriage_rate",
        "mean_age_first_marriage",
    }
    assert [(r["iso3"], r["year"], r["dataset"]) for r in mart[:2]] == [
        ("AUT", 2023, "youth_unemployment"),
        ("AUT", 2023, "youth_unemployment"),
    ]
    assert len(oecd_labour.build_mart({"house_prices": staged["house_prices"]})) == 34
    dup = staged["house_prices"] + [dict(staged["house_prices"][0])]
    with pytest.raises(ValueError, match="duplicate"):
        oecd_labour.build_mart({"house_prices": dup})
