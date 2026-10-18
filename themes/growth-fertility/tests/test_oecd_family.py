"""oecd_family.py: OECD Family Database SF2.5 childlessness workbook -> long rows (pure).

Fixture: the real ``SF_2-5-Childlessness.xlsx`` (2026-10-18) reduced to ten countries in
Chart SF2.5.A and six in Chart SF2.5.B, cell positions unchanged (including the duplicated
Poland row in Chart B and the non-member / non-country rows that must be dropped).
"""

import io
from pathlib import Path

import openpyxl
import pytest

from theme_growth_fertility import oecd, oecd_family

FIXTURE = (Path(__file__).parent / "fixtures" / "oecd_sf2_5_childlessness.xlsx").read_bytes()


def test_source_url_and_license_are_fixed() -> None:
    assert oecd_family.URL == (
        "https://webfs.oecd.org/Els-com/Family_Database/SF_2-5-Childlessness.xlsx"
    )
    assert oecd_family.RAW_NAME == "sf2_5_childlessness.xlsx"
    assert oecd_family.SOURCE == "oecd_family"
    assert oecd.LICENSE in oecd_family.LICENSE and "SF2.5" in oecd_family.LICENSE
    assert set(oecd_family.NAME_TO_ISO3.values()) <= set(oecd.OECD_MEMBERS) | {
        "CHN", "BGR", "HRV", "CYP", "MLT", "ROU",
    }  # fmt: skip


def by_key(rows: list[dict[str, object]]) -> dict[tuple[str, int, str, str], float]:
    return {
        (str(r["iso3"]), int(str(r["cohort"])), str(r["metric"]), str(r["chart"])): float(
            str(r["value"])
        )
        for r in rows
    }


def test_chart_a_gives_cohort_childlessness_for_members_and_drops_the_rest() -> None:
    rows, dropped = oecd_family.parse(FIXTURE)
    assert set(rows[0]) == {"iso3", "cohort", "metric", "value", "chart", "source"}
    assert all(r["source"] == "oecd_family" for r in rows)
    a = [r for r in rows if r["chart"] == "SF2.5.A"]
    assert {r["metric"] for r in a} == {"childless_share_pct"}
    assert {r["iso3"] for r in a} == {"DEU", "USA", "ITA", "FIN", "JPN", "KOR", "POL"}
    k = by_key(a)
    assert k["JPN", 1970, "childless_share_pct", "SF2.5.A"] == 26.9
    assert k["JPN", 1975, "childless_share_pct", "SF2.5.A"] == 28.3
    assert k["FIN", 1970, "childless_share_pct", "SF2.5.A"] == 20.6
    assert k["USA", 1935, "childless_share_pct", "SF2.5.A"] == 6.1
    assert k["DEU", 1955, "childless_share_pct", "SF2.5.A"] == 16
    assert ("DEU", 1960, "childless_share_pct", "SF2.5.A") not in k  # empty cell: no row
    assert sorted({int(str(r["cohort"])) for r in a if r["iso3"] == "USA"}) == [
        1935, 1940, 1945, 1950, 1955, 1960, 1963, 1964, 1965, 1970, 1975,
    ]  # fmt: skip
    assert sorted(dropped) == [
        "Chart SF2.5.A: Bulgaria (BGR) dropped: not an OECD member",
        "Chart SF2.5.A: China (CHN) dropped: not an OECD member",
        "Chart SF2.5.A: England and Wales dropped: not a country",
        "Chart SF2.5.B: Bulgaria (BGR) dropped: not an OECD member",
        "Chart SF2.5.B: Poland repeated with identical values (kept once)",
    ]


def test_chart_b_gives_childlessness_and_completed_fertility_for_the_1975_cohort() -> None:
    rows, _ = oecd_family.parse(FIXTURE)
    b = [r for r in rows if r["chart"] == "SF2.5.B"]
    assert {r["metric"] for r in b} == {"childless_share_pct", "completed_fertility"}
    assert {int(str(r["cohort"])) for r in b} == {1975}
    k = by_key(b)
    assert k["JPN", 1975, "childless_share_pct", "SF2.5.B"] == 28.3
    assert k["JPN", 1975, "completed_fertility", "SF2.5.B"] == 1.443
    assert k["USA", 1975, "completed_fertility", "SF2.5.B"] == 2.203
    assert k["POL", 1975, "childless_share_pct", "SF2.5.B"] == 19.9
    assert len([r for r in b if r["iso3"] == "POL"]) == 2  # the repeat is kept once


def _edit(mutate) -> bytes:  # type: ignore[no-untyped-def]
    wb = openpyxl.load_workbook(io.BytesIO(FIXTURE))
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


def _years_as_text(wb: openpyxl.Workbook) -> None:
    for cell in wb["Chart SF2.5.A"][5]:
        if isinstance(cell.value, int):
            cell.value = str(cell.value)


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (_rename("Chart SF2.5.A", "Chart A"), "Chart SF2.5.A"),
        (_rename("Chart SF2.5.B", "Chart B"), "Chart SF2.5.B"),
        (_set("Chart SF2.5.A", "R20", "Nippon"), "Nippon"),
        (_set("Chart SF2.5.A", "W20", "n.a."), "n.a."),
        (_years_as_text, "cohort"),
        (_set("Chart SF2.5.B", "A2", "Proportion (%) of cohort definitive childless"), "cohort"),
        (_set("Chart SF2.5.B", "N4", "Childless"), "Permanent childles"),
        (_set("Chart SF2.5.B", "M17", "FIN"), "Japan"),
        (_set("Chart SF2.5.B", "N27", 20.0), "Poland"),
    ],
    ids=[
        "sheet-a", "sheet-b", "unknown-name", "text-value", "no-cohort-header",
        "no-cohort-year", "no-b-header", "code-mismatch", "conflicting-repeat",
    ],
)  # fmt: skip
def test_layout_changes_fail_closed(mutate, match) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=match):
        oecd_family.parse(_edit(mutate))


def test_non_workbook_fails_closed() -> None:
    with pytest.raises(ValueError, match="workbook"):
        oecd_family.parse(b"<html>maintenance</html>")


def test_build_mart_sorts_by_key_and_rejects_duplicates() -> None:
    rows, _ = oecd_family.parse(FIXTURE)
    mart = oecd_family.build_mart(list(reversed(rows)))
    assert len(mart) == len(rows)
    keys = [(r["iso3"], r["cohort"], r["chart"], r["metric"]) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert set(mart[0]) == {"iso3", "cohort", "metric", "value", "chart", "source"}
    with pytest.raises(ValueError, match="duplicate"):
        oecd_family.build_mart([*rows, rows[0]])


# ---- H11: SF2.4 Share of births outside of marriage (annual sheet) ------------------------------
# Fixture: the real ``SF_2_4_Share_births_outside_marriage.xlsx`` (2026-10-18) reduced to the
# ``Births_outside_marriage`` sheet with ten member countries plus Bulgaria; cell positions
# unchanged (header row 4, years 1960–2024 in C..BO, legend and notes rows below the data).

FIXTURE_BOM = (
    Path(__file__).parent / "fixtures" / "oecd_sf2_4_births_outside_marriage.xlsx"
).read_bytes()


def test_bom_source_url_and_license_are_fixed() -> None:
    assert oecd_family.BOM_URL == (
        "https://webfs.oecd.org/Els-com/Family_Database/SF_2_4_Share_births_outside_marriage.xlsx"
    )
    assert oecd_family.BOM_RAW_NAME == "sf2_4_births_outside_marriage.xlsx"
    assert oecd.LICENSE in oecd_family.BOM_LICENSE
    assert "SF2.4 Share of births outside of marriage" in oecd_family.BOM_LICENSE
    assert "2026-10-18" in oecd_family.BOM_LICENSE
    assert oecd_family.BOM_METRIC == "births_outside_marriage_pct"


def bom_keyed(rows: list[dict[str, object]]) -> dict[tuple[str, int], float]:
    out = {(str(r["iso3"]), int(str(r["year"]))): float(str(r["value"])) for r in rows}
    assert len(out) == len(rows)
    return out


def test_parse_births_outside_marriage_gives_country_x_year_and_drops_non_members() -> None:
    rows, dropped = oecd_family.parse_births_outside_marriage(FIXTURE_BOM)
    assert set(rows[0]) == {"iso3", "year", "metric", "value", "chart", "source"}
    assert all(r["source"] == "oecd_family" for r in rows)
    assert {r["metric"] for r in rows} == {"births_outside_marriage_pct"}
    assert {r["chart"] for r in rows} == {"Births_outside_marriage"}
    assert {r["iso3"] for r in rows} == {
        "CZE", "DNK", "FRA", "IRL", "ITA", "JPN", "KOR", "ESP", "SWE", "USA",
    }  # fmt: skip
    assert len(rows) == 64 + 62 + 26 + 60 + 64 + 32 + 44 + 64 + 63 + 64
    k = bom_keyed(rows)
    assert k["JPN", 1960] == 1.2
    assert ("JPN", 1961) not in k  # '..' -> no row
    assert k["JPN", 2023] == 2.4
    assert ("JPN", 2024) not in k
    assert k["KOR", 1981] == pytest.approx(1.134874090538604)
    assert k["KOR", 2024] == pytest.approx(4.719860190933278)
    assert k["SWE", 1970] == 18.6
    assert k["USA", 2023] == 40
    assert k["DNK", 2021] == 54.7 and ("DNK", 2022) not in k
    assert k["FRA", 1998] == 41.7 and ("FRA", 1997) not in k
    assert min(y for _, y in k) == 1960 and max(y for _, y in k) == 2024
    assert dropped == ["Births_outside_marriage: Bulgaria (BGR) dropped: not an OECD member"]


def _edit_bom(mutate) -> bytes:  # type: ignore[no-untyped-def]
    wb = openpyxl.load_workbook(io.BytesIO(FIXTURE_BOM))
    mutate(wb)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _bom_set(cell: str, value: object):  # type: ignore[no-untyped-def]
    def mutate(wb: openpyxl.Workbook) -> None:
        wb["Births_outside_marriage"][cell] = value

    return mutate


def _bom_year_gap(wb: openpyxl.Workbook) -> None:
    wb["Births_outside_marriage"]["D4"] = 1962  # 1960, 1962, 1962, ...


def _bom_duplicate_country(wb: openpyxl.Workbook) -> None:
    wb["Births_outside_marriage"]["A5"] = "Japan"  # Czech Republic row relabelled


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (_rename("Births_outside_marriage", "Data"), "Births_outside_marriage"),
        (_bom_set("A4", "Economy"), "header"),
        (_bom_set("B4", "Remark"), "header"),
        (_bom_year_gap, "consecutive"),
        (_bom_set("A10", "Nippon"), "Nippon"),
        (_bom_set("BN10", "n.a."), "n.a."),
        (_bom_duplicate_country, "duplicate"),
    ],
    ids=["sheet", "no-country-header", "no-note-header", "year-gap", "unknown-name",
         "text-value", "duplicate-country"],
)  # fmt: skip
def test_bom_layout_changes_fail_closed(mutate, match) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match=match):
        oecd_family.parse_births_outside_marriage(_edit_bom(mutate))


def test_bom_non_workbook_fails_closed() -> None:
    with pytest.raises(ValueError, match="workbook"):
        oecd_family.parse_births_outside_marriage(b"<html>maintenance</html>")


def test_build_bom_mart_sorts_by_iso3_year_and_rejects_duplicates() -> None:
    rows, _ = oecd_family.parse_births_outside_marriage(FIXTURE_BOM)
    mart = oecd_family.build_births_outside_marriage_mart(list(reversed(rows)))
    assert len(mart) == len(rows)
    keys = [(r["iso3"], r["year"], r["chart"], r["metric"]) for r in mart]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert mart[0]["iso3"] == "CZE" and mart[0]["year"] == 1960
    with pytest.raises(ValueError, match="duplicate"):
        oecd_family.build_births_outside_marriage_mart([*rows, rows[0]])
