"""fetch -> stage -> mart for parliament-size. All I/O goes through ports.

Each data source gets its own pure-transform module (``ipu.py`` …) plus a ``# ---- <source>``
block here. Sources are independent: a missing raw is reported in ``skipped`` and the others
still run (design/themes/parliament-size.md lists the adoption order).
"""

from collections.abc import Callable
from dataclasses import dataclass

from socioscope_core.core.pipeline import Context, Stage, StageResult
from socioscope_core.ports.fetcher import FetchError
from theme_parliament_size import (
    camera,
    clb,
    estat,
    fran,
    ilostat,
    ipss,
    ipu,
    kokkai,
    mof,
    oecd,
    parlgov,
    soumu,
    ukbills,
    worldbank,
)

THEME = "parliament-size"
PANEL_TABLE = "marts/parliament_size_panel"

# Cross-source panel, long format: one metric per row so sources with different granularity
# (chamber, election, prefecture, PR block) can share one table.
PANEL_COLUMNS: tuple[str, ...] = (
    "iso3",
    "year",
    "unit",  # e.g. lower_house / upper_house / both / pr_block:<name> / pref:<code>
    "metric",  # e.g. seats / population / seats_per_million / staff_per_member
    "value",
    "source",
)
PANEL_KEY: tuple[str, ...] = ("iso3", "year", "unit", "metric", "source")


def build_panel(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Deterministic mart: keep only the panel columns, sort by key, reject duplicate keys."""
    out = [{c: r.get(c) for c in PANEL_COLUMNS} for r in rows]
    out.sort(key=lambda r: tuple(str(r[k]) for k in PANEL_KEY))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in PANEL_KEY)
        if k in seen:
            msg = f"duplicate panel key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out


def fetch(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _fetch_ipu(ctx, written, skipped)
    written, skipped = _fetch_soumu(ctx, written, skipped)
    written, skipped = _fetch_estat(ctx, written, skipped)
    written, skipped = _fetch_single(ctx, written, skipped, MOF)
    written, skipped = _fetch_single(ctx, written, skipped, CLB)
    written, skipped = _fetch_single(ctx, written, skipped, WDI)
    written, skipped = _fetch_single(ctx, written, skipped, WDI_POP)
    written, skipped = _fetch_single(ctx, written, skipped, PARLGOV)
    written, skipped = _fetch_single(ctx, written, skipped, ILO_ECO)
    written, skipped = _fetch_single(ctx, written, skipped, ILO_INS)
    written, skipped = _fetch_single(ctx, written, skipped, IPSS)
    written, skipped = _fetch_single(ctx, written, skipped, CAMERA_LAWS)
    written, skipped = _fetch_single(ctx, written, skipped, CAMERA_SITTINGS)
    written, skipped = _fetch_single(ctx, written, skipped, ILO_EAR)
    written, skipped = _fetch_single(ctx, written, skipped, WDI_GDP_PCAP)
    written, skipped = _fetch_single(ctx, written, skipped, OECD_GOV)
    written, skipped = _fetch_kokkai(ctx, written, skipped)
    written, skipped = _fetch_ukbills(ctx, written, skipped)
    written, skipped = _fetch_fran(ctx, written, skipped)
    return StageResult(stage=Stage.FETCH, written=tuple(written), skipped=tuple(skipped))


def stage(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _stage_ipu(ctx, written, skipped)
    written, skipped = _stage_soumu(ctx, written, skipped)
    written, skipped = _stage_estat(ctx, written, skipped)
    written, skipped = _stage_single(ctx, written, skipped, MOF)
    written, skipped = _stage_single(ctx, written, skipped, CLB)
    written, skipped = _stage_single(ctx, written, skipped, WDI)
    written, skipped = _stage_single(ctx, written, skipped, WDI_POP)
    written, skipped = _stage_single(ctx, written, skipped, PARLGOV)
    written, skipped = _stage_single(ctx, written, skipped, ILO_ECO)
    written, skipped = _stage_single(ctx, written, skipped, ILO_INS)
    written, skipped = _stage_single(ctx, written, skipped, IPSS)
    written, skipped = _stage_single(ctx, written, skipped, CAMERA_LAWS)
    written, skipped = _stage_single(ctx, written, skipped, CAMERA_SITTINGS)
    written, skipped = _stage_single(ctx, written, skipped, ILO_EAR)
    written, skipped = _stage_single(ctx, written, skipped, WDI_GDP_PCAP)
    written, skipped = _stage_single(ctx, written, skipped, OECD_GOV)
    written, skipped = _stage_kokkai(ctx, written, skipped)
    written, skipped = _stage_ukbills(ctx, written, skipped)
    written, skipped = _stage_fran(ctx, written, skipped)
    return StageResult(stage=Stage.STAGE, written=tuple(written), skipped=tuple(skipped))


def mart(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _mart_ipu(ctx, written, skipped)
    written, skipped = _mart_soumu(ctx, written, skipped)
    written, skipped = _mart_estat(ctx, written, skipped)
    written, skipped = _mart_single(ctx, written, skipped, MOF)
    written, skipped = _mart_single(ctx, written, skipped, CLB)
    written, skipped = _mart_single(ctx, written, skipped, WDI)
    written, skipped = _mart_single(ctx, written, skipped, WDI_POP)
    written, skipped = _mart_single(ctx, written, skipped, PARLGOV)
    written, skipped = _mart_single(ctx, written, skipped, ILO_ECO)
    written, skipped = _mart_single(ctx, written, skipped, ILO_INS)
    written, skipped = _mart_single(ctx, written, skipped, IPSS)
    written, skipped = _mart_single(ctx, written, skipped, CAMERA_LAWS)
    written, skipped = _mart_single(ctx, written, skipped, CAMERA_SITTINGS)
    written, skipped = _mart_single(ctx, written, skipped, ILO_EAR)
    written, skipped = _mart_single(ctx, written, skipped, WDI_GDP_PCAP)
    written, skipped = _mart_single(ctx, written, skipped, OECD_GOV)
    written, skipped = _mart_kokkai(ctx, written, skipped)
    written, skipped = _mart_ukbills(ctx, written, skipped)
    written, skipped = _mart_fran(ctx, written, skipped)
    # The cross-source panel is written only once it has rows: a zero-row Parquet has no
    # columns and DuckDB cannot build a view on it.
    return StageResult(stage=Stage.MART, written=tuple(written), skipped=tuple(skipped))


# ---- IPU Parline API: chambers (281) and countries (193), 100 per page ---
# Pages are followed through ``links.next`` so a change in the number of entities needs no code
# change; ``ipu.MAX_PAGES`` bounds the walk. A non-JSON payload (block page) never reaches raw.

IPU_CHAMBERS_TABLE = "staged/ipu/chamber_attributes"
IPU_COUNTRIES_TABLE = "staged/ipu/country_attributes"
IPU_MART = "marts/ipu_parliaments"
_IPU_TABLE: dict[str, str] = {"chambers": IPU_CHAMBERS_TABLE, "countries": IPU_COUNTRIES_TABLE}


def _fetch_ipu(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(ipu.SOURCE):
        return written, skipped
    for kind in ipu.KINDS:
        for page in range(1, ipu.MAX_PAGES + 1):
            url = ipu.url(kind, page)
            name = ipu.raw_name(kind, page)
            try:
                payload = ctx.fetcher.fetch(url)
            except FetchError as e:
                skipped.append(f"{name}: {e}")
                break
            if not payload.lstrip().startswith(b"{"):
                skipped.append(f"{name}: non-JSON payload")
                break
            rec = ctx.raw.put(
                theme=THEME,
                source=ipu.SOURCE,
                name=name,
                url=url,
                license=ipu.LICENSE,
                payload=payload,
            )
            written.append(rec.relative_path)
            if not ipu.has_next(payload):
                break
    return written, skipped


def _stage_ipu(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(ipu.SOURCE):
        return written, skipped
    for kind in ipu.KINDS:
        rows: list[dict[str, object]] = []
        for page in range(1, ipu.MAX_PAGES + 1):
            name = ipu.raw_name(kind, page)
            payload = ctx.raw.get(theme=THEME, source=ipu.SOURCE, name=name)
            if payload is None:
                if page == 1:
                    skipped.append(f"{name}: raw missing (run fetch)")
                break
            try:
                rows.extend(ipu.parse(payload, kind, page))
            except ValueError as e:
                skipped.append(f"{name}: {e}")
                rows = []
                break
        if rows:
            ctx.tables.write_table(_IPU_TABLE[kind], rows)
            written.append(_IPU_TABLE[kind])
    return written, skipped


def _mart_ipu(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(ipu.SOURCE):
        return written, skipped
    tables = set(ctx.tables.list_tables())
    missing = [t for t in (IPU_CHAMBERS_TABLE, IPU_COUNTRIES_TABLE) if t not in tables]
    if missing:
        skipped.append(f"{IPU_MART}: staged missing ({', '.join(missing)}; run stage)")
        return written, skipped
    try:
        rows = ipu.build_mart(
            ctx.tables.read_table(IPU_CHAMBERS_TABLE), ctx.tables.read_table(IPU_COUNTRIES_TABLE)
        )
    except ValueError as e:
        skipped.append(f"{IPU_MART}: {e}")
        return written, skipped
    ctx.tables.write_table(IPU_MART, rows)
    written.append(IPU_MART)
    return written, skipped


# ---- 総務省 衆議院議員総選挙 結果調 Excel（第 50・51 回）----------------
# One workbook per (election, table). The magic bytes are checked (xls: OLE2, xlsx: zip) so an
# HTML block page never reaches raw.


def _fetch_soumu(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(soumu.SOURCE):
        return written, skipped
    for election in sorted(soumu.ELECTIONS):
        for key in soumu.KEYS:
            url, name = soumu.url(election, key), soumu.raw_name(election, key)
            try:
                payload = ctx.fetcher.fetch(url)
            except FetchError as e:
                skipped.append(f"{name}: {e}")
                continue
            if not payload.startswith(soumu.magic(election, key)):
                skipped.append(f"{name}: non-{soumu.ext_of(election, key)} payload")
                continue
            rec = ctx.raw.put(
                theme=THEME,
                source=soumu.SOURCE,
                name=name,
                url=url,
                license=soumu.LICENSE,
                payload=payload,
            )
            written.append(rec.relative_path)
    return written, skipped


SOUMU_ELECTORATE_TABLE = "staged/soumu/electorate"
SOUMU_PR_VOTES_TABLE = "staged/soumu/pr_votes"
SOUMU_PR_SEATS_TABLE = "staged/soumu/pr_seats"
SOUMU_ELECTORATE_MART = "marts/jp_hr_electorate"
SOUMU_PR_MART = "marts/jp_hr_pr_results"
SOUMU_WINNERS_TABLE = "staged/soumu/winners_by_party"
SOUMU_WINNERS_MART = "marts/jp_hr_seats_by_party"


def _stage_soumu(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(soumu.SOURCE):
        return written, skipped
    electorate: list[dict[str, object]] = []
    votes: list[dict[str, object]] = []
    seats: list[dict[str, object]] = []
    winners: list[dict[str, object]] = []
    for election in sorted(soumu.ELECTIONS):
        meta = {"election": election, "election_date": soumu.ELECTIONS[election].date}
        for key in soumu.KEYS:
            name = soumu.raw_name(election, key)
            payload = ctx.raw.get(theme=THEME, source=soumu.SOURCE, name=name)
            if payload is None:
                skipped.append(f"{name}: raw missing (run fetch)")
                continue
            try:
                rows = soumu.rows_of(payload, election, key=key)
                if key == "electorate_smd":
                    electorate += [
                        {**meta, "tier": "smd", "block": None, **r}
                        for r in soumu.parse_electorate_smd(rows)
                    ]
                elif key == "electorate_pr":
                    electorate += [
                        {**meta, "tier": "pr", **r} for r in soumu.parse_electorate_pr(rows)
                    ]
                elif key == "pr_votes_by_block":
                    votes += [{**meta, **r} for r in soumu.parse_pr_votes(rows)]
                elif key == "pr_seats_table":
                    seats += [{**meta, **r} for r in soumu.parse_pr_seats(rows)]
                else:
                    sheets = [soumu.rows_of(payload, election, i, key=key) for i in range(2)]
                    totals = soumu.ELECTIONS[election].seats
                    winners += [{**meta, **r} for r in soumu.parse_winners(sheets, totals)]
            except ValueError as e:
                skipped.append(f"{name}: layout not recognised ({e})")
    for table, rows_ in (
        (SOUMU_ELECTORATE_TABLE, electorate),
        (SOUMU_PR_VOTES_TABLE, votes),
        (SOUMU_PR_SEATS_TABLE, seats),
        (SOUMU_WINNERS_TABLE, winners),
    ):
        if rows_:
            ctx.tables.write_table(table, rows_)
            written.append(table)
    return written, skipped


def _mart_soumu(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(soumu.SOURCE):
        return written, skipped
    tables = set(ctx.tables.list_tables())
    if SOUMU_ELECTORATE_TABLE in tables:
        try:
            rows = soumu.build_electorate_mart(ctx.tables.read_table(SOUMU_ELECTORATE_TABLE))
        except ValueError as e:
            skipped.append(f"{SOUMU_ELECTORATE_MART}: {e}")
        else:
            ctx.tables.write_table(SOUMU_ELECTORATE_MART, rows)
            written.append(SOUMU_ELECTORATE_MART)
    else:
        skipped.append(f"{SOUMU_ELECTORATE_MART}: staged missing (run stage)")
    if SOUMU_PR_VOTES_TABLE in tables and SOUMU_PR_SEATS_TABLE in tables:
        try:
            rows = soumu.build_pr_mart(
                ctx.tables.read_table(SOUMU_PR_VOTES_TABLE),
                ctx.tables.read_table(SOUMU_PR_SEATS_TABLE),
            )
        except ValueError as e:
            skipped.append(f"{SOUMU_PR_MART}: {e}")
        else:
            ctx.tables.write_table(SOUMU_PR_MART, rows)
            written.append(SOUMU_PR_MART)
    else:
        skipped.append(f"{SOUMU_PR_MART}: staged missing (run stage)")
    if SOUMU_WINNERS_TABLE in tables:
        rows = soumu.build_winners_mart(ctx.tables.read_table(SOUMU_WINNERS_TABLE))
        ctx.tables.write_table(SOUMU_WINNERS_MART, rows)
        written.append(SOUMU_WINNERS_MART)
    else:
        skipped.append(f"{SOUMU_WINNERS_MART}: staged missing (run stage)")
    return written, skipped


# ---- e-Stat 令和 2 年国勢調査 表 2-1（都道府県別 日本人人口、アダムズ方式の基礎）---

CENSUS_TABLE = "staged/estat/census2020_prefecture"
CENSUS_MART = "marts/jp_census2020_prefecture"
LONGPOP_TABLE = "staged/estat/population_longterm"
LONGPOP_MART = "marts/jp_population_longterm"


def _fetch_estat(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(estat.SOURCE):
        return written, skipped
    try:
        payload = ctx.fetcher.fetch(estat.URL)
    except FetchError as e:
        skipped.append(f"{estat.RAW_NAME}: {e}")
        return written, skipped
    if not payload.startswith(estat.MAGIC):
        skipped.append(f"{estat.RAW_NAME}: non-xlsx payload")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME,
        source=estat.SOURCE,
        name=estat.RAW_NAME,
        url=estat.URL,
        license=estat.LICENSE,
        payload=payload,
    )
    written.append(rec.relative_path)
    try:
        payload = ctx.fetcher.fetch(estat.LONGPOP_URL)
    except FetchError as e:
        skipped.append(f"{estat.LONGPOP_RAW_NAME}: {e}")
        return written, skipped
    if not payload.startswith(estat.LONGPOP_MAGIC):
        skipped.append(f"{estat.LONGPOP_RAW_NAME}: non-Excel payload")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME,
        source=estat.SOURCE,
        name=estat.LONGPOP_RAW_NAME,
        url=estat.LONGPOP_URL,
        license=estat.LICENSE,
        payload=payload,
    )
    written.append(rec.relative_path)
    return written, skipped


def _stage_estat(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(estat.SOURCE):
        return written, skipped
    payload = ctx.raw.get(theme=THEME, source=estat.SOURCE, name=estat.RAW_NAME)
    if payload is None:
        skipped.append(f"{estat.RAW_NAME}: raw missing (run fetch)")
        return written, skipped
    try:
        rows = estat.parse(estat.workbook_rows(payload))
    except ValueError as e:
        skipped.append(f"{estat.RAW_NAME}: layout not recognised ({e})")
        return written, skipped
    ctx.tables.write_table(CENSUS_TABLE, [{**r, "source": estat.SOURCE} for r in rows])
    written.append(CENSUS_TABLE)
    payload = ctx.raw.get(theme=THEME, source=estat.SOURCE, name=estat.LONGPOP_RAW_NAME)
    if payload is None:
        skipped.append(f"{estat.LONGPOP_RAW_NAME}: raw missing (run fetch)")
        return written, skipped
    try:
        rows = estat.parse_longpop(estat.workbook_rows(payload))
    except ValueError as e:
        skipped.append(f"{estat.LONGPOP_RAW_NAME}: layout not recognised ({e})")
        return written, skipped
    ctx.tables.write_table(LONGPOP_TABLE, [{**r, "source": estat.SOURCE} for r in rows])
    written.append(LONGPOP_TABLE)
    return written, skipped


def _mart_estat(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(estat.SOURCE):
        return written, skipped
    if CENSUS_TABLE not in ctx.tables.list_tables():
        skipped.append(f"{CENSUS_MART}: staged missing (run stage)")
        return written, skipped
    try:
        rows = estat.build_mart(ctx.tables.read_table(CENSUS_TABLE))
    except ValueError as e:
        skipped.append(f"{CENSUS_MART}: {e}")
        return written, skipped
    ctx.tables.write_table(CENSUS_MART, rows)
    written.append(CENSUS_MART)
    if LONGPOP_TABLE in ctx.tables.list_tables():
        ctx.tables.write_table(
            LONGPOP_MART, estat.build_longpop_mart(ctx.tables.read_table(LONGPOP_TABLE))
        )
        written.append(LONGPOP_MART)
    else:
        skipped.append(f"{LONGPOP_MART}: staged missing (run stage)")
    return written, skipped


# ---- 1 文書 1 ソースの共通結線（財務省 予算書 PDF、内閣法制局 HTML）--------


@dataclass(frozen=True)
class SingleDoc:
    source: str
    license: str
    url: str
    raw_name: str
    magic: bytes
    parse: Callable[[bytes], list[dict[str, object]]]
    build_mart: Callable[[list[dict[str, object]]], list[dict[str, object]]]
    table: str
    mart: str


MOF = SingleDoc(
    source=mof.SOURCE,
    license=mof.LICENSE,
    url=mof.URL,
    raw_name=mof.RAW_NAME,
    magic=mof.MAGIC,
    parse=lambda payload: mof.parse(mof.pdf_pages(payload)),
    build_mart=mof.build_mart,
    table="staged/mof/budget_by_organ",
    mart="marts/jp_budget_by_organ",
)
CLB = SingleDoc(
    source=clb.SOURCE,
    license=clb.LICENSE,
    url=clb.URL,
    raw_name=clb.RAW_NAME,
    magic=b"<",
    parse=clb.parse,
    build_mart=clb.build_mart,
    table="staged/clb/bill_counts",
    mart="marts/jp_bill_counts",
)
WDI = SingleDoc(
    source=worldbank.SOURCE,
    license=worldbank.LICENSE,
    url=worldbank.URL,
    raw_name=worldbank.RAW_NAME,
    magic=worldbank.MAGIC,
    parse=worldbank.parse,
    build_mart=worldbank.build_mart,
    table="staged/worldbank/gdp_lcu",
    mart="marts/wdi_gdp_lcu",
)
WDI_POP = SingleDoc(
    source=worldbank.SOURCE,
    license=worldbank.LICENSE,
    url=worldbank.POP_URL,
    raw_name=worldbank.POP_RAW_NAME,
    magic=worldbank.MAGIC,
    parse=worldbank.parse_population,
    build_mart=worldbank.build_population_mart,
    table="staged/worldbank/population",
    mart="marts/wdi_population",
)
PARLGOV = SingleDoc(
    source=parlgov.SOURCE,
    license=parlgov.LICENSE,
    url=parlgov.URL,
    raw_name=parlgov.RAW_NAME,
    magic=parlgov.MAGIC,
    parse=parlgov.parse,
    build_mart=parlgov.build_mart,
    table="staged/parlgov/elections",
    mart="marts/parlgov_elections",
)
ILO_ECO = SingleDoc(
    source=ilostat.SOURCE,
    license=ilostat.LICENSE,
    url=ilostat.ECO_URL,
    raw_name=ilostat.ECO_RAW_NAME,
    magic=ilostat.MAGIC,
    parse=ilostat.parse,
    build_mart=ilostat.build_mart,
    table="staged/ilostat/emp_eco",
    mart="marts/ilo_emp_public_admin",
)
ILO_INS = SingleDoc(
    source=ilostat.SOURCE,
    license=ilostat.LICENSE,
    url=ilostat.INS_URL,
    raw_name=ilostat.INS_RAW_NAME,
    magic=ilostat.MAGIC,
    parse=ilostat.parse,
    build_mart=ilostat.build_mart,
    table="staged/ilostat/emp_ins",
    mart="marts/ilo_emp_public_sector",
)
IPSS = SingleDoc(
    source=ipss.SOURCE,
    license=ipss.LICENSE,
    url=ipss.URL,
    raw_name=ipss.RAW_NAME,
    magic=ipss.MAGIC,
    parse=lambda payload: ipss.parse(ipss.workbook_rows(payload)),
    build_mart=ipss.build_mart,
    table="staged/ipss/prefecture_projection",
    mart="marts/jp_prefecture_projection",
)
CAMERA_LAWS = SingleDoc(
    source=camera.SOURCE,
    license=camera.LICENSE,
    url=camera.LAWS_URL,
    raw_name=camera.LAWS_RAW_NAME,
    magic=camera.MAGIC,
    parse=camera.parse_laws,
    build_mart=camera.build_mart,
    table="staged/camera/laws_by_year",
    mart="marts/it_laws_by_year",
)
CAMERA_SITTINGS = SingleDoc(
    source=camera.SOURCE,
    license=camera.LICENSE,
    url=camera.SITTINGS_URL,
    raw_name=camera.SITTINGS_RAW_NAME,
    magic=camera.MAGIC,
    parse=camera.parse_sittings,
    build_mart=camera.build_mart,
    table="staged/camera/sittings_by_year",
    mart="marts/it_sittings_by_year",
)
ILO_EAR = SingleDoc(
    source=ilostat.SOURCE,
    license=ilostat.LICENSE,
    url=ilostat.EAR_URL,
    raw_name=ilostat.EAR_RAW_NAME,
    magic=ilostat.MAGIC,
    parse=ilostat.parse_earnings,
    build_mart=ilostat.build_mart,
    table="staged/ilostat/earnings",
    mart="marts/ilo_earnings_monthly",
)
WDI_GDP_PCAP = SingleDoc(
    source=worldbank.SOURCE,
    license=worldbank.LICENSE,
    url=worldbank.GDP_PCAP_URL,
    raw_name=worldbank.GDP_PCAP_RAW_NAME,
    magic=worldbank.MAGIC,
    parse=worldbank.parse_gdp_pcap,
    build_mart=worldbank.build_gdp_pcap_mart,
    table="staged/worldbank/gdp_pcap_lcu",
    mart="marts/wdi_gdp_pcap_lcu",
)
OECD_GOV = SingleDoc(
    source=oecd.SOURCE,
    license=oecd.LICENSE,
    url=oecd.URL,
    raw_name=oecd.RAW_NAME,
    magic=oecd.MAGIC,
    parse=oecd.parse,
    build_mart=oecd.build_mart,
    table="staged/oecd/gov_finance",
    mart="marts/oecd_gov_finance",
)


def _fetch_single(
    ctx: Context, written: list[str], skipped: list[str], doc: SingleDoc
) -> tuple[list[str], list[str]]:
    if not ctx.wants(doc.source):
        return written, skipped
    try:
        payload = ctx.fetcher.fetch(doc.url)
    except FetchError as e:
        skipped.append(f"{doc.raw_name}: {e}")
        return written, skipped
    if not payload.lstrip().startswith(doc.magic):
        skipped.append(f"{doc.raw_name}: unexpected payload (magic mismatch)")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME,
        source=doc.source,
        name=doc.raw_name,
        url=doc.url,
        license=doc.license,
        payload=payload,
    )
    written.append(rec.relative_path)
    return written, skipped


def _stage_single(
    ctx: Context, written: list[str], skipped: list[str], doc: SingleDoc
) -> tuple[list[str], list[str]]:
    if not ctx.wants(doc.source):
        return written, skipped
    payload = ctx.raw.get(theme=THEME, source=doc.source, name=doc.raw_name)
    if payload is None:
        skipped.append(f"{doc.raw_name}: raw missing (run fetch)")
        return written, skipped
    try:
        rows = doc.parse(payload)
    except ValueError as e:
        skipped.append(f"{doc.raw_name}: layout not recognised ({e})")
        return written, skipped
    ctx.tables.write_table(doc.table, [{**r, "source": doc.source} for r in rows])
    written.append(doc.table)
    return written, skipped


def _mart_single(
    ctx: Context, written: list[str], skipped: list[str], doc: SingleDoc
) -> tuple[list[str], list[str]]:
    if not ctx.wants(doc.source):
        return written, skipped
    if doc.table not in ctx.tables.list_tables():
        skipped.append(f"{doc.mart}: staged missing (run stage)")
        return written, skipped
    try:
        rows = doc.build_mart(ctx.tables.read_table(doc.table))
    except ValueError as e:
        skipped.append(f"{doc.mart}: {e}")
        return written, skipped
    ctx.tables.write_table(doc.mart, rows)
    written.append(doc.mart)
    return written, skipped


# ---- UK Parliament Bills API（Take=100 でページを辿る。IsAct はクライアント側で絞る）------

UKBILLS_TABLE = "staged/ukbills/bills"
UKBILLS_MART = "marts/uk_acts"


def _fetch_ukbills(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(ukbills.SOURCE):
        return written, skipped
    for page in range(1, ukbills.MAX_PAGES + 1):
        url, name = ukbills.url(page), ukbills.raw_name(page)
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            break
        if not payload.lstrip().startswith(b"{"):
            skipped.append(f"{name}: non-JSON payload")
            break
        rec = ctx.raw.put(
            theme=THEME,
            source=ukbills.SOURCE,
            name=name,
            url=url,
            license=ukbills.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
        if not ukbills.has_next(payload, page):
            break
    return written, skipped


def _stage_ukbills(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(ukbills.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    for page in range(1, ukbills.MAX_PAGES + 1):
        name = ukbills.raw_name(page)
        payload = ctx.raw.get(theme=THEME, source=ukbills.SOURCE, name=name)
        if payload is None:
            if page == 1:
                skipped.append(f"{name}: raw missing (run fetch)")
            break
        try:
            rows.extend({**r, "source": ukbills.SOURCE} for r in ukbills.parse(payload, page))
        except ValueError as e:
            skipped.append(f"{name}: {e}")
            rows = []
            break
    if rows:
        ctx.tables.write_table(UKBILLS_TABLE, rows)
        written.append(UKBILLS_TABLE)
    return written, skipped


def _mart_ukbills(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(ukbills.SOURCE):
        return written, skipped
    if UKBILLS_TABLE not in ctx.tables.list_tables():
        skipped.append(f"{UKBILLS_MART}: staged missing (run stage)")
        return written, skipped
    try:
        rows = ukbills.build_mart(ctx.tables.read_table(UKBILLS_TABLE))
    except ValueError as e:
        skipped.append(f"{UKBILLS_MART}: {e}")
        return written, skipped
    ctx.tables.write_table(UKBILLS_MART, rows)
    written.append(UKBILLS_MART)
    return written, skipped


# ---- フランス国民議会 Dossiers législatifs（立法期ごとの zip）------------------------------

FRAN_TABLE = "staged/fran/dossiers"
FRAN_MART = "marts/fr_laws"


def _fetch_fran(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(fran.SOURCE):
        return written, skipped
    for leg in fran.LEGISLATURES:
        url, name = fran.url(leg), fran.raw_name(leg)
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.startswith(fran.MAGIC):
            skipped.append(f"{name}: non-zip payload")
            continue
        rec = ctx.raw.put(
            theme=THEME,
            source=fran.SOURCE,
            name=name,
            url=url,
            license=fran.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_fran(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(fran.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    for leg in fran.LEGISLATURES:
        name = fran.raw_name(leg)
        payload = ctx.raw.get(theme=THEME, source=fran.SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            rows.extend({**r, "source": fran.SOURCE} for r in fran.parse(payload, leg))
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
    if rows:
        ctx.tables.write_table(FRAN_TABLE, rows)
        written.append(FRAN_TABLE)
    return written, skipped


def _mart_fran(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(fran.SOURCE):
        return written, skipped
    if FRAN_TABLE not in ctx.tables.list_tables():
        skipped.append(f"{FRAN_MART}: staged missing (run stage)")
        return written, skipped
    try:
        rows = fran.build_mart(ctx.tables.read_table(FRAN_TABLE))
    except ValueError as e:
        skipped.append(f"{FRAN_MART}: {e}")
        return written, skipped
    ctx.tables.write_table(FRAN_MART, rows)
    written.append(FRAN_MART)
    return written, skipped


# ---- 国会会議録検索システム API（衆議院の会議一覧、年 × 100 件ページ）----------------

KOKKAI_TABLE = "staged/kokkai/meetings"
KOKKAI_MART = "marts/jp_hr_sitting_days"


def _fetch_kokkai(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(kokkai.SOURCE):
        return written, skipped
    for year in kokkai.YEARS:
        for page in range(1, kokkai.MAX_PAGES + 1):
            url, name = kokkai.url(year, page), kokkai.raw_name(year, page)
            try:
                payload = ctx.fetcher.fetch(url)
            except FetchError as e:
                skipped.append(f"{name}: {e}")
                break
            if not payload.lstrip().startswith(kokkai.MAGIC):
                skipped.append(f"{name}: non-JSON payload")
                break
            rec = ctx.raw.put(
                theme=THEME,
                source=kokkai.SOURCE,
                name=name,
                url=url,
                license=kokkai.LICENSE,
                payload=payload,
            )
            written.append(rec.relative_path)
            if not kokkai.has_next(payload):
                break
    return written, skipped


def _stage_kokkai(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(kokkai.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    for year in kokkai.YEARS:
        for page in range(1, kokkai.MAX_PAGES + 1):
            name = kokkai.raw_name(year, page)
            payload = ctx.raw.get(theme=THEME, source=kokkai.SOURCE, name=name)
            if payload is None:
                if page == 1:
                    skipped.append(f"{name}: raw missing (run fetch)")
                break
            try:
                rows.extend(
                    {**r, "source": kokkai.SOURCE} for r in kokkai.parse(payload, year, page)
                )
            except ValueError as e:
                skipped.append(f"{name}: {e}")
                break
    if rows:
        ctx.tables.write_table(KOKKAI_TABLE, rows)
        written.append(KOKKAI_TABLE)
    return written, skipped


def _mart_kokkai(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(kokkai.SOURCE):
        return written, skipped
    if KOKKAI_TABLE not in ctx.tables.list_tables():
        skipped.append(f"{KOKKAI_MART}: staged missing (run stage)")
        return written, skipped
    try:
        rows = kokkai.build_mart(ctx.tables.read_table(KOKKAI_TABLE))
    except ValueError as e:
        skipped.append(f"{KOKKAI_MART}: {e}")
        return written, skipped
    ctx.tables.write_table(KOKKAI_MART, rows)
    written.append(KOKKAI_MART)
    return written, skipped
