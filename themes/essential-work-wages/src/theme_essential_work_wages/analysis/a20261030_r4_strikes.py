"""R4: 倫理的人質。第三者被害がスト能力を奪い、交渉力を下げているか（H4）。

事前登録（design/themes/essential-work-wages.md、2026-10-29）:
  H4  : T=1 の産業（医療・福祉、教育）の雇用者 1,000 人当たり争議件数・労働損失日数は、
        同程度の人手不足にある T=0 の産業（運輸、建設、製造）の 2 分の 1 以下。日本の
        労働争議統計で比が 0.5 以下、かつ ILOSTAT で OECD 10 か国以上のうち 7 か国以上で
        同じ向きなら整合。比が 1.0 前後なら不支持。
  H4b : 医療従事者のストが合法で頻度が高い国（英国・韓国・フランス）では看護師の賃金比が
        日本より高い（記述）。

事後の具体化（結果を見る前に固定、2026-10-30）:
  - 日本: 労働争議統計調査（2012〜2024 年）の産業大分類 P 医療，福祉・O 教育，学習支援業 を T=1、
    H 運輸業，郵便業・D 建設業・E 製造業 を T=0 とし、雇用者数は労働組合基礎調査の産業別雇用者数
    （労働力調査由来）で割る。件数（総争議）と労働損失日数（半日以上の同盟罷業等）の 13 年合計の比。
    「同程度の人手不足」は R3 の求人倍率で介護（3.5）と建設・運転（2〜5）が近いことで担保する。
  - 国際: ILOSTAT の産業別 争議件数（STR_TSTR_ECO_NB_A）・労働損失日数（STR_DAYS_ECO_NB_A）を
    ISIC Q 人間の健康・社会事業＋P 教育（T=1）と H 運輸・F 建設・C 製造（T=0）で 2015〜2024 年合計、
    雇用者数の代わりに Eurostat/ILO の雇用がここには無いため、各国で「T=1 の合計 ÷ T=0 の合計」を
    件数と日数で出し、OECD 加盟国に限って「T=1 の方が少ない（比 < 1）」国の数を数える。雇用規模で
    割っていないので粗い（P＋Q の雇用は多くの国で C＋F＋H と同程度かやや多い。
    向きの判定にのみ使う）。
  - H4b: OECD 医療職報酬（RINF 病院看護師、FCTR_WG_A_SAL_A 平均賃金比、被用者）の最新年で
    日本と英国・韓国・フランス・OECD 中央値を並べる。
  - 補助（探索）: 労働組合基礎調査の産業別 推定組織率と争議率の関係（組織率が同程度でも T=1 の
    争議が少ないか）。

決定的スクリプト。入力は data/marts/{jp_labour_disputes_by_industry, jp_union_density_by_industry,
ilo_strikes_by_industry, oecd_health_remuneration}.parquet。図は reports/figures/r4_*.png。
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import polars as pl

from theme_essential_work_wages.analysis.common import (
    FIGURES,
    GRID,
    INK,
    MARTS,
    SERIES,
    as_float,
    md_table,
)

LOG = logging.getLogger("r4")
JP_T1 = ("P", "O")
JP_T0 = ("H", "D", "E")
JP_LABEL = {
    "P": "医療，福祉",
    "O": "教育，学習支援",
    "H": "運輸，郵便",
    "D": "建設",
    "E": "製造",
    "I": "卸売，小売",
    "G": "情報通信",
    "J": "金融，保険",
    "M": "宿泊，飲食",
    "F": "電気・ガス・水道",
    "S": "公務",
}
ISIC_T1 = ("Q", "P")
ISIC_T0 = ("H", "F", "C")
OECD = {
    "AUS",
    "AUT",
    "BEL",
    "CAN",
    "CHL",
    "COL",
    "CRI",
    "CZE",
    "DNK",
    "EST",
    "FIN",
    "FRA",
    "DEU",
    "GRC",
    "HUN",
    "ISL",
    "IRL",
    "ISR",
    "ITA",
    "JPN",
    "KOR",
    "LVA",
    "LTU",
    "LUX",
    "MEX",
    "NLD",
    "NZL",
    "NOR",
    "POL",
    "PRT",
    "SVK",
    "SVN",
    "ESP",
    "SWE",
    "CHE",
    "TUR",
    "GBR",
    "USA",
}


def jp_rates(disp: pl.DataFrame, unions: pl.DataFrame) -> pl.DataFrame:
    """Per industry: 13-year totals of disputes and days lost, mean employees, rates per 1,000."""
    u = (
        unions.filter(pl.col("employees").is_not_null())
        .group_by("industry_code")
        .agg(
            pl.col("employees").mean().alias("employees"),
            pl.col("union_density_pct").mean().alias("density"),
        )
    )
    d = disp.group_by("industry_code").agg(
        pl.col("disputes_total").sum().alias("disputes"),
        pl.col("disputes_with_action").sum().alias("disputes_action"),
        pl.col("days_lost").sum().alias("days_lost"),
        pl.col("participants").sum().alias("participants"),
        pl.len().alias("n_years"),
    )
    out = d.join(u, on="industry_code", how="inner").with_columns(
        (pl.col("disputes") / pl.col("employees") * 1000 / pl.col("n_years")).alias(
            "disputes_per_1000_yr"
        ),
        (pl.col("days_lost") / pl.col("employees") * 1000 / pl.col("n_years")).alias(
            "days_per_1000_yr"
        ),
        (pl.col("participants") / pl.col("employees") * 1000 / pl.col("n_years")).alias(
            "participants_per_1000_yr"
        ),
        (pl.col("days_lost") / pl.col("participants")).alias("days_per_participant"),
        (pl.col("days_lost") / pl.col("disputes_action")).alias("days_per_action_dispute"),
        (pl.col("disputes_action") / pl.col("disputes")).alias("action_share"),
    )
    return out.sort("industry_code")


def ratio_of_groups(
    df: pl.DataFrame, col: str, t1: tuple[str, ...], t0: tuple[str, ...], key: str = "industry_code"
) -> float:
    a = df.filter(pl.col(key).is_in(list(t1)))
    b = df.filter(pl.col(key).is_in(list(t0)))
    num = float(a[col].sum()) / float(a["employees"].sum())
    den = float(b[col].sum()) / float(b["employees"].sum())
    return num / den if den > 0 else math.nan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marts", type=Path, default=MARTS)
    parser.add_argument("--figures", type=Path, default=FIGURES)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    plt.rcParams["font.family"] = ["IPAGothic", "IPAexGothic", "Noto Sans CJK JP", "DejaVu Sans"]

    disp = pl.read_parquet(args.marts / "jp_labour_disputes_by_industry.parquet")
    unions = pl.read_parquet(args.marts / "jp_union_density_by_industry.parquet")
    ilo = pl.read_parquet(args.marts / "ilo_strikes_by_industry.parquet")
    remun = pl.read_parquet(args.marts / "oecd_health_remuneration.parquet")
    nama = pl.read_parquet(args.marts / "nama_industry_value_added_employment.parquet")

    print("# R4 倫理的人質: 第三者被害がスト能力を奪っているか（H4）")
    years = sorted(disp["year"].unique().to_list())
    print(
        f"日本の争議統計: {years[0]}〜{years[-1]}（{len(years)} 年）、"
        "雇用者数は労働組合基礎調査の産業別雇用者数の平均"
    )
    jp = jp_rates(disp.filter(pl.col("industry_code") != "ALL"), unions)
    rows: list[list[object]] = []
    for r in jp.filter(
        pl.col("industry_code").is_in(list(JP_T1 + JP_T0 + ("I", "G", "J", "M", "F", "S")))
    ).iter_rows(named=True):
        tag = (
            "T=1" if r["industry_code"] in JP_T1 else ("T=0" if r["industry_code"] in JP_T0 else "")
        )
        rows.append(
            [
                f"{r['industry_code']} {JP_LABEL.get(r['industry_code'], '')}",
                tag,
                int(r["disputes"]),
                int(r["days_lost"] or 0),
                f"{r['employees'] / 1e4:,.0f} 万人",
                f"{r['disputes_per_1000_yr']:.4f}",
                f"{r['days_per_1000_yr']:.3f}",
                f"{r['participants_per_1000_yr']:.3f}",
                f"{r['density']:.1f}%",
            ]
        )
    print("\n### 日本: 産業別の争議（13 年合計）と雇用者 1,000 人・年当たり")
    print(
        md_table(
            [
                "産業",
                "群",
                "総争議 件数",
                "労働損失日数",
                "雇用者（平均）",
                "件数/1000 人・年",
                "損失日数/1000 人・年",
                "参加人員/1000 人・年",
                "組織率",
            ],
            rows,
        )
    )
    r_disp = ratio_of_groups(jp, "disputes", JP_T1, JP_T0)
    r_days = ratio_of_groups(jp, "days_lost", JP_T1, JP_T0)
    r_part = ratio_of_groups(jp, "participants", JP_T1, JP_T0)
    r_disp_p = ratio_of_groups(jp, "disputes", ("P",), JP_T0)
    r_days_p = ratio_of_groups(jp, "days_lost", ("P",), JP_T0)
    print(
        f"\nT=1（P＋O）÷ T=0（H＋D＋E）の雇用者当たり比: 件数 {r_disp:.2f}、"
        f"労働損失日数 {r_days:.2f}、参加人員 {r_part:.2f}。"
        f" 医療・福祉のみ: 件数 {r_disp_p:.2f}、損失日数 {r_days_p:.2f}"
    )
    v_jp_disp = (
        "満たす" if r_disp <= 0.5 else ("不支持（1.0 前後以上）" if r_disp >= 0.8 else "満たさない")
    )
    v_jp_days = (
        "満たす" if r_days <= 0.5 else ("不支持（1.0 前後以上）" if r_days >= 0.8 else "満たさない")
    )
    print(f"日本の判定（件数・損失日数とも ≤ 0.5 で整合）: 件数 {v_jp_disp}、損失日数 {v_jp_days}")
    print("\n### 日本: 争議の「長さ」の代理（13 年合計。参加人員は争議行為を伴う争議のもの）")
    rows = []
    for r in jp.filter(pl.col("industry_code").is_in(list(JP_T1 + JP_T0 + ("I", "G")))).iter_rows(
        named=True
    ):
        rows.append(
            [
                f"{r['industry_code']} {JP_LABEL.get(r['industry_code'], '')}",
                "T=1"
                if r["industry_code"] in JP_T1
                else ("T=0" if r["industry_code"] in JP_T0 else ""),
                f"{r['action_share']:.2f}" if r["action_share"] is not None else "–",
                f"{r['days_per_action_dispute']:.1f}"
                if r["days_per_action_dispute"] is not None
                else "–",
                f"{r['days_per_participant']:.2f}"
                if r["days_per_participant"] is not None
                else "–",
            ]
        )
    print(
        md_table(
            [
                "産業",
                "群",
                "争議行為を伴う割合",
                "損失日数 ÷ 争議行為を伴う争議（日/件）",
                "損失日数 ÷ 参加人員（日/人）",
            ],
            rows,
        )
    )
    print(
        "注: 損失日数は半日以上の同盟罷業・作業所閉鎖のみ。"
        "「損失日数 ÷ 参加人員」は参加者 1 人当たりの"
        "平均ストライキ日数の近似（半日未満の行為は分子に入らない）。"
    )

    # international
    print("\n### 国際（ILOSTAT、2015〜2024 年合計、雇用規模で割らない粗い比）")
    i = ilo.filter((pl.col("year") >= 2015) & pl.col("industry").is_in(list(ISIC_T1 + ISIC_T0)))
    agg = i.group_by("iso3", "metric", "industry").agg(pl.col("value").sum().alias("v"))
    rows = []
    counts = {"strikes_n": [0, 0], "days_not_worked": [0, 0]}
    per_country: dict[str, dict[str, float]] = {}
    for iso in sorted(agg["iso3"].unique().to_list()):
        if iso not in OECD:
            continue
        cells: list[object] = [iso]
        for metric in ("strikes_n", "days_not_worked"):
            sub = agg.filter((pl.col("iso3") == iso) & (pl.col("metric") == metric))
            t1 = float(sub.filter(pl.col("industry").is_in(list(ISIC_T1)))["v"].sum())
            t0 = float(sub.filter(pl.col("industry").is_in(list(ISIC_T0)))["v"].sum())
            n_ind = sub.height
            if n_ind < 4 or t0 <= 0:
                cells.append("–")
                continue
            ratio = t1 / t0
            per_country.setdefault(iso, {})[metric] = ratio
            counts[metric][0] += int(ratio < 1)
            counts[metric][1] += 1
            cells.append(f"{ratio:.2f}")
        rows.append(cells)
    print(md_table(["国", "件数 T=1÷T=0", "損失日数 T=1÷T=0"], rows))
    for metric, (less, n) in counts.items():
        print(f"{metric}: T=1 の方が少ない国 {less}/{n}（基準: 10 か国以上のうち 7 か国以上）")
    # employment-normalised version where Eurostat employment by section is available (EU/EFTA)
    print(
        "\n### 国際（雇用で割った比。Eurostat 国民経済計算の産業別就業者がある国のみ、"
        "2015〜2023 年平均）"
    )
    emp = (
        nama.filter(
            (pl.col("year") >= 2015)
            & pl.col("nace_r2").is_in(list(ISIC_T1 + ISIC_T0))
            & pl.col("iso3").is_not_null()
        )
        .group_by("iso3", "nace_r2")
        .agg(pl.col("employment_ths").mean().alias("emp"))
    )
    rows = []
    norm_counts = {"strikes_n": [0, 0], "days_not_worked": [0, 0]}
    for iso in sorted(set(emp["iso3"].to_list()) & set(per_country)):
        if iso not in OECD:
            continue
        e = emp.filter(pl.col("iso3") == iso)
        e1 = float(e.filter(pl.col("nace_r2").is_in(list(ISIC_T1)))["emp"].sum())
        e0 = float(e.filter(pl.col("nace_r2").is_in(list(ISIC_T0)))["emp"].sum())
        if e1 <= 0 or e0 <= 0:
            continue
        cells = [iso, f"{e1 / e0:.2f}"]
        for metric in ("strikes_n", "days_not_worked"):
            raw = per_country[iso].get(metric)
            if raw is None:
                cells.append("–")
                continue
            normed = raw / (e1 / e0)
            norm_counts[metric][0] += int(normed < 1)
            norm_counts[metric][1] += 1
            cells.append(f"{normed:.2f}")
        rows.append(cells)
    print(
        md_table(
            ["国", "雇用 T=1÷T=0", "件数（雇用当たり）T=1÷T=0", "損失日数（雇用当たり）T=1÷T=0"],
            rows,
        )
    )
    for metric, (less, n) in norm_counts.items():
        print(f"{metric}（雇用当たり）: T=1 の方が少ない国 {less}/{n}")
    jp_i = per_country.get("JPN", {})
    print(
        f"日本（ILOSTAT）: 件数比 {jp_i.get('strikes_n', math.nan):.2f}、"
        f"損失日数比 {jp_i.get('days_not_worked', math.nan):.2f}"
    )
    intl_ok = norm_counts["days_not_worked"][1] >= 10 and norm_counts["days_not_worked"][0] >= 7
    intl_ok_n = norm_counts["strikes_n"][1] >= 10 and norm_counts["strikes_n"][0] >= 7
    both_jp = r_disp <= 0.5 and r_days <= 0.5
    if both_jp and intl_ok and intl_ok_n:
        overall = "整合"
    elif r_disp >= 0.8 and r_days >= 0.8:
        overall = "不支持"
    else:
        overall = "中間（指標で向きが割れる）"
    print(
        f"\n**H4 総合判定: {overall}**（日本 件数比 {r_disp:.2f}・日数比 {r_days:.2f}、"
        f"国際（雇用当たり）件数 {norm_counts['strikes_n'][0]}/{norm_counts['strikes_n'][1]}"
        f"・日数 {norm_counts['days_not_worked'][0]}/{norm_counts['days_not_worked'][1]}、"
        f"雇用で割らない参考値 件数 {counts['strikes_n'][0]}/{counts['strikes_n'][1]}"
        f"・日数 {counts['days_not_worked'][0]}/{counts['days_not_worked'][1]}）"
    )

    # H4b nurses remuneration ratio
    print("\n### H4b: 病院看護師の報酬 ÷ 平均賃金（OECD、被用者、男女計、最新年）")
    nurses = remun.filter(
        (pl.col("health_prof") == "RINF")
        & (pl.col("unit") == "FCTR_WG_A_SAL_A")
        & (pl.col("worker_status") == "ICSE93_1")
        & (pl.col("sex") == "_T")
    )
    latest = (
        nurses.sort("year")
        .group_by("iso3")
        .agg(pl.col("year").last(), pl.col("value").last())
        .sort(["value", "iso3"], descending=[True, False])
    )
    med = as_float(latest["value"].median())
    rows = [[r["iso3"], int(r["year"]), f"{r['value']:.2f}"] for r in latest.iter_rows(named=True)]
    print(md_table(["国", "年", "看護師 ÷ 平均賃金"], rows))
    for iso in ("JPN", "GBR", "KOR", "FRA", "USA", "DEU"):
        v = latest.filter(pl.col("iso3") == iso)
        print(
            f"{iso}: {f'{v["value"][0]:.2f}（{int(v["year"][0])}）' if v.height else '–'}", end="; "
        )
    print(f"OECD 中央値 {med:.2f}（n={latest.height}）")

    # exploratory: union density vs dispute rate
    print("\n### 補助（探索）: 組織率と争議率（日本、産業別 13 年平均）")
    rows = [
        [
            f"{r['industry_code']} {JP_LABEL.get(r['industry_code'], r['industry_code'])}",
            f"{r['density']:.1f}",
            f"{r['disputes_per_1000_yr']:.4f}",
            f"{r['days_per_1000_yr']:.3f}",
        ]
        for r in jp.filter(pl.col("density").is_not_null())
        .sort("density", descending=True)
        .iter_rows(named=True)
    ]
    print(md_table(["産業", "組織率 %", "件数/1000 人・年", "損失日数/1000 人・年"], rows))

    # figure
    args.figures.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    ax = axes[0]
    for r in jp.iter_rows(named=True):
        c = (
            SERIES[0]
            if r["industry_code"] in JP_T1
            else (SERIES[1] if r["industry_code"] in JP_T0 else "#8a8a8a")
        )
        ax.scatter(
            r["disputes_per_1000_yr"], r["days_per_1000_yr"], color=c, s=40, edgecolor="none"
        )
        ax.annotate(
            r["industry_code"],
            (r["disputes_per_1000_yr"], r["days_per_1000_yr"]),
            fontsize=8,
            color=INK,
            xytext=(3, 3),
            textcoords="offset points",
        )
    ax.set_xlabel("総争議 件数 / 雇用者 1,000 人・年", color=INK)
    ax.set_ylabel("労働損失日数 / 雇用者 1,000 人・年", color=INK)
    ax.set_title(
        "日本 2012–2024: 青 = T=1（P 医療福祉, O 教育）、橙 = T=0（H 運輸, D 建設, E 製造）",
        color=INK,
        fontsize=9,
    )
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    ax = axes[1]
    vals = sorted(
        ((iso, m["days_not_worked"]) for iso, m in per_country.items() if "days_not_worked" in m),
        key=lambda t: t[1],
    )
    ax.barh(
        [v[0] for v in vals],
        [v[1] for v in vals],
        color=[SERIES[0] if v[0] == "JPN" else "#8a8a8a" for v in vals],
    )
    ax.axvline(1.0, color=INK, linestyle="--", linewidth=1)
    ax.set_xscale("log")
    ax.set_xlabel("労働損失日数 T=1（Q+P）÷ T=0（H+F+C）、2015–2024 合計（対数）", color=INK)
    ax.set_title("ILOSTAT: 1 より左 = 医療・教育の方がストが少ない", color=INK, fontsize=9)
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    for a in axes:
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(args.figures / "r4_h4_strikes.png", dpi=150)
    plt.close(fig)
    print("\nfigures: r4_h4_strikes.png")


if __name__ == "__main__":
    main()
