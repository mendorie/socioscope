"""Dingel-Neiman (2020) teleworkability by occupation, mapped onto Census 2018 occupation codes."""

from pathlib import Path

import pytest

from socioscope_core.core.pipeline import Context
from socioscope_core.testing.fakes import FakeFetcher, InMemoryRawStore, InMemoryTableStore
from theme_essential_work_wages import acs
from theme_essential_work_wages import teleworkable as tw
from theme_essential_work_wages.pipeline import THEME

FIX = Path(__file__).parent / "fixtures"


def payload() -> bytes:
    return (FIX / "occupations_workathome_head.csv").read_bytes()


def make_ctx(resp: dict[str, bytes] | None = None) -> Context:
    return Context(
        fetcher=FakeFetcher(resp or {}), raw=InMemoryRawStore(), tables=InMemoryTableStore()
    )


def code(occ: str, soc: str, title: str, soc2010: str = "") -> dict[str, object]:
    return {
        "occupation_code": occ,
        "occupation": title,
        "soc_code": soc,
        "soc_2010_codes": soc2010,
        "classification": acs.CLASSIFICATION,
    }


CODES: list[dict[str, object]] = [
    code("0010", "11-1011", "Chief Executives", "11-1011"),
    code("0020", "11-1021", "General and Operations Managers", "11-1021"),
    code("0040", "11-2011", "Advertising and Promotions Managers", "11-2011"),
    code("0120", "11-3031", "Financial Managers", "11-3031"),
    code("0205", "11-9013", "Farmers, Ranchers, and Other Agricultural Managers", "11-9013"),
    code("0310", "11-9051", "Food Service Managers", "11-9051"),
]


# ---- constants / fetch


def test_constants() -> None:
    assert tw.SOURCE == "dingel_neiman"
    assert tw.URL == (
        "https://raw.githubusercontent.com/jdingel/DingelNeiman-workathome/master/"
        "occ_onet_scores/output/occupations_workathome.csv"
    )
    assert tw.RAW_NAME == "occupations_workathome.csv"
    assert tw.MAGIC == b"onetsoccode"
    assert "GPL" in tw.LICENSE
    assert tw.MART_TABLE == "marts/us_occupation_teleworkable"


def test_fetch_puts_the_csv_with_license() -> None:
    ctx = make_ctx({tw.URL: payload()})
    written, skipped = tw.fetch(ctx, [], [])
    assert written == [f"{THEME}/{tw.SOURCE}/{tw.RAW_NAME}"]
    assert skipped == []
    rec = ctx.raw.records()[0]
    assert (rec.url, rec.license) == (tw.URL, tw.LICENSE)
    assert ctx.raw.get(theme=THEME, source=tw.SOURCE, name=tw.RAW_NAME) == payload()


def test_fetch_rejects_non_csv_payload_and_reports_fetch_error() -> None:
    ctx = make_ctx({tw.URL: b"<html>rate limited</html>"})
    written, skipped = tw.fetch(ctx, [], [])
    assert (written, skipped) == ([], [f"{tw.RAW_NAME}: non-csv payload"])
    assert ctx.raw.records() == []
    ctx = make_ctx()
    written, skipped = tw.fetch(ctx, [], [])
    assert written == []
    assert skipped[0].startswith(f"{tw.RAW_NAME}: ")


# ---- pure transforms


def test_parse_reads_onet_code_title_and_score() -> None:
    rows = tw.parse(payload())
    assert len(rows) == 10
    assert rows[0] == {
        "onetsoccode": "11-1011.00",
        "title": "Chief Executives",
        "teleworkable": 1.0,
    }
    assert rows[5] == {
        "onetsoccode": "11-3031.02",
        "title": "Financial Managers, Branch or Department",
        "teleworkable": 1.0,
    }
    assert rows[6]["teleworkable"] == 0.0


@pytest.mark.parametrize(
    "bad",
    [
        b"code,title,teleworkable\n11-1011.00,x,1\n",  # wrong header
        b"onetsoccode,title,teleworkable\n111011,x,1\n",  # not an O*NET-SOC code
        b"onetsoccode,title,teleworkable\n11-1011.00,x,2\n",  # outside [0, 1]
        b"onetsoccode,title,teleworkable\n11-1011.00,x,\n",  # empty score
        b"onetsoccode,title,teleworkable\n11-1011.00,x,1\n11-1011.00,y,0\n",  # duplicate
    ],
)
def test_parse_rejects_bad_input(bad: bytes) -> None:
    with pytest.raises(ValueError):
        tw.parse(bad)


def test_soc_prefix_strips_trailing_zero_or_x_placeholders() -> None:
    assert tw.soc_prefix("11-1011") == "11-1011"
    assert tw.soc_prefix("13-1020") == "13-102"
    assert tw.soc_prefix("11-9030") == "11-903"
    assert tw.soc_prefix("13-20XX") == "13-20"
    assert tw.soc_prefix("19-40XX") == "19-40"
    assert tw.soc_prefix("51-4XXX") == "51-4"
    assert tw.soc_prefix("none") is None


def test_build_mart_averages_onet_to_soc6_then_soc6_to_census() -> None:
    out = tw.build_mart(tw.parse(payload()), CODES)
    assert [tuple(r) for r in out] == [
        (
            "occupation_code",
            "occupation",
            "classification",
            "soc_code",
            "teleworkable",
            "n_onet",
            "source",
        )
    ] * 6
    by = {r["occupation_code"]: r for r in out}
    assert by["0010"]["teleworkable"] == 1.0
    assert by["0010"]["n_onet"] == 2  # 11-1011.00 + 11-1011.03
    assert by["0120"] == {
        "occupation_code": "0120",
        "occupation": "Financial Managers",
        "classification": acs.CLASSIFICATION,
        "soc_code": "11-3031",
        "teleworkable": 1.0,
        "n_onet": 2,
        "source": "dingel_neiman_2020",
    }
    assert by["0205"]["teleworkable"] == 0.0
    assert by["0205"]["n_onet"] == 3
    assert by["0310"]["teleworkable"] == 0.0


def test_build_mart_uses_mean_of_soc6_means_for_broad_codes() -> None:
    dn = [
        {"onetsoccode": "11-1011.00", "title": "a", "teleworkable": 1.0},
        {"onetsoccode": "11-1011.03", "title": "b", "teleworkable": 0.0},
        {"onetsoccode": "11-1021.00", "title": "c", "teleworkable": 1.0},
    ]
    codes = [code("0010", "11-1010", "Top executives"), code("0011", "11-10XX", "Top execs")]
    by = {r["occupation_code"]: r for r in tw.build_mart(dn, codes)}
    assert by["0010"]["teleworkable"] == 0.5
    assert by["0010"]["n_onet"] == 2
    assert by["0011"]["teleworkable"] == pytest.approx(0.75)  # mean(0.5, 1.0), not 2/3
    assert by["0011"]["n_onet"] == 3


def test_build_mart_falls_back_to_2010_soc_codes_from_the_crosswalk() -> None:
    # D-N is SOC 2010: 15-1131 (programmers) vs. Census 2018 15-1251.
    dn = [{"onetsoccode": "15-1131.00", "title": "Computer Programmers", "teleworkable": 1.0}]
    codes = [code("1010", "15-1251", "Computer Programmers", "15-1131")]
    (row,) = tw.build_mart(dn, codes)
    assert (row["teleworkable"], row["n_onet"]) == (1.0, 1)


def test_build_mart_leaves_soc_none_without_a_value_and_excludes_it_from_the_rate() -> None:
    dn = tw.parse(payload())
    codes = [*CODES, code("9830", "none", "Military, Rank Not Specified")]
    by = {r["occupation_code"]: r for r in tw.build_mart(dn, codes)}
    assert by["9830"]["teleworkable"] is None
    assert by["9830"]["n_onet"] == 0


def test_build_mart_rejects_match_rate_below_95_percent() -> None:
    codes = [*CODES, code("0030", "11-1031", "Legislators", "11-1031")]  # O*NET has no 11-1031
    with pytest.raises(ValueError, match="match rate"):
        tw.build_mart(tw.parse(payload()), codes)


def test_build_mart_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError):
        tw.build_mart([], CODES)
    with pytest.raises(ValueError):
        tw.build_mart(tw.parse(payload()), [])


# ---- stage / mart through the ports


def test_stage_reports_no_raw() -> None:
    ctx = make_ctx()
    assert tw.stage(ctx, [], []) == ([], [f"{tw.RAW_NAME}: no raw"])
    assert ctx.tables.list_tables() == []


def test_stage_writes_the_staged_table() -> None:
    ctx = make_ctx({tw.URL: payload()})
    tw.fetch(ctx, [], [])
    written, skipped = tw.stage(ctx, [], [])
    assert (written, skipped) == ([tw.STAGED_TABLE], [])
    assert ctx.tables.read_table(tw.STAGED_TABLE) == tw.parse(payload())


def test_mart_skips_when_staged_or_acs_codes_are_missing() -> None:
    ctx = make_ctx()
    assert tw.mart(ctx, [], []) == ([], [f"{tw.STAGED_TABLE}: no staged table"])
    ctx.tables.write_table(tw.STAGED_TABLE, tw.parse(payload()))
    assert tw.mart(ctx, [], []) == ([], [f"{acs.CODES_TABLE}: no staged table"])
    assert tw.MART_TABLE not in ctx.tables.list_tables()


def test_fetch_stage_mart_end_to_end() -> None:
    ctx = make_ctx({tw.URL: payload()})
    ctx.tables.write_table(acs.CODES_TABLE, CODES)
    tw.fetch(ctx, [], [])
    tw.stage(ctx, [], [])
    written, skipped = tw.mart(ctx, [], [])
    assert (written, skipped) == ([tw.MART_TABLE], [])
    rows = ctx.tables.read_table(tw.MART_TABLE)
    assert [r["occupation_code"] for r in rows] == [c["occupation_code"] for c in CODES]
    assert {r["source"] for r in rows} == {"dingel_neiman_2020"}
