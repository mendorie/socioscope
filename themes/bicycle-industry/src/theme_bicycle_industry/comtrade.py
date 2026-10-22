"""UN Comtrade preview API（キー不要）→ 自転車関連 HS の輸出入 行 の純粋変換。
決定的・fail-closed。

`https://comtradeapi.un.org/public/v1/preview/C/A/HS?...` は 1 呼び出し 1 期間・最大 500 行。
報告国 × 年 × {8712 完成自転車, 871160 電動二輪（e-bike を含む、HS2017 以降）, 8714 部品}
× {M 輸入, X 輸出}、
相手国は世界計（partnerCode=0）。並列呼び出しは 429 になるので逐次に呼ぶ。
台湾は reporterCode 490（"Other Asia, nes"）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

SOURCE = "un_comtrade"
LICENSE = (
    "UN Comtrade Terms of Use: 非商用・出典表示で利用可、バルク再配布は制限（確認 2026-10-22）。"
    "出典: UN Comtrade Database（comtradeplus.un.org）。raw は非コミット"
)
BASE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

# reporterCode → ISO3（Comtrade の preview は reporterISO を返さないので固定辞書で付ける）
REPORTERS: dict[int, str] = {
    392: "JPN",
    842: "USA",
    276: "DEU",
    528: "NLD",
    250: "FRA",
    826: "GBR",
    380: "ITA",
    156: "CHN",
    490: "TWN",  # Other Asia, nes
}
COMMODITIES: dict[str, str] = {
    "8712": "bicycle_complete",
    "871160": "ebike_motor_only",  # 電動機のみの二輪（原付・電動バイクを含む）
    "8714": "bicycle_parts",
}
FLOWS: dict[str, str] = {"M": "import", "X": "export"}
YEARS: tuple[int, ...] = tuple(range(2010, 2025))


def url(year: int) -> str:
    reporters = ",".join(str(c) for c in REPORTERS)
    cmds = ",".join(COMMODITIES)
    return (
        f"{BASE}?reporterCode={reporters}&period={year}&cmdCode={cmds}&flowCode=M,X&partnerCode=0"
    )


def raw_name(year: int) -> str:
    return f"comtrade_{year}.json"


@dataclass
class Parsed:
    rows: list[dict[str, object]]
    skipped: list[str] = field(default_factory=list)


def parse(payload: bytes, year: int) -> Parsed:
    """preview JSON → long 行。期待した形でなければ ValueError。

    行: iso3, reporter_code, year, flow(import/export), hs(8712/871160/8714), product, qty(台、
    無ければ None), qty_unit_code, net_wgt_kg, value_usd(primaryValue), source。
    知らない報告国・品目・フローの行は落として skipped に出す。
    """
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = "payload is not JSON"
        raise ValueError(msg) from e
    if not isinstance(doc, dict) or "data" not in doc:
        msg = f"unexpected Comtrade payload: {str(doc)[:120]!r}"
        raise ValueError(msg)
    data = doc["data"]
    if not isinstance(data, list):
        msg = "Comtrade 'data' is not a list"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    skipped: list[str] = []
    for d in data:
        rc = int(d["reporterCode"])
        cmd = str(d["cmdCode"])
        flow = str(d["flowCode"])
        if rc not in REPORTERS or cmd not in COMMODITIES or flow not in FLOWS:
            skipped.append(f"unexpected row reporter={rc} cmd={cmd} flow={flow}")
            continue
        if str(d["period"]) != str(year) or int(d["partnerCode"]) != 0:
            msg = f"row period/partner mismatch: {d['period']}/{d['partnerCode']} (want {year}/0)"
            raise ValueError(msg)
        qty = d.get("qty")
        unit = int(d.get("qtyUnitCode", -1))
        out.append(
            {
                "iso3": REPORTERS[rc],
                "reporter_code": rc,
                "year": year,
                "flow": FLOWS[flow],
                "hs": cmd,
                "product": COMMODITIES[cmd],
                "qty": float(qty) if qty is not None and unit != -1 else None,
                "qty_unit_code": unit,
                "net_wgt_kg": float(d["netWgt"]) if d.get("netWgt") is not None else None,
                "value_usd": float(d["primaryValue"]),
                "source": SOURCE,
            }
        )
    return Parsed(rows=out, skipped=skipped)


MART_KEY: tuple[str, ...] = ("iso3", "year", "flow", "hs")


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    out = [dict(r) for r in staged]
    out.sort(key=lambda r: tuple(str(r[c]) for c in MART_KEY))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in MART_KEY)
        if k in seen:
            msg = f"duplicate trade key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out
