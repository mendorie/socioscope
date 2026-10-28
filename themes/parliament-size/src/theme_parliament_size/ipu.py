"""IPU Parline API (https://api.data.ipu.org/v1, JSON:API, no key): chambers and countries.

Pure transforms only (no I/O). The API returns, per entity, dozens of attributes; each is either a
list of time-bounded records ``{"value", "date_from", "date_to", ...}``, a single object with a
``value`` key, or a bare scalar. A record value may itself be an amount with a unit
(``{"type": "JPY", "value": 71975000000}``) or a list of terms (``[{"term": "oecd_members"}]``).
``parse`` keeps the attributes in ``CHAMBER_ATTRS`` / ``COUNTRY_ATTRS`` as one long row per
record and is fail-closed on any shape it does not expect.

License (API ``meta.licence``, confirmed 2026-10-27): CC BY-NC-SA 4.0. Non-commercial use only.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Literal

SOURCE = "ipu_parline"
LICENSE = (
    "CC BY-NC-SA 4.0 (Inter-Parliamentary Union, Parline, https://data.ipu.org; "
    "non-commercial, attribution, share-alike)"
)
BASE = "https://api.data.ipu.org/v1"
PAGE_SIZE = 100
MAX_PAGES = 10  # 281 chambers / 193 countries at 100 per page -> 3 / 2 pages; hard stop for safety

Kind = Literal["chambers", "countries"]
KINDS: tuple[Kind, ...] = ("chambers", "countries")
_TYPE_OF: dict[str, str] = {"chambers": "Chamber", "countries": "Country"}

CHAMBER_ATTRS: tuple[str, ...] = (
    "chamber_name",
    "parliament",  # country code the chamber belongs to
    "statutory_members_number",
    "current_members_number",
    "directly_elected_number",
    "designation_mode",
    "electoral_system",
    "electoral_subsystem",
    "major_sys_elect_mems",  # seats in the majoritarian tier of a mixed system
    "mixed_sys_elect_mems",  # seats in the proportional tier of a mixed system
    "permanent_staff_number",
    "is_staff_combined_parl",
    "chamber_budget",
    "chamber_budget_ppp",
    "is_budget_combined_parl",
    "basic_salary",
    "basic_salary_ppp",
    "num_days_parl_plen",
    "num_cham_perm_committees",
    # 役割の補助指標（追加 2026-10-27、R7）
    "num_written_question_ask",  # written questions put to the government per year
    "members_government_number",  # members holding a government post
    "members_government_percentage",
    "is_carry_out_inquiries",  # chamber conducts inquiries / investigations
    "approx_num_government_app",  # government appointments the chamber scrutinises
)
COUNTRY_ATTRS: tuple[str, ...] = (
    "country_name",
    "iso_alpha3",
    "region",
    "subregion",
    "political_system",
    "local_currency",
    "members_per_country",
    "population_in_thousands",
    "inhabitants_per_parliament",
    "parliament_devoted_budget_perc",
    "ppp_conversion_factor",
    "other_groupings",
)
ATTRS: dict[str, tuple[str, ...]] = {"chambers": CHAMBER_ATTRS, "countries": COUNTRY_ATTRS}

STAGED_COLUMNS: tuple[str, ...] = (
    "kind",
    "entity_id",
    "attribute",
    "seq",
    "value",
    "value_num",
    "unit",
    "date_from",
    "date_to",
    "source",
)


def url(kind: Kind, page: int) -> str:
    return f"{BASE}/{kind}?page[size]={PAGE_SIZE}&page[number]={page}"


def raw_name(kind: Kind, page: int) -> str:
    return f"{kind}_p{page}.json"


# ---- parse --------------------------------------------------------------------------------------

_CUR_NUM = re.compile(r"^(?:[A-Z]{3}\s+)?-?[\d,]+(?:\.\d+)?$")


def _unwrap(value: object) -> tuple[object, str]:
    """``{"type": "JPY", "value": 123}`` -> (123, "JPY"); anything else -> (value, "")."""
    if isinstance(value, dict) and "value" in value and isinstance(value.get("type"), str):
        return value["value"], str(value["type"])
    return value, ""


def _num(value: object) -> float | None:
    """Numeric view of a record value: numbers as is, 'JPY 68,113,000,000' -> 68113000000.0."""
    value, _ = _unwrap(value)
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and _CUR_NUM.match(value.strip()):
        digits = value.strip().split()[-1].replace(",", "")
        return float(digits)
    return None


def _text(value: object) -> str:
    value, _ = _unwrap(value)
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, list):
        return ";".join(_text(v) for v in value)
    if isinstance(value, dict):
        if set(value) == {"term"}:
            return _text(value["term"])
        if "value" in value:
            return _text(value["value"])
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    msg = f"unsupported value type {type(value).__name__}"
    raise ValueError(msg)


def _records(attr: str, raw: object) -> list[tuple[object, str, str]]:
    """Normalise an attribute payload to [(value, date_from, date_to)]."""
    if isinstance(raw, list):
        out: list[tuple[object, str, str]] = []
        for rec in raw:
            if not isinstance(rec, dict) or "value" not in rec:
                msg = f"attribute {attr}: list item without 'value'"
                raise ValueError(msg)
            out.append(
                (rec["value"], str(rec.get("date_from") or ""), str(rec.get("date_to") or ""))
            )
        return out
    if isinstance(raw, dict):
        if "value" not in raw:
            msg = f"attribute {attr}: object without 'value'"
            raise ValueError(msg)
        return [(raw["value"], str(raw.get("date_from") or ""), str(raw.get("date_to") or ""))]
    return [(raw, "", "")]


def parse(payload: bytes, kind: Kind, page: int) -> list[dict[str, object]]:
    """One JSON:API page -> long rows for the attributes of interest. Fail-closed."""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"{kind} page {page}: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, dict) or not isinstance(doc.get("data"), list):
        msg = f"{kind} page {page}: missing 'data' list"
        raise ValueError(msg)
    want_type = _TYPE_OF[kind]
    rows: list[dict[str, object]] = []
    for item in doc["data"]:
        if not isinstance(item, dict) or item.get("type") != want_type:
            msg = f"{kind} page {page}: item is not of type {want_type}"
            raise ValueError(msg)
        entity_id = item.get("id")
        attrs = item.get("attributes")
        if not isinstance(entity_id, str) or not isinstance(attrs, dict):
            msg = f"{kind} page {page}: item without id/attributes"
            raise ValueError(msg)
        for attr in ATTRS[kind]:
            if attr not in attrs or attrs[attr] is None:
                continue
            for seq, (value, d_from, d_to) in enumerate(_records(attr, attrs[attr])):
                rows.append(
                    {
                        "kind": kind,
                        "entity_id": entity_id,
                        "attribute": attr,
                        "seq": seq,
                        "value": _text(value),
                        "value_num": _num(value),
                        "unit": _unwrap(value)[1],
                        "date_from": d_from,
                        "date_to": d_to,
                        "source": SOURCE,
                    }
                )
    if not rows and doc["data"]:
        msg = f"{kind} page {page}: no attribute of interest found (schema changed?)"
        raise ValueError(msg)
    return rows


def has_next(payload: bytes) -> bool:
    doc = json.loads(payload)
    links = doc.get("links") if isinstance(doc, dict) else None
    return bool(isinstance(links, dict) and links.get("next"))


# ---- mart --------------------------------------------------------------------------------------

MART_COLUMNS: tuple[str, ...] = (
    "iso3",
    "country",
    "region",
    "subregion",
    "oecd_member",
    "chamber_id",
    "chamber_type",
    "chamber_name",
    "electoral_system",
    "electoral_subsystem",
    "designation_mode",
    "statutory_seats",
    "statutory_seats_since",
    "current_members",
    "directly_elected",
    "majoritarian_tier_seats",
    "proportional_tier_seats",
    "permanent_staff",
    "staff_year",
    "staff_combined_parl",
    "chamber_budget",
    "budget_currency",
    "chamber_budget_ppp",
    "budget_year",
    "budget_combined_parl",
    "basic_salary_ppp",
    "salary_year",
    "plenary_days",
    "plenary_year",
    "committees",
    "written_questions",
    "written_questions_year",
    "members_in_government",
    "members_in_government_pct",
    "carries_out_inquiries",
    "government_appointments",
    "members_per_country",
    "population_thousands",
    "population_year",
    "parliament_budget_pct_gov",
    "source",
)

# attribute -> (value column, year column or None, unit column or None)
_NUMERIC_LATEST: dict[str, tuple[str, str | None, str | None]] = {
    "statutory_members_number": ("statutory_seats", "statutory_seats_since", None),
    "current_members_number": ("current_members", None, None),
    "directly_elected_number": ("directly_elected", None, None),
    "major_sys_elect_mems": ("majoritarian_tier_seats", None, None),
    "mixed_sys_elect_mems": ("proportional_tier_seats", None, None),
    "permanent_staff_number": ("permanent_staff", "staff_year", None),
    "chamber_budget": ("chamber_budget", "budget_year", "budget_currency"),
    "chamber_budget_ppp": ("chamber_budget_ppp", None, None),
    "basic_salary_ppp": ("basic_salary_ppp", "salary_year", None),
    "num_days_parl_plen": ("plenary_days", "plenary_year", None),
    "num_cham_perm_committees": ("committees", None, None),
    "num_written_question_ask": ("written_questions", "written_questions_year", None),
    "members_government_number": ("members_in_government", None, None),
    "members_government_percentage": ("members_in_government_pct", None, None),
    "approx_num_government_app": ("government_appointments", None, None),
}
_TEXT_LATEST = {
    "chamber_name": "chamber_name",
    "electoral_system": "electoral_system",
    "electoral_subsystem": "electoral_subsystem",
    "designation_mode": "designation_mode",
}
_BOOL_LATEST = {
    "is_staff_combined_parl": "staff_combined_parl",
    "is_budget_combined_parl": "budget_combined_parl",
    "is_carry_out_inquiries": "carries_out_inquiries",
}


def _latest(rows: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None:
    """Latest record by date_from (then seq); records with an empty value are ignored."""
    cands = [r for r in rows if r["value"] not in ("", None)]
    if not cands:
        return None
    return max(cands, key=lambda r: (str(r["date_from"]), int(str(r["seq"]))))


def _year(date: object) -> int | None:
    s = str(date or "")
    return int(s[:4]) if len(s) >= 4 and s[:4].isdigit() else None


def _index(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, dict[str, list[Mapping[str, object]]]]:
    out: dict[str, dict[str, list[Mapping[str, object]]]] = {}
    for r in rows:
        out.setdefault(str(r["entity_id"]), {}).setdefault(str(r["attribute"]), []).append(r)
    return out


def _country_name(rec: Mapping[str, object] | None) -> str:
    """country_name is {"en": ..., "fr": ...} (stored as JSON text); take the English name."""
    if rec is None:
        return ""
    text = str(rec["value"])
    if text.startswith("{"):
        parsed = json.loads(text)
        return str(parsed.get("en", text))
    return text


def build_mart(
    chamber_rows: Sequence[Mapping[str, object]], country_rows: Sequence[Mapping[str, object]]
) -> list[dict[str, object]]:
    """One row per chamber with the latest value of each attribute, joined to its country."""
    countries = _index(country_rows)
    out: list[dict[str, object]] = []
    for chamber_id, attrs in _index(chamber_rows).items():
        parl = _latest(attrs.get("parliament", []))
        cc = str(parl["value"]) if parl else chamber_id.split("-")[0]
        c = countries.get(cc, {})
        iso3_rec = _latest(c.get("iso_alpha3", []))
        if iso3_rec is None:
            msg = f"chamber {chamber_id}: country {cc} not in countries pages"
            raise ValueError(msg)
        pop = _latest(c.get("population_in_thousands", []))
        mpc = _latest(c.get("members_per_country", []))
        groups = _latest(c.get("other_groupings", []))
        region = _latest(c.get("region", []))
        subregion = _latest(c.get("subregion", []))
        budget_pct = _latest(c.get("parliament_devoted_budget_perc", []))
        suffix = chamber_id.split("-")[-1][:2]
        row: dict[str, object] = {
            "iso3": str(iso3_rec["value"]),
            "country": _country_name(_latest(c.get("country_name", []))),
            "region": str(region["value"]) if region else "",
            "subregion": str(subregion["value"]) if subregion else "",
            "oecd_member": "oecd_members" in str(groups["value"]).split(";") if groups else False,
            "chamber_id": chamber_id,
            "chamber_type": {"LC": "lower", "UC": "upper"}.get(suffix, "unknown"),
            "members_per_country": mpc["value_num"] if mpc else None,
            "population_thousands": pop["value_num"] if pop else None,
            "population_year": _year(pop["date_from"]) if pop else None,
            "parliament_budget_pct_gov": budget_pct["value_num"] if budget_pct else None,
            "source": SOURCE,
        }
        for attr, col in _TEXT_LATEST.items():
            rec = _latest(attrs.get(attr, []))
            row[col] = str(rec["value"]) if rec else ""
        for attr, col in _BOOL_LATEST.items():
            rec = _latest(attrs.get(attr, []))
            row[col] = (str(rec["value"]) == "True") if rec else None
        for attr, (col, ycol, ucol) in _NUMERIC_LATEST.items():
            rec = _latest(attrs.get(attr, []))
            row[col] = rec["value_num"] if rec else None
            if ycol:
                row[ycol] = _year(rec["date_from"]) if rec else None
            if ucol:
                row[ucol] = str(rec["unit"]) if rec else ""
        out.append({col: row.get(col) for col in MART_COLUMNS})
    out.sort(key=lambda r: (str(r["iso3"]), str(r["chamber_id"])))
    ids = [r["chamber_id"] for r in out]
    if len(ids) != len(set(ids)):
        msg = "duplicate chamber_id in mart"
        raise ValueError(msg)
    return out
