"""eiren（日本映画製作者連盟）の「興行収入10億円以上番組」PDF から
年別の興収集中度データセットを組み立てる。

使い方:
    python build_boxoffice_dataset.py <rows.json>

rows.json は PDF から pypdf で抽出・パースした行（year -> [{title, oku, dist, section}]）。
PDF の取得元: https://www.eiren.org/toukei/img/eiren_kosyu/data_<YEAR>.pdf（2000–2024）、
            https://www.eiren.org/toukei/img/eiren_kosyu/data_current_2025.pdf（2025）
全体興収・邦画/洋画: https://www.eiren.org/toukei/data.html（百万円）
数値は一切推定しない。eiren に無い年は欠損のまま出力する。
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "data"

# eiren 過去データ一覧表（data.html, 2026-10-24 取得）: 興収 合計 / 邦画 / 洋画（百万円）
TOTALS_MILLION_YEN = {
    2000: (170862, 54334, 116528),
    2001: (200154, 78144, 122010),
    2002: (196780, 53294, 143486),
    2003: (203259, 67125, 136134),
    2004: (210914, 79054, 131860),
    2005: (198160, 81780, 116380),
    2006: (202934, 107944, 94990),
    2007: (198443, 94645, 103798),
    2008: (194836, 115859, 78977),
    2009: (206035, 117309, 88726),
    2010: (220737, 118217, 102521),
    2011: (181197, 99531, 81666),
    2012: (195190, 128181, 67009),
    2013: (194237, 117685, 76552),
    2014: (207034, 120715, 86319),
    2015: (217119, 120367, 96752),
    2016: (235508, 148608, 86900),
    2017: (228572, 125483, 103089),
    2018: (222511, 122029, 100482),
    2019: (261180, 142192, 118988),
    2020: (143285, 109276, 34009),
    2021: (161893, 128339, 33554),
    2022: (213111, 146579, 66532),
    2023: (221482, 148181, 73301),
    2024: (206983, 155800, 51183),
    2025: (274452, 207569, 66883),
}
TOTALS_URL = "https://www.eiren.org/toukei/data.html"


def ranking_url(year: int) -> str:
    if year == 2025:
        return "https://www.eiren.org/toukei/img/eiren_kosyu/data_current_2025.pdf"
    return f"https://www.eiren.org/toukei/img/eiren_kosyu/data_{year}.pdf"


# 子ども・ファミリー向けキャラクター／アニメ IP（狭義）。判定はタイトルの部分一致。
KIDS_FAMILY_KEYWORDS = [
    "ポケットモンスター",
    "ﾎﾟｹｯﾄﾄﾞﾝｽﾀｰ",
    "ﾎﾟｹｯﾄﾓﾝｽﾀｰ",
    "ドラえもん",
    "名探偵コナン",
    "クレヨンしんちゃん",
    "妖怪ウォッチ",
    "デジモン",
    "プリキュア",
    "ぷりきゅあ",
    "ＯＮＥ ＰＩＥＣＥ",
    "ONE PIECE",
    "ワンピース",
    # スタジオジブリ
    "千と千尋",
    "猫の恩返し",
    "ハウルの動く城",
    "ゲド戦記",
    "崖の上のポニョ",
    "借りぐらしのアリエッティ",
    "コクリコ坂",
    "風立ちぬ",
    "君たちはどう生きるか",
    # ディズニー／ピクサー／イルミネーション等の長編アニメ
    "トイ・ストーリー",
    "ターザン",
    "ダイナソー",
    "モンスターズ・インク",
    "モンスターズ・ユニバーシティ",
    "ファインディング・ニモ",
    "ファインディング・ドリー",
    "Ｍｒ．インクレディブル",
    "インクレディブル・ファミリー",
    "カールじいさん",
    "ＷＡＬＬ・Ｅ",
    "アナと雪の女王",
    "ベイマックス",
    "ミニオン",
    "怪盗グルー",
    "インサイド・ヘッド",
    "ズートピア",
    "ペット",
    "モアナ",
    "ＳＩＮＧ／シング",
    "リメンバー・ミー",
    "スーパーマリオ",
    "ウィッシュ",
    "シュレック",
    "アイス・エイジ",
    "カーズ",
    "塔の上のラプンツェル",
    # 細田守のファミリー向けアニメ
    "おおかみこども",
    "バケモノの子",
    "竜とそばかすの姫",
]
# すべてのアニメ作品（広義: 上記 + 少年・青年向けアニメ）
ANIME_EXTRA_KEYWORDS = [
    "鬼滅の刃",
    "⿁滅の刃",
    "呪術廻戦",
    "ＳＰＹ×ＦＡＭＩＬＹ",
    "ハイキュー",
    "チェンソーマン",
    "ヒーローアカデミア",
    "ガンダム",
    "Gundam",
    "エヴァンゲリ",
    "ヱヴァンゲリヲン",
    "ＳＬＡＭ ＤＵＮＫ",
    "君の名は。",
    "天気の子",
    "すずめの戸締まり",
    "ヴァイオレット・エヴァーガーデン",
    "Fate/stay night",
    "ルパン三世",
    "はたらく細胞",  # はたらく細胞は実写なので除外（下で明示）
]
NOT_ANIME = {"はたらく細胞", "ルパン三世ｖｓ名探偵コナン"}  # 実写／既に狭義で数える


def is_kids_family(title: str) -> bool:
    return any(k in title for k in KIDS_FAMILY_KEYWORDS)


def is_anime(title: str) -> bool:
    if is_kids_family(title):
        return True
    if any(n in title for n in NOT_ANIME):
        return False
    return any(k in title for k in ANIME_EXTRA_KEYWORDS)


def clean_title(t: str) -> str:
    t = re.sub(r"^\d\d年\d+月\d+日[（(].[)）]\s*", "", t)  # 2000–2010 形式の公開日
    t = re.sub(r"\s*(\d{1,3}\.\d)\1+\s*$", "", t)  # 2012 形式の重複数値（同じ値の繰り返しのみ）
    return re.sub(r"\s+", " ", t).strip()


def main(rows_json: str) -> None:
    with open(rows_json, encoding="utf-8") as f:
        rows_by_year = {int(k): v for k, v in json.load(f).items()}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    films_path = OUT_DIR / "boxoffice_films_over_10oku.csv"
    with films_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "year",
                "rank_overall",
                "section",
                "title",
                "oku",
                "distributor",
                "kids_family_ip",
                "anime",
                "source_url",
            ]
        )
        for year in sorted(rows_by_year):
            rs = sorted(rows_by_year[year], key=lambda r: -r["oku"])
            for i, r in enumerate(rs, 1):
                t = clean_title(r["title"])
                w.writerow(
                    [
                        year,
                        i,
                        r["section"],
                        t,
                        r["oku"],
                        r["dist"],
                        int(is_kids_family(t)),
                        int(is_anime(t)),
                        ranking_url(year),
                    ]
                )

    conc_path = OUT_DIR / "boxoffice_concentration.csv"
    cols = [
        "year",
        "total_oku",
        "domestic_oku",
        "foreign_oku",
        "n_over_100",
        "top1_title",
        "top1_oku",
        "top3_sum",
        "top3_share",
        "top10_sum",
        "top10_share",
        "top10_domestic_sum",
        "top10_domestic_share",
        "n_kids_family_ip_top10",
        "n_anime_top10",
        "n_films_over_10",
        "sum_over_10",
        "top3_titles",
        "source_url",
    ]
    with conc_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for year in range(2000, 2027):
            tot = TOTALS_MILLION_YEN.get(year)
            rs = sorted(rows_by_year.get(year, []), key=lambda r: -r["oku"])
            row = {"year": year}
            if tot is None or not rs:
                row.update({c: "" for c in cols if c != "year"})
                row["source_url"] = "NA (eiren 未公表)"
                w.writerow(row)
                continue
            total, dom, forn = (v / 100 for v in tot)
            top3 = rs[:3]
            top10 = rs[:10]
            dom_rs = [r for r in rs if r["section"] == "邦"][:10]
            top3_sum = round(sum(r["oku"] for r in top3), 1)
            top10_sum = round(sum(r["oku"] for r in top10), 1)
            dom10_sum = round(sum(r["oku"] for r in dom_rs), 1)
            titles10 = [clean_title(r["title"]) for r in top10]
            row.update(
                {
                    "total_oku": round(total, 2),
                    "domestic_oku": round(dom, 2),
                    "foreign_oku": round(forn, 2),
                    "n_over_100": sum(r["oku"] >= 100 for r in rs),
                    "top1_title": clean_title(rs[0]["title"]),
                    "top1_oku": rs[0]["oku"],
                    "top3_sum": top3_sum,
                    "top3_share": round(top3_sum / total, 4),
                    "top10_sum": top10_sum,
                    "top10_share": round(top10_sum / total, 4),
                    "top10_domestic_sum": dom10_sum,
                    "top10_domestic_share": round(dom10_sum / dom, 4),
                    "n_kids_family_ip_top10": sum(is_kids_family(t) for t in titles10),
                    "n_anime_top10": sum(is_anime(t) for t in titles10),
                    "n_films_over_10": len(rs),
                    "sum_over_10": round(sum(r["oku"] for r in rs), 1),
                    "top3_titles": " / ".join(clean_title(r["title"]) for r in top3),
                    "source_url": f"{ranking_url(year)} ; {TOTALS_URL}",
                }
            )
            w.writerow(row)
    print("wrote", films_path, conc_path)


if __name__ == "__main__":
    main(sys.argv[1])
