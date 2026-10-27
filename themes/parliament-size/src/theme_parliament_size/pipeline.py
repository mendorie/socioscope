"""fetch -> stage -> mart for parliament-size. All I/O goes through ports.

No data source is wired yet (design/themes/parliament-size.md lists the adoption order:
IPU Parline + WDI population first). Each source gets its own pure-transform module plus a
``# ---- <source>`` block here; sources stay independent so a missing raw is reported in
``skipped`` and the others still run.
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult

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


_NO_SOURCE = f"{THEME}: no data source adopted yet (see design/themes/parliament-size.md)"


def fetch(ctx: Context) -> StageResult:
    return StageResult(stage=Stage.FETCH, notes=(_NO_SOURCE,))


def stage(ctx: Context) -> StageResult:
    return StageResult(stage=Stage.STAGE, notes=(_NO_SOURCE,))


def mart(ctx: Context) -> StageResult:
    # An empty Parquet has no columns and DuckDB cannot read it, so nothing is written until a
    # source produces rows.
    return StageResult(stage=Stage.MART, notes=(_NO_SOURCE,))
