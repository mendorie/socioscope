"""OECD Data Explorer SDMX-JSON（sdmx.oecd.org、鍵不要）: Government at a Glance 2025。

番外編 R16・R17（H15・H16）に使う。Pure transforms only (no I/O)。
- 公的財政（`DF_GOV_PF_2025`）: 一般政府（S13）の支出 `GE`・収入 `GR` の対 GDP 比（`PT_B1GQ`）と
  1 人当たり支出 `GE_POP`（`USD_PPP_PS`）、2007〜2024 年。
- 信頼（`DF_GOV_TDG_2025`）: 立法府への信頼 `TRUST_LE`、議会が政府に責任を問う `TRUST_PVGA`、
  国の政府への信頼 `TRUST_NG`（回答者比率 `PT_RESP`、尺度 `HMH` = 高い＋やや高い。`TRUST_PVGA` は
  `LIK` = そう思う）、2021・2023 年。
`parse` は dimensionAtObservation=AllDimensions の観測キー（`i:j:k:...`）を次元の値に戻し、
国 × 年 × 指標 の long 行にする（`format=jsondata` で Accept ヘッダなしでも SDMX-JSON）。
採用外の指標・単位・尺度・集計地域（ISO3 でない）の行は捨て、JSON でない・観測が無い・
フィルタの次元が無い場合は ValueError（fail-closed）。

License: OECD Terms & Conditions（2024-07-01 改定。出典表示で商用含め自由利用。
https://www.oecd.org/en/about/terms-conditions.html、2026-10-29 確認）。
出典表記「OECD (2025), Government at a Glance 2025, https://sdmx.oecd.org (accessed 2026-10-29)」。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

SOURCE = "oecd_gov_glance"
LICENSE = (
    "OECD Terms & Conditions 2024-07-01 (free use with attribution, "
    "https://www.oecd.org/en/about/terms-conditions.html)"
)
BASE = "https://sdmx.oecd.org/public/rest/data"
MAGIC = b"{"


@dataclass(frozen=True)
class Spec:
    """1 dataflow の取り込み仕様。metrics は MEASURE → (metric 名, 必要な UNIT_MEASURE)。"""

    metrics: Mapping[str, tuple[str, str]]
    filters: Mapping[str, str] = field(default_factory=dict)  # 次元 → 採用する値
    metric_filters: Mapping[str, Mapping[str, str]] = field(
        default_factory=dict
    )  # MEASURE 別の上書き


PF_FLOW = "OECD.GOV.GIP,DSD_GOV@DF_GOV_PF_2025,1.0"
PF_SPEC = Spec(
    metrics={
        "GE": ("gov_expenditure_pct_gdp", "PT_B1GQ"),
        "GR": ("gov_revenue_pct_gdp", "PT_B1GQ"),
        "GE_POP": ("gov_expenditure_pcap_usd_ppp", "USD_PPP_PS"),
    },
    filters={"SECTOR": "S13"},
)
URL = (
    f"{BASE}/{PF_FLOW}/A..GE+GR+GE_POP....?startPeriod=2007&endPeriod=2024"
    "&dimensionAtObservation=AllDimensions&format=jsondata"
)
RAW_NAME = "gov_pf_2025_ge_gr_gepop.json"

TRUST_FLOW = "OECD.GOV.GIP,DSD_GOV_INT@DF_GOV_TDG_2025,1.1"
TRUST_SPEC = Spec(
    metrics={
        "TRUST_LE": ("trust_legislature_pct", "PT_RESP"),
        "TRUST_PVGA": ("parliament_holds_gov_accountable_pct", "PT_RESP"),
        "TRUST_NG": ("trust_national_government_pct", "PT_RESP"),
    },
    filters={"SCALE": "HMH"},
    metric_filters={"TRUST_PVGA": {"SCALE": "LIK"}},  # 「問うと思う（likely）」の比率
)
TRUST_URL = (
    f"{BASE}/{TRUST_FLOW}/A..TRUST_LE+TRUST_PVGA+TRUST_NG......"
    "?dimensionAtObservation=AllDimensions&format=jsondata"
)
TRUST_RAW_NAME = "gov_tdg_2025_trust.json"


def _dimensions(doc: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    data = doc.get("data")
    if not isinstance(data, dict):
        msg = "oecd: no 'data' object"
        raise ValueError(msg)
    structure = data.get("structures", [None])[0] if "structures" in data else data.get("structure")
    if not isinstance(structure, dict):
        msg = "oecd: no structure"
        raise ValueError(msg)
    dims = structure.get("dimensions", {}).get("observation")
    if not isinstance(dims, list) or not dims:
        msg = "oecd: no observation dimensions (use dimensionAtObservation=AllDimensions)"
        raise ValueError(msg)
    return [(str(d["id"]), [str(v["id"]) for v in d["values"]]) for d in dims]


def parse(payload: bytes, spec: Spec = PF_SPEC) -> list[dict[str, object]]:
    """SDMX-JSON → [{iso3, year, metric, value}]（採用指標・単位・フィルタ・ISO3 の国のみ）。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = f"oecd: not JSON ({e})"
        raise ValueError(msg) from e
    if not isinstance(doc, dict):
        msg = "oecd: expected a JSON object"
        raise ValueError(msg)
    dims = _dimensions(doc)
    ids = [d[0] for d in dims]
    needed = ("REF_AREA", "MEASURE", "UNIT_MEASURE", "TIME_PERIOD", *spec.filters)
    if any(k not in ids for k in needed):
        msg = f"oecd: dimensions {needed} required, got {ids}"
        raise ValueError(msg)
    datasets = doc["data"].get("dataSets") or []
    obs = datasets[0].get("observations") if datasets else None
    if not isinstance(obs, dict) or not obs:
        msg = "oecd: no observations"
        raise ValueError(msg)
    rows: list[dict[str, object]] = []
    for key, vals in obs.items():
        idx = [int(i) for i in key.split(":")]
        if len(idx) != len(dims):
            msg = f"oecd: key {key!r} does not match {len(dims)} dimensions"
            raise ValueError(msg)
        at = {ids[n]: dims[n][1][i] for n, i in enumerate(idx)}
        found = spec.metrics.get(at["MEASURE"])
        value = vals[0] if isinstance(vals, list) and vals else None
        filters = {**spec.filters, **spec.metric_filters.get(at["MEASURE"], {})}
        if (
            found is None
            or at["UNIT_MEASURE"] != found[1]
            or any(at[k] != v for k, v in filters.items())
            or len(at["REF_AREA"]) != 3
            or value is None
        ):
            continue
        rows.append(
            {
                "iso3": at["REF_AREA"],
                "year": int(at["TIME_PERIOD"]),
                "metric": found[0],
                "value": float(value),
            }
        )
    rows.sort(key=lambda r: (str(r["iso3"]), str(r["metric"]), int(str(r["year"]))))
    return rows


def parse_trust(payload: bytes) -> list[dict[str, object]]:
    return parse(payload, TRUST_SPEC)


def build_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """国 × 年 × 指標 の long mart。同じキーが 2 行あれば ValueError。"""
    seen: set[tuple[str, int, str]] = set()
    out: list[dict[str, object]] = []
    for r in staged:
        key = (str(r["iso3"]), int(str(r["year"])), str(r["metric"]))
        if key in seen:
            msg = f"oecd: duplicate {key}"
            raise ValueError(msg)
        seen.add(key)
        out.append(
            {
                "iso3": key[0],
                "year": key[1],
                "metric": key[2],
                "value": r["value"],
                "source": SOURCE,
            }
        )
    out.sort(key=lambda r: (str(r["iso3"]), str(r["metric"]), int(str(r["year"]))))
    return out
