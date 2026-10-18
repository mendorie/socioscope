"""ipss.py (H12): 人口統計資料集 2026 T06-01★（初婚・再婚別婚姻数 1884–2024）と
第 16 回出生動向基本調査 報告書グラフデータ CSV（12 figures、CP932、tidy）-> long rows (pure,
fail-closed), plus the attitudes mart. CSV fixtures are the real files cut to the title, the
header and the first / last six rows (bytes untouched); the xlsx fixture is the real workbook
re-saved with values only."""

import io
from pathlib import Path

import openpyxl
import pytest

from theme_growth_fertility import ipss

FIXTURES = Path(__file__).parent / "fixtures"
T0601 = (FIXTURES / "ipss_T06-01.xlsx").read_bytes()
GRAPH_URL = "https://www.ipss.go.jp/ps-doukou/j/db_16/16HoukokuBaseData/"


def graph(figure: str) -> bytes:
    return (FIXTURES / f"ipss_graph_{figure}.csv").read_bytes()


def table(code: str) -> ipss.Table:
    return next(t for t in ipss.TABLES if t.code == code)


def marriage_keyed(rs: list[dict[str, object]]) -> dict[tuple[object, ...], object]:
    out = {(r["year"], r["metric"], r["sex"], r["age_class"]): r["value"] for r in rs}
    assert len(out) == len(rs)
    return out


def attitude_key(r: dict[str, object]) -> tuple[object, ...]:
    return tuple(r[c] for c in ipss.ATTITUDES_KEY)


# ---- registry ------------------------------------------------------------------------------


def test_t06_01_is_appended_to_tables_and_its_metrics_to_marriage_metrics() -> None:
    t = table("T06-01")
    assert ipss.TABLES[-1] == t
    assert t.key == "t06_01" and t.sheet == "T06-01★" and t.mart == "marriage"
    assert t.url == "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2026/T06-01.xlsx"
    assert t.raw_name == "T06-01.xlsx"
    # appended after the H10 / H11 metrics so the sort order of the earlier rows is unchanged
    assert ipss.MARRIAGE_METRICS[:7] == (
        "never_married_share",
        "mean_age_marriage_all",
        "mean_age_first_marriage",
        "never_married_at_50",
        "married_share",
        "widowed_share",
        "divorced_share",
    )
    assert (
        ipss.MARRIAGE_METRICS[7:]
        == ipss.FIRST_MARRIAGE_METRICS
        == (
            "marriages_total",
            "first_marriages_husband",
            "remarriages_husband",
            "first_marriages_wife",
            "remarriages_wife",
            "first_marriage_share_husband_pct",
            "first_marriage_share_wife_pct",
            "crude_marriage_rate",
        )
    )


def test_graph_files_and_urls_are_fixed() -> None:
    assert ipss.GRAPH_BASE_URL == GRAPH_URL
    assert ipss.GRAPH_FILES == (
        "1_1_1",
        "1_1_2",
        "1_2_1",
        "1_2_2",
        "1_3_2",
        "2_1_1",
        "2_1_2",
        "2_3_1",
        "3_2_1",
        "5_2_1",
        "5_2_2",
        "12_1_2",
    )
    assert ipss.graph_url("12_1_2") == GRAPH_URL + "houkokuFigure12_1_2.csv"
    assert ipss.graph_raw_name("1_1_1") == "houkokuFigure1_1_1.csv"
    assert ipss.GRAPH_SOURCE == "ipss_jnfs16_graph"
    assert set(ipss.GRAPH_HEADERS) == set(ipss.GRAPH_FILES)
    assert ipss.GRAPH_ROUND_YEARS == {
        8: 1982,
        9: 1987,
        10: 1992,
        11: 1997,
        12: 2002,
        13: 2005,
        14: 2010,
        15: 2015,
        16: 2021,
    }


# ---- T06-01★: 初婚・再婚別婚姻数および婚姻率 ---------------------------------------------------


def _edited_t06_01(mutate) -> bytes:  # type: ignore[no-untyped-def]
    wb = openpyxl.load_workbook(io.BytesIO(T0601))
    mutate(wb)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_first_marriage_rows_read_every_year_with_unknowns_dropped() -> None:
    rows = ipss.parse_table(T0601, table("T06-01"))
    assert set(rows[0]) == {"year", "metric", "sex", "age_class", "value", "table", "source"}
    assert all(r["table"] == "T06-01" and r["source"] == "ipss" for r in rows)
    assert all(r["age_class"] is None for r in rows)
    k = marriage_keyed(rows)
    years = sorted({int(str(r["year"])) for r in rows})
    # the sheet has no rows for the war years 1941–1946
    assert years == [y for y in range(1884, 2025) if y not in range(1941, 1947)]
    assert len(years) == 135
    # total and crude rate every year; the first / remarriage split only where published
    assert k[(1884, "marriages_total", "T", None)] == 287842
    assert k[(1884, "crude_marriage_rate", "T", None)] == 7.6
    assert (1884, "first_marriages_wife", "F", None) not in k
    assert (1898, "first_marriages_husband", "M", None) not in k
    assert k[(1899, "first_marriages_husband", "M", None)] == 234075
    assert k[(1899, "remarriages_husband", "M", None)] == 60645
    assert k[(1899, "first_marriages_wife", "F", None)] == 247093
    assert k[(1899, "remarriages_wife", "F", None)] == 42079
    assert k[(1899, "first_marriage_share_husband_pct", "M", None)] == 78.7
    assert k[(1899, "first_marriage_share_wife_pct", "F", None)] == 83.1
    assert (1947, "first_marriages_wife", "F", None) not in k
    assert k[(1947, "marriages_total", "T", None)] == 934170
    assert k[(1982, "first_marriages_wife", "F", None)] == 704840
    assert k[(2019, "first_marriages_wife", "F", None)] == 497598
    assert k[(2020, "first_marriages_wife", "F", None)] == 437169
    assert k[(2021, "first_marriages_wife", "F", None)] == 417783
    assert k[(2024, "marriages_total", "T", None)] == 485092
    assert k[(2024, "first_marriage_share_wife_pct", "F", None)] == pytest.approx(84.4)
    assert k[(2024, "crude_marriage_rate", "T", None)] == 4.0
    by_metric = {m: sum(1 for r in rows if r["metric"] == m) for m in ipss.FIRST_MARRIAGE_METRICS}
    assert by_metric["marriages_total"] == 135 and by_metric["crude_marriage_rate"] == 135
    assert by_metric["first_marriages_wife"] == by_metric["remarriages_husband"]
    # '…' for 1884–1898 and 1947–1951 (135 − 15 − 5 = 115), minus the one upstream typo per sex:
    # 1918 夫 and 1926 妻 have 初婚 + 再婚 > 総数, so those split / share cells give no row
    assert by_metric["first_marriages_wife"] == 114
    assert by_metric["first_marriage_share_husband_pct"] == 114
    assert (1951, "first_marriages_wife", "F", None) not in k
    assert (1952, "first_marriages_wife", "F", None) in k
    assert (1918, "first_marriages_husband", "M", None) not in k
    assert (1918, "first_marriage_share_husband_pct", "M", None) not in k
    assert k[(1918, "first_marriages_wife", "F", None)] == 446747
    assert (1926, "remarriages_wife", "F", None) not in k
    assert (1926, "first_marriage_share_wife_pct", "F", None) not in k
    assert k[(1926, "first_marriages_husband", "M", None)] == 429570
    assert {r["sex"] for r in rows} == {"T", "M", "F"}


def test_first_marriage_rows_fail_closed_on_title_header_years_and_totals() -> None:
    def title(wb: openpyxl.Workbook) -> None:
        wb["T06-01★"]["A1"] = "表６－２ 何か別の表"

    with pytest.raises(ValueError, match="title"):
        ipss.parse_table(_edited_t06_01(title), table("T06-01"))

    def header(wb: openpyxl.Workbook) -> None:
        wb["T06-01★"]["E3"] = "再婚"

    with pytest.raises(ValueError, match="header"):
        ipss.parse_table(_edited_t06_01(header), table("T06-01"))

    def year_gap(wb: openpyxl.Workbook) -> None:
        wb["T06-01★"]["A10"] = 1891  # 1890 -> 1891 (duplicate / gap)

    with pytest.raises(ValueError, match="consecutive"):
        ipss.parse_table(_edited_t06_01(year_gap), table("T06-01"))

    def split_exceeds_total(wb: openpyxl.Workbook) -> None:
        wb["T06-01★"]["C19"] = 900000  # 1899 夫 初婚 234075 -> 900000 > 総数 297372

    with pytest.raises(ValueError, match="1899"):
        ipss.parse_table(_edited_t06_01(split_exceeds_total), table("T06-01"))

    def text_value(wb: openpyxl.Workbook) -> None:
        wb["T06-01★"]["B19"] = "n.a."

    with pytest.raises(ValueError, match="n.a."):
        ipss.parse_table(_edited_t06_01(text_value), table("T06-01"))

    def missing_sheet(wb: openpyxl.Workbook) -> None:
        wb.remove(wb["T06-01★"])

    with pytest.raises(ValueError, match="T06-01★"):
        ipss.parse_table(_edited_t06_01(missing_sheet), table("T06-01"))


# ---- 報告書グラフデータ CSV ---------------------------------------------------------------------

COLUMNS = {
    "figure",
    "survey_round",
    "survey_year",
    "period",
    "marriage_year",
    "sex",
    "age",
    "category",
    "item",
    "sub",
    "count",
    "share_pct",
    "se",
    "ci_low",
    "ci_high",
    "denominator",
    "source",
}


def test_graph_rows_1_1_1_marriage_intention_with_confidence_intervals() -> None:
    rows = ipss.graph_rows(graph("1_1_1"), "1_1_1")
    assert len(rows) == 12
    assert set(rows[0]) == COLUMNS
    assert all(r["figure"] == "1_1_1" and r["source"] == "ipss_jnfs16_graph" for r in rows)
    assert all(r["category"] == "生涯の結婚意思" for r in rows)
    assert all(r["age"] == "" and r["sub"] == "" and r["marriage_year"] == "" for r in rows)
    assert all(r["period"] == "" and r["denominator"] is None for r in rows)
    first = rows[0]
    assert first["survey_round"] == 8 and first["survey_year"] == 1982
    assert first["sex"] == "male" and first["item"] == "いずれ結婚するつもり"
    assert first["count"] == 2620 and first["share_pct"] == 95.9 and first["se"] == 0.4
    assert first["ci_high"] == 96.6 and first["ci_low"] == 95.2
    assert isinstance(first["count"], float)
    last = rows[-1]
    assert last["survey_round"] == 16 and last["survey_year"] == 2021
    assert last["sex"] == "female" and last["item"] == "不詳"
    assert last["count"] == 22 and last["share_pct"] == 1.1 and last["ci_low"] == 0.6
    assert len({attitude_key(r) for r in rows}) == len(rows)


def test_graph_rows_map_each_figure_layout_to_the_common_columns() -> None:
    # 1_1_2: age column
    rows = ipss.graph_rows(graph("1_1_2"), "1_1_2")
    assert rows[0]["age"] == "18～19歳" and rows[0]["category"] == "生涯の結婚意思"
    assert rows[-1]["age"] == "30～34歳" and rows[-1]["sex"] == "female"
    # 1_2_1 / 1_2_2: 総数 -> denominator, no CI
    rows = ipss.graph_rows(graph("1_2_1"), "1_2_1")
    assert rows[0]["category"] == "結婚の利点" and rows[0]["item"] == "経済的に余裕がもてる"
    assert rows[0]["survey_round"] == 9 and rows[0]["survey_year"] == 1987
    assert rows[0]["count"] == 108 and rows[0]["share_pct"] == 3.3
    assert rows[0]["denominator"] == 3299 and rows[0]["se"] is None and rows[0]["ci_low"] is None
    rows = ipss.graph_rows(graph("1_2_2"), "1_2_2")
    assert rows[0]["category"] == "独身生活の利点" and rows[0]["item"] == "行動や生き方が自由"
    # 1_3_2: age + 独身の理由
    rows = ipss.graph_rows(graph("1_3_2"), "1_3_2")
    assert rows[0]["category"] == "独身の理由" and rows[0]["age"] == "18～24歳"
    assert rows[0]["item"] == "結婚するにはまだ若すぎるから" and rows[0]["denominator"] == 2685
    # 2_1_1 / 2_1_2: 18～34歳（総数） kept as the age label
    rows = ipss.graph_rows(graph("2_1_1"), "2_1_1")
    assert rows[0]["category"] == "異性との交際状況" and rows[0]["age"] == "18～34歳（総数）"
    assert rows[0]["item"] == "恋人または婚約者がいる（再掲）" and rows[0]["share_pct"] == 21.9
    rows = ipss.graph_rows(graph("2_1_2"), "2_1_2")
    assert rows[0]["category"] == "交際希望" and rows[0]["survey_year"] == 1982
    assert rows[0]["item"] == "交際相手なし－交際希望の設問なし"
    assert rows[0]["count"] == 1006 and rows[0]["share_pct"] == 36.8
    assert rows[0]["denominator"] == 2732
    # 2_3_1: no denominator column
    rows = ipss.graph_rows(graph("2_3_1"), "2_3_1")
    assert rows[0]["category"] == "知り合ったきっかけ" and rows[0]["item"] == "学校で"
    assert rows[0]["sex"] == "male" and rows[0]["denominator"] is None
    # 3_2_1: sex from the long labels, 重視する程度 -> sub
    rows = ipss.graph_rows(graph("3_2_1"), "3_2_1")
    assert rows[0]["sex"] == "male" and rows[-1]["sex"] == "female"
    assert rows[-1]["category"] == "重視する項目" and rows[-1]["item"] == "家事・育児の能力や姿勢"
    assert rows[-1]["sub"] == "考慮する" and rows[-1]["share_pct"] == 26.3
    assert rows[-1]["denominator"] == 1731
    # 12_1_2: 割合 before 度数, 支持／不支持 -> sub
    rows = ipss.graph_rows(graph("12_1_2"), "12_1_2")
    assert rows[0]["category"] == "結婚・家族に関する考え方"
    assert rows[0]["item"] == "14.同性での結婚かまわない（反対）" and rows[0]["sub"] == "設問なし"
    assert rows[0]["share_pct"] == 100.0 and rows[0]["count"] == 4215
    assert rows[-1]["sub"] == "不詳" and rows[-1]["share_pct"] == 1.3 and rows[-1]["count"] == 26


def test_graph_rows_5_2_1_use_marriage_year_and_keep_negative_ci_bounds() -> None:
    rows = ipss.graph_rows(graph("5_2_1"), "5_2_1")
    assert all(r["survey_round"] is None and r["survey_year"] is None for r in rows)
    assert all(r["sex"] == "" and r["age"] == "" for r in rows)
    assert rows[0]["marriage_year"] == "1930～39年" and rows[0]["item"] == "恋愛結婚"
    assert rows[0]["category"] == "知り合ったきっかけ"
    assert rows[0]["count"] == 78 and rows[0]["share_pct"] == 13.4 and rows[0]["se"] == 1.4
    assert rows[0]["ci_high"] == 16.1 and rows[0]["ci_low"] == 10.6
    last = rows[-1]
    assert last["marriage_year"] == "2019～21年" and last["item"] == "その他・不詳"
    assert last["count"] == 1 and last["share_pct"] == 0.3 and last["ci_low"] == -0.3


def test_graph_rows_5_2_2_split_the_16th_round_into_two_periods() -> None:
    rows = ipss.graph_rows(graph("5_2_2"), "5_2_2")
    assert rows[0]["survey_round"] == 8 and rows[0]["survey_year"] == 1982
    assert rows[0]["period"] == "" and rows[0]["item"] == "学校で"
    assert rows[0]["count"] == 79 and rows[0]["share_pct"] == 6.1
    assert rows[0]["sex"] == "" and rows[0]["category"] == "知り合ったきっかけ"
    last = rows[-1]
    assert last["survey_round"] == 16 and last["survey_year"] == 2021
    assert last["period"] == "2018/7-2021/6" and last["item"] == "不詳"
    assert len({attitude_key(r) for r in rows}) == len(rows)


def _csv(lines: list[str]) -> bytes:
    return ("\r\n".join(lines) + "\r\n").encode("cp932")


HEAD_1_1_1 = [
    "報告書図表1-1-1 調査別にみた、未婚者の生涯の結婚意思",
    '"調査回","性別","生涯の結婚意思","度数","割合","標準誤差","95%信頼区間上限","95%信頼区間下限"',
]


def test_graph_rows_treat_dash_empty_and_na_as_null() -> None:
    rows = ipss.graph_rows(
        _csv(
            [
                *HEAD_1_1_1,
                '"第8回(1982)","男性","いずれ結婚するつもり","2620","95.9","-","","NA"',
            ]
        ),
        "1_1_1",
    )
    assert rows[0]["se"] is None and rows[0]["ci_high"] is None and rows[0]["ci_low"] is None


def test_graph_rows_fail_closed_on_title_header_round_sex_numbers_and_duplicates() -> None:
    with pytest.raises(ValueError, match="title"):
        ipss.graph_rows(graph("1_1_2"), "1_1_1")
    with pytest.raises(ValueError, match="header"):
        ipss.graph_rows(_csv([HEAD_1_1_1[0], '"調査回","性別","結婚意思","度数","割合"']), "1_1_1")
    with pytest.raises(ValueError, match="unknown figure"):
        ipss.graph_rows(graph("1_1_1"), "9_9_9")
    row = '"{r}","{s}","いずれ結婚するつもり","2620","95.9","0.4","96.6","95.2"'
    with pytest.raises(ValueError, match="round"):
        ipss.graph_rows(_csv([*HEAD_1_1_1, row.format(r="第8回(1983)", s="男性")]), "1_1_1")
    with pytest.raises(ValueError, match="round"):
        ipss.graph_rows(_csv([*HEAD_1_1_1, row.format(r="第17回(2026)", s="男性")]), "1_1_1")
    with pytest.raises(ValueError, match="sex"):
        ipss.graph_rows(_csv([*HEAD_1_1_1, row.format(r="第8回(1982)", s="男")]), "1_1_1")
    with pytest.raises(ValueError, match="non-numeric"):
        ipss.graph_rows(
            _csv(
                [*HEAD_1_1_1, '"第8回(1982)","男性","いずれ結婚するつもり","abc","95.9","","",""']
            ),
            "1_1_1",
        )
    with pytest.raises(ValueError, match="columns"):
        ipss.graph_rows(
            _csv([*HEAD_1_1_1, '"第8回(1982)","男性","いずれ結婚するつもり","2620"']), "1_1_1"
        )
    good = row.format(r="第8回(1982)", s="男性")
    with pytest.raises(ValueError, match="duplicate"):
        ipss.graph_rows(_csv([*HEAD_1_1_1, good, good]), "1_1_1")
    with pytest.raises(ValueError, match="empty"):
        ipss.graph_rows(_csv(HEAD_1_1_1), "1_1_1")
    with pytest.raises(ValueError, match="cp932"):
        ipss.graph_rows("報告書図表1-1-1 x\r\n".encode("utf-16"), "1_1_1")


def test_build_attitudes_mart_combines_all_figures_sorts_and_rejects_duplicates() -> None:
    parts = {f: ipss.graph_rows(graph(f), f) for f in ipss.GRAPH_FILES}
    mart = ipss.build_attitudes_mart(parts)
    assert len(mart) == 12 * 12
    assert ipss.ATTITUDES_KEY == (
        "figure",
        "survey_round",
        "period",
        "marriage_year",
        "sex",
        "age",
        "category",
        "item",
        "sub",
    )
    keys = [attitude_key(r) for r in mart]
    assert len(set(keys)) == len(keys)
    figs = [str(r["figure"]) for r in mart]
    assert figs == sorted(figs, key=ipss.GRAPH_FILES.index)
    assert mart[0]["figure"] == "1_1_1" and mart[-1]["figure"] == "12_1_2"
    rounds = [r["survey_round"] for r in mart if r["figure"] == "1_1_1"]
    assert rounds == sorted(rounds, key=lambda x: int(str(x)))
    with pytest.raises(ValueError, match="duplicate"):
        ipss.build_attitudes_mart({"a": parts["1_1_1"], "b": parts["1_1_1"][:1]})
