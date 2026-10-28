"""R17（番外編）: R16 を深める 3 つの問い（H16a〜c、ユーザー提起）。

事後追加の仮説（design/themes/parliament-size.md「事後追加（2026-10-30、番外編 R17）」、
結果の計算前に固定）:
  H16a: (i) 比例代表制 vs 多数代表・混合制 の一般政府支出比の中央値差 ≥ 3 pt で
        Persson–Tabellini を「再現」。(ii) 比例代表制の層内で 立方根補正比 × 支出比 の |ρ| < 0.2
        なら「選挙制度の経路」に整合、ρ ≥ 0.3 で不支持、間は中間。
  H16b: 議員 1 人当たりの一般政府支出（USD PPP）で日本が 38 か国中 上位 5 位以内なら整合。
        補助: 議会予算 ÷ 政府予算（IPU）× 支出比 の ρ、× 議員 1 人当たり支出 の ρ。
  H16c: 立方根補正比 × 立法府への信頼（最新年）の ρ。|ρ| < 0.2 で「無関係」に整合、ρ ≤ −0.3 で
        「小さい議会ほど信頼される」に整合、ρ ≥ +0.3 で逆。補助: 素の比率、議員 1 人当たり支出、
        「議会が政府に責任を問う」との ρ。

決定的スクリプト。入力は data/marts/{oecd_gov_finance, oecd_gov_trust, ipu_parliaments}.parquet。
純粋ヘルパは tests/test_analysis_r17.py で検証する。
"""

from __future__ import annotations

import argparse
import logging
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

import polars as pl

from theme_parliament_size.analysis.a20261027_r1_ratio import cube_ratio, per_million
from theme_parliament_size.analysis.a20261027_r2_pr_blocks import md_row
from theme_parliament_size.analysis.a20261027_r3_cost import rank_of
from theme_parliament_size.analysis.a20261029_r16_government_size import (
    p_value,
    rho_of,
    window_mean,
)

THEME_DIR = Path(__file__).resolve().parents[3]
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#8e6cc0", "#5d5d5d"]
INK = "#333333"
MUTED = "#8a8a8a"
GRID = "#e6e6e6"
JP = "JPN"
PR = "proportional_representation"
SYSTEM_JA = {
    PR: "比例代表制",
    "mixed_system": "混合制",
    "plurality_majority": "多数代表制",
}


# ---- pure helpers -------------------------------------------------------------------------------


def median(values: Sequence[float]) -> float:
    xs = sorted(values)
    n = len(xs)
    if n == 0:
        return math.nan
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def spend_per_member(pcap_usd: float, population_thousands: float, seats: float) -> float:
    """1 人当たり政府支出（USD PPP）× 人口 ÷ 下院定数 = 議員 1 人当たりの政府支出（USD PPP）。"""
    return pcap_usd * population_thousands * 1000.0 / seats


def latest(rows: Sequence[Mapping[str, object]]) -> tuple[int, float] | None:
    """[{year, value}] → 最新年の (年, 値)。"""
    cands = [(int(str(r["year"])), float(str(r["value"]))) for r in rows]
    return max(cands) if cands else None


def judge_h16a_i(diff_pt: float) -> str:
    if math.isnan(diff_pt):
        return "判定不能"
    return "再現" if diff_pt >= 3.0 else "再現せず"


def judge_h16a_ii(rho: float) -> str:
    if math.isnan(rho):
        return "判定不能"
    if abs(rho) < 0.2:
        return "整合"
    if rho >= 0.3:
        return "不支持"
    return "中間"


def judge_h16b(rank_desc: int) -> str:
    return "整合" if rank_desc <= 5 else "不支持"


def judge_h16c(rho: float) -> str:
    if math.isnan(rho):
        return "判定不能"
    if abs(rho) < 0.2:
        return "整合（無関係）"
    if rho <= -0.3:
        return "整合（小さい議会ほど信頼）"
    if rho >= 0.3:
        return "逆（大きい議会ほど信頼）"
    return "中間"


# ---- figures -------------------------------------------------------------------------------------


def _style(ax: object) -> None:
    import matplotlib.axes

    assert isinstance(ax, matplotlib.axes.Axes)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_system(
    cube: Mapping[str, float],
    ge: Mapping[str, float],
    system: Mapping[str, str],
    path: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    colors = {PR: SERIES[0], "mixed_system": SERIES[2], "plurality_majority": SERIES[3]}
    for sysname, ja in SYSTEM_JA.items():
        ks = sorted(k for k in cube if k in ge and system.get(k) == sysname)
        ax.scatter(
            [cube[k] for k in ks], [ge[k] for k in ks], s=24, color=colors[sysname], label=ja
        )
    for k in sorted(k for k in cube if k in ge):
        ax.annotate(
            k,
            (cube[k], ge[k]),
            fontsize=6.5,
            color=SERIES[1] if k == JP else INK,
            xytext=(3, 2),
            textcoords="offset points",
        )
    ax.set_xlabel("下院定数 ÷ 人口の立方根（1.0 = 立方根法則どおり）", fontsize=8, color=INK)
    ax.set_ylabel("一般政府支出 ÷ GDP（%、2019〜2023 年平均）", fontsize=8, color=INK)
    ax.set_title(
        "選挙制度別に見た議会の大きさと政府の大きさ（OECD 下院）",
        fontsize=10,
        color=INK,
        loc="left",
    )
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    fig.text(
        0.01,
        0.005,
        "出典: OECD Government at a Glance 2025、IPU Parline（CC BY-NC-SA 4.0）",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_per_member(spm: Mapping[str, float], names: Mapping[str, str], path: Path) -> None:
    import matplotlib.pyplot as plt

    keys = sorted(spm, key=lambda k: spm[k])
    fig, ax = plt.subplots(figsize=(7.2, 7.4))
    ax.barh(
        range(len(keys)),
        [spm[k] / 1e9 for k in keys],
        color=[SERIES[1] if k == JP else "#7f9cc4" for k in keys],
        height=0.7,
    )
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels([names[k] for k in keys], fontsize=7)
    for i, k in enumerate(keys):
        ax.text(spm[k] / 1e9 + 0.05, i, f"{spm[k] / 1e9:.1f}", va="center", fontsize=6.5, color=INK)
    ax.set_xlabel(
        "議員 1 人当たりの一般政府支出（10 億 USD、購買力平価、2019〜2023 年平均）", fontsize=8
    )
    ax.set_title("議員 1 人が監視する政府支出（OECD 下院）", fontsize=10, color=INK, loc="left")
    _style(ax)
    fig.text(
        0.01,
        0.005,
        "出典: OECD Government at a Glance 2025（GE_POP）、IPU Parline（CC BY-NC-SA 4.0）",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_trust(cube: Mapping[str, float], trust: Mapping[str, float], path: Path) -> None:
    import matplotlib.pyplot as plt

    keys = sorted(k for k in cube if k in trust)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.scatter(
        [cube[k] for k in keys],
        [trust[k] for k in keys],
        s=22,
        color=[SERIES[1] if k == JP else "#7f9cc4" for k in keys],
    )
    for k in keys:
        ax.annotate(
            k,
            (cube[k], trust[k]),
            fontsize=6.5,
            color=INK,
            xytext=(3, 2),
            textcoords="offset points",
        )
    ax.set_xlabel("下院定数 ÷ 人口の立方根（1.0 = 立方根法則どおり）", fontsize=8, color=INK)
    ax.set_ylabel("立法府を信頼する人の割合（%、高い＋やや高い）", fontsize=8, color=INK)
    ax.set_title("議会の大きさと立法府への信頼（OECD）", fontsize=10, color=INK, loc="left")
    _style(ax)
    fig.text(
        0.01,
        0.005,
        f"出典: OECD Trust Survey 2023（{len(keys)} か国、最新年）、IPU Parline（CC BY-NC-SA 4.0）",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---- main ----------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=THEME_DIR.parents[1] / "data")
    ap.add_argument("--fig-dir", type=Path, default=THEME_DIR / "reports" / "figures")
    args = ap.parse_args(argv)
    import matplotlib

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    fonts = ["Hiragino Sans", "Noto Sans CJK JP", "IPAPGothic", "IPAGothic", "sans-serif"]
    matplotlib.rcParams["font.family"] = fonts
    args.fig_dir.mkdir(parents=True, exist_ok=True)
    marts = args.data_dir / "marts"
    ipu = pl.read_parquet(marts / "ipu_parliaments.parquet")
    gov = pl.read_parquet(marts / "oecd_gov_finance.parquet")
    trust_df = pl.read_parquet(marts / "oecd_gov_trust.parquet")
    lower = ipu.filter(pl.col("oecd_member") & (pl.col("chamber_type") == "lower"))
    names = {str(r["iso3"]): str(r["country"]) for r in lower.iter_rows(named=True)}
    seats = {str(r["iso3"]): float(r["statutory_seats"]) for r in lower.iter_rows(named=True)}
    pop_k = {str(r["iso3"]): float(r["population_thousands"]) for r in lower.iter_rows(named=True)}
    system = {str(r["iso3"]): str(r["electoral_system"]) for r in lower.iter_rows(named=True)}
    pbudget = {
        str(r["iso3"]): float(r["parliament_budget_pct_gov"])
        for r in lower.iter_rows(named=True)
        if r["parliament_budget_pct_gov"] is not None
    }
    per_m = {k: per_million(seats[k], pop_k[k]) for k in seats}
    cube = {k: cube_ratio(seats[k], pop_k[k]) for k in seats}

    def series(df: pl.DataFrame, metric: str) -> dict[str, list[dict[str, object]]]:
        out: dict[str, list[dict[str, object]]] = {}
        for r in df.filter(pl.col("metric") == metric).iter_rows(named=True):
            out.setdefault(str(r["iso3"]), []).append(r)
        return out

    ge = {
        k: v
        for k in seats
        if (v := window_mean(series(gov, "gov_expenditure_pct_gdp").get(k, []))) is not None
    }
    pcap_rows = series(gov, "gov_expenditure_pcap_usd_ppp")
    pcap = {k: v for k in seats if (v := window_mean(pcap_rows.get(k, []))) is not None}
    spm = {k: spend_per_member(pcap[k], pop_k[k], seats[k]) for k in pcap}
    tr: dict[str, tuple[int, float]] = {}
    for k, rows in series(trust_df, "trust_legislature_pct").items():
        tl = latest(rows)
        if tl is not None and k in seats:
            tr[k] = tl
    trust = {k: v[1] for k, v in tr.items()}
    # TRUST_PVGA は PT_RESP と宣言されているが値は 0〜1 の割合（最大 0.6）なので % に直す
    pvga = {
        k: pv[1] * 100.0
        for k, rows in series(trust_df, "parliament_holds_gov_accountable_pct").items()
        if (pv := latest(rows)) is not None and k in seats
    }
    keys = sorted(k for k in seats if k in ge)

    print(
        "# R17（番外編）選挙制度・監視対象・信頼: R16 を深める 3 つの問い（H16a〜c）（2026-10-30）"
    )
    print("\n事後追加の仮説（設計書 2026-10-30 節）。順位相関と順位の記述のみ。因果の主張はない。")

    # ---- H16a
    pr_keys = [k for k in keys if system[k] == PR]
    non_pr = [k for k in keys if system[k] != PR]
    med_pr, med_non = median([ge[k] for k in pr_keys]), median([ge[k] for k in non_pr])
    diff = med_pr - med_non
    rho_pr = rho_of(cube, ge, pr_keys)
    rho_non = rho_of(cube, ge, non_pr)
    rho_all = rho_of(cube, ge, keys)
    print("\n## H16a: 選挙制度が「議会の大きさ × 政府の大きさ」を説明するか")
    print(
        md_row(
            ["選挙制度", "n", "支出比 中央値 %", "立方根補正比 中央値", "補正比 × 支出比 ρ", "p"]
        )
    )
    print("|" + "---|" * 6)
    for label, ks, rho in (
        ("比例代表制", pr_keys, rho_pr),
        ("多数代表・混合制", non_pr, rho_non),
        ("全体", keys, rho_all),
    ):
        print(
            md_row(
                [
                    label,
                    len(ks),
                    f"{median([ge[k] for k in ks]):.1f}",
                    f"{median([cube[k] for k in ks]):.2f}",
                    f"{rho:+.2f}",
                    f"{p_value(rho, len(ks)):.3f}",
                ]
            )
        )
    for sysname, ja in SYSTEM_JA.items():
        ks = [k for k in keys if system[k] == sysname]
        print(
            f"- {ja}（{len(ks)}）: " + "、".join(names[k] for k in sorted(ks, key=lambda k: -ge[k]))
        )
    print(
        f"\n- **H16a (i)**: 比例代表制の支出比中央値 {med_pr:.1f}% − "
        f"多数代表・混合制 {med_non:.1f}% = {diff:+.1f} pt → **{judge_h16a_i(diff)}**"
        "（≥ 3 pt で Persson–Tabellini を再現）"
    )
    print(
        f"- **H16a (ii)**: 比例代表制の層内で 補正比 × 支出比 ρ = {rho_pr:+.2f}"
        f"（n = {len(pr_keys)}） → **{judge_h16a_ii(rho_pr)}**"
        "（|ρ| < 0.2 で「選挙制度の経路」に整合、≥ 0.3 で不支持）"
    )
    mean_pr = sum(ge[k] for k in pr_keys) / len(pr_keys)
    mean_non = sum(ge[k] for k in non_pr) / len(non_pr)
    print(
        f"- 参考: 多数代表・混合制の層内 ρ = {rho_non:+.2f}（n = {len(non_pr)}）。日本は混合制。"
        f"平均値では比例代表制 {mean_pr:.1f}%、多数代表・混合制 {mean_non:.1f}%"
        f"（差 {mean_pr - mean_non:+.1f} pt）"
    )

    # ---- H16b
    print("\n## H16b: 議員 1 人が監視する政府支出")
    print(
        md_row(
            [
                "国",
                "議員 1 人当たり支出（10 億 USD PPP）",
                "1 人当たり支出（USD PPP）",
                "下院定数",
                "議会予算 ÷ 政府予算 %",
            ]
        )
    )
    print("|" + "---|" * 5)
    for k in sorted(spm, key=lambda k: -spm[k]):
        mark = "**" if k == JP else ""
        print(
            md_row(
                [
                    f"{mark}{names[k]}{mark}",
                    f"{spm[k] / 1e9:.2f}",
                    f"{pcap[k]:,.0f}",
                    f"{seats[k]:.0f}",
                    f"{pbudget[k]:.3f}" if k in pbudget else "–",
                ]
            )
        )
    rank_desc = len(spm) + 1 - rank_of(spm, JP)
    med_spm = median(list(spm.values()))
    rho_pb_ge = rho_of(pbudget, ge, keys)
    rho_pb_spm = rho_of(pbudget, spm, keys)
    n_pb = len([k for k in keys if k in pbudget])
    print(
        f"\n- 日本の議員 1 人当たり政府支出は {spm[JP] / 1e9:.2f} 十億 USD（PPP）で "
        f"{len(spm)} か国中 大きい方から {rank_desc} 位（中央値 {med_spm / 1e9:.2f}、"
        f"中央値の {spm[JP] / med_spm:.1f} 倍） → **H16b {judge_h16b(rank_desc)}**"
        "（5 位以内で整合）"
    )
    print(
        f"- 補助: 議会予算 ÷ 政府予算 × 支出比 ρ = {rho_pb_ge:+.2f}、× 議員 1 人当たり支出 ρ = "
        f"{rho_pb_spm:+.2f}（n = {n_pb}）。日本の議会予算 ÷ 政府予算は {pbudget[JP]:.3f}% で "
        f"{n_pb} か国中 少ない方から "
        f"{rank_of({k: v for k, v in pbudget.items() if k in keys}, JP)} 位"
    )

    # ---- H16c
    print("\n## H16c: 議会の大きさと立法府への信頼")
    print(
        md_row(
            [
                "国",
                "立法府への信頼 %",
                "年",
                "議会が政府に責任を問う %",
                "立方根補正比",
                "下院 /100 万人",
            ]
        )
    )
    print("|" + "---|" * 6)
    for k in sorted(trust, key=lambda k: -trust[k]):
        mark = "**" if k == JP else ""
        print(
            md_row(
                [
                    f"{mark}{names[k]}{mark}",
                    f"{trust[k]:.1f}",
                    tr[k][0],
                    f"{pvga[k]:.1f}" if k in pvga else "–",
                    f"{cube[k]:.2f}",
                    f"{per_m[k]:.2f}",
                ]
            )
        )
    tkeys = sorted(k for k in trust if k in cube)
    rho_c = rho_of(cube, trust, tkeys)
    rho_raw = rho_of(per_m, trust, tkeys)
    rho_spm = rho_of(spm, trust, tkeys)
    rho_pv = rho_of(cube, pvga, tkeys)
    rho_ge_tr = rho_of(ge, trust, tkeys)
    print(
        f"\n- **H16c**: 補正比 × 立法府への信頼 ρ = {rho_c:+.2f}（n = {len(tkeys)}、"
        f"p = {p_value(rho_c, len(tkeys)):.3f}） → **{judge_h16c(rho_c)}**"
    )
    print(
        f"- 補助: 素の人口当たり議員数 × 信頼 ρ = {rho_raw:+.2f}、議員 1 人当たり支出 × 信頼 ρ = "
        f"{rho_spm:+.2f}、補正比 × 「議会が政府に責任を問う」ρ = {rho_pv:+.2f}"
        f"（n = {len([k for k in tkeys if k in pvga])}）、支出比 × 信頼 ρ = {rho_ge_tr:+.2f}"
    )
    t23 = {k: v[1] for k, v in tr.items() if v[0] == 2023 and k in cube}
    k23 = sorted(t23)
    print(
        f"- 頑健性: 2023 年のみ（n = {len(k23)}）で 補正比 × 信頼 ρ = "
        f"{rho_of(cube, t23, k23):+.2f}。日本の定数を 420 にすると議員 1 人当たり支出は "
        f"{spm[JP] * seats[JP] / 420 / 1e9:.2f} 十億 USD"
    )
    print(
        f"- 日本の立法府への信頼は {trust[JP]:.1f}%（{tr[JP][0]} 年）で {len(trust)} か国中 "
        f"低い方から {rank_of(trust, JP)} 位（中央値 {median(list(trust.values())):.1f}%）"
    )
    fig_system(cube, ge, system, args.fig_dir / "r17_system_cube_vs_spending.png")
    fig_per_member(spm, names, args.fig_dir / "r17_spending_per_member.png")
    fig_trust(cube, trust, args.fig_dir / "r17_trust_vs_cube.png")
    print(
        f"\n図: {args.fig_dir}/r17_system_cube_vs_spending.png, r17_spending_per_member.png, "
        "r17_trust_vs_cube.png"
    )


if __name__ == "__main__":
    main()
