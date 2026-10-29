"""労働争議統計調査 第 2 表（産業別 争議件数・参加人員・労働損失日数）: fetch -> stage -> mart."""

from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import disputes
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
# 2024 file: header rows 0-8, the 20 major-industry rows, one middle row (09 食料品製造業) and
# the note rows, all verbatim.
XLSX = (FIXTURES / "disputes_2024_industry_cut.xlsx").read_bytes()


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def major(code: str, name: str, *vals: object) -> list[object]:
    return [code, None, name, None, None, *vals]


def small_rows(total_row: list[object] | None = None) -> list[list[object]]:
    """20 majors (A..T) with numbers only in 3 of them; the rest are '-'. 2012-style strings."""
    dash = ["-"] * 22
    rows: list[list[object]] = [[None] * 27 for _ in range(8)]
    rows.append(
        total_row
        or [
            "全産業",
            None,
            None,
            None,
            None,
            "596",
            "125,992",
            "517",
            "75,802",
            "79",
            "50,190",
            "12,361",
            "38",
            "1,233",
            "3,839",
        ]
    )
    letters = "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴ"
    for code in letters:
        if code == "Ｅ":
            rows.append(
                major(
                    "Ｅ",
                    "製造業",
                    "500",
                    "100,000",
                    "450",
                    "60,000",
                    "50",
                    "40,000",
                    "10,000",
                    "30",
                    "1,000",
                    "3,000",
                )
            )
            rows.append(
                [
                    None,
                    None,
                    "09",
                    "食料品製造業",
                    None,
                    "4",
                    "3,571",
                    "3",
                    "3,570",
                    "1",
                    "1",
                    "1",
                    "-",
                    "-",
                    "-",
                ]
            )
        elif code == "Ｐ":
            rows.append(
                major(
                    "Ｐ",
                    "医療，福祉",
                    "95",
                    "25,992",
                    "67",
                    "15,802",
                    "28",
                    "10,190",
                    "2,361",
                    "8",
                    "233",
                    "839",
                )
            )
        elif code == "Ｔ":
            rows.append(
                major("Ｔ", "分類不能の産業", "1", "0", "-", "-", "1", "0", "0", "-", "-", "-")
            )
        else:
            rows.append(major(code, f"産業{code}", *dash))
    rows.append(["注： 1)  争議行為を伴う争議で", None])
    return rows


# ---- constants


def test_one_table_per_year_2012_to_2024() -> None:
    assert disputes.SOURCE == "mhlw_disputes"
    assert "政府標準利用規約" in disputes.LICENSE
    assert sorted(disputes.TABLES) == list(range(2012, 2025))
    assert disputes.TABLES[2024] == ("000040372369", 4)
    assert disputes.TABLES[2012] == ("000023598519", 0)
    assert disputes.url(2024).endswith("statInfId=000040372369&fileKind=4")
    assert disputes.url(2019).endswith("statInfId=000032018193&fileKind=0")
    assert disputes.raw_name(2024) == "disputes_2024_industry.xlsx"
    assert XLSX.startswith(disputes.MAGIC)


# ---- fetch


def test_fetch_puts_every_year_in_raw_and_skips_errors_and_non_xlsx() -> None:
    responses = {disputes.url(y): XLSX for y in disputes.TABLES}
    del responses[disputes.url(2013)]
    responses[disputes.url(2014)] = b"<html>"
    ctx = make_ctx(responses)
    written, skipped = disputes.fetch(ctx, [], [])
    recs = ctx.raw.records()
    assert [r.name for r in recs] == [
        disputes.raw_name(y) for y in range(2012, 2025) if y not in (2013, 2014)
    ]
    assert written == [r.relative_path for r in recs]
    assert all(r.theme == THEME and r.source == disputes.SOURCE for r in recs)
    assert recs[0].url == disputes.url(2012)
    assert recs[0].license == disputes.LICENSE
    assert skipped[0].startswith(f"{disputes.raw_name(2013)}: ")
    assert skipped[1] == f"{disputes.raw_name(2014)}: non-xlsx payload"
    assert len(skipped) == 2


# ---- parse (pure)


def test_parse_reads_the_major_rows_and_the_total() -> None:
    out = disputes.parse(small_rows(), 2012)
    assert len(out) == 21
    assert out[0] == {
        "year": 2012,
        "industry_code": "ALL",
        "industry": "全産業",
        "disputes_total": 596.0,
        "participants_total": 125992.0,
        "disputes_with_action": 79.0,
        "participants": 12361.0,
        "days_lost": 3839.0,
    }
    p = next(r for r in out if r["industry_code"] == "P")
    assert p["industry"] == "医療，福祉"
    assert (p["disputes_total"], p["disputes_with_action"]) == (95.0, 28.0)
    assert (p["participants"], p["days_lost"]) == (2361.0, 839.0)
    a = next(r for r in out if r["industry_code"] == "A")
    assert a["disputes_total"] is None and a["days_lost"] is None
    # the middle row 09 is not a major and is dropped
    assert all(r["industry"] != "食料品製造業" for r in out)


def test_parse_rejects_totals_that_do_not_add_up() -> None:
    bad = [
        "全産業",
        None,
        None,
        None,
        None,
        "597",
        "125,992",
        "517",
        "75,802",
        "79",
        "50,190",
        "12,361",
        "38",
        "1,233",
        "3,839",
    ]
    with pytest.raises(ValueError, match="disputes_total"):
        disputes.parse(small_rows(list(bad)), 2012)


def test_parse_rejects_missing_majors_or_total() -> None:
    rows = [r for r in small_rows() if r[0] != "Ｐ"]
    with pytest.raises(ValueError, match="20 major"):
        disputes.parse(rows, 2012)
    rows = [r for r in small_rows() if r[0] != "全産業"]
    with pytest.raises(ValueError, match="全産業"):
        disputes.parse(rows, 2012)


def test_parse_on_the_real_2024_cut() -> None:
    out = disputes.parse(disputes.workbook_rows(XLSX), 2024)
    assert [r["industry_code"] for r in out] == ["ALL", *"ABCDEFGHIJKLMNOPQRST"]
    total = out[0]
    assert (total["disputes_total"], total["disputes_with_action"]) == (278.0, 76.0)
    assert (total["participants"], total["days_lost"]) == (8982.0, 2501.0)
    p = next(r for r in out if r["industry_code"] == "P")
    assert p["industry"] == "医療，福祉"
    assert (p["disputes_total"], p["participants"], p["days_lost"]) == (80.0, 6459.0, 411.0)
    assert (
        next(r for r in out if r["industry_code"] == "L")["industry"]
        == "学術研究，専門･技術サービス業"
    )


def test_workbook_rows_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="xlsx"):
        disputes.workbook_rows(b"PK\x03\x04nope")


# ---- stage / mart (state)


def test_stage_writes_one_staged_table_per_year_present_in_raw() -> None:
    ctx = make_ctx({disputes.url(2024): XLSX, disputes.url(2023): XLSX})
    disputes.fetch(ctx, [], [])
    written, skipped = disputes.stage(ctx, [], [])
    assert written == [disputes.staged_table(2023), disputes.staged_table(2024)]
    assert skipped == [f"{disputes.raw_name(y)}: no raw" for y in range(2012, 2023)]
    rows = ctx.tables.read_table(disputes.staged_table(2023))
    assert len(rows) == 21 and rows[0]["year"] == 2023


def test_mart_concatenates_years_and_adds_keys() -> None:
    ctx = make_ctx({disputes.url(2024): XLSX, disputes.url(2023): XLSX})
    disputes.fetch(ctx, [], [])
    disputes.stage(ctx, [], [])
    written, skipped = disputes.mart(ctx, [], [])
    assert written == [disputes.MART_TABLE]
    assert skipped == []
    rows = ctx.tables.read_table(disputes.MART_TABLE)
    assert len(rows) == 42
    assert [(r["year"], r["industry_code"]) for r in rows[:3]] == [
        (2023, "A"),
        (2023, "ALL"),
        (2023, "B"),
    ]
    r = rows[0]
    assert r["iso3"] == "JPN" and r["source"] == disputes.SOURCE
    assert list(r) == [
        "iso3",
        "year",
        "industry_code",
        "industry",
        "disputes_total",
        "participants_total",
        "disputes_with_action",
        "participants",
        "days_lost",
        "source",
    ]


def test_mart_skips_when_no_staged_table_exists() -> None:
    ctx = make_ctx()
    written, skipped = disputes.mart(ctx, [], [])
    assert written == []
    assert skipped == [f"{disputes.SOURCE}: no staged table"]
    assert ctx.tables.list_tables() == []


def test_build_mart_rejects_duplicate_year_industry() -> None:
    row: dict[str, object] = {"year": 2024, "industry_code": "P", "industry": "医療，福祉"}
    with pytest.raises(ValueError, match="duplicate"):
        disputes.build_mart([row, dict(row)])
