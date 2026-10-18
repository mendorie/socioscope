"""NHK 放送文化研究所「日本人の意識」調査 Q49 結婚観 JSON -> long rows (no I/O). H12.

One request (``URL``, no key, verified 2026-10-18): ``q49[0].q[0].a[]`` lists the answers
(01 「するのが当然」に近い / 02 「必ずしも結婚する必要はない」に近い / 03 どちらともいえない・
わからない・無回答), each with ``year["1993".."2018"].{ratio, number}.{all, male, female, age[7],
cross[14], city[5], acad[7]}``. ``parse`` takes ``all`` / ``male`` / ``female`` and the seven
``age`` groups (the site labels them 16-19歳 … 70歳以上; ``cross`` / ``city`` / ``acad`` are not
taken).
A value prefixed ``*`` is the site's small-sample mark (< 50 respondents) and is read as the
number. The document shape is validated with Pydantic; any other year, a missing group, a short
``age`` list, a non-numeric value or a repeated answer code is a ``ValueError`` (fail closed).

The survey ran every five years 1973–2018; this question was asked from 1993 (6 rounds). The
2022 / 2024 follow-up surveys use a four-point scale and are not comparable (not taken).

License (usage.html, 2024-01-24): attribution required, derived works must say so, no commercial
use -> the raw JSON is **not committed** (manifest only); staged / mart rows carry the source.
"""

import json
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

__all__ = [
    "AGE_LABELS",
    "GROUPS",
    "LICENSE",
    "MART_KEY",
    "QUESTION",
    "RAW_NAME",
    "SOURCE",
    "URL",
    "YEARS",
    "build_mart",
    "parse",
]

URL = "https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/data/q49.json"
RAW_NAME = "q49.json"
SOURCE = "nhk_nihonjin_ishiki"
QUESTION = "q49"
LICENSE = (
    "NHK放送文化研究所「日本人の意識」調査 サイト利用ルール "
    "(https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/usage.html, 2024-01-24 制定): "
    "出典を記載すれば利用可、編集・加工した場合はその旨を明記、営利目的の利用は不可（要問い合わせ）。"
    "raw はコミットしない。出典表記: NHK放送文化研究所「日本人の意識」調査"
    "（https://www.nhk.or.jp/bunken/yoron-isiki/nihonzin/）を加工して作成"
)
YEARS: tuple[int, ...] = (1993, 1998, 2003, 2008, 2013, 2018)
AGE_LABELS: tuple[str, ...] = (
    "16-19歳",
    "20-29歳",
    "30-39歳",
    "40-49歳",
    "50-59歳",
    "60-69歳",
    "70歳以上",
)
GROUPS: tuple[str, ...] = ("all", "male", "female", "age")
MART_KEY: tuple[str, ...] = ("question", "year", "answer_code", "group", "group_label")


class _Breakdown(BaseModel):
    model_config = ConfigDict(extra="ignore")
    all: int | str
    male: int | str
    female: int | str
    age: list[int | str]


class _YearData(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ratio: _Breakdown
    number: _Breakdown


class _Answer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    text: str
    short: str = ""
    year: dict[str, _YearData]


class _Question(BaseModel):
    model_config = ConfigDict(extra="ignore")
    a: list[_Answer]


class _Topic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q: list[_Question]


class _Doc(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q49: list[_Topic]


def _number(value: int | str, where: str) -> float:
    if isinstance(value, int):
        return float(value)
    s = value.strip().removeprefix("*")
    try:
        return float(s)
    except ValueError:
        msg = f"{where}: non-numeric value {value!r}"
        raise ValueError(msg) from None


def _row(
    year: int, answer: _Answer, group: str, label: str, ratio: int | str, number: int | str
) -> dict[str, object]:
    where = f"q49 {year} answer {answer.id} {group} {label}".rstrip()
    n = _number(number, where)
    if n != int(n):
        msg = f"{where}: respondent count {number!r} is not an integer"
        raise ValueError(msg)
    return {
        "question": QUESTION,
        "year": year,
        "answer_code": answer.id,
        "answer_label": answer.text,
        "answer_short": answer.short,
        "group": group,
        "group_label": label,
        "ratio_pct": _number(ratio, where),
        "n": int(n),
        "source": SOURCE,
    }


def _answers(payload: bytes) -> list[_Answer]:
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = "unexpected NHK response shape: not json"
        raise ValueError(msg) from e
    parsed = _Doc.model_validate(doc)  # pydantic ValidationError is a ValueError
    if len(parsed.q49) != 1 or len(parsed.q49[0].q) != 1:
        msg = f"q49.json must hold exactly one question, got {len(parsed.q49)} topic(s)"
        raise ValueError(msg)
    answers = parsed.q49[0].q[0].a
    if not answers:
        msg = "q49.json: no answers"
        raise ValueError(msg)
    ids = [a.id for a in answers]
    if len(ids) != len(set(ids)):
        msg = f"q49.json: duplicate answer code in {ids}"
        raise ValueError(msg)
    return answers


def parse(payload: bytes) -> list[dict[str, object]]:
    """JSON bytes -> rows ``question, year, answer_code, answer_label, answer_short, group,
    group_label, ratio_pct, n, source`` in (year, answer, group) order. ``ValueError`` on any
    deviation from the documented shape (see the module docstring)."""
    answers = _answers(payload)
    years: set[int] = set()
    for a in answers:
        for y in a.year:
            if not y.isdigit() or int(y) not in YEARS:
                msg = f"q49.json answer {a.id}: unexpected year {y!r} (expected one of {YEARS})"
                raise ValueError(msg)
            years.add(int(y))
    out: list[dict[str, object]] = []
    for year in sorted(years):
        for a in answers:
            data = a.year.get(str(year))
            if data is None:
                msg = f"q49.json answer {a.id}: year {year} missing"
                raise ValueError(msg)
            r, n = data.ratio, data.number
            if len(r.age) != len(AGE_LABELS) or len(n.age) != len(AGE_LABELS):
                msg = f"q49.json {year} answer {a.id}: age must have {len(AGE_LABELS)} entries"
                raise ValueError(msg)
            out.append(_row(year, a, "all", "", r.all, n.all))
            out.append(_row(year, a, "male", "", r.male, n.male))
            out.append(_row(year, a, "female", "", r.female, n.female))
            for label, rv, nv in zip(AGE_LABELS, r.age, n.age, strict=True):
                out.append(_row(year, a, "age", label, rv, nv))
    return out


def build_mart(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """``marts/jp_norms_nhk``: rows sorted by (question, year, answer_code, group, group_label)
    with group / age label in declaration order; duplicate keys raise ``ValueError``."""

    def key(r: dict[str, object]) -> tuple[object, ...]:
        label = str(r["group_label"])
        return (
            str(r["question"]),
            int(str(r["year"])),
            str(r["answer_code"]),
            GROUPS.index(str(r["group"])),
            AGE_LABELS.index(label) if label else -1,
        )

    out = sorted((dict(r) for r in rows), key=key)
    keys = [tuple(r[c] for c in MART_KEY) for r in out]
    if len(keys) != len(set(keys)):
        dup = next(k for i, k in enumerate(keys) if k in keys[:i])
        msg = f"duplicate key {MART_KEY} = {dup}"
        raise ValueError(msg)
    return out
