"""総務省 衆議院議員総選挙 結果調 Excel: 都道府県別 有権者数、比例代表 ブロック別 党派別得票・議席。

Pure transforms only (no I/O). One workbook per (election, table). 第 50 回（2024-10-27）は .xls、
第 51 回（2026-02-08）は .xlsx。`parse_*` は行リスト（`rows_of` の出力）を受ける純粋関数で、
見出しや合計の検算に失敗したら ValueError（fail-closed）。

License: 総務省ホームページは政府標準利用規約（第 2.0 版、CC BY 4.0 互換）。出典表示で利用可。
"""

from __future__ import annotations

import io
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

SOURCE = "soumu_senkyo"
LICENSE = (
    "政府標準利用規約（第2.0版、CC BY 4.0 互換）。出典: 総務省「衆議院議員総選挙 結果調」"
    "（https://www.soumu.go.jp/senkyo/senkyo_s/data/）"
)
BASE = "https://www.soumu.go.jp/main_content/"

# 表のキー（結果調の章立てに従う）:
#   electorate_smd     2(1) 都道府県別 有権者数・投票者数・投票率（小選挙区）
#   electorate_pr      2(2) 都道府県別 有権者数・投票者数・投票率（比例代表）
#   pr_votes_by_block  3(10) 選挙区（ブロック）別 党派別 得票数（比例代表）
#   pr_seats_table     3(12) 党派別 議席配分表（比例代表）
#   winners_by_party   3(1) 届出政党等別 男女別 新前元別 当選人数（小選挙区、比例代表）
KEYS: tuple[str, ...] = (
    "electorate_smd",
    "electorate_pr",
    "pr_votes_by_block",
    "pr_seats_table",
    "winners_by_party",
)


@dataclass(frozen=True)
class Election:
    number: int
    date: str
    ext: str  # xls / xlsx（既定）
    files: dict[str, str]  # key -> main_content id
    seats: tuple[int, int] = (289, 176)  # (小選挙区, 比例代表) の法定定数。当選人数表の検算に使う
    exts: dict[str, str] = field(default_factory=dict)  # key -> ext（既定と違う表だけ）


def _ids(prefix: str, numbers: Sequence[str]) -> dict[str, str]:
    return dict(zip(KEYS, [f"{prefix}{n}" for n in numbers], strict=True))


# 資料集ページ senkyo/senkyo_s/data/shugiin<N>/index.html の Excel リンク（2026-10-27 確認）。
# 第 42〜44 回（2000・2003・2005 年）は Excel 配布がない（ページ無しまたは PDF のみ）。
ELECTIONS: dict[int, Election] = {
    45: Election(
        45,
        "2009-08-30",
        "xls",
        _ids("0000", ("37612", "37614", "37637", "37639", "37622")),
        seats=(300, 180),
    ),
    46: Election(
        46,
        "2012-12-16",
        "xls",
        _ids("000", ("194180", "194182", "194192", "194198", "194183")),
        seats=(300, 180),
    ),
    47: Election(
        47,
        "2014-12-14",
        "xls",
        _ids("000", ("328940", "328942", "328952", "328954", "328943")),
        seats=(295, 180),
    ),
    48: Election(
        48,
        "2017-10-22",
        "xls",
        _ids("000", ("516715", "516717", "516728", "516730", "516719")),
    ),
    49: Election(
        49,
        "2021-10-31",
        "xls",
        _ids("000", ("776963", "776965", "776976", "776978", "776967")),
        exts={"pr_votes_by_block": "xlsx", "pr_seats_table": "xlsx"},
    ),
    50: Election(
        50,
        "2024-10-27",
        "xls",
        {
            "electorate_smd": "000979118",
            "electorate_pr": "000979120",
            "pr_votes_by_block": "000979131",
            "pr_seats_table": "000979133",
            "winners_by_party": "000979122",
        },
    ),
    51: Election(
        51,
        "2026-02-08",
        "xlsx",
        {
            "electorate_smd": "001061471",
            "electorate_pr": "001061473",
            "pr_votes_by_block": "001061484",
            "pr_seats_table": "001061486",
            "winners_by_party": "001061475",
        },
    ),
}

MAGIC: dict[str, bytes] = {"xls": b"\xd0\xcf\x11\xe0", "xlsx": b"PK"}
BLOCKS: tuple[str, ...] = (
    "北海道",
    "東北",
    "北関東",
    "南関東",
    "東京",
    "北陸信越",
    "東海",
    "近畿",
    "中国",
    "四国",
    "九州",
)
N_PREFS = 47


def ext_of(election: int, key: str | None = None) -> str:
    e = ELECTIONS[election]
    return e.exts.get(key, e.ext) if key else e.ext


def url(election: int, key: str) -> str:
    return f"{BASE}{ELECTIONS[election].files[key]}.{ext_of(election, key)}"


def raw_name(election: int, key: str) -> str:
    return f"shugiin{election}_{key}.{ext_of(election, key)}"


def magic(election: int, key: str | None = None) -> bytes:
    return MAGIC[ext_of(election, key)]


Rows = list[list[object]]


def xls_rows(payload: bytes, sheet: int = 0) -> Rows:
    import xlrd

    try:
        sh = xlrd.open_workbook(file_contents=payload).sheets()[sheet]
    except Exception as e:
        msg = "payload is not a readable xls"
        raise ValueError(msg) from e
    return [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]


def xlsx_rows(payload: bytes, sheet: int = 0) -> Rows:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
        ws = wb.worksheets[sheet]
    except Exception as e:
        msg = "payload is not a readable xlsx"
        raise ValueError(msg) from e
    return [list(r) for r in ws.iter_rows(values_only=True)]


def rows_of(payload: bytes, election: int, sheet: int = 0, key: str | None = None) -> Rows:
    return (xls_rows if ext_of(election, key) == "xls" else xlsx_rows)(payload, sheet)


# ---- helpers -----------------------------------------

_PREF = re.compile(r"^(北海道|.+?[都府県])$")
_BLOCK_MARK = re.compile(r"[<＜](.+?)選挙区[>＞]")


def _cell(row: Sequence[object], i: int) -> object:
    return row[i] if i < len(row) else None


def _text(v: object) -> str:
    return "" if v is None else str(v).replace("　", " ").strip()


def _num(v: object) -> float | None:
    """数値セル、または '694,578.943' のような文字列を float に。空・非数値は None。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, int | float):
        return float(v)
    s = _text(v).replace(",", "")
    if s and re.match(r"^-?\d+(\.\d+)?$", s):
        return float(s)
    return None


def _f(v: object) -> float:
    return float(str(v))


def _block_name(s: str) -> str:
    return "東京" if s == "東京都" else s


def _check_sum(label: str, parts: float, total: float, tol: float = 0.01) -> None:
    if abs(parts - total) > tol:
        msg = f"{label}: parts {parts} != total {total}"
        raise ValueError(msg)


# ---- 2(1) 都道府県別 有権者数（小選挙区）----------------------------


def parse_electorate_smd(rows: Rows) -> list[dict[str, object]]:
    """→ [{pref, electorate, voters}] 47 行。'計' 行で検算。"""
    out: list[dict[str, object]] = []
    total: tuple[float, float] | None = None
    for row in rows:
        label = _text(_cell(row, 0))
        el, vo = _num(_cell(row, 3)), _num(_cell(row, 6))
        if el is None or vo is None:
            continue
        if label == "計":
            total = (el, vo)
        elif _PREF.match(label):
            out.append({"pref": label, "electorate": el, "voters": vo})
    if len(out) != N_PREFS or total is None:
        msg = f"electorate_smd: expected {N_PREFS} prefectures + total row, got {len(out)}"
        raise ValueError(msg)
    _check_sum("electorate_smd electorate", sum(_f(r["electorate"]) for r in out), total[0])
    _check_sum("electorate_smd voters", sum(_f(r["voters"]) for r in out), total[1])
    return out


# ---- 2(2) 都道府県別 有権者数（比例代表、ブロック付き）---------------------


def parse_electorate_pr(rows: Rows) -> list[dict[str, object]]:
    """→ [{block, pref, electorate, voters}] 47 行。ブロック '計' 行と総計で検算。"""
    out: list[dict[str, object]] = []
    block = ""
    block_sum = 0.0
    grand: float | None = None
    for row in rows:
        b = _text(_cell(row, 0))
        label = _text(_cell(row, 1))
        el, vo = _num(_cell(row, 4)), _num(_cell(row, 7))
        if b:
            block = _block_name(b)
            block_sum = 0.0
        if el is None or vo is None:
            continue
        if label == "計":
            if b:  # 最終行: 全国計（ブロック列が空か '計'）
                grand = el
            elif block_sum:
                _check_sum(f"electorate_pr block {block}", block_sum, el)
            else:
                grand = el
            continue
        if _PREF.match(label):
            if not block:
                msg = f"electorate_pr: prefecture {label} before any block"
                raise ValueError(msg)
            out.append({"block": block, "pref": label, "electorate": el, "voters": vo})
            block_sum += el
    if len(out) != N_PREFS:
        msg = f"electorate_pr: expected {N_PREFS} prefectures, got {len(out)}"
        raise ValueError(msg)
    blocks = sorted({str(r["block"]) for r in out})
    if set(blocks) != set(BLOCKS):
        msg = f"electorate_pr: blocks {blocks} != {BLOCKS}"
        raise ValueError(msg)
    if grand is not None:
        _check_sum("electorate_pr grand total", sum(_f(r["electorate"]) for r in out), grand)
    return out


# ---- 3(10) 比例代表 選挙区別 党派別 得票数 -------------------------


def parse_pr_votes(rows: Rows) -> list[dict[str, object]]:
    """→ [{block, rank, party, votes, share_pct}]。ブロックごとに '得票総数' で検算。"""
    out: list[dict[str, object]] = []
    block = ""
    acc = 0.0
    checked: set[str] = set()
    for row in rows:
        for g in (0, 4, 8):
            cells = [_cell(row, g + i) for i in range(4)]
            m = _BLOCK_MARK.search(_text(cells[1])) or _BLOCK_MARK.search(_text(cells[0]))
            if m and g == 0:
                block = _block_name(m.group(1))
                acc = 0.0
                break
            party = _text(cells[1])
            votes = _num(cells[2])
            if party == "得票総数" and votes is not None:
                _check_sum(f"pr_votes block {block}", acc, votes)
                checked.add(block)
                break
            rank = _num(cells[0])
            if rank is None or votes is None or not party:
                continue
            if not block:
                msg = "pr_votes: party row before any block marker"
                raise ValueError(msg)
            out.append(
                {
                    "block": block,
                    "rank": int(rank),
                    "party": party,
                    "votes": votes,
                    "share_pct": _num(cells[3]),
                }
            )
            acc += votes
    if checked != set(BLOCKS):
        msg = f"pr_votes: blocks with a verified total {sorted(checked)} != {BLOCKS}"
        raise ValueError(msg)
    return out


# ---- 3(12) 党派別 議席配分表（比例代表）----------------------------


def parse_pr_seats(rows: Rows) -> list[dict[str, object]]:
    """→ [{block, party, seats}]（議席 0 の党は出ない）。順位が 1..S を漏れなく埋めることで検算。

    レイアウト: '<ブロック選挙区>' の後、党名の行（各党は 2 列: 順位 | 商）、'順位' 見出し行、
    除数 1..50 の行。党が多いと同じブロックが複数回続く。
    順位（当選順）の列は第 50・51 回では党名と同じ列（商はその右）、第 45〜49 回では党名の 1 列左
    （党名は商の列にある）。'順位' 見出し行で '順位' が党名の 1 列左にあれば後者と判定する。
    """
    seats: dict[tuple[str, str], int] = {}
    ranks: dict[str, set[int]] = {}
    block = ""
    party_cols: list[tuple[int, str]] = []
    rank_offset = 0
    for row in rows:
        marks = [_BLOCK_MARK.search(_text(c)) for c in row[:3]]
        mk = next((m for m in marks if m), None)
        if mk:
            block = _block_name(mk.group(1))
            party_cols = []
            rank_offset = 0
            continue
        if not block:
            continue
        texts = [_text(c) for c in row]
        if not party_cols:
            names = [(i, t) for i, t in enumerate(texts) if i >= 1 and t and t != "除数"]
            if names and all(_num(t) is None for _, t in names) and "順位" not in texts:
                party_cols = names
            continue
        if _num(_cell(row, 0)) is None:
            if "順位" in texts and all(
                _text(_cell(row, col - 1)) == "順位" for col, _ in party_cols if col >= 1
            ):
                rank_offset = -1
            continue  # 見出し（順位 行）など
        for col, party in party_cols:
            r = _num(_cell(row, col + rank_offset))
            if r is None:
                continue
            seats[(block, party)] = seats.get((block, party), 0) + 1
            ranks.setdefault(block, set()).add(int(r))
    out: list[dict[str, object]] = []
    for b in BLOCKS:
        got = ranks.get(b, set())
        n = len(got)
        if n == 0 or got != set(range(1, n + 1)):
            msg = f"pr_seats block {b}: ranks {sorted(got)} are not 1..S"
            raise ValueError(msg)
    for (b, p), s in seats.items():
        out.append({"block": b, "party": p, "seats": s})
    out.sort(key=lambda r: (BLOCKS.index(str(r["block"])), -int(str(r["seats"])), str(r["party"])))
    return out


# ---- 3(1) 届出政党等別 当選人数（小選挙区、比例代表）------------------

SMD_SEATS = 289
PR_SEATS = 176
_NOT_PARTY = {
    "本人･推薦届出",
    "本人・推薦届出",
    "小 計",
    "小計",
    "合 計",
    "合計",
    "区 分",
    "区分",
}
# 本人届出の候補者（無所属扱い）のうち政党等に所属する者の列。党名ではないが議席を持つ
_RENAME = {"政党等所属": "本人届出（政党等所属）"}


_SELF_NOMINATED = {"本人･推薦届出", "本人・推薦届出"}
# 本人届出シートの小見出しが空白のとき（第 47〜49 回）の列: 政党等所属 | 無所属 | 小計 | 合計
_SELF_DEFAULT_COLS: list[tuple[int, str]] = [(2, "本人届出（政党等所属）"), (5, "無所属")]


def parse_winners(
    sheets: Sequence[Rows], totals: tuple[int, int] = (SMD_SEATS, PR_SEATS)
) -> list[dict[str, object]]:
    """→ [{party, smd_seats, pr_seats}]（無所属を含む）。小選挙区・比例の法定定数 `totals` で検算。

    レイアウト: 党名の行（党名の 2 列右に '計' 列）の後、'小選挙区' 新/前/元/計、
    '比例代表' 新/前/元/計、
    '合計' 新/前/元/計 の 12 行。列 1 が '計' の行が順に 小選挙区・比例代表・合計 の計。
    党名が 2 行に割れる（第 49 回「ＮＨＫと裁判し／弁護士法７２条」）ときは連結する。
    本人届出シートの小見出し（政党等所属／無所属／小計）が空白のときは列位置で割り当てる。
    """
    seats: dict[str, dict[str, float]] = {}
    for rows in sheets:
        party_cols: list[tuple[int, str]] = []
        n_total_rows = 0
        self_sheet = False
        for row in rows:
            texts = [_text(c) for c in row]
            if _text(_cell(row, 1)) == "計" and party_cols:
                n_total_rows += 1
                tier = {1: "smd_seats", 2: "pr_seats"}.get(n_total_rows)
                if tier:
                    for col, party in party_cols:
                        v = _num(_cell(row, col + 2))
                        seats.setdefault(party, {"smd_seats": 0.0, "pr_seats": 0.0})
                        seats[party][tier] += v or 0.0
                if n_total_rows == 3:
                    party_cols = []
                    n_total_rows = 0
                continue
            if _text(_cell(row, 2)) in _SELF_NOMINATED:
                self_sheet = True
            if self_sheet and not party_cols and texts[2:5] == ["男", "女", "計"]:
                party_cols = list(_SELF_DEFAULT_COLS)
                n_total_rows = 0
                continue
            names = [
                (i, t.replace(" ", ""))
                for i, t in enumerate(texts)
                if i >= 2 and t and _num(t) is None and t not in ("男", "女", "計")
            ]
            names = [
                (i, _RENAME.get(t, t))
                for i, t in names
                if t.replace(" ", "") not in _NOT_PARTY and not t.startswith(("（", "("))  # 表題
            ]
            if names and all(_num(_cell(row, i + 2)) is None for i, _ in names):
                second = dict(names)
                if party_cols and n_total_rows == 0 and set(second) <= {c for c, _ in party_cols}:
                    # 党名の 2 行目（列が 1 行目の部分集合）: 同じ列の名前に連結する
                    party_cols = [(i, p + second.get(i, "")) for i, p in party_cols]
                else:
                    party_cols = names
                n_total_rows = 0
    out = [{"party": p, **v} for p, v in seats.items()]
    smd = sum(float(str(r["smd_seats"])) for r in out)
    pr = sum(float(str(r["pr_seats"])) for r in out)
    if (smd, pr) != (float(totals[0]), float(totals[1])):
        msg = f"winners: smd {smd} / pr {pr} != {totals[0]} / {totals[1]}"
        raise ValueError(msg)
    out.sort(
        key=lambda r: (-(float(str(r["smd_seats"])) + float(str(r["pr_seats"]))), str(r["party"]))
    )
    return out


def build_winners_mart(staged: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    out = [
        {
            "iso3": "JPN",
            "election": int(str(r["election"])),
            "election_date": r["election_date"],
            "party": r["party"],
            "smd_seats": r["smd_seats"],
            "pr_seats": r["pr_seats"],
            "total_seats": float(str(r["smd_seats"])) + float(str(r["pr_seats"])),
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(
        key=lambda r: (int(str(r["election"])), -float(str(r["total_seats"])), str(r["party"]))
    )
    return out


# ---- marts -------------------------------------------


def build_electorate_mart(
    staged: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """staged/soumu/electorate（election, tier, block, pref, …）→ 選挙×都道府県 1 行。"""
    by: dict[tuple[int, str], dict[str, object]] = {}
    for r in staged:
        key = (int(str(r["election"])), str(r["pref"]))
        row = by.setdefault(
            key,
            {
                "iso3": "JPN",
                "election": key[0],
                "election_date": r["election_date"],
                "pref": key[1],
                "block": None,
                "electorate_smd": None,
                "voters_smd": None,
                "electorate_pr": None,
                "voters_pr": None,
                "source": SOURCE,
            },
        )
        tier = str(r["tier"])
        row[f"electorate_{tier}"] = r["electorate"]
        row[f"voters_{tier}"] = r["voters"]
        if r.get("block"):
            row["block"] = r["block"]
    out = list(by.values())
    for row in out:
        if any(row[c] is None for c in ("block", "electorate_smd", "electorate_pr")):
            msg = f"electorate mart: incomplete row {row['election']} {row['pref']}"
            raise ValueError(msg)
    out.sort(key=lambda r: (int(str(r["election"])), BLOCKS.index(str(r["block"])), str(r["pref"])))
    return out


def build_pr_mart(
    votes: Sequence[Mapping[str, object]], seats: Sequence[Mapping[str, object]]
) -> list[dict[str, object]]:
    """→ 選挙×ブロック×政党: votes, share_pct, rank, seats（0 含む）, block_seats, block_votes。"""
    seat_of = {
        (int(str(r["election"])), str(r["block"]), str(r["party"])): int(str(r["seats"]))
        for r in seats
    }
    block_seats: dict[tuple[int, str], int] = {}
    for (e, b, _), s in seat_of.items():
        block_seats[(e, b)] = block_seats.get((e, b), 0) + s
    block_votes: dict[tuple[int, str], float] = {}
    for r in votes:
        k = (int(str(r["election"])), str(r["block"]))
        block_votes[k] = block_votes.get(k, 0.0) + float(str(r["votes"]))
    out: list[dict[str, object]] = []
    seen: set[tuple[int, str, str]] = set()
    for r in votes:
        e, b, p = int(str(r["election"])), str(r["block"]), str(r["party"])
        seen.add((e, b, p))
        out.append(
            {
                "iso3": "JPN",
                "election": e,
                "election_date": r["election_date"],
                "block": b,
                "party": p,
                "rank": r["rank"],
                "votes": r["votes"],
                "share_pct": r["share_pct"],
                "seats": seat_of.get((e, b, p), 0),
                "block_seats": block_seats.get((e, b)),
                "block_votes": block_votes[(e, b)],
                "source": SOURCE,
            }
        )
    missing = [k for k in seat_of if k not in seen]
    if missing:
        msg = f"pr mart: seat rows without a vote row: {missing[:3]}"
        raise ValueError(msg)
    for e, b in block_seats:
        if (e, b) not in block_votes:
            msg = f"pr mart: seats for {e} {b} but no votes"
            raise ValueError(msg)
    out.sort(
        key=lambda r: (int(str(r["election"])), BLOCKS.index(str(r["block"])), int(str(r["rank"])))
    )
    return out
