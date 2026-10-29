"""Dingel & Neiman (2020) teleworkability index per Census 2018 occupation code.

Source: https://github.com/jdingel/DingelNeiman-workathome (occ_onet_scores/output/
occupations_workathome.csv; columns onetsoccode,title,teleworkable; ~968 O*NET-SOC 2010
occupations, score 0/1). Repository LICENSE is GPL-3.0 (checked 2026-10-29); we redistribute
only derived averages with attribution: Dingel, J. I. & Neiman, B. (2020), "How many jobs can
be done at home?", Journal of Public Economics 189.

Mapping (pure, deterministic): O*NET 8-digit code -> 6-digit SOC (first 7 characters) by
arithmetic mean -> Census 2018 occupation by the mean of the SOC-6 means whose code starts
with the prefix of the Census row's SOC. The prefix drops ``X`` placeholders (``13-20XX`` ->
``13-20``, ``51-4XXX`` -> ``51-4``) or trailing zeros of a broad/minor group (``13-1020`` ->
``13-102``); detailed codes match exactly. D-N is on SOC 2010 while the Census list is SOC 2018
(e.g. programmers 15-1131 -> 15-1251), so each Census row also tries the 2010 SOC codes from
the Census crosswalk (``soc_2010_codes`` in ``staged/acs/occupation_codes``, written by
``acs.py``); without that step the match rate is 86.9 %, with it 96.1 %. The remaining misses
are the "All Other" residual codes (``xx-9099``) and Legislators, which O*NET does not score.
``soc_code == 'none'`` rows get no value. A match rate below ``MIN_MATCH_RATE`` raises
``ValueError`` (fail-closed).

Mart: ``marts/us_occupation_teleworkable`` with occupation_code, occupation, classification,
soc_code, teleworkable (0-1 share), n_onet (O*NET codes averaged), source. Depends on
``acs.stage`` having written the code table; otherwise ``mart`` reports it as skipped.
"""

import csv
import io
import re
from collections import defaultdict

from socioscope_core.core.pipeline import Context
from socioscope_core.ports.fetcher import FetchError
from theme_essential_work_wages.acs import CLASSIFICATION, CODES_TABLE
from theme_essential_work_wages.pipeline import THEME

SOURCE = "dingel_neiman"
SOURCE_TAG = "dingel_neiman_2020"
LICENSE = (
    "GPL-3.0 (github.com/jdingel/DingelNeiman-workathome LICENSE); derived averages only, "
    "cite Dingel & Neiman (2020) J. Public Econ."
)
URL = (
    "https://raw.githubusercontent.com/jdingel/DingelNeiman-workathome/master/"
    "occ_onet_scores/output/occupations_workathome.csv"
)
RAW_NAME = "occupations_workathome.csv"
MAGIC = b"onetsoccode"
STAGED_TABLE = "staged/dingel_neiman/teleworkable"
MART_TABLE = "marts/us_occupation_teleworkable"
MIN_MATCH_RATE = 0.95

_ONET = re.compile(r"\d{2}-\d{4}\.\d{2}")
_SOC = re.compile(r"\d{2}-[\dX]{4}")
_COLUMNS = ("onetsoccode", "title", "teleworkable")


# ---- fetch


def fetch(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    try:
        payload = ctx.fetcher.fetch(URL)
    except FetchError as e:
        skipped.append(f"{RAW_NAME}: {e}")
        return written, skipped
    if not payload.startswith(MAGIC):
        skipped.append(f"{RAW_NAME}: non-csv payload")
        return written, skipped
    rec = ctx.raw.put(
        theme=THEME, source=SOURCE, name=RAW_NAME, url=URL, license=LICENSE, payload=payload
    )
    written.append(rec.relative_path)
    return written, skipped


# ---- pure transforms


def parse(payload: bytes) -> list[dict[str, object]]:
    """Rows of onetsoccode / title / teleworkable (float in [0, 1]); duplicates rejected."""
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if tuple(reader.fieldnames or ()) != _COLUMNS:
        msg = f"unexpected header {reader.fieldnames}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for r in reader:
        code = (r["onetsoccode"] or "").strip()
        if not _ONET.fullmatch(code):
            msg = f"not an O*NET-SOC code: {code!r}"
            raise ValueError(msg)
        if code in seen:
            msg = f"duplicate O*NET-SOC code {code}"
            raise ValueError(msg)
        seen.add(code)
        try:
            score = float(r["teleworkable"])
        except (TypeError, ValueError) as e:
            msg = f"{code}: teleworkable {r['teleworkable']!r} is not a number"
            raise ValueError(msg) from e
        if not 0.0 <= score <= 1.0:
            msg = f"{code}: teleworkable {score} outside [0, 1]"
            raise ValueError(msg)
        out.append(
            {"onetsoccode": code, "title": (r["title"] or "").strip(), "teleworkable": score}
        )
    if not out:
        msg = "no rows"
        raise ValueError(msg)
    return out


def soc_prefix(soc: str) -> str | None:
    """Prefix of SOC-6 codes covered by a Census SOC entry; None for 'none'."""
    if not _SOC.fullmatch(soc):
        return None
    if "X" in soc:
        return soc.rstrip("X")
    return soc.rstrip("0")


def build_mart(
    rows: list[dict[str, object]], codes: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Mean-of-SOC-6-means per Census code; ValueError when < MIN_MATCH_RATE codes get a value."""
    if not rows or not codes:
        msg = "empty teleworkable rows or code table"
        raise ValueError(msg)
    by_soc6: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by_soc6[str(r["onetsoccode"])[:7]].append(float(str(r["teleworkable"])))
    soc6_mean = {k: sum(v) / len(v) for k, v in by_soc6.items()}
    out: list[dict[str, object]] = []
    matched = 0
    eligible = 0
    for c in codes:
        soc = str(c["soc_code"])
        extra = [s for s in str(c.get("soc_2010_codes") or "").split(";") if s]
        prefixes = [p for p in (soc_prefix(s) for s in (soc, *extra)) if p]
        hits = sorted(k for k in soc6_mean if any(k.startswith(p) for p in prefixes))
        value: float | None = None
        if prefixes:
            eligible += 1
        if hits:
            matched += 1
            value = sum(soc6_mean[k] for k in hits) / len(hits)
        out.append(
            {
                "occupation_code": str(c["occupation_code"]),
                "occupation": str(c["occupation"]),
                "classification": CLASSIFICATION,
                "soc_code": soc,
                "teleworkable": value,
                "n_onet": sum(len(by_soc6[k]) for k in hits),
                "source": SOURCE_TAG,
            }
        )
    rate = matched / eligible if eligible else 0.0
    if rate < MIN_MATCH_RATE:
        msg = f"teleworkable match rate {rate:.3f} ({matched}/{eligible}) below {MIN_MATCH_RATE}"
        raise ValueError(msg)
    out.sort(key=lambda r: str(r["occupation_code"]))
    return out


# ---- stage / mart


def stage(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    payload = ctx.raw.get(theme=THEME, source=SOURCE, name=RAW_NAME)
    if payload is None:
        skipped.append(f"{RAW_NAME}: no raw")
        return written, skipped
    ctx.tables.write_table(STAGED_TABLE, parse(payload))
    written.append(STAGED_TABLE)
    return written, skipped


def mart(ctx: Context, written: list[str], skipped: list[str]) -> tuple[list[str], list[str]]:
    try:
        rows = ctx.tables.read_table(STAGED_TABLE)
    except FileNotFoundError:
        skipped.append(f"{STAGED_TABLE}: no staged table")
        return written, skipped
    try:
        codes = ctx.tables.read_table(CODES_TABLE)
    except FileNotFoundError:
        skipped.append(f"{CODES_TABLE}: no staged table")
        return written, skipped
    ctx.tables.write_table(MART_TABLE, build_mart(rows, codes))
    written.append(MART_TABLE)
    return written, skipped
