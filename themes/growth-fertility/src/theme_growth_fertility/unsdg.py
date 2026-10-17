"""UN SDG Global Database (UNSD SDG API, no key): series JSON -> long rows (no I/O).

H8d. Two series, each one request (URLs verified 2026-10-17, fixed in :data:`SERIES`):

* ``SL_DOM_TSPD`` 5.4.1 proportion of time spent on unpaid domestic chores and care work
  (% of 24 h) by sex x age x location
* ``IC_GEN_MGTL`` 5.5.2 proportion of women in managerial positions (%)

``geoAreaCode`` is a UN M49 numeric code. Countries and territories are mapped to ISO3 with the
fixed :data:`M49_TO_ISO3` (built from the codes present in the two responses); regional and
income aggregates (World, Sub-Saharan Africa, LDCs, ...) are dropped and reported so stage can
list them. A ``value`` that is not a number is dropped and reported (never imputed). Pagination
(``totalElements`` > rows, ``totalPages`` != 1), a row of another series, an unexpected unit, a
non-integer year or a ``Sex``/``Location`` code outside the closed sets is a ``ValueError``.

Output columns: ``iso3, country, year, series, sex(F/M/T), age, location, value, nature, source``.
Age groups differ by country (15+, 10+, ...); all are kept and the choice is made in analysis.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

__all__ = [
    "BASE",
    "LICENSE",
    "M49_TO_ISO3",
    "SERIES",
    "SOURCE",
    "Parsed",
    "Series",
    "build_mart",
    "mart_key",
    "parse",
]

BASE = "https://unstats.un.org/sdgapi/v1/sdg/Series/Data"
SOURCE = "unsdg"
LICENSE = (
    "UN Terms of Use (https://www.un.org/en/about-us/terms-of-use) and UNdata Terms of Use "
    "(https://data.un.org/Host.aspx?Content=UNdataUse: reproduction and redistribution with "
    "attribution). Terms differ, so raw is not committed; staged/marts cite: United Nations "
    "Statistics Division, SDG Global Database (Series SL_DOM_TSPD, IC_GEN_MGTL), "
    "https://unstats.un.org/sdgs/dataportal (accessed 2026-10-18)"
)
UNIT = "PERCENT"
SEX_CODES: dict[str, str] = {"FEMALE": "F", "MALE": "M", "BOTHSEX": "T"}
LOCATIONS: tuple[str, ...] = ("ALLAREA", "RURAL", "URBAN")
MART_KEY = ("iso3", "year", "series", "sex", "age", "location")


@dataclass(frozen=True)
class Series:
    key: str
    code: str
    page_size: int

    @property
    def raw_name(self) -> str:
        return f"{self.key}.json"

    @property
    def url(self) -> str:
        return f"{BASE}?seriesCode={self.code}&pageSize={self.page_size}"


SERIES: tuple[Series, ...] = (
    Series(key="sl_dom_tspd", code="SL_DOM_TSPD", page_size=5000),
    Series(key="ic_gen_mgtl", code="IC_GEN_MGTL", page_size=10000),
)

# UN M49 numeric code -> ISO 3166-1 alpha-3, for every country/territory that appears in the
# two series (2026-10-17). Aggregates (1 World, 2 Africa, 9 Oceania, 62, 199 LDCs, 202, 419,
# 432 LLDCs, 513, 514, 515, 543, 722 SIDS, 747, 753 and the sub-regions) are deliberately absent.
M49_TO_ISO3: dict[str, str] = {
    "4": "AFG", "8": "ALB", "12": "DZA", "24": "AGO", "28": "ATG", "31": "AZE", "32": "ARG",
    "36": "AUS", "40": "AUT", "44": "BHS", "48": "BHR", "50": "BGD", "51": "ARM", "52": "BRB",
    "56": "BEL", "60": "BMU", "64": "BTN", "68": "BOL", "70": "BIH", "72": "BWA", "76": "BRA",
    "84": "BLZ", "90": "SLB", "96": "BRN", "100": "BGR", "104": "MMR", "108": "BDI", "112": "BLR",
    "116": "KHM", "120": "CMR", "124": "CAN", "132": "CPV", "136": "CYM", "144": "LKA",
    "152": "CHL", "156": "CHN", "170": "COL", "174": "COM", "178": "COG", "180": "COD",
    "184": "COK", "188": "CRI", "191": "HRV", "192": "CUB", "196": "CYP", "203": "CZE",
    "204": "BEN", "208": "DNK", "212": "DMA", "214": "DOM", "218": "ECU", "222": "SLV",
    "231": "ETH", "233": "EST", "242": "FJI", "246": "FIN", "250": "FRA", "262": "DJI",
    "268": "GEO", "270": "GMB", "275": "PSE", "276": "DEU", "288": "GHA", "296": "KIR",
    "300": "GRC", "308": "GRD", "320": "GTM", "324": "GIN", "328": "GUY", "332": "HTI",
    "340": "HND", "344": "HKG", "348": "HUN", "352": "ISL", "356": "IND", "360": "IDN",
    "364": "IRN", "368": "IRQ", "372": "IRL", "376": "ISR", "380": "ITA", "384": "CIV",
    "388": "JAM", "392": "JPN", "398": "KAZ", "400": "JOR", "404": "KEN", "410": "KOR",
    "414": "KWT", "417": "KGZ", "418": "LAO", "422": "LBN", "426": "LSO", "428": "LVA",
    "430": "LBR", "440": "LTU", "442": "LUX", "450": "MDG", "454": "MWI", "458": "MYS",
    "462": "MDV", "466": "MLI", "470": "MLT", "480": "MUS", "484": "MEX", "496": "MNG",
    "498": "MDA", "499": "MNE", "500": "MSR", "504": "MAR", "508": "MOZ", "512": "OMN",
    "516": "NAM", "520": "NRU", "524": "NPL", "528": "NLD", "531": "CUW", "533": "ABW",
    "548": "VUT", "554": "NZL", "558": "NIC", "562": "NER", "566": "NGA", "570": "NIU",
    "578": "NOR", "583": "FSM", "584": "MHL", "585": "PLW", "586": "PAK", "591": "PAN",
    "598": "PNG", "600": "PRY", "604": "PER", "608": "PHL", "616": "POL", "620": "PRT",
    "624": "GNB", "626": "TLS", "630": "PRI", "634": "QAT", "638": "REU", "642": "ROU",
    "643": "RUS", "646": "RWA", "660": "AIA", "662": "LCA", "670": "VCT", "674": "SMR",
    "678": "STP", "682": "SAU", "686": "SEN", "688": "SRB", "690": "SYC", "694": "SLE",
    "702": "SGP", "703": "SVK", "704": "VNM", "705": "SVN", "706": "SOM", "710": "ZAF",
    "716": "ZWE", "724": "ESP", "728": "SSD", "729": "SDN", "740": "SUR", "748": "SWZ",
    "752": "SWE", "756": "CHE", "760": "SYR", "762": "TJK", "764": "THA", "768": "TGO",
    "772": "TKL", "776": "TON", "780": "TTO", "784": "ARE", "788": "TUN", "792": "TUR",
    "798": "TUV", "800": "UGA", "804": "UKR", "807": "MKD", "818": "EGY", "826": "GBR",
    "832": "JEY", "833": "IMN", "834": "TZA", "840": "USA", "854": "BFA", "858": "URY",
    "862": "VEN", "876": "WLF", "882": "WSM", "887": "YEM", "894": "ZMB",
}  # fmt: skip


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore")
    totalElements: int  # noqa: N815  (UNSD field name)
    totalPages: int  # noqa: N815
    data: list[dict[str, object]]


class _Attributes(BaseModel):
    model_config = ConfigDict(extra="ignore")
    Nature: str
    Units: str


class _Dimensions(BaseModel):
    model_config = ConfigDict(extra="ignore")
    Sex: str
    Age: str
    Location: str = "ALLAREA"  # IC_GEN_MGTL has no location dimension


class _Point(BaseModel):
    model_config = ConfigDict(extra="ignore")
    series: str
    geoAreaCode: str  # noqa: N815
    geoAreaName: str  # noqa: N815
    timePeriodStart: float  # noqa: N815
    value: str | float | None
    attributes: _Attributes
    dimensions: _Dimensions


@dataclass(frozen=True)
class Parsed:
    rows: list[dict[str, object]]
    dropped_areas: tuple[str, ...]  # "code name" of aggregates not in M49_TO_ISO3, sorted
    skipped: tuple[str, ...]  # rows dropped for a non-numeric value, in payload order


def _page(payload: bytes) -> _Page:
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = "unexpected UNSD response shape: not JSON"
        raise ValueError(msg) from e
    if not isinstance(doc, dict) or "data" not in doc:
        msg = "unexpected UNSD response shape: expected an object with 'data'"
        raise ValueError(msg)
    page = _Page.model_validate(doc)
    if page.totalPages != 1 or page.totalElements != len(page.data):
        msg = (
            f"paginated/truncated UNSD response: totalPages={page.totalPages} "
            f"totalElements={page.totalElements} rows={len(page.data)}; raise pageSize"
        )
        raise ValueError(msg)
    return page


def _year(point: _Point) -> int:
    if point.timePeriodStart != int(point.timePeriodStart):
        msg = f"non-integer year {point.timePeriodStart} for {point.geoAreaName}"
        raise ValueError(msg)
    return int(point.timePeriodStart)


def parse(payload: bytes, series: Series) -> Parsed:
    """One series page -> long rows sorted by :data:`MART_KEY`, plus dropped areas / rows."""
    page = _page(payload)
    out: list[dict[str, object]] = []
    dropped: set[str] = set()
    skipped: list[str] = []
    for raw in page.data:
        p = _Point.model_validate(raw)
        if p.series != series.code:
            msg = f"UNSD series {p.series!r}, expected {series.code!r}"
            raise ValueError(msg)
        if p.attributes.Units != UNIT:
            msg = f"UNSD Units {p.attributes.Units!r}, expected {UNIT!r}"
            raise ValueError(msg)
        if p.dimensions.Sex not in SEX_CODES:
            msg = f"UNSD Sex {p.dimensions.Sex!r} not in {tuple(SEX_CODES)}"
            raise ValueError(msg)
        if p.dimensions.Location not in LOCATIONS:
            msg = f"UNSD Location {p.dimensions.Location!r} not in {LOCATIONS}"
            raise ValueError(msg)
        year = _year(p)
        iso3 = M49_TO_ISO3.get(p.geoAreaCode)
        if iso3 is None:
            dropped.add(f"{p.geoAreaCode} {p.geoAreaName}")
            continue
        try:
            value = float(p.value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            skipped.append(
                f"{p.geoAreaCode} {p.geoAreaName} {year} {p.dimensions.Age} "
                f"{p.dimensions.Sex}: non-numeric value {p.value!r}"
            )
            continue
        out.append(
            {
                "iso3": iso3,
                "country": p.geoAreaName,
                "year": year,
                "series": series.code,
                "sex": SEX_CODES[p.dimensions.Sex],
                "age": p.dimensions.Age,
                "location": p.dimensions.Location,
                "value": value,
                "nature": p.attributes.Nature,
                "source": SOURCE,
            }
        )
    out.sort(key=mart_key)
    return Parsed(rows=out, dropped_areas=tuple(sorted(dropped)), skipped=tuple(skipped))


def mart_key(row: Mapping[str, object]) -> tuple[str, int, str, str, str, str]:
    return (
        str(row["iso3"]),
        int(str(row["year"])),
        str(row["series"]),
        str(row["sex"]),
        str(row["age"]),
        str(row["location"]),
    )


def build_mart(staged: Mapping[str, Sequence[Mapping[str, object]]]) -> list[dict[str, object]]:
    """Concatenate the staged series tables, sort by :data:`MART_KEY`; duplicate keys fail."""
    rows = [dict(r) for key in sorted(staged) for r in staged[key]]
    rows.sort(key=mart_key)
    seen: set[tuple[object, ...]] = set()
    for r in rows:
        k = mart_key(r)
        if k in seen:
            msg = f"duplicate UNSD mart key {k}"
            raise ValueError(msg)
        seen.add(k)
    return rows
