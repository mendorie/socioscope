"""財務省 令和 7 年度 一般会計歳入歳出予算（衆参修正後）PDF: 歳出の所管別内訳（国会 など）。

Pure transforms only (no I/O)。PDF は AES 暗号化されているが空パスワードで開ける（pypdf）。
2 ページ目「所管別内訳」は数値行（前年度当初 A、令和 7 年度修正後 B、増減、伸率）が所管名より先に
並ぶので、数値行を `ORGANS` の順に割り当て、所管名が本文に現れること・主要行の合計が「合計」行と
一致することで検算する（fail-closed）。

License: 財務省ホームページは政府標準利用規約（第 2.0 版、CC BY 4.0 互換）。出典表示で利用可。
"""

from __future__ import annotations

import io
import re

SOURCE = "mof_budget"
LICENSE = (
    "政府標準利用規約（第2.0版、CC BY 4.0 互換）。出典: 財務省「令和7年度一般会計歳入歳出予算"
    "（衆議院修正＋参議院修正後）」（https://www.mof.go.jp/policy/budget/budger_workflow/budget/fy2025/）"
)
URL = "https://www.mof.go.jp/policy/budget/budger_workflow/budget/fy2025/0003.pdf"
RAW_NAME = "fy2025_general_account_revised.pdf"
MAGIC = b"%PDF"
FY_PREV, FY = 2024, 2025
UNIT = "100m_jpy"  # 億円

# 2 ページ目の数値行の順（2026-10-27 に確認）。内閣府の内訳（内閣本府等・警察庁）は内閣府に
# 含まれるので
# 合計の検算から除く。予備費は 2 行（物価高騰対策等予備費、予備費）。
ORGANS: tuple[tuple[str, bool], ...] = (
    ("皇室費", True),
    ("国会", True),
    ("裁判所", True),
    ("会計検査院", True),
    ("内閣", True),
    ("内閣府", True),
    ("内閣府_内閣本府等", False),
    ("内閣府_警察庁", False),
    ("デジタル庁", True),
    ("総務省", True),
    ("法務省", True),
    ("外務省", True),
    ("財務省", True),
    ("文部科学省", True),
    ("厚生労働省", True),
    ("農林水産省", True),
    ("経済産業省", True),
    ("国土交通省", True),
    ("環境省", True),
    ("防衛省", True),
    ("予備費_物価高騰対策等", True),
    ("予備費", True),
)
_MUST_MENTION = ("所管別内訳", "国会", "皇室費", "裁判所", "防衛省", "予備費")
_NUM_ROW = re.compile(r"^\s*([\d,]+|－)\s+([\d,]+|－)\s+(△\s*)?([\d,]+|－)")
_FOOTER = re.compile(r"^\s*－\s*\d+\s*－\s*$")
_TOTAL_ROW = re.compile(r"^\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+[\d.]+\s*合")


def pdf_pages(payload: bytes) -> list[str]:
    """ページごとのテキスト。暗号化 PDF は空パスワードで復号。PDF でなければ ValueError。"""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(payload))
        if reader.is_encrypted:
            reader.decrypt("")
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        msg = "payload is not a readable PDF"
        raise ValueError(msg) from e


def _amount(s: str) -> float | None:
    s = s.strip()
    if s == "－":
        return None
    return float(s.replace(",", ""))


def parse(pages: list[str]) -> list[dict[str, object]]:
    """→ [{organ, in_total, fy, amount}]（億円、FY2024 当初と FY2025 修正後の 2 行ずつ）＋ 合計。"""
    text = next((p for p in pages if "所管別内訳" in p), None)
    if text is None:
        msg = "page with 所管別内訳 not found"
        raise ValueError(msg)
    for word in _MUST_MENTION:
        if word not in text:
            msg = f"所管別内訳 page lacks the label {word!r}"
            raise ValueError(msg)
    rows: list[tuple[float | None, float | None]] = []
    total: tuple[float, float] | None = None
    for line in text.split("\n"):
        if line.lstrip().startswith("(") or _FOOTER.match(line):
            continue  # 「うち」内訳（括弧付き）、ページ番号「－ 2 －」
        mt = _TOTAL_ROW.match(line)
        if mt:
            total = (float(mt.group(1).replace(",", "")), float(mt.group(2).replace(",", "")))
            continue
        m = _NUM_ROW.match(line)
        if m:
            rows.append((_amount(m.group(1)), _amount(m.group(2))))
    if len(rows) != len(ORGANS) or total is None:
        msg = f"expected {len(ORGANS)} organ rows and a total row, got {len(rows)}"
        raise ValueError(msg)
    out: list[dict[str, object]] = []
    sums = [0.0, 0.0]
    for (organ, in_total), (a, b) in zip(ORGANS, rows, strict=True):
        for fy, amount, label in ((FY_PREV, a, "initial"), (FY, b, "revised")):
            out.append(
                {"organ": organ, "in_total": in_total, "fy": fy, "stage": label, "amount": amount}
            )
        if in_total:
            sums[0] += a or 0.0
            sums[1] += b or 0.0
    for s, t, fy in ((sums[0], total[0], FY_PREV), (sums[1], total[1], FY)):
        if abs(s - t) > 1.0:
            msg = f"FY{fy}: organ rows sum {s} != total {t}"
            raise ValueError(msg)
    for fy, amount, label in ((FY_PREV, total[0], "initial"), (FY, total[1], "revised")):
        out.append({"organ": "合計", "in_total": False, "fy": fy, "stage": label, "amount": amount})
    return out


def build_mart(staged: list[dict[str, object]]) -> list[dict[str, object]]:
    out = [
        {
            "iso3": "JPN",
            "fy": r["fy"],
            "stage": r["stage"],
            "organ": r["organ"],
            "in_total": r["in_total"],
            "amount_100m_jpy": r["amount"],
            "source": SOURCE,
        }
        for r in staged
    ]
    out.sort(key=lambda r: (int(str(r["fy"])), str(r["organ"])))
    if not any(r["organ"] == "国会" for r in out):
        msg = "mart lacks the 国会 row"
        raise ValueError(msg)
    return out
