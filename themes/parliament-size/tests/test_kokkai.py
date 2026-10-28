"""国会会議録 API の会議一覧（実 API の形を縮約、2026-10-29 確認）。

ILOSTAT 賃金と WDI 1 人当たり GDP の変種も確かめる。"""

import json

import pytest

from theme_parliament_size import ilostat, kokkai, worldbank


def meeting(iid: str, date: str, name: str, house: str = "衆議院") -> dict[str, object]:
    return {
        "issueID": iid,
        "session": 216,
        "nameOfHouse": house,
        "nameOfMeeting": name,
        "issue": "第1号",
        "date": date,
        "speechRecord": [],
    }


def page(items: list[dict[str, object]], next_pos: int | None) -> bytes:
    return json.dumps(
        {
            "numberOfRecords": 592,
            "numberOfReturn": len(items),
            "startRecord": 1,
            "nextRecordPosition": next_pos,
            "meetingRecord": items,
        },
        ensure_ascii=False,
    ).encode()


def test_kokkai_url_paging_parse_and_mart() -> None:
    assert "from=2024-01-01" in kokkai.url(2024, 2) and "startRecord=101" in kokkai.url(2024, 2)
    assert kokkai.raw_name(2024, 1) == "meetings_2024_p1.json"
    p = page(
        [
            meeting("a", "2024-12-24", "本会議"),
            meeting("b", "2024-12-24", "予算委員会"),
            meeting("c", "2024-12-20", "法務委員会"),
            meeting("d", "2024-12-20", "参議院本会議", house="参議院"),  # 対象外
        ],
        next_pos=4,
    )
    assert kokkai.has_next(p) and not kokkai.has_next(page([], None))
    rows = kokkai.parse(p, 2024, 1)
    assert [(r["issue_id"], r["is_plenary"]) for r in rows] == [
        ("a", True),
        ("b", False),
        ("c", False),
    ]
    mart = kokkai.build_mart(rows)
    assert {(r["metric"], r["value"]) for r in mart} == {
        ("plenary_days", 1),
        ("committee_meetings", 2),
        ("committee_days", 2),
        ("sitting_days", 2),
    }
    with pytest.raises(ValueError, match="duplicate"):
        kokkai.build_mart(rows + rows)
    with pytest.raises(ValueError, match="missing meetingRecord"):
        kokkai.parse(b"{}", 2024, 1)


def test_ilostat_earnings_without_classif1() -> None:
    body = json.dumps(
        [
            {
                "ref_area": "JPN",
                "source": "x",
                "sex": "SEX_T",
                "classif1": "CUR_TYPE_LCU",
                "time": "2023",
                "obs_value": 342000.0,
            },
            {
                "ref_area": "JPN",
                "source": "x",
                "sex": "SEX_T",
                "classif1": "CUR_TYPE_USD",
                "time": "2023",
                "obs_value": 2400.0,
            },
        ]
    ).encode()
    rows = ilostat.parse_earnings(body)
    assert rows == [
        {
            "iso3": "JPN",
            "year": 2023,
            "metric": "earnings_monthly_lcu",
            "value_thousands": 342000.0,
            "source_note": "x",
        }
    ]
    assert "EAR_EMTA_SEX_CUR_NB_A" in ilostat.EAR_URL and "CUR_TYPE_LCU" in ilostat.EAR_URL


def test_worldbank_gdp_pcap_variant() -> None:
    point = {
        "indicator": {"id": "NY.GDP.PCAP.CN", "value": "GDP per capita (current LCU)"},
        "country": {"id": "JP", "value": "Japan"},
        "countryiso3code": "JPN",
        "date": "2025",
        "value": 5380358.0,
    }
    body = json.dumps([{"page": 1, "pages": 1, "total": 1}, [point]]).encode()
    rows = worldbank.parse_gdp_pcap(body)
    assert rows[0]["gdp_pcap_lcu"] == 5380358.0
    assert worldbank.build_gdp_pcap_mart(rows)[0]["gdp_pcap_lcu"] == 5380358.0
    assert worldbank.GDP_PCAP_URL.endswith(
        "NY.GDP.PCAP.CN?format=json&per_page=20000&date=2005:2025"
    )
