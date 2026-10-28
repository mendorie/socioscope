import pytest

from theme_parliament_size import estat

PREFS = [f"{i:02d}000_県{i}" for i in range(1, 48)]


def sheet(
    drop_japanese_for: str | None = None, national_total: float | None = None
) -> list[tuple[str, estat.Rows]]:
    rows: estat.Rows = [
        ["令和２年国勢調査　人口等基本集計"],
        ["第２－１表　…"],
        [],
        ["国籍総数か日本人", "男女", "地域識別コード", "地域名", ""],
    ]
    total = 0.0
    jp = 0.0
    body: estat.Rows = []
    for i, area in enumerate(PREFS, start=1):
        t, j = 1000.0 * i, 900.0 * i
        total += t
        jp += j
        body.append(["0_国籍総数", "0_総数", "a", area, t, 1, 2])
        body.append(["0_国籍総数", "1_男", "a", area, t / 2, 1, 2])
        body.append(["0_国籍総数", "0_総数", "1", f"{i:02d}100_市{i}", t / 3, 1, 2])  # 市は除く
        if area != drop_japanese_for:
            body.append(["1_うち日本人", "0_総数", "a", area, j, 1, 2])
    rows.append(["0_国籍総数", "0_総数", "a", "00000_全国", national_total or total, 1, 2])
    rows.append(["1_うち日本人", "0_総数", "a", "00000_全国", jp, 1, 2])
    rows += body
    return [("b02_01", rows)]


def test_parse_reads_total_and_japanese_population_for_47_prefectures() -> None:
    out = estat.parse(sheet())
    assert len(out) == 47
    assert out[0] == {
        "pref_code": "01",
        "pref": "県1",
        "population_total": 1000.0,
        "population_japanese": 900.0,
    }
    assert out[-1]["pref_code"] == "47"


def test_parse_fails_closed() -> None:
    with pytest.raises(ValueError, match="lacks total or japanese"):
        estat.parse(sheet(drop_japanese_for=PREFS[3]))
    with pytest.raises(ValueError, match="!= national"):
        estat.parse(sheet(national_total=1.0))
    with pytest.raises(ValueError, match="expected 47"):
        estat.parse([("s", sheet()[0][1][:30])])
    with pytest.raises(ValueError, match="no sheet"):
        estat.parse([])


def test_build_mart_adds_keys_and_sorts_by_code() -> None:
    staged = list(reversed(estat.parse(sheet())))
    mart = estat.build_mart(staged)
    assert [r["pref_code"] for r in mart][:3] == ["01", "02", "03"]
    assert (
        mart[0]["iso3"] == "JPN" and mart[0]["year"] == 2020 and mart[0]["source"] == "estat_census"
    )
    with pytest.raises(ValueError, match="distinct"):
        estat.build_mart(staged[:46])


def longpop_sheet(last: int = 2000) -> list[tuple[str, estat.Rows]]:
    rows: estat.Rows = [["第１表 男女別人口"], [], ["", "", "", "総人口", "", "", "日本人人口"]]
    for y in range(1920, last + 1):
        jp: object = "－" if y < 1950 else 1000.0 * (y - 1900) * 0.98
        rows.append([f"{y}年", y, "", 1000.0 * (y - 1900), 1.0, 1.0, jp, 1.0, 1.0])
    rows.append(["注", "", "", "", "", "", ""])
    return [("第1表", rows)]


def test_parse_longpop_reads_yearly_totals_and_optional_japanese() -> None:
    out = estat.parse_longpop(longpop_sheet())
    assert len(out) == 81
    assert out[0] == {
        "year": 1920,
        "population_total_thousands": 20000.0,
        "population_japanese_thousands": None,
    }
    assert out[-1]["year"] == 2000 and out[-1]["population_japanese_thousands"] == pytest.approx(
        98000.0
    )
    with pytest.raises(ValueError, match="1920..2000"):
        estat.parse_longpop(longpop_sheet(last=1999))
    mart = estat.build_longpop_mart(list(reversed(out)))
    assert mart[0]["year"] == 1920 and mart[0]["iso3"] == "JPN"
