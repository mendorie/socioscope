"""ILOSTAT JSON（レコード配列）の純粋変換。実 API の形を縮約（2026-10-28 確認）。"""

import json

import pytest

from theme_parliament_size import ilostat


def rec(area: str, cl: str, year: str, value: float | None) -> dict[str, object]:
    return {
        "ref_area": area,
        "source": "BA:15715",
        "indicator": "EMP_TEMP_SEX_ECO_NB",
        "sex": "SEX_T",
        "classif1": cl,
        "time": year,
        "obs_value": value,
        "note_source": "",
    }


def test_parse_keeps_adopted_classifications_as_long_rows() -> None:
    payload = json.dumps(
        [
            rec("JPN", "ECO_ISIC4_O", "2023", 2477.183),
            rec("JPN", "ECO_ISIC4_TOTAL", "2023", 67140.978),
            rec("JPN", "ECO_ISIC4_A", "2023", 1.0),  # 採用外
            rec("DEU", "ECO_ISIC4_O", "2025", None),  # 欠損
        ]
    ).encode()
    rows = ilostat.parse(payload)
    assert [(r["iso3"], r["metric"], r["year"], r["value_thousands"]) for r in rows] == [
        ("JPN", "emp_public_admin", 2023, 2477.183),
        ("JPN", "emp_total", 2023, 67140.978),
    ]
    mart = ilostat.build_mart(rows)
    assert mart[0]["source"] == "ilostat" and mart[0]["source_note"] == "BA:15715"
    assert "classif1=ECO_ISIC4_O+ECO_ISIC4_TOTAL" in ilostat.ECO_URL
    assert "classif1=INS_SECTOR_PUB" in ilostat.INS_URL


def test_parse_and_mart_are_fail_closed() -> None:
    with pytest.raises(ValueError, match="not JSON"):
        ilostat.parse(b"<html>")
    with pytest.raises(ValueError, match="JSON array"):
        ilostat.parse(b'{"error": "x"}')
    with pytest.raises(ValueError, match="record without"):
        ilostat.parse(json.dumps([{"ref_area": "JPN"}]).encode())
    rows = ilostat.parse(json.dumps([rec("JPN", "ECO_ISIC4_O", "2023", 1.0)] * 2).encode())
    with pytest.raises(ValueError, match="duplicate"):
        ilostat.build_mart(rows)
