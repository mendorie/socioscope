"""R15: 少数政党を保護することは守るべき原則か（H14a〜c）。

入口としての価値・阻止条項・泡沫政党の票。事後追加の仮説（design/themes/parliament-size.md
「事後追加（2026-10-29 夜、R15）」、結果の計算前に固定）:
  H14a: 第 45〜51 回で比例 1〜3 議席で初めて議席を得た政党のうち、2 回後までに衆院総議席 5 以上に
        成長した割合。3 分の 1 以上なら「入口として機能」に整合、0 なら不支持。
  H14b: OECD の比例・混合制の下院で法定阻止条項 3% 以上の国が過半数なら「2〜3% 未満を外すのは普通」
        に整合。日本の実効閾値（R2）と比べる。
  H14c: 各選挙で比例 1〜2 議席にとどまった政党の得票率・票数（記述）。

決定的スクリプト。入力は data/marts/{jp_hr_pr_results, jp_hr_seats_by_party}.parquet と
src/theme_parliament_size/intl_thresholds.csv。純粋ヘルパは tests/test_analysis_r15.py で検証する。
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row

THEME_DIR = Path(__file__).resolve().parents[3]
THRESHOLD_CSV = THEME_DIR / "src" / "theme_parliament_size" / "intl_thresholds.csv"
ELECTIONS: tuple[int, ...] = (45, 46, 47, 48, 49, 50, 51)
ENTRY_MAX_PR_SEATS = 3
GROWN_MIN_TOTAL = 5
MICRO_MAX_PR_SEATS = 2


# ---- pure helpers -------------------------------------------------------------------------------


def entries(
    pr_seats: Mapping[str, Mapping[int, int]], total_seats: Mapping[str, Mapping[int, float]]
) -> list[dict[str, object]]:
    """政党 → {選挙: 比例議席} と {選挙: 総議席} から、比例 1〜3 議席で初当選した政党と
    その後を返す。

    「初当選」= その選挙で比例議席 > 0 かつ、それ以前の選挙（第 45 回以降）で比例議席も総議席も 0。
    第 45 回で既に議席がある政党は初当選と判定できないので除く。
    """
    out: list[dict[str, object]] = []
    for party, seats in pr_seats.items():
        tot = total_seats.get(party, {})
        for i, e in enumerate(ELECTIONS):
            s = seats.get(e, 0)
            if s <= 0:
                continue
            before = [x for x in ELECTIONS[:i] if seats.get(x, 0) > 0 or tot.get(x, 0) > 0]
            if i == 0 or before:
                break  # 第 45 回に既にいる、または以前に議席がある → 初当選ではない
            if s > ENTRY_MAX_PR_SEATS:
                break
            later = ELECTIONS[i + 1 : i + 3]
            peak = max((float(tot.get(x, 0)) for x in later), default=0.0)
            out.append(
                {
                    "party": party,
                    "entry": e,
                    "entry_pr_seats": s,
                    "entry_total": tot.get(e, 0),
                    "later": {x: tot.get(x, 0) for x in later},
                    "grown": peak >= GROWN_MIN_TOTAL,
                    "observed": len(later) > 0,
                }
            )
            break
    return sorted(out, key=lambda r: (int(str(r["entry"])), str(r["party"])))


def judge_h14a(grown: int, observed: int) -> str:
    if observed == 0:
        return "判定不能"
    if grown == 0:
        return "不支持"
    return "整合" if grown / observed >= 1 / 3 else "中間"


def judge_h14b(rows: Sequence[Mapping[str, object]]) -> tuple[str, int, int]:
    """OECD の比例・混合制で法定閾値 ≥ 3% の国が過半数なら整合。(判定, 該当国数, 対象国数)。"""
    n = len(rows)
    k = sum(1 for r in rows if float(str(r["legal_threshold_pct"])) >= 3.0)
    return ("整合" if k > n / 2 else "不支持"), k, n


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    args = ap.parse_args(argv)
    marts = args.data_dir / "marts"
    pr = pl.read_parquet(marts / "jp_hr_pr_results.parquet")
    win = pl.read_parquet(marts / "jp_hr_seats_by_party.parquet")
    dates = {int(r["election"]): str(r["election_date"])[:4] for r in pr.iter_rows(named=True)}

    nat = pr.group_by("election", "party").agg(pl.col("votes").sum(), pl.col("seats").sum())
    nat = nat.with_columns(
        (pl.col("votes") / pl.col("votes").sum().over("election") * 100).alias("share")
    )
    pr_seats: dict[str, dict[int, int]] = {}
    shares: dict[tuple[int, str], tuple[float, float]] = {}
    for r in nat.iter_rows(named=True):
        pr_seats.setdefault(str(r["party"]), {})[int(r["election"])] = int(r["seats"])
        shares[(int(r["election"]), str(r["party"]))] = (float(r["share"]), float(r["votes"]))
    total: dict[str, dict[int, float]] = {}
    for r in win.iter_rows(named=True):
        total.setdefault(str(r["party"]), {})[int(r["election"])] = float(r["total_seats"])

    print("# R15 少数政党を保護することは守るべき原則か（H14a〜c）（2026-10-29）")
    print("\n事後追加の仮説（設計書 2026-10-29 夜 節）。記述のみ。「価値」の判断はしない。")

    # ---- H14a ----
    ent = entries(pr_seats, total)
    print("\n## 表 1: 比例 1〜3 議席で初めて議席を得た政党と、その後 2 回の衆院総議席")
    print(md_row(["政党", "初当選", "比例議席", "総議席", "次回", "次々回", "5 議席以上に成長"]))
    print("|" + "---|" * 7)
    for r in ent:
        later = r["later"]
        assert isinstance(later, dict)
        ls = [f"{int(v)}" for v in later.values()] + ["–"] * (2 - len(later))
        print(
            md_row(
                [
                    r["party"],
                    f"{r['entry']}（{dates[int(str(r['entry']))]}）",
                    r["entry_pr_seats"],
                    int(float(str(r["entry_total"]))),
                    ls[0],
                    ls[1],
                    "はい" if r["grown"] else ("未観測" if not r["observed"] else "いいえ"),
                ]
            )
        )
    observed = [r for r in ent if r["observed"]]
    grown = [r for r in observed if r["grown"]]
    print(
        f"\n- 1〜3 議席で入った政党 {len(ent)}（うち次回以降を観測できる {len(observed)}）、"
        f"2 回後までに 5 議席以上に成長 {len(grown)}（{'、'.join(str(r['party']) for r in grown)}）"
    )
    print(f"- **H14a 判定: {judge_h14a(len(grown), len(observed))}**（3 分の 1 以上で整合）")

    # ---- H14b ----
    with THRESHOLD_CSV.open(encoding="utf-8") as f:
        th = list(csv.DictReader(f))
    verdict, k, n = judge_h14b(th)
    print("\n## 表 2: OECD の比例代表・混合制の下院の法定阻止条項（手入力、各国選挙法・ACE）")
    print(md_row(["国", "制度", "法定閾値 %", "備考"]))
    print("|---|---|---|---|")
    for r in sorted(th, key=lambda r: (-float(r["legal_threshold_pct"]), r["iso3"])):
        print(md_row([r["country"], r["system"], r["legal_threshold_pct"], r["note"]]))
    none = [r["iso3"] for r in th if float(r["legal_threshold_pct"]) == 0]
    print(
        f"\n- 対象 {n} か国中、法定閾値 3% 以上は {k} か国。"
        f"閾値なしは {len(none)} か国（{'、'.join(none)}）"
    )
    print(
        "- 日本は法定閾値なしだが、11 ブロック制の実効閾値は 6.6〜9.5%（四国 12.3%、R2）で、"
        "ドイツの 5% やイタリアの 3% より高い。"
        "全国 2〜3% の政党が議席を得るのは、特定ブロックで票が集まる場合に限られる"
    )
    print(f"- **H14b 判定: {verdict}**（3% 以上が過半数なら整合）")

    # ---- H14c ----
    print("\n## 表 3: 比例 1〜2 議席にとどまった政党の得票（各選挙）")
    print(md_row(["回（年）", "政党（比例議席）", "全国得票率 %", "票数（万）"]))
    print("|---|---|---|---|")
    for e in ELECTIONS:
        micro = [
            (p, s)
            for p, seats in pr_seats.items()
            if 0 < (s := seats.get(e, 0)) <= MICRO_MAX_PR_SEATS
        ]
        if not micro:
            print(md_row([f"{e}（{dates[e]}）", "なし", "–", "–"]))
            continue
        tot_share = sum(shares[(e, p)][0] for p, _ in micro)
        tot_votes = sum(shares[(e, p)][1] for p, _ in micro)
        print(
            md_row(
                [
                    f"{e}（{dates[e]}）",
                    "、".join(f"{p}（{s}）" for p, s in micro),
                    f"{tot_share:.1f}",
                    f"{tot_votes / 1e4:,.0f}",
                ]
            )
        )
    print("- H14c は記述。これらの政党の票は、45 減ドント（R2）では議席に結びつかなくなる。")


if __name__ == "__main__":
    main()
