from pathlib import Path

import pytest

from theme_growth_fertility import oecd, oecd_eag

FIXTURES = Path(__file__).parent / "fixtures"
FIN_SOURCE = (FIXTURES / "oecd_eag_fin_source.csv").read_bytes()
EARN_REL = (FIXTURES / "oecd_eag_earn_rel.csv").read_bytes()
FIN_PERSTUD = (FIXTURES / "oecd_eag_fin_perstud.csv").read_bytes()
BY_KEY = {"fin_source": FIN_SOURCE, "earn_rel": EARN_REL, "fin_perstud": FIN_PERSTUD}

COLUMNS = {
    "iso3", "year", "dataset", "measure", "education_level", "exp_source", "sex", "work_time",
    "price_base", "unit", "base_per", "value", "obs_status", "source",
}  # fmt: skip


def test_three_datasets_with_fixed_urls_and_raw_names() -> None:
    assert [d.key for d in oecd_eag.DATASETS] == ["fin_source", "earn_rel", "fin_perstud"]
    by_key = {d.key: d for d in oecd_eag.DATASETS}
    assert by_key["fin_source"].url == (
        "https://sdmx.oecd.org/public/rest/data/OECD.EDU.IMEP,DSD_EAG_UOE_FIN@DF_UOE_FIN_SOURCE_GV_PR_NDOM,3.2/"
        ".EXP.ISCED11_1T8+ISCED11_1T4+ISCED11_5T8+ISCED11_02.S13+S1D_NON_EDU+S2+_T.INST_EDU.DIR_EXP.."
        "PT_EXP+PT_B1GQ.SOURCE?startPeriod=1995&format=csvfilewithlabels"
    )
    assert by_key["earn_rel"].url == (
        "https://sdmx.oecd.org/public/rest/data/OECD.EDU.IMEP,DSD_EAG_LSO_EA@DF_LSO_EARN_REL_UPPER,1.0/"
        "..Y25T64.ISCED11A_0T2+ISCED11A_5T8+ISCED11A_5+ISCED11A_6+ISCED11A_7_8._T.EARN_RELATIVE._Z._T._Z."
        "ED_NED.EMP._Z.PT_EARN_WR_ISCED11A_3.OBS..EARNINGS.A?startPeriod=2000&format=csvfilewithlabels"
    )
    assert by_key["fin_perstud"].url == (
        "https://sdmx.oecd.org/public/rest/data/OECD.EDU.IMEP,DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_PERSTUD,3.2/"
        ".FIN_PERSTUD.ISCED11_1T8+ISCED11_1T4+ISCED11_5T8+ISCED11_02._T.INST_EDU.DIR_EXP.Q+V.USD_PPP_ST."
        "SOURCE?startPeriod=1995&format=csvfilewithlabels"
    )
    assert [d.raw_name for d in oecd_eag.DATASETS] == [
        "eag_fin_source.csv",
        "eag_earn_rel.csv",
        "eag_fin_perstud.csv",
    ]
    assert oecd_eag.SOURCE == "oecd_eag" and oecd_eag.LICENSE == oecd.LICENSE


def test_fin_source_rows_keep_members_drop_blanks_and_report_dropped_areas() -> None:
    parsed = oecd_eag.parse(FIN_SOURCE, oecd_eag.DATASETS[0])
    rows = parsed.rows
    assert {r["iso3"] for r in rows} == {"JPN", "KOR", "SWE", "USA"}
    assert parsed.dropped_ref_areas == ("BRA", "EU25", "OECD")
    assert len(rows) == 6  # blank JPN pre-primary row dropped
    assert set(rows[0]) == COLUMNS
    assert rows[0] == {
        "iso3": "JPN",
        "year": 2022,
        "dataset": "fin_source",
        "measure": "EXP",
        "education_level": "ISCED11_1T8",
        "exp_source": "S1D_NON_EDU",
        "sex": "_Z",
        "work_time": "_Z",
        "price_base": "_Z",
        "unit": "PT_EXP",
        "base_per": "",
        "value": 26.7163025574758,
        "obs_status": "W",
        "source": "oecd_eag",
    }
    kor = [(r["year"], r["value"], r["obs_status"]) for r in rows if r["iso3"] == "KOR"]
    assert kor == [(2015, 30.2912864265979, "W"), (2022, 17.3812562370568, "W")]
    assert [(r["iso3"], r["year"]) for r in rows] == sorted((r["iso3"], r["year"]) for r in rows)


def test_earn_rel_rows_carry_sex_and_work_time() -> None:
    parsed = oecd_eag.parse(EARN_REL, oecd_eag.DATASETS[1])
    rows = parsed.rows
    assert parsed.dropped_ref_areas == ("ARG", "BRA", "OECD")
    assert len(rows) == 6  # JPN blank (O) and ARG blank (A) dropped
    kor = next(r for r in rows if r["iso3"] == "KOR")
    assert kor == {
        "iso3": "KOR",
        "year": 2022,
        "dataset": "earn_rel",
        "measure": "EARN_RELATIVE",
        "education_level": "ISCED11A_5T8",
        "exp_source": "_Z",
        "sex": "F",
        "work_time": "FT",
        "price_base": "_Z",
        "unit": "PT_EARN_WR_ISCED11A_3",
        "base_per": "",
        "value": 130.8905487060547,
        "obs_status": "A",
        "source": "oecd_eag",
    }
    assert {r["obs_status"] for r in rows} == {"A", "B", "W"}
    jpn = [r["year"] for r in rows if r["iso3"] == "JPN"]
    assert jpn == [2005, 2012]


def test_fin_perstud_rows_keep_price_base_and_base_period() -> None:
    parsed = oecd_eag.parse(FIN_PERSTUD, oecd_eag.DATASETS[2])
    rows = parsed.rows
    assert parsed.dropped_ref_areas == ("BGR", "OECD")
    assert len(rows) == 6
    jpn = [
        (r["year"], r["price_base"], r["base_per"], r["value"]) for r in rows if r["iso3"] == "JPN"
    ]
    assert jpn == [
        (2005, "V", "", 8981.05304891896),
        (2022, "Q", "2020", 13178.2367105341),
        (2022, "V", "", 14068.8938226181),
    ]
    assert {r["unit"] for r in rows} == {"USD_PPP_ST"}
    assert {r["measure"] for r in rows} == {"FIN_PERSTUD"}
    assert {r["exp_source"] for r in rows} == {"_T"}


def test_parse_fails_closed_on_other_dataflow_dimension_or_header() -> None:
    ds = oecd_eag.DATASETS[0]
    other = FIN_SOURCE.replace(b"DF_UOE_FIN_SOURCE_GV_PR_NDOM(3.2)", b"DF_X(1.0)")
    with pytest.raises(ValueError, match="STRUCTURE_ID"):
        oecd_eag.parse(other, ds)
    wrong_fixed = FIN_SOURCE.replace(b",DIR_EXP,", b",CAP_EXP,")
    with pytest.raises(ValueError, match="EXPENDITURE_TYPE"):
        oecd_eag.parse(wrong_fixed, ds)
    unknown_level = FIN_SOURCE.replace(b",ISCED11_1T8,", b",ISCED11_9,")
    with pytest.raises(ValueError, match="EDUCATION_LEV"):
        oecd_eag.parse(unknown_level, ds)
    with pytest.raises(ValueError, match="header"):
        oecd_eag.parse(b"a,b,c\n1,2,3\n", ds)
    # a payload from another EAG dataflow is rejected by the dataset it is parsed as
    with pytest.raises(ValueError, match="header"):
        oecd_eag.parse(EARN_REL, ds)
    with pytest.raises(ValueError, match="STRUCTURE_ID"):
        oecd_eag.parse(FIN_PERSTUD, ds)  # same header family, other dataflow
    unknown_work_time = EARN_REL.replace(b",OBS,Observed,FT,", b",OBS,Observed,PT,")
    with pytest.raises(ValueError, match="WORK_TIME_ARNGMNT"):
        oecd_eag.parse(unknown_work_time, oecd_eag.DATASETS[1])


def test_build_mart_concatenates_sorts_and_rejects_duplicate_keys() -> None:
    staged = {d.key: oecd_eag.parse(BY_KEY[d.key], d).rows for d in oecd_eag.DATASETS}
    mart = oecd_eag.build_mart(staged)
    assert len(mart) == 18
    assert set(mart[0]) == COLUMNS
    keys = [oecd_eag.mart_key(r) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert [(r["iso3"], r["year"], r["dataset"]) for r in mart[:3]] == [
        ("ITA", 2019, "earn_rel"),
        ("JPN", 2005, "earn_rel"),
        ("JPN", 2005, "fin_perstud"),
    ]
    # a single dataset is enough (the others may be missing at stage)
    assert len(oecd_eag.build_mart({"earn_rel": staged["earn_rel"]})) == 6
    dup = staged["fin_source"] + [dict(staged["fin_source"][0])]
    with pytest.raises(ValueError, match="duplicate"):
        oecd_eag.build_mart({"fin_source": dup})
