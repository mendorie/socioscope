"""ParlGov tab・UK Bills API・仏 AN ドシエ zip の純粋変換。

行・ページ・zip は実データの様式を縮約した合成（2026-10-28 確認）。"""

import io
import json
import zipfile

import pytest

from theme_parliament_size import fran, parlgov, ukbills, worldbank

# ---- ParlGov ------------------------------------------------------------------------------------

PG_HEADER = (
    "country_name_short\tcountry_name\telection_type\telection_date\tvote_share\tseats\t"
    "seats_total\tparty_name_short\tcountry_id\telection_id\tparty_id"
)


def pg_payload(rows: list[str]) -> bytes:
    return ("\n".join([PG_HEADER, *rows]) + "\n").encode()


def test_parlgov_parse_keeps_parliament_elections_one_row_per_election() -> None:
    rows = [
        '"JPN"\t"Japan"\t"parliament"\t2017-10-22\t33.3\t284\t465\t"LDP"\t1\t900\t10',
        '"JPN"\t"Japan"\t"parliament"\t2017-10-22\t19.9\t55\t465\t"CDP"\t1\t900\t11',
        '"JPN"\t"Japan"\t"ep"\t2019-05-26\t1.0\t1\t50\t"X"\t1\t901\t12',
        '"DEU"\t"Germany"\t"parliament"\t2021-09-26\t25.7\t206\t736\t"SPD"\t2\t902\t13',
    ]
    out = parlgov.parse(pg_payload(rows))
    assert out == [
        {"iso3": "DEU", "election_date": "2021-09-26", "election_id": 902, "seats_total": 736},
        {"iso3": "JPN", "election_date": "2017-10-22", "election_id": 900, "seats_total": 465},
    ]
    mart = parlgov.build_mart(out)
    assert mart[1]["year"] == 2017 and mart[1]["source"] == "parlgov"
    assert parlgov.URL.endswith("/api/access/datafile/10437092")


def test_parlgov_parse_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        parlgov.parse(b"a\tb\n1\t2\n")
    bad = ['"JPN"\t"Japan"\t"parliament"\t2017-10-22\t33.3\t284\tx\t"LDP"\t1\t900\t10']
    with pytest.raises(ValueError, match="non-numeric"):
        parlgov.parse(pg_payload(bad))
    two = [
        '"JPN"\t"Japan"\t"parliament"\t2017-10-22\t33.3\t284\t465\t"LDP"\t1\t900\t10',
        '"JPN"\t"Japan"\t"parliament"\t2017-10-22\t19.9\t55\t480\t"CDP"\t1\t900\t11',
    ]
    with pytest.raises(ValueError, match="differs within election"):
        parlgov.parse(pg_payload(two))


# ---- UK Bills API ------------------------------------------------------------------------------


def uk_bill(bid: int, type_id: int, is_act: bool, date: str = "2024-05-24") -> dict[str, object]:
    stage: dict[str, object] = (
        {
            "stageId": 11,
            "description": "Royal Assent",
            "stageSittings": [{"date": f"{date}T00:00:00"}],
        }
        if is_act
        else {"stageId": 7, "description": "2nd reading", "stageSittings": []}
    )
    return {
        "billId": bid,
        "shortTitle": f"Bill {bid}",
        "billTypeId": type_id,
        "introducedSessionId": 39,
        "isAct": is_act,
        "currentStage": stage,
    }


def uk_page(items: list[dict[str, object]], total: int) -> bytes:
    return json.dumps({"items": items, "totalResults": total}).encode()


def test_ukbills_url_paging_and_parse() -> None:
    assert ukbills.url(2) == "https://bills-api.parliament.uk/api/v1/Bills?Take=100&Skip=100"
    assert ukbills.raw_name(1) == "bills_p1.json"
    page = uk_page(
        [uk_bill(1, 1, True), uk_bill(2, 7, True, "2023-09-18"), uk_bill(3, 5, False)], 250
    )
    assert ukbills.has_next(page, 1) and ukbills.has_next(page, 2) and not ukbills.has_next(page, 3)
    rows = ukbills.parse(page, 1)
    assert [(r["bill_id"], r["origin"], r["is_act"], r["royal_assent_date"]) for r in rows] == [
        (1, "government", True, "2024-05-24"),
        (2, "member", True, "2023-09-18"),
        (3, "member", False, None),
    ]
    mart = ukbills.build_mart(rows)
    assert [(r["year"], r["bill_id"], r["iso3"]) for r in mart] == [
        (2023, 2, "GBR"),
        (2024, 1, "GBR"),
    ]
    assert ukbills.origin_of(6) == "other"


def test_ukbills_parse_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="not JSON"):
        ukbills.parse(b"<html>", 1)
    with pytest.raises(ValueError, match="missing 'items'"):
        ukbills.parse(b"{}", 1)
    act = uk_bill(9, 1, True)
    act["currentStage"] = {"stageId": 7, "stageSittings": []}
    with pytest.raises(ValueError, match="not at Royal Assent"):
        ukbills.parse(uk_page([act], 1), 1)
    with pytest.raises(ValueError, match="duplicate bill_id"):
        ukbills.build_mart(ukbills.parse(uk_page([uk_bill(1, 1, True), uk_bill(1, 1, True)], 2), 1))


# ---- 仏 AN ドシエ ------------------------------------------------------------------------------


def fr_dossier(uid: str, libelle: str, text_prefix: str, promulgated: str | None) -> bytes:
    actes: dict[str, object] = {
        "acteLegislatif": [
            {
                "codeActe": "AN1",
                "actesLegislatifs": {
                    "acteLegislatif": {
                        "codeActe": "AN1-DEPOT",
                        "texteAssocie": f"{text_prefix}ANR5L17B0001",
                    }
                },
            }
        ]
    }
    if promulgated:
        actes["acteLegislatif"].append(  # type: ignore[union-attr]
            {
                "codeActe": "PROM",
                "actesLegislatifs": {
                    "acteLegislatif": {
                        "codeActe": "PROM-PUB",
                        "dateActe": f"{promulgated}T00:00:00.000+02:00",
                    }
                },
            }
        )
    return json.dumps(
        {
            "dossierParlementaire": {
                "uid": uid,
                "legislature": "17",
                "procedureParlementaire": {"code": "2", "libelle": libelle},
                "actesLegislatifs": actes,
            }
        },
        ensure_ascii=False,
    ).encode()


def fr_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_fran_parse_classifies_origin_and_promulgation() -> None:
    payload = fr_zip(
        {
            "json/dossierParlementaire/A.json": fr_dossier(
                "A", "Proposition de loi ordinaire", "PION", "2026-04-21"
            ),
            "json/dossierParlementaire/B.json": fr_dossier(
                "B", "Projet de loi ordinaire", "PRJL", "2025-01-10"
            ),
            "json/dossierParlementaire/C.json": fr_dossier(
                "C", "Proposition de loi ordinaire", "PION", None
            ),
            "json/dossierParlementaire/D.json": fr_dossier("D", "Résolution", "PION", None),
            "json/dossierParlementaire/E.json": fr_dossier(
                "E", "Projet de ratification des traités et conventions", "PRJL", "2025-03-01"
            ),
            "json/document/X.json": b'{"document": {}}',
        }
    )
    rows = fran.parse(payload, 17)
    assert [(r["uid"], r["origin"], r["promulgated"], r["promulgation_date"]) for r in rows] == [
        ("A", "member", True, "2026-04-21"),
        ("B", "government", True, "2025-01-10"),
        ("C", "member", False, None),
        ("E", "government", True, "2025-03-01"),
    ]
    mart = fran.build_mart(rows)
    assert [(r["year"], r["uid"], r["origin"]) for r in mart] == [
        (2025, "B", "government"),
        (2025, "E", "government"),
        (2026, "A", "member"),
    ]
    # 立法期をまたぐ同じ uid は legislature の大きい方を残す
    dup = [*rows, {**rows[1], "legislature": 16, "promulgated": False, "promulgation_date": None}]
    assert [(r["uid"], r["legislature"]) for r in fran.build_mart(dup)] == [
        ("B", 17),
        ("E", 17),
        ("A", 17),
    ]
    assert fran.url(16).endswith("/16/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip")
    assert fran.raw_name(17) == "dossiers_legislatifs_L17.json.zip"


def test_fran_parse_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="not a zip"):
        fran.parse(b"<html>", 17)
    with pytest.raises(ValueError, match="no json/dossierParlementaire"):
        fran.parse(fr_zip({"json/document/X.json": b"{}"}), 17)


# ---- WDI 人口 ------------------------------------------------------------------------------------


def test_worldbank_population_variant() -> None:
    point = {
        "indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
        "country": {"id": "JP", "value": "Japan"},
        "countryiso3code": "JPN",
        "date": "2020",
        "value": 126261000.0,
    }
    body = json.dumps([{"page": 1, "pages": 1, "total": 1}, [point]]).encode()
    rows = worldbank.parse_population(body)
    assert rows == [{"iso3": "JPN", "country": "Japan", "year": 2020, "population": 126261000.0}]
    assert worldbank.build_population_mart(rows)[0]["population"] == 126261000.0
    assert worldbank.POP_URL.endswith("SP.POP.TOTL?format=json&per_page=20000&date=1980:2025")
