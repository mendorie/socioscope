"""fetch -> stage -> mart for bicycle-industry. All I/O goes through ports.

Each data source gets its own pure-transform module (``meti.py`` …) plus a ``# ---- <source>``
block here. Sources are independent: a missing raw is reported in ``skipped`` and the others
still run (design/themes/bicycle-industry.md lists the adoption order).
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult
from socioscope_core.ports.fetcher import FetchError
from theme_bicycle_industry import comtrade, meti, prices, shimano

THEME = "bicycle-industry"
PANEL_TABLE = "marts/bicycle_industry_panel"

# Columns of the cross-source panel (not written yet). Long format: one metric per row so sources
# with different granularity (product type, price band, country) can share one table.
PANEL_COLUMNS: tuple[str, ...] = (
    "iso3",
    "year",
    "product",  # e.g. bicycle_total / e_assist / sports / city / parts
    "metric",  # e.g. units / value_jpy / price_index
    "value",
    "source",
)


def build_panel(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Deterministic mart: keep only the panel columns, sort by key, reject duplicate keys."""
    key = ("iso3", "year", "product", "metric", "source")
    out = [{c: r.get(c) for c in PANEL_COLUMNS} for r in rows]
    out.sort(key=lambda r: tuple(str(r[k]) for k in key))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in key)
        if k in seen:
            msg = f"duplicate panel key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out


def fetch(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _fetch_meti(ctx, written, skipped)
    written, skipped = _fetch_comtrade(ctx, written, skipped)
    written, skipped = _fetch_prices(ctx, written, skipped)
    written, skipped = _fetch_shimano(ctx, written, skipped)
    return StageResult(stage=Stage.FETCH, written=tuple(written), skipped=tuple(skipped))


def stage(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _stage_meti(ctx, written, skipped)
    written, skipped = _stage_comtrade(ctx, written, skipped)
    written, skipped = _stage_prices(ctx, written, skipped)
    written, skipped = _stage_shimano(ctx, written, skipped)
    return StageResult(stage=Stage.STAGE, written=tuple(written), skipped=tuple(skipped))


def mart(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _mart_meti(ctx, written, skipped)
    written, skipped = _mart_comtrade(ctx, written, skipped)
    written, skipped = _mart_prices(ctx, written, skipped)
    written, skipped = _mart_shimano(ctx, written, skipped)
    # The cross-source panel is written only once it has rows: a zero-row Parquet has no
    # columns and DuckDB cannot build a view on it (CI smoke `socioscope db build`).
    return StageResult(stage=Stage.MART, written=tuple(written), skipped=tuple(skipped))


# ---- METI 生産動態統計（機械統計）年報 xlsx: 自転車 2430 ＋ 自動車・二輪 2400 -------------
# One xlsx per report year (meti.YEARS). www.meti.go.jp answers 403 to non-browser User-Agents, so
# the CLI fetcher sends a browser UA to that host (Settings.browser_ua_hosts). An HTML payload
# (block page) is rejected before it reaches raw.

METI_TABLE = "staged/meti/seidou_annual"
METI_MART = "marts/meti_production"


def _fetch_meti(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(meti.SOURCE):
        return written, skipped
    for year in meti.YEARS:
        url = meti.annual_url(year)
        name = meti.raw_name(year)
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.startswith(b"PK"):
            skipped.append(f"{name}: non-xlsx payload (blocked or moved?)")
            continue
        rec = ctx.raw.put(
            theme=THEME,
            source=meti.SOURCE,
            name=name,
            url=url,
            license=meti.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_meti(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(meti.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    staged_any = False
    for year in meti.YEARS:
        name = meti.raw_name(year)
        payload = ctx.raw.get(theme=THEME, source=meti.SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            parsed = meti.parse(payload, report_year=year)
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
            continue
        rows.extend(parsed.rows)
        skipped.extend(f"{name}: {s}" for s in parsed.skipped)
        staged_any = True
    if staged_any:
        ctx.tables.write_table(METI_TABLE, rows)
        written.append(METI_TABLE)
    return written, skipped


def _mart_meti(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(METI_TABLE)
    except FileNotFoundError:
        skipped.append(f"{METI_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(METI_MART, meti.build_mart(staged))
    written.append(METI_MART)
    return written, skipped


# ---- UN Comtrade preview API: HS 8712 / 871160 / 8714 × 9 reporters × 2010–2024 ---------------
# One JSON per year (the preview endpoint takes one period per call). 429 under parallel calls,
# so the loop is sequential; a failed year is reported in skipped and can be re-fetched later.

COMTRADE_TABLE = "staged/comtrade/bicycle_trade"
COMTRADE_MART = "marts/bicycle_trade"


def _fetch_comtrade(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(comtrade.SOURCE):
        return written, skipped
    for year in comtrade.YEARS:
        url = comtrade.url(year)
        name = comtrade.raw_name(year)
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.lstrip().startswith(b"{"):
            skipped.append(f"{name}: non-JSON payload")
            continue
        rec = ctx.raw.put(
            theme=THEME,
            source=comtrade.SOURCE,
            name=name,
            url=url,
            license=comtrade.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_comtrade(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(comtrade.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    staged_any = False
    for year in comtrade.YEARS:
        name = comtrade.raw_name(year)
        payload = ctx.raw.get(theme=THEME, source=comtrade.SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            parsed = comtrade.parse(payload, year=year)
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
            continue
        rows.extend(parsed.rows)
        skipped.extend(f"{name}: {s}" for s in parsed.skipped)
        staged_any = True
    if staged_any:
        ctx.tables.write_table(COMTRADE_TABLE, rows)
        written.append(COMTRADE_TABLE)
    return written, skipped


def _mart_comtrade(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(COMTRADE_TABLE)
    except FileNotFoundError:
        skipped.append(f"{COMTRADE_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(COMTRADE_MART, comtrade.build_mart(staged))
    written.append(COMTRADE_MART)
    return written, skipped


# ---- Price indices: Eurostat HICP CP0711/0712/0713 (one JSON-stat) + US BLS CPI (v2 GET) -----
# Two raw sources, one staged table per source, one long mart. Each source is filtered by its
# own name (`eurostat_hicp`, `bls_cpi`).

HICP_TABLE = "staged/eurostat/hicp_cp071x"
BLS_TABLE = "staged/bls/cpi_vehicles"
PRICES_MART = "marts/price_indices"


def _fetch_prices(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if ctx.wants(prices.HICP_SOURCE):
        url = prices.hicp_url()
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{prices.HICP_RAW_NAME}: {e}")
        else:
            rec = ctx.raw.put(
                theme=THEME,
                source=prices.HICP_SOURCE,
                name=prices.HICP_RAW_NAME,
                url=url,
                license=prices.HICP_LICENSE,
                payload=payload,
            )
            written.append(rec.relative_path)
    if ctx.wants(prices.BLS_SOURCE):
        for series_id in prices.BLS_SERIES:
            for start, end in prices.BLS_RANGES:
                url = prices.bls_url(series_id, start, end)
                name = prices.bls_raw_name(series_id, start, end)
                try:
                    payload = ctx.fetcher.fetch(url)
                except FetchError as e:
                    skipped.append(f"{name}: {e}")
                    continue
                rec = ctx.raw.put(
                    theme=THEME,
                    source=prices.BLS_SOURCE,
                    name=name,
                    url=url,
                    license=prices.BLS_LICENSE,
                    payload=payload,
                )
                written.append(rec.relative_path)
    return written, skipped


def _stage_prices(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if ctx.wants(prices.HICP_SOURCE):
        payload = ctx.raw.get(theme=THEME, source=prices.HICP_SOURCE, name=prices.HICP_RAW_NAME)
        if payload is None:
            skipped.append(f"{prices.HICP_RAW_NAME}: raw missing (run fetch)")
        else:
            try:
                parsed = prices.parse_hicp(payload)
            except ValueError as e:
                skipped.append(f"{prices.HICP_RAW_NAME}: layout not recognised ({e})")
            else:
                ctx.tables.write_table(HICP_TABLE, parsed.rows)
                written.append(HICP_TABLE)
                skipped.extend(f"{prices.HICP_RAW_NAME}: {s}" for s in parsed.skipped)
    if ctx.wants(prices.BLS_SOURCE):
        rows: list[dict[str, object]] = []
        staged_any = False
        for series_id in prices.BLS_SERIES:
            for start, end in prices.BLS_RANGES:
                name = prices.bls_raw_name(series_id, start, end)
                payload = ctx.raw.get(theme=THEME, source=prices.BLS_SOURCE, name=name)
                if payload is None:
                    skipped.append(f"{name}: raw missing (run fetch)")
                    continue
                try:
                    parsed = prices.parse_bls(payload, series_id)
                except ValueError as e:
                    skipped.append(f"{name}: layout not recognised ({e})")
                    continue
                rows.extend(parsed.rows)
                skipped.extend(f"{name}: {s}" for s in parsed.skipped)
                staged_any = True
        if staged_any:
            ctx.tables.write_table(BLS_TABLE, rows)
            written.append(BLS_TABLE)
    return written, skipped


def _mart_prices(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    rows: list[dict[str, object]] = []
    found = False
    for table in (HICP_TABLE, BLS_TABLE):
        try:
            rows.extend(ctx.tables.read_table(table))
        except FileNotFoundError:
            skipped.append(f"{table}: staged table missing (run stage)")
            continue
        found = True
    if found:
        ctx.tables.write_table(PRICES_MART, prices.build_mart(rows))
        written.append(PRICES_MART)
    return written, skipped


# ---- Shimano 有価証券報告書 PDF（EDINET、キー不要）: セグメント・地域別売上 FY2013–2025 ------
# One PDF per fiscal year (shimano.DOCS). Each filing carries the prior year too, so the mart
# prefers the filing of the year itself and records a restatement when the next year differs.

SHIMANO_TABLE = "staged/edinet/shimano_segments"
SHIMANO_MART = "marts/shimano_segments"


def _fetch_shimano(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(shimano.SOURCE):
        return written, skipped
    for fy in sorted(shimano.DOCS):
        url = shimano.url(fy)
        name = shimano.raw_name(fy)
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.startswith(b"%PDF"):
            skipped.append(f"{name}: non-PDF payload")
            continue
        rec = ctx.raw.put(
            theme=THEME,
            source=shimano.SOURCE,
            name=name,
            url=url,
            license=shimano.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_shimano(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(shimano.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    staged_any = False
    for fy in sorted(shimano.DOCS):
        name = shimano.raw_name(fy)
        payload = ctx.raw.get(theme=THEME, source=shimano.SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            parsed = shimano.parse(payload, fy)
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
            continue
        rows.extend(parsed.rows)
        skipped.extend(f"{name}: {s}" for s in parsed.skipped)
        staged_any = True
    if staged_any:
        ctx.tables.write_table(SHIMANO_TABLE, rows)
        written.append(SHIMANO_TABLE)
    return written, skipped


def _mart_shimano(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(SHIMANO_TABLE)
    except FileNotFoundError:
        skipped.append(f"{SHIMANO_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(SHIMANO_MART, shimano.build_mart(staged))
    written.append(SHIMANO_MART)
    return written, skipped
