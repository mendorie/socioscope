"""財務省 法人企業統計 年次別調査 統計表 2（業種別・規模別 損益表）:
fetch → stage → mart の状態検証と純粋変換のテスト。"""

from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import hojin as mod
from theme_essential_work_wages.pipeline import THEME

FIXTURE = Path(__file__).parent / "fixtures" / "hojin_t2_sample.xlsx"
SIZES = ("総　　額", "10未満", "10～50未満", "50～100未満", "100～1,000未満", "1,000以上")
Rows = list[list[object]]


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def sheet(
    title: str, sales: float, profit: float, va: float, emp: float, *, wages: float = 10.0
) -> tuple[str, Rows]:
    """実表と同じ並び（列 1〜6 に項目名、列 7 に総額、列 8〜12 に資本金階級）の最小シート。"""

    def row(label: str, depth: int, total: float) -> list[object]:
        cells: list[object] = [None] * 13
        cells[depth] = label
        cells[7] = total
        for j in range(8, 13):  # 各階級は総額の 1/5（検算は総額列のみ）
            cells[j] = total / 5
        return cells

    header: list[object] = [None, "資　　本　　金　　別", None, None, None, None, None, *SIZES]
    rows: Rows = [
        ["２．業種別，規模別資産・負債・純資産及び損益表"] + [None] * 12,
        [title] + [None] * 12,
        [None] * 12 + ["（単位：百万円）"],
        header,
        row("母　　集　　団（社）", 1, 100),
        row("流動資産", 1, 999),
        row("売上高", 1, sales),
        row("営業利益", 1, profit),
        row("付加価値額", 1, va),
        row("役員給与", 2, wages),
        row("役員賞与", 2, 1.0),
        row("従業員給与", 2, 5.0),
        row("従業員賞与", 2, 2.0),
        row("福利厚生費", 2, 2.0),
        row("営業純益", 2, 3.0),
        row("役　 　 員 　　 数 （人）", 2, 7),
        row("従　 業 　員 　数 （人）", 2, emp),
    ]
    return (title, rows)


def sample_sheets() -> list[tuple[str, Rows]]:
    return [
        sheet("全産業", 1000.0, 50.0, 300.0, 40.0),
        sheet("製造業", 400.0, 20.0, 100.0, 10.0),
        sheet("食料品製造業", 100.0, 5.0, 30.0, 4.0),
        sheet("非製造業", 600.0, 30.0, 200.0, 30.0),
        sheet("医療、福祉業", 50.0, 1.0, 40.0, 10.0),
        # 以降は金融・保険（別様式: 売上高・付加価値額が無い）。読まない。
        ("全産業（金融業、保険業を含む）", [["２．（続）"], ["全産業（金融業、保険業を含む）"]]),
        (
            "銀行業",
            [["２．（続）"], ["銀行業"], [None, "経常収益", None, None, None, None, None, 1]],
        ),
    ]


# ---- 定数・契約


def test_module_exposes_the_source_contract() -> None:
    assert mod.SOURCE == "mof_hojin"
    assert "政府標準利用規約" in mod.LICENSE
    assert mod.MAGIC == (b"PK", b"\xd0\xcf\x11\xe0")
    assert sorted(mod.STAT_INF_IDS) == list(range(2012, 2023))
    assert mod.STAT_INF_IDS[2022] == "000040172276"
    assert mod.url(2022) == (
        "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040172276&fileKind=0"
    )
    assert mod.raw_name(2022) == "hojin_t2_fy2022.xls"


# ---- parse（純粋変換）


def test_parse_reads_each_industry_sheet_into_long_rows_per_size_class() -> None:
    rows = mod.parse(sample_sheets(), 2022)
    assert len(rows) == 5 * 6
    all_row = next(r for r in rows if r["industry"] == "全産業" and r["size_class"] == "all")
    assert all_row == {
        "fiscal_year": 2022,
        "industry": "全産業",
        "industry_code": "ALL_EXFIN",
        "industry_level": "total",
        "parent_code": None,
        "size_class": "all",
        "sales_mn_yen": 1000.0,
        "operating_profit_mn_yen": 50.0,
        # 役員給与 10 + 役員賞与 1 + 従業員給与 5 + 従業員賞与 2 + 福利厚生費 2
        "personnel_cost_mn_yen": 20.0,
        "value_added_mn_yen": 300.0,
        "employees": 40,
    }
    med = next(r for r in rows if r["industry"] == "医療、福祉業" and r["size_class"] == "ge_1000")
    assert med["industry_code"] == "P" and med["parent_code"] == "SVC"
    assert med["industry_level"] == "major" and med["sales_mn_yen"] == 10.0
    food = next(r for r in rows if r["industry_code"] == "E01")
    assert food["industry"] == "食料品製造業" and food["parent_code"] == "E"
    assert food["industry_level"] == "minor"
    assert [r["size_class"] for r in rows[:6]] == [
        "all",
        "lt_10",
        "10_50",
        "50_100",
        "100_1000",
        "ge_1000",
    ]


def test_parse_normalises_sheet_name_variants_and_dash_as_missing() -> None:
    sheets = sample_sheets()
    gas = sheet("ガス・熱供給水道業", 10.0, 1.0, 3.0, 1.0)  # FY2012 の表記ゆれ
    gas[1][7][7] = "－"  # 営業利益 総額
    gas[1][7][8] = "△ 30,070"  # FY2013 までの負数表記（△ ＝ マイナス、桁区切り付き文字列）
    sheets.insert(5, gas)
    rows = mod.parse(sheets, 2012)
    g = next(r for r in rows if r["industry_code"] == "F2" and r["size_class"] == "all")
    assert g["industry"] == "ガス・熱供給・水道業"
    assert g["operating_profit_mn_yen"] is None
    g10 = next(r for r in rows if r["industry_code"] == "F2" and r["size_class"] == "lt_10")
    assert g10["operating_profit_mn_yen"] == -30070.0


def test_parse_rejects_when_all_industries_differ_from_manufacturing_plus_non_manufacturing() -> (
    None
):
    sheets = sample_sheets()
    sheets[0] = sheet("全産業", 1010.0, 50.0, 300.0, 40.0)  # 1.0% ずれ
    with pytest.raises(ValueError, match="sales_mn_yen"):
        mod.parse(sheets, 2022)
    sheets[0] = sheet("全産業", 1004.0, 50.0, 300.0, 40.0)  # 0.4% は許容
    assert mod.parse(sheets, 2022)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda s: s.pop(3), "非製造業"),  # 検算に要るシートが無い
        (lambda s: s.insert(1, sheet("謎の産業", 1.0, 1.0, 1.0, 1.0)), "unknown sheet"),
        (lambda s: s[1][1].pop(6), "売上高"),  # 項目行が無い
        (lambda s: s[1][1].pop(3), "size header"),
        (lambda s: s[1][1][6].__setitem__(7, "n/a"), "not a number"),
        (lambda s: s.clear(), "no sheet"),
    ],
)
def test_parse_fails_closed_on_unexpected_layout(mutate, match: str) -> None:  # type: ignore[no-untyped-def]
    sheets = sample_sheets()
    mutate(sheets)
    with pytest.raises(ValueError, match=match):
        mod.parse(sheets, 2022)


def test_workbook_rows_reads_xlsx_fixture_and_rejects_garbage() -> None:
    sheets = mod.workbook_rows(FIXTURE.read_bytes())
    assert [name for name, _ in sheets][:3] == ["全産業", "製造業", "食料品製造業"]
    rows = mod.parse(sheets, 2022)
    assert len(rows) == 5 * 6
    with pytest.raises(ValueError, match="xls"):
        mod.workbook_rows(b"PK\x03\x04 not really a workbook")


# ---- build_mart（純粋変換）


def test_build_mart_adds_keys_ratios_and_rejects_duplicates() -> None:
    staged = mod.parse(sample_sheets(), 2022) + mod.parse(sample_sheets(), 2021)
    out = mod.build_mart(staged)
    assert len(out) == 60
    assert [r["fiscal_year"] for r in out[:1]] == [2021]  # 年度 → 産業コード → 規模 の順
    r = next(r for r in out if r["fiscal_year"] == 2022 and r["industry_code"] == "ALL_EXFIN")
    assert r["iso3"] == "JPN" and r["year"] == 2022 and r["source"] == "mof_hojin"
    assert r["value_added_per_employee_mn_yen"] == pytest.approx(300.0 / 40)
    assert r["operating_margin_pct"] == pytest.approx(5.0)
    with pytest.raises(ValueError, match="duplicate"):
        mod.build_mart(staged + staged[:1])


def test_build_mart_leaves_ratios_none_when_denominator_missing() -> None:
    staged = mod.parse(sample_sheets(), 2022)
    assert (staged[0]["industry_code"], staged[0]["size_class"]) == ("ALL_EXFIN", "all")
    staged[0]["employees"] = 0
    staged[0]["sales_mn_yen"] = None
    r = next(
        r
        for r in mod.build_mart(staged)
        if r["industry_code"] == "ALL_EXFIN" and r["size_class"] == "all"
    )
    assert r["value_added_per_employee_mn_yen"] is None
    assert r["operating_margin_pct"] is None


# ---- fetch / stage / mart（状態検証）


def test_fetch_writes_one_raw_per_fiscal_year_and_skips_failures_and_non_excel() -> None:
    payload = FIXTURE.read_bytes()
    responses = {mod.url(fy): payload for fy in mod.STAT_INF_IDS}
    responses[mod.url(2013)] = b"<html>error</html>"
    del responses[mod.url(2014)]
    ctx = make_ctx(responses)
    written, skipped = mod.fetch(ctx, [], [])
    assert len(written) == len(mod.STAT_INF_IDS) - 2
    assert written[0] == f"{THEME}/mof_hojin/hojin_t2_fy2012.xls"
    assert skipped == [
        "hojin_t2_fy2013.xls: non-Excel payload",
        f"hojin_t2_fy2014.xls: no fake response for {mod.url(2014)}",
    ]
    recs = ctx.raw.records()
    assert all(r.license == mod.LICENSE and r.source == "mof_hojin" for r in recs)
    assert ctx.fetcher.requested == [mod.url(fy) for fy in sorted(mod.STAT_INF_IDS)]


def test_stage_without_raw_skips_and_writes_nothing() -> None:
    ctx = make_ctx()
    written, skipped = mod.stage(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.raw_name(fy)}: no raw" for fy in sorted(mod.STAT_INF_IDS)]
    assert ctx.tables.list_tables() == []


def test_mart_without_any_staged_table_skips() -> None:
    ctx = make_ctx()
    written, skipped = mod.mart(ctx, [], [])
    assert written == []
    assert skipped == [f"{mod.MART_TABLE}: no staged table"]
    assert ctx.tables.list_tables() == []


def test_fetch_stage_mart_end_to_end_with_partial_years() -> None:
    payload = FIXTURE.read_bytes()
    ctx = make_ctx({mod.url(2021): payload, mod.url(2022): payload})
    mod.fetch(ctx, [], [])
    written, skipped = mod.stage(ctx, [], [])
    assert written == ["staged/mof_hojin/hojin_t2_fy2021", "staged/mof_hojin/hojin_t2_fy2022"]
    assert len(skipped) == len(mod.STAT_INF_IDS) - 2
    staged = ctx.tables.read_table("staged/mof_hojin/hojin_t2_fy2021")
    assert {r["fiscal_year"] for r in staged} == {2021}

    written, skipped = mod.mart(ctx, [], [])
    assert written == [mod.MART_TABLE]
    assert skipped == []
    mart = ctx.tables.read_table(mod.MART_TABLE)
    assert len(mart) == 60
    assert {r["year"] for r in mart} == {2021, 2022}
    assert {r["iso3"] for r in mart} == {"JPN"} and {r["source"] for r in mart} == {"mof_hojin"}
