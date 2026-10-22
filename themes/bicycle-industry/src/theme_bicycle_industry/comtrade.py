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

# ---- 原産国別（H8）: 輸入国 5 × 相手国（中国・台湾）× 2015–2024、輸入のみ
PARTNERS: dict[int, str] = {156: "CHN", 490: "TWN", 0: "WLD"}
ORIGIN_REPORTERS: tuple[int, ...] = (392, 842, 276, 528, 826)
ORIGIN_YEARS: tuple[int, ...] = tuple(range(2015, 2025))


# ---- 台湾の完成車輸出（H9）: reporter 490 × 仕向地 × 2015–2024、輸出のみ
TAIWAN_REPORTER = 490
TAIWAN_PARTNERS: dict[int, str] = {
    392: "JPN",
    842: "USA",
    276: "DEU",
    528: "NLD",
    826: "GBR",
    0: "WLD",
}
TAIWAN_COMMODITIES: dict[str, str] = {"8712": "bicycle_complete", "871160": "ebike_motor_only"}
TAIWAN_YEARS: tuple[int, ...] = tuple(range(2015, 2025))


def taiwan_url(year: int) -> str:
    cmds = ",".join(TAIWAN_COMMODITIES)
    partners = ",".join(str(c) for c in TAIWAN_PARTNERS)
    return (
        f"{BASE}?reporterCode={TAIWAN_REPORTER}&period={year}&cmdCode={cmds}"
        f"&flowCode=X&partnerCode={partners}"
    )


def taiwan_raw_name(year: int) -> str:
    return f"comtrade_taiwan_exports_{year}.json"


def parse_taiwan(payload: bytes, year: int) -> Parsed:
    """台湾輸出ファイル → 行 (iso3=TWN, year, flow=export, hs, product, partner, qty, net_wgt_kg,
    value_usd, source)。期間不一致は ValueError、知らない相手国・品目は skipped。"""
    try:
        doc = json.loads(payload)
    except ValueError as e:
        msg = "payload is not JSON"
        raise ValueError(msg) from e
    data = doc.get("data") if isinstance(doc, dict) else None
    if not isinstance(data, list):
        msg = f"unexpected Comtrade payload: {str(doc)[:120]!r}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    skipped: list[str] = []
    for d in data:
        if int(d["reporterCode"]) != TAIWAN_REPORTER or str(d["flowCode"]) != "X":
            skipped.append(f"unexpected reporter/flow {d['reporterCode']}/{d['flowCode']}")
            continue
        if str(d["period"]) != str(year):
            msg = f"row period mismatch: {d['period']} (want {year})"
            raise ValueError(msg)
        cmd, partner = str(d["cmdCode"]), int(d["partnerCode"])
        if cmd not in TAIWAN_COMMODITIES or partner not in TAIWAN_PARTNERS:
            skipped.append(f"unexpected cmd/partner {cmd}/{partner}")
            continue
        qty = d.get("qty")
        unit = int(d.get("qtyUnitCode", -1))
        out.append(
            {
                "iso3": "TWN",
                "year": year,
                "flow": "export",
                "hs": cmd,
                "product": TAIWAN_COMMODITIES[cmd],
                "partner": TAIWAN_PARTNERS[partner],
                "qty": float(qty) if qty is not None and unit != -1 else None,
                "net_wgt_kg": float(d["netWgt"]) if d.get("netWgt") is not None else None,
                "value_usd": float(d["primaryValue"]),
                "source": SOURCE,
            }
        )
    return Parsed(rows=out, skipped=skipped)


TAIWAN_MART_KEY: tuple[str, ...] = ("year", "hs", "partner")


def build_taiwan_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    """仕向地別に加え、OTH（= WLD − 5 か国）を足す。キー順ソート、重複は ValueError。"""
    out = [dict(r) for r in staged]
    by: dict[tuple[object, object], dict[str, dict[str, object]]] = {}
    for r in staged:
        by.setdefault((r["year"], r["hs"]), {})[str(r["partner"])] = r
    for parts in by.values():
        w = parts.get("WLD")
        named = [parts[k] for k in TAIWAN_PARTNERS.values() if k != "WLD" and k in parts]
        if w is None or len(named) != len(TAIWAN_PARTNERS) - 1:
            continue
        qtys = [w["qty"], *(r["qty"] for r in named)]
        oth_qty = None
        if all(isinstance(q, int | float) for q in qtys):
            nums = [float(q) for q in qtys if isinstance(q, int | float)]
            oth_qty = nums[0] - sum(nums[1:])
        oth_val = float(str(w["value_usd"])) - sum(float(str(r["value_usd"])) for r in named)
        out.append(
            {**w, "partner": "OTH", "qty": oth_qty, "net_wgt_kg": None, "value_usd": oth_val}
        )
    out.sort(key=lambda r: tuple(str(r[c]) for c in TAIWAN_MART_KEY))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in TAIWAN_MART_KEY)
        if k in seen:
            msg = f"duplicate taiwan key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out


def origin_url(year: int) -> str:
    reporters = ",".join(str(c) for c in ORIGIN_REPORTERS)
    cmds = ",".join(COMMODITIES)
    partners = ",".join(str(c) for c in PARTNERS if c != 0)
    return (
        f"{BASE}?reporterCode={reporters}&period={year}&cmdCode={cmds}"
        f"&flowCode=M&partnerCode={partners}"
    )


def origin_raw_name(year: int) -> str:
    return f"comtrade_origin_{year}.json"


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


def parse(payload: bytes, year: int, *, partners: bool = False) -> Parsed:
    """preview JSON → long 行。期待した形でなければ ValueError。

    行: iso3, reporter_code, year, flow(import/export), hs(8712/871160/8714), product, qty(台、
    無ければ None), qty_unit_code, net_wgt_kg, value_usd(primaryValue), source。
    `partners=True` のとき（原産国別ファイル）は `partner`（CHN/TWN）列を足し、相手国は世界計以外。
    知らない報告国・品目・フロー・相手国の行は落として skipped に出す。
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
        partner_code = int(d["partnerCode"])
        if str(d["period"]) != str(year):
            msg = f"row period mismatch: {d['period']} (want {year})"
            raise ValueError(msg)
        if not partners and partner_code != 0:
            msg = f"row partner mismatch: {partner_code} (want world = 0)"
            raise ValueError(msg)
        if partners and partner_code not in PARTNERS:
            skipped.append(f"unexpected partner {partner_code}")
            continue
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
                **({"partner": PARTNERS[partner_code]} if partners else {}),
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


ORIGIN_MART_KEY: tuple[str, ...] = ("iso3", "year", "hs", "partner")


def build_origin_mart(
    origin_rows: list[dict[str, object]], world_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    """原産国別 mart: 中国・台湾の行に、世界計（WLD）と「その他（OTH）= 世界 − 中国 − 台湾」を足す。

    世界計は `staged/comtrade/bicycle_trade`（flow=import）から取る。台数は片方でも欠ければ None。
    """
    out: list[dict[str, object]] = [dict(r) for r in origin_rows]
    by_key: dict[tuple[object, object, object, object], dict[str, object]] = {
        (r["iso3"], r["year"], r["hs"], r["partner"]): r for r in origin_rows
    }
    for w in world_rows:
        if w["flow"] != "import":
            continue
        iso3, year, hs = w["iso3"], w["year"], w["hs"]
        chn, twn = by_key.get((iso3, year, hs, "CHN")), by_key.get((iso3, year, hs, "TWN"))
        if chn is None and twn is None:
            continue
        both = chn is not None and twn is not None
        parts = [r for r in (chn, twn) if r is not None]
        qtys = [w["qty"], *(r["qty"] for r in parts)]
        oth_qty: float | None = None
        if both and all(isinstance(q, int | float) for q in qtys):
            nums = [float(q) for q in qtys if isinstance(q, int | float)]
            oth_qty = nums[0] - sum(nums[1:])
        oth_val: float | None = None
        if both:
            vals = [float(str(r["value_usd"])) for r in parts]
            oth_val = float(str(w["value_usd"])) - sum(vals)
        out.append({**w, "partner": "WLD"})
        out.append(
            {**w, "partner": "OTH", "qty": oth_qty, "net_wgt_kg": None, "value_usd": oth_val}
        )
    out.sort(key=lambda r: tuple(str(r[c]) for c in ORIGIN_MART_KEY))
    seen: set[tuple[object, ...]] = set()
    for r in out:
        k = tuple(r[c] for c in ORIGIN_MART_KEY)
        if k in seen:
            msg = f"duplicate origin key {k}"
            raise ValueError(msg)
        seen.add(k)
    return out
