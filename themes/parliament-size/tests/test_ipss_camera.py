"""IPSS 結果表 1 と dati.camera.it SPARQL 結果の純粋変換。

実データの様式を縮約（2026-10-29 確認）。"""

import json

import pytest

from theme_parliament_size import camera, ipss

YEARS = [2020, 2025, 2030, 2035, 2040, 2045, 2050]


def ipss_rows(n_prefs: int = 47, total_2020: int = ipss.CENSUS_2020_TOTAL) -> list[list[object]]:
    rows: list[list[object]] = [
        ["結果表1　総人口および指数"],
        [],
        [],
        [
            "コード",
            "市などの別",
            "都道府県",
            "市区町村",
            "総人口（人）",
            "",
            "",
            "",
            "",
            "",
            "",
            "令和2（2020）年",
        ],
        ["", "", "", "", *[f"{y}年" for y in YEARS], "2020年", "2025年"],
    ]
    base = total_2020 // n_prefs
    for i in range(n_prefs):
        pop = base + (total_2020 - base * n_prefs if i == 0 else 0)
        rows.append(
            [f"{i + 1}000", "a", f"県{i + 1}", "", *[pop - k * 1000 for k in range(7)], 100, 99]
        )
        rows.append([f"{i + 1}100", "1", f"県{i + 1}", "市", *[1] * 7, 100, 99])  # 市は対象外
    return rows


def test_ipss_parse_keeps_47_prefectures_by_year_and_checks_the_2020_total() -> None:
    out = ipss.parse(ipss_rows())
    assert len(out) == 47 * 7
    assert out[0]["pref"] == "県1" and out[0]["year"] == 2020
    assert [r["year"] for r in out[:7]] == YEARS
    mart = ipss.build_mart(out)
    assert mart[0]["iso3"] == "JPN" and mart[0]["source"] == "ipss_regional"
    with pytest.raises(ValueError, match="expected 47"):
        ipss.parse(ipss_rows(n_prefs=46))
    with pytest.raises(ValueError, match="2020 total"):
        ipss.parse(ipss_rows(total_2020=100_000_000))
    with pytest.raises(ValueError, match="year header"):
        ipss.parse([["x"], ["y"]])


def sparql(pairs: list[tuple[str, str]]) -> bytes:
    return json.dumps(
        {
            "head": {"vars": ["y", "n"]},
            "results": {"bindings": [{"y": {"value": y}, "n": {"value": n}} for y, n in pairs]},
        }
    ).encode()


def test_camera_parse_and_mart() -> None:
    rows = camera.parse_laws(sparql([("2023", "83"), ("2022", "71")]))
    assert rows == [
        {"iso3": "ITA", "year": 2022, "metric": "laws_promulgated", "value": 71},
        {"iso3": "ITA", "year": 2023, "metric": "laws_promulgated", "value": 83},
    ]
    sit = camera.parse_sittings(sparql([("2023", "178")]))
    assert sit[0]["metric"] == "plenary_sittings"
    mart = camera.build_mart([*rows, *sit])
    assert [(r["metric"], r["year"]) for r in mart] == [
        ("laws_promulgated", 2022),
        ("laws_promulgated", 2023),
        ("plenary_sittings", 2023),
    ]
    assert camera.LAWS_URL.startswith("https://dati.camera.it/sparql?query=PREFIX")
    with pytest.raises(ValueError, match="no results"):
        camera.parse_laws(b'{"results": {"bindings": []}}')
    with pytest.raises(ValueError, match="numeric"):
        camera.parse_laws(sparql([("x", "1")]))
