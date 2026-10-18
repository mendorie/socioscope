"""nhk.py (H12): NHK 放送文化研究所「日本人の意識」調査 Q49 結婚観 JSON -> long rows (pure,
fail-closed) and the mart. The fixture is the real ``q49.json`` cut to answers 01 / 02 and the
years 1993 / 2018 (every breakdown kept)."""

import json
from pathlib import Path

import pytest

from theme_growth_fertility import nhk

FIXTURES = Path(__file__).parent / "fixtures"
PAYLOAD = (FIXTURES / "nhk_q49.json").read_bytes()


def keyed(rows: list[dict[str, object]]) -> dict[tuple[object, ...], dict[str, object]]:
    out = {tuple(r[c] for c in nhk.MART_KEY): r for r in rows}
    assert len(out) == len(rows)
    return out


def edited(mutate) -> bytes:  # type: ignore[no-untyped-def]
    doc = json.loads(PAYLOAD)
    mutate(doc)
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def test_constants_fix_the_url_the_question_and_the_license() -> None:
    assert nhk.URL == "https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/data/q49.json"
    assert nhk.RAW_NAME == "q49.json"
    assert nhk.SOURCE == "nhk_nihonjin_ishiki"
    assert nhk.QUESTION == "q49"
    assert nhk.YEARS == (1993, 1998, 2003, 2008, 2013, 2018)
    assert nhk.AGE_LABELS == (
        "16-19歳",
        "20-29歳",
        "30-39歳",
        "40-49歳",
        "50-59歳",
        "60-69歳",
        "70歳以上",
    )
    assert "営利" in nhk.LICENSE and "加工して作成" in nhk.LICENSE
    assert "https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/" in nhk.LICENSE
    assert nhk.MART_KEY == ("question", "year", "answer_code", "group", "group_label")


def test_parse_gives_all_male_female_and_seven_age_groups_per_answer_and_year() -> None:
    rows = nhk.parse(PAYLOAD)
    assert len(rows) == 2 * 2 * 10
    assert set(rows[0]) == {
        "question",
        "year",
        "answer_code",
        "answer_label",
        "answer_short",
        "group",
        "group_label",
        "ratio_pct",
        "n",
        "source",
    }
    assert all(r["question"] == "q49" and r["source"] == "nhk_nihonjin_ishiki" for r in rows)
    k = keyed(rows)
    r = k[("q49", 1993, "01", "all", "")]
    assert r["answer_label"] == "甲に近い" and r["answer_short"] == "するのが当然"
    assert r["ratio_pct"] == 45.0 and r["n"] == 1701
    assert isinstance(r["ratio_pct"], float) and isinstance(r["n"], int)
    assert k[("q49", 1993, "01", "male", "")]["ratio_pct"] == 51.0
    assert k[("q49", 1993, "01", "female", "")]["ratio_pct"] == 39.0
    assert k[("q49", 1993, "01", "age", "16-19歳")]["ratio_pct"] == 25.0
    assert k[("q49", 1993, "01", "age", "16-19歳")]["n"] == 67
    assert k[("q49", 1993, "01", "age", "70歳以上")]["ratio_pct"] == 75.0
    assert k[("q49", 2018, "01", "all", "")]["ratio_pct"] == 27.0
    assert k[("q49", 2018, "01", "all", "")]["n"] == 740
    assert k[("q49", 2018, "01", "male", "")]["ratio_pct"] == 35.0
    assert k[("q49", 2018, "01", "female", "")]["ratio_pct"] == 20.0
    assert k[("q49", 2018, "02", "all", "")]["answer_short"] == "しなくてよい"
    assert k[("q49", 2018, "02", "all", "")]["ratio_pct"] == 68.0
    # cross / city / acad breakdowns are not taken
    assert {r["group"] for r in rows} == {"all", "male", "female", "age"}
    assert {r["year"] for r in rows} == {1993, 2018}


def test_parse_strips_the_small_sample_asterisk() -> None:
    def star(doc: dict[str, object]) -> None:
        y = doc["q49"][0]["q"][0]["a"][0]["year"]["2018"]  # type: ignore[index]
        y["ratio"]["age"][0] = "*9"
        y["number"]["age"][0] = "*9"

    k = keyed(nhk.parse(edited(star)))
    assert k[("q49", 2018, "01", "age", "16-19歳")]["ratio_pct"] == 9.0
    assert k[("q49", 2018, "01", "age", "16-19歳")]["n"] == 9


def test_parse_fails_closed_on_shape_years_groups_and_values() -> None:
    with pytest.raises(ValueError, match="json"):
        nhk.parse(b"not json")
    with pytest.raises(ValueError, match="q49"):
        nhk.parse(b'{"q50": []}')

    def two_questions(doc: dict[str, object]) -> None:
        doc["q49"][0]["q"].append(doc["q49"][0]["q"][0])  # type: ignore[index]

    with pytest.raises(ValueError, match="question"):
        nhk.parse(edited(two_questions))

    def bad_year(doc: dict[str, object]) -> None:
        a = doc["q49"][0]["q"][0]["a"][0]  # type: ignore[index]
        a["year"]["2022"] = a["year"].pop("2018")

    with pytest.raises(ValueError, match="2022"):
        nhk.parse(edited(bad_year))

    def short_age(doc: dict[str, object]) -> None:
        doc["q49"][0]["q"][0]["a"][0]["year"]["1993"]["ratio"]["age"].pop()  # type: ignore[index]

    with pytest.raises(ValueError, match="age"):
        nhk.parse(edited(short_age))

    def text_ratio(doc: dict[str, object]) -> None:
        doc["q49"][0]["q"][0]["a"][0]["year"]["1993"]["ratio"]["all"] = "n/a"  # type: ignore[index]

    with pytest.raises(ValueError, match="n/a"):
        nhk.parse(edited(text_ratio))

    def no_male(doc: dict[str, object]) -> None:
        del doc["q49"][0]["q"][0]["a"][0]["year"]["1993"]["ratio"]["male"]  # type: ignore[index]

    with pytest.raises(ValueError, match="male"):
        nhk.parse(edited(no_male))

    def dup_answer(doc: dict[str, object]) -> None:
        doc["q49"][0]["q"][0]["a"].append(doc["q49"][0]["q"][0]["a"][0])  # type: ignore[index]

    with pytest.raises(ValueError, match="duplicate"):
        nhk.parse(edited(dup_answer))


def test_build_mart_sorts_by_key_and_rejects_duplicates() -> None:
    rows = nhk.parse(PAYLOAD)
    mart = nhk.build_mart(list(reversed(rows)))
    assert len(mart) == len(rows)
    assert [tuple(r[c] for c in nhk.MART_KEY) for r in mart] == [
        tuple(r[c] for c in nhk.MART_KEY) for r in rows
    ]
    assert mart[0]["year"] == 1993 and mart[0]["answer_code"] == "01" and mart[0]["group"] == "all"
    assert mart[1]["group"] == "male" and mart[2]["group"] == "female"
    assert mart[3]["group"] == "age" and mart[3]["group_label"] == "16-19歳"
    assert mart[9]["group_label"] == "70歳以上"
    with pytest.raises(ValueError, match="duplicate"):
        nhk.build_mart([*rows, rows[0]])
