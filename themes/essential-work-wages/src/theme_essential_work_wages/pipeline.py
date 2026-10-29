"""fetch -> stage -> mart for essential-work-wages. All I/O goes through ports.

Each data source is one module in this package that exposes ``SOURCE`` (raw-store source name)
and three functions ``fetch(ctx, written, skipped)``, ``stage(ctx, written, skipped)``,
``mart(ctx, written, skipped)`` (see ``CLAUDE.md`` "ソースモジュールの契約"). ``SOURCES`` lists
them in adoption order (design/themes/essential-work-wages.md). Sources are independent: a
missing raw is reported in ``skipped`` and the others still run.
"""

from collections.abc import Callable
from types import ModuleType

from socioscope_core.core.pipeline import Context, Stage, StageResult

THEME = "essential-work-wages"
PANEL_TABLE = "marts/essential_work_wages_panel"

# Occupation-level long panel shared by every source. One metric per row so sources with
# different granularity (occupation, occupation x industry, industry) can share one table.
PANEL_COLUMNS: tuple[str, ...] = (
    "iso3",
    "year",
    "occupation",  # source classification code (JSOC / SOC / SOC2020), see `classification`
    "classification",  # e.g. jp_bsws2020 / us_soc2018 / uk_soc2020 / isic_rev4 (industry rows)
    "metric",  # e.g. wage_median / wage_p10 / wage_p90 / employees / jobs_to_applicants
    "value",
    "source",
)

PANEL_KEY: tuple[str, ...] = ("iso3", "year", "occupation", "classification", "metric", "source")

# Source modules in adoption order. Registered by the integrator only (see CLAUDE.md).
SOURCES: tuple[ModuleType, ...] = ()

StepFn = Callable[[Context, list[str], list[str]], tuple[list[str], list[str]]]


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


def _run(stage: Stage, ctx: Context) -> StageResult:
    written: list[str] = []
    skipped: list[str] = []
    for mod in SOURCES:
        if not ctx.wants(mod.SOURCE):
            continue
        step: StepFn = getattr(mod, stage.value)
        written, skipped = step(ctx, written, skipped)
    notes = () if SOURCES else (f"{THEME}: no source wired yet",)
    return StageResult(stage=stage, written=tuple(written), skipped=tuple(skipped), notes=notes)


def fetch(ctx: Context) -> StageResult:
    return _run(Stage.FETCH, ctx)


def stage(ctx: Context) -> StageResult:
    return _run(Stage.STAGE, ctx)


def mart(ctx: Context) -> StageResult:
    result = _run(Stage.MART, ctx)
    ctx.tables.write_table(PANEL_TABLE, build_panel([]))
    return StageResult(
        stage=Stage.MART,
        written=(*result.written, PANEL_TABLE),
        skipped=result.skipped,
        notes=result.notes,
    )
