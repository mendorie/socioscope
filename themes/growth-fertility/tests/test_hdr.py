from pathlib import Path

import pytest

from theme_growth_fertility import hdr

FIXTURES = Path(__file__).parent / "fixtures"
CSV = (FIXTURES / "hdr25_composite.csv").read_bytes()
COLUMNS = {"iso3", "country", "year", "metric", "value", "source"}


def test_fixed_url_raw_name_license_and_metrics() -> None:
    assert hdr.URL == (
        "https://hdr.undp.org/sites/default/files/2025_HDR/"
        "HDR25_Composite_indices_complete_time_series.csv"
    )
    assert hdr.RAW_NAME == "hdr25_composite_indices.csv"
    assert hdr.SOURCE == "undp_hdr"
    assert "CC BY 3.0 IGO" in hdr.LICENSE and "https://hdr.undp.org/terms-use" in hdr.LICENSE
    assert hdr.METRICS == ("gii", "mmr", "abr", "se_f", "se_m", "pr_f", "pr_m", "lfpr_f", "lfpr_m")


def test_rows_are_long_per_metric_year_decoded_latin1_and_aggregates_dropped() -> None:
    parsed = hdr.parse(CSV)
    rows = parsed.rows
    assert parsed.dropped_areas == ("ZZK.WORLD World",)
    assert {r["iso3"] for r in rows} == {"JPN", "KOR", "SWE", "TUR", "USA"}
    assert next(r["country"] for r in rows if r["iso3"] == "TUR") == "Türkiye"
    assert set(rows[0]) == COLUMNS
    assert rows[0] == {
        "iso3": "JPN",
        "country": "Japan",
        "year": 2000,
        "metric": "abr",
        "value": 5.532,
        "source": "undp_hdr",
    }
    assert {r["metric"] for r in rows} == set(hdr.METRICS)
    assert {r["year"] for r in rows} == {2000, 2010, 2023}
    jpn_gii = [(r["year"], r["value"]) for r in rows if r["iso3"] == "JPN" and r["metric"] == "gii"]
    assert jpn_gii == [(2000, 0.15), (2010, 0.118), (2023, 0.059)]
    # non-metric columns (hdi_*, hdicode, region, ranks) are ignored
    assert len(rows) == 5 * 9 * 3 - parsed.blank_cells
    keys = [hdr.mart_key(r) for r in rows]
    assert keys == sorted(keys)


def test_parse_fails_closed_on_header_values_or_no_metric_columns() -> None:
    with pytest.raises(ValueError, match="header"):
        hdr.parse(b"a,b,c\n1,2,3\n")
    with pytest.raises(ValueError, match="metric"):
        hdr.parse(b"iso3,country,hdi_2000\nJPN,Japan,0.9\n")
    with pytest.raises(ValueError, match="numeric"):
        hdr.parse(b"iso3,country,gii_2000\nJPN,Japan,n/a\n")


def test_rank_and_other_prefixed_columns_are_ignored() -> None:
    # gii_rank_2023 / hdi_rank_2023 / hdicode / region exist upstream and are not metric cells
    parsed = hdr.parse(b"iso3,country,gii_rank_2023,gii_2023,hdi_2023\nJPN,Japan,23,0.059,0.9\n")
    assert [(r["metric"], r["year"], r["value"]) for r in parsed.rows] == [("gii", 2023, 0.059)]
    assert parsed.blank_cells == 0


def test_blank_cells_are_dropped_not_imputed() -> None:
    parsed = hdr.parse(b"iso3,country,gii_2000,gii_2001,mmr_2000\nJPN,Japan,0.1,,5\n")
    assert [(r["metric"], r["year"], r["value"]) for r in parsed.rows] == [
        ("gii", 2000, 0.1),
        ("mmr", 2000, 5.0),
    ]
    assert parsed.blank_cells == 1


def test_build_mart_sorts_and_rejects_duplicate_keys() -> None:
    rows = hdr.parse(CSV).rows
    mart = hdr.build_mart(list(reversed(rows)))
    assert mart == rows
    with pytest.raises(ValueError, match="duplicate"):
        hdr.build_mart(rows + [dict(rows[0])])
