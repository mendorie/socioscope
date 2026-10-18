"""eb_ideals.py: Special Eurobarometer 253 (2006) ideal number of children (pure).

Workbook fixtures are built in-test from the conftest BIFF8 builder, mirroring the two real
layouts: EB65.1 Volume C (one .xls per country inside a zip; QC2 / QC3 with sex and age
columns) and EB65.3 Volume A (one .xls; QE2 / QE3 with the candidate countries as columns).
The Finland and Bulgaria / Romania figures are the real weighted counts (checked 2026-10-18).
"""

import io
import zipfile
from collections.abc import Callable

import pytest

from theme_growth_fertility import eb_ideals
from theme_growth_fertility import eurobarometer as ebm

Builder = Callable[[dict[str, list[list[object]]]], bytes]

GENERAL_FR = (
    "QC2 En général, quel est, selon vous, le nombre idéal d'enfants par famille ? (NE PAS LIRE)"
)
GENERAL_EN = (
    "QC2 Generally speaking, what do you think is the ideal number of children for a family? "
    "(DO NOT PROMPT)"
)
PERSONAL_FR = (
    "QC3 Quel est le nombre idéal d'enfants que vous aimeriez personnellement avoir ou auriez "
    "aimé avoir ? (NE PAS LIRE)"
)
PERSONAL_EN = (
    "QC3 And for you personally, what would be the ideal number of children you would like to "
    "have or would have liked to have had? (DO NOT PROMPT)"
)
ANSWERS_FR = [
    "Aucun", "Un", "Deux", "Trois", "Quatre", "Cinq", "Six", "Plus de six",
    "Il n’y a pas de nombre idéal, cela dépend", "NSP",
]  # fmt: skip
ANSWERS_EN = [
    "None", "One ", "Two", "Three", "Four", "Five", "Six", "More than six",
    "There is no ideal number, it depends", "DK",
]  # fmt: skip

# Finland, EB65.1 Volume C: TOTAL / Male / Female / 15-24 / 25-39 / 40-54 / 55+ (weighted counts)
FI_PERSONAL: list[list[float]] = [
    [1004, 484, 519, 151, 239, 278, 336],
    [26, 8, 18, 9, 6, 9, 2],
    [61, 31, 30, 6, 10, 25, 21],
    [446, 240, 206, 65, 115, 117, 149],
    [278, 126, 151, 39, 72, 67, 99],
    [86, 33, 53, 9, 16, 28, 33],
    [25, 5, 21, 6, 4, 4, 12],
    [10, 0, 10, 1, 1, 6, 2],
    [13, 5, 8, 2, 2, 7, 1],
    [41, 22, 20, 7, 9, 15, 10],
    [17, 15, 2, 6, 4, 0, 7],
]
FI_GENERAL: list[list[float]] = [
    [1004, 484, 519, 151, 239, 278, 336],
    [2, 1, 1, 0, 1, 0, 1],
    [19, 9, 10, 0, 3, 9, 7],
    [430, 236, 193, 75, 110, 119, 127],
    [368, 158, 210, 47, 93, 94, 135],
    [75, 27, 48, 12, 12, 20, 30],
    [21, 6, 14, 5, 4, 4, 8],
    [3, 1, 2, 1, 1, 1, 0],
    [5, 1, 4, 2, 1, 1, 1],
    [66, 35, 32, 7, 11, 28, 19],
    [13, 9, 4, 2, 2, 2, 7],
]
# Bulgaria / Romania, EB65.3 Volume A (QE3 personal, QE2 general)
BG_RO_PERSONAL: list[list[float]] = [
    [1031, 1008], [6, 18], [102, 185], [684, 543], [147, 82], [14, 27], [3, 11], [3, 4],
    [0, 2], [40, 75], [33, 62],
]  # fmt: skip
BG_RO_GENERAL: list[list[float]] = [
    [1031, 1008], [3, 9], [67, 140], [650, 588], [168, 90], [19, 26], [1, 6], [2, 2],
    [1, 0], [69, 98], [51, 51],
]  # fmt: skip


def _share(v: float, total: float) -> object:
    return "- " if v == 0 else round(v / total, 2)


def vol_c_sheet(
    code: str,
    question_fr: str,
    question_en: str,
    counts: list[list[float]],
    *,
    country_title: str = "SUOMEN",
    extra_cols: tuple[str, ...] = (),
) -> list[list[object]]:
    """QC2 / QC3 sheet of a Volume C workbook (first 9 columns of the real 143)."""
    pad: list[object] = [""] * len(extra_cols)
    rows: list[list[object]] = [
        ["Index", "", "", "", "", "", f"EUROBAROMETER 65.1 - {country_title}"],
        ["", "", "VOLUME C", "", "", "", "", "", "", "", "", "", "Terrain/Fieldwork : 02-03/2006"],
        ["", question_fr, "", "B country code", "", "", "", "", "", "", question_en],
        [],
        [],
        [],
        [],
        [],
        ["", "", "", *pad, "Sexe", "", "Age"],
        ["", "", "", *pad, "-"],
        ["", "", "", *pad, "Sex"],
        ["", "", code, *pad, "Homme", "Femme", " 15-24", " 25-39", " 40-54", " 55 +", 15.0],
        [],
        ["", "", " ", *([" "] * len(extra_cols)), "-", "-"],
        ["", "", code, *extra_cols, "Male", "Female"],
        [],
    ]
    total = counts[0]
    extra_totals: list[object] = [1.0] * len(extra_cols)
    rows.append(["", "TOTAL", total[0], *extra_totals, *total[1:]])
    for fr, en, line in zip(ANSWERS_FR, ANSWERS_EN, counts[1:], strict=True):
        rows.append(["", fr, line[0], *([0.0] * len(extra_cols)), *line[1:]])
        rows.append(
            [
                "",
                en,
                _share(line[0], total[0]),
                *(["- "] * len(extra_cols)),
                *[_share(v, t) for v, t in zip(line[1:], total[1:], strict=True)],
            ]
        )
    return rows


def vol_a_sheet(
    codes: list[str], question_fr: str, question_en: str, counts: list[list[float]]
) -> list[list[object]]:
    """QE2 / QE3 sheet of the EB65.3 Volume A workbook (candidate countries as columns)."""
    blank9: list[object] = [""] * 9
    rows: list[list[object]] = [
        ["Index", "", "", "", "", "", "EUROBAROMETER 65.3"],
        ["", "", "VOLUME A Pondéré Weighted", *blank9, "Terrain/Fieldwork : 05-06/2006"],
        ["", question_fr.replace("QC", "QE"), *blank9[:8], question_en.replace("QC", "QE")],
        [],
        [],
        [],
        [],
        [],
        ["", "", "", *codes],
        ["", "TOTAL", "", *counts[0]],
    ]  # fmt: skip
    for fr, en, line in zip(ANSWERS_FR, ANSWERS_EN, counts[1:], strict=True):
        rows.append(["", fr, "", *line])
        rows.append(["", en, "", *[_share(v, t) for v, t in zip(line, counts[0], strict=True)]])
    return rows


INDEX_SHEET: list[list[object]] = [
    ["Q1!A1", "Q1 Quelle est votre nationalité ?", "", "", "Q1 What is your nationality?"],
    ["QC1!A1", "QC1 ...", "", "", "QC1 Which of the following suggestions ..."],
    ["QC2!A1", GENERAL_FR, "", "", GENERAL_EN],
    ["QC3!A1", PERSONAL_FR, "", "", PERSONAL_EN],
]


def country_xls(
    xls: Builder,
    code: str,
    personal: list[list[float]],
    general: list[list[float]],
    *,
    title: str = "SUOMEN",
    extra_cols: tuple[str, ...] = (),
) -> bytes:
    return xls(
        {
            "Index": INDEX_SHEET,
            "QC1": [
                ["Index", "", "", "", "", "", "EUROBAROMETER 65.1 - X"],
                ["", "", "VOLUME C"],
                ["", "QC1 ...", "", "", "", "", "", "", "", "", "QC1 Which ..."],
            ],  # fmt: skip
            "QC2": vol_c_sheet(
                code, GENERAL_FR, GENERAL_EN, general, country_title=title, extra_cols=extra_cols
            ),  # fmt: skip
            "QC3": vol_c_sheet(
                code, PERSONAL_FR, PERSONAL_EN, personal, country_title=title, extra_cols=extra_cols
            ),  # fmt: skip
        }
    )


def zip_of(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def vol_c_zip(xls: Builder) -> bytes:
    """Finland, Germany (national file + the East-Germany file that must be dropped)."""
    return zip_of(
        {
            "VolumeCFIEB651EMPLageingandfertility20060407.xls": country_xls(
                xls, "FI", FI_PERSONAL, FI_GENERAL
            ),
            "VolumeCDEEB651EMPLageingandfertility20060407.xls": country_xls(
                xls, "DE", FI_PERSONAL, FI_GENERAL, title="DEUTSCHLAND ", extra_cols=("D-W", "D-E")
            ),
            "VolumeCEGEB651EMPLageingandfertility20060407.xls": country_xls(
                xls, "D-E", FI_PERSONAL, FI_GENERAL, title="DEUTSCHLAND OST"
            ),
        }
    )


def vol_a_zip(xls: Builder) -> bytes:
    return zip_of(
        {
            "VolumeAEB653EMPLfertility20060627.xls": xls(
                {
                    "Index": [[r[0].replace("QC", "QE"), *r[1:]] for r in INDEX_SHEET],
                    "QE2": vol_a_sheet(["BG", "RO"], GENERAL_FR, GENERAL_EN, BG_RO_GENERAL),
                    "QE3": vol_a_sheet(["BG", "RO"], PERSONAL_FR, PERSONAL_EN, BG_RO_PERSONAL),
                }
            )
        }
    )


def ebs253() -> ebm.SpecialWave:
    return next(w for w in ebm.SPECIAL_WAVES if w.code == "EBS253")


def by_key(rows: list[dict[str, object]]) -> dict[tuple[str, str, str, str], dict[str, object]]:
    return {(str(r["iso3"]), str(r["sex"]), str(r["age_class"]), str(r["metric"])): r for r in rows}


# ---------------------------------------------------------------- Volume C (EB65.1)


def test_volume_c_gives_country_sex_and_age_rows_and_drops_sub_national_files(
    xls_from_sheets,
) -> None:  # type: ignore[no-untyped-def]
    rows, issues = eb_ideals.ideal_rows(vol_c_zip(xls_from_sheets), ebs253())
    assert {r["iso3"] for r in rows} == {"FIN", "DEU"}
    assert {(r["sex"], r["age_class"]) for r in rows} == {
        ("T", "total"), ("M", "total"), ("F", "total"),
        ("T", "15-24"), ("T", "25-39"), ("T", "40-54"), ("T", "55+"),
    }  # fmt: skip
    assert set(rows[0]) == {
        "iso3", "survey_year", "sex", "age_class", "metric", "value", "n", "table", "source"
    }  # fmt: skip
    assert all(r["survey_year"] == 2006 and r["source"] == ebm.SPECIAL_SOURCE for r in rows)
    assert len(rows) == 2 * 7 * len(eb_ideals.METRICS)
    assert issues == [
        "VolumeCEGEB651EMPLageingandfertility20060407.xls: D-E dropped "
        "(sub-national; the national file is used)"
    ]


def test_volume_c_mean_excludes_no_ideal_and_dk_and_keeps_face_values_above_four(
    xls_from_sheets,
) -> None:  # type: ignore[no-untyped-def]
    rows, _ = eb_ideals.ideal_rows(vol_c_zip(xls_from_sheets), ebs253())
    k = by_key(rows)
    # FI total personal: (61 + 2*446 + 3*278 + 4*86 + 5*25 + 6*10 + 7*13) / 945
    assert k["FIN", "T", "total", "ideal_personal_mean"]["value"] == 2.547
    assert k["FIN", "T", "total", "ideal_personal_mean"]["n"] == 1004
    assert k["FIN", "T", "total", "ideal_personal_mean"]["table"] == "QC3 (EB65.1 Volume C)"
    # women 25-39 is not a column: sex and age are separate breakdowns
    assert ("FIN", "F", "25-39", "ideal_personal_mean") not in k
    # age 25-39, both sexes: (10 + 230 + 216 + 64 + 20 + 6 + 14) / 226
    assert k["FIN", "T", "25-39", "ideal_personal_mean"]["value"] == 2.478
    assert k["FIN", "T", "25-39", "ideal_personal_mean"]["n"] == 239
    # general ideal, women: (10 + 386 + 630 + 192 + 70 + 12 + 28) / 482
    assert k["FIN", "F", "total", "ideal_general_mean"]["value"] == 2.755
    assert k["FIN", "F", "total", "ideal_general_mean"]["table"] == "QC2 (EB65.1 Volume C)"


def test_volume_c_shares_are_percent_of_all_respondents_from_counts(xls_from_sheets) -> None:  # type: ignore[no-untyped-def]
    rows, _ = eb_ideals.ideal_rows(vol_c_zip(xls_from_sheets), ebs253())
    k = by_key(rows)
    fi = {m: k["FIN", "T", "total", m]["value"] for m in eb_ideals.METRICS}
    assert fi["ideal_zero_share"] == 2.59  # 26 / 1004
    assert fi["ideal_one_share"] == 6.08
    assert fi["ideal_two_share"] == 44.42
    assert fi["ideal_three_share"] == 27.69
    assert fi["ideal_four_plus_share"] == 13.35  # (86 + 25 + 10 + 13) / 1004
    assert fi["ideal_no_ideal_share"] == 4.08
    assert fi["ideal_dk_share"] == 1.69
    assert fi["ideal_general_zero_share"] == 0.2  # 2 / 1004
    assert fi["ideal_general_two_share"] == 42.83
    assert k["FIN", "M", "total", "ideal_general_zero_share"]["value"] == 0.21  # 1 / 484


# ---------------------------------------------------------------- Volume A (EB65.3)


def test_volume_a_gives_total_rows_for_candidate_countries(xls_from_sheets) -> None:  # type: ignore[no-untyped-def]
    rows, issues = eb_ideals.ideal_rows(vol_a_zip(xls_from_sheets), ebs253())
    assert issues == []
    assert {r["iso3"] for r in rows} == {"BGR", "ROU"}
    assert {(r["sex"], r["age_class"]) for r in rows} == {("T", "total")}
    k = by_key(rows)
    # BG personal: (102 + 1368 + 441 + 56 + 15 + 18 + 0) / 959
    assert k["BGR", "T", "total", "ideal_personal_mean"]["value"] == 2.086
    assert k["BGR", "T", "total", "ideal_personal_mean"]["table"] == "QE3 (EB65.3 Volume A)"
    assert k["ROU", "T", "total", "ideal_general_dk_share"]["value"] == 5.06  # 51 / 1008
    assert k["ROU", "T", "total", "ideal_general_mean"]["n"] == 1008


# ---------------------------------------------------------------- fail closed


def test_sheets_without_the_ideal_questions_yield_nothing(xls_from_sheets) -> None:  # type: ignore[no-untyped-def]
    only_index = zip_of({"VolumeCFI.xls": xls_from_sheets({"Index": INDEX_SHEET})})
    assert eb_ideals.ideal_rows(only_index, ebs253()) == ([], [])


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda s: [r for r in s if not (r and r[1:2] == ["TOTAL"])], "TOTAL"),
        (lambda s: [r for r in s if not (r and r[1:2] == ["Three"])], "Three"),
        (lambda s: [r for r in s if not (r and r[1:2] == ["DK"])], "DK"),
        (lambda s: [[*r[:2], "ZZ", *r[3:]] if r[2:3] == ["FI"] else r for r in s], "ZZ"),
        (lambda s: [[*r[:4], "", *r[5:]] if "Femme" in r else r for r in s], "Femme"),
        (lambda s: [[*r[:2], 900.0, *r[3:]] if r[1:2] == ["TOTAL"] else r for r in s], "sum"),
        (lambda s: [[*r[:2], "n/a", *r[3:]] if r[1:2] == ["Deux"] else r for r in s], "Deux"),
        (lambda s: [[*r[:2], 44.0, *r[3:]] if r[1:2] == ["Two"] else r for r in s], "fraction"),
    ],
    ids=["no-total", "missing-answer", "missing-dk", "unknown-code", "missing-sex", "sum", "text",
         "share"],
)  # fmt: skip
def test_layout_changes_fail_closed(xls_from_sheets, mutate, match) -> None:  # type: ignore[no-untyped-def]
    sheet = mutate(vol_c_sheet("FI", PERSONAL_FR, PERSONAL_EN, FI_PERSONAL))
    payload = zip_of({"VolumeCFI.xls": xls_from_sheets({"QC3": sheet})})
    with pytest.raises(ValueError, match=match):
        eb_ideals.ideal_rows(payload, ebs253())


def test_duplicate_country_across_members_and_non_zip_fail_closed(xls_from_sheets) -> None:  # type: ignore[no-untyped-def]
    fi = country_xls(xls_from_sheets, "FI", FI_PERSONAL, FI_GENERAL)
    twice = zip_of({"VolumeCFI_a.xls": fi, "VolumeCFI_b.xls": fi})
    with pytest.raises(ValueError, match="duplicate"):
        eb_ideals.ideal_rows(twice, ebs253())
    with pytest.raises(ValueError, match="zip"):
        eb_ideals.ideal_rows(b"<html>maintenance</html>", ebs253())
    with pytest.raises(ValueError, match="workbook"):
        eb_ideals.ideal_rows(zip_of({"readme.txt": b"hi"}), ebs253())
