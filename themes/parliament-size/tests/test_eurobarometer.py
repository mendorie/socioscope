"""Eurobarometer Volume A の純粋変換。実ファイルの様式を縮約した合成シート（2026-10-31 確認）。"""

import io

import openpyxl
import pytest

from theme_parliament_size import eurobarometer as eb


def book(sheets: dict[str, list[list[object]]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


HEAD = [
    [None, None, "Volume A weighted"],
    [None, "QA6.7. How much trust do you have in certain institutions?"],
    [None, "The (NATIONALITY PARLIAMENT) (USE PROPER NAME FOR LOWER HOUSE)"],
    [None, "Base: All Respondents"],
    [],
    ["<<Back to content", None, "UE27\nEU27", "BE", "D-W", "DE", "IT", "UK", "n"],
    ["", "Total", 26525, 1136, 1241, 1542, 1026, 1000, 999],
]


def test_parse_reads_fraction_rows_and_maps_codes() -> None:
    rows = [
        *HEAD,
        [None, "Plutôt confiance", 9000, 500, 600, 700, 300, 350],
        [None, "Tend to trust", 0.36, 0.44, 0.48, 0.45, 0.29, 0.35, 12345],  # 国列の外は無視
    ]
    other = [
        [None, "QA6.1. trust"],
        [None, "Political parties"],
        *HEAD[5:],
        [None, "Tend to trust", 0.2],
    ]
    payload = book({"QA6_1": other, "QA6_7": rows})
    out = eb.parse(payload, eb.WAVES[-1])
    assert [(r["iso3"], r["value"]) for r in out] == [
        ("BEL", 44.0),
        ("DEU", 45.0),
        ("EU27", 36.0),
        ("GBR", 35.0),
        ("ITA", 29.0),
    ]
    assert out[0]["wave"] == 103 and out[0]["metric"] == "trust_national_parliament_pct"
    mart = eb.build_mart(out)
    assert mart[0]["source"] == "eurobarometer"
    with pytest.raises(ValueError, match="duplicate"):
        eb.build_mart(out + out)


def test_parse_takes_the_row_below_a_combined_label_and_percent_values() -> None:
    # EB93 の様式: 件数の行に「Plutôt confiance\nTend to trust」、次の行に割合
    rows = [
        *HEAD,
        [None, "Plutôt confiance\nTend to trust", 9673, 336, 640, 900, 301, 1],
        [None, None, 0.36, 0.33, 0.63, 0.58, 0.29, 0.01],
    ]
    out = eb.parse(book({"T45": rows}), eb.WAVES[2])
    assert {r["iso3"]: r["value"] for r in out}["ITA"] == 29.0
    # % がそのまま入っている様式と、2019 年の波の「EU28-UK」列
    head = [
        *HEAD[:5],
        ["", "", "UE28\nEU28", "UE28-UK\nEU28-UK", "IT"],
        ["", "TOTAL", 27464, 26432, 1026],
    ]
    rows = [*head, [None, "Tend to trust", 34.0, 36.0, 31.0]]
    out = {r["iso3"]: r["value"] for r in eb.parse(book({"QA6a.9": rows}), eb.WAVES[0])}
    assert out == {"EU27": 36.0, "EU28": 34.0, "ITA": 31.0}


def test_parse_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="not an Excel"):
        eb.parse(b"<html>", eb.WAVES[0])
    with pytest.raises(ValueError, match="not found"):
        eb.parse(book({"QA1": [[None, "something else"]]}), eb.WAVES[0])
    with pytest.raises(ValueError, match="Tend to trust"):
        eb.parse(book({"QA6_7": HEAD}), eb.WAVES[0])
    with pytest.raises(ValueError, match="no percentage"):
        eb.parse(
            book({"QA6_7": [*HEAD, [None, "Tend to trust", 9000, 500, 600, 700, 300, 350]]}),
            eb.WAVES[0],
        )
