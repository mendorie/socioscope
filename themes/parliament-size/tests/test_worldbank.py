"""World Bank WDI（GDP 現地通貨）の純粋変換。実 API の [meta, data] 形（2026-10-27 確認）を縮約。"""

import json

import pytest

from theme_parliament_size import worldbank


def _point(iso3: str, cc: str, name: str, year: str, value: float | None) -> dict[str, object]:
    return {
        "indicator": {"id": "NY.GDP.MKTP.CN", "value": "GDP (current LCU)"},
        "country": {"id": cc, "value": name},
        "countryiso3code": iso3,
        "date": year,
        "value": value,
        "unit": "",
        "obs_status": "",
        "decimal": 0,
    }


def payload(points: list[dict[str, object]], pages: int = 1) -> bytes:
    meta = {"page": 1, "pages": pages, "per_page": 20000, "total": len(points)}
    return json.dumps([meta, points]).encode()


def test_url_and_names() -> None:
    assert worldbank.URL == (
        "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CN"
        "?format=json&per_page=20000&date=2005:2025"
    )
    assert worldbank.RAW_NAME == "gdp_lcu_2005_2025.json"
    assert worldbank.MAGIC == b"["


def test_parse_keeps_valued_points_as_iso3_year_rows_sorted() -> None:
    rows = worldbank.parse(
        payload(
            [
                _point("JPN", "JP", "Japan", "2024", 634226000000000.0),
                _point("JPN", "JP", "Japan", "2023", 616033000000000.0),
                _point("DEU", "DE", "Germany", "2024", None),
                _point("", "1A", "Arab World", "2024", 1.0),  # 集計体（iso3 空）は落とす
            ]
        )
    )
    assert rows == [
        {"iso3": "JPN", "country": "Japan", "year": 2023, "gdp_lcu": 616033000000000.0},
        {"iso3": "JPN", "country": "Japan", "year": 2024, "gdp_lcu": 634226000000000.0},
    ]


@pytest.mark.parametrize(
    ("bad", "msg"),
    [
        (b"<html>", "not JSON"),
        (json.dumps({"message": "x"}).encode(), "shape"),
        (payload([], pages=2), "paginated"),
        (json.dumps([{"page": 1, "pages": 1, "total": 1}, [{"date": "x"}]]).encode(), "point"),
    ],
)
def test_parse_is_fail_closed(bad: bytes, msg: str) -> None:
    with pytest.raises(ValueError, match=msg):
        worldbank.parse(bad)


def test_build_mart_adds_keys_and_source() -> None:
    staged = [
        {
            "iso3": "JPN",
            "country": "Japan",
            "year": 2024,
            "gdp_lcu": 1.0,
            "source": worldbank.SOURCE,
        }
    ]
    assert worldbank.build_mart(staged) == [
        {
            "iso3": "JPN",
            "year": 2024,
            "country": "Japan",
            "gdp_lcu": 1.0,
            "source": worldbank.SOURCE,
        }
    ]
