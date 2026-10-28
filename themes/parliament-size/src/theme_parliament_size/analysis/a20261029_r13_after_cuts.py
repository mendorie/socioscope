"""R13: 定数を大幅に減らした議会はその後どう働いたか — イタリア 2022・ハンガリー 2014（H7）。

事後追加の仮説 H7（design/themes/parliament-size.md「事後追加（2026-10-29、R11〜R13）」、
結果の計算前に固定）:
  削減後 2 会期（年）の 成立法律数／年 と 本会議日数／年 がどちらも削減前 2 会期より 10% 以上減れば
  「減らすと働きが落ちる」に整合、どちらも減っていなければ不支持、片方なら中間。議員 1 人当たりの
  委員会兼任数は記述。

データ: イタリア下院 open data（年別の成立法律数・本会議回数、marts/it_*）、IPU Parline
の本会議日数・
質問主意書・常任委員会数の履歴（staged/ipu/chamber_attributes）。ハンガリーは法律数が取れない
（国会サイトが CAPTCHA）ので IPU の指標のみ。選挙年（イタリア 2022、ハンガリー 2014）
は前後から除く。
純粋ヘルパは tests/test_analysis_r13.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row

THEME_DIR = Path(__file__).resolve().parents[3]
CASES: dict[str, dict[str, object]] = {
    "ITA": {
        "chamber": "IT-LC01",
        "cut_year": 2022,
        "before": (630, 2019, 2021),
        "after": (400, 2023, 2025),
    },
    "HUN": {
        "chamber": "HU-LC01",
        "cut_year": 2014,
        "before": (386, 2011, 2013),
        "after": (199, 2015, 2017),
    },
}


# ---- pure helpers -------------------------------------------------------------------------------


def mean_in(series: Mapping[int, float], years: tuple[int, int]) -> float | None:
    vals = [v for y, v in series.items() if years[0] <= y <= years[1]]
    return sum(vals) / len(vals) if vals else None


def pct_change(before: float | None, after: float | None) -> float | None:
    if before is None or after is None or before == 0:
        return None
    return 100.0 * (after - before) / before


def judge_h7(law_change: float | None, days_change: float | None) -> str:
    """両方 −10% 以下で整合、両方それより上で不支持、片方なら中間、片方欠損なら判定不能。"""
    if law_change is None or days_change is None:
        return "判定不能"
    a, b = law_change <= -10.0, days_change <= -10.0
    if a and b:
        return "整合"
    if not a and not b:
        return "不支持"
    return "中間"


def yearly_from_ipu(rows: Sequence[Mapping[str, object]], attribute: str) -> dict[int, float]:
    """staged/ipu/chamber_attributes の 1 議院分 → {年: 値}（date_from の年、同年は後勝ち）。"""
    out: dict[int, float] = {}
    for r in rows:
        if str(r["attribute"]) != attribute or r["value_num"] is None:
            continue
        y = str(r["date_from"] or "")[:4]
        if y.isdigit():
            out[int(y)] = float(str(r["value_num"]))
    return out


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    args = ap.parse_args(argv)
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    marts = args.data_dir / "marts"
    laws = pl.read_parquet(marts / "it_laws_by_year.parquet")
    sits = pl.read_parquet(marts / "it_sittings_by_year.parquet")
    attrs = pl.read_parquet(args.data_dir / "staged" / "ipu" / "chamber_attributes.parquet")

    print("# R13 定数を大幅に減らした議会はその後どう働いたか（H7）（2026-10-29）")
    print("\n事後追加の仮説（設計書 2026-10-29 節）。削減前後の記述のみ。因果の主張はない。")
    verdicts: dict[str, str] = {}
    for iso, c in CASES.items():
        rows = list(attrs.filter(pl.col("entity_id") == str(c["chamber"])).iter_rows(named=True))
        days = yearly_from_ipu(rows, "num_days_parl_plen")
        questions = yearly_from_ipu(rows, "num_written_question_ask")
        staff = yearly_from_ipu(rows, "permanent_staff_number")
        committees = yearly_from_ipu(rows, "num_cham_perm_committees")
        law_series = (
            {int(r["year"]): float(r["value"]) for r in laws.iter_rows(named=True)}
            if iso == "ITA"
            else {}
        )
        sit_series = (
            {int(r["year"]): float(r["value"]) for r in sits.iter_rows(named=True)}
            if iso == "ITA"
            else {}
        )
        b_tuple = c["before"]
        a_tuple = c["after"]
        assert isinstance(b_tuple, tuple) and isinstance(a_tuple, tuple)
        b_seats, before = int(b_tuple[0]), (int(b_tuple[1]), int(b_tuple[2]))
        a_seats, after = int(a_tuple[0]), (int(a_tuple[1]), int(a_tuple[2]))
        print(
            f"\n## {iso}: 定数 {b_seats} → {a_seats}（{c['cut_year']} 年選挙から）。前 "
            f"{before[0]}–{before[1]} 年、後 {after[0]}–{after[1]} 年の年平均"
        )
        print(md_row(["指標", "削減前", "削減後", "変化 %", "出典"]))
        print("|---|---|---|---|---|")
        metrics: list[tuple[str, dict[int, float], str]] = [
            ("成立法律数／年（公布年）", law_series, "dati.camera.it"),
            ("本会議回数／年（下院 open data）", sit_series, "dati.camera.it"),
            ("本会議日数／年（IPU）", days, "IPU Parline"),
            ("質問主意書／年", questions, "IPU Parline"),
            ("議会職員数", staff, "IPU Parline"),
        ]
        changes: dict[str, float | None] = {}
        for lab, series, src in metrics:
            mb, ma = mean_in(series, before), mean_in(series, after)
            ch = pct_change(mb, ma)
            changes[lab] = ch
            print(
                md_row(
                    [
                        lab,
                        f"{mb:.0f}" if mb is not None else "–",
                        f"{ma:.0f}" if ma is not None else "–",
                        f"{ch:+.0f}" if ch is not None else "–",
                        src,
                    ]
                )
            )
        law_ch = changes["成立法律数／年（公布年）"]
        days_ch = changes["本会議日数／年（IPU）"]
        if days_ch is None:
            days_ch = changes["本会議回数／年（下院 open data）"]
        v = judge_h7(law_ch, days_ch)
        verdicts[iso] = v
        # 議員 1 人当たりの委員会兼任（平均定員は不明なので、委員会数 ÷ 100 議員で代理）
        cm = sorted(committees.items())
        if cm:
            per100_b = cm[0][1] / b_seats * 100
            per100_a = cm[-1][1] / a_seats * 100
            print(
                f"- 常任委員会数の記録: {cm}。議員 100 人当たりの委員会数は "
                f"{b_seats} 人で {per100_b:.1f}、{a_seats} 人で {per100_a:.1f}"
            )
        else:
            print("- 常任委員会数の記録なし")
        if staff:
            sb, sa = mean_in(staff, before), mean_in(staff, after)
            if sb and sa:
                print(f"- 議員 1 人当たり職員: {sb / b_seats:.2f} → {sa / a_seats:.2f}")
        print(f"- **H7 判定（{iso}）: {v}**")
    print(
        "\n- ハンガリーは成立法律数が取れず、本会議日数のみで「片方欠損」のため判定不能。"
        "質問主意書と職員数は記述。"
    )
    print(f"- **H7 総合: イタリア {verdicts['ITA']}、ハンガリー {verdicts['HUN']}**")


if __name__ == "__main__":
    main()
