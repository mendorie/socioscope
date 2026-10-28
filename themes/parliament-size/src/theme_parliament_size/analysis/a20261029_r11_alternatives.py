"""R11: 代替案の数字 — 配分方式の変更だけで何が変わるか、1 人当たり資源の目標値、
委員会の担い手（H8・H9・H10）。

事後追加の仮説（design/themes/parliament-size.md「事後追加（2026-10-29、R11〜R13）」、
結果の計算前に固定）:
  H8  : 定数 176 のまま修正サンラグ式にすると、7 選挙の比例の Gallagher 指数が平均 1 pt 以上下がり、
        定数 10 以下のブロックの参入閾値が上がらなければ、代替案 1（定数維持＋方式変更）に整合。
  H9  : 議員 1 人当たり議会職員を OECD の上位 3 分の 1 の水準に上げる費用を、45 減の節約額
        （24.9〜30.9 億円）と比べる。記述。
  H10 : 衆院 17 常任委員会の委員定数の合計 ÷ 議員定数（兼任率）が 465 → 420 でどうなるか。記述。

決定的スクリプト。入力は data/marts/{jp_hr_pr_results, jp_hr_electorate, ipu_parliaments}.parquet と
src/theme_parliament_size/jp_committee_seats.csv。純粋ヘルパは tests/test_analysis_r11.py
で検証する。
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size import apportion
from theme_parliament_size.analysis.a20261027_r2_pr_blocks import (
    allocate,
    block_votes_of,
    md_row,
    national_shares,
    official_block_seats,
    party_totals,
)
from theme_parliament_size.analysis.a20261027_r5_roles import staff_per_member
from theme_parliament_size.analysis.a20261028_r6_pr_history import ELECTIONS, seat_shares

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
COMMITTEE_CSV = THEME_DIR / "src" / "theme_parliament_size" / "jp_committee_seats.csv"
JP_SEATS_LOWER, JP_SEATS_UPPER = 465, 248
CUT_SCENARIOS: dict[str, int] = {"現行 465": 465, "31 減 434": 434, "45 減 420": 420}
SAVING_45_100M_JPY = (24.9, 30.9)  # R3: 45 減で浮く直接経費（億円/年、下限〜上限）
# 職員 1 人当たりの年間人件費（給与＋手当＋事業主負担）の仮定。人事院「国家公務員給与等実態調査」の
# 行政職俸給表(一) 平均給与（年額換算 約 650 万円）に事業主負担・退職給付を上乗せした幅。
# 出典付きの取得値では
# なく仮定として扱い、下限〜上限で示す。
STAFF_COST_100M_JPY_PER_PERSON = (0.065, 0.100)  # 650 万〜1,000 万円


# ---- pure helpers -------------------------------------------------------------------------------


def gallagher_pr(shares: Mapping[str, float], seats: Mapping[str, int]) -> float:
    return apportion.gallagher(shares, seat_shares(seats))


def percentile(values: Sequence[float], q: float) -> float:
    """単純な分位点（線形補間）。q は 0〜1。"""
    xs = sorted(values)
    if not xs:
        return float("nan")
    pos = (len(xs) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def extra_staff(current_per_member: float, target_per_member: float, members: int) -> int:
    return max(0, round((target_per_member - current_per_member) * members))


def committee_load(total_committee_seats: int, members: int) -> float:
    """委員定数の合計 ÷ 議員定数 = 1 人当たりの常任委員会の兼任数。"""
    return total_committee_seats / members


def judge_h8(mean_drop: float, threshold_rises: Sequence[float]) -> str:
    if mean_drop >= 1.0 and all(r <= 0 for r in threshold_rises):
        return "整合"
    if mean_drop < 0.5:
        return "不支持"
    return "中間"


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Hiragino Sans", "Noto Sans CJK JP", "sans-serif"]
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    marts = args.data_dir / "marts"
    pr = pl.read_parquet(marts / "jp_hr_pr_results.parquet")
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")

    print(
        "# R11 代替案の数字: 配分方式の変更・1 人当たり資源・委員会の担い手（H8・H9・H10）"
        "（2026-10-29）"
    )
    print("\n事後追加の仮説（設計書 2026-10-29 節）。機械的試算と記述のみ。因果の主張はない。")

    # ---- H8 ----
    print(
        "\n## 表 1: 定数 176 のまま配分方式だけを変えたとき（7 選挙、ブロック定数は各選挙の法定）"
    )
    print(
        md_row(
            [
                "回（年）",
                "Gallagher 比例 ドント",
                "修正サンラグ",
                "差 pt",
                "小政党群の議席 ドント → 修正サンラグ",
                "四国の参入閾値 % ドント → 修正サンラグ",
            ]
        )
    )
    print("|" + "---|" * 6)
    drops: list[float] = []
    rises: list[float] = []
    dates = {int(r["election"]): str(r["election_date"]) for r in pr.iter_rows(named=True)}
    for e in ELECTIONS:
        bv = block_votes_of(pr, e)
        shares = national_shares(bv)
        seats = official_block_seats(pr, e)
        d = party_totals(allocate(bv, seats, "dhondt"))
        m = party_totals(allocate(bv, seats, "msl"))
        g_d, g_m = gallagher_pr(shares, d), gallagher_pr(shares, m)
        drops.append(g_d - g_m)
        small_d = sum(s for p, s in d.items() if shares[p] < 10.0)
        small_m = sum(s for p, s in m.items() if shares[p] < 10.0)
        thr_d = apportion.threshold_share(bv["四国"], seats["四国"], "__new__")
        # 修正サンラグの参入閾値: 新党の票 x が、他党の最後の議席の商を 1.4 で割った値を超えれば
        # 1 議席
        thr_m = _msl_threshold(bv["四国"], seats["四国"])
        rises.append(thr_m - thr_d)
        print(
            md_row(
                [
                    f"{e}（{dates[e][:4]}）",
                    f"{g_d:.2f}",
                    f"{g_m:.2f}",
                    f"{g_m - g_d:+.2f}",
                    f"{small_d} → {small_m}",
                    f"{thr_d:.1f} → {thr_m:.1f}",
                ]
            )
        )
    mean_drop = sum(drops) / len(drops)
    print(
        f"\n- Gallagher 指数（比例のみ）の低下: 平均 {mean_drop:.2f} pt"
        f"（範囲 {min(drops):.2f}〜{max(drops):.2f}）。"
        f"四国の参入閾値の変化: {min(rises):+.1f}〜{max(rises):+.1f} pt"
    )
    print(
        f"- **H8 判定: {judge_h8(mean_drop, rises)}**（平均 ≥ 1 pt "
        "低下かつ閾値が上がらなければ整合）"
    )

    # ---- H9 ----
    o = ipu.filter(pl.col("oecd_member"))
    spm: dict[str, float] = {}
    for iso3, grp in o.group_by("iso3"):
        s = staff_per_member(list(grp.iter_rows(named=True)))
        if s is not None:
            spm[str(iso3[0])] = s[0]
    jp = spm["JPN"]
    members = JP_SEATS_LOWER + JP_SEATS_UPPER
    targets = {
        "中央値": percentile(list(spm.values()), 0.5),
        "上位 3 分の 1 の境界": percentile(list(spm.values()), 2 / 3),
        "上位 4 分の 1 の境界": percentile(list(spm.values()), 0.75),
    }
    print("\n## 表 2: 議員 1 人当たり議会職員を引き上げる費用と 45 減の節約額（両院 713 人ベース）")
    print(
        md_row(
            [
                "目標",
                "職員 ÷ 議員",
                "必要な増員（人）",
                "年間費用（億円、650 万〜1,000 万円/人）",
                "45 減の節約額（億円）に対して",
            ]
        )
    )
    print("|---|---|---|---|---|")
    for lab, t in targets.items():
        n = extra_staff(jp, t, members)
        lo, hi = n * STAFF_COST_100M_JPY_PER_PERSON[0], n * STAFF_COST_100M_JPY_PER_PERSON[1]
        rel = (
            f"{lo / SAVING_45_100M_JPY[1]:.1f}〜{hi / SAVING_45_100M_JPY[0]:.1f} 倍"
            if n
            else "0（既に上回る）"
        )
        print(md_row([lab, f"{t:.2f}", n, f"{lo:.1f}〜{hi:.1f}", rel]))
    print(
        f"- 日本の現状 {jp:.2f} 人/議員（衆参事務局 ÷ 713）。OECD {len(spm)} か国の中央値 "
        f"{targets['中央値']:.2f}、"
        f"上位 3 分の 1 の境界 {targets['上位 3 分の 1 の境界']:.2f}"
    )
    print(
        "- H9 は記述。職員単価は仮定（本文参照）で、公設秘書の増員（議員 1 人 3 → 4 人なら 713 "
        "人、約 1,000 万円/人で約 70 億円）も同じ比較ができる。"
    )

    # ---- H10 ----
    with COMMITTEE_CSV.open(encoding="utf-8") as f:
        committees = list(csv.DictReader(f))
    total = sum(int(r["seats"]) for r in committees)
    print("\n## 表 3: 衆院 常任委員会の委員定数（衆議院規則 第 92 条）と兼任率")
    print(md_row(["定数", "委員定数の合計", "兼任率（委員定数 ÷ 議員定数）"]))
    print("|---|---|---|")
    for lab, n in CUT_SCENARIOS.items():
        print(md_row([lab, total, f"{committee_load(total, n):.2f}"]))
    print(
        f"- 17 委員会の委員定数の合計は {total}（予算 50、厚労・国交 40、議運 25、懲罰 20 ほか）。"
        f"465 で 1 人 {committee_load(total, 465):.2f} 委員会、"
        f"420 で {committee_load(total, 420):.2f}。"
        "委員定数を据え置けば兼任が 1 割増える。"
        "委員定数を比例して減らせば委員会ごとの審査の担い手が減る。H10 は記述。"
    )


def _msl_threshold(votes: Mapping[str, float], seats: int, first_divisor: float = 1.4) -> float:
    """修正サンラグ式で新党が 1 議席を取る最小得票率（他党の票を固定）。
    他党の商（v/1.4, v/3, v/5, …）の seats 番目を x/1.4 が超えればよい。"""
    quotients: list[float] = []
    for v in votes.values():
        quotients.append(v / first_divisor)
        quotients += [v / (2 * k + 1) for k in range(1, seats)]
    quotients.sort(reverse=True)
    if len(quotients) < seats:
        return 0.0
    need = quotients[seats - 1] * first_divisor
    total_others = sum(votes.values())
    return 100.0 * need / (total_others + need)


if __name__ == "__main__":
    main()
