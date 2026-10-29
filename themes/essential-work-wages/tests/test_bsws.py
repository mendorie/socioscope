"""賃金構造基本統計調査（e-Stat）職種別賃金: fetch / parse / stage / mart の状態検証。

fixture は実ファイルを切り詰めたもの:
- ``bsws_2025_occupation.xlsx``: 新形式（145 職種）の先頭 10 職種 ＋ 看護助手
  （ページ送りで性別接頭辞が再掲される行）＋ 不詳（'-' を含む行）× 3 性別ブロック。
- ``bsws_2019_grid.json`` / ``bsws_2009_grid.json``: 旧形式（129 職種）のセル格子
  （xls は書き出せないので xlrd で読んだ行リストを JSON に保存）。2009 は性別ごとに 1 シート、
  2010 以降は 1 シート 3 ブロック。
"""

import copy
import json
from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import bsws
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
XLSX_2025 = (FIXTURES / "bsws_2025_occupation.xlsx").read_bytes()
GRID_2019: list[list[list[object]]] = json.loads((FIXTURES / "bsws_2019_grid.json").read_text())
GRID_2009: list[list[list[object]]] = json.loads((FIXTURES / "bsws_2009_grid.json").read_text())

FIXTURE_OCCUPATIONS = 12


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def by_key(rows: list[dict[str, object]]) -> dict[tuple[object, ...], dict[str, object]]:
    return {(r["year"], r["sex"], r["size_class"], r["occupation"]): r for r in rows}


# ---- constants ---------------------------------------------------------------


def test_tables_cover_every_survey_year_from_2009_to_2025() -> None:
    assert sorted(bsws.TABLES) == list(range(2009, 2026))
    for year, (stat_inf_id, file_kind) in bsws.TABLES.items():
        assert len(stat_inf_id) == 12 and stat_inf_id.isdigit()
        assert file_kind == (4 if year >= 2021 else 0), year


def test_raw_name_and_url_follow_the_file_kind() -> None:
    assert bsws.raw_name(2025) == "bsws_2025_occupation.xlsx"
    assert bsws.raw_name(2020) == "bsws_2020_occupation.xls"
    assert bsws.raw_name(2009) == "bsws_2009_occupation.xls"
    assert bsws.url(2025) == (
        "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040421116&fileKind=4"
    )
    assert bsws.SOURCE == "estat_bsws"
    assert "政府標準利用規約" in bsws.LICENSE


def test_classification_switches_at_the_2020_revision() -> None:
    assert bsws.classification(2019) == "jp_bsws2009"
    assert bsws.classification(2020) == "jp_bsws2020"


# ---- parse: new format (2020-) ---------------------------------------------------


def test_parse_new_format_yields_one_wide_row_per_sex_size_occupation() -> None:
    rows = bsws.parse(XLSX_2025, 2025, expected_occupations=FIXTURE_OCCUPATIONS)
    assert len(rows) == 3 * 4 * FIXTURE_OCCUPATIONS
    assert [r["sex"] for r in rows[:4]] == ["T", "T", "T", "T"]
    assert [r["size_class"] for r in rows[:4]] == ["all", "1000+", "100-999", "10-99"]
    assert {r["sex"] for r in rows} == {"T", "M", "F"}
    assert all(r["classification"] == "jp_bsws2020" for r in rows)
    assert set(rows[0]) == set(bsws.STAGED_COLUMNS)

    k = by_key(rows)
    top = k[(2025, "T", "all", "管理的職業従事者")]
    assert top["age"] == 51.5
    assert top["tenure_years"] == 22.6
    assert top["scheduled_hours"] == 163
    assert top["overtime_hours"] == 2
    assert top["monthly_cash_thousand_yen"] == 599.7
    assert top["scheduled_wage_thousand_yen"] == 591
    assert top["annual_bonus_thousand_yen"] == 2471.2
    assert top["workers"] == 1758300  # 175,830 十人
    small = k[(2025, "T", "10-99", "管理的職業従事者")]
    assert (small["age"], small["workers"]) == (53.1, 397610)
    men = k[(2025, "M", "all", "管理的職業従事者")]
    assert (men["age"], men["workers"]) == (51.7, 1558330)


def test_parse_new_format_strips_sex_prefixes_and_maps_dash_to_none() -> None:
    rows = bsws.parse(XLSX_2025, 2025, expected_occupations=FIXTURE_OCCUPATIONS)
    names = {r["occupation"] for r in rows}
    assert "看護助手" in names and "不詳" in names
    assert all("男" not in n and "　" not in n and "\n" not in n for n in names)
    k = by_key(rows)
    unknown_f = k[(2025, "F", "all", "不詳")]
    assert (unknown_f["age"], unknown_f["workers"]) == (29.5, 20)
    missing = k[(2025, "F", "10-99", "不詳")]
    assert all(missing[c] is None for c in bsws.METRIC_COLUMNS)


def test_parse_rejects_a_truncated_table_when_the_full_count_is_expected() -> None:
    with pytest.raises(ValueError, match="145"):
        bsws.parse(XLSX_2025, 2025)


def test_parse_rejects_non_excel_payload() -> None:
    with pytest.raises(ValueError):
        bsws.parse(b"<html>not excel</html>", 2025)


# ---- parse: old format (2009-2019) ------------------------------------------------


def test_parse_grids_old_format_single_sheet_2019() -> None:
    rows = bsws.parse_grids(GRID_2019, 2019, expected_occupations=FIXTURE_OCCUPATIONS)
    assert len(rows) == 3 * 4 * FIXTURE_OCCUPATIONS
    assert all(r["classification"] == "jp_bsws2009" for r in rows)
    k = by_key(rows)
    first = k[(2019, "T", "all", "自然科学系研究者")]
    assert (first["age"], first["tenure_years"], first["scheduled_hours"]) == (39.0, 10.4, 153)
    last_small = k[(2019, "T", "10-99", "自然科学系研究者")]
    assert last_small["scheduled_wage_thousand_yen"] == 429.1
    assert last_small["annual_bonus_thousand_yen"] == 1154.8
    assert last_small["workers"] == 1890
    assert "製鋼工" in {r["occupation"] for r in rows}  # prefix repeat row kept, prefix stripped
    assert k[(2019, "F", "all", "用務員")]["age"] == 55.9


def test_parse_grids_old_format_one_sheet_per_sex_2009() -> None:
    rows = bsws.parse_grids(GRID_2009, 2009, expected_occupations=FIXTURE_OCCUPATIONS)
    assert len(rows) == 3 * 4 * FIXTURE_OCCUPATIONS
    k = by_key(rows)
    first = k[(2009, "T", "all", "自然科学系研究者")]
    assert (first["age"], first["tenure_years"]) == (37.5, 10.2)
    assert k[(2009, "T", "10-99", "自然科学系研究者")]["workers"] == 2960
    assert {r["sex"] for r in rows} == {"T", "M", "F"}
    assert (2009, "T", "all", "男女計") not in k  # standalone label row is not an occupation


def test_parse_grids_rejects_blocks_whose_occupations_differ() -> None:
    grid = copy.deepcopy(GRID_2019)
    sheet = grid[0]
    men_first = next(i for i, r in enumerate(sheet) if str(r[7]).strip().startswith("男\n"))
    sheet[men_first + 1][7] = "別の職種"
    with pytest.raises(ValueError, match="occupation"):
        bsws.parse_grids(grid, 2019, expected_occupations=FIXTURE_OCCUPATIONS)


def test_parse_grids_rejects_a_sex_prefix_in_the_wrong_block() -> None:
    grid = copy.deepcopy(GRID_2019)
    sheet = grid[0]
    men_first = next(i for i, r in enumerate(sheet) if str(r[7]).strip().startswith("男\n"))
    sheet[men_first][7] = "　女\n\n自然科学系研究者"
    with pytest.raises(ValueError, match="sex"):
        bsws.parse_grids(grid, 2019, expected_occupations=FIXTURE_OCCUPATIONS)


def test_parse_grids_rejects_unknown_cell_markers_and_wrong_units() -> None:
    grid = copy.deepcopy(GRID_2019)
    grid[0][12][9] = "?"
    with pytest.raises(ValueError, match="cell"):
        bsws.parse_grids(grid, 2019, expected_occupations=FIXTURE_OCCUPATIONS)
    grid = copy.deepcopy(GRID_2019)
    grid[0][10][40] = "人"  # 労働者数 unit must be 十人
    with pytest.raises(ValueError, match="unit"):
        bsws.parse_grids(grid, 2019, expected_occupations=FIXTURE_OCCUPATIONS)


# ---- fetch / stage / mart ---------------------------------------------------------


def test_fetch_stores_excel_payloads_and_skips_fetch_errors_and_non_excel() -> None:
    ctx = make_ctx({bsws.url(2025): XLSX_2025, bsws.url(2024): b"<html>maintenance</html>"})
    written, skipped = bsws.fetch(ctx, [], [])
    assert written == [f"{THEME}/{bsws.SOURCE}/bsws_2025_occupation.xlsx"]
    assert f"{bsws.raw_name(2024)}: non-excel payload" in skipped
    assert any(s.startswith("bsws_2009_occupation.xls: ") for s in skipped)
    assert len(skipped) == len(bsws.TABLES) - 1
    recs = ctx.raw.records()
    assert len(recs) == 1
    assert recs[0].url == bsws.url(2025)
    assert recs[0].license == bsws.LICENSE
    assert (
        ctx.raw.get(theme=THEME, source=bsws.SOURCE, name="bsws_2025_occupation.xlsx") == XLSX_2025
    )


def test_stage_skips_years_without_raw_and_writes_one_table_per_year() -> None:
    ctx = make_ctx()
    written, skipped = bsws.stage(ctx, [], [])
    assert written == []
    assert skipped == [f"{bsws.raw_name(y)}: no raw" for y in sorted(bsws.TABLES)]
    assert ctx.tables.list_tables() == []

    ctx = make_ctx()
    ctx.raw.put(
        theme=THEME,
        source=bsws.SOURCE,
        name=bsws.raw_name(2025),
        url=bsws.url(2025),
        license=bsws.LICENSE,
        payload=XLSX_2025,
    )
    with pytest.raises(ValueError):  # truncated fixture: fail closed rather than stage partial data
        bsws.stage(ctx, [], [])

    written, skipped = bsws.stage(ctx, [], [], expected_occupations=FIXTURE_OCCUPATIONS)
    assert written == ["staged/bsws/occupation_wages_2025"]
    assert len(skipped) == len(bsws.TABLES) - 1
    rows = ctx.tables.read_table("staged/bsws/occupation_wages_2025")
    assert len(rows) == 3 * 4 * FIXTURE_OCCUPATIONS
    assert rows[0]["year"] == 2025 and rows[0]["classification"] == "jp_bsws2020"


def test_mart_concatenates_staged_years_and_adds_iso3_and_source() -> None:
    ctx = make_ctx()
    written, skipped = bsws.mart(ctx, [], [])
    assert written == []
    assert skipped == [bsws.MART_TABLE + ": no staged tables"]

    ctx = make_ctx()
    new = bsws.parse(XLSX_2025, 2025, expected_occupations=FIXTURE_OCCUPATIONS)
    old = bsws.parse_grids(GRID_2019, 2019, expected_occupations=FIXTURE_OCCUPATIONS)
    ctx.tables.write_table(bsws.staged_table(2025), new)
    ctx.tables.write_table(bsws.staged_table(2019), old)
    written, skipped = bsws.mart(ctx, [], [])
    assert written == [bsws.MART_TABLE]
    assert skipped == []
    rows = ctx.tables.read_table(bsws.MART_TABLE)
    assert len(rows) == len(new) + len(old)
    assert {r["iso3"] for r in rows} == {"JPN"}
    assert {r["source"] for r in rows} == {"estat_bsws"}
    keys = [(r["year"], r["sex"], r["size_class"], r["occupation"]) for r in rows]
    assert keys == sorted(keys)
    assert rows[0]["year"] == 2019 and rows[-1]["year"] == 2025
    assert list(rows[0]) == list(bsws.MART_COLUMNS)


def test_build_mart_rejects_duplicate_keys() -> None:
    rows = bsws.parse_grids(GRID_2019, 2019, expected_occupations=FIXTURE_OCCUPATIONS)
    with pytest.raises(ValueError, match="duplicate"):
        bsws.build_mart(rows + rows[:1])
