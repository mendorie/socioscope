import json
from pathlib import Path

import pytest

from theme_bicycle_industry import auto_moto as am

ROWS = json.loads((Path(__file__).parent / "fixtures" / "auto_moto_rows.json").read_text())


def _by(rows: list[dict[str, object]], key: str) -> dict[tuple[int, str], int]:
    return {(int(str(r["year"])), str(r[key])): int(str(r["units"])) for r in rows}


def test_zenkei_years_and_columns() -> None:
    k = _by(am.parse_zenkei_rows(ROWS["zenkei_kei4"], "kei4").rows, "segment")
    assert k[(1967, "kei4_total")] == 771_383 and k[(2025, "kei4_total")] == 1_667_360
    assert k[(2019, "kei4_passenger_group")] == 1_531_748  # 令和元年(19)
    m = _by(am.parse_zenkei_rows(ROWS["zenkei_moto2"], "moto2").rows, "segment")
    assert m[(2022, "moto_gt250")] == 100_889 and m[(2025, "moto_126_250")] == 61_990
    assert m[(1968, "moto_126_250")] == 23_464
    with pytest.raises(ValueError, match="header not recognised"):
        am.parse_zenkei_rows(ROWS["zenkei_moto2"], "kei4")
    with pytest.raises(ValueError, match="unknown zenkei key"):
        am.parse_zenkei_rows(ROWS["zenkei_kei4"], "x")


def test_jada_total_and_bytype() -> None:
    t = _by(am.parse_jada_rows(ROWS["jada_total"], "total").rows, "segment")
    assert t == {
        (2022, "registered_plus_kei_total"): 4_201_262,
        (2023, "registered_plus_kei_total"): 4_778_861,
        (2024, "registered_plus_kei_total"): 4_421_234,
        (2025, "registered_plus_kei_total"): 4_565_503,
    }
    b = _by(am.parse_jada_rows(ROWS["jada_bytype"], "bytype").rows, "segment")
    assert (
        b[(2025, "standard_passenger")] == 1_700_143 and b[(2021, "registered_total")] == 2_795_818
    )
    assert b[(2023, "passenger_subtotal")] == 2_651_397 and b[(2024, "truck_subtotal")] == 330_424
    with pytest.raises(ValueError, match="header not recognised"):
        am.parse_jada_rows(ROWS["jada_bytype"], "total")
    with pytest.raises(ValueError, match="row labels"):
        broken = [
            r if "バ" not in str(r[1]) else [*r[:1], "トラック", *r[2:]]
            for r in ROWS["jada_bytype"]
        ]
        am.parse_jada_rows(broken, "bytype")


def test_jaia_bands_sum_and_share() -> None:
    rows = am.parse_jaia_rows(ROWS["jaia_pricerange"]).rows
    j = _by(rows, "band")
    assert (
        j[(2025, "total")] == 241_189
        and j[(2025, "ge_2000")] == 10_791
        and j[(2019, "500_599")] == 37_913
    )
    mart = {(r["year"], r["band"]): r for r in am.build_jaia_mart(rows)}
    assert mart[(2025, "ge_2000")]["share"] == pytest.approx(10_791 / 241_189)
    broken = [
        [*r[:3], 999.0, *r[4:]] if str(r[1]).strip() == "2025年" and str(r[2]) == "台数" else r
        for r in ROWS["jaia_pricerange"]
    ]
    with pytest.raises(ValueError, match="do not sum"):
        am.parse_jaia_rows(broken)
    with pytest.raises(ValueError, match="band header"):
        am.parse_jaia_rows([["x"]])


def test_marts_unique_and_xls_guard() -> None:
    rows = am.parse_zenkei_rows(ROWS["zenkei_moto2"], "moto2").rows
    assert all(r["iso3"] == "JPN" for r in am.build_zenkei_mart(rows))
    with pytest.raises(ValueError, match="duplicate"):
        am.build_zenkei_mart(rows + rows[:1])
    with pytest.raises(ValueError, match="not a readable xls"):
        am.xls_rows(b"<html>")
