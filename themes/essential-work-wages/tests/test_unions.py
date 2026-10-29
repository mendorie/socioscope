"""労働組合基礎調査 概況 第 3 表（産業別 組合員数・雇用者数・組織率）: fetch -> stage -> mart."""

from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import unions
from theme_essential_work_wages.pipeline import THEME

FIXTURES = Path(__file__).parent / "fixtures"
# Page 6 (index 5) of the 令和 7 年 概況 PDF, cut with pypdf: the 第 3 表 page only.
PDF = (FIXTURES / "unions_2025_overview_p5.pdf").read_bytes()

INDUSTRIES_2012 = {
    "農 業 ， 林 業 、 漁 業": ("13,055", "60", "2.2"),
    "鉱 業 , 採 石 業 , 砂 利 採 取 業": ("5,112", "3", "17.0"),
    "建 設 業": ("830,545", "419", "19.8"),
    "製 造 業": ("2,695,254", "988", "27.3"),
    "電 気 ・ ｶ ﾞ ｽ ・ 熱 供 給 ・ 水 道 業": ("186,772", "37", "50.5"),
    "情 報 通 信 業": ("388,983", "177", "22.0"),
    "運 輸 業 , 郵 便 業": ("873,408", "329", "26.5"),
    "卸 売 業 , 小 売 業": ("1,210,000", "926", "13.1"),
    "金 融 業 ， 保 険 業": ("733,736", "153", "48.0"),
    "不 動 産 業 , 物 品 賃 貸 業": ("28,504", "102", "2.8"),
    "学術研究,専門・技術 サービス業": ("146,444", "154", "9.5"),
    "宿 泊 業 , 飲 食 サ ー ビ ス 業": ("142,646", "313", "4.6"),
    "生 活 関 連 サ ー ビ ス 業 , 娯 楽 業": ("111,742", "188", "5.9"),
    "教 育 , 学 習 支 援 業": ("543,114", "271", "20.0"),
    "医 療 , 福 祉": ("480,462", "673", "7.1"),
    "複 合 サ ー ビ ス 事 業": ("269,715", "47", "57.4"),
    "サービス業(他に分類されないもの)": ("180,818", "412", "4.4"),
    "公務(他に分類されるものを除く)": ("928,719", "235", "39.5"),
    "分 類 不 能 の 産 業": ("61,838", "42", "…"),
}


def page_2012(total: str = "9,830,867") -> str:
    """Layout-mode text in the 2012 shape: 人 人 ％ ％ 万人 ％, women in separate '(…)' lines."""
    lines = [
        "２ 産業別の状況",
        "                 対前年差      対前年比    構成比",
        "                      人            人           ％        ％        万人        ％",
        f"   総           計     {total}     -66,482      -0.7     100.0     5,528      …",
        "                       (2,984,327)    (28,525)    (1.0)",
    ]
    for name, (members, emp, dens) in INDUSTRIES_2012.items():
        lines.append(f"   {name}      {members}     -528     -3.9     0.1     {emp}     {dens}")
        lines.append("                 (1,265)   (-56)   (-4.2)")
    lines.append(" (注) 1) 「分類不能の産業」の労働組合員数には")
    return "\n".join(lines)


# pypdf layout-mode text of page 3 (index 2) of the 平成 30 年 調査結果の概要 PDF (statInfId
# 000031792619): the 2013-2022 shape with women's figures in parentheses on the same line.
PAGE_2018 = (FIXTURES / "unions_2018_overview_p2_layout.txt").read_text(encoding="utf-8")


def make_ctx(responses: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(responses or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def by_code(rows: list[dict[str, object]]) -> dict[object, dict[str, object]]:
    return {r["industry_code"]: r for r in rows}


# ---- constants


def test_one_overview_pdf_per_year_2012_to_2025() -> None:
    assert unions.SOURCE == "mhlw_unions"
    assert "政府標準利用規約" in unions.LICENSE
    assert sorted(unions.FILES) == list(range(2012, 2026))
    assert unions.FILES[2025] == "000040389648"
    assert unions.FILES[2012] == "000023609833"
    assert unions.url(2025).endswith("statInfId=000040389648&fileKind=2")
    assert unions.raw_name(2025) == "unions_2025_overview.pdf"
    assert PDF.startswith(unions.MAGIC)
    assert len(unions.INDUSTRY_CODES) == 20


# ---- fetch


def test_fetch_puts_every_year_in_raw_and_skips_errors_and_non_pdf() -> None:
    responses = {unions.url(y): PDF for y in unions.FILES}
    del responses[unions.url(2013)]
    responses[unions.url(2014)] = b"<html>"
    ctx = make_ctx(responses)
    written, skipped = unions.fetch(ctx, [], [])
    recs = ctx.raw.records()
    assert [r.name for r in recs] == [
        unions.raw_name(y) for y in range(2012, 2026) if y not in (2013, 2014)
    ]
    assert written == [r.relative_path for r in recs]
    assert all(r.theme == THEME and r.source == unions.SOURCE for r in recs)
    assert recs[0].url == unions.url(2012)
    assert recs[0].license == unions.LICENSE
    assert skipped[0].startswith(f"{unions.raw_name(2013)}: ")
    assert skipped[1] == f"{unions.raw_name(2014)}: non-pdf payload"
    assert len(skipped) == 2


# ---- parse (pure, on layout-mode page text)


def test_parse_2012_shape_members_in_persons_employees_in_10k() -> None:
    out = unions.parse([page_2012()], 2012)
    assert len(out) == 20
    rows = by_code(out)
    assert rows["ALL"] == {
        "year": 2012,
        "industry_code": "ALL",
        "industry": "総計",
        "members": 9830867.0,
        "employees": 55280000.0,
        "union_density_pct": None,
    }
    assert rows["P"] == {
        "year": 2012,
        "industry_code": "P",
        "industry": "医療、福祉",
        "members": 480462.0,
        "employees": 6730000.0,
        "union_density_pct": 7.1,
    }
    assert rows["F"]["industry"] == "電気・ガス・熱供給・水道業"
    assert rows["F"]["union_density_pct"] == 50.5
    assert rows["A-B"]["industry"] == "農業、林業、漁業"
    assert rows["T"]["union_density_pct"] is None
    assert rows["R"]["industry"] == "サービス業(他に分類されないもの)"


def test_parse_2018_shape_with_women_in_parentheses() -> None:
    out = unions.parse(["intro page without the table", PAGE_2018], 2018)
    rows = by_code(out)
    assert rows["ALL"]["members"] == 9996004.0
    assert rows["ALL"]["employees"] == 59400000.0
    assert rows["L"]["industry"] == "学術研究、専門・技術サービス業"
    assert (rows["L"]["members"], rows["L"]["employees"], rows["L"]["union_density_pct"]) == (
        144118.0,
        1910000.0,
        7.5,
    )
    assert rows["S"]["union_density_pct"] == 36.9


def test_parse_2025_shape_members_in_thousands_two_years_side_by_side() -> None:
    out = unions.parse(unions.pdf_pages(PDF), 2025)
    rows = by_code(out)
    assert rows["ALL"]["members"] == 9864000.0
    assert rows["ALL"]["employees"] == 62050000.0
    assert rows["ALL"]["union_density_pct"] == 15.9
    assert rows["E"]["members"] == 2614000.0
    assert rows["E"]["employees"] == 9890000.0
    assert rows["E"]["union_density_pct"] == 26.4
    assert rows["P"]["union_density_pct"] == 5.3
    assert rows["T"]["employees"] is None
    assert rows["C"]["members"] == 5000.0  # name glued to the number in text mode, not in layout


def test_parse_rejects_a_total_that_does_not_match_the_industry_sum() -> None:
    with pytest.raises(ValueError, match="sum of industries"):
        unions.parse([page_2012(total="9,000,000")], 2012)


def test_parse_rejects_pages_without_the_table_or_with_a_missing_industry() -> None:
    with pytest.raises(ValueError, match="units"):
        unions.parse(["no table here"], 2012)
    page = "\n".join(line for line in page_2012().splitlines() if "医 療" not in line)
    with pytest.raises(ValueError, match="医療、福祉"):
        unions.parse([page], 2012)


def test_pdf_pages_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="pdf"):
        unions.pdf_pages(b"%PDF-1.4 but nothing else")


# ---- stage / mart (state)


def test_stage_writes_one_staged_table_per_year_present_in_raw() -> None:
    ctx = make_ctx({unions.url(2025): PDF, unions.url(2024): PDF})
    unions.fetch(ctx, [], [])
    written, skipped = unions.stage(ctx, [], [])
    assert written == [unions.staged_table(2024), unions.staged_table(2025)]
    assert skipped == [f"{unions.raw_name(y)}: no raw" for y in range(2012, 2024)]
    rows = ctx.tables.read_table(unions.staged_table(2024))
    assert len(rows) == 20 and rows[0]["year"] == 2024


def test_mart_concatenates_years_and_adds_keys() -> None:
    ctx = make_ctx({unions.url(2025): PDF, unions.url(2024): PDF})
    unions.fetch(ctx, [], [])
    unions.stage(ctx, [], [])
    written, skipped = unions.mart(ctx, [], [])
    assert written == [unions.MART_TABLE]
    assert skipped == []
    rows = ctx.tables.read_table(unions.MART_TABLE)
    assert len(rows) == 40
    assert [(r["year"], r["industry_code"]) for r in rows[:3]] == [
        (2024, "A-B"),
        (2024, "ALL"),
        (2024, "C"),
    ]
    r = rows[0]
    assert r["iso3"] == "JPN" and r["source"] == unions.SOURCE
    assert list(r) == [
        "iso3",
        "year",
        "industry_code",
        "industry",
        "members",
        "employees",
        "union_density_pct",
        "source",
    ]


def test_mart_skips_when_no_staged_table_exists() -> None:
    ctx = make_ctx()
    written, skipped = unions.mart(ctx, [], [])
    assert written == []
    assert skipped == [f"{unions.SOURCE}: no staged table"]


def test_build_mart_rejects_duplicate_year_industry() -> None:
    row: dict[str, object] = {"year": 2024, "industry_code": "P", "industry": "医療、福祉"}
    with pytest.raises(ValueError, match="duplicate"):
        unions.build_mart([row, dict(row)])
