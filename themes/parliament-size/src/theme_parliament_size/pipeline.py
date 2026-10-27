"""fetch -> stage -> mart for parliament-size. All I/O goes through ports.

Each data source gets its own pure-transform module (``ipu.py`` …) plus a ``# ---- <source>``
block here. Sources are independent: a missing raw is reported in ``skipped`` and the others
still run (design/themes/parliament-size.md lists the adoption order).
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult
from socioscope_core.ports.fetcher import FetchError
from theme_parliament_size import ipu

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
    return StageResult(stage=Stage.FETCH, written=tuple(written), skipped=tuple(skipped))


def stage(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _stage_ipu(ctx, written, skipped)
    return StageResult(stage=Stage.STAGE, written=tuple(written), skipped=tuple(skipped))


def mart(ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    written, skipped = _mart_ipu(ctx, written, skipped)
    # The cross-source panel is written only once it has rows: a zero-row Parquet has no
    # columns and DuckDB cannot build a view on it.
    return StageResult(stage=Stage.MART, written=tuple(written), skipped=tuple(skipped))


# ---- IPU Parline API: chambers (281) and countries (193), 100 per page ---------------------
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
