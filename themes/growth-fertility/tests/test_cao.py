"""cao.py (H10): 内閣府 県民経済計算 総括表 7（1 人当たり県民所得、2011–2022 年度）xlsx ->
long rows (pure, fail-closed). Fixture = the real workbook with only the 実数 sheet and without
the 地域ブロック / 政令指定都市 rows."""

from pathlib import Path

import pytest

from theme_growth_fertility import cao

FIXTURES = Path(__file__).parent / "fixtures"


def test_url_raw_name_source_and_license() -> None:
    assert cao.URL == (
        "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2022/"
        "soukatu7.xlsx"
    )
    assert cao.RAW_NAME == "kenmin_soukatu7.xlsx"
    assert cao.SOURCE == "cao_kenmin"
    assert "政府標準利用規約" in cao.LICENSE and "内閣府" in cao.LICENSE
    assert tuple(range(2011, 2023)) == cao.YEARS


def test_income_rows_are_48_regions_x_12_fiscal_years_in_thousand_yen() -> None:
    rows = cao.income_rows((FIXTURES / "cao_soukatu7.xlsx").read_bytes())
    assert len(rows) == 48 * 12
    assert set(rows[0]) == {
        "pref_code",
        "pref_name",
        "year",
        "metric",
        "sex",
        "age_class",
        "value",
        "table",
        "source",
    }
    k = {(r["pref_code"], r["year"]): r["value"] for r in rows}
    assert len(k) == len(rows)
    assert k[("01", 2011)] == 2456
    assert k[("01", 2022)] == 2891
    assert k[("47", 2022)] == 2249
    assert k[("00", 2022)] == 3449  # 全県計
    assert k[("00", 2011)] == 2991
    assert all(
        r["metric"] == "income_per_capita"
        and r["sex"] == "T"
        and r["age_class"] is None
        and r["table"] == "総括表7"
        and r["source"] == "cao_kenmin"
        for r in rows
    )
    assert {r["pref_name"] for r in rows if r["pref_code"] == "01"} == {"北海道"}
    assert {r["pref_name"] for r in rows if r["pref_code"] == "13"} == {"東京"}
    assert all(isinstance(r["value"], int) for r in rows)


def test_income_rows_fail_closed_on_title_unit_years_or_prefectures() -> None:
    raw = (FIXTURES / "cao_soukatu7.xlsx").read_bytes()
    rows = cao.sheet_rows(raw)
    with pytest.raises(ValueError, match="title"):
        cao.income_rows_from_sheet([{8: "８．県民所得"}, *rows[1:]])
    with pytest.raises(ValueError, match="unit"):
        cao.income_rows_from_sheet([*rows[:2], {**rows[2], 16: "（単位：百万円）"}, *rows[3:]])
    with pytest.raises(ValueError, match="year"):
        cao.income_rows_from_sheet([*rows[:4], {**rows[4], 15: "2023"}, *rows[5:]])
    with pytest.raises(ValueError, match="prefecture"):
        cao.income_rows_from_sheet([*rows[:10], {**rows[10], 1: "06"}, *rows[11:]])
    with pytest.raises(ValueError, match="全県計"):
        cao.income_rows_from_sheet(rows[:53])
    with pytest.raises(ValueError, match="non-numeric"):
        cao.income_rows_from_sheet([*rows[:6], {**rows[6], 4: "x"}, *rows[7:]])
    with pytest.raises(ValueError, match="xlsx"):
        cao.income_rows(b"not an xlsx")
