"""fetch -> stage -> mart for bicycle-industry. All I/O goes through ports.

Each data source gets its own pure-transform module (``meti.py`` …) plus a ``# ---- <source>``
block here. Sources are independent: a missing raw is reported in ``skipped`` and the others
still run (design/themes/bicycle-industry.md lists the adoption order).
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult
from socioscope_core.ports.fetcher import FetchError
from theme_bicycle_industry import meti

THEME = "bicycle-industry"
PANEL_TABLE = "marts/bicycle_industry_panel"

# Columns of the (still empty) cross-source panel. Long format: one metric per row so sources
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
    return StageResult(stage=Stage.FETCH, written=tuple(written), skipped=tuple(skipped))


def stage(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _stage_meti(ctx, written, skipped)
    return StageResult(stage=Stage.STAGE, written=tuple(written), skipped=tuple(skipped))


def mart(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _mart_meti(ctx, written, skipped)
    ctx.tables.write_table(PANEL_TABLE, build_panel([]))
    written.append(PANEL_TABLE)
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
