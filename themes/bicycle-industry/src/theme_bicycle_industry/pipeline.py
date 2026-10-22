"""fetch -> stage -> mart for bicycle-industry. All I/O goes through ports.

Each data source gets its own pure-transform module (``meti.py`` …) plus a ``# ---- <source>``
block here. Sources are independent: a missing raw is reported in ``skipped`` and the others
still run (design/themes/bicycle-industry.md lists the adoption order).
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult
from socioscope_core.ports.fetcher import FetchError
from theme_bicycle_industry import census, comtrade, cpi, meti, prices, shakai, shimano, tw_mops

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
    written, skipped = _fetch_comtrade_origin(ctx, written, skipped)
    written, skipped = _fetch_prices(ctx, written, skipped)
    written, skipped = _fetch_shimano(ctx, written, skipped)
    written, skipped = _fetch_cpi(ctx, written, skipped)
    written, skipped = _fetch_census(ctx, written, skipped)
    written, skipped = _fetch_shakai(ctx, written, skipped)
    written, skipped = _fetch_taiwan(ctx, written, skipped)
    written, skipped = _fetch_mops(ctx, written, skipped)
    return StageResult(stage=Stage.FETCH, written=tuple(written), skipped=tuple(skipped))


def stage(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _stage_meti(ctx, written, skipped)
    written, skipped = _stage_comtrade(ctx, written, skipped)
    written, skipped = _stage_comtrade_origin(ctx, written, skipped)
    written, skipped = _stage_prices(ctx, written, skipped)
    written, skipped = _stage_shimano(ctx, written, skipped)
    written, skipped = _stage_cpi(ctx, written, skipped)
    written, skipped = _stage_census(ctx, written, skipped)
    written, skipped = _stage_shakai(ctx, written, skipped)
    written, skipped = _stage_taiwan(ctx, written, skipped)
    written, skipped = _stage_mops(ctx, written, skipped)
    return StageResult(stage=Stage.STAGE, written=tuple(written), skipped=tuple(skipped))


def mart(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _mart_meti(ctx, written, skipped)
    written, skipped = _mart_comtrade(ctx, written, skipped)
    written, skipped = _mart_comtrade_origin(ctx, written, skipped)
    written, skipped = _mart_prices(ctx, written, skipped)
    written, skipped = _mart_shimano(ctx, written, skipped)
    written, skipped = _mart_cpi(ctx, written, skipped)
    written, skipped = _mart_census(ctx, written, skipped)
    written, skipped = _mart_shakai(ctx, written, skipped)
    written, skipped = _mart_taiwan(ctx, written, skipped)
    written, skipped = _mart_mops(ctx, written, skipped)
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


# ---- 総務省 CPI 2025 年基準 品目別 長期時系列 CSV（e-Stat、appId 不要）: 自転車 A/B・乗用車 -----
# Two CSVs (annual, monthly). An HTML error page is not CP932 → rejected before raw.

CPI_TABLE = "staged/estat/cpi_items"
CPI_MART = "marts/jp_cpi_vehicles"


def _fetch_cpi(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(cpi.SOURCE):
        return written, skipped
    for key in cpi.FILES:
        url = cpi.url(key)
        name = cpi.raw_name(key)
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if payload.lstrip().startswith(b"<"):
            skipped.append(f"{name}: HTML payload (wrong statInfId or fileKind?)")
            continue
        rec = ctx.raw.put(
            theme=THEME, source=cpi.SOURCE, name=name, url=url, license=cpi.LICENSE, payload=payload
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_cpi(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(cpi.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    staged_any = False
    for key in cpi.FILES:
        name = cpi.raw_name(key)
        payload = ctx.raw.get(theme=THEME, source=cpi.SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            parsed = cpi.parse(payload, key)
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
            continue
        rows.extend(parsed.rows)
        skipped.extend(f"{name}: {s}" for s in parsed.skipped)
        staged_any = True
    if staged_any:
        ctx.tables.write_table(CPI_TABLE, rows)
        written.append(CPI_TABLE)
    return written, skipped


def _mart_cpi(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(CPI_TABLE)
    except FileNotFoundError:
        skipped.append(f"{CPI_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(CPI_MART, cpi.build_mart(staged))
    written.append(CPI_MART)
    return written, skipped


# ---- 経済センサス（令和 3 年）小売業 産業編 第 1 表 xlsx（e-Stat、appId 不要）: 自転車小売業 -----
# One xlsx; the national rows of five retail industries, 1994–2021.

CENSUS_TABLE = "staged/estat/census_retail"
CENSUS_MART = "marts/jp_retail_census"


def _fetch_census(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(census.SOURCE):
        return written, skipped
    try:
        payload = ctx.fetcher.fetch(census.URL)
    except FetchError as e:
        skipped.append(f"{census.RAW_NAME}: {e}")
        return written, skipped
    if not payload.startswith(b"PK"):
        skipped.append(f"{census.RAW_NAME}: non-xlsx payload (wrong statInfId or fileKind?)")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME,
        source=census.SOURCE,
        name=census.RAW_NAME,
        url=census.URL,
        license=census.LICENSE,
        payload=payload,
    )
    written.append(rec.relative_path)
    return written, skipped


def _stage_census(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(census.SOURCE):
        return written, skipped
    payload = ctx.raw.get(theme=THEME, source=census.SOURCE, name=census.RAW_NAME)
    if payload is None:
        skipped.append(f"{census.RAW_NAME}: raw missing (run fetch)")
        return written, skipped
    try:
        parsed = census.parse(payload)
    except ValueError as e:
        skipped.append(f"{census.RAW_NAME}: layout not recognised ({e})")
        return written, skipped
    ctx.tables.write_table(CENSUS_TABLE, parsed.rows)
    written.append(CENSUS_TABLE)
    skipped.extend(f"{census.RAW_NAME}: {s}" for s in parsed.skipped)
    return written, skipped


def _mart_census(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(CENSUS_TABLE)
    except FileNotFoundError:
        skipped.append(f"{CENSUS_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(CENSUS_MART, census.build_mart(staged))
    written.append(CENSUS_MART)
    return written, skipped


# ---- UN Comtrade 原産国別（H8）: 輸入 5 か国 × 相手国 中国・台湾 × 2015–2024 -------------------
# Same preview endpoint, one JSON per year, imports only. The mart adds WLD (world, from the
# world-partner staged table) and OTH (= world − CHN − TWN) rows.

COMTRADE_ORIGIN_SOURCE = "un_comtrade_origin"
COMTRADE_ORIGIN_TABLE = "staged/comtrade/bicycle_trade_origin"
COMTRADE_ORIGIN_MART = "marts/bicycle_trade_by_origin"


def _fetch_comtrade_origin(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(COMTRADE_ORIGIN_SOURCE):
        return written, skipped
    for year in comtrade.ORIGIN_YEARS:
        url = comtrade.origin_url(year)
        name = comtrade.origin_raw_name(year)
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
            source=COMTRADE_ORIGIN_SOURCE,
            name=name,
            url=url,
            license=comtrade.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_comtrade_origin(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(COMTRADE_ORIGIN_SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    staged_any = False
    for year in comtrade.ORIGIN_YEARS:
        name = comtrade.origin_raw_name(year)
        payload = ctx.raw.get(theme=THEME, source=COMTRADE_ORIGIN_SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            parsed = comtrade.parse(payload, year=year, partners=True)
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
            continue
        rows.extend(parsed.rows)
        skipped.extend(f"{name}: {s}" for s in parsed.skipped)
        staged_any = True
    if staged_any:
        ctx.tables.write_table(COMTRADE_ORIGIN_TABLE, rows)
        written.append(COMTRADE_ORIGIN_TABLE)
    return written, skipped


def _mart_comtrade_origin(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    try:
        origin = ctx.tables.read_table(COMTRADE_ORIGIN_TABLE)
    except FileNotFoundError:
        skipped.append(f"{COMTRADE_ORIGIN_TABLE}: staged table missing (run stage)")
        return written, skipped
    try:
        world = ctx.tables.read_table(COMTRADE_TABLE)
    except FileNotFoundError:
        skipped.append(f"{COMTRADE_TABLE}: staged table missing (run stage); OTH/WLD rows omitted")
        world = []
    ctx.tables.write_table(COMTRADE_ORIGIN_MART, comtrade.build_origin_mart(origin, world))
    written.append(COMTRADE_ORIGIN_MART)
    return written, skipped


# ---- 社会生活基本調査 時系列統計表（e-Stat、appId 不要）: スポーツ種類別 行動者率 1986–2021 ----

SHAKAI_TABLE = "staged/estat/shakai_sports_rates"
SHAKAI_MART = "marts/jp_sports_participation"


def _fetch_shakai(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(shakai.SOURCE):
        return written, skipped
    try:
        payload = ctx.fetcher.fetch(shakai.URL)
    except FetchError as e:
        skipped.append(f"{shakai.RAW_NAME}: {e}")
        return written, skipped
    if not payload.startswith(b"PK"):
        skipped.append(f"{shakai.RAW_NAME}: non-xlsx payload (wrong statInfId or fileKind?)")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME,
        source=shakai.SOURCE,
        name=shakai.RAW_NAME,
        url=shakai.URL,
        license=shakai.LICENSE,
        payload=payload,
    )
    written.append(rec.relative_path)
    return written, skipped


def _stage_shakai(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(shakai.SOURCE):
        return written, skipped
    payload = ctx.raw.get(theme=THEME, source=shakai.SOURCE, name=shakai.RAW_NAME)
    if payload is None:
        skipped.append(f"{shakai.RAW_NAME}: raw missing (run fetch)")
        return written, skipped
    try:
        parsed = shakai.parse(payload)
    except ValueError as e:
        skipped.append(f"{shakai.RAW_NAME}: layout not recognised ({e})")
        return written, skipped
    ctx.tables.write_table(SHAKAI_TABLE, parsed.rows)
    written.append(SHAKAI_TABLE)
    skipped.extend(f"{shakai.RAW_NAME}: {s}" for s in parsed.skipped)
    return written, skipped


def _mart_shakai(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(SHAKAI_TABLE)
    except FileNotFoundError:
        skipped.append(f"{SHAKAI_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(SHAKAI_MART, shakai.build_mart(staged))
    written.append(SHAKAI_MART)
    return written, skipped


# ---- UN Comtrade 台湾輸出（H9）: reporter 490 × 仕向地 × 2015–2024 ---------------------------

COMTRADE_TAIWAN_SOURCE = "un_comtrade_taiwan"
COMTRADE_TAIWAN_TABLE = "staged/comtrade/taiwan_exports"
COMTRADE_TAIWAN_MART = "marts/taiwan_bicycle_exports"


def _fetch_taiwan(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(COMTRADE_TAIWAN_SOURCE):
        return written, skipped
    for year in comtrade.TAIWAN_YEARS:
        url = comtrade.taiwan_url(year)
        name = comtrade.taiwan_raw_name(year)
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
            source=COMTRADE_TAIWAN_SOURCE,
            name=name,
            url=url,
            license=comtrade.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_taiwan(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(COMTRADE_TAIWAN_SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    staged_any = False
    for year in comtrade.TAIWAN_YEARS:
        name = comtrade.taiwan_raw_name(year)
        payload = ctx.raw.get(theme=THEME, source=COMTRADE_TAIWAN_SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            parsed = comtrade.parse_taiwan(payload, year=year)
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
            continue
        rows.extend(parsed.rows)
        skipped.extend(f"{name}: {s}" for s in parsed.skipped)
        staged_any = True
    if staged_any:
        ctx.tables.write_table(COMTRADE_TAIWAN_TABLE, rows)
        written.append(COMTRADE_TAIWAN_TABLE)
    return written, skipped


def _mart_taiwan(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(COMTRADE_TAIWAN_TABLE)
    except FileNotFoundError:
        skipped.append(f"{COMTRADE_TAIWAN_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(COMTRADE_TAIWAN_MART, comtrade.build_taiwan_mart(staged))
    written.append(COMTRADE_TAIWAN_MART)
    return written, skipped


# ---- 台湾 MOPS 月次売上（H10）: Giant・Merida・KMC・Ideal × 2014–2026、JSON POST ------------------  # noqa: E501
# One POST per company-month (tw_mops.requests()). A month before coverage returns code 200
# without data; it is stored (the API's answer is the evidence) and staged as no row.

MOPS_TABLE = "staged/tw_mops/monthly_revenue"
MOPS_MART = "marts/tw_bicycle_monthly_revenue"


def _fetch_mops(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(tw_mops.SOURCE):
        return written, skipped
    for cid, year, month in tw_mops.requests():
        name = tw_mops.raw_name(cid, year, month)
        try:
            payload = ctx.fetcher.post_json(tw_mops.URL, tw_mops.body(cid, year, month))
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.lstrip().startswith(b"{"):
            skipped.append(f"{name}: non-JSON payload")
            continue
        rec = ctx.raw.put(
            theme=THEME,
            source=tw_mops.SOURCE,
            name=name,
            url=f"{tw_mops.URL}#companyId={cid}&year={tw_mops.roc_year(year)}&month={month}",
            license=tw_mops.LICENSE,
            payload=payload,
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_mops(
    ctx: Context, written: list[str], skipped: list[str]
) -> tuple[list[str], list[str]]:
    if not ctx.wants(tw_mops.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    staged_any = False
    empty = 0
    for cid, year, month in tw_mops.requests():
        name = tw_mops.raw_name(cid, year, month)
        payload = ctx.raw.get(theme=THEME, source=tw_mops.SOURCE, name=name)
        if payload is None:
            continue
        try:
            parsed = tw_mops.parse(payload, cid, year, month)
        except ValueError as e:
            skipped.append(f"{name}: layout not recognised ({e})")
            continue
        rows.extend(parsed.rows)
        empty += len(parsed.skipped)
        staged_any = True
    if staged_any:
        ctx.tables.write_table(MOPS_TABLE, rows)
        written.append(MOPS_TABLE)
        if empty:
            skipped.append(
                f"mops: {empty} company-months without data (before coverage / not yet published)"
            )
    else:
        skipped.append("mops: raw missing (run fetch)")
    return written, skipped


def _mart_mops(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    try:
        staged = ctx.tables.read_table(MOPS_TABLE)
    except FileNotFoundError:
        skipped.append(f"{MOPS_TABLE}: staged table missing (run stage)")
        return written, skipped
    ctx.tables.write_table(MOPS_MART, tw_mops.build_mart(staged))
    written.append(MOPS_MART)
    return written, skipped
