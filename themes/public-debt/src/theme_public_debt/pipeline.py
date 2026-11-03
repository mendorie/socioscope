"""fetch -> stage -> mart for public-debt. All I/O goes through ports.

No data source is wired yet (design/themes/public-debt.md lists the adoption order: the
Jordà–Schularick–Taylor Macrohistory Database first). Each source gets its own pure-transform
module plus a ``# ---- <source>`` block here; sources stay independent so a missing raw is
reported in ``skipped`` and the others still run.
"""

from socioscope_core.core.pipeline import Context, Stage, StageResult

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


_NO_SOURCE = f"{THEME}: no data source adopted yet (see design/themes/public-debt.md)"


def fetch(ctx: Context) -> StageResult:
    return StageResult(stage=Stage.FETCH, notes=(_NO_SOURCE,))


def stage(ctx: Context) -> StageResult:
    return StageResult(stage=Stage.STAGE, notes=(_NO_SOURCE,))


def mart(ctx: Context) -> StageResult:
    # An empty Parquet has no columns and DuckDB cannot read it, so nothing is written until a
    # source produces rows.
    return StageResult(stage=Stage.MART, notes=(_NO_SOURCE,))
