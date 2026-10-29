"""職業安定業務統計（一般職業紹介状況）職業別労働市場関係指標: fetch -> stage -> mart with fakes."""

import copy
from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import jobs
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
XLSX = (FIXTURES / "jobs_jsoc2009_from2022_04.xlsx").read_bytes()
XLS = (FIXTURES / "jobs_mhlw2011_from2012_03.xls").read_bytes()

INCL = "regular_incl_parttime"
EXCL = "regular_excl_parttime"
PT = "parttime"


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def full_responses() -> dict[str, bytes]:
    return {jobs.FILE_2012.url: XLS, jobs.FILE_2022.url: XLSX}


def index(rows: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    return {
        (r["year"], r["month"], r["occupation"], r["employment_type"], r["metric"]): r["value"]
        for r in rows
    }


# ---- constants


def test_files_are_fixed_to_the_two_estat_long_series_tables() -> None:
    assert jobs.SOURCE == "mhlw_jobs"
    assert "政府標準利用規約" in jobs.LICENSE
    assert [f.stat_inf_id for f in jobs.FILES] == ["000031942508", "000040505332"]
    assert jobs.FILE_2012.url.endswith("statInfId=000031942508&fileKind=0")
    assert jobs.FILE_2012.classification == "jp_mhlw2011"
    assert jobs.FILE_2022.classification == "jp_jsoc2009"
    assert jobs.FILE_2012.raw_name.endswith(".xls")
    assert jobs.FILE_2022.raw_name.endswith(".xlsx")
    assert XLS.startswith(jobs.FILE_2012.magic)
    assert XLSX.startswith(jobs.FILE_2022.magic)


# ---- fetch


def test_fetch_puts_both_workbooks_in_raw_with_manifest_rows() -> None:
    ctx = make_ctx(full_responses())
    written, skipped = jobs.fetch(ctx, [], [])
    assert skipped == []
    assert written == [f"{THEME}/{jobs.SOURCE}/{f.raw_name}" for f in jobs.FILES]
    recs = ctx.raw.records()
    assert [r.url for r in recs] == [f.url for f in jobs.FILES]
    assert all(r.license == jobs.LICENSE and r.theme == THEME for r in recs)


def test_fetch_rejects_payload_without_excel_magic_and_reports_fetch_error() -> None:
    ctx = make_ctx({jobs.FILE_2022.url: b"<html>maintenance</html>"})
    written, skipped = jobs.fetch(ctx, [], [])
    assert written == []
    assert skipped == [
        f"{jobs.FILE_2012.raw_name}: no fake response for {jobs.FILE_2012.url}",
        f"{jobs.FILE_2022.raw_name}: non-excel payload",
    ]
    assert ctx.raw.records() == []


# ---- parse (pure)


def test_parse_xlsx_yields_long_rows_in_original_units() -> None:
    rows = jobs.parse(XLSX, jobs.FILE_2022)
    assert set(rows[0]) == {
        "year",
        "month",
        "classification",
        "occupation",
        "employment_type",
        "metric",
        "value",
    }
    assert {r["classification"] for r in rows} == {"jp_jsoc2009"}
    # 3 occupations x 14 months (2022-04..2023-05) x 3 employment types x 6 metrics
    assert len(rows) == 3 * 14 * 3 * 6
    v = index(rows)
    assert v[(2022, 4, "職業計", INCL, "job_openings")] == 2183059.0
    assert v[(2022, 4, "職業計", INCL, "job_seekers")] == 2051303.0
    assert v[(2022, 4, "職業計", INCL, "openings_to_seekers")] == 1.06
    assert v[(2023, 5, "介護サービス職業従事者", PT, "openings_to_seekers")] == 4.09
    assert v[(2022, 12, "保健師，助産師，看護師", EXCL, "openings_to_seekers")] == 2.86
    # annual / fiscal-year average columns are not months and must be dropped
    assert {r["month"] for r in rows} == set(range(1, 13))
    assert rows == sorted(
        rows,
        key=lambda r: (r["year"], r["month"], r["employment_type"], r["occupation"], r["metric"]),
    )


def test_parse_xls_reads_wareki_headers_and_strips_fullwidth_indent() -> None:
    rows = jobs.parse(XLS, jobs.FILE_2012)
    assert {r["classification"] for r in rows} == {"jp_mhlw2011"}
    assert {r["occupation"] for r in rows} == {
        "職業計",
        "保健師、助産師、看護師",
        "介護サービスの職業",
    }
    # 平成31年1月 .. 令和2年3月 = 15 months, no 元年計 / 年度計 columns
    assert sorted({(r["year"], r["month"]) for r in rows}) == [
        *[(2019, m) for m in range(1, 13)],
        (2020, 1),
        (2020, 2),
        (2020, 3),
    ]
    v = index(rows)
    assert v[(2019, 5, "介護サービスの職業", INCL, "openings_to_seekers")] == 4.02
    assert v[(2019, 1, "職業計", INCL, "job_openings")] == 2446881.0
    assert v[(2020, 3, "職業計", INCL, "openings_to_seekers")] == 1.3


def test_parse_skips_blank_rows_with_none_label() -> None:
    # the real ratio sheets contain an empty row (label None, all cells None) above the notes
    grids = copy.deepcopy(jobs.read_grids(XLSX, jobs.FILE_2022.layout))
    width = len(grids[6][5])
    grids[6].insert(8, [None] * width)
    rows = jobs.grids_to_rows(grids, jobs.FILE_2022)
    assert {r["occupation"] for r in rows} == {
        "職業計",
        "保健師，助産師，看護師",
        "介護サービス職業従事者",
    }
    assert jobs.normalize_name(None) == ""
    assert jobs.normalize_name("　介護関係職種（※）") == "介護関係職種"


def test_parse_maps_dash_cells_to_none() -> None:
    grids = jobs.read_grids(XLSX, jobs.FILE_2022.layout)
    grids = copy.deepcopy(grids)
    # sheet 0 = 新規求人（パート含む常用）, row 7 = 介護サービス, col 3 = 2022-04
    grids[0][7][3] = "-"
    rows = jobs.grids_to_rows(grids, jobs.FILE_2022)
    assert index(rows)[(2022, 4, "介護サービス職業従事者", INCL, "new_openings")] is None


def test_parse_fails_closed_when_total_ratio_does_not_equal_openings_over_seekers() -> None:
    grids = copy.deepcopy(jobs.read_grids(XLSX, jobs.FILE_2022.layout))
    # sheet 6 = 有効求人倍率（パート含む常用）, row 5 = 職業計, col 3 = 2022-04 (1.06 -> 1.07)
    grids[6][5][3] = 1.07
    with pytest.raises(ValueError, match="職業計.*2022-04"):
        jobs.grids_to_rows(grids, jobs.FILE_2022)


def test_parse_fails_closed_on_unexpected_cell_and_non_monotonic_months() -> None:
    grids = copy.deepcopy(jobs.read_grids(XLSX, jobs.FILE_2022.layout))
    grids[0][7][3] = "n.a."
    with pytest.raises(ValueError, match="n.a."):
        jobs.grids_to_rows(grids, jobs.FILE_2022)
    grids = copy.deepcopy(jobs.read_grids(XLS, jobs.FILE_2012.layout))
    grids[0][2][5] = "30年2月"  # 31年1月 followed by 30年2月
    with pytest.raises(ValueError, match="monotonic"):
        jobs.grids_to_rows(grids, jobs.FILE_2012)


def test_parse_rejects_payload_that_is_not_a_workbook() -> None:
    with pytest.raises(ValueError, match="workbook"):
        jobs.parse(jobs.FILE_2022.magic + b"garbage", jobs.FILE_2022)
    with pytest.raises(ValueError, match="workbook"):
        jobs.parse(jobs.FILE_2012.magic + b"garbage", jobs.FILE_2012)


def test_wareki_month_headers_switch_era_at_gannen() -> None:
    assert jobs.wareki_months(["31年1月", "2月", "4月", "元年5月", "12月", "2年1月"]) == [
        (2019, 1),
        (2019, 2),
        (2019, 4),
        (2019, 5),
        (2019, 12),
        (2020, 1),
    ]
    assert jobs.wareki_months(["24年3月", "4月"]) == [(2012, 3), (2012, 4)]


# ---- stage


def test_stage_reports_missing_raw_per_file_and_writes_nothing() -> None:
    ctx = make_ctx()
    written, skipped = jobs.stage(ctx, [], [])
    assert written == []
    assert skipped == [f"{f.raw_name}: no raw" for f in jobs.FILES]
    assert ctx.tables.list_tables() == []


def test_stage_writes_one_staged_table_per_file() -> None:
    ctx = make_ctx(full_responses())
    jobs.fetch(ctx, [], [])
    written, skipped = jobs.stage(ctx, [], [])
    assert skipped == []
    assert written == [
        "staged/jobs/occupation_indicators_from2012_03",
        "staged/jobs/occupation_indicators_from2022_04",
    ]
    assert len(ctx.tables.read_table(written[1])) == 3 * 14 * 3 * 6


# ---- mart


def test_mart_skips_when_no_staged_table_exists() -> None:
    ctx = make_ctx()
    written, skipped = jobs.mart(ctx, [], [])
    assert written == []
    assert skipped == [f"{f.staged_table}: no staged table" for f in jobs.FILES]
    assert ctx.tables.list_tables() == []


def test_mart_concatenates_months_and_averages_calendar_years() -> None:
    ctx = make_ctx(full_responses())
    jobs.fetch(ctx, [], [])
    jobs.stage(ctx, [], [])
    written, skipped = jobs.mart(ctx, [], [])
    assert skipped == []
    assert written == [jobs.MONTHLY_TABLE, jobs.ANNUAL_TABLE]

    monthly = ctx.tables.read_table(jobs.MONTHLY_TABLE)
    assert len(monthly) == 3 * (15 + 14) * 3 * 6
    assert {r["iso3"] for r in monthly} == {"JPN"}
    assert {r["source"] for r in monthly} == {"mhlw_jobs"}
    assert list(monthly[0]) == [
        "iso3",
        "year",
        "month",
        "classification",
        "occupation",
        "employment_type",
        "metric",
        "value",
        "source",
    ]
    assert monthly[0]["year"] == 2019 and monthly[-1]["year"] == 2023

    annual = ctx.tables.read_table(jobs.ANNUAL_TABLE)
    assert list(annual[0]) == [
        "iso3",
        "year",
        "classification",
        "occupation",
        "employment_type",
        "openings_to_seekers_mean",
        "job_openings_mean",
        "job_seekers_mean",
        "n_months",
        "source",
    ]
    by = {
        (r["year"], r["classification"], r["occupation"], r["employment_type"]): r for r in annual
    }
    # partial years are kept and flagged through n_months
    assert by[(2019, "jp_mhlw2011", "職業計", INCL)]["n_months"] == 12
    assert by[(2020, "jp_mhlw2011", "職業計", INCL)]["n_months"] == 3
    assert by[(2022, "jp_jsoc2009", "職業計", INCL)]["n_months"] == 9
    care = by[(2023, "jp_jsoc2009", "介護サービス職業従事者", INCL)]
    assert care["n_months"] == 5
    assert care["openings_to_seekers_mean"] == pytest.approx((3.82 + 3.58 + 3.43 + 3.38 + 3.54) / 5)
    assert care["job_openings_mean"] == pytest.approx(
        (205999 + 201404 + 203202 + 201757 + 206557) / 5
    )
    assert len(annual) == (2 + 2) * 3 * 3
    assert annual == sorted(
        annual,
        key=lambda r: (r["year"], r["classification"], r["employment_type"], r["occupation"]),
    )


def test_build_monthly_rejects_duplicate_keys() -> None:
    rows = jobs.parse(XLSX, jobs.FILE_2022)
    with pytest.raises(ValueError, match="duplicate"):
        jobs.build_monthly([rows, rows])


def test_build_annual_ignores_none_and_counts_months_with_a_ratio() -> None:
    base = {
        "iso3": "JPN",
        "classification": "jp_jsoc2009",
        "occupation": "職業計",
        "employment_type": INCL,
        "source": "mhlw_jobs",
    }
    monthly = [
        {**base, "year": 2024, "month": 1, "metric": "openings_to_seekers", "value": 1.0},
        {**base, "year": 2024, "month": 1, "metric": "job_openings", "value": 10.0},
        {**base, "year": 2024, "month": 1, "metric": "job_seekers", "value": 10.0},
        {**base, "year": 2024, "month": 2, "metric": "openings_to_seekers", "value": None},
        {**base, "year": 2024, "month": 2, "metric": "job_openings", "value": 30.0},
        {**base, "year": 2024, "month": 2, "metric": "job_seekers", "value": None},
    ]
    (row,) = jobs.build_annual(monthly)
    assert row["n_months"] == 1
    assert row["openings_to_seekers_mean"] == 1.0
    assert row["job_openings_mean"] == 20.0
    assert row["job_seekers_mean"] == 10.0
