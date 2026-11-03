"""fetch -> stage -> mart for public-debt. All I/O goes through ports.

Each data source gets its own pure-transform module (``jst.py``, ``imf.py`` …) plus a
``# ---- <source>`` block here. Sources are independent: a missing raw is reported in
``skipped`` and the others still run (design/themes/public-debt.md lists the adoption order).
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult
from socioscope_core.ports.fetcher import FetchError
from theme_public_debt import imf, jst

THEME = "public-debt"
PANEL_TABLE = "marts/public_debt_panel"

# Cross-source panel, long format: one metric per row so sources with different debt
# definitions (central vs general government, gross vs net, loans vs total credit) can share
# one table without being silently compared to each other.
PANEL_COLUMNS: tuple[str, ...] = (
    "iso3",
    "year",
    "unit",  # e.g. general_gov_gross / central_gov_gross / general_gov_net / households / nfc
    "metric",  # e.g. debt_gdp / ltrate / ngdp_growth / cpi_inflation / primary_balance_gdp
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
    written, skipped = _fetch_jst(ctx, written, skipped)
    written, skipped = _fetch_imf(ctx, written, skipped)
    return StageResult(stage=Stage.FETCH, written=tuple(written), skipped=tuple(skipped))


def stage(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _stage_jst(ctx, written, skipped)
    written, skipped = _stage_imf(ctx, written, skipped)
    return StageResult(stage=Stage.STAGE, written=tuple(written), skipped=tuple(skipped))


def mart(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _mart_jst(ctx, written, skipped)
    written, skipped = _mart_imf(ctx, written, skipped)
    # The cross-source panel is written only once it has rows: a zero-row Parquet has no
    # columns and DuckDB cannot build a view on it.
    panel_rows: list[dict[str, object]] = []
    for table in (jst.MART_TABLE, imf.MART_TABLE):
        if table in ctx.tables.list_tables():
            panel_rows.extend(ctx.tables.read_table(table))
    if panel_rows:
        ctx.tables.write_table(PANEL_TABLE, build_panel(panel_rows))
        written.append(PANEL_TABLE)
    return StageResult(stage=Stage.MART, written=tuple(written), skipped=tuple(skipped))


# ---- JST Macrohistory Database R6: one xlsx --------------------------------------------------
# The magic bytes are checked (xlsx = zip) so an HTML block page never reaches raw.


def _fetch_jst(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(jst.SOURCE):
        return written, skipped
    try:
        payload = ctx.fetcher.fetch(jst.URL)
    except FetchError as e:
        skipped.append(f"{jst.RAW_NAME}: {e}")
        return written, skipped
    if not payload.startswith(jst.MAGIC):
        skipped.append(f"{jst.RAW_NAME}: non-xlsx payload")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME,
        source=jst.SOURCE,
        name=jst.RAW_NAME,
        url=jst.URL,
        license=jst.LICENSE,
        payload=payload,
    )
    written.append(rec.relative_path)
    return written, skipped


def _stage_jst(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(jst.SOURCE):
        return written, skipped
    payload = ctx.raw.get(theme=THEME, source=jst.SOURCE, name=jst.RAW_NAME)
    if payload is None:
        skipped.append(f"{jst.RAW_NAME}: raw missing (run fetch)")
        return written, skipped
    try:
        rows = jst.parse(jst.workbook_rows(payload))
    except ValueError as e:
        skipped.append(f"{jst.RAW_NAME}: {e}")
        return written, skipped
    ctx.tables.write_table(jst.STAGED_TABLE, rows)
    written.append(jst.STAGED_TABLE)
    return written, skipped


def _mart_jst(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(jst.SOURCE):
        return written, skipped
    if jst.STAGED_TABLE not in ctx.tables.list_tables():
        skipped.append(f"{jst.MART_TABLE}: staged missing ({jst.STAGED_TABLE}; run stage)")
        return written, skipped
    rows = jst.build_mart(ctx.tables.read_table(jst.STAGED_TABLE))
    ctx.tables.write_table(jst.MART_TABLE, rows)
    written.append(jst.MART_TABLE)
    return written, skipped


# ---- IMF DataMapper API: WEO / Fiscal Monitor / Global Debt Database, one JSON per indicator -
# A non-JSON payload (block page) never reaches raw. Indicators are independent: one failing
# request is reported in ``skipped`` and the others are still stored / staged.


def _fetch_imf(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(imf.SOURCE):
        return written, skipped
    for code in imf.INDICATORS:
        url, name = imf.url(code), imf.raw_name(code)
        try:
            payload = ctx.fetcher.fetch(url)
        except FetchError as e:
            skipped.append(f"{name}: {e}")
            continue
        if not payload.lstrip().startswith(imf.MAGIC):
            skipped.append(f"{name}: non-JSON payload")
            continue
        rec = ctx.raw.put(
            theme=THEME, source=imf.SOURCE, name=name, url=url, license=imf.LICENSE, payload=payload
        )
        written.append(rec.relative_path)
    return written, skipped


def _stage_imf(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(imf.SOURCE):
        return written, skipped
    rows: list[dict[str, object]] = []
    for code in imf.INDICATORS:
        name = imf.raw_name(code)
        payload = ctx.raw.get(theme=THEME, source=imf.SOURCE, name=name)
        if payload is None:
            skipped.append(f"{name}: raw missing (run fetch)")
            continue
        try:
            rows.extend(imf.parse(payload, code))
        except ValueError as e:
            skipped.append(f"{name}: {e}")
    if rows:
        ctx.tables.write_table(imf.STAGED_TABLE, rows)
        written.append(imf.STAGED_TABLE)
    return written, skipped


def _mart_imf(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    if not ctx.wants(imf.SOURCE):
        return written, skipped
    if imf.STAGED_TABLE not in ctx.tables.list_tables():
        skipped.append(f"{imf.MART_TABLE}: staged missing ({imf.STAGED_TABLE}; run stage)")
        return written, skipped
    rows = imf.build_mart(ctx.tables.read_table(imf.STAGED_TABLE))
    ctx.tables.write_table(imf.MART_TABLE, rows)
    written.append(imf.MART_TABLE)
    return written, skipped
