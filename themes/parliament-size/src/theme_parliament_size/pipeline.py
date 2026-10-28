"""fetch -> stage -> mart for parliament-size. All I/O goes through ports.

Each data source gets its own pure-transform module (``ipu.py`` …) plus a ``# ---- <source>``
block here. Sources are independent: a missing raw is reported in ``skipped`` and the others
still run (design/themes/parliament-size.md lists the adoption order).
"""

from collections.abc import Callable
from dataclasses import dataclass

from socioscope_core.core.pipeline import Context, Stage, StageResult
from socioscope_core.ports.fetcher import FetchError
from theme_parliament_size import clb, estat, ipu, mof, soumu, worldbank

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
