"""総務省 結果調 Excel の純粋変換（行リストは実ファイルの様式を縮約した合成、2026-10-27 確認）。"""

import pytest

from theme_parliament_size import soumu

PREFS_BY_BLOCK: dict[str, list[str]] = {
    "北海道": ["北海道"],
    "東北": ["青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"],
    "北関東": ["茨城県", "栃木県", "群馬県", "埼玉県"],
    "南関東": ["千葉県", "神奈川県", "山梨県"],
    "東京都": ["東京都"],
    "北陸信越": ["新潟県", "富山県", "石川県", "福井県", "長野県"],
    "東海": ["岐阜県", "静岡県", "愛知県", "三重県"],
    "近畿": ["滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県"],
    "中国": ["鳥取県", "島根県", "岡山県", "広島県", "山口県"],
    "四国": ["徳島県", "香川県", "愛媛県", "高知県"],
    "九州": ["福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"],
}
PREFS = [p for ps in PREFS_BY_BLOCK.values() for p in ps]
assert len(PREFS) == 47


def smd_rows() -> soumu.Rows:
    rows: soumu.Rows = [
        ["　　２．投票結果", "", "", "（１）都道府県別有権者数、投票者数、投票率（小選挙区）"],
        [],
        ["", "", "選　挙　当　日　の　有　権　者　数", "", "", "投　　票　　者　　数"],
        ["区　　分"],
        ["", "男", "女", "計", "男", "女", "計", "男", "女", "計"],
        [],
    ]
    for i, p in enumerate(PREFS):
        el = 1000.0 * (i + 1)
        rows.append([p, el / 2, el / 2, el, el / 4, el / 4, el / 2, el / 4, el / 4, el / 2])
    total = sum(1000.0 * (i + 1) for i in range(47))
    rows.append(["計", total / 2, total / 2, total, total / 4, total / 4, total / 2, 0, 0, 0])
    return rows


def pr_electorate_rows() -> soumu.Rows:
    rows: soumu.Rows = [
        ["", "", "", "（２）都道府県別有権者数、投票者数、投票率（比例代表）"],
        [],
        ["比例代表区", "区　　分", "男", "女", "計", "男", "女", "計", "男", "女", "計"],
        [],
    ]
    grand = 0.0
    for block, prefs in PREFS_BY_BLOCK.items():
        bsum = 0.0
        for j, p in enumerate(prefs):
            el = 1000.0 * (PREFS.index(p) + 1)
            bsum += el
            rows.append(
                [
                    f" {block}" if j == 0 else " ",
                    f"　{p}",
                    el / 2,
                    el / 2,
                    el,
                    1,
                    1,
                    el / 2,
                    0,
                    0,
                    0,
                ]
            )
        if len(prefs) > 1:
            rows.append(["", "　計", bsum / 2, bsum / 2, bsum, 1, 1, bsum / 2, 0, 0, 0])
        grand += bsum
    rows.append(["計", "", grand / 2, grand / 2, grand, 1, 1, grand / 2, 0, 0, 0])
    return rows


VOTES = {"甲党": 60_000.5, "乙党": 30_000.0, "丙党": 10_000.0}


def pr_votes_rows(as_text: bool = True) -> soumu.Rows:
    rows: soumu.Rows = [["（10）比例代表選挙区別党派別得票数"], []]
    for block in PREFS_BY_BLOCK:
        rows.append(["", f"＜{block}選挙区＞"])
        rows.append(["順位", "政党等名", "得票数", "得票率"] * 3)
        rows.append([])
        total = sum(VOTES.values())
        for rank, (party, v) in enumerate(VOTES.items(), start=1):
            votes = f"{v:,.3f}" if as_text else v
            rows.append([float(rank), party, votes, v / total * 100])
            rows.append([])
        rows.append(["", "得票総数", f"{total:,.3f}" if as_text else total, 100.0])
        rows.append([])
    return rows


def pr_seats_rows() -> soumu.Rows:
    """各ブロック 3 議席: 甲党 2（順位 1, 3）、乙党 1（順位 2）。丙党は別チャンクで 0。"""
    rows: soumu.Rows = [["（12）党派別議席配分表（比例代表）"], []]
    for block in PREFS_BY_BLOCK:
        rows += [
            ["", f"<{block}選挙区>"],
            ["除数", "      甲党", "", "      乙党"],
            [],
            ["", "順位", "", "順位"],
            [1.0, 1.0, "60,000.500", 2.0, "30,000.000"],
            [2.0, 3.0, "30,000.250", "", "15,000.000"],
            [3.0, "", "20,000.167"],
            [4.0],
            ["", f"<{block}選挙区>"],
            ["除数", "      丙党"],
            [],
            ["", "順位"],
            [1.0, "", "10,000.000"],
            [2.0],
        ]
    return rows


def test_url_raw_name_and_magic() -> None:
    assert soumu.url(50, "electorate_smd") == "https://www.soumu.go.jp/main_content/000979118.xls"
    assert soumu.url(51, "pr_seats_table") == "https://www.soumu.go.jp/main_content/001061486.xlsx"
    assert soumu.raw_name(50, "pr_votes_by_block") == "shugiin50_pr_votes_by_block.xls"
    assert soumu.magic(50) == b"\xd0\xcf\x11\xe0" and soumu.magic(51) == b"PK"


def test_parse_electorate_smd_reads_47_prefectures_and_checks_the_total() -> None:
    out = soumu.parse_electorate_smd(smd_rows())
    assert len(out) == 47
    assert out[0] == {"pref": "北海道", "electorate": 1000.0, "voters": 500.0}
    assert out[-1]["pref"] == "沖縄県"
    bad = smd_rows()
    bad[-1][3] = 1.0
    with pytest.raises(ValueError, match="parts"):
        soumu.parse_electorate_smd(bad)
    with pytest.raises(ValueError, match="expected 47"):
        soumu.parse_electorate_smd(smd_rows()[:-5])


def test_parse_electorate_pr_assigns_blocks_and_checks_block_totals() -> None:
    out = soumu.parse_electorate_pr(pr_electorate_rows())
    assert len(out) == 47
    assert out[0] == {"block": "北海道", "pref": "北海道", "electorate": 1000.0, "voters": 500.0}
    assert {r["pref"]: r["block"] for r in out}["山梨県"] == "南関東"
    assert {r["pref"]: r["block"] for r in out}["東京都"] == "東京"
    bad = pr_electorate_rows()
    idx = next(i for i, r in enumerate(bad) if len(r) > 1 and r[1] == "　計")
    bad[idx][4] = 5.0
    with pytest.raises(ValueError, match="block 東北"):
        soumu.parse_electorate_pr(bad)


@pytest.mark.parametrize("as_text", [True, False])
def test_parse_pr_votes_reads_every_block_and_checks_totals(as_text: bool) -> None:
    out = soumu.parse_pr_votes(pr_votes_rows(as_text))
    assert len(out) == 33
    assert out[0] == {
        "block": "北海道",
        "rank": 1,
        "party": "甲党",
        "votes": 60_000.5,
        "share_pct": pytest.approx(60.0, abs=0.01),
    }
    assert {r["block"] for r in out} == set(soumu.BLOCKS)
    bad = pr_votes_rows(as_text)
    bad[5][2] = "1"
    with pytest.raises(ValueError, match="pr_votes block 北海道"):
        soumu.parse_pr_votes(bad)
    with pytest.raises(ValueError, match="verified total"):
        soumu.parse_pr_votes(pr_votes_rows(as_text)[:-12])


def test_parse_pr_seats_counts_rank_cells_per_party_across_chunks() -> None:
    out = soumu.parse_pr_seats(pr_seats_rows())
    assert len(out) == 22  # 11 ブロック × 2 党（丙党は 0 議席なので出ない）
    assert out[:2] == [
        {"block": "北海道", "party": "甲党", "seats": 2},
        {"block": "北海道", "party": "乙党", "seats": 1},
    ]
    bad = pr_seats_rows()
    bad[6][3] = 5.0  # 北海道の乙党の順位を 2 → 5 に: 1..S が埋まらない
    with pytest.raises(ValueError, match="block 北海道: ranks"):
        soumu.parse_pr_seats(bad)


def test_build_marts_join_and_fail_closed() -> None:
    meta50 = {"election": 50, "election_date": "2024-10-27"}
    staged = [
        {**meta50, "tier": "smd", "block": None, **r}
        for r in soumu.parse_electorate_smd(smd_rows())
    ] + [{**meta50, "tier": "pr", **r} for r in soumu.parse_electorate_pr(pr_electorate_rows())]
    mart = soumu.build_electorate_mart(staged)
    assert len(mart) == 47
    assert mart[0]["pref"] == "北海道" and mart[0]["block"] == "北海道"
    assert mart[0]["electorate_smd"] == mart[0]["electorate_pr"] == 1000.0
    with pytest.raises(ValueError, match="incomplete"):
        soumu.build_electorate_mart(staged[:47])  # smd のみ → block/electorate_pr が無い

    votes = [{**meta50, **r} for r in soumu.parse_pr_votes(pr_votes_rows())]
    seats = [{**meta50, **r} for r in soumu.parse_pr_seats(pr_seats_rows())]
    pr = soumu.build_pr_mart(votes, seats)
    assert len(pr) == 33
    first = pr[0]
    assert (first["block"], first["party"], first["seats"], first["block_seats"]) == (
        "北海道",
        "甲党",
        2,
        3,
    )
    assert pr[2]["seats"] == 0 and pr[2]["party"] == "丙党"
    assert first["block_votes"] == pytest.approx(100_000.5)
    with pytest.raises(ValueError, match="without a vote row"):
        soumu.build_pr_mart(
            votes, [*seats, {**meta50, "block": "北海道", "party": "丁党", "seats": 1}]
        )


def winners_sheets() -> list[soumu.Rows]:
    """2 党 ＋ 無所属（別シート）。小選挙区 289・比例 176 を満たす合成。"""
    main: soumu.Rows = [
        [
            "3. 開票結果",
            "",
            "",
            "",
            "",
            "（１）届出政党等別男女別新前元別当選人数(小選挙区、比例代表)",
        ],
        [],
        ["", "", "甲党", "", "", "乙党"],
        ["区  分"],
        ["", "", "男", "女", "計", "男", "女", "計"],
        ["小", "新", 1.0, 0.0, 1.0, 0.0, 0.0, 0.0],
        ["選", "前", 199.0, 0.0, 199.0, 80.0, 0.0, 80.0],
        ["挙", "元", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ["区", "計", 200.0, 0.0, 200.0, 80.0, 0.0, 80.0],
        ["比", "新", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ["例", "前", 100.0, 0.0, 100.0, 76.0, 0.0, 76.0],
        ["代", "元", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ["表", "計", 100.0, 0.0, 100.0, 76.0, 0.0, 76.0],
        ["", "新", 1.0, 0.0, 1.0, 0.0, 0.0, 0.0],
        ["合", "前", 299.0, 0.0, 299.0, 156.0, 0.0, 156.0],
        ["計", "元", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ["", "計", 300.0, 0.0, 300.0, 156.0, 0.0, 156.0],
    ]
    other: soumu.Rows = [
        ["3. 開票結果"],
        ["", "", "本人･推薦届出"],
        ["", "", "", "", "", "", "", "", "", "", "", "　　     合　計"],
        [
            "区  分",
            "",
            "         政党等所属",
            "",
            "",
            "         無所属",
            "",
            "",
            "         小   計",
        ],
        ["", "", "男", "女", "計", "男", "女", "計", "男", "女", "計", "男", "女", "計"],
        ["小", "新", "", "", "", 3.0, "", 3.0, 3.0, "", 3.0, 27.0, 7.0, 34.0],
        ["選", "前", "", "", "", 5.0, "", 5.0, 5.0, "", 5.0, 219.0, 27.0, 246.0],
        ["挙", "元", 1.0, "", 1.0, "", "", "", 1.0, "", 1.0, 8.0, 1.0, 9.0],
        ["区", "計", 1.0, "", 1.0, 8.0, "", 8.0, 9.0, "", 9.0, 254.0, 35.0, 289.0],
        ["比", "新"],
        ["例", "前"],
        ["代", "元"],
        ["表", "計", "", "", "", "", "", "", "", "", "", 138.0, 38.0, 176.0],
        ["", "新", "", "", "", 3.0, "", 3.0],
        ["合", "前", "", "", "", 5.0, "", 5.0],
        ["計", "元", 1.0, "", 1.0],
        ["", "計", 1.0, "", 1.0, 8.0, "", 8.0, 9.0, "", 9.0, 392.0, 73.0, 465.0],
    ]
    return [main, other]


def test_parse_winners_reads_smd_and_pr_seats_per_party_and_checks_totals() -> None:
    out = soumu.parse_winners(winners_sheets())
    assert out == [
        {"party": "甲党", "smd_seats": 200.0, "pr_seats": 100.0},
        {"party": "乙党", "smd_seats": 80.0, "pr_seats": 76.0},
        {"party": "無所属", "smd_seats": 8.0, "pr_seats": 0.0},
        {"party": "本人届出（政党等所属）", "smd_seats": 1.0, "pr_seats": 0.0},
    ]
    bad = winners_sheets()
    bad[0][8][4] = 199.0
    with pytest.raises(ValueError, match="winners: smd 288.0"):
        soumu.parse_winners(bad)
    mart = soumu.build_winners_mart(
        [{"election": 50, "election_date": "2024-10-27", **r} for r in out]
    )
    assert mart[0]["total_seats"] == 300.0 and mart[0]["iso3"] == "JPN"
    assert [r["party"] for r in mart][:2] == ["甲党", "乙党"]
