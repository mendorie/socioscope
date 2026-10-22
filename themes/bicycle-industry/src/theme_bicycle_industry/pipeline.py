"""fetch -> stage -> mart for bicycle-industry. All I/O goes through ports.

No data source is wired yet (design/themes/bicycle-industry.md lists the candidates). Each
source will get its own pure-transform module (e.g. ``meti.py``, ``customs.py``) plus a
``# ---- <source>`` block here, as in the other themes.
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult

THEME = "bicycle-industry"
PANEL_TABLE = "marts/bicycle_industry_panel"

# Columns of the (still empty) mart. Long format: one metric per row so sources with
# different granularity (product type, price band, country) can share one table.
PANEL_COLUMNS: tuple[str, ...] = (
    "iso3",
    "year",
    "product",  # e.g. bicycle_total / e_assist / sports / city / parts
    "metric",  # e.g. units / value_jpy / price_index
    "value",
    "source",
)


def fetch(ctx: Context) -> StageResult:
    return StageResult(stage=Stage.FETCH, notes=(f"{THEME}: no sources registered yet",))


def stage(ctx: Context) -> StageResult:
    return StageResult(stage=Stage.STAGE, notes=(f"{THEME}: no sources registered yet",))


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


def mart(ctx: Context) -> StageResult:
    ctx.tables.write_table(PANEL_TABLE, build_panel([]))
    return StageResult(stage=Stage.MART, written=(PANEL_TABLE,))
