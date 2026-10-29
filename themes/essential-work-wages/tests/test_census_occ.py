"""令和 2 年国勢調査 抽出詳細集計 第 10 表（職業小分類 × 男女、全国）: fetch -> stage -> mart."""

from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import census_occ
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
# Rows 0-11 (headers) + per sex: the 総数 row, major A (all middle/minor rows) and major L, cut
# from the real file. The 総数 row's counts were recomputed as the sum of the kept minor rows so
# that the national check holds on the cut (see scratch builder; everything else is verbatim).
XLSX = (FIXTURES / "census2020_occupation_sex_cut.xlsx").read_bytes()

HEADER = [
    [
        "地域識別コード",
        "地域名",
        "男女",
        "階層レベル（職業）",
        "職業（大分類）",
        "職業（中分類）",
        "職業",
        " ",
    ],
]


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def row(sex: str, level: str, major: str, middle: str, occ: str, total: object) -> list[object]:
    return ["a", "00000_全国", sex, level, major, middle, occ, total, "-", "-"]


def small_rows() -> list[list[object]]:
    """A consistent 3-sex grid: one major A with one middle 01 and two minors."""
    out: list[list[object]] = [list(h) for h in HEADER]
    for sex, a, b in (("0_総数", 100, 300), ("1_男", 40, 100), ("2_女", 60, 200)):
        out += [
            row(sex, "1", "-", "-", "0_総数", a + b),
            row(sex, "1", "A_管理的職業従事者", "-", "A_管理的職業従事者", a + b),
            row(sex, "2", "A_管理的職業従事者", "01_管理的公務員", "01_管理的公務員", a + b),
            row(sex, "3", "A_管理的職業従事者", "01_管理的公務員", "01a_管理的公務員", a),
            row(sex, "3", "A_管理的職業従事者", "01_管理的公務員", "01b_その他", b),
        ]
    # A prefecture block must be ignored even though it comes with the same codes.
    out.append(["a", "01000_北海道", "0_総数", "1", "-", "-", "0_総数", 999999, "-", "-"])
    return out


# ---- constants


def test_constants_point_at_the_estat_table_10_xlsx() -> None:
    assert census_occ.SOURCE == "estat_census2020"
    assert "政府標準利用規約" in census_occ.LICENSE
    assert census_occ.STAT_INF_ID == "000032266822"
    assert census_occ.URL.endswith("statInfId=000032266822&fileKind=0")
    assert census_occ.RAW_NAME.endswith(".xlsx")
    assert XLSX.startswith(census_occ.MAGIC)
    assert census_occ.CENSUS_YEAR == 2020


# ---- fetch


def test_fetch_puts_the_workbook_in_raw_with_a_manifest_row() -> None:
    ctx = make_ctx({census_occ.URL: XLSX})
    written, skipped = census_occ.fetch(ctx, [], [])
    assert skipped == []
    recs = ctx.raw.records()
    assert len(recs) == 1
    assert recs[0].theme == THEME
    assert recs[0].source == census_occ.SOURCE
    assert recs[0].name == census_occ.RAW_NAME
    assert recs[0].url == census_occ.URL
    assert recs[0].license == census_occ.LICENSE
    assert written == [recs[0].relative_path]
    assert ctx.raw.get(theme=THEME, source=census_occ.SOURCE, name=census_occ.RAW_NAME) == XLSX


def test_fetch_rejects_a_non_xlsx_payload_and_records_a_fetch_error() -> None:
    ctx = make_ctx({census_occ.URL: b"<html>maintenance</html>"})
    written, skipped = census_occ.fetch(ctx, [], [])
    assert written == []
    assert skipped == [f"{census_occ.RAW_NAME}: non-xlsx payload"]
    assert ctx.raw.records() == []

    ctx = make_ctx({})
    written, skipped = census_occ.fetch(ctx, [], [])
    assert written == []
    assert len(skipped) == 1 and skipped[0].startswith(f"{census_occ.RAW_NAME}: ")
    assert ctx.raw.records() == []


# ---- parse (pure)


def test_parse_returns_one_row_per_occupation_with_sex_counts() -> None:
    out = census_occ.parse(small_rows())
    assert [(r["occupation_code"], r["level"]) for r in out] == [
        ("A", "major"),
        ("01", "middle"),
        ("01a", "minor"),
        ("01b", "minor"),
    ]
    minor = next(r for r in out if r["occupation_code"] == "01a")
    assert minor == {
        "occupation_code": "01a",
        "occupation": "管理的公務員",
        "level": "minor",
        "workers_total": 100.0,
        "workers_male": 40.0,
        "workers_female": 60.0,
    }
    major = out[0]
    assert (major["occupation"], major["workers_total"]) == ("管理的職業従事者", 400.0)


def test_parse_maps_dash_to_none() -> None:
    rows = small_rows()
    # the minor 01b for women becomes '-'
    for r in rows:
        if r[2] == "2_女" and r[6] == "01b_その他":
            r[7] = "-"
        if r[2] == "2_女" and r[6] in ("0_総数", "A_管理的職業従事者", "01_管理的公務員"):
            r[7] = 60
    out = census_occ.parse(rows)
    assert next(r for r in out if r["occupation_code"] == "01b")["workers_female"] is None


def test_parse_rejects_a_total_that_does_not_match_the_sum_of_minors() -> None:
    rows = small_rows()
    rows[1][7] = 500  # 総数 for 0_総数 (true sum 400 -> off by 25%)
    with pytest.raises(ValueError, match="sum of minor"):
        census_occ.parse(rows)


def test_parse_rejects_a_missing_sex_block() -> None:
    rows = [r for r in small_rows() if r[2] != "2_女"]
    with pytest.raises(ValueError, match="2_女"):
        census_occ.parse(rows)


def test_parse_rejects_an_empty_or_foreign_sheet() -> None:
    with pytest.raises(ValueError, match="national"):
        census_occ.parse(HEADER)


def test_parse_on_the_real_cut_keeps_the_hierarchy_and_names() -> None:
    out = census_occ.parse(census_occ.workbook_rows(XLSX))
    codes = [r["occupation_code"] for r in out]
    assert codes == ["A", "01", "01a", "02", "021", "02a", "03", "03a", "049", "L", "99", "999"]
    company = next(r for r in out if r["occupation_code"] == "021")
    assert company["occupation"] == "会社役員"
    assert company["workers_total"] == 913490.0
    assert company["workers_male"] == 767880.0
    unclass = next(r for r in out if r["occupation_code"] == "999")
    assert (unclass["workers_total"], unclass["workers_female"]) == (1638490.0, 766820.0)


def test_workbook_rows_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="xlsx"):
        census_occ.workbook_rows(b"PK\x03\x04 but not a zip")


# ---- stage / mart (state)


def test_stage_writes_the_staged_table_from_raw() -> None:
    ctx = make_ctx({census_occ.URL: XLSX})
    census_occ.fetch(ctx, [], [])
    written, skipped = census_occ.stage(ctx, [], [])
    assert skipped == []
    assert written == [census_occ.STAGED_TABLE]
    rows = ctx.tables.read_table(census_occ.STAGED_TABLE)
    assert len(rows) == 12
    assert rows[0]["occupation_code"] == "A"


def test_stage_skips_when_raw_is_missing() -> None:
    ctx = make_ctx()
    written, skipped = census_occ.stage(ctx, [], [])
    assert written == []
    assert skipped == [f"{census_occ.RAW_NAME}: no raw"]
    assert ctx.tables.list_tables() == []


def test_mart_adds_keys_and_female_share() -> None:
    ctx = make_ctx({census_occ.URL: XLSX})
    census_occ.fetch(ctx, [], [])
    census_occ.stage(ctx, [], [])
    written, skipped = census_occ.mart(ctx, [], [])
    assert skipped == []
    assert written == [census_occ.MART_TABLE]
    rows = ctx.tables.read_table(census_occ.MART_TABLE)
    assert len(rows) == 12
    r = next(r for r in rows if r["occupation_code"] == "021")
    assert r["iso3"] == "JPN"
    assert r["year"] == 2020
    assert r["source"] == census_occ.SOURCE
    assert r["classification"] == census_occ.CLASSIFICATION
    # counts are rounded to tens independently, so male + female != total; share uses female/total
    assert r["workers_female"] == 145620.0
    assert r["female_share"] == pytest.approx(145620 / 913490)
    assert list(r) == [
        "iso3",
        "year",
        "occupation_code",
        "occupation",
        "level",
        "classification",
        "workers_total",
        "workers_male",
        "workers_female",
        "female_share",
        "source",
    ]
    # majors first, then middles, then minors; code order inside each level
    levels = [str(r["level"]) for r in rows]
    assert levels == sorted(levels, key=["major", "middle", "minor"].index)


def test_mart_skips_when_staged_is_missing() -> None:
    ctx = make_ctx()
    written, skipped = census_occ.mart(ctx, [], [])
    assert written == []
    assert skipped == [f"{census_occ.STAGED_TABLE}: no staged table"]


def test_build_mart_female_share_is_none_without_a_total_and_duplicates_fail() -> None:
    staged: list[dict[str, object]] = [
        {
            "occupation_code": "01a",
            "occupation": "x",
            "level": "minor",
            "workers_total": None,
            "workers_male": None,
            "workers_female": None,
        }
    ]
    assert census_occ.build_mart(staged)[0]["female_share"] is None
    with pytest.raises(ValueError, match="duplicate"):
        census_occ.build_mart(staged + [dict(staged[0])])
