"""フランス国民議会 open data「Dossiers législatifs」（立法期ごとの zip、JSON）: 法律のドシエ。

1 ドシエ 1 行（H2d）。Pure transforms only (no I/O)。
zip の `json/dossierParlementaire/*.json` だけを読む（`json/document/` は法案本文のメタで対象外）。
`procedureParlementaire.libelle` に「loi」または「ratification」を含むドシエを法律案とし、
提出の種別は本文中の文書 uid の接頭辞で決める（`PRJL…` = projet de loi（政府提出）、`PION…` =
proposition de loi（議員提出））。公布は `codeActe == "PROM-PUB"` の `dateActe`。

License: Licence Ouverte / Open Licence 2.0（Etalab。出典表示で利用可。
data.assemblee-nationale.fr）。
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import Mapping, Sequence

SOURCE = "fr_an_dossiers"
LICENSE = (
    "Licence Ouverte 2.0 (Etalab; Assemblée nationale open data, "
    "https://data.assemblee-nationale.fr)"
)
BASE = "https://data.assemblee-nationale.fr/static/openData/repository"
# 第 16 期 2022-06-22〜2024-06-09、第 17 期 2024-07-08〜。第 15 期以前は zip が無い
LEGISLATURES: tuple[int, ...] = (16, 17)
MAGIC = b"PK"
_DOSSIER_DIR = "json/dossierParlementaire/"
_TEXT_UID = re.compile(r'"(PRJL|PION)[A-Z]{2,4}R5')


def url(legislature: int) -> str:
    return f"{BASE}/{legislature}/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"


def raw_name(legislature: int) -> str:
    return f"dossiers_legislatifs_L{legislature}.json.zip"


def is_law(libelle: str) -> bool:
    """法律案のドシエか。「loi」を含む種別と、条約批准法（Projet de ratification …）。"""
    low = libelle.lower()
    return "loi" in low or "ratification" in low


def _promulgation(o: object) -> str | None:
    if isinstance(o, dict):
        if o.get("codeActe") == "PROM-PUB":
            return str(o.get("dateActe") or "")[:10] or None
        for v in o.values():
            d = _promulgation(v)
            if d:
                return d
    elif isinstance(o, list):
        for v in o:
            d = _promulgation(v)
            if d:
                return d
    return None


def parse(payload: bytes, legislature: int) -> list[dict[str, object]]:
    """zip → 法律案ドシエ 1 行: uid, legislature, procedure, origin（government/member/unknown）,
    promulgated（bool）, promulgation_date。Fail-closed（zip でない・ドシエが無い）。"""
    try:
        z = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as e:
        msg = f"fr_an L{legislature}: payload is not a zip"
        raise ValueError(msg) from e
    names = [n for n in z.namelist() if n.startswith(_DOSSIER_DIR) and n.endswith(".json")]
    if not names:
        msg = f"fr_an L{legislature}: no {_DOSSIER_DIR}*.json in zip"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for name in sorted(names):
        raw = z.read(name)
        doc = json.loads(raw).get("dossierParlementaire")
        if not isinstance(doc, dict):
            msg = f"fr_an L{legislature}: {name} without dossierParlementaire"
            raise ValueError(msg)
        proc = doc.get("procedureParlementaire") or {}
        libelle = str(proc.get("libelle") or "")
        if not is_law(libelle):
            continue
        kinds = set(_TEXT_UID.findall(raw.decode("utf-8")))
        origin = "unknown"
        if kinds == {"PRJL"}:
            origin = "government"
        elif kinds == {"PION"}:
            origin = "member"
        date = _promulgation(doc.get("actesLegislatifs"))
        rows.append(
            {
                "uid": str(doc.get("uid") or name),
                "legislature": legislature,
                "procedure": libelle,
                "origin": origin,
                "promulgated": date is not None,
                "promulgation_date": date,
            }
        )
    return rows


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """公布された法律だけ: iso3, year（公布年）, uid, legislature, procedure, origin。

    立法期をまたぐドシエは両方の zip に入る（同じ uid）ので、legislature の大きい方（公布まで
    含む新しい記録）を残す。
    """
    latest: dict[str, Mapping[str, object]] = {}
    for r in staged:
        uid = str(r["uid"])
        prev = latest.get(uid)
        if prev is None or int(str(r["legislature"])) > int(str(prev["legislature"])):
            latest[uid] = r
    out: list[dict[str, object]] = []
    for uid, r in latest.items():
        if not r.get("promulgated"):
            continue
        out.append(
            {
                "iso3": "FRA",
                "year": int(str(r["promulgation_date"])[:4]),
                "promulgation_date": r["promulgation_date"],
                "uid": uid,
                "legislature": int(str(r["legislature"])),
                "procedure": r["procedure"],
                "origin": r["origin"],
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: (str(r["promulgation_date"]), str(r["uid"])))
    return out
